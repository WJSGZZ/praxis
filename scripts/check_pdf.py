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


def inspect_mcm_delivery_format(path, identity, *, ai_report_expected=False):
    """Bounded checks of the actual current MCM PDF, separate from edition rules.

    A4 is the project delivery choice. This does not impose the latest contest's
    page limit on historical editions, classify paragraphs, or inspect raster
    text. All pages still need the exact-PDF-bound rendering review.
    """
    from scripts.contest_rules import extract, evaluate
    errors, page_boxes = [], []
    reader = PdfReader(str(path))
    if reader.is_encrypted or not reader.pages:
        raise ValueError('Current MCM PDF must be readable and nonempty')
    a4 = (210 / 25.4 * 72, 297 / 25.4 * 72)
    tolerance = .08  # bp; permits PDF numeric rounding, not a different page size.
    for number, page in enumerate(reader.pages, 1):
        unit = float(page.get('/UserUnit', 1))
        media = [float(v) * unit for v in page.mediabox]
        crop = [float(v) * unit for v in page.cropbox]
        width, height = media[2] - media[0], media[3] - media[1]
        record = {'page': number, 'media_box_bp': media, 'crop_box_bp': crop,
                  'user_unit': unit, 'rotation': int(page.get('/Rotate', 0)) % 360}
        page_boxes.append(record)
        if (not math.isfinite(unit) or unit <= 0 or record['rotation'] != 0
                or any(not math.isfinite(v) for v in media + crop)
                or abs(width - a4[0]) > tolerance or abs(height - a4[1]) > tolerance
                or abs(media[0]) > tolerance or abs(media[1]) > tolerance
                or any(abs(a - b) > tolerance for a, b in zip(media, crop))):
            errors.append(f'page {number}: current MCM requires an uncropped portrait A4 page box')
    records = extract(path)
    first = ' '.join(records[0]['lines'][:16])
    for label in ('Problem Chosen', 'Team Control Number', 'Summary Sheet'):
        if label.casefold() not in first.casefold():
            errors.append('page 1: missing shared summary identity ' + label)
    for field in ('team', 'edition', 'problem'):
        if not re.search(r'(?<![A-Za-z0-9])' + re.escape(str(identity[field])) + r'(?![A-Za-z0-9])', first):
            errors.append('page 1: summary ' + field + ' differs from the current TeX identity')
    if re.search(r'Team\s*#|\bPage\s*1\s*of\s*[0-9]+\b', first, re.I):
        errors.append('page 1: summary metadata must not duplicate the running page header')
    for number, record in enumerate(records[1:], 2):
        top = ' '.join(record['lines'][:3])
        team = re.search(r'Team\s*#\s*([0-9]{1,12})(?![0-9])', top, re.I)
        # PDF reading order may join "of19" despite correct visible spacing.
        # Read complete numeric tokens; comparing both numbers catches a joined
        # wrong total such as of191 rather than accepting a prefix of it.
        marks = re.search(r'\bPage\s*([0-9]+)\s*of\s*([0-9]+)\b', top, re.I)
        if team is None or team.group(1) != identity['team']:
            errors.append(f'page {number}: running team header differs from the summary identity')
        if marks is None or tuple(map(int, marks.groups())) != (number, len(records)):
            errors.append(f'page {number}: running page identity is missing, unresolved or inconsistent')
    evaluated = evaluate(records, 'mcm')
    facts = evaluated['facts']
    observed_ai = facts['ai_report_heading_on_page'] is not None
    if observed_ai != ai_report_expected:
        errors.append('PDF AI-report presence differs from the checked TeX source')
    if observed_ai and not facts['ai_report_starts_new_page']:
        errors.append('PDF AI-report boundary is mixed or ambiguous')
    if observed_ai:
        from scripts.paper_template import review_mcm_identity_statements
        tail = '\n'.join(record['text'] for record in records[facts['ai_report_heading_on_page']-1:])
        declaration_review = review_mcm_identity_statements(tail, identity['team'])
        errors.extend(declaration_review['errors'])
    else:
        declaration_review = {'statements': [], 'errors': [], 'scope': 'No AI tail present'}
    # evaluate rejects duplicate literal headings; retain that boundary error
    # without importing a latest-edition page-count or dominant-font policy.
    for error in evaluated['errors']:
        if 'AI report' in error or 'AI-report' in error:
            if error not in errors:
                errors.append(error)
    return {'pdf_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'identity': identity, 'page_boxes': page_boxes, 'a4_tolerance_bp': tolerance,
            'author_identity_statements': declaration_review,
            'pdf_boundaries': {key: facts[key] for key in (
                'total_pages', 'counted_pages', 'ai_report_from_page',
                'ai_report_heading_on_page', 'ai_report_starts_new_page')},
            'errors': errors, 'passed': not errors, 'visual_review_required': True,
            'scope': 'Actual page boxes and extractable summary/running-header/AI-boundary identity; no arbitrary TeX expansion, paragraph measurement, raster/outline QA or edition compliance certification'}


MCM_PAGE_REVIEW_CHECKS = (
    'paragraph_indentation', 'figures_tables_fonts', 'clipping_overlap',
    'cross_references', 'summary_headers', 'ai_report_boundary',
)


def inspect_mcm_page_review(path, review_path=None):
    """Require a complete recorded rendering review bound to this exact PDF.

    The actor records actual judgment; this validates completeness and binding,
    never claims that a checklist proves visual or scientific correctness.
    """
    review_path = Path(review_path) if review_path is not None else Path(str(path) + '.page-review.json')
    if not review_path.is_file():
        raise ValueError('Current MCM delivery requires an exact-PDF-bound all-page rendering review (--page-review)')
    review = json.loads(review_path.read_text(encoding='utf-8'))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    count = len(PdfReader(str(path)).pages)
    checks = review.get('format_checks')
    if (review.get('pdf_sha256') != digest
            or not isinstance(review.get('actor'), str) or not review['actor'].strip()
            or not isinstance(review.get('pages'), list)
            or any(type(number) is not int for number in review['pages'])
            or review['pages'] != list(range(1, count + 1))
            or not isinstance(checks, dict)
            or any(checks.get(name) is not True for name in MCM_PAGE_REVIEW_CHECKS)):
        raise ValueError('Current MCM page review must match PDF hash, actor, every actual page and all required format checks')
    return {'review_path': str(review_path.resolve()),
            'review_sha256': hashlib.sha256(review_path.read_bytes()).hexdigest(),
            'pdf_sha256': digest, 'actor': review['actor'], 'pages': review['pages'],
            'format_checks': {name: checks[name] for name in MCM_PAGE_REVIEW_CHECKS},
            'passed': True, 'judgment_accuracy_not_certified': True}


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
