"""Known-answer and brute-force checks for the nonlinear, decision-process and inference tools."""
import itertools

import numpy as np
import pytest

from modeling import inference, nonlinear


def test_nlp_known_optimum_and_multimodal():
    # min (x-1)^2+(y-2)^2 s.t. x+y<=2  -> projection onto half-plane: (0.5, 1.5), value 0.5
    r = nonlinear.minimize_nlp(lambda v: (v[0] - 1) ** 2 + (v[1] - 2) ** 2, [[-5, 5], [-5, 5]], [dict(type='ineq', fun=lambda v: 2 - v[0] - v[1])], starts=8)
    assert r['x'] == pytest.approx([.5, 1.5], abs=1e-5) and r['value'] == pytest.approx(.5, abs=1e-7) and r['active_constraints'] == [0]
    # a multimodal function: several local optima must be listed, best one is the global
    r = nonlinear.minimize_nlp(lambda v: np.sin(3 * v[0]) + .1 * v[0] ** 2, [[-4, 4]], starts=30)
    assert len(r['distinct_optima']) >= 2 and r['value'] == pytest.approx(min(np.sin(3 * x) + .1 * x * x for x in np.linspace(-4, 4, 200001)), abs=1e-5)


def test_nlp_infeasible_reported():
    r = nonlinear.minimize_nlp(lambda v: v[0], [[0, 1]], [dict(type='ineq', fun=lambda v: -1 - v[0])], starts=4)
    assert r['feasible'] is False


def test_knapsack_matches_enumeration():
    rng = np.random.default_rng(1)
    for _ in range(20):
        n = 8
        v, w = rng.integers(1, 30, n).tolist(), rng.integers(1, 12, n).tolist()
        cap = int(rng.integers(5, 40))
        best = max(sum(vi for vi, s in zip(v, sel) if s) for sel in itertools.product([0, 1], repeat=n) if sum(wi for wi, s in zip(w, sel) if s) <= cap)
        r = nonlinear.knapsack(v, w, cap)
        assert r['value'] == best and r['weight'] <= cap


def test_min_cost_flow_small():
    # supply 2 at a, demand 2 at d; cheap path a-b-d has capacity 1, the other a-c-d costs more
    r = nonlinear.min_cost_flow([['a', 'b', 1, 1], ['b', 'd', 1, 1], ['a', 'c', 5, 2], ['c', 'd', 5, 2]], {'a': -2, 'b': 0, 'c': 0, 'd': 2})
    assert r['cost'] == 2 + 4 and r['feasible']
    assert nonlinear.min_cost_flow([['a', 'd', 1, 1]], {'a': -2, 'd': 2})['feasible'] is False


def test_robust_lp_limits_and_worst_case():
    c, A, b = [3, 2], [[1, 1], [2, 1]], [10, 15]
    delta = [[.5, .5], [.4, .2]]
    nominal = nonlinear.robust_lp(c, A, b, delta, 0, maximize=True)['value']
    from scipy.optimize import linprog
    assert nominal == pytest.approx(-linprog([-3, -2], A_ub=A, b_ub=b).fun)
    full = nonlinear.robust_lp(c, A, b, delta, 2, maximize=True)
    box = -linprog([-3, -2], A_ub=(np.array(A) + np.array(delta)), b_ub=b).fun
    assert full['value'] == pytest.approx(box)
    mid = nonlinear.robust_lp(c, A, b, delta, 1, maximize=True)
    assert box - 1e-9 <= mid['value'] <= nominal + 1e-9
    # every realisation with at most gamma=1 coefficient per row at its worst case is satisfied
    x = np.array(mid['x'])
    for i in range(2):
        for j in range(2):
            row = np.array(A[i], float); row[j] += delta[i][j]
            assert row @ x <= b[i] + 1e-7


def test_mdp_backward_induction_equals_brute_force():
    rng = np.random.default_rng(3)
    ns, na, T = 3, 2, 3
    P = rng.random((na, ns, ns)); P /= P.sum(2, keepdims=True)
    R = rng.random((ns, na))
    r = nonlinear.solve_mdp(P, R, horizon=T)
    best = np.full(ns, -np.inf)
    # enumerate every stage-dependent deterministic policy and evaluate by forward distributions
    for pol in itertools.product(range(na), repeat=ns * T):
        pol = np.array(pol).reshape(T, ns)
        V = np.zeros(ns)
        for t in range(T):          # stage t from the end uses pol[t]
            V = np.array([R[s, pol[t, s]] + P[pol[t, s], s] @ V for s in range(ns)])
        best = np.maximum(best, V)
    assert np.allclose(r['value'], best)


def test_mdp_value_iteration_fixed_point():
    P = [[[.9, .1], [.2, .8]], [[.5, .5], [.5, .5]]]
    R = [[1, 0], [0, 2]]
    r = nonlinear.solve_mdp(P, R, discount=.9)
    V = np.array(r['value'])
    Q = np.array([[R[s][a] + .9 * np.array(P[a][s]) @ V for a in range(2)] for s in range(2)])
    assert np.allclose(V, Q.max(1), atol=1e-8)


def test_hypothesis_tests_against_hand_values():
    a, b = [5.1, 4.9, 5.6, 5.8, 6.0, 5.3], [4.2, 4.8, 4.5, 5.0, 4.4, 4.7]
    r = inference.hypothesis_test('welch_t', a, b)
    from scipy import stats
    assert r['p'] == pytest.approx(stats.ttest_ind(a, b, equal_var=False).pvalue) and r['significant'] and r['effect_size_cohen_d'] > 1
    t = [[30, 10], [10, 30]]
    c = inference.hypothesis_test('chi2_independence', None, table=t)
    assert c['effect_size_cramers_v'] == pytest.approx(.5) and c['flags'] == []
    assert inference.hypothesis_test('chi2_independence', None, table=[[2, 1], [1, 3]])['flags']
    with pytest.raises(ValueError):
        inference.hypothesis_test('nope', a, b)


def test_bootstrap_covers_true_mean():
    rng = np.random.default_rng(5)
    hits = 0
    for s in range(60):
        x = rng.normal(10, 3, 40)
        lo, hi = inference.bootstrap_ci(x, 'mean', n_resamples=500, seed=s)['ci']
        hits += lo <= 10 <= hi
    assert 0.85 <= hits / 60 <= 1.0       # nominal 95%; wide tolerance for 60 trials


def test_monte_carlo_known_moments():
    r = inference.monte_carlo(lambda s: s['a'] + 2 * s['b'], dict(a=dict(dist='norm', params=dict(loc=1, scale=1)), b=dict(dist='uniform', params=dict(loc=0, scale=1))), n=200000, threshold=3)
    assert r['mean'] == pytest.approx(2.0, abs=4 * r['mc_standard_error']) and r['settled']
    assert r['sd'] == pytest.approx(np.sqrt(1 + 4 / 12), rel=.01)
    # P(a + 2b > 3) estimated against numerical integration
    from scipy import integrate, stats
    exact = integrate.quad(lambda b: stats.norm.sf(3 - 2 * b, loc=1), 0, 1)[0]
    lo, hi = r['exceedance']['ci']
    assert lo <= exact <= hi


def test_solve_ode_exponential_and_event():
    r = inference.solve_ode(lambda t, y: -y, [1.0], [0, 5], t_eval=[1, 2, 5])
    assert np.allclose(r['y'][0], np.exp([-1, -2, -5]), atol=1e-6) and r['tolerance_check_max_difference'] < 1e-6
    ev = lambda t, y: y[0] - .5
    ev.terminal = True
    r = inference.solve_ode(lambda t, y: -y, [1.0], [0, 5], events=ev)
    assert r['events'][0]['t'][0] == pytest.approx(np.log(2), abs=1e-6)


def test_arima_recovers_ar1_and_forecast_shape():
    rng = np.random.default_rng(7)
    y = np.zeros(300)
    for t in range(1, 300):
        y[t] = .7 * y[t - 1] + rng.normal()
    r = inference.arima_forecast(y + 50, 5, max_p=2, max_d=1, max_q=1)
    assert len(r['forecast']) == 5 and r['order'][1] == 0 and r['residuals_white']


def test_pca_and_cluster():
    rng = np.random.default_rng(9)
    z = rng.normal(size=200)
    X = np.c_[z, 2 * z + .01 * rng.normal(size=200), rng.normal(size=200)]
    p = inference.pca_report(X)
    assert p['explained_ratio'][0] > .6 and sum(p['explained_ratio']) == pytest.approx(1)
    blobs = np.r_[rng.normal(0, .3, (60, 2)), rng.normal(4, .3, (60, 2)), rng.normal([0, 5], .3, (60, 2))]
    c = inference.cluster_report(blobs, (2, 3, 4, 5))
    assert c['best_k'] == 3 and c['stability_ari_mean'] > .9


def test_ode_default_common_time_comparison_matches_closed_form():
    result = inference.solve_ode(lambda t, y: -y, [1.], [0., 5.])
    assert np.max(np.abs(np.asarray(result['y'])[0] - np.exp(-np.asarray(result['t'])))) < 1e-6
    assert result['tolerance_check_max_difference'] < 1e-6
    check = result['tolerance_check']
    assert check['common_interval'] == [0., 5.]
    assert check['times'][0] == 0. and check['times'][-1] == 5.
    backward = inference.solve_ode(lambda t, y: -y, [np.exp(-5.)], [5., 0.])
    assert backward['tolerance_check_max_difference'] < 1e-6
    assert backward['y'][0][-1] == pytest.approx(1., abs=1e-6)


def test_ode_event_overlap_never_extrapolates_even_without_output_samples():
    event = lambda t, y: y[0] - .5
    event.terminal = True
    for grid in (None, [.1, 1., 3.], [1., 3.]):
        result = inference.solve_ode(lambda t, y: -y, [1.], [0., 5.], t_eval=grid, events=event)
        check = result['tolerance_check']
        first_end = result['events'][0]['t'][0]
        second_end = result['tighter_events'][0]['t'][0]
        assert check['common_interval'][1] == min(first_end, second_end)
        assert max(check['times']) <= min(first_end, second_end)
        assert first_end == pytest.approx(np.log(2), abs=1e-6)
        assert result['tolerance_check_max_difference'] < 1e-6
    # A failed integration cannot masquerade as a successful sensitivity check.
    with pytest.raises(RuntimeError):
        inference.solve_ode(lambda t, y: y * y, [1.], [0., 2.], method='RK45')
