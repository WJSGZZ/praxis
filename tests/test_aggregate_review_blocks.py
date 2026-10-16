"""Review declarations survive aggregation without becoming an award rubric."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from evals import aggregate as ag


# Fixed pre-C3.4 values: these are diagnostic weights, not fitted award cutoffs.
ORIGINAL_WEIGHTS = {
    'general': {'coverage': 10, 'assumptions': 15, 'model': 15, 'correctness': 25,
                'robustness': 10, 'writing': 10, 'verifiability': 15},
    'cumcm': {'coverage': 10, 'assumptions': 20, 'model': 20, 'correctness': 25,
              'robustness': 5, 'writing': 15, 'verifiability': 5},
    'mcm': {'coverage': 10, 'assumptions': 10, 'model': 15, 'correctness': 20,
            'robustness': 15, 'writing': 20, 'verifiability': 10},
}


def _item(paper='P', reviewer='one'):
    return {'paper': paper, 'reviewer': reviewer,
            'scores': dict(coverage=4, assumptions=3, model=2, correctness=1,
                           robustness=0, writing=4, verifiability=2)}


def _reader(found='yes'):
    return {'type': 'reader', 'actor': 'packet-reader', 'minutes_used': 2.5,
            'problem_items': [{'id': 'P1', 'answer_found': found,
                               'answer_one_line': 'The stated output is 2.',
                               'why_credible': 'Summary p1, not recomputed.',
                               'top_question': 'How was the parameter measured?'}],
            'limitations': ['Presence of an answer does not establish correctness.']}


def _comparison(preferred='reference'):
    return {'reference': {'id': 'R', 'award_source': 'official results p2'},
            'preferred': preferred, 'confidence': 0.75,
            'reasons': ['Self p1 versus reference p1: answer coverage.',
                        'Self p3 versus reference p4: model justification.',
                        'Self p5 versus reference p6: uncertainty treatment.'],
            'focus': 'Coverage, model choice, evidence and readability.',
            'scope': {'version': 'sha256:declared', 'pages': [1, 3, 5]}}


def _write(tmp_path, items):
    path = tmp_path / 'reviews.json'
    path.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
    return path


@pytest.mark.parametrize('contest,expected', [('general', 52.5), ('cumcm', 58.75), ('mcm', 55)])
def test_diagnostic_flag_preserves_hand_computed_weights_and_no_award(tmp_path, contest, expected):
    # E.g. general: 10 + 11.25 + 7.5 + 6.25 + 0 + 10 + 7.5 = 52.5.
    result = ag.aggregate([_write(tmp_path, [_item()])], contest)['P']
    assert result['diagnostic_only'] is True
    assert result['weights'] == ORIGINAL_WEIGHTS[contest]
    assert ag.percent(_item()['scores'], ORIGINAL_WEIGHTS[contest]) == expected
    assert result['percent_each'] == [round(expected, 1)]
    assert result['award_estimates'] == []
    user = ag.user_view({'P': result}, contest)['P']
    assert user['assessments'] == []
    assert user['status'] == 'insufficient_scoped_award_evidence'
    assert 'percent_mean' not in user


def test_every_profile_marks_weight_role_without_changing_any_value():
    assert set(ag.PROFILES) == set(ORIGINAL_WEIGHTS)
    for contest, profile in ag.PROFILES.items():
        assert profile['weights'] == ORIGINAL_WEIGHTS[contest]
        assert profile['diagnostic_only'] is True
        assert '诊断权重，不参与奖档' in profile['weights_usage']


@pytest.mark.parametrize('many', [False, True])
def test_optional_blocks_and_severity_are_kept_per_reviewer_without_scoring(tmp_path, many):
    first, second = _item(reviewer='first'), _item(reviewer='second')
    first['reader'], second['reader'] = _reader(), _reader('no')
    first['comparison'] = [_comparison(), _comparison('self')] if many else _comparison()
    second['comparison'] = []  # No comparison was made; do not infer one.
    for item, severity in ((first, 'decisive'), (second, 'local')):
        item['issues'] = [{'id': 'i', 'description': 'Reviewer-scoped finding',
                           'evidence': 'p3 and arithmetic witness', 'severity': severity,
                           'actions': ['Check the affected answer.']}]
    originals = copy.deepcopy([first, second])
    internal = ag.aggregate([_write(tmp_path, originals)])['P']
    user = ag.user_view({'P': internal})['P']
    assert internal['percent_each'] == [52.5, 52.5]
    assert internal['award_estimates'] == user['assessments'] == []
    for index, item in enumerate(originals):
        for field in ('reader', 'comparison', 'issues'):
            assert internal['reviews'][index][field] == item[field]
            assert user['reviews'][index][field] == item[field]
        assert user['reviews'][index]['reviewer'] == item['reviewer']
        assert user['reviews'][index]['review_id'] == f'review-{index + 1}'
    assert [first, second] == originals


def test_absent_optional_blocks_and_ungraded_legacy_issues_stay_absent(tmp_path):
    item = _item()
    item['issues'] = [{'id': 'old', 'description': 'Archived finding', 'evidence': 'p2'}]
    report = ag.aggregate([_write(tmp_path, [item])])
    for record in (report['P']['reviews'][0], ag.user_view(report)['P']['reviews'][0]):
        assert 'reader' not in record and 'comparison' not in record
        assert record['issues'] == item['issues'] and 'severity' not in record['issues'][0]


@pytest.mark.parametrize('extension', [
    {'reader': None}, {'reader': []}, {'reader': 'reader output'},
    {'reader': {'problem_items': {}}}, {'reader': {'problem_items': ['P1']}},
    {'reader': {'problem_items': [{'answer_found': True}]}},
    {'comparison': None}, {'comparison': 'self wins'}, {'comparison': [False]},
    {'comparison': {'preferred': 'O'}}, {'comparison': {'confidence': True}},
    {'comparison': {'confidence': 0.49}}, {'comparison': {'confidence': 1.01}},
    {'comparison': {'confidence': float('nan')}},
    {'comparison': {'reasons': 'p1, p2, p3'}},
    {'comparison': {'reasons': ['p1', ' ']}},
])
def test_malformed_optional_declarations_are_refused(extension, tmp_path):
    item = _item()
    item.update(extension)
    with pytest.raises(ValueError, match='reader|comparison'):
        ag.aggregate([_write(tmp_path, [item])])


@pytest.mark.parametrize('severity', [None, True, 1, 'major', 'DECISIVE', ''])
def test_present_severity_must_use_documented_enum(severity, tmp_path):
    item = _item()
    item['issues'] = [{'id': 'i', 'description': 'Finding', 'evidence': 'p1', 'severity': severity}]
    with pytest.raises(ValueError, match='severity'):
        ag.aggregate([_write(tmp_path, [item])])


def test_optional_blocks_are_declarations_not_completeness_certificates(tmp_path):
    item = _item()
    item.update(reader={'problem_items': [], 'scope': 'Not performed'},
                comparison={'scope': 'No reference available'})
    result = ag.user_view(ag.aggregate([_write(tmp_path, [item])]))['P']
    assert result['reviews'][0]['reader'] == item['reader']
    assert result['reviews'][0]['comparison'] == item['comparison']
    assert result['assessments'] == []


def test_archived_research_severity_is_not_reclassified_by_competition_enum():
    # This is an existing, frozen research label, not a fourth competition grade.
    path = Path(__file__).resolve().parents[1] / 'demos/domino-research/evaluation.json'
    original = json.loads(path.read_text(encoding='utf-8'))[0]
    result = ag.user_view(ag.aggregate([path]))[original['paper']]
    assert result['reviews'][0]['issues'] == original['issues']
    assert result['reviews'][0]['issues'][0]['severity'] == 'nonblocking'


def test_existing_cli_user_view_keeps_blocks_and_unicode(tmp_path):
    item = _item()
    item['reader'] = _reader()
    item['reader']['actor'] = '逐问阅读者'
    item['comparison'] = _comparison()
    result = subprocess.run([sys.executable, '-m', 'evals.aggregate',
                             '--contest=mcm', '--view=user', str(_write(tmp_path, [item]))],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    review = json.loads(result.stdout)['P']['reviews'][0]
    assert review['reader'] == item['reader']
    assert review['comparison'] == item['comparison']
    assert result.stderr == ''
