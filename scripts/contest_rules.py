"""Check a PDF against the hard format rules of a contest: page limits, first page, table of contents, page marks, body font size, margins.

    uv run --locked python -m scripts.contest_rules paper.pdf --contest mcm|cumcm [--forbidden "University of ..."]

The rules are those published for MCM/ICM 2026 (COMAP instructions) and in the CUMCM paper-format specification (2019, 2021, 2023 revisions).
They change: compare with the current official documents before relying on a pass. A pass means the PDF meets these mechanical rules;
it says nothing about the content."""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

MCM_PAGE_LIMIT = 25
CUMCM_BODY_PAGES = 20
MIN_BODY_PT = 11.5            # 12 pt LaTeX body text measures about 11.96
MIN_MARGIN_PT = 2.5 / 2.54 * 72 - 3


def extract(path):
    """One record per page: text, its lines, and the most common font size by character count."""
    records = []
    for page in PdfReader(str(path)).pages:
        sizes = collections.Counter()

        def visitor(text, cm, tm, font_dict, font_size):
            if text.strip():
                sizes[round(float(font_size) * abs(float(tm[0]) if tm[0] else 1.0) * abs(float(cm[0]) if cm[0] else 1.0), 1)] += len(text.strip())
        text = page.extract_text(visitor_text=visitor) or ''
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        records.append(dict(text=text, lines=lines, body_size=sizes.most_common(1)[0][0] if sizes else None))
    return records


def evaluate(records, contest, *, margins=None, forbidden=()):
    """Apply the rules to page records; returns errors (rule broken), warnings (probably broken or not checkable) and facts."""
    errors, warnings, facts = [], [], {}
    n = len(records)
    full = '\n'.join(r['text'] for r in records)
    for item in forbidden:
        if item and item.lower() in full.lower():
            errors.append(f'identifying text found: {item!r}')
    if contest == 'mcm':
        # a heading is a line that is only the title (a contents entry ends with a page number or dots)
        ai_page = next((i for i, r in enumerate(records) if any(re.fullmatch(r'(?:\d+\s+)?Report on Use of AI\s*', line, re.I) for line in r['lines'])), None)
        counted = ai_page if ai_page is not None else n
        facts.update(total_pages=n, counted_pages=counted, ai_report_from_page=None if ai_page is None else ai_page + 1)
        if counted > MCM_PAGE_LIMIT:
            errors.append(f'{counted} pages count toward the 25-page limit (summary sheet, text, contents, references, appendices, code)')
        first = records[0]['text'] if records else ''
        if not re.search(r'summary', first, re.I):
            warnings.append('page 1 does not mention "Summary"; the Summary Sheet must be the first page')
        numbers = set()
        for i, r in enumerate(records[:counted]):
            m = re.search(r'Team\s*(?:#|Control Number)?\s*(\d{4,8})', ' '.join(r['lines'][:3]))
            if not m:
                warnings.append(f'page {i + 1}: no team control number found at the top')
                continue
            numbers.add(m.group(1))
            if not re.search(r'Page\s*%d\b' % (i + 1), ' '.join(r['lines'][:3])):
                warnings.append(f'page {i + 1}: page number not found at the top')
        if len(numbers) > 1:
            errors.append(f'different team numbers on different pages: {sorted(numbers)}')
        facts['team_number'] = sorted(numbers)[0] if numbers else None
        facts['has_table_of_contents'] = any(re.fullmatch(r'(Table of )?Contents', line.strip(), re.I) for r in records[:3] for line in r['lines'][:6])
        if ai_page is None:
            warnings.append('no "Report on Use of AI" section: required only if AI tools were used')
        sizes = [r['body_size'] for r in records[:counted] if r['body_size']]
        facts['body_font_pt'] = collections.Counter(sizes).most_common(1)[0][0] if sizes else None
        if facts['body_font_pt'] and facts['body_font_pt'] < MIN_BODY_PT:
            errors.append(f'body text is about {facts["body_font_pt"]} pt; the minimum is 12 pt')
    elif contest == 'cumcm':
        first = records[0]['text'] if records else ''
        if not (re.search(r'摘\s*要', first) and '关键词' in first):
            errors.append('page 1 must be the abstract page with the title, abstract and keywords')
        if n > 1 and '关键词' in records[1]['text'] and re.search(r'摘\s*要', records[1]['text']):
            errors.append('the abstract continues on page 2; it must fit on one page')
        toc = [i + 1 for i, r in enumerate(records[:4]) if re.match(r'\s*目\s*录', r['text'])]
        if toc:
            errors.append(f'a table of contents on page {toc}; the specification says not to include one')
        appendix = next((i for i, r in enumerate(records) if re.search(r'^\s*附\s*录', r['text'], re.M) and i > 0), None)
        body = appendix if appendix is not None else n
        facts.update(total_pages=n, body_pages=body, appendix_from_page=None if appendix is None else appendix + 1)
        if body > CUMCM_BODY_PAGES:
            warnings.append(f'the body (before the appendix) has {body} pages; the specification asks for about 20 at most')
        if appendix is None:
            errors.append('no appendix found: the specification requires the file list and the complete runnable source code')
        else:
            tail = '\n'.join(r['text'] for r in records[appendix:])
            if not re.search(r'源程序|源代码|没有用到程序|没有用到源程序', tail):
                errors.append('the appendix has no source code and no statement that no program was used')
            if not re.search(r'支撑材料|文件列表|没有支撑材料', tail):
                errors.append('the appendix has no list of supporting files (or the statement that there are none)')
        for i, r in enumerate(records):
            last = r['lines'][-1] if r['lines'] else ''
            if not re.fullmatch(r'\s*-?\s*%d\s*-?\s*' % (i + 1), last):
                warnings.append(f'page {i + 1}: the last line is not the page number {i + 1} (page numbers run from the abstract page, bottom centre)')
                break
        if margins:
            small = [p['page'] for p in margins['pages'] if not p.get('blank') and min(p['left_pt'], p['right_pt']) < MIN_MARGIN_PT]
            if small:
                errors.append(f'ink closer than 2.5 cm to the side edge on pages {small[:10]}')
        sizes = [r['body_size'] for r in records[:body] if r['body_size']]
        facts['body_font_pt'] = collections.Counter(sizes).most_common(1)[0][0] if sizes else None
    else:
        raise ValueError('contest must be mcm or cumcm')
    return dict(contest=contest, errors=errors, warnings=warnings, facts=facts, passed=not errors,
                note='Mechanical rules only; compare with the current official documents. Font sizes and the page number line are read from the PDF text and can be misjudged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--contest', required=True, choices=['mcm', 'cumcm'])
    parser.add_argument('--forbidden', action='append', default=[], help='text that must not appear (school, names, region)')
    args = parser.parse_args()
    margins = None
    if args.contest == 'cumcm':
        from scripts.check_pdf import margin_report
        margins = margin_report(args.path)
    report = evaluate(extract(args.path), args.contest, margins=margins, forbidden=args.forbidden)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
