"""Check a PDF against the hard format rules of a contest: page limits, first page, table of contents, page marks, body font size, margins.

    uv run --locked python -m scripts.contest_rules paper.pdf --contest mcm|cumcm|graduate [--edition 2026] [--forbidden "University of ..."]

The mechanical MCM rules were rechecked against COMAP 2027 instructions on 2026-10-08; CUMCM uses the official 2026 paper-format revision, rechecked on 2026-10-09.
Graduate checks are a deliberately limited subset of the official 2026 format, and require --edition 2026.
They change: compare with the current official documents before relying on a pass. A pass means the PDF meets these mechanical rules;
it says nothing about the content."""
import argparse
import collections
import json
import re
import sys
from pathlib import Path


MCM_PAGE_LIMIT = 25
CUMCM_BODY_PAGES = 30
MIN_BODY_PT = 11.5            # 12 pt LaTeX body text measures about 11.96
MIN_MARGIN_PT = 2.5 / 2.54 * 72 - 3


def extract(path):
    """One record per page: text, its lines, and the most common font size by character count."""
    from scripts.pdf_text import extract_pages
    records = extract_pages(path)
    for record in records:
        record['lines'] = [x.strip() for x in record['text'].splitlines() if x.strip()]
    return records


def unreferenced_floats(records):
    """Flag numbered floats with only one mention (their caption).

    A reference can start a paragraph, so removing every line that starts with
    'Figure 1' would also remove valid prose. This is a text heuristic, not a
    semantic check that the additional mention explains the float's claim.
    """
    norm = lambda word: word.lower() if word.isascii() else word
    caption = re.compile(r'^\s*(图|表|Figure|Table)\s*(\d+)\s*[:.：]?', re.I | re.M)
    mention = re.compile(r'(图|表|Figure|Table)\s*(\d+)', re.I)
    captions, mentions = set(), {}
    for r in records:
        text = r['text']
        captions |= {(norm(m.group(1)), m.group(2)) for m in caption.finditer(text)}
        for m in mention.finditer(re.sub(r'\s+', ' ', text)):
            key = (norm(m.group(1)), m.group(2))
            mentions[key] = mentions.get(key, 0) + 1
    return sorted(f'{k[0]} {k[1]}' for k in captions if mentions.get(k, 0) < 2)


def evaluate(records, contest, *, margins=None, forbidden=(), edition=None):
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
        # an appendix heading is a short line that starts with 附录 and has no sentence punctuation; a line that merely begins with the word is body text
        appendix = next((i for i, r in enumerate(records) if i > 0 and any(re.match(r'\s*附\s*录', line) and len(line) <= 30 and not re.search(r'[。，；,.;]', line) for line in r['lines'])), None)
        before_appendix = appendix if appendix is not None else n
        body = max(0, before_appendix - 1)  # Abstract is a separate dedicated page.
        facts.update(total_pages=n, body_pages=body, abstract_pages=1 if n else 0,
                     pages_before_appendix=before_appendix,
                     body_page_limit=CUMCM_BODY_PAGES, format_edition='2026',
                     appendix_from_page=None if appendix is None else appendix + 1)
        if body > CUMCM_BODY_PAGES:
            errors.append(f'the body has {body} pages; the 2026 specification permits at most 30, excluding the abstract and appendix')
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
        sizes = [r['body_size'] for r in records[1:before_appendix] if r['body_size']]
        facts['body_font_pt'] = collections.Counter(sizes).most_common(1)[0][0] if sizes else None
    elif contest == 'graduate':
        if edition != '2026':
            raise ValueError('graduate format checks require the exact supported edition 2026')
        first = records[0]['text'] if records else ''
        if not re.search(r'摘\s*要', first):
            errors.append('page 1 must start the abstract with the paper title')
        if not any('关键词' in r['text'] for r in records[:2]):
            warnings.append('keywords not found in the first two pages; check the abstract (usually at most two pages, a guideline rather than a hard limit)')
        for i, r in enumerate(records):
            if not r['lines'] or not re.fullmatch(r'\s*%d\s*' % (i + 1), r['lines'][-1]):
                warnings.append(f'page {i + 1}: bottom page-number text is not {i + 1}; check continuous Arabic numbers starting at the abstract')
        sizes = [r['body_size'] for r in records[1:] if r.get('body_size')]
        size = collections.Counter(sizes).most_common(1)[0][0] if sizes else None
        if size is not None and abs(size - 12.0) > .35:
            warnings.append(f'dominant text is about {size} pt; verify Chinese prose against 小四号 (12 pt). This statistic also includes equations and cannot certify Chinese-only typography.')
        facts.update(total_pages=n, format_edition=edition, body_font_pt=size,
                     page_limit=None, ai_policy_status='unconfirmed')
        warnings.append('Not checked mechanically: 宋体/黑体 font families, title/heading size and centering, single spacing, absence of running headers, complete anonymity and citation format; review actual PDF and official standard document.')
    else:
        raise ValueError('contest must be mcm, cumcm or graduate')
    loose = unreferenced_floats(records)
    if loose:
        warnings.append('figures or tables never referred to in the text: ' + ', '.join(loose))
    return dict(contest=contest, errors=errors, warnings=warnings, facts=facts, passed=not errors,
                note='Mechanical rules only; compare with the current official documents. Font sizes and the page number line are read from the PDF text and can be misjudged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--contest', required=True, choices=['mcm', 'cumcm', 'graduate'])
    parser.add_argument('--edition', help='required for graduate; currently only 2026 is checked')
    parser.add_argument('--forbidden', action='append', default=[], help='text that must not appear (school, names, region)')
    args = parser.parse_args()
    margins = None
    if args.contest == 'cumcm':
        from scripts.check_pdf import margin_report
        margins = margin_report(args.path)
    if args.contest == 'graduate' and args.edition != '2026':
        parser.error('graduate checks require --edition 2026; unknown editions do not inherit rules')
    report = evaluate(extract(args.path), args.contest, margins=margins, forbidden=args.forbidden, edition=args.edition)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
