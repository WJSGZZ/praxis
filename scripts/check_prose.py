"""Warning-only prose diagnostics from actual PDF text plus literal TeX structure.

No PDF text is synthesized from TeX. Mapping failures make body statistics
unavailable rather than silently counting exempt sections as body text.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import unicodedata

from scripts.manuscript import (
    diagnostic, document, plain_text, quantities, sections, significant_digits,
    strip_comments, warning,
)

# Exactly the lexical proxy and minimum length used by calibration/metrics.py.
NEG = re.compile(r"\b(not|cannot|can't|don't|doesn't|isn't|aren't|no|neither|nor|never|without|unless|only)\b", re.I)
EXEMPT_BODY = {'summary', 'memo', 'limitations', 'references', 'appendix', 'ai', 'reproducibility'}
EXEMPT_LEAK = {'appendix', 'reproducibility', 'references', 'ai'}
EXEMPT_PRECISION = {'appendix', 'reproducibility', 'references', 'ai'}
RUN_ID = re.compile(r'(?<![\w])20[0-9]{6}T[0-9]{6}-[0-9a-f]{8,}(?![\w])', re.I)
HEX_ID = re.compile(r'(?<![\w])[0-9a-f]{12,}(?![\w])', re.I)
LOCAL_PATH = re.compile(r'(?<![\w:/])(?:/Users/[^\s<>"\u201c\u201d]+|[A-Za-z]:[\\/][^\s<>"\u201c\u201d]+)')
PUBLIC_URL = re.compile(r'https?://[^\s<>]+', re.I)


def _normal(text):
    return ''.join(char for char in unicodedata.normalize('NFKC', text).casefold() if char.isalnum())


def _heading_matches(title, pages):
    wanted, matches = _normal(title), set()
    allowed_titles = {'memo', 'memorandum'} if wanted in {'memo', 'memorandum'} else {wanted}
    if not wanted:
        return []
    for page_number, page in enumerate(pages, 1):
        lines = page.splitlines(keepends=True)
        offsets, cursor = [], 0
        for line in lines:
            offsets.append(cursor)
            cursor += len(line)
        for index in range(len(lines)):
            for width in range(1, min(3, len(lines) - index) + 1):
                if width > 1 and re.fullmatch(r'\s*[0-9.()]+\s*', lines[index]):
                    continue
                candidate = ' '.join(lines[index:index + width]).strip()
                # Keep appendix letters in titles; remove only literal section numbers.
                candidate = re.sub(r'^\s*[0-9]+(?:\.[0-9]+)*[.)]?\s+', '', candidate)
                unlettered = re.sub(r'^(?:Appendix\s+)?[A-Z](?:\.[0-9]+)*[.)]?\s+', '', candidate)
                if _normal(candidate) in allowed_titles or _normal(unlettered) in allowed_titles:
                    matches.add((page_number, offsets[index]))
    return sorted(matches)


def _map_pdf(parts, pages):
    """Exact normalized heading-line mapping, with explicit ambiguity rejection."""
    mapped, unresolved = [], []
    for part in parts:
        if not part['title']:
            if part['kind'] in EXEMPT_BODY and plain_text(part['text'][part['content_start'] - part['start']:]).strip():
                unresolved.append({'title': '', 'kind': part['kind'],
                                   'reason': 'A non-rendering section marker has following content but no literal PDF heading anchor'})
            continue
        matches = _heading_matches(part['title'], pages)
        if len(matches) != 1:
            unresolved.append({'title': part['title'], 'kind': part['kind'],
                               'candidate_locations': [{'page': p, 'offset': o} for p, o in matches]})
        else:
            mapped.append({**part, 'pdf_location': matches[0]})
    if unresolved:
        return [], unresolved, 'uncertain'
    positions = [part['pdf_location'] for part in mapped]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        return [], [{'reason': 'PDF headings are not uniquely ordered as literal TeX headings'}], 'uncertain'
    if not mapped:
        return [{'page': index, 'text': page, 'offset': 0, 'kind': 'body', 'title': ''}
                for index, page in enumerate(pages, 1)], [], 'no_literal_headings'
    page_starts, cursor = [], 0
    for page in pages:
        page_starts.append(cursor)
        cursor += len(page) + 1
    # Keep pages separate so every reported candidate retains a real page location.
    segments = []
    for index, part in enumerate(mapped):
        first_page, first_offset = part['pdf_location']
        last_page, last_offset = (mapped[index + 1]['pdf_location'] if index + 1 < len(mapped)
                                  else (len(pages), len(pages[-1])))
        for page_number in range(first_page, last_page + 1):
            start = first_offset if page_number == first_page else 0
            end = last_offset if page_number == last_page else len(pages[page_number - 1])
            if start < end:
                segments.append({'page': page_number, 'offset': start,
                    'text': pages[page_number - 1][start:end], 'kind': part['kind'], 'title': part['title']})
    return segments, [], 'mapped_literal_headings'


def _mask_spans(tex, spans):
    chars = list(tex)
    for node in spans:
        for index in range(node.pos, min(len(chars), node.pos + node.len)):
            if chars[index] not in '\n\r':
                chars[index] = ' '
    return ''.join(chars)


def inspect(tex_text, pdf_pages, *, problem_year=None, allow_anachronism=False) -> dict:
    parsed = document(tex_text)
    if not isinstance(pdf_pages, (list, tuple)) or any(not isinstance(p, str) for p in pdf_pages):
        raise TypeError('pdf_pages must be a list of actual extracted PDF page strings')
    if problem_year is not None and (type(problem_year) is not int or not 1900 <= problem_year <= 2200):
        raise ValueError('problem_year must be an integer in 1900..2200')
    if type(allow_anachronism) is not bool:
        raise TypeError('allow_anachronism must be a boolean')
    output = diagnostic('prose')
    parts = sections(tex_text)
    segments, unresolved, mapping_status = _map_pdf(parts, pdf_pages) if pdf_pages else ([], [], 'no_pdf_pages')
    if not any(page.strip() for page in pdf_pages):
        mapping_status = 'no_extractable_text'
        segments = []
        output['warnings'].append(warning('prose_pdf_text_missing',
            'PDF pages have no extracted text; no body language statistic is available.'))
    if unresolved:
        output['warnings'].append(warning('prose_section_mapping_uncertain',
            'Literal TeX headings could not be uniquely mapped to actual PDF heading lines; body statistics and exemption-sensitive PDF scans are unavailable.'))
    hidden = [item for item in parsed['unexpanded'] if item['kind'] != 'macro_definition']
    if hidden:
        output['warnings'].append(warning('prose_unexpanded_source',
            'External inputs or unevaluated conditions can hide section boundaries; mapped statistics cover literal source only.'))
    body_segments = [s for s in segments if s['kind'] not in EXEMPT_BODY]
    body_text = ' '.join(s['text'] for s in body_segments)
    sents = [s for s in re.split(r'(?<=[.!?])\s+', re.sub(r'\s+', ' ', body_text)) if len(s.split()) >= 6]
    negative = sum(bool(NEG.search(sentence)) for sentence in sents)
    ratio = negative / len(sents) if sents else None
    output['metrics'].update(pdf_pages=len(pdf_pages), text_source='actual_pdf_page_text',
        mapping_status=mapping_status, unresolved_sections=unresolved,
        mapped_sections=[{'title': s['title'], 'kind': s['kind'], 'page': s['page']} for s in segments],
        body_sentences=len(sents) if segments else None,
        negative_sentences=negative if segments else None, neg_ratio=round(ratio, 3) if ratio is not None else None,
        neg_ratio_threshold=0.16, neg_ratio_threshold_status='calibration_sample',
        neg_ratio_calibration_range=[0.04, 0.16], minimum_sentence_words=6,
        problem_year=problem_year, allow_anachronism=allow_anachronism)
    if ratio is not None and ratio > 0.16:
        output['warnings'].append(warning('prose_negation_ratio',
            f'{negative}/{len(sents)} body sentences contain a calibration negation cue ({ratio:.3f} > 0.16); this is a lexical review prompt.'))
    precision, leaks = [], []
    for segment in segments:
        text = segment['text']
        if segment['kind'] not in EXEMPT_PRECISION:
            for quantity in quantities(text):
                # This diagnostic targets money, ratios and discrete counts;
                # physical measurement precision needs domain-specific judgment.
                unit = quantity['unit'].lower()
                eligible = re.search(r'[$€£¥%]|usd|eur|gbp|cny|rmb|kes|dollar|euro|pound|yuan|percent|'
                                     r'million|billion|thousand|count|countr|people|person|household|boma|unit|'
                                     r'case|path|sample|observation|trial|run|polic|scenario|元|人|户|个', unit)
                if eligible and significant_digits(quantity['literal']) >= 6:
                    candidate = {'text': quantity['text'], 'significant_digits': significant_digits(quantity['literal']),
                                 'page': segment['page'], 'offset': segment['offset'] + quantity['start']}
                    precision.append(candidate)
                    output['warnings'].append(warning('prose_precision_candidate',
                        f'{quantity["text"]} has {candidate["significant_digits"]} significant digits; review displayed precision.',
                        page=candidate['page'], offset=candidate['offset'], section=segment['title']))
        if segment['kind'] not in EXEMPT_LEAK:
            # Public URLs (including fixed Git commit URLs) remain ordinary
            # published reproducibility links; never flag their hash fragments.
            public_spans = [match.span() for match in PUBLIC_URL.finditer(text)]
            seen = set()
            for code, pattern in (('run_identifier', RUN_ID), ('hex_identifier', HEX_ID), ('local_path', LOCAL_PATH)):
                for match in pattern.finditer(text):
                    if any(start <= match.start() < end for start, end in public_spans):
                        continue
                    if any(start <= match.start() and match.end() <= end for start, end in seen):
                        continue
                    seen.add(match.span())
                    candidate = {'kind': code, 'text': match.group(), 'page': segment['page'],
                                 'offset': segment['offset'] + match.start()}
                    leaks.append(candidate)
                    output['warnings'].append(warning('prose_process_leak',
                        f'Possible process detail ({code}): {match.group()}',
                        page=candidate['page'], offset=candidate['offset'], section=segment['title']))
    source = _mask_spans(tex_text, parsed['comments'] + parsed['math'] + parsed['ignored'])
    # Escaped underscores are ordinary text; the warning is a raw TeX subscript
    # token outside known mathematical nodes (including align/equation bodies).
    underscores = []
    for match in re.finditer('_', source):
        prefix = source[:match.start()]
        slashes = len(prefix) - len(prefix.rstrip('\\'))
        if slashes % 2:
            continue
        part = next((part for part in parts if part['start'] <= match.start() < part['end']), None)
        if match.start() < parsed['start'] or (part and part['kind'] in EXEMPT_LEAK):
            continue
        underscores.append(match.start())
        output['warnings'].append(warning('prose_text_subscript',
            'Unescaped underscore outside a parsed mathematical environment.', position=match.start(), tex=tex_text))
    citations = []
    if problem_year is not None:
        # Dates are checked only inside literal bibliography/reference sections,
        # never arbitrary body years or years embedded in a public URL.
        for part in parts:
            if part['kind'] != 'references':
                continue
            raw = strip_comments(tex_text)[part['content_start']:part['end']]
            raw = re.sub(r'\\(?:url|href)\{[^{}]*\}', ' ', raw)
            for match in re.finditer(r'(?<![\w])(?:19|20|21)[0-9]{2}(?![\w])', plain_text(raw)):
                year = int(match.group())
                if year > problem_year:
                    citations.append({'year': year, 'section': part['title']})
                    if not allow_anachronism:
                        output['warnings'].append(warning('prose_anachronistic_reference',
                            f'Reference year {year} is later than problem year {problem_year}.',
                            position=part['start'], tex=tex_text, section=part['title'], reference_text_offset=match.start()))
    output['metrics'].update(precision_candidates=precision, process_leak_candidates=leaks,
                             text_subscripts=underscores, later_reference_years=citations,
                             unexpanded_constructs=hidden)
    if problem_year is None:
        output['warnings'].append(warning('prose_reference_year_unchecked',
            'Problem year was not supplied; reference chronology was not checked.'))
    output['limitations'] += [
        'PDF headings must match normalized literal TeX titles uniquely and in order; repeated running headings, renamed macros and TOC ambiguity can prevent mapping.',
        'Negation uses the original calibration English tokens and six-word sentence minimum; Chinese prose is not calibrated.',
        'Precision covers recognized money/percentage/count quantities with six or more displayed significant digits; bare decimals and implicit units are outside coverage.',
        'Chronology checks literal reference-section years, not an external bibliography database or the truth of publication dates.',
    ]
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tex', type=Path)
    parser.add_argument('pdf', type=Path, help='Actual PDF; each page is extracted with pypdf')
    parser.add_argument('--problem-year', type=int)
    parser.add_argument('--allow-anachronism', action='store_true')
    args = parser.parse_args(argv)
    try:
        from pypdf import PdfReader
        reader = PdfReader(args.pdf)
        pages = [page.extract_text() or '' for page in reader.pages]
        output = inspect(args.tex.read_text(encoding='utf-8'), pages,
                         problem_year=args.problem_year, allow_anachronism=args.allow_anachronism)
    except (OSError, UnicodeError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(output, indent=2, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
