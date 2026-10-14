"""Check a PDF against the hard format rules of a contest: page limits, first page, table of contents, page marks, body font size, margins.

    uv run --locked python -m scripts.contest_rules paper.pdf --contest mcm|cumcm|graduate [--edition 2026] [--forbidden "University of ..."]

The mechanical MCM rules were rechecked against COMAP 2027 instructions on 2026-10-08; CUMCM uses the official 2026 paper-format revision, rechecked on 2026-10-09.
CUMCM edition=None retains the legacy mechanical subset; specify --edition 2026
to check the mandatory AI declaration. Unsupported explicit editions are refused.
Graduate checks require --edition 2026. The default document_kind='report' is
an anonymous abstract/body report; --document-kind submission checks the official
cover followed by the abstract. Neither mode certifies a complete submission.
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
MIN_BODY_PT = 12.0            # 12 TeX pt = 11.95517 PDF bp, extracted at 0.1 bp precision
MIN_MARGIN_PT = 2.5 / 2.54 * 72 - 3
GRADUATE_AI_SOURCE = 'https://cpipc.acge.org.cn/sysFile/downFile.do?fileId=4fc024f7a1504abb87fc056440c64a28'


def _supported_2026_edition(edition, contest, *, allow_unspecified=False):
    if edition is None and allow_unspecified:
        return None
    # bool is an int subclass, and a float such as 2026.0 is not an edition.
    if type(edition) is int:
        edition = str(edition)
    if not isinstance(edition, str) or edition != '2026':
        raise ValueError(f'{contest} checks require exact supported edition 2026; unknown editions do not inherit its rules')
    return edition


def _chinese_heading_positions(records, title):
    """Recognize a literal heading, including whitespace/line-split extraction.

    Prose containing the title, punctuation and contents entries ending with a
    page number are not headings. This is text structure, not semantic review.
    """
    target = title.upper()
    found = []
    seen_ends = set()
    for page, record in enumerate(records):
        lines = record['lines']
        for start in range(len(lines)):
            for end in range(start + 1, min(len(lines), start + len(title) + 2) + 1):
                value = re.sub(r'\s+', '', ''.join(lines[start:end])).upper()
                value = re.sub(r'^(?:[0-9]+(?:\.[0-9]+)*[.、]?|[一二三四五六七八九十百]+[、.])', '', value)
                if value == target:
                    if (page, end) not in seen_ends:
                        found.append((page, start, end))
                        seen_ends.add((page, end))
                    break
                if not target.startswith(value):
                    break
    return found


def _cumcm_ai_declaration(records, appendix_heading):
    """Check the 2026 heading boundary, never the truth of an AI-use claim."""
    toc_pages = {p for p, _, _ in _chinese_heading_positions(records, '目录')}
    def in_body(position):
        page, line, _ = position
        return (page > 0 and page not in toc_pages and
                (appendix_heading is None or (page, line) < appendix_heading))
    declarations = [p for p in _chinese_heading_positions(records, 'AI工具使用声明') if in_body(p)]
    references = [p for p in _chinese_heading_positions(records, '参考文献') if in_body(p)]
    errors = []
    if not declarations:
        errors.append('CUMCM 2026 requires one AI工具使用声明 in the body before references, whether AI was used or not')
    elif len(declarations) > 1:
        errors.append('CUMCM 2026 requires exactly one AI工具使用声明; multiple body declarations found')
    if references and any((p, line) > references[0][:2] for p, line, _ in declarations):
        errors.append('CUMCM 2026 AI工具使用声明 must precede the references')
    facts = dict(ai_declaration_policy_edition='2026',
                 ai_declaration_count=len(declarations),
                 ai_declaration_pages=[p + 1 for p, _, _ in declarations],
                 ai_use_truth_verified=False, ai_details_attachment_checked=False)
    return errors, facts


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


def _first_content_line(lines, *, mcm=False):
    """Skip only recognized running headers, never arbitrary preceding prose."""
    index = 0
    header = re.compile(r'(?:Team\s*(?:#|Control Number)?\s*\d{1,12}'
                        r'(?:\s+Page\s*\d+\s+of\s*\d+)?|Page\s*\d+\s+of\s*\d+)', re.I)
    while index < len(lines) and (not lines[index].strip() or
                                 (mcm and header.fullmatch(lines[index].strip()))):
        index += 1
    return index


def evaluate(records, contest, *, margins=None, forbidden=(), edition=None, document_kind='report'):
    """Apply the rules to page records; returns errors (rule broken), warnings (probably broken or not checkable) and facts."""
    errors, warnings, facts = [], [], {}
    n = len(records)
    if document_kind not in {'report', 'submission'}:
        raise ValueError('document_kind must be report or submission')
    if contest != 'graduate' and document_kind != 'report':
        raise ValueError('document_kind=submission is supported only for graduate')
    if contest == 'cumcm':
        edition = _supported_2026_edition(edition, contest, allow_unspecified=True)
    elif contest == 'graduate':
        edition = _supported_2026_edition(edition, contest)
    # The official graduate submission cover must contain team identity. The
    # anonymity boundary begins at the following abstract page.
    anonymous_records = records[1:] if contest == 'graduate' and document_kind == 'submission' else records
    full = '\n'.join(r['text'] for r in anonymous_records)
    for item in forbidden:
        if item and item.lower() in full.lower():
            errors.append(f'identifying text found: {item!r}')
    if contest == 'mcm':
        # a heading is a line that is only the title (a contents entry ends with a page number or dots)
        ai_headings = [(i, j) for i, r in enumerate(records) for j, line in enumerate(r['lines'])
                       if re.fullmatch(r'(?:\d+\s+)?Report on Use of AI(?: Tools)?\s*', line, re.I)]
        observed = ai_headings[0][0] if ai_headings else None
        isolated = (len(ai_headings) == 1 and ai_headings[0][1] ==
                    _first_content_line(records[observed]['lines'], mcm=True))
        ai_page = observed if isolated else None
        if len(ai_headings) > 1:
            errors.append('multiple AI report headings: cannot identify an unambiguous excluded section')
        elif ai_headings and not isolated:
            errors.append('AI report must start on a separate page; preceding solution/reference content cannot be excluded')
        counted = ai_page if ai_page is not None else n
        facts.update(total_pages=n, counted_pages=counted, ai_report_from_page=None if ai_page is None else ai_page + 1,
                     ai_report_heading_on_page=None if observed is None else observed + 1,
                     ai_report_starts_new_page=isolated if ai_headings else None)
        if counted > MCM_PAGE_LIMIT:
            errors.append(f'{counted} pages count toward the 25-page limit (summary sheet, text, contents, references, appendices, code)')
        first = records[0]['text'] if records else ''
        if not re.search(r'summary', first, re.I):
            warnings.append('page 1 does not mention "Summary"; the Summary Sheet must be the first page')
        numbers = set()
        for i, r in enumerate(records[:counted]):
            top = ' '.join(r['lines'][:8] if i == 0 else r['lines'][:3])
            m = re.search(r'Team\s*(?:#|Control Number)?\s*(\d{4,8})', top)
            summary_metadata = i == 0 and bool(re.search(r'Problem Chosen', top)) and bool(re.search(r'Summary Sheet', top))
            if not m and summary_metadata:
                # PDF reading order may interleave the three independent columns.
                m = re.search(r'(?<!\d)(\d{7})(?!\d)', top)
            if not m:
                warnings.append(f'page {i + 1}: no team control number found at the top')
                continue
            numbers.add(m.group(1))
            if i == 0 and summary_metadata:
                facts['summary_page_marks'] = 'official-style metadata; running page header omitted'
                if edition is not None and not re.search(r'\b' + re.escape(str(edition)) + r'\b', top):
                    errors.append(f'summary year does not match requested edition {edition}')
            elif not re.search(r'Page\s*%d\b' % (i + 1), top):
                warnings.append(f'page {i + 1}: page number not found at the top')
        if len(numbers) > 1:
            errors.append(f'different team numbers on different pages: {sorted(numbers)}')
        facts['team_number'] = sorted(numbers)[0] if numbers else None
        facts['has_table_of_contents'] = any(re.fullmatch(r'(Table of )?Contents', line.strip(), re.I) for r in records[:3] for line in r['lines'][:6])
        if not ai_headings:
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
        appendix_heading = next(((i, j) for i, r in enumerate(records) if i > 0 for j, line in enumerate(r['lines'])
                                 if re.match(r'\s*附\s*录', line) and len(line) <= 30 and not re.search(r'[。，；,.;]', line)), None)
        appendix = appendix_heading[0] if appendix_heading else None
        isolated = (appendix_heading is not None and appendix_heading[1] ==
                    _first_content_line(records[appendix]['lines']))
        # A shared page still contains body text: count it, even though the
        # appendix itself has no page limit. Continuous appendices are allowed.
        before_appendix = (appendix + (not isolated)) if appendix is not None else n
        body = max(0, before_appendix - 1)  # Abstract is a separate dedicated page.
        facts.update(total_pages=n, body_pages=body, abstract_pages=1 if n else 0,
                     pages_before_appendix=before_appendix,
                     body_page_limit=CUMCM_BODY_PAGES, format_edition=edition,
                     format_rules_source_edition='2026',
                     appendix_from_page=None if appendix is None else appendix + 1,
                     appendix_starts_new_page=isolated if appendix is not None else None)
        if appendix is not None and not isolated:
            warnings.append(f'page {appendix + 1} contains body content before the appendix; it counts toward the body limit')
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
        if edition == '2026':
            ai_errors, ai_facts = _cumcm_ai_declaration(
                records, appendix_heading[:2] if appendix_heading else None)
            errors.extend(ai_errors)
            facts.update(ai_facts)
            warnings.append('AI declaration heading/order only: actual AI use, statement truth, manual verification and supporting AI工具使用详情.pdf are not checked by this PDF checker')
        else:
            facts.update(ai_declaration_policy_edition=None,
                         ai_use_truth_verified=False, ai_details_attachment_checked=False)
            warnings.append('CUMCM edition is unspecified: legacy mechanical subset only (sourced from 2026); this pass does not certify the 2026 AI declaration policy. Use --edition 2026 for that gate')
    elif contest == 'graduate':
        report_records = records[1:] if document_kind == 'submission' else records
        if document_kind == 'submission':
            cover = re.sub(r'\s+', '', records[0]['text']) if records else ''
            if not all(label in cover for label in ('学校', '参赛队号', '队员姓名')):
                errors.append('graduate 2026 submission must retain the official cover as PDF page 1 (学校, 参赛队号, 队员姓名); abstract starts on PDF page 2')
            warnings.append('Submission cover labels only: the four original logos, official template layout, filled identity fields, filename and actual upload are not certified mechanically')
        else:
            warnings.append('document_kind=report checks the anonymous abstract/body report only; it does not certify the complete 2026 submission PDF, whose official cover is required. Use --document-kind submission')
        first = report_records[0]['text'] if report_records else ''
        if not re.search(r'摘\s*要', first):
            errors.append(f'PDF page {2 if document_kind == "submission" else 1} must start the abstract with the paper title')
        if not any('关键词' in r['text'] for r in report_records[:2]):
            warnings.append('keywords not found in the first two abstract/report pages; the 2026 opening notice limits the abstract to two pages, but this text statistic does not establish its full boundary')
        for i, r in enumerate(report_records):
            if not r['lines'] or not re.fullmatch(r'\s*%d\s*' % (i + 1), r['lines'][-1]):
                physical = i + (2 if document_kind == 'submission' else 1)
                warnings.append(f'PDF page {physical}: bottom page-number text is not {i + 1}; check continuous Arabic numbers starting at the abstract')
        sizes = [r['body_size'] for r in report_records[1:] if r.get('body_size')]
        size = collections.Counter(sizes).most_common(1)[0][0] if sizes else None
        if size is not None and abs(size - 12.0) > .35:
            warnings.append(f'dominant text is about {size} pt; verify Chinese prose against 小四号 (12 pt). This statistic also includes equations and cannot certify Chinese-only typography.')
        facts.update(total_pages=n, format_edition=edition, body_font_pt=size,
                     page_limit=None, document_kind=document_kind,
                     abstract_from_pdf_page=2 if document_kind == 'submission' else 1,
                     anonymity_from_pdf_page=2 if document_kind == 'submission' else 1,
                     ai_policy_status='confirmed', ai_policy_version='2026-09-16',
                     ai_policy_source=GRADUATE_AI_SOURCE,
                     ai_use_compliance_checked=False)
        warnings.append('The 2026-09-16 AI policy is confirmed; actual tool/version/source attribution, data-analysis annotations, program comments and problem-specific input/output records are not certified by this format checker')
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
    parser.add_argument('--document-kind', choices=['report', 'submission'], default='report',
                        help='graduate only: anonymous report (compatibility default) or complete submission with the official cover')
    parser.add_argument('--forbidden', action='append', default=[], help='text that must not appear (school, names, region)')
    args = parser.parse_args()
    margins = None
    if args.contest == 'cumcm':
        from scripts.check_pdf import margin_report
        margins = margin_report(args.path)
    if args.contest == 'graduate' and args.edition != '2026':
        parser.error('graduate checks require --edition 2026; unknown editions do not inherit rules')
    if args.contest == 'cumcm' and args.edition not in {None, '2026'}:
        parser.error('cumcm checks support only --edition 2026; unknown editions do not inherit rules')
    if args.contest != 'graduate' and args.document_kind != 'report':
        parser.error('--document-kind submission is supported only for graduate')
    report = evaluate(extract(args.path), args.contest, margins=margins, forbidden=args.forbidden,
                      edition=args.edition, document_kind=args.document_kind)
    print(json.dumps(report, ensure_ascii=True, indent=1))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
