"""Create a new byte-identical read-only snapshot, never modify the source PDF."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader


def freeze(source, destination, *, tex=None, contest=None, build_receipt=None,
           minimum_font_tex_pt=None, font_review=None, structure_review=None):
    layout = None
    structure = None
    if (tex is None) != (contest is None):
        raise ValueError("Supply both TeX source and contest for a layout-gated snapshot")
    if build_receipt is not None and tex is None:
        raise ValueError("Build receipts require TeX source and contest")
    if structure_review is not None and tex is None:
        raise ValueError('A structure review requires TeX source and contest')
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
        from scripts.paper_structure import inspect_structure
        structure = inspect_structure(tex.read_bytes().decode('utf-8'), structure_review)
        if not structure['passed']:
            raise ValueError('Heading structure review failed: resolve single-child headings '
                             'or supply an exact-source-bound review with specific reasons; '
                             'inspect with python -m scripts.paper_structure')
    doc = PdfReader(BytesIO(raw))
    if doc.is_encrypted or len(doc.pages) == 0:
        raise ValueError("PDF must be readable and nonempty")
    sizes = None
    if font_review is not None and minimum_font_tex_pt is None:
        raise ValueError('A font review requires an explicit minimum font size')
    if minimum_font_tex_pt is not None:
        from scripts.check_pdf import inspect_font_sizes
        sizes = inspect_font_sizes(source, minimum_font_tex_pt, font_review)
        if not sizes['passed']:
            raise ValueError('PDF font-size review failed: ' + '; '.join(sizes['errors']))
    boundaries = None
    if layout is not None and contest in ('mcm', 'cumcm'):
        from scripts.contest_rules import evaluate, extract
        facts = evaluate(extract(source), contest)['facts']
        if contest == 'mcm':
            if facts['ai_report_heading_on_page'] is not None and not facts['ai_report_starts_new_page']:
                raise ValueError('PDF AI-report boundary is mixed or ambiguous; preceding solution content cannot be excluded')
            keys = ('total_pages', 'counted_pages', 'ai_report_from_page',
                    'ai_report_heading_on_page', 'ai_report_starts_new_page')
        else:
            keys = ('total_pages', 'body_pages', 'appendix_from_page', 'appendix_starts_new_page')
        # This is boundary evidence, not an edition-specific compliance pass.
        boundaries = {key: facts[key] for key in keys}
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
    return {**({"layout": layout} if layout else {}), **({"pdf_boundaries": boundaries} if boundaries else {}),
            **({"heading_structure_review": structure} if structure is not None else {}),
            **({"font_size_review": sizes} if sizes is not None else {}),
            "source": str(source.resolve()), "snapshot": str(destination.resolve()),
            "sha256": sha, "bytes": len(raw), "created_utc": datetime.now(timezone.utc).isoformat(),
            "note": "Local snapshot only; not proof of contest deadline compliance or submission."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--tex", type=Path, help="Required with --contest; validate shared layout before snapshot")
    parser.add_argument("--build-receipt", type=Path, help="Canonical .build.json receipt required for layout-gated freezing")
    parser.add_argument("--contest", choices=["mcm", "cumcm", "research"])
    parser.add_argument("--minimum-font-tex-pt", type=float, help="Reject undersized final text before snapshot creation")
    parser.add_argument("--font-review", type=Path, help="Exact-PDF-bound review of smaller mathematical text")
    parser.add_argument("--structure-review", type=Path, help="Exact-source-bound reasons for retaining single-child headings")
    args = parser.parse_args()
    receipt_path = args.destination.with_suffix(".pdf.receipt.json")
    if receipt_path.exists():
        parser.error("Receipt already exists; choose a new destination")
    receipt = freeze(args.source, args.destination, tex=args.tex, contest=args.contest, build_receipt=args.build_receipt,
                     minimum_font_tex_pt=args.minimum_font_tex_pt, font_review=args.font_review,
                     structure_review=args.structure_review)
    # Receipt has its own name, never replaces the PDF or an earlier receipt.
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
