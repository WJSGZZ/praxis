import pytest

from modeling import lessons


def sample(**kw):
    base = dict(problem='cooling bath, minimise added water', structure='energy balance + monotone loss', recognized='loss grows with temperature',
                routes_tried=['simulation only', 'ODE with lower bound'], what_failed='simulation gave no optimality evidence',
                what_worked='coast then hold, proved by monotonicity', verified_by='independent ODE integration', principle='if loss is monotone in state, delay the control',
                tags=['ode', 'control'])
    base.update(kw)
    return base


def test_add_search_and_patterns(tmp_path):
    f = tmp_path / 'planning' / 'lessons.jsonl'
    assert lessons.add_lesson(f, sample())['id'] == 'L0001'
    second = lessons.add_lesson(f, sample(problem='portfolio with fees', structure='piecewise cost + relaxation', tags=['milp'], evidence='derived',
                                                  recognized='fee jumps at a threshold', principle='relax the kink to get a bound', what_worked='MILP with relaxation bound', routes_tried=['greedy']))
    assert second['id'] == 'L0002'
    hits = lessons.search_lessons(f, 'monotone loss delay control')
    assert hits[0]['id'] == 'L0001'
    assert lessons.search_lessons(f, tags=['MILP'])[0]['id'] == 'L0002'
    assert lessons.search_lessons(f, 'zebra') == []
    lessons.add_lesson(f, sample(problem='another cooling task'))
    out = lessons.patterns(f)
    assert out['lessons'] == 3 and out['repeated_structures'] == {'energy balance + monotone loss': 2}


def test_incomplete_or_unknown_evidence_is_rejected(tmp_path):
    f = tmp_path / 'l.jsonl'
    with pytest.raises(ValueError, match='principle'):
        lessons.add_lesson(f, sample(principle='  '))
    with pytest.raises(ValueError, match='evidence'):
        lessons.add_lesson(f, sample(evidence='felt right'))
    assert not f.exists()
