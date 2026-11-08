"""Reader-facing regressions: warnings remain advisory, including Chinese prose."""
from scripts import check_prose


def codes(report):
    assert report['diagnostic_only'] is True
    return {w['code'] for w in report['warnings']}


def test_chinese_headings_run_in_and_exempt_limitations():
    tex = (r'\begin{document}\begin{abstract}本文给出条件结果。\end{abstract}'
           r'\section{引言：研究问题}本轮核读没有建立可靠证据。'
           r'\subsection{模型定义}这个方法不能保证任何市场都实现收入目标。'
           r'\section{局限与后续研究}尚未识别现实概率。'
           r'\subsection{覆盖范围}目前无法识别总体概率。'
           r'\appendix\section{复现说明}本轮冻结收据。\end{document}')
    pages = ['摘要. 本文给出条件结果。\n1. 引言：研究问题\n本轮核读没有建立可靠证据。\n'
             '1.1. 模型定义. 这个方法不能保证任何市场都实现收入目标。\n'
             '2. 局限与后续研究\n尚未识别现实概率。\n2.1. 覆盖范围. 目前无法识别总体概率。\n'
             '附录 A. 复现说明\n本轮冻结收据。']
    result = check_prose.inspect(tex, pages)
    assert result['metrics']['mapping_status'] == 'mapped_literal_headings'
    assert result['metrics']['language'] == 'zh'
    assert result['metrics']['body_sentences'] == 2
    assert result['metrics']['negative_sentences'] == 1
    assert 'prose_process_leak' in codes(result)
    assert all(c['text'] not in ('冻结', '收据') for c in result['metrics']['process_leak_candidates'])


def test_self_evaluation_is_separate_from_necessary_conditions():
    tex = r'\begin{document}\section{分析}本文不是新定理，尚未建立原创贡献。\end{document}'
    result = check_prose.inspect(tex, ['1. 分析\n本文不是新定理，尚未建立原创贡献。'])
    assert 'prose_self_evaluation' in codes(result)
    assert result['metrics']['neg_ratio_threshold_status'] == 'calibration_sample'
    assert result['metrics']['neg_ratio_threshold'] != 0.16
    good = check_prose.inspect(r'\section{Analysis}Text',
        ['1 Analysis\nThe value is not defined when the denominator is zero.'])
    assert 'prose_self_evaluation' not in codes(good)


def test_english_self_evaluation_and_negation_rule_preserved():
    result = check_prose.inspect(r'\section{Analysis}Text',
        ['1 Analysis\nThis result is not novel enough for a top journal.'])
    assert 'prose_self_evaluation' in codes(result)
    assert result['metrics']['language'] == 'en'
    assert result['metrics']['neg_ratio_threshold'] == 0.16


def test_research_summary_distinguishes_targets_and_results():
    from scripts.check_summary import inspect
    target = r'\begin{abstract}本文研究月收入3000元目标。尚未识别现实概率。\end{abstract}'
    result = inspect(target, reader_quality=True)
    assert {'summary_result_numbers_missing', 'summary_limitation_boundary'} <= codes(result)
    found = inspect(r'\begin{abstract}在给定情景中，净额由3020元升至3300元。结果用于比较条件方案。\end{abstract}', reader_quality=True)
    assert found['metrics']['result_quantity_count'] == 2
    assert 'summary_result_numbers_missing' not in codes(found)


def test_chinese_first_page_labels_and_research_coverage_scope():
    from scripts.manuscript_delivery import inspect
    tex = r'\begin{document}\begin{abstract}净额由3020元升至3300元。\end{abstract}\section{引言}正文。\end{document}'
    result = inspect(tex, ['摘要. 净额由3020元升至3300元。\n1. 引言\n中文正文用于讨论经营回报。\nDate: 2026\nKey words and phrases.'],
                     pdf_sha256='a'*64, mode='research')
    assert 'delivery.first_page_language' in {w['code'] for w in result['warnings']}
    assert 'delivery.coverage_inputs' not in {w['code'] for w in result['warnings']}


def test_research_archived_style_preserved_and_new_style_localizes():
    from scripts.paper_template import style_block, check
    old = style_block('research', layout_version=1)
    new = style_block('research')
    assert 'PraxisResearchChinese' in new
    assert 'PraxisResearchChinese' not in old
    for block in (old, new):
        check(r'\newcommand{\PraxisTitle}{A result}' + block +
              r'\title[A result]{A result}\begin{document}Text.\end{document}', 'research')


def test_reader_status_is_truthful_without_rejecting_delivery(tmp_path):
    from scripts.reader_packet import quality_status, QUALITY_CHECKLIST
    assert quality_status(None, 'a'*64)['status'] == '未经独立读者审阅'
    good = {'type': 'reader', 'actor': 'fresh reader', 'source_pdf_sha256': 'a'*64,
            'fresh_context': True, 'reading_scope': 'rendered_pages_only',
            'quality_checks': [{'id': str(i+1), 'verdict': 'clear', 'evidence': 'page 1'}
                               for i in range(len(QUALITY_CHECKLIST))], 'issues': []}
    assert quality_status(good, 'b'*64)['status'] == '未经独立读者审阅'
    good['issues'] = [{'id': 'one', 'status': 'open', 'description': 'ambiguous label', 'page': 1}]
    assert quality_status(good, 'a'*64)['status'] == '有 1 项未处理'
    good['issues'][0]['status'] = 'retained'
    assert quality_status(good, 'a'*64)['status'] == '有 1 项未处理'
    good['issues'][0]['resolution'] = 'Approximate continuous value explicitly stated on page 2.'
    assert quality_status(good, 'a'*64)['status'] == '已完成独立读者审阅'
    good['issues'][0]['status'] = 'fixed'
    assert quality_status(good, 'a'*64)['status'] == '有 1 项未处理'
    good['review_round'] = 'followup'
    assert quality_status(good, 'a'*64)['status'] == '已完成独立读者审阅'


def test_reader_quality_missing_or_incomplete_stays_pending():
    from scripts.reader_packet import quality_status
    for review in ({}, {'type':'reader'}, {'type':'reader', 'source_pdf_sha256':'a'*64,
         'actor':'reader', 'fresh_context':True, 'reading_scope':'rendered_pages_only',
         'quality_checks':[], 'issues':[]}):
        assert quality_status(review, 'a'*64)['status'] == '未经独立读者审阅'


def test_followup_reuses_the_initial_reader_without_claiming_a_new_blind_context():
    import copy
    from scripts.reader_packet import quality_status, QUALITY_CHECKLIST
    initial={'type':'reader','actor':'reader-one','source_pdf_sha256':'a'*64,
             'fresh_context':True,'reading_scope':'rendered_pages_only',
             'quality_checks':[{'id':str(i+1),'verdict':'clear','evidence':'page 1'}
                               for i in range(len(QUALITY_CHECKLIST))],'issues':[]}
    final=copy.deepcopy(initial)
    final.update(fresh_context=False,review_round='followup',source_pdf_sha256='b'*64,
                 initial_pdf_sha256='a'*64,initial_review=initial)
    final['issues']=[{'status':'open','id':'new','description':'still overlapped'}]
    assert quality_status(final,'b'*64)['status'] == '有 1 项未处理'
    final['issues'][0].update(status='fixed',resolution='same reader checked page 1 again')
    assert quality_status(final,'b'*64)['status'] == '已完成独立读者审阅'
    final['actor']='different-reader'
    assert quality_status(final,'b'*64)['status'] == '未经独立读者审阅'


def test_quality_packet_includes_every_page_even_blank(tmp_path):
    import json
    from pypdf import PdfWriter
    from scripts.reader_packet import build_quality
    source=tmp_path/'source.pdf';writer=PdfWriter()
    writer.add_blank_page(width=300,height=400)
    writer.add_blank_page(width=300,height=400)
    writer.write(source)
    packet=build_quality(source,tmp_path/'packet','A research question')
    assert packet['source_pages'] == packet['packet_pages'] == 2
    assert (tmp_path/'packet/page-02.png').exists()
    assert packet['figures'] == []
    assert (tmp_path/'packet/packet.pdf').read_bytes() == source.read_bytes()
    template = json.loads((tmp_path/'packet/reader-review-template.json').read_text())
    assert template['quality_schema_version'] == 2
    assert template['fresh_context'] is None
    assert all(row['issue_ids'] == [] for row in template['quality_checks'])


def test_unrelated_issue_cannot_close_a_comparison_or_hide_it_on_followup():
    from scripts.reader_packet import QUALITY_CHECKLIST, quality_status
    initial = {
        'quality_schema_version': 2, 'type': 'reader', 'actor': 'fixture',
        'reading_scope': 'rendered_pages_only', 'fresh_context': True, 'review_round': 'initial',
        'source_pdf_sha256': 'a'*64,
        'quality_checks': [
            {'id': str(i), 'verdict': 'clear', 'evidence': 'page 1', 'issue_ids': []}
            for i in range(1, len(QUALITY_CHECKLIST) + 1)],
        'issues': [{'id': 'unit', 'page': 1, 'description': 'Unit abbreviation.',
                    'status': 'retained', 'resolution': 'Table header specifies hours.'}]}
    initial['quality_checks'][1].update(verdict='issue', issue_ids=['comparison'])
    # The 70% reduction compares the proposed method at low load with the
    # baseline at high load. Neither a resolved unit question nor a clean
    # verdict on the next PDF accounts for the reader's original objection.
    assert quality_status(initial, 'a'*64)['unresolved'] == 1
    problem = {'id': 'comparison', 'page': 1, 'description': 'Unlike workloads.', 'status': 'open'}
    initial['issues'].append(problem)
    assert quality_status(initial, 'a'*64)['unresolved'] == 1
    revised = dict(initial, review_round='followup', fresh_context=False,
                   initial_review=initial, initial_pdf_sha256='a'*64, source_pdf_sha256='b'*64,
                   quality_checks=[dict(c, verdict='clear', issue_ids=[]) for c in initial['quality_checks']],
                   issues=initial['issues'][:1])
    assert quality_status(revised, 'b'*64)['unresolved'] == 1
    downgraded = {k: v for k, v in revised.items() if k != 'quality_schema_version'}
    assert quality_status(downgraded, 'b'*64)['status'] == '未经独立读者审阅'
    assert quality_status(dict(downgraded, quality_schema_version=1), 'b'*64)['status'] == '未经独立读者审阅'
    # A reader named the concern on the checklist but omitted its issue
    # row. It must survive even if the new checklist now says clear.
    incomplete = dict(initial, issues=initial['issues'][:1])
    assert quality_status(dict(revised, initial_review=incomplete), 'b'*64)['unresolved'] == 1
    unnamed = dict(incomplete, quality_checks=[dict(c, issue_ids=[]) for c in incomplete['quality_checks']])
    assert quality_status(dict(revised, initial_review=unnamed), 'b'*64)['unresolved'] == 1
    revised['issues'].append(dict(problem, status='fixed', resolution='Page 1 compares like workloads.'))
    assert quality_status(revised, 'b'*64)['unresolved'] == 0
    assert quality_status(dict(revised, initial_review=incomplete), 'b'*64)['unresolved'] == 0
    linked = [dict(c) for c in revised['quality_checks']]
    linked[1]['issue_ids'] = ['comparison']
    assert quality_status(dict(revised, initial_review=unnamed, quality_checks=linked), 'b'*64)['unresolved'] == 0
    assert quality_status(dict(revised, fresh_context=True), 'b'*64)['status'] == '未经独立读者审阅'
    unbound = dict(revised, initial_pdf_sha256=None, initial_review=dict(initial, source_pdf_sha256=None))
    assert quality_status(unbound, 'b'*64)['status'] == '未经独立读者审阅'


def test_contract_acceptance_is_not_an_internal_process_leak():
    r = check_prose.inspect(r'\section{分析}正文。',
        ['1. 分析\n客户验收标准决定约定交付单位，已验收并回款后才计入经营收入。'])
    assert 'prose_process_leak' not in codes(r)
    bad = check_prose.inspect(r'\section{分析}正文。',
        ['1. 分析\n本轮验收完成后冻结内部报告与收据。'])
    assert 'prose_process_leak' in codes(bad)
    crossed = check_prose.inspect(r'\section{分析}正文。',
        ['1. 分析\n虚线只用于显示目标，不是经验收入水平的观察记录。'])
    assert 'prose_process_leak' not in codes(crossed)


def test_summary_actual_pdf_numbers_override_unexpanded_tex():
    from scripts.check_summary import inspect
    source=r'\begin{document}\begin{abstract}We estimate \unknownfact{rate} outcomes.\end{abstract}\section{Model}Body.\end{document}'
    r=inspect(source,reader_quality=True,pdf_pages=['Abstract\nWe get 46.20 hours from the model.\n1 Model\nBody.'])
    assert r['metrics']['result_quantity_count'] == 1
    assert r['metrics']['reader_quality_text_source'] == 'actual_pdf_abstract'
    assert 'summary_result_numbers_missing' not in codes(r)


def test_scientific_units_and_pdf_paragraph_uncertainty():
    from scripts.manuscript import quantities
    from scripts.check_summary import inspect
    assert len(quantities('At 10 dB the range reaches 6 hops; the battery is 9 V.')) == 3
    r=inspect('Random wave theory predicts 6 hops. We get 4 hops at 10 dB. '
              'The result is stable. We explain the model.',reader_quality=True,paragraph_boundaries_known=False)
    assert 'summary_first_paragraph_long' not in codes(r)
    assert r['metrics']['first_paragraph_sentences'] is None
    assert r['metrics']['result_quantity_count'] >= 2


def test_currency_precision_and_mathematical_candidates_are_not_process_noise():
    r=check_prose.inspect(r'\section{分析}Text',
        ['1. 分析\n报价候选解的净额为3250.00元，端点为855.569985元。'])
    assert 'prose_process_leak' not in codes(r)
    assert [p['text'] for p in r['metrics']['precision_candidates']] == ['855.569985元']
