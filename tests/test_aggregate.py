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
