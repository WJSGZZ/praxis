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

QUALITY_CHECKLIST = [
    '摘要是否给出主要发现和关键数字？',
    '结论是否先讲发现及其含义？',
    '有无自我评价和内部过程话？',
    '逐图逐面板列出已查的标注和图例：文字是否被线、点、填充穿过？图例整个框内及边缘是否有数据或距离过近？',
    '逐图核对关键数字与正文：近似显示、连续值和实际实施精度能否直接区分？摘要、结论及教材／备忘录等对外说明的量词与分母是否和正文一致，是否会造成读法矛盾？',
    '同一文字角色的字体家族与字号是否跨图一致，术语、单位及数字精度是否一致且含义明确？',
    '首页和模板标签的语言是否统一？',
    '局限是否集中、具体，且保留结论所需条件？',
    '读者最可能误解的一处是什么？',
]


def quality_status(review, pdf_sha256):
    """Record truthfully; missing/unfinished review is a warning, never refusal.

    Actor/context/scope are declarations, not mechanically certified isolation.
    Historical coverage-only records remain readable but do not certify this review.
    """
    pending = {'status': '未经独立读者审阅', 'unresolved': None,
               'diagnostic_only': True}
    if not isinstance(review, dict):
        return pending
    initial = review.get('initial_review')
    followup = (review.get('review_round') == 'followup' and isinstance(initial, dict)
                and initial.get('actor') == review.get('actor')
                and initial.get('fresh_context') is True
                and initial.get('source_pdf_sha256') == review.get('initial_pdf_sha256')
                and quality_status(initial, review.get('initial_pdf_sha256'))['status'] != pending['status'])
    checks = review.get('quality_checks')
    if (review.get('type') != 'reader' or review.get('source_pdf_sha256') != pdf_sha256
            or not isinstance(review.get('actor'), str) or not review['actor'].strip()
            or (review.get('fresh_context') is not True and not followup)
            or review.get('reading_scope') != 'rendered_pages_only'
            or not isinstance(checks, list) or len(checks) != len(QUALITY_CHECKLIST)
            or any(not isinstance(c, dict) or not isinstance(c.get('id'), str)
                   or c.get('verdict') not in ('clear', 'issue', 'uncertain')
                   or not isinstance(c.get('evidence'), str) or not c['evidence'].strip() for c in checks)
            or {c.get('id') for c in checks} != {str(i+1) for i in range(len(QUALITY_CHECKLIST))}
            or not isinstance(review.get('issues'), list)):
        return pending
    rows = review['issues']
    if any(not isinstance(row, dict) for row in rows):
        return pending
    unresolved = sum(row.get('status') not in ('fixed', 'retained')
                     or not isinstance(row.get('resolution'), str) or not row['resolution'].strip()
                     or (row.get('status') == 'fixed' and review.get('review_round') != 'followup')
                     for row in rows)
    # An issue/uncertainty verdict cannot disappear by omitting the issues list.
    if not rows and any(c['verdict'] != 'clear' for c in checks):
        unresolved = sum(c['verdict'] != 'clear' for c in checks)
    return {'status': f'有 {unresolved} 项未处理' if unresolved else '已完成独立读者审阅',
            'unresolved': unresolved, 'diagnostic_only': True}


def build_quality(source, destination, question):
    """Full rendered-page review packet; no source, logs or author assessments.

    Large PDF Form XObjects get isolated enlarged views. Inline pgfplots/raster
    figures without separable forms need explicit visual coverage on full pages;
    no crop inferred from a caption is presented as a precise figure extraction.
    """
    from pypdf.generic import ContentStream
    import pypdfium2
    source, destination = Path(source), Path(destination)
    raw = source.read_bytes()
    if not isinstance(question, str) or not question.strip():
        raise ValueError('Supply the original research question or problem')
    destination.mkdir(parents=True, exist_ok=False)
    (destination/'packet.pdf').write_bytes(raw)
    (destination/'question.txt').write_text(question, encoding='utf-8')
    reader, writer = PdfReader(source), PdfWriter()
    figures, number_tokens = [], []
    doc = pypdfium2.PdfDocument(source)
    for number, pdf_page in enumerate(reader.pages, 1):
        page = doc[number-1]
        page.render(scale=1.5).to_pil().save(destination/f'page-{number:02}.png')
        text = page.get_textpage()
        number_tokens.append({'page':number, 'tokens':re.findall(r'\d+(?:\.\d+)?', text.get_text_range()),
                              'scope':'actual full page; figure-only numeric tokens below when separable'})
        text.close()
        matrix, stack = (1,0,0,1,0,0), []
        def compose(m, n):
            a,b,c,d,e,f=m;g,h,i,j,k,l=map(float,n)
            return (a*g+c*h,b*g+d*h,a*i+c*j,b*i+d*j,a*k+c*l+e,b*k+d*l+f)
        for args, op in ContentStream(pdf_page.get('/Contents'), reader).operations:
            if op == b'q': stack.append(matrix)
            elif op == b'Q': matrix=stack.pop()
            elif op == b'cm': matrix=compose(matrix,args)
            elif op == b'Do':
                obj=pdf_page['/Resources']['/XObject'][args[0]].get_object()
                if obj.get('/Subtype') != '/Form' or '/BBox' not in obj: continue
                x0,y0,x1,y1=map(float,obj['/BBox'])
                a,b,c,d,e,f=compose(matrix,obj.get('/Matrix',(1,0,0,1,0,0)))
                points=[(a*x+c*y+e,b*x+d*y+f) for x,y in [(x0,y0),(x1,y1),(x0,y1),(x1,y0)]]
                left,right=min(x for x,y in points),max(x for x,y in points)
                bottom,top=min(y for x,y in points),max(y for x,y in points)
                if right-left < 120 or top-bottom < 60: continue
                view=writer.add_page(pdf_page)
                view.cropbox.lower_left=(left,bottom);view.cropbox.upper_right=(right,top)
                i=len(figures)+1
                # Preserve the PDF crop too, not only a raster enlargement.
                page.render(scale=2.5,crop=(max(0,left),max(0,bottom),
                    max(0,float(page.get_width())-right),max(0,float(page.get_height())-top))).to_pil().save(destination/f'figure-{i:02}.png')
                ft=page.get_textpage()
                bounded=ft.get_text_bounded(left,bottom,right,top);ft.close()
                figures.append({'figure':i,'page':number,'bbox_pdf_points':[left,bottom,right,top],
                    'numbers':re.findall(r'\d+(?:\.\d+)?',bounded),'view':f'figure-{i:02}.png'})
        page.close()
    doc.close()
    if figures:
        writer.write(destination/'figure-views.pdf')
    template={'type':'reader','actor':'','source_pdf_sha256':hashlib.sha256(raw).hexdigest(),
        'fresh_context':True,'reading_scope':'rendered_pages_only','review_round':'initial',
        'quality_checks':[{'id':str(i+1),'question':q,'verdict':None,'evidence':''}
                          for i,q in enumerate(QUALITY_CHECKLIST)],'issues':[]}
    (destination/'reader-review-template.json').write_text(json.dumps(template,ensure_ascii=False,indent=2))
    (destination/'PROMPT.txt').write_text('只读本目录成品PDF/页面和问题，先独立审阅，不读源码、作者记录或其他评语。逐页实看，并逐图放大核对。按九条清单填写记录，给页面依据；问题写id/page/description/status=open。没有问题也需逐条有据。不要给奖档，不重算模型，不自行改论文。\n'+ '\n'.join(f'{i+1}. {q}' for i,q in enumerate(QUALITY_CHECKLIST)),encoding='utf-8')
    packet={'type':'reader_quality_packet','source_pdf_sha256':hashlib.sha256(raw).hexdigest(),
        'source_pages':len(reader.pages),'packet_pages':len(reader.pages),'scope':'all_pages',
        'figures':figures,'page_number_tokens':number_tokens,
        'figure_review_scope':'separable large Form XObjects; inline pgfplots or unseparated images require manual enlarged full-page review',
        'limitations':['Numeric tokens are not automatically matched to scientific claims.',
                       'Fresh context and allowed-input isolation require orchestration; this packet does not enforce a sandbox.']}
    (destination/'packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2))
    if source.read_bytes()!=raw: raise ValueError('PDF changed while preparing packet')
    return packet


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
    parser.add_argument('--requirements', type=Path)
    parser.add_argument('--quality', action='store_true', help='Full rendered-page professional reader review')
    parser.add_argument('--question', type=Path, help='Original problem or research question text')
    parser.add_argument('--pages', nargs='*', type=int, default=[])
    parser.add_argument('--minutes', type=int, default=25)
    args = parser.parse_args()
    if args.quality:
        if args.question is None: parser.error('--quality needs --question')
        result = build_quality(args.pdf,args.destination,args.question.read_text(encoding='utf-8'))
    else:
        if args.requirements is None: parser.error('coverage packet needs --requirements')
        result = build(args.pdf, args.destination, json.loads(args.requirements.read_text(encoding='utf-8')),
                       extra_pages=args.pages, minutes=args.minutes)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
