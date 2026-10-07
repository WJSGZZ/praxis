"""Create a new byte-identical read-only snapshot, never modify the source PDF."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader


def freeze(source, destination):
    raw = source.read_bytes()
    doc = PdfReader(BytesIO(raw))
    if doc.is_encrypted or len(doc.pages) == 0:
        raise ValueError("PDF must be readable and nonempty")
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects an existing snapshot even under concurrent use.
    with destination.open("xb") as stream:
        stream.write(raw)
    sha = hashlib.sha256(raw).hexdigest()
    if hashlib.sha256(destination.read_bytes()).hexdigest() != sha:
        raise RuntimeError("Snapshot integrity check failed")
    destination.chmod(0o444)
    return {"source": str(source.resolve()), "snapshot": str(destination.resolve()),
            "sha256": sha, "bytes": len(raw), "created_utc": datetime.now(timezone.utc).isoformat(),
            "note": "Local snapshot only; not proof of contest deadline compliance or submission."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    receipt_path = args.destination.with_suffix(".pdf.receipt.json")
    if receipt_path.exists():
        parser.error("Receipt already exists; choose a new destination")
    receipt = freeze(args.source, args.destination)
    # Receipt has its own name, never replaces the PDF or an earlier receipt.
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
