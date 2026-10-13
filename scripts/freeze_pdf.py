"""Create a new byte-identical read-only snapshot, never modify the source PDF."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader


def freeze(source, destination, *, tex=None, contest=None, build_receipt=None,
           minimum_font_tex_pt=None, font_review=None, structure_review=None,
           layout_mode='current', page_review=None):
    layout = None
    structure = None
    diagnostics = None
    if layout_mode not in {'current', 'archive'}:
        raise ValueError('Layout mode must be current or archive')
    current_mcm = tex is not None and contest == 'mcm' and layout_mode == 'current'
    if page_review is not None and not current_mcm:
        raise ValueError('Page format review is used with current MCM TeX delivery')
    if (tex is None) != (contest is None):
        raise ValueError("Supply both TeX source and contest for a layout-gated snapshot")
    if build_receipt is not None and tex is None:
        raise ValueError("Build receipts require TeX source and contest")
    if structure_review is not None and tex is None:
        raise ValueError('A structure review requires TeX source and contest')
    if tex is not None:
        from scripts.paper_template import check
        tex_bytes = tex.read_bytes()
        text = tex_bytes.decode('utf-8')
        layout = check(text, contest, layout_mode=layout_mode)
    if current_mcm:
        if minimum_font_tex_pt is not None and (
                type(minimum_font_tex_pt) not in (int, float)
                or not math.isfinite(minimum_font_tex_pt) or minimum_font_tex_pt != 12):
            raise ValueError('Current MCM delivery requires the fixed 12 TeX pt ordinary-text minimum')
        minimum_font_tex_pt = 12
    raw = source.read_bytes()
    if layout is not None:
        if build_receipt is None:
            raise ValueError('Layout-gated freeze requires a canonical --build-receipt')
        build_bytes = Path(build_receipt).read_bytes()
        build = json.loads(build_bytes.decode('utf-8'))
        runtime = json.loads((Path(__file__).resolve().parents[1]/'templates/typesetting-runtime.json').read_text(encoding='utf-8'))
        if current_mcm and build.get('layout_mode') != 'current':
            raise ValueError('Current MCM delivery requires a current-mode canonical build receipt; rebuild the candidate')
        if (build.get('runtime') != runtime or build.get('layout') != layout
                or build.get('tex_sha256') != hashlib.sha256(tex_bytes).hexdigest()
                or build.get('pdf_sha256') != hashlib.sha256(raw).hexdigest()):
            raise ValueError('Canonical build receipt does not match runtime, layout, source or PDF')
        if current_mcm:
            from scripts.paper_template import inspect_typesetting_log
            log_file = source.with_suffix('.log')
            diagnostics = inspect_typesetting_log(log_file, pdf=source)
            recorded = build.get('typesetting_diagnostics')
            if recorded is not None and (
                    not isinstance(recorded, dict)
                    or recorded.get('log_sha256') != diagnostics['log_sha256']):
                raise ValueError('Canonical build receipt does not match the current typesetting log')
            diagnostics['legacy_build_without_diagnostics'] = recorded is None
        layout['tex_sha256'] = hashlib.sha256(tex_bytes).hexdigest()
        layout['runtime_profile'] = runtime['profile']
        layout['build_receipt_sha256'] = hashlib.sha256(build_bytes).hexdigest()
        from scripts.paper_structure import inspect_structure
        structure = inspect_structure(text, structure_review)
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
    delivery_format, pages = None, None
    if current_mcm:
        from scripts.check_pdf import inspect_mcm_delivery_format, inspect_mcm_page_review
        from scripts.paper_template import mcm_identity, mcm_ai_report_expected
        delivery_format = inspect_mcm_delivery_format(source, mcm_identity(text),
                                                      ai_report_expected=mcm_ai_report_expected(text))
        if not delivery_format['passed']:
            raise ValueError('Current MCM PDF format failed: ' + '; '.join(delivery_format['errors']))
        pages = inspect_mcm_page_review(source, page_review)
    digest = hashlib.sha256(raw).hexdigest()
    if (source.read_bytes() != raw or (tex is not None and tex.read_bytes() != tex_bytes)
            or (sizes is not None and sizes['pdf_sha256'] != digest)
            or (diagnostics is not None and hashlib.sha256(log_file.read_bytes()).hexdigest()
                != diagnostics['log_sha256'])
            or (current_mcm and (delivery_format['pdf_sha256'] != digest or pages['pdf_sha256'] != digest))):
        raise ValueError('Source or PDF changed during final delivery inspection; rebuild and review the exact candidate')
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
            **({'layout_mode': layout_mode} if layout is not None else {}),
            **({'current_mcm_format': delivery_format, 'page_format_review': pages} if current_mcm else {}),
            **({'typesetting_diagnostics': diagnostics} if diagnostics is not None else {}),
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
    parser.add_argument('--layout-mode', choices=['current', 'archive'], default='current',
                        help='Current delivery by default; archive preserves an explicitly retained historical profile')
    parser.add_argument('--page-review', type=Path,
                        help='Current MCM requires PDF hash/actor/all-pages/format-check rendering review; defaults to <source>.page-review.json')
    args = parser.parse_args()
    receipt_path = args.destination.with_suffix(".pdf.receipt.json")
    if receipt_path.exists():
        parser.error("Receipt already exists; choose a new destination")
    receipt = freeze(args.source, args.destination, tex=args.tex, contest=args.contest, build_receipt=args.build_receipt,
                     minimum_font_tex_pt=args.minimum_font_tex_pt, font_review=args.font_review,
                     structure_review=args.structure_review, layout_mode=args.layout_mode,
                     page_review=args.page_review)
    # Receipt has its own name, never replaces the PDF or an earlier receipt.
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
