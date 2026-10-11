"""Thin edition adapters cannot invent unconfirmed policy or inherit another year."""
import json
from pathlib import Path

import pytest

from evals.competitions import lookup
from evals.aggregate import _award_view
from scripts.contest_rules import evaluate


def page(text, size=12):
    return {'text': text, 'lines': text.splitlines(), 'body_size': size}


def test_graduate_invitation_and_format_have_separate_verified_sources():
    record = lookup('graduate', 'main', '2026')
    assert record['status'] == {'rules': 'partial', 'workflow': 'not_validated', 'awards': 'uncalibrated'}
    assert any(source.get('sha256') and 'downFile.do' in source['url'] for source in record['sources'])
    assert any('2c90801ca06f016101a0a47e06b77d9b' in source['url'] for source in record['sources'])
    assert record['ai'].startswith('Confirmed 2026-09-16 policy:') and record['format']['page_limit'] is None
    assert record['submission']['md5_window'][1] < record['submission']['pdf_window'][0]
    assert '三等奖' in record['award_system'] and 'defense' in record['defense']


def test_historical_award_labels_do_not_certify_rules_or_calibration():
    record = lookup('mcm', 'MCM', '2024')
    assert record['status'] == {'rules': 'unconfirmed', 'workflow': 'not_validated', 'awards': 'uncalibrated'}
    assert 'deliverables' not in record and 'ai' not in record
    assert '2024_MCM_Problem_B_Results.pdf' in record['sources'][0]['url']
    award = dict(contest='mcm', event='MCM', edition='2024', problem='B',
        version='actual-version', scope='explicit review scope', target='Outstanding Winner',
        most_likely='Finalist', range=['Meritorious', 'Finalist'], calibrated=False,
        basis='Scoped reviewer judgment, no award probability', gaps=[], actions=[])
    view = _award_view(award, 'mcm')
    assert view['award_system_status'] == 'verified' and view['most_likely'] == 'Finalist'
    assert view['calibrated'] is False
    # A results record neither licenses another edition nor accepts foreign labels.
    assert lookup('mcm', 'MCM', '2023')['status']['rules'] == 'unconfirmed'
    assert _award_view(dict(award, edition='2099'), 'mcm')['most_likely'] is None
    with pytest.raises(ValueError, match='exact contest edition'):
        _award_view(dict(award, most_likely='全国一等奖'), 'mcm')


@pytest.mark.parametrize('event,edition', [('main', '2027'), ('other', '2026'), ('main', None)])
def test_graduate_unknown_identity_does_not_inherit_2026(event, edition):
    assert lookup('graduate', event, edition)['status']['rules'] == 'unconfirmed'
    with pytest.raises(ValueError, match='exact supported edition'):
        evaluate([], 'graduate', edition=edition if edition != '2026' else None)


def test_graduate_abstract_guidance_is_not_a_cumcm_page_limit():
    records = [page('题目\n摘要\n内容\n1'), page('摘要续\n关键词：甲\n2')]
    records += [page(f'正文\n内容\n{i}') for i in range(3, 40)]
    report = evaluate(records, 'graduate', edition='2026')
    assert report['passed'] and report['facts']['page_limit'] is None
    assert report['facts']['ai_policy_status'] == 'confirmed'
    assert report['facts']['ai_policy_version'] == '2026-09-16'
    assert not any('keywords' in w or 'page-number' in w for w in report['warnings'])
    assert any('Not checked mechanically' in w for w in report['warnings'])
    assert evaluate([page('正文\n1')], 'graduate', edition='2026')['errors']


def test_graduate_size_and_footer_are_scoped_warnings():
    report = evaluate([page('摘要\n关键词：甲\n1'), page('正文\n9', 10)], 'graduate', edition='2026')
    assert any('bottom page-number' in w for w in report['warnings'])
    assert any('equations' in w for w in report['warnings'])


def test_cumcm_ai_policy_replaces_stale_source_without_rewriting_history():
    record = lookup('cumcm', 'undergraduate', '2026')
    assert record['ai_requirements']['team_led_core'] is True
    assert record['ai_requirements']['details_file_if_used'] == 'AI工具使用详情.pdf'
    assert any('fef94648' in s['url'] for s in record['sources'])
    profiles = json.loads((Path(__file__).resolve().parents[1]/'evals/profiles.json').read_text())
    assert '2026' in profiles['cumcm']['rules_source']
    assert 'historical' in profiles['cumcm']['rules_source_note']
    assert 'format2019.doc' in profiles['cumcm']['rules_source_sha256']
