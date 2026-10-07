"""Each tool is checked against an answer derived independently of its implementation."""
import itertools
import math

import numpy as np
import pytest

from modeling.weights import ahp, entropy_weights
from modeling.optimize import solve_lp, solve_milp
from modeling.graph import shortest_path, max_flow, minimum_spanning_tree
from modeling.queueing import mmc
from modeling.epidemic import simulate_sir, final_size, fit_sir
from modeling.forecast import gm11, rolling_origin


def test_ahp_recovers_weights_of_a_consistent_matrix_and_flags_a_bad_one():
    w = np.array([.5, .3, .2])
    result = ahp(np.outer(w, 1 / w))
    assert np.allclose(result['weights'], w) and abs(result['consistency_ratio']) < 1e-9
    bad = ahp([[1, 9, 1 / 9], [1 / 9, 1, 9], [9, 1 / 9, 1]])  # cyclic preferences
    assert not bad['acceptable']
    with pytest.raises(ValueError):
        ahp([[1, 2], [2, 1]])  # not reciprocal


def test_entropy_weights_give_zero_to_a_constant_column_and_more_to_the_spread_one():
    x = [[1, 5, 3], [1, 5, 4], [1, 5, 9], [1, 6, 5]]
    result = entropy_weights(x)
    assert result['weights'][0] == 0 and result['columns_without_spread'] == [0]
    assert abs(sum(result['weights']) - 1) < 1e-12
    with pytest.raises(ValueError):
        entropy_weights([[1, 1], [1, 1]])


def test_lp_textbook_optimum_and_duality_certificate():
    # max 3x + 2y  s.t. x + y <= 4, x + 3y <= 6, x <= 3  ->  x=3, y=1, value 11
    r = solve_lp([3, 2], A_ub=[[1, 1], [1, 3]], b_ub=[4, 6], bounds=[(0, 3), (0, None)], maximize=True)
    assert r['success'] and r['certified']
    assert np.allclose(r['x'], [3, 1]) and abs(r['objective'] - 11) < 1e-9


def test_lp_infeasible_is_reported_not_hidden():
    r = solve_lp([1], A_ub=[[1], [-1]], b_ub=[1, -2])
    assert not r['success']


def test_milp_knapsack_matches_brute_force():
    values, weights, cap = [10, 13, 7, 8, 4], [5, 7, 4, 5, 3], 12
    r = solve_milp(values, A_ub=[weights], b_ub=[cap], bounds=[(0, 1)] * 5, integrality=[1] * 5, maximize=True)
    best = max(sum(v for v, s in zip(values, pick) if s) for pick in itertools.product([0, 1], repeat=5)
               if sum(w for w, s in zip(weights, pick) if s) <= cap)
    assert r['proved_optimal'] and abs(r['objective'] - best) < 1e-9


def test_graph_tools():
    edges = [['a', 'b', 4], ['a', 'c', 1], ['c', 'b', 2], ['b', 'd', 1], ['c', 'd', 5]]
    assert shortest_path(edges, 'a', 'd') == dict(reachable=True, path=['a', 'c', 'b', 'd'], length=4.0)
    assert shortest_path(edges, 'd', 'a')['reachable'] is False
    flow = max_flow([['s', 'a', 3], ['s', 'b', 2], ['a', 'b', 1], ['a', 't', 2], ['b', 't', 3]], 's', 't')
    assert flow['flow'] == flow['cut_capacity'] == 5
    assert minimum_spanning_tree([['a', 'b', 1], ['b', 'c', 2], ['a', 'c', 3]])['total'] == 3
    with pytest.raises(ValueError):
        shortest_path([['a', 'b', -1]], 'a', 'b')


def test_mmc_matches_closed_forms():
    one = mmc(.5, 1, 1)  # M/M/1: L = rho/(1-rho), Wq = rho/(mu-lambda)
    assert abs(one['mean_in_system'] - 1) < 1e-12 and abs(one['mean_wait'] - 1) < 1e-12 and abs(one['prob_wait'] - .5) < 1e-12
    two = mmc(1, 1, 2)  # a=1, c=2: Erlang C = (1/2)/(1-1/2) / (1 + 1 + 1) = 1/3
    assert abs(two['prob_wait'] - 1 / 3) < 1e-12
    assert abs(two['mean_in_system'] - 1 * (two['mean_system_time'])) < 1e-12  # Little's law
    with pytest.raises(ValueError):
        mmc(2, 1, 2)


def test_sir_conserves_population_and_matches_final_size_relation():
    r = simulate_sir(.4, .2, 1000., 1., 400)
    total = np.array(r['S']) + np.array(r['I']) + np.array(r['R'])
    assert np.allclose(total, 1000., atol=1e-5)
    z = final_size(2.)
    assert abs(z - 0.7968121) < 1e-6
    assert abs(r['R'][-1] / 1000 - z) < 5e-3


def test_sir_fit_recovers_known_parameters_from_noiseless_data():
    truth = simulate_sir(.45, .15, 5000., 5., 60)['I']
    fit = fit_sir(truth, 5000.)
    assert abs(fit['beta'] - .45) < 2e-3 and abs(fit['gamma'] - .15) < 2e-3


def test_gm11_on_a_geometric_series_and_baselines_on_exact_patterns():
    series = [10 * 1.1 ** k for k in range(8)]
    g = gm11(series, 2)
    assert g['grade'] == 'good' and abs(g['forecast'][0] / (10 * 1.1 ** 8) - 1) < .01
    with pytest.raises(ValueError):
        gm11([1, 2, -3, 4])
    linear = list(2 + 3 * np.arange(30))
    assert rolling_origin(linear, 3)['mae']['linear_trend'] < 1e-9
    seasonal = list(np.tile([1., 5., 2., 8.], 8))
    assert rolling_origin(seasonal, 4, season=4)['mae']['seasonal_naive'] < 1e-9


def test_assignment_matches_brute_force_and_tsp_is_bracketed():
    from modeling.optimize import assignment, tsp
    rng = np.random.default_rng(3)
    cost = rng.integers(1, 20, (5, 5)).astype(float)
    best = min(sum(cost[i, p[i]] for i in range(5)) for p in itertools.permutations(range(5)))
    assert abs(assignment(cost)['total'] - best) < 1e-9
    angles = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    pts = np.c_[np.cos(angles), np.sin(angles)]
    dist = np.linalg.norm(pts[:, None] - pts[None], axis=2)
    result = tsp(dist)
    perimeter = 8 * 2 * math.sin(math.pi / 8)  # convex position: the optimal tour is the polygon
    assert abs(result['length'] - perimeter) < 1e-9 and result['lower_bound'] <= result['length'] + 1e-9
    pts = rng.random((7, 2)); dist = np.linalg.norm(pts[:, None] - pts[None], axis=2)
    optimum = min(sum(dist[t[i], t[(i + 1) % 7]] for i in range(7)) for t in ((0,) + p for p in itertools.permutations(range(1, 7))))
    r = tsp(dist)
    assert r['lower_bound'] <= optimum + 1e-9 <= r['length'] + 2e-9


def test_lp_greater_equal_rows_and_shadow_prices():
    from modeling import optimize
    # min 2x + 3y s.t. x + y >= 4 : optimum x = 4, y = 0, value 8; one more unit of demand costs 2 (the textbook dual y1 = 2)
    r = optimize.solve_lp([2, 3], A_ge=[[1, 1]], b_ge=[4])
    assert abs(r['objective'] - 8) < 1e-9 and abs(r['ge_duals'][0] - 2) < 1e-9 and r['certified']
    # mixed row types: max x + y s.t. x <= 3 (<=), x + y >= 1, y <= 2 (<=): value 5, shadow price of x <= 3 is 1
    r = optimize.solve_lp([1, 1], A_ub=[[1, 0], [0, 1]], b_ub=[3, 2], A_ge=[[1, 1]], b_ge=[1], maximize=True)
    assert abs(r['objective'] - 5) < 1e-9 and np.allclose(r['ineq_duals'], [1, 1]) and abs(r['ge_duals'][0]) < 1e-9
    m = optimize.solve_milp([-1, -1], A_ub=[[2, 2]], b_ub=[5], A_ge=[[1, 0]], b_ge=[1], integrality=[1, 1], bounds=[(0, 10), (0, 10)])
    assert abs(m['objective'] + 2) < 1e-9 and m['x'][0] >= 1 - 1e-9
