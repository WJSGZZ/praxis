import json

import pytest

from evals import aggregate as ag


def judge(paper, **scores):
    base = dict.fromkeys(ag.WEIGHTS, 2)
    base.update(scores)
    return dict(paper=paper, scores=base)


def test_percent_and_spread(tmp_path):
    assert ag.percent(dict.fromkeys(ag.WEIGHTS, 4)) == 100 and ag.percent(dict.fromkeys(ag.WEIGHTS, 0)) == 0
    assert abs(ag.percent(dict.fromkeys(ag.WEIGHTS, 2)) - 50) < 1e-9
    (tmp_path / 'a.json').write_text(json.dumps([judge('P', correctness=4), judge('Q')]))
    (tmp_path / 'b.json').write_text(json.dumps([judge('P', correctness=2), judge('Q')]))
    out = ag.aggregate([tmp_path / 'a.json', tmp_path / 'b.json'])
    assert out['P']['judges'] == 2 and out['P']['unstable_dimensions'] == ['correctness'] and out['P']['percent_range'] == 12.5
    assert out['Q']['percent_mean'] == 50 and out['Q']['unstable_dimensions'] == []
    with pytest.raises(ValueError):
        ag.percent({'coverage': 5, **{k: 2 for k in ag.WEIGHTS if k != 'coverage'}})
    with pytest.raises(ValueError):
        ag.percent({'coverage': 2})


def test_checklist_scores_and_adjust_rules(tmp_path):
    import json
    from evals import aggregate as ag
    dims = list(ag.WEIGHTS)
    def full(met_share):
        return {d: {f'{d}{i}': {'met': i < met_share, 'evidence': 'p1'} for i in range(4)} for d in dims}
    item = {'paper': 'A', 'checklist': full(3)}
    assert set(ag.dimension_scores(item).values()) == {3.0}
    item['adjust'] = {'model': {'value': 1, 'reason': 'insight beyond the routine route'}}
    assert ag.dimension_scores(item)['model'] == 4.0
    item['adjust'] = {'model': {'value': 1, 'reason': ''}}
    import pytest
    with pytest.raises(ValueError):
        ag.dimension_scores(item)
    item['adjust'] = {'model': {'value': 2, 'reason': 'too much'}}
    with pytest.raises(ValueError):
        ag.dimension_scores(item)
    (tmp_path / 'j.json').write_text(json.dumps([{'paper': 'A', 'checklist': full(4)}, {'paper': 'B', 'scores': {d: 2 for d in dims}}]))
    out = ag.aggregate([tmp_path / 'j.json'])
    assert out['A']['percent_mean'] == 100.0 and out['B']['percent_mean'] == 50.0


def test_contest_weights_sum_to_100_and_change_the_score():
    from evals import aggregate as ag
    for w in ag.CONTEST_WEIGHTS.values():
        assert sum(w.values()) == 100 and set(w) == set(ag.WEIGHTS)
    scores = {d: 2 for d in ag.WEIGHTS}
    scores['writing'] = 4
    assert ag.percent(scores, ag.CONTEST_WEIGHTS['mcm']) > ag.percent(scores, ag.CONTEST_WEIGHTS['cumcm'])


def test_every_profile_is_complete_and_unknown_contests_are_refused():
    import pytest
    from evals import aggregate as ag
    for name, profile in ag.PROFILES.items():
        assert sum(profile['weights'].values()) == 100 and set(profile['weights']) == set(ag.WEIGHTS), name
        assert profile['source'] and profile['checked'], name
    assert ag.PROFILES['general']['weights'] == ag.WEIGHTS
    with pytest.raises(ValueError, match='No profile'):
        ag.aggregate([], 'imc')


def test_award_estimates_are_passed_through(tmp_path):
    import json
    from evals import aggregate as ag
    est = {'most_likely': '省一', 'range': ['省二', '国二'], 'basis': 'x', 'calibrated': False}
    (tmp_path / 'j.json').write_text(json.dumps([{'paper': 'A', 'scores': {d: 3 for d in ag.WEIGHTS}, 'award_estimate': est}]))
    assert ag.aggregate([tmp_path / 'j.json'])['A']['award_estimates'] == [est]


def audited_item():
    return {
        'schema_version': 2, 'paper': 'audited',
        'checklist': {dim: {key: {'met': True, 'reviewed': True, 'evidence': 'independent record p1'}
                            for key in keys} for dim, keys in ag.CHECKLIST_IDS.items()},
        'critical_claims': [{'id': 'answer', 'claim': 'x = 2 solves x + 1 = 3',
                             'status': 'supported', 'evidence': 'substitution: 2 + 1 = 3'}],
    }


def test_na_and_unreviewed_have_different_denominators(tmp_path):
    item = audited_item()
    # Hand calculation: robustness 2/3 -> 8/3 -> 2.5; writing 4/5 -> 3.2 -> 3.
    item['checklist']['robustness']['R2'] = {
        'met': None, 'reviewed': True, 'reason': 'no fitted parameters', 'evidence': 'p2 fixed-input table'}
    item['checklist']['robustness']['R3']['met'] = False
    item['checklist']['writing']['W5'] = {
        'met': False, 'reviewed': False, 'reason': 'language review not performed', 'evidence': 'only numerical audit available'}
    scores = ag.dimension_scores(item)
    assert scores['robustness'] == 2.5 and scores['writing'] == 3
    # Remaining weights 80 at 4/4; R contributes 6.25, W contributes 7.5.
    assert ag.percent(scores) == 93.75
    path = tmp_path / 'review.json'
    path.write_text(json.dumps([item]))
    report = ag.aggregate([path])['audited']
    assert report['percent_mean'] == 93.8
    assert report['reviews'][0]['not_applicable_items'] == ['robustness/R2']
    assert report['reviews'][0]['unreviewed_items'] == ['writing/W5']


@pytest.mark.parametrize('mutation', [
    lambda x: x['checklist']['coverage'].pop('C4'),
    lambda x: x['checklist']['coverage']['C1'].pop('met'),
    lambda x: x['checklist']['coverage']['C1'].pop('reviewed'),
    lambda x: x['checklist']['coverage']['C1'].update(met='false'),
    lambda x: x['checklist']['coverage']['C1'].update(met=1),
    lambda x: x['checklist']['coverage']['C1'].update(evidence=' '),
    lambda x: x['checklist']['coverage']['C1'].update(reviewed=False, reason='not checked'),
    lambda x: x['checklist']['robustness']['R2'].update(met=None),
    lambda x: x['checklist']['robustness']['R2'].update(met=None, reviewed=False, reason='unknown'),
    lambda x: x['checklist']['coverage']['C1'].update(met=False, reviewed=False),
    lambda x: x.update(adjust={'model': {'value': True, 'reason': 'not a number'}}),
    lambda x: x.update(adjust={'model': {'value': float('nan'), 'reason': 'invalid'}}),
])
def test_malformed_or_unsubstantiated_checklist_is_refused(mutation):
    item = audited_item()
    mutation(item)
    with pytest.raises(ValueError):
        ag.dimension_scores(item)


def test_whole_dimension_na_does_not_reweight_and_checklist_cannot_be_bypassed():
    item = audited_item()
    for entry in item['checklist']['robustness'].values():
        entry.update(met=None, reason='claimed out of scope')
    item['scores'] = dict.fromkeys(ag.WEIGHTS, 4)
    with pytest.raises(ValueError, match='no applicable'):
        ag.dimension_scores(item)


def test_explicit_half_up_rounding():
    # Nine of sixteen = 2.25/4, exactly between 2 and 2.5.
    legacy = {'checklist': {dim: {str(i): {'met': i < 9, 'evidence': 'p1'}
                                 for i in range(16)} for dim in ag.WEIGHTS}}
    assert set(ag.dimension_scores(legacy).values()) == {2.5}


@pytest.mark.parametrize('value', [True, '4', float('nan'), float('inf'), None, -0.1, 4.1])
def test_direct_legacy_scores_reject_invalid_numeric_values(value):
    with pytest.raises(ValueError):
        ag.dimension_scores(judge('legacy', correctness=value))


def test_counterexample_is_retained_separately_from_high_diagnostic_score(tmp_path):
    item = audited_item()
    # Independent arithmetic witness: 1.523595 > 1.5 + 0.002.
    assert 1.523595 - (1.5 + 0.002) == pytest.approx(0.021595)
    item['critical_claims'] = [{'id': 'feasible', 'claim': 'recommended schedule satisfies spread bound',
        'status': 'refuted', 'evidence': 'replay: 1.523595 > 1.502', 'issue_ids': ['mesh']}]
    item['issues'] = [{'id': 'mesh', 'description': 'fine-grid replay violates bound',
                       'evidence': '1.523595 > 1.502'}]
    for dim, key in [('correctness', 'K3'), ('correctness', 'K4'), ('robustness', 'R3'), ('verifiability', 'V4')]:
        item['checklist'][dim][key].update(met=False, evidence='same mesh counterexample', issue_ids=['mesh'])
    item['award_estimate'] = {'most_likely': 'H', 'range': ['SP', 'M'], 'calibrated': False}
    path = tmp_path / 'counterexample.json'
    path.write_text(json.dumps([item]))
    report = ag.aggregate([path])['audited']
    # K=2.5, R=3, V=3. 25*2.5/4 + 10*3/4 + 15*3/4 + 50 = 84.375.
    assert report['percent_mean'] == 84.4
    assert report['reviews'][0]['validity_status'] == 'refuted'
    assert len(report['reviews'][0]['issues']) == 1
    assert report['award_estimates'] == [item['award_estimate']]


@pytest.mark.parametrize('mutation', [
    lambda x: x.pop('critical_claims'),
    lambda x: x.update(critical_claims='missing'),
    lambda x: x.update(issues={'id': 'wrong shape'}),
    lambda x: x.update(issues=[{'id': 'a', 'description': 'x', 'evidence': 'p1'},
                               {'id': 'a', 'description': 'y', 'evidence': 'p2'}]),
    lambda x: x['critical_claims'][0].update(evidence=''),
    lambda x: x['critical_claims'][0].update(status='correct'),
    lambda x: x['critical_claims'][0].update(issue_ids=['undeclared']),
    lambda x: x['checklist']['correctness']['K4'].update(issue_ids=['undeclared']),
])
def test_invalid_claim_evidence_and_dangling_issue_ids_are_refused(mutation):
    item = audited_item()
    mutation(item)
    with pytest.raises(ValueError):
        ag.review_record(item)


def test_unknown_claim_does_not_become_supported_and_legacy_is_not_certified(tmp_path):
    item = audited_item()
    item['critical_claims'][0].update(status='unverified', evidence='replay missing for this claim')
    path = tmp_path / 'mixed.json'
    path.write_text(json.dumps([item, judge('old')]))
    report = ag.aggregate([path])
    assert report['audited']['percent_mean'] == 100
    assert report['audited']['reviews'][0]['validity_status'] == 'unverified'
    assert report['old']['percent_mean'] == 50
    assert report['old']['reviews'][0]['validity_status'] == 'not_assessed'
    assert report['old']['reviews'][0]['score_source'] == 'legacy_direct'
