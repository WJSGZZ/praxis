"""Build a bounded reader packet from an actual PDF; no paper-quality score.

Heading/caption selection is a text heuristic. Explicit page additions cover
unlabelled figures and unusual headings after a human checks the full PDF.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from pypdf import PdfReader, PdfWriter


_FIGURE = re.compile(r"\b(?:Figure|Fig\.)\s*\d+|图\s*\d+", re.I)
_TARGET = re.compile(
    r"^(?:\d+(?:\.\d+)*[.)]?\s+)?"
    r"(?P<title>Conclusions?(?:\s+and\s+\w+)?|Concluding remarks|"
    r"(?:Executive\s+)?Memorandum|Memo(?:randum)?(?:\s+to\s+.{1,80})?|"
    r"Letter(?:\s+to\s+.{1,80})?|Report\s+to\s+[^.!?]{1,100}Committee|Committee(?:\s+report)?|"
    r"结论|结论与展望|备忘录|委员会报告)\s*$", re.I)
_STOP = re.compile(
    r"^(?:\d+(?:\.\d+)*[.)]?\s+)?(?:References|Bibliography|Appendix(?:\s+\w+)?|"
    r"Report on Use of AI(?: Tools)?|参考文献|附录|AI工具使用声明)\s*$", re.I)
_BODY_HEADING = re.compile(r"^\d+(?:\.\d+)*\s+\S")
_PAGE_HEADER = re.compile(r"^(?:Team\s*(?:#|Control Number)|Page\s*\d+|\d+\s*(?:of\s*\d+)?$)", re.I)


def select_pages(pages, *, extra_pages=()):
    """Return one-based pages plus reasons; never silently call it full reading."""
    if not pages:
        raise ValueError('Reader packet requires a nonempty PDF')
    if any(not isinstance(page, str) for page in pages):
        raise ValueError('PDF pages must be extracted text strings')
    extra_pages = list(extra_pages)
    if any(type(page) is not int or not 1 <= page <= len(pages) for page in extra_pages):
        raise ValueError('Explicit pages must be one-based integers inside the PDF')
    selected = {1: ['first_page']}
    active = None
    for number, text in enumerate(pages, 1):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        reasons = []
        if _FIGURE.search(text):
            reasons.append('figure_text_or_reference')
        # Contents entries ending in page numbers do not match target headings.
        targets = [m for line in lines if (m := _TARGET.fullmatch(line))]
        significant = [line for line in lines[:12] if not _PAGE_HEADER.match(line)]
        stop_before_target = any(_STOP.fullmatch(line) or _BODY_HEADING.match(line)
                                 for line in significant[:1])
        if active and stop_before_target and not targets:
            active = None
        if targets:
            title = targets[0].group('title')
            active = 'conclusion' if re.search(r'conclu|结论', title, re.I) else 'memo'
            reasons.append(active + '_heading')
        elif active:
            reasons.append(active + '_continuation_candidate')
        if reasons:
            selected.setdefault(number, []).extend(reasons)
    for number in extra_pages:
        selected.setdefault(number, []).append('explicit_page')
    if not any('conclusion_heading' in reasons for reasons in selected.values()):
        # Argument-led final sections need not literally be called Conclusions.
        # Include candidates, while retaining the need for a page-coverage review.
        boundaries = [number for number, text in enumerate(pages, 1)
                      if any(_STOP.fullmatch(line.strip()) or
                             ((match := _TARGET.fullmatch(line.strip()))
                              and not re.search(r'conclu|结论', match.group('title'), re.I))
                             for line in text.splitlines())]
        boundary = min(boundaries) if boundaries else len(pages) + 1
        for number in range(max(2, boundary - 2), boundary):
            selected.setdefault(number, []).append('last_body_conclusion_candidate')
    return [{'original_page': page, 'reasons': sorted(set(selected[page]))}
            for page in sorted(selected)]


def review_warnings(review, problem_items):
    """Check a returned reader's coverage and fields, without grading answers."""
    warnings = []

    def warn(code, message, location):
        warnings.append(dict(code=code, message=message, location=location))

    ids = [item['id'] for item in problem_items]
    if not isinstance(review, dict) or review.get('type') != 'reader':
        return [dict(code='reader.type', message='Expected type: reader', location='review')]
    rows = review.get('problem_items')
    if not isinstance(rows, list):
        return [dict(code='reader.items', message='Expected problem_items list', location='review')]
    seen = set()
    for index, row in enumerate(rows):
        location = f'problem_items[{index}]'
        if not isinstance(row, dict):
            warn('reader.row', 'Expected an item object', location)
            continue
        identity = row.get('id')
        if not isinstance(identity, str) or identity not in ids or identity in seen:
            warn('reader.identity', 'Unknown or repeated problem item id', location)
        else:
            seen.add(identity)
        if row.get('answer_found') not in ('yes', 'no'):
            warn('reader.answer_found', 'answer_found must be yes or no', location)
        elif row['answer_found'] == 'no':
            warn('reader.answer_missing', 'Reader did not find an answer', str(identity))
        for field in ('answer_one_line', 'why_credible', 'top_question'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                warn('reader.field', f'Missing {field}; state uncertainty explicitly', location)
    for identity in sorted(set(ids) - seen):
        warn('reader.item_missing', 'No reader response for this problem item', identity)
    return warnings


def build(source, destination, requirements, *, extra_pages=(), minutes=25):
    source, destination = Path(source), Path(destination)
    if type(minutes) is not int or not 20 <= minutes <= 30:
        raise ValueError('Reader time budget must be 20 to 30 minutes')
    items = requirements.get('problem_items') if isinstance(requirements, dict) else None
    if (not isinstance(items, list) or not items or
            any(not isinstance(item, dict) or not isinstance(item.get('id'), str)
                or not item['id'].strip() or not isinstance(item.get('quote'), str)
                or not item['quote'].strip() for item in items)):
        raise ValueError('Requirements need nonempty problem_items with id and quote')
    if len({item['id'] for item in items}) != len(items):
        raise ValueError('Problem item ids must be unique')
    if destination.exists():
        raise FileExistsError(destination)
    raw = source.read_bytes()
    from io import BytesIO
    doc = PdfReader(BytesIO(raw))
    if doc.is_encrypted:
        raise ValueError('Reader PDF must be unencrypted')
    pages = [page.extract_text() or '' for page in doc.pages]
    selected = select_pages(pages, extra_pages=extra_pages)
    writer = PdfWriter()
    for record in selected:
        writer.add_page(doc.pages[record['original_page'] - 1])
    destination.mkdir(parents=True, exist_ok=False)
    packet_pdf = destination / 'packet.pdf'
    with packet_pdf.open('xb') as stream:
        writer.write(stream)
    template = {'type': 'reader', 'actor': '', 'minutes_used': None,
                'source_pdf_sha256': hashlib.sha256(raw).hexdigest(),
                'problem_items': [{'id': item['id'], 'answer_found': None,
                                   'answer_one_line': '', 'why_credible': '', 'top_question': ''}
                                  for item in items]}
    prompt = (
        f'在全新上下文中只读此 packet、题面条目和空白模板，限时 {minutes} 分钟。\n'
        '逐项回答是否找到直接答案（yes/no）、一句话答案、可信依据、最想追问的问题。\n'
        '没有找到时如实写 no；未知依据写未知。不要读取完整论文、源码或其他评审，'
        '不要给奖档。填 reader-review-template.json，保留实际 actor 和耗时。\n'
        'packet 包含首页、可识别图页、结论与 Memo 候选页；页码映射见 packet.json。\n')
    (destination / 'PROMPT.txt').write_text(prompt, encoding='utf-8')
    (destination / 'problem-items.json').write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (destination / 'reader-review-template.json').write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    receipt = dict(schema_version=1, type='reader_packet', diagnostic_only=True,
                   created_utc=datetime.now(timezone.utc).isoformat(),
                   source_pdf_sha256=hashlib.sha256(raw).hexdigest(),
                   packet_pdf_sha256=hashlib.sha256(packet_pdf.read_bytes()).hexdigest(),
                   source_pages=len(pages), packet_pages=len(selected), pages=selected,
                   minutes=minutes,
                   limitations=['Text-based figure selection includes prose references and can miss unlabelled graphics.',
                                'Heading continuation and final-body fallback are heuristic; inspect coverage and add explicit pages as needed.',
                                'Packet reading is not full-paper or mathematical validation.'])
    (destination / 'packet.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    if source.read_bytes() != raw:
        raise ValueError('Source PDF changed while building reader packet')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--requirements', required=True, type=Path)
    parser.add_argument('--pages', nargs='*', type=int, default=[])
    parser.add_argument('--minutes', type=int, default=25)
    args = parser.parse_args()
    result = build(args.pdf, args.destination, json.loads(args.requirements.read_text(encoding='utf-8')),
                   extra_pages=args.pages, minutes=args.minutes)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
