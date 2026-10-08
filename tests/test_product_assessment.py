import pytest
from evals.aggregate import user_view
from evals.competitions import lookup


def report(awards):
    return {'A': dict(percent_mean=99, award_estimates=awards, reviews=[{'validity_status': 'unverified'}])}


def award():
    return dict(target='Meritorious', most_likely='Honorable Mention', range=['Successful Participant', 'Meritorious'],
                basis='Conditional numerical checks; structural assumptions unresolved', calibrated=False,
                contest='mcm', event='MCM', edition='2027', problem='synthetic-example', version='draft-1', scope='summary and one calculation only',
                gaps=['No held-out check'], actions=['Check section 3 on a separate scenario; recommendation may change'])


def test_high_diagnostic_cannot_manufacture_an_award():
    result = user_view(report([{'most_likely': 'Outstanding'}]), 'mcm')['A']
    assert not result['assessments'] and result['status'] == 'insufficient_scoped_award_evidence'
    assert 'percent_mean' not in result


def test_scoped_awards_preserve_conflict_and_allow_abstention():
    a = award()
    b = {**award(), 'most_likely': None, 'range': [], 'basis': 'Insufficient model evidence'}
    result = user_view(report([a, b]), 'mcm')['A']
    assert len(result['assessments']) == 2
    assert result['assessments'][0]['target'] == 'Meritorious'
    assert result['assessments'][1]['most_likely'] is None
    assert result['validity'] == ['unverified']


def test_calibration_claim_needs_an_explicit_evidence_reference():
    with pytest.raises(ValueError, match='calibration_evidence'):
        user_view(report([{**award(), 'calibrated': True}]), 'mcm')


def test_cannot_mix_awards_from_another_contest():
    with pytest.raises(ValueError, match='contest'):
        user_view(report([award()]), 'cumcm')
    with pytest.raises(ValueError, match='Award label'):
        user_view(report([{**award(), 'most_likely': '全国一等奖'}]), 'mcm')


def test_peak_hour_objection_changes_stability_not_a_finite_wait_prediction():
    from examples.novice_queue_demo import scenario
    # 80% utilization; Wq = rho/(mu-lambda) hours = .8/12 hours = 4 minutes.
    assert scenario(48, 60)['queue_wait_minutes'] == 4
    assert scenario(0, 60)['queue_wait_minutes'] == 0
    assert scenario(60, 60)['queue_wait_minutes'] is None
    assert not scenario(72, 60)['stable']


def test_unknown_editions_and_subevents_do_not_inherit_compliance():
    known = lookup('mcm', 'MCM', '2027')
    assert known['status']['rules'] == 'partial'
    for result in [lookup('mcm', 'MCM', '2028'), lookup('mcm', 'other', '2027'), lookup('mathorcup', 'main', '2026')]:
        assert result['status']['rules'] == 'unconfirmed'
        assert not result['sources']
        assert result['status']['awards'] == 'uncalibrated'


@pytest.mark.parametrize('target', ['全国一等奖', 'Outstanding', '', 7, False])
def test_target_is_validated_against_the_same_exact_system(target):
    with pytest.raises(ValueError, match='award target|Award label'):
        user_view(report([{**award(), 'target': target}]), 'mcm')


@pytest.mark.parametrize('target', [None, '未设定', 'unset'])
def test_target_unset_is_explicit_and_does_not_become_a_label(target):
    result = user_view(report([{**award(), 'target': target}]), 'mcm')['A']['assessments'][0]
    assert result['target'] is None
    assert result['target_status'] == 'unset'
    assert result['most_likely'] == 'Honorable Mention'


@pytest.mark.parametrize('contest,event,edition', [
    ('mcm', 'MCM', '2028'), ('cumcm', 'undergraduate', '2026'),
    ('mathorcup', 'main', '2026'),
])
def test_missing_edition_award_system_abstains_instead_of_bypassing_validation(contest, event, edition):
    proposal = {**award(), 'contest': contest, 'event': event, 'edition': edition,
                'most_likely': 'an unchecked award label'}
    view = user_view(report([proposal]), contest)['A']
    assessed = view['assessments'][0]
    assert view['status'] == 'award_system_unverified'
    assert assessed['award_system_status'] == 'unverified'
    assert assessed['assessment_status'] == 'abstained_unverified_award_system'
    assert assessed['most_likely'] is None and assessed['range'] == []
    assert assessed['target'] is None and assessed['target_status'] == 'unverified'
    assert assessed['unverified_proposal']['most_likely'] == 'an unchecked award label'


def test_missing_award_system_cannot_be_called_calibrated():
    with pytest.raises(ValueError, match='verified edition award system'):
        user_view(report([{**award(), 'edition': '2028', 'calibrated': True,
                           'calibration_evidence': 'unverified labels are not enough'}]), 'mcm')


def test_distinct_counterexamples_keep_review_scope_source_and_actions(tmp_path):
    import json
    from evals.aggregate import aggregate
    from tests.test_aggregate import audited_item

    first, second = audited_item(), audited_item()
    first.update(reviewer='reader A', award_estimate=award(), scope='feasibility replay only')
    second.update(reviewer='reader B', award_estimate={**award(), 'actions': ['Section 4: correct cost comparison']})
    first['critical_claims'] = [{'id': 'recommendation', 'claim': 'schedule satisfies the capacity bound',
        'status': 'refuted', 'evidence': 'capacity 12 exceeds bound 10', 'scope': 'scenario A',
        'actions': ['Section 3: recalculate the schedule'], 'issue_ids': ['capacity']}]
    first['issues'] = [{'id': 'capacity', 'description': 'capacity omitted', 'evidence': '12 > 10'}]
    second['critical_claims'] = [{'id': 'recommendation', 'claim': 'recommended plan minimizes cost',
        'status': 'refuted', 'evidence': 'alternative cost 8 below claimed minimum 9',
        'scope': 'scenario B', 'actions': ['Section 4: correct cost comparison']}]
    path = tmp_path / 'readers.json'
    path.write_text(json.dumps([first, second]))
    internal = aggregate([path], 'mcm')
    view = user_view(internal, 'mcm')['audited']
    a, b = view['reviews']
    assert a['reviewer'] == 'reader A' and b['reviewer'] == 'reader B'
    assert a['source'] == b['source'] == str(path)
    assert (a['source_record_index'], b['source_record_index']) == (0, 1)
    assert a['scope'] == 'feasibility replay only'
    assert a['critical_claims'][0]['claim'] != b['critical_claims'][0]['claim']
    assert a['critical_claims'][0]['evidence'] == 'capacity 12 exceeds bound 10'
    assert a['critical_claims'][0]['scope'] == 'scenario A'
    assert a['critical_claims'][0]['actions'] == ['Section 3: recalculate the schedule']
    assert a['issues'][0]['id'] == 'capacity'
    for review, assessment in zip(view['reviews'], view['assessments']):
        assert review['award_assessment'] == assessment
        assert review['review_id'] == assessment['review_id']
        assert review['reviewer'] == assessment['reviewer']
    assert b['award_assessment']['actions'] == ['Section 4: correct cost comparison']
    # A root error is exposed, but never changes the declared award by an automatic cap.
    assert a['award_assessment']['most_likely'] == 'Honorable Mention'


def test_legacy_aggregate_with_lost_association_does_not_guess_a_judge():
    result = user_view(report([award(), award()]), 'mcm')['A']
    assert all(a['review_id'] is None for a in result['assessments'])
    assert all(a['association_status'] == 'unavailable_in_legacy_report' for a in result['assessments'])
    assert result['reviews'][0]['award_assessment'] is None


def test_math_audit_without_award_keeps_claims_and_repair_advice(tmp_path):
    import json
    from evals.aggregate import aggregate
    from tests.test_aggregate import audited_item
    item = audited_item()
    item.update(judge='legacy reviewer identity', scope='one arithmetic witness',
                overall_note='Section 2: replace the unsupported assertion')
    item['critical_claims'][0].update(status='unverified', evidence='proof missing')
    path = tmp_path / 'audit.json'
    path.write_text(json.dumps([item]))
    view = user_view(aggregate([path]), 'mcm')['audited']
    assert view['status'] == 'insufficient_scoped_award_evidence'
    assert view['reviews'][0]['critical_claims'][0]['evidence'] == 'proof missing'
    assert view['reviews'][0]['overall_note'] == item['overall_note']
    assert view['reviews'][0]['reviewer'] == 'legacy reviewer identity'
    assert view['reviews'][0]['scope'] == 'one arithmetic witness'


def test_an_explicit_target_alone_is_not_an_award_estimate():
    view = user_view(report([{**award(), 'most_likely': None, 'range': []}]), 'mcm')['A']
    assert view['assessments'][0]['assessment_status'] == 'abstained'
