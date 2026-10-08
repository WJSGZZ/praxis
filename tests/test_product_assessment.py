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
