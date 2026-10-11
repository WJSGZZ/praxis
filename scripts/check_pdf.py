"""Read-only generic PDF inspection; visual layout review remains necessary."""
import argparse
import hashlib
import json
import math
import re
from fnmatch import fnmatchcase
from pathlib import Path
from pypdf import PdfReader


def font_record(font):
    """Report the extracted font face and structural embedding, not visual correctness."""
    name=str(font.get('/BaseFont', 'unknown')).lstrip('/')
    name=re.sub(r'^[A-Z]{6}\+', '', name)
    subtype=str(font.get('/Subtype', 'unknown'))
    targets=[font]
    if subtype=='/Type0':
        targets=[f.get_object() for f in font.get('/DescendantFonts', [])]
    embedding=[]
    for target in targets:
        desc=target.get('/FontDescriptor')
        if desc:
            desc=desc.get_object()
            embedding.append(any(k in desc for k in ['/FontFile', '/FontFile2', '/FontFile3']))
        elif target.get('/Subtype')=='/Type3':
            embedding.append(bool(target.get('/CharProcs')))
        else:embedding.append(False)
    return {'face':name, 'subtype':subtype, 'embedding_present':bool(embedding) and all(embedding)}


def summarize_checks(path, claimed_count=None):
    checks=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(checks,list) or not checks:
        raise ValueError('Checks must be a nonempty JSON list')
    names=set()
    for c in checks:
        if (not isinstance(c,dict) or type(c.get('passed')) is not bool
            or not isinstance(c.get('name'),str) or not c['name'].strip()
            or not isinstance(c.get('evidence'),str) or not c['evidence'].strip()):
            raise ValueError('Each check requires a name, boolean result and concrete evidence')
        if c['name'] in names:raise ValueError('Check names must be unique')
        names.add(c['name'])
    total=len(checks);passed=sum(c['passed'] for c in checks)
    errors=[]
    if claimed_count is not None and claimed_count!=total:errors.append('Claimed check count differs from actual evidence')
    if passed!=total:errors.append('Not all recorded checks passed')
    return {'total':total,'passed':passed,'failed':total-passed,'names':[c['name'] for c in checks],'errors':errors,
            'independence_not_assessed':True}


def inspect_font_sizes(path, minimum_tex_pt, review_path=None):
    """Locate every smaller extractable run, without guessing mathematical roles.

    A review can exempt only explicitly identified mathematical text. It is
    bound to the exact PDF and threshold; it is a recorded judgment, not a
    machine certification that the text really is mathematics.
    """
    from scripts.pdf_text import effective_font_runs
    if (type(minimum_tex_pt) not in (int, float) or not math.isfinite(minimum_tex_pt)
            or minimum_tex_pt <= 0):
        raise ValueError('Minimum font size must be a positive finite TeX point value')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    pages = effective_font_runs(path)
    runs = [run for page in pages for run in page['runs']]
    # Five-decimal PDF operators can differ by a few micro-points. This is
    # numerical rounding tolerance, not a half-point typography allowance.
    tolerance = 0.001
    candidates = [r for r in runs if r['size_tex_pt'] < minimum_tex_pt - tolerance]
    approved = {}
    unmapped_runs = [run for page in pages for run in page['unmapped_runs']]
    approved_unmapped = {}
    if review_path is not None:
        review = json.loads(Path(review_path).read_text(encoding='utf-8'))
        if (review.get('pdf_sha256') != digest
                or type(review.get('minimum_font_tex_pt')) not in (int, float)
                or review['minimum_font_tex_pt'] != minimum_tex_pt):
            raise ValueError('Font review does not match this PDF and minimum size')
        entries = review.get('approved_math_runs')
        if not isinstance(entries, list):
            raise ValueError('Font review requires approved_math_runs')
        ids = {r['id'] for r in candidates}
        for entry in entries:
            if (not isinstance(entry, dict) or entry.get('id') not in ids
                    or entry['id'] in approved
                    or entry.get('role') not in {'math_script', 'math_notation'}
                    or not isinstance(entry.get('reason'), str) or not entry['reason'].strip()):
                raise ValueError('Font review needs unique existing mathematical run IDs and concrete reasons')
            approved[entry['id']] = entry
        unknown_entries = review.get('approved_unmapped_math_glyphs', [])
        if not isinstance(unknown_entries, list):
            raise ValueError('Unmapped mathematical glyph review must be a list')
        unknown_ids = {r['id'] for r in unmapped_runs}
        for entry in unknown_entries:
            if (not isinstance(entry, dict) or entry.get('id') not in unknown_ids
                    or entry['id'] in approved_unmapped or entry.get('role') != 'math_notation'
                    or not isinstance(entry.get('reason'), str) or not entry['reason'].strip()):
                raise ValueError('Unmapped review needs unique existing mathematical glyph IDs and concrete reasons')
            approved_unmapped[entry['id']] = entry
    unresolved = [r for r in candidates if r['id'] not in approved]
    errors = []
    if not runs:
        errors.append('No measurable PDF text: font-size compliance cannot be checked')
    if unresolved:
        errors.append(f'{len(unresolved)} smaller text runs require correction or explicit mathematical-role review')
    unmapped = sum(p['unmapped_glyphs'] for p in pages)
    unresolved_unmapped = [r for r in unmapped_runs if r['id'] not in approved_unmapped]
    if unresolved_unmapped:
        errors.append(f'{len(unresolved_unmapped)} unmapped glyphs require visual/font review')
    return {'pdf_sha256': digest, 'minimum_font_tex_pt': minimum_tex_pt,
            'tolerance_tex_pt': tolerance, 'measured_runs': len(runs),
            'smaller_runs': candidates, 'approved_math_runs': list(approved.values()),
            'unresolved_runs': unresolved, 'unmapped_glyphs': unmapped, 'errors': errors,
            'unmapped_runs': unmapped_runs, 'unresolved_unmapped_runs': unresolved_unmapped,
            'approved_unmapped_math_glyphs': list(approved_unmapped.values()),
            'passed': not errors, 'visual_review_required': True,
            'scope': 'Effective vertical em sizes of extractable text after PDF transforms; no automatic prose/math classification or raster/outline-text certification'}


def inspect_pdf(path, max_pages=None, max_bytes=None, forbidden=(), forbidden_fonts=(),
                require_embedded_fonts=False, checks_path=None, claimed_check_count=None,
                minimum_font_tex_pt=None, font_review=None):
    raw = path.read_bytes()
    from scripts.pdf_text import extract_pages
    extracted = extract_pages(path)
    errors, warnings = [], []
    with path.open('rb') as stream:
        doc = PdfReader(stream)
        if doc.is_encrypted:
            raise ValueError('Encrypted PDF must be opened by its owner first')
        if not doc.pages:
            errors.append('Empty PDF')
        if max_pages is not None and len(doc.pages) > max_pages:
            errors.append('Page count exceeds configured limit')
        if max_bytes is not None and len(raw) > max_bytes:
            errors.append('File exceeds configured byte limit')
        metadata = {str(k): str(v) for k,v in (doc.metadata or {}).items()}
        pages=[]
        texts=[]
        fonts={}
        for number,page in enumerate(doc.pages,1):
            def record_text(text, cm, tm, font, size):
                if text.strip() and font is not None:
                    entry=font_record(font);key=(entry['face'],entry['subtype'],entry['embedding_present'])
                    if key not in fonts:fonts[key]={**entry,'pages':[]}
                    if number not in fonts[key]['pages']:fonts[key]['pages'].append(number)
            page.extract_text(visitor_text=record_text)
            text = extracted[number - 1]['text']
            texts.append(text)
            if not text.strip():
                warnings.append(f'Page {number}: no extracted text; image review required')
            pages.append({'page':number,'size_points':[float(page.mediabox.width),float(page.mediabox.height)],'text_characters':len(text),'text_backend':extracted[number - 1]['text_backend']})
        searchable='\n'.join(texts)+json.dumps(metadata, ensure_ascii=False)
        for term in forbidden:
            if term and term.casefold() in searchable.casefold():
                errors.append(f'Configured forbidden term found: {term}')
        for entry in fonts.values():
            if any(fnmatchcase(entry['face'].casefold(),pattern.casefold()) for pattern in forbidden_fonts):
                errors.append('Configured forbidden font face found: '+entry['face'])
            if not entry['embedding_present']:
                message='Extracted font has no embedding program: '+entry['face']
                (errors if require_embedded_fonts else warnings).append(message)
        summary=summarize_checks(checks_path,claimed_check_count) if checks_path else None
        if claimed_check_count is not None and checks_path is None:
            raise ValueError('A claimed check count requires actual checks.json')
        if summary:errors.extend(summary['errors'])
        if font_review is not None and minimum_font_tex_pt is None:
            raise ValueError('A font review requires an explicit minimum font size')
        sizes = inspect_font_sizes(path, minimum_font_tex_pt, font_review) if minimum_font_tex_pt is not None else None
        if sizes:errors.extend(sizes['errors'])
        return {'fonts':list(fonts.values()),'font_inspection_scope':'Fonts identified by text extraction; outlined/raster text and visual face usage require rendering review',
                'font_size_review':sizes,
                'check_summary':summary,'sha256' :hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'total_pages':len(doc.pages),'metadata':metadata,'pages':pages,'errors':errors,'warnings':warnings,'visual_review_required':True}


def margin_report(path, *, scale=0.9, ink_level=200, tolerance_pt=6.0, edge_pt=28.0, gap_fraction=0.3):
    """Render every page and measure the blank space left and right of the ink (text, figures, rules).

    Reports each page's margins in points and flags pages whose two margins differ by more than `tolerance_pt` (a figure, table or code box
    wider than the text block, or a page that is not centred) or whose ink comes within `edge_pt` of a page edge, that have a vertical white gap above `gap_fraction` of the page height, or that are more than 40% empty below the last line (the last page excepted). Pages that are uneven by
    design (a numbered code listing, a hanging reference list) are flagged too: this finds candidates, a person decides."""
    import numpy as np
    import pypdfium2 as pdfium
    document = pdfium.PdfDocument(str(path))
    pages, flagged = [], []
    for number in range(len(document)):
        page = document[number]
        width_pt = float(page.get_width())
        image = np.asarray(page.render(scale=scale).to_pil().convert('L'))
        cols = np.flatnonzero((image < ink_level).any(axis=0))
        if not len(cols):
            pages.append({'page': number + 1, 'blank': True})
            continue
        pixel = width_pt / image.shape[1]
        left, right = float(cols.min() * pixel), float((image.shape[1] - 1 - cols.max()) * pixel)
        record = {'page': number + 1, 'left_pt': round(left, 1), 'right_pt': round(right, 1)}
        rows = np.flatnonzero((image < ink_level).any(axis=1))
        height = image.shape[0]
        gaps = np.diff(rows)
        biggest_gap = float(gaps.max() / height) if len(gaps) else 0.0
        bottom_blank = float((height - 1 - rows.max()) / height)
        record['bottom_blank_fraction'] = round(bottom_blank, 2)
        record['largest_vertical_gap_fraction'] = round(biggest_gap, 2)
        reasons = []
        if biggest_gap > gap_fraction:
            reasons.append('large vertical gap (float or figure left white space)')
        if bottom_blank > 0.4 and number < len(document) - 1:
            reasons.append('page is mostly empty below the last line')
        if abs(left - right) > tolerance_pt:
            reasons.append('margins differ')
        if min(left, right) < edge_pt:
            reasons.append('ink near the page edge')
        if reasons:
            record['flags'] = reasons
            flagged.append(number + 1)
        pages.append(record)
    return {'pages': pages, 'flagged_pages': flagged, 'tolerance_pt': tolerance_pt,
            'note': 'Rendered check of horizontal centring and overflow; it does not judge content, and uneven-by-design pages are flagged too.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('path',type=Path)
    p.add_argument('--max-pages',type=int)
    p.add_argument('--max-bytes',type=int)
    p.add_argument('--forbidden',action='append',default=[])
    p.add_argument('--forbidden-font',action='append',default=[],help='PostScript face name or quoted glob, without subset prefix')
    p.add_argument('--require-embedded-fonts',action='store_true')
    p.add_argument('--minimum-font-tex-pt',type=float,help='Final text size in TeX points; smaller runs require mathematical-role review')
    p.add_argument('--font-review',type=Path,help='PDF-hash-bound JSON review of smaller mathematical runs')
    p.add_argument('--checks',type=Path,help='Actual validator checks.json')
    p.add_argument('--claimed-check-count',type=int)
    p.add_argument('--margins',action='store_true',help='render pages and report left/right margins and uneven or overflowing pages')
    a=p.parse_args()
    if any(v is not None and v<1 for v in [a.max_pages,a.max_bytes]):
        p.error('Limits must be positive')
    r=inspect_pdf(a.path,a.max_pages,a.max_bytes,a.forbidden,a.forbidden_font,
                  a.require_embedded_fonts,a.checks,a.claimed_check_count,
                  a.minimum_font_tex_pt,a.font_review)
    if a.margins:
        r['margins']=margin_report(a.path)
    print(json.dumps(r,ensure_ascii=False,indent=2))
    raise SystemExit(1 if r['errors'] else 0)


if __name__=='__main__':
    main()
