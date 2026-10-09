"""Independent boundary and recovery fixtures for advisor batch B."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from modeling import regression, routes, sensitivity

ROOT = Path(__file__).resolve().parents[1]


def graph():
    g = routes.new_graph('boundary', 'standard')
    routes.add_path(g, 'a', 'candidate')
    routes.add_path(g, 'b', 'alternative')
    routes.attack(g, 'a', 'claim', 'independent check', 'survived', 'old evidence')
    return g


@pytest.mark.parametrize('elimination', ['kill', 'attack', 'merge'])
def test_eliminated_route_requires_explicit_reopen_and_fresh_attack(elimination):
    g = graph()
    if elimination == 'kill':
        routes.kill(g, 'a', 'new counterexample')
    elif elimination == 'attack':
        routes.attack(g, 'a', 'claim', 'counterexample', 'killed', 'new counterexample')
    else:
        routes.merge(g, ['a', 'b'], 'c', 'hybrid', 'combine surviving parts')
    previous = dict(g['paths']['a'])
    with pytest.raises(ValueError, match='killed|merged'):
        routes.choose(g, 'a', 'old success')
    with pytest.raises(ValueError):
        routes.reopen(g, 'a', ' ', 'new independent evidence')
    routes.reopen(g, 'a', 'counterexample premise corrected', 'new independent evidence')
    history = g['paths']['a']['reopen_history'][-1]
    assert history['previous_status'] == previous['status']
    assert history['previous_reason'] == previous['reason']
    with pytest.raises(ValueError, match='no attack'):
        routes.choose(g, 'a', 'premature')
    routes.attack(g, 'a', 'corrected claim', 'new independent check', 'survived', 'new check')
    routes.choose(g, 'a', 'fresh evidence')
    assert not routes.validate(g)
    assert 'counterexample premise corrected' in routes.trace_markdown(g)


def test_reopen_operation_is_available_and_preserves_old_attacks():
    g = graph()
    routes.kill(g, 'a', 'failed')
    result = routes.apply(g, [dict(op='reopen', key='a', reason='corrected assumption', evidence='verified premise')])
    assert result['graph']['attacks'] == g['attacks']
    assert g['paths']['a']['status'] == 'killed'


def test_no_intercept_ols_matches_scalar_normal_equation_without_changing_model():
    x = np.arange(1., 11.)
    y = 2*x + np.array([.1, -.2, .3, -.1, .2, -.3, .1, .2, -.1, .1])
    report = regression.ols_report(x, y, names=['slope'], add_constant=False)
    assert len(report['coefficients']) == report['parameters'] == 1
    assert report['coefficients'][0]['estimate'] == pytest.approx(float(x@y/(x@x)))
    assert report['diagnostics']['breusch_pagan_p'] is None
    assert report['diagnostics']['breusch_pagan']['status'] == 'not_applicable'
    standard = regression.ols_report(x, y)
    assert standard['diagnostics']['breusch_pagan']['status'] == 'computed'
    assert standard['diagnostics']['breusch_pagan_p'] is not None


@pytest.mark.parametrize('names', [[], ['a', 'b']])
def test_ols_refuses_silently_truncated_coefficient_names(names):
    with pytest.raises(ValueError, match='names'):
        regression.ols_report(np.arange(1., 11.), np.arange(1., 11.), names=names)


def test_sobol_budget_is_cumulative_and_rejected_before_any_call():
    calls = []
    def model(x):
        calls.append(len(x))
        return x[:, 0]
    with pytest.raises(ValueError, match='budget'):
        sensitivity.sobol_convergence(model, ['x'], [[0, 1]], n=64, max_evaluations=400)
    assert calls == []
    result = sensitivity.sobol_convergence(model, ['x'], [[0, 1]], n=64, max_evaluations=576)
    assert calls == [192, 384]
    assert result['total_evaluations'] == sum(calls) == 576


def test_sobol_coarse_failure_does_not_start_fine_stage():
    calls = []
    def model(x):
        calls.append(len(x))
        raise RuntimeError('coarse failed')
    with pytest.raises(RuntimeError, match='coarse failed'):
        sensitivity.sobol_convergence(model, ['x'], [[0, 1]], n=64, max_evaluations=576)
    assert calls == [192]


def mesh_module():
    spec = importlib.util.spec_from_file_location('advisor_b_mesh', ROOT/'demos/mcm-2016-a/reproduce/run_mesh_check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('best_ok,buffer_ok', [(True, False), (False, True), (False, False)])
def test_mesh_failed_candidates_retained_without_blocking_valid_one(best_ok, buffer_ok):
    module = mesh_module()
    p = json.loads((ROOT/'demos/mcm-2016-a/reproduce/reference/extended.json').read_text())['parameters']
    p.update(horizon=1., floor=0., ceiling=100., span=100.)
    valid = dict(flow_lpm=[0.], water_l=0.)
    failed = dict(flow_lpm=None, water_l=None, buffer_c=.1)
    result = module.validate_candidates(dict(parameters=p, control=dict(
        best=valid if best_ok else failed,
        buffer_price=[valid if buffer_ok else failed])))
    diagnostics = result['candidate_diagnostics']
    assert len(diagnostics) == 2
    assert [d['accepted'] for d in diagnostics] == [best_ok, buffer_ok]
    for d, ok in zip(diagnostics, [best_ok, buffer_ok]):
        if not ok:
            assert d['error']['type'] == 'no_candidate'
            assert d['flow_lpm'] is None and d['water_l'] is None
    assert bool(result['accepted_schedule']) == (best_ok or buffer_ok)
    if best_ok or buffer_ok:
        assert result['accepted_schedule']['water_l'] == 0
        assert result['accepted_schedule']['source'] == ('best' if best_ok else 'buffer_price[0]')
    else:
        assert not any(c['passed'] for c in result['checks'])


def test_mesh_empty_candidate_record_preserved():
    module = mesh_module()
    p = json.loads((ROOT/'demos/mcm-2016-a/reproduce/reference/extended.json').read_text())['parameters']
    p.update(horizon=1., floor=0., ceiling=100., span=100.)
    result = module.validate_candidates(dict(parameters=p, control=dict(best=None, buffer_price=[None, {}])))
    assert len(result['candidate_diagnostics']) == 3
    assert result['accepted_schedule'] is None
