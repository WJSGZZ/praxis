import json
import pytest
from scripts import check_prose


def codes(result):
    return {w['code'] for w in result['warnings']}


def test_profiles_use_separate_calibration_and_unknown_uses_wider():
    config = json.loads(check_prose.CALIBRATION.read_text())['profiles']
    text = '条件尚未满足时需要额外核对测量范围。' + '本文分析实际观察数据并解释测量范围。' * 12
    results = {p: check_prose.inspect('', [text], profile=p) for p in ('contest', 'research', 'unknown')}
    assert results['contest']['metrics']['neg_ratio_threshold'] == 0.05
    assert results['research']['metrics']['neg_ratio_threshold'] == config['research']['threshold']
    assert results['unknown']['metrics']['neg_ratio_threshold'] == max(v['threshold'] for v in config.values())
    assert results['unknown']['metrics']['neg_ratio_threshold_profile'] == 'research'
    assert 'prose_negation_ratio' in codes(results['contest'])
    assert 'prose_negation_ratio' not in codes(results['research'])
    assert 'prose_negation_ratio' in codes(check_prose.inspect('', ['尚未确定对象时需要核对所有测量范围。'] * 4, profile='research'))
    assert results['research']['diagnostic_only'] is True


def test_profile_validation_and_english_unchanged():
    with pytest.raises(ValueError):
        check_prose.inspect('', ['text'], profile='made-up')
    for profile in ('contest', 'research', 'unknown'):
        assert check_prose.inspect('', ['The model has a clear local interpretation.'], profile=profile)['metrics']['neg_ratio_threshold'] == 0.16


def test_precision_table_endpoint_and_summary_are_separate():
    tex = r'''\section{摘要}结果为0.1234567。
\section{推导}精确端点为$855.569985$元。
\begin{tabular}{rr}端点 & 123.456789元\\\end{tabular}
\section{结论}建议为855.569985元，指标0.1234567。'''
    pages = ['摘要\n结果为0.1234567。\n推导\n精确端点为855.569985元。\n端点 123.456789元\n结论\n建议为855.569985元，指标0.1234567。']
    r = check_prose.inspect(tex, pages)
    assert [p['text'] for p in r['metrics']['precision_candidates']] == ['0.1234567', '855.569985元', '0.1234567']
    assert {p['reason'] for p in r['metrics']['precision_exemptions']} == {'unique_literal_table_cell', 'unique_literal_math_endpoint'}


def test_precision_does_not_exempt_unbound_or_repeated_literals():
    tex = r'\section{推导}端点$855.569985$元。推荐855.569985元。'
    r = check_prose.inspect(tex, ['推导\n端点855.569985元。推荐855.569985元。'])
    assert len(r['metrics']['precision_candidates']) == 2
    assert not r['metrics']['precision_exemptions']
    assert len(check_prose.inspect(r'\section{推导}text', ['推导\n端点855.569985元。'])['metrics']['precision_candidates']) == 1


def test_multiline_derivation_matches_pdf_wrap_but_not_conclusion():
    tex = r'''\section{推导}
连续最优为$P=\sqrt{732000}\approx855.569985$元，净额约3250.064935元。

\section{结论}连续最优端点约855.569985元。'''
    r = check_prose.inspect(tex, ['推导\n连续最优为 P =\n855.569985元，净额约\n3250.064935元。\n结论\n连续最优端点约855.569985元。'])
    assert len(r['metrics']['precision_exemptions']) == 2
    assert [x['page'] for x in r['metrics']['precision_candidates']] == [1]


def test_delivery_propagates_profile():
    from scripts.manuscript_delivery import inspect
    for mode in ('contest', 'research'):
        result = inspect('', ['本文分析实际观察数据并解释测量范围。'], pdf_sha256='a'*64, mode=mode)
        assert result['reports']['prose']['metrics']['neg_ratio_threshold_profile'] == mode


def test_unrelated_table_or_formula_cannot_exempt_a_prose_claim():
    tex = r'''\section{分析}推荐报价为855.569985元。
\begin{tabular}{r}855.569985元\end{tabular}
\section{端点推导}端点$855.569985$元。'''
    result = check_prose.inspect(tex, ['分析\n推荐报价为855.569985元。\n855.569985元\n端点推导\n端点855.569985元。'])
    assert len(result['metrics']['precision_candidates']) == 2
    assert len(result['metrics']['precision_exemptions']) == 1
