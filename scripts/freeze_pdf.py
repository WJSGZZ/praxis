"""Create a new byte-identical read-only snapshot, never modify the source PDF."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader


def freeze(source, destination, *, tex=None, contest=None, build_receipt=None):
    layout = None
    if (tex is None) != (contest is None):
        raise ValueError("Supply both TeX source and contest for a layout-gated snapshot")
    if build_receipt is not None and tex is None:
        raise ValueError("Build receipts require TeX source and contest")
    if tex is not None:
        from scripts.paper_template import check
        layout = check(tex.read_text(encoding='utf-8'), contest)
    raw = source.read_bytes()
    if layout is not None:
        if build_receipt is None:
            raise ValueError('Layout-gated freeze requires a canonical --build-receipt')
        build = json.loads(Path(build_receipt).read_text(encoding='utf-8'))
        runtime = json.loads((Path(__file__).resolve().parents[1]/'templates/typesetting-runtime.json').read_text(encoding='utf-8'))
        if (build.get('runtime') != runtime or build.get('layout') != layout
                or build.get('tex_sha256') != hashlib.sha256(tex.read_bytes()).hexdigest()
                or build.get('pdf_sha256') != hashlib.sha256(raw).hexdigest()):
            raise ValueError('Canonical build receipt does not match runtime, layout, source or PDF')
        layout['tex_sha256'] = hashlib.sha256(tex.read_bytes()).hexdigest()
        layout['runtime_profile'] = runtime['profile']
        layout['build_receipt_sha256'] = hashlib.sha256(Path(build_receipt).read_bytes()).hexdigest()
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
    return {**({"layout": layout} if layout else {}), "source": str(source.resolve()), "snapshot": str(destination.resolve()),
            "sha256": sha, "bytes": len(raw), "created_utc": datetime.now(timezone.utc).isoformat(),
            "note": "Local snapshot only; not proof of contest deadline compliance or submission."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--tex", type=Path, help="Required with --contest; validate shared layout before snapshot")
    parser.add_argument("--build-receipt", type=Path, help="Canonical .build.json receipt required for layout-gated freezing")
    parser.add_argument("--contest", choices=["mcm", "cumcm"])
    args = parser.parse_args()
    receipt_path = args.destination.with_suffix(".pdf.receipt.json")
    if receipt_path.exists():
        parser.error("Receipt already exists; choose a new destination")
    receipt = freeze(args.source, args.destination, tex=args.tex, contest=args.contest, build_receipt=args.build_receipt)
    # Receipt has its own name, never replaces the PDF or an earlier receipt.
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
