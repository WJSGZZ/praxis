"""Read-only CSV/TSV/XLSX diagnostics with parsing and contract disclosure."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import warnings

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype

from modeling.data_analysis import _finite_json
from modeling.schema_contracts import unique_object_pairs


def _sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _header_value(value):
    if value is None or type(value) in (str, int, float, bool):
        return value
    if hasattr(value, "item"):
        return _header_value(value.item())
    return str(value)


def _header_report(original, parsed, original_types=None, parsed_types=None):
    duplicates = []
    for position, name in enumerate(original):
        if any(name == earlier for earlier in original[:position]):
            continue
        positions = [index for index, other in enumerate(original) if name == other]
        if len(positions) > 1:
            duplicates.append({"name": name, "positions": positions})
    mapping = [{"position": index, "original": name, "parsed": parsed[index],
                "renamed": name != parsed[index]} for index, name in enumerate(original)]
    return {"position_base": 0, "original_names": original, "parsed_names": parsed,
            "original_name_types": original_types or [type(name).__name__ for name in original],
            "parsed_name_types": parsed_types or [type(name).__name__ for name in parsed],
            "mapping": mapping, "duplicate_original_names": duplicates,
            "blank_original_positions": [index for index, name in enumerate(original) if name == ""],
            "automatic_renaming": any(item["renamed"] for item in mapping)}


def _numeric_reports(numeric):
    if not len(numeric.columns):
        return [], []
    profiles = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        summary = numeric.describe()
        for position, name in enumerate(numeric.columns):
            series = numeric.iloc[:, position]
            present = series.notna()
            finite = np.isfinite(series)
            nonfinite_count = int((present & ~finite).sum())
            null_fields = {}
            for statistic, value in summary.iloc[:, position].items():
                if np.isnan(value):
                    null_fields[statistic] = "nan"
                elif np.isposinf(value):
                    null_fields[statistic] = "positive_infinity"
                elif np.isneginf(value):
                    null_fields[statistic] = "negative_infinity"
            profile = {"numeric_summary": json.loads(summary.iloc[:, position].to_json()),
                       "numeric_summary_status": {"nonfinite_nonmissing": nonfinite_count,
                                                  "null_serialized_statistics": null_fields},
                       "numeric_finite_summary": None}
            if nonfinite_count:
                finite_series = series.loc[finite]
                profile["numeric_finite_summary"] = {
                    "status": "computed" if len(finite_series) else "no_finite_observations",
                    "included_finite": len(finite_series), "excluded_nonfinite_nonmissing": nonfinite_count,
                    "excluded_missing": int(series.isna().sum()),
                    "summary": json.loads(finite_series.describe().to_json())}
            profiles.append(profile)
    return profiles, [str(warning.message) for warning in caught]


def _column_reference(df, display_name):
    matches = [{"position": position, "parsed_name": _header_value(name),
                "parsed_name_type": type(name).__name__}
               for position, name in enumerate(df.columns) if str(name) == display_name]
    return {"display_name": display_name,
            "status": "matched" if len(matches) == 1 else "ambiguous" if matches else "missing",
            "matches": matches}


def _contract_report(df, contract):
    if contract is None:
        contract = {}
    if not isinstance(contract, dict):
        raise ValueError("contract must be an object")
    _finite_json(contract, "contract")
    supported = {"observation_unit", "population", "coverage", "source", "columns", "unique_keys"}
    if set(contract) - supported:
        raise ValueError(f"Unsupported contract fields: {sorted(set(contract) - supported)}")
    metadata = {}
    for field in ("observation_unit", "population", "coverage", "source"):
        value = contract.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"contract.{field} must be a nonempty string")
        metadata[field] = {"status": "declared" if value is not None else "unknown", "value": value}
    declarations = contract.get("columns", {})
    if not isinstance(declarations, dict):
        raise ValueError("contract.columns must be an object keyed by JSON display names of parsed columns")
    issues, checks, column_matches = [], [], []
    for name, rules in declarations.items():
        if not isinstance(rules, dict) or set(rules) - {"meaning", "unit", "kind", "nullable", "finite", "minimum", "maximum", "allowed_values"}:
            raise ValueError(f"contract.columns.{name}: unsupported or invalid rules")
        for field in ("meaning", "unit"):
            if field in rules and (not isinstance(rules[field], str) or not rules[field].strip()):
                raise ValueError(f"{name}.{field} must be a nonempty string")
        if "nullable" in rules and type(rules["nullable"]) is not bool:
            raise ValueError(f"{name}.nullable must be a boolean")
        if "finite" in rules and type(rules["finite"]) is not bool:
            raise ValueError(f"{name}.finite must be a boolean")
        kind = rules.get("kind")
        if "kind" in rules and (not isinstance(kind, str) or kind not in {"numeric", "integer", "string", "boolean", "datetime"}):
            raise ValueError(f"{name}.kind is unsupported")
        for field in ("minimum", "maximum"):
            if field in rules and type(rules[field]) not in (int, float):
                raise ValueError(f"{name}.{field} must be a finite number")
        if "minimum" in rules and "maximum" in rules and rules["minimum"] > rules["maximum"]:
            raise ValueError(f"{name}: minimum exceeds maximum")
        allowed = rules.get("allowed_values")
        if "allowed_values" in rules and (not isinstance(allowed, list) or any(isinstance(value, (list, dict)) for value in allowed)):
            raise ValueError(f"{name}.allowed_values must be scalar JSON values")
        reference = _column_reference(df, name)
        column_matches.append(reference)
        if reference["status"] == "missing":
            issues.append({"column": name, "check": "present", "status": "failed", "count": None, "column_reference": reference})
            continue
        if reference["status"] == "ambiguous":
            issues.append({"column": name, "check": "column_reference", "status": "not_checked",
                           "reason": "JSON display name matches multiple typed columns; no column selected", "column_reference": reference})
            continue
        series = df.iloc[:, reference["matches"][0]["position"]]
        present = series.dropna()
        numeric = is_numeric_dtype(series.dtype) and not is_bool_dtype(series.dtype)
        invalid_kind = 0
        if kind == "numeric":
            invalid_kind = 0 if numeric else len(present)
        elif kind == "integer":
            invalid_kind = int((present % 1 != 0).sum()) if numeric else len(present)
        elif kind == "string":
            invalid_kind = int(sum(not isinstance(value, str) for value in present))
        elif kind == "boolean":
            invalid_kind = int(sum(not isinstance(value, bool) for value in present))
        elif kind == "datetime":
            invalid_kind = 0 if is_datetime64_any_dtype(series.dtype) else len(present)
        failures = {}
        if kind is not None:
            failures["kind"] = invalid_kind
        if rules.get("nullable") is False:
            failures["not_null"] = int(series.isna().sum())
        if rules.get("finite") is True:
            if numeric:
                failures["finite"] = int((series.notna() & ~np.isfinite(series)).sum())
            elif len(present):
                issues.append({"column": name, "check": "finite", "status": "not_checked", "reason": "Parsed column is not numeric; no coercion performed"})
        if allowed is not None:
            failures["allowed_values"] = int((~series.isin(allowed) & series.notna()).sum())
        for field, operation in (("minimum", "lt"), ("maximum", "gt")):
            if field in rules:
                if numeric:
                    failures[field] = int(getattr(present, operation)(rules[field]).sum())
                elif len(present):
                    issues.append({"column": name, "check": field, "status": "not_checked", "reason": "Parsed column is not numeric; no coercion performed"})
        for check, count in failures.items():
            record = {"column": name, "check": check, "status": "failed" if count else "passed", "count": count,
                      "column_reference": reference}
            checks.append(record)
            if count:
                issues.append(record)
    keys = contract.get("unique_keys", [])
    if not isinstance(keys, list):
        raise ValueError("contract.unique_keys must be a list of column-name lists")
    key_checks = []
    for key in keys:
        if (not isinstance(key, list) or not key or any(not isinstance(name, str) for name in key)
                or len(set(key)) != len(key)):
            raise ValueError("Each declared unique key must contain distinct column names")
        references = [_column_reference(df, name) for name in key]
        absent = [item["display_name"] for item in references if item["status"] == "missing"]
        ambiguous = [item["display_name"] for item in references if item["status"] == "ambiguous"]
        if absent:
            record = {"columns": key, "status": "failed", "missing_columns": absent}
        elif ambiguous:
            record = {"columns": key, "status": "not_checked", "ambiguous_columns": ambiguous,
                      "reason": "JSON display name matches multiple typed columns; no key selected"}
        else:
            selected = df.iloc[:, [item["matches"][0]["position"] for item in references]]
            null_rows = int(selected.isna().any(axis=1).sum())
            duplicate_rows = int(selected.duplicated(keep=False).sum())
            record = {"columns": key, "status": "failed" if null_rows or duplicate_rows else "passed",
                      "null_key_rows": null_rows, "duplicate_key_rows": duplicate_rows}
        record["column_references"] = references
        key_checks.append(record)
        if record["status"] != "passed":
            issues.append({"check": "unique_key", **record})
    column_metadata = []
    for position, name in enumerate(df.columns):
        reference = _column_reference(df, str(name))
        rules = declarations.get(str(name), {})
        record = {"position": position, "parsed_name": _header_value(name), "parsed_name_type": type(name).__name__,
                  "column_reference": reference}
        for field in ("meaning", "unit"):
            declared = rules.get(field)
            record[field] = {"status": "ambiguous" if declared and reference["status"] == "ambiguous" else "declared" if declared else "unknown",
                             "value": declared if reference["status"] == "matched" else None}
            if declared and reference["status"] == "ambiguous":
                record[field]["unapplied_declaration"] = declared
        column_metadata.append(record)
    return {"status": "issues_found" if issues else ("checked" if declarations or keys else "not_declared"),
            "metadata": metadata, "column_declarations": declarations, "checks": checks,
            "column_matches": column_matches,
            "column_metadata": column_metadata,
            "unique_key_checks": key_checks, "issues": issues,
            "scope": "Supplied declarations checked against parsed rows only; units, meanings, population and sampling design are not independently verified"}


def audit(path, sheet=0, encoding="utf-8", sep=None, *, contract=None,
          max_rows=None, missing_values=None, keep_default_na=True):
    path = Path(path)
    if max_rows is not None and (type(max_rows) is not int or max_rows < 1):
        raise ValueError("max_rows must be a positive integer or null")
    if type(keep_default_na) is not bool:
        raise ValueError("keep_default_na must be a boolean")
    if missing_values is not None:
        _finite_json(missing_values, "missing_values")
        if not isinstance(missing_values, list) or any(isinstance(value, (list, dict)) for value in missing_values):
            raise ValueError("missing_values must be a list of scalar JSON values")
    original_hash = _sha256(path)
    read_options = {"nrows": max_rows + 1 if max_rows else None,
                    "keep_default_na": keep_default_na, "na_values": missing_values}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if path.suffix.lower() in {".csv", ".tsv"}:
            separator = sep if sep is not None else ("\t" if path.suffix.lower() == ".tsv" else ",")
            if not isinstance(separator, str) or len(separator) != 1 or separator in {"\n", "\r"}:
                raise ValueError("sep must be a single delimiter character")
            raw_header = pd.read_csv(path, encoding=encoding, sep=separator, header=None,
                                     nrows=1, dtype=str, keep_default_na=False)
            original = raw_header.iloc[0].tolist() if len(raw_header) else []
            original_types = [type(name).__name__ for name in original]
            def read_rows(nrows):
                return pd.read_csv(path, encoding=encoding, sep=separator,
                                   **{**read_options, "nrows": nrows})
            df = read_rows(read_options["nrows"])
            parser = {"format": path.suffix.lower()[1:], "encoding": encoding, "separator": separator,
                      "header_row": "First nonblank CSV record", "skip_blank_lines": True}
        elif path.suffix.lower() == ".xlsx":
            if isinstance(sheet, str) and sheet.isdecimal():
                sheet = int(sheet)
            if not isinstance(sheet, (str, int)) or isinstance(sheet, bool):
                raise ValueError("sheet must be a sheet name or zero-based integer index")
            raw_header = pd.read_excel(path, sheet_name=sheet, header=None, nrows=1, keep_default_na=False, dtype=object)
            raw_names = raw_header.iloc[0].tolist() if len(raw_header) else []
            original_types = [type(name).__name__ for name in raw_names]
            original = [_header_value(value) for value in raw_names]
            def read_rows(nrows):
                return pd.read_excel(path, sheet_name=sheet, **{**read_options, "nrows": nrows})
            df = read_rows(read_options["nrows"])
            parser = {"format": "xlsx", "sheet": sheet, "header_row": 0}
        else:
            raise ValueError("Supported formats: .csv, .tsv and .xlsx")
        loaded_rows = len(df)
        truncated = max_rows is not None and loaded_rows > max_rows
        if truncated:
            # Reparse the requested prefix so a lookahead row with a different
            # type cannot change dtype inference or the prefix's summaries.
            df = read_rows(max_rows)
    parsed_names = [_header_value(name) for name in df.columns]
    if len(original) != len(parsed_names):
        raise ValueError("Original and parsed header lengths differ; cannot establish a positional column mapping")
    parser.update({"library": "pandas", "version": pd.__version__, "keep_default_na": keep_default_na,
                   "missing_values_declared": missing_values or [], "dtype_inference": True,
                   "default_na_policy": "Pandas default missing-value markers enabled" if keep_default_na else "Pandas default missing-value markers disabled",
                   "warnings": [str(warning.message) for warning in caught],
                   "implicit_index_inference": not isinstance(df.index, pd.RangeIndex),
                   "implicit_index_note": "Surplus leading row fields were interpreted as an index; header-label mapping does not establish field alignment" if not isinstance(df.index, pd.RangeIndex) else None})
    preserved_hash = _sha256(path)
    if preserved_hash != original_hash:
        raise RuntimeError("Input bytes changed while auditing; report is not a stable original-file snapshot")
    data_contract = _contract_report(df, contract)
    numeric_positions = [position for position in range(len(df.columns))
                         if is_numeric_dtype(df.iloc[:, position].dtype) and not is_bool_dtype(df.iloc[:, position].dtype)]
    numeric_profiles, summary_warnings = _numeric_reports(df.iloc[:, numeric_positions])
    by_position = dict(zip(numeric_positions, numeric_profiles))
    column_profiles, legacy = [], {name: {} for name in ("dtypes", "missing", "numeric_summary", "numeric_summary_status", "numeric_finite_summary")}
    for position, name in enumerate(df.columns):
        series = df.iloc[:, position]
        profile = {"position": position, "parsed_name": parsed_names[position],
                   "parsed_name_type": type(name).__name__, "display_name": str(name),
                   "dtype": str(series.dtype), "missing": int(series.isna().sum()),
                   "nonfinite_nonmissing": int((series.notna() & ~np.isfinite(series)).sum()) if position in by_position else None,
                   "unique_nonmissing": int(series.nunique())}
        profile.update(by_position.get(position, {"numeric_summary": None, "numeric_summary_status": None, "numeric_finite_summary": None}))
        column_profiles.append(profile)
        for field in legacy:
            if field == "dtypes":
                legacy[field][str(name)] = profile["dtype"]
            elif field == "missing":
                legacy[field][str(name)] = profile["missing"]
            elif profile[field] is not None:
                legacy[field][str(name)] = profile[field]
    collisions = []
    for name in dict.fromkeys(str(column) for column in df.columns):
        reference = _column_reference(df, name)
        if reference["status"] == "ambiguous":
            affected = [field for field in legacy if name in legacy[field]]
            collisions.append({**reference, "affected_fields": affected,
                               "policy": "Colliding legacy dictionary keys are null; complete results remain in column_profiles by position"})
            for field in affected:
                legacy[field][name] = None
    return {"path": str(path.resolve()), "sha256": original_hash,
            "original_preserved": True, "rows": len(df), "columns": len(df.columns),
            "duplicate_rows": int(df.duplicated().sum()),
            "header": _header_report(original, parsed_names, original_types, [type(name).__name__ for name in df.columns]),
            "scan": {"scope": "row_prefix" if truncated else "full_table", "truncated": truncated,
                     "sampling": "Ordered row prefix; not a random or representative sample" if truncated else "All parsed data rows",
                     "rows_audited": len(df), "rows_read": loaded_rows,
                     "total_rows": None if truncated else loaded_rows, "max_rows": max_rows,
                     "rows_available_lower_bound": loaded_rows, "scope_applies_to": "All summaries, missingness, duplicates and contract checks"},
            "parser": parser, "data_contract": data_contract,
            "column_profiles": column_profiles, "legacy_key_collisions": collisions,
            **legacy,
            "numeric_summary_policy": {"input": "All parsed audited numeric observations, including nonfinite values; original observations are unchanged",
                                       "serialization": "Pandas NaN and +/-inf summary statistics become JSON null; numeric_summary_status records their actual state",
                                       "finite_view": "Additional finite-only summaries for columns containing nonfinite observations; exclusions are counted explicitly and no cleaned dataset is created",
                                       "warnings": summary_warnings},
            "manual_review": ["Units and definitions", "Keys, joins and duplicate meaning", "Time order and sampling bias", "Missingness and valid ranges", "License and original source"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--sheet", default="0", help="Worksheet name or zero-based index")
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--sep", help="Single-character delimiter; defaults to comma for CSV and tab for TSV")
    parser.add_argument("--max-rows", type=int, help="Audit an ordered prefix; omitted scans the whole table")
    parser.add_argument("--missing-values", help="JSON array of explicitly declared missing-value markers")
    parser.add_argument("--no-default-na", action="store_true", help="Keep Pandas default NA tokens as literal data")
    parser.add_argument("--contract", type=Path, help="JSON file containing data declarations and checks")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sheet = int(args.sheet) if args.sheet.isdecimal() else args.sheet
    contract = json.loads(args.contract.read_text(encoding="utf-8"), object_pairs_hook=unique_object_pairs) if args.contract else None
    missing_values = json.loads(args.missing_values) if args.missing_values else None
    result = json.dumps(audit(args.path, sheet, args.encoding, args.sep, contract=contract,
                             max_rows=args.max_rows, missing_values=missing_values,
                             keep_default_na=not args.no_default_na), ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        for original in [args.path] + ([args.contract] if args.contract else []):
            if (args.output.resolve() == original.resolve()
                    or args.output.exists() and args.output.samefile(original)):
                parser.error("Output must not overwrite input or its source contract")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
