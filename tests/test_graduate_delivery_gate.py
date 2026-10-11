"""The full 2026 submission and the anonymous report are different objects."""
import pytest

from scripts.contest_rules import evaluate, extract
from tests.test_cumcm_delivery_gate import page, write_cjk_pdf


def report():
    return [page('题目\n摘 要\n摘要。\n关键词：甲；乙\n1'),
            page('正文\n结果。\n2')]


def submission():
    return [page('中国研究生数学建模竞赛\n学 校：某某大学\n参赛队号：26000010001\n队员姓名：甲、乙、丙')] + report()


def test_report_default_preserves_the_anonymous_report_boundary():
    result = evaluate(report(), 'graduate', edition='2026')
    assert result['passed']
    assert result['facts']['document_kind'] == 'report'
    assert result['facts']['abstract_from_pdf_page'] == 1
    assert any('does not certify the complete' in w for w in result['warnings'])


def test_submission_starts_with_cover_then_logical_abstract_page_one():
    result = evaluate(submission(), 'graduate', edition=2026, document_kind='submission')
    assert result['passed'], result
    assert result['facts']['abstract_from_pdf_page'] == 2
    assert result['facts']['anonymity_from_pdf_page'] == 2
    assert not any('bottom page-number' in w for w in result['warnings'])
    assert any('four original logos' in w for w in result['warnings'])


def test_anonymous_report_is_not_a_complete_submission():
    result = evaluate(report(), 'graduate', edition='2026', document_kind='submission')
    assert not result['passed']
    assert any('official cover' in e for e in result['errors'])


def test_cover_cannot_replace_the_following_abstract():
    records = submission()
    records[1] = page('正文\n结果。\n1')
    assert any('PDF page 2' in e for e in evaluate(
        records, 'graduate', edition='2026', document_kind='submission')['errors'])


def test_identity_is_permitted_only_on_the_submission_cover():
    records = submission()
    assert evaluate(records, 'graduate', edition='2026', document_kind='submission',
                    forbidden=['某某大学', '26000010001'])['passed']
    records[2] = page('正文\n某某大学\n2')
    assert any('identifying text' in e for e in evaluate(
        records, 'graduate', edition='2026', document_kind='submission',
        forbidden=['某某大学'])['errors'])


def test_ai_policy_is_confirmed_without_certifying_use_compliance():
    facts = evaluate(report(), 'graduate', edition='2026')['facts']
    assert facts['ai_policy_status'] == 'confirmed'
    assert facts['ai_policy_version'] == '2026-09-16'
    assert facts['ai_policy_source'].endswith('fileId=4fc024f7a1504abb87fc056440c64a28')
    assert not facts['ai_use_compliance_checked']


@pytest.mark.parametrize('edition', [None, '2025', True, 2026.0])
def test_unknown_graduate_editions_do_not_inherit_2026(edition):
    with pytest.raises(ValueError, match='edition 2026'):
        evaluate(report(), 'graduate', edition=edition)


def test_actual_cjk_pdf_has_a_cover_followed_by_numbered_abstract(tmp_path):
    pdf = tmp_path/'submission.pdf'
    write_cjk_pdf(pdf, submission())
    records = extract(pdf)
    assert '参赛队号' in records[0]['text']
    result = evaluate(records, 'graduate', edition='2026', document_kind='submission',
                      forbidden=['某某大学', '26000010001'])
    assert result['passed'], result
