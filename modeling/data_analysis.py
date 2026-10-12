"""Read-only data diagnostics using Pandas, with declared interpretation limits."""
import math

import pandas as pd


def _finite_json(value, name):
    if value is None or type(value) in (bool, int, str):
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as error:
                raise ValueError(f"{name}: invalid Unicode string") from error
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite_json(item, f"{name}[{index}]")
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for key, item in value.items():
            _finite_json(key, name)
            _finite_json(item, f"{name}.{key}")
        return
    raise ValueError(f"{name}: expected finite JSON values")


def _records_frame(records, name, keys):
    if not isinstance(records, list):
        raise ValueError(f"{name} must be a list of records")
    if len(records) > 200_000:
        raise ValueError(f"{name} exceeds the 200000 input-row audit limit")
    schema = set(records[0]) if records and isinstance(records[0], dict) else set(keys)
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != schema:
            raise ValueError(f"{name}[{index}]: records must have one consistent column schema")
        _finite_json(record, f"{name}[{index}]")
        for key in keys:
            if key not in record:
                raise ValueError(f"{name}: missing join key {key!r}")
            if record[key] is not None and type(record[key]) not in (str, int, float, bool):
                raise ValueError(f"{name}.{key}: join keys must be finite JSON scalars or null")
    if records and not set(keys) <= schema:
        raise ValueError(f"{name}: missing join keys")
    # Object dtype avoids converting large integer keys to imprecise floats when
    # a column also contains null. No parsing, casting or mutation of input keys.
    return pd.DataFrame(records, columns=keys, dtype=object)


def _key_kind(frame, key, name):
    kinds = {type(value).__name__ for value in frame[key] if value is not None}
    if len(kinds) > 1:
        raise ValueError(f"{name}.{key}: mixed key types {sorted(kinds)} require explicit upstream normalization")
    return next(iter(kinds), "unknown")


def _internal_name(columns, name):
    while name in columns:
        name += "_"
    return name


def audit_join(left, right, on, how="left", relationship="many_to_one",
               null_policy="reject", max_output_rows=100_000):
    """Audit a declared join without returning or changing the input records.

    ``on`` identifies key tuples, not a verified scientific entity. Null policy
    is reject (default), drop all rows with any null key, or explicitly match
    using Pandas semantics (including matching null to null). A grouped-key
    merge computes exact output cardinality before the row-ID merge is allowed.
    Only keys and source row IDs are materialized; payload columns are not joined.
    """
    keys = [on] if isinstance(on, str) else on
    if (not isinstance(keys, list) or not keys or
            any(not isinstance(key, str) or not key for key in keys) or
            len(set(keys)) != len(keys)):
        raise ValueError("on must contain unique nonempty column names")
    _finite_json(keys, "on")
    if not isinstance(how, str) or how not in {"inner", "left", "right", "outer"}:
        raise ValueError("how must be inner, left, right or outer")
    if not isinstance(relationship, str) or relationship not in {"one_to_one", "one_to_many", "many_to_one", "many_to_many"}:
        raise ValueError("relationship must declare one_to_one, one_to_many, many_to_one or many_to_many")
    if not isinstance(null_policy, str) or null_policy not in {"reject", "drop", "match"}:
        raise ValueError("null_policy must be reject, drop or match")
    if type(max_output_rows) is not int or not 1 <= max_output_rows <= 1_000_000:
        raise ValueError("max_output_rows must be an integer between 1 and 1000000")
    left_df, right_df = _records_frame(left, "left", keys), _records_frame(right, "right", keys)
    key_types = {}
    for key in keys:
        left_type, right_type = _key_kind(left_df, key, "left"), _key_kind(right_df, key, "right")
        if left_type != "unknown" and right_type != "unknown" and left_type != right_type:
            raise ValueError(f"{key}: incompatible left/right key types {left_type}/{right_type}")
        key_types[key] = {"left": left_type, "right": right_type}
    null_left = left_df[keys].isna().any(axis=1)
    null_right = right_df[keys].isna().any(axis=1)
    null_counts = {"left": int(null_left.sum()), "right": int(null_right.sum())}
    if null_policy == "reject" and any(null_counts.values()):
        raise ValueError(f"Null join keys rejected: {null_counts}; declare drop or match explicitly")
    if null_policy == "drop":
        left_df, right_df = left_df.loc[~null_left], right_df.loc[~null_right]
    left_id = _internal_name(keys, "__praxis_left_row")
    right_id = _internal_name(keys + [left_id], "__praxis_right_row")
    indicator = _internal_name(keys + [left_id, right_id], "__praxis_merge")
    left_keys, right_keys = left_df[keys].copy(), right_df[keys].copy()
    left_keys[left_id], right_keys[right_id] = left_df.index, right_df.index
    duplicate_left = bool(left_keys.duplicated(keys).any())
    duplicate_right = bool(right_keys.duplicated(keys).any())
    invalid_relationship = (
        relationship in {"one_to_one", "one_to_many"} and duplicate_left or
        relationship in {"one_to_one", "many_to_one"} and duplicate_right
    )
    if invalid_relationship:
        # Invoke the mature validator on the actual rows. Pandas validates
        # uniqueness before computing the result's potentially huge row index.
        left_keys.merge(right_keys, on=keys, how=how, validate=relationship,
                        indicator=indicator)
        raise RuntimeError("Pandas unexpectedly accepted the declared join relationship")
    left_count = _internal_name(keys, "__left_count")
    right_count = _internal_name(keys + [left_count], "__right_count")
    # Keep keys from the original object columns. reset_index after groupby can
    # coerce integer-plus-null group labels to float and round integer IDs.
    left_counts, right_counts = left_keys[keys].copy(), right_keys[keys].copy()
    left_counts[left_count] = left_keys.groupby(keys, dropna=False, sort=False)[left_id].transform("size")
    right_counts[right_count] = right_keys.groupby(keys, dropna=False, sort=False)[right_id].transform("size")
    counts = left_counts.drop_duplicates(keys).merge(
        right_counts.drop_duplicates(keys), on=keys, how="outer",
        validate="one_to_one", indicator=indicator)
    matched_left = matched_right = pairs = left_only = right_only = 0
    for left_n, right_n, category in counts[[left_count, right_count, indicator]].itertuples(index=False, name=None):
        if category == "both":
            left_n, right_n = int(left_n), int(right_n)
            pairs += left_n * right_n
            matched_left += left_n
            matched_right += right_n
        elif category == "left_only":
            left_only += int(left_n)
        else:
            right_only += int(right_n)
    estimated_rows = pairs + (left_only if how in {"left", "outer"} else 0) + (right_only if how in {"right", "outer"} else 0)
    if estimated_rows > max_output_rows:
        raise ValueError(f"Join would produce {estimated_rows} rows, exceeding max_output_rows={max_output_rows}; no row-pair join was materialized")
    estimated_cells = estimated_rows * (len(keys) + 3)  # keys, two row IDs, indicator
    if estimated_cells > 5_000_000:
        raise ValueError(f"Join would materialize {estimated_cells} key/row-ID cells, exceeding the 5000000 audit-cell limit; no row-pair join was materialized")
    joined = left_keys.merge(right_keys, on=keys, how=how, validate=relationship,
                             indicator=indicator)
    if len(joined) != estimated_rows:
        raise RuntimeError("Preflight cardinality disagrees with the actual Pandas join")
    result = {
        "status": "audited", "backend": {"library": "pandas", "version": pd.__version__, "validate": relationship},
        "on": keys, "how": how, "relationship": relationship, "null_policy": null_policy,
        "key_types": key_types, "max_output_rows": max_output_rows,
        "max_materialized_cells": 5_000_000, "estimated_materialized_cells": estimated_cells,
        "estimated_output_rows": estimated_rows, "output_rows": len(joined),
        "indicator_counts": {category: int((joined[indicator] == category).sum()) for category in ("both", "left_only", "right_only")},
        "key_entities": {"definition": "Distinct join-key tuples; scientific entity meaning is not inferred", "output": int(joined[keys].drop_duplicates().shape[0])},
        "materialization": "Join-key columns and source row IDs only; original records and payload values are not returned",
        "overlapping_payload_columns": sorted((set(left[0] if left else []) & set(right[0] if right else [])) - set(keys)),
        "interpretation": {"observation_unit": "unknown", "units": "unknown", "population": "unknown", "payload_merge_compatibility": "not_checked"},
    }
    for name, frame, original, null_rows, matched, row_id in [
        ("left", left_keys, left, null_counts["left"], matched_left, left_id),
        ("right", right_keys, right, null_counts["right"], matched_right, right_id),
    ]:
        unique = int(frame[keys].drop_duplicates().shape[0])
        retained = int(joined[row_id].nunique())
        result[name] = {
            "original_rows": len(original), "effective_rows": len(frame), "null_key_rows": null_rows,
            "dropped_null_key_rows": null_rows if null_policy == "drop" else 0,
            "unique_keys": unique, "duplicate_key_rows": int(frame.duplicated(keys, keep=False).sum()),
            "duplicate_key_excess_rows": len(frame) - unique, "matched_input_rows": matched,
            "unmatched_input_rows": len(frame) - matched,
            "unmatched_fraction_effective": (len(frame) - matched) / len(frame) if len(frame) else None,
            "retained_input_rows": retained, "omitted_effective_input_rows": len(frame) - retained,
            "output_row_contributions": int(joined[row_id].notna().sum()),
            "expansion_factor": len(joined) / len(frame) if len(frame) else None,
            "key_entity_change": result["key_entities"]["output"] - unique,
        }
    return result
