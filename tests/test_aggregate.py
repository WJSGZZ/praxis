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
