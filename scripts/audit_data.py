"""Read-only CSV/XLSX audit. Does not infer units or silently repair data."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd


def audit(path, sheet=0, encoding="utf-8", sep=","):
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, encoding=encoding, sep=sep)
    elif path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path, sheet_name=sheet)
    else:
        raise ValueError("Supported formats: .csv and .xlsx")
    numeric = df.select_dtypes(include="number")
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": len(df), "columns": len(df.columns), "duplicate_rows": int(df.duplicated().sum()),
            "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
            "missing": {str(k): int(v) for k, v in df.isna().sum().items()},
            "numeric_summary": json.loads(numeric.describe().to_json()) if len(numeric.columns) else {},
            "manual_review": ["Units and definitions", "Keys, joins and duplicate meaning", "Time order and sampling bias", "Missingness and valid ranges", "License and original source"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--sheet", default="0", help="Worksheet name or zero-based index")
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--sep", default=",")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sheet = int(args.sheet) if args.sheet.isdecimal() else args.sheet
    result = json.dumps(audit(args.path, sheet, args.encoding, args.sep), ensure_ascii=False, indent=2)
    if args.output:
        if args.output.resolve() == args.path.resolve():
            parser.error("Output must not overwrite input")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
