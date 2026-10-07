import itertools
import math

import numpy as np
import pytest

from modeling import decision_models as dm


def test_markov_stationary_and_absorption_against_closed_forms():
    p = 0.3, 0.1                                    # two-state chain: pi = (b, a)/(a+b)
    r = dm.markov_stationary([[1 - p[0], p[0]], [p[1], 1 - p[1]]])
    assert np.allclose(r['stationary'], [p[1] / sum(p), p[0] / sum(p)]) and r['irreducible'] and r['residual'] < 1e-12
    assert not dm.markov_stationary([[1, 0], [0, 1]])['irreducible']
    # gambler's ruin on {0..4}, fair coin: ruin probability from i is 1 - i/4, expected duration i (4 - i)
    P = np.zeros((5, 5)); P[0, 0] = P[4, 4] = 1
    for i in (1, 2, 3):
        P[i, i - 1] = P[i, i + 1] = .5
    r = dm.markov_absorption(P, [0, 4])
    assert np.allclose(r['expected_steps'], [1 * 3, 2 * 2, 3 * 1])
    assert np.allclose([row[0] for row in r['absorption_probabilities']], [.75, .5, .25])
    with pytest.raises(ValueError):
        dm.markov_absorption(P, [0, 3])


def test_matrix_game_values():
    r = dm.matrix_game([[0, -1, 1], [1, 0, -1], [-1, 1, 0]])          # rock-paper-scissors
    assert abs(r['value']) < 1e-9 and np.allclose(r['row_strategy'], [1 / 3] * 3) and not r['has_saddle']
    r = dm.matrix_game([[3, 2], [1, 4]])                               # mixed game: value (3*4 - 2*1)/(3+4-2-1) = 2.5
    assert abs(r['value'] - 2.5) < 1e-9 and np.allclose(r['row_strategy'], [.75, .25]) and np.allclose(r['column_strategy'], [.5, .5])
    r = dm.matrix_game([[4, 2], [3, 1]])                               # saddle point at (row 0, col 1): value 2
    assert r['has_saddle'] and abs(r['value'] - 2) < 1e-9
    # negative payoffs are handled
    assert abs(dm.matrix_game([[-3, -2], [-1, -4]])['value'] + 2.5) < 1e-9


def test_eoq_and_newsvendor_closed_forms():
    r = dm.eoq(1200, 50, 2)
    assert abs(r['order_quantity'] - math.sqrt(2 * 1200 * 50 / 2)) < 1e-9
    q = r['order_quantity']
    assert abs(r['annual_cost'] - (1200 / q * 50 + q / 2 * 2)) < 1e-9
    b = dm.eoq(1200, 50, 2, stockout_cost=6)
    assert b['order_quantity'] > q and abs(b['annual_cost'] - r['annual_cost'] * math.sqrt(6 / 8)) < 1e-9
    # the cost is minimised: perturbing the order quantity or the shortage share cannot lower it
    def cost(Q, s):
        return 50 * 1200 / Q + 2 * s ** 2 / (2 * Q) + 6 * (Q - s) ** 2 / (2 * Q)
    assert abs(cost(b['order_quantity'], b['max_inventory']) - b['annual_cost']) < 1e-9
    assert all(cost(b['order_quantity'] * f, b['max_inventory'] * g) >= b['annual_cost'] - 1e-9 for f in (.9, 1, 1.1) for g in (.9, 1, 1.1))
    nv = dm.newsvendor(price=10, cost=6, salvage=2, mean=100, sd=20)
    assert abs(nv['critical_fractile'] - 0.5) < 1e-12 and abs(nv['order_quantity'] - 100) < 1e-9
    # brute-force the expected profit on a fine demand grid
    xs = np.linspace(100 - 8 * 20, 100 + 8 * 20, 200001)
    pdf = np.exp(-.5 * ((xs - 100) / 20) ** 2) / (20 * math.sqrt(2 * math.pi))
    Q = nv['order_quantity']
    profit = np.where(xs < Q, 10 * xs + 2 * (Q - xs), 10 * Q) - 6 * Q
    assert abs(np.trapezoid(profit * pdf, xs) - nv['expected_profit']) < 1e-3


def test_cvar_portfolio_matches_a_brute_force_search_on_two_assets():
    rng = np.random.default_rng(4)
    R = np.column_stack([rng.normal(.02, .01, 400), rng.normal(.06, .08, 400)])
    r = dm.cvar_portfolio(R, target=.04, alpha=.9)
    assert abs(sum(r['weights']) - 1) < 1e-9 and r['expected_return'] >= .04 - 1e-9
    assert abs(r['cvar'] - r['empirical_tail_mean']) < 1e-6
    best = min(((-(R @ np.array([w, 1 - w]))).copy() for w in np.linspace(0, 1, 2001) if R.mean(axis=0) @ np.array([w, 1 - w]) >= .04),
               key=lambda l: np.sort(l)[::-1][:40].mean())
    assert r['cvar'] <= np.sort(best)[::-1][:40].mean() + 1e-9


def test_pareto_front_dominance():
    pts = [[1, 5], [2, 4], [3, 3], [2, 2], [1, 1], [3, 1]]
    r = dm.pareto_front(pts, [+1, +1])                       # maximise both
    assert r['indices'] == [0, 1, 2]
    r = dm.pareto_front([[1, 5], [2, 4], [3, 3], [4, 4]], [-1, -1])  # minimise both
    assert r['indices'] == [0, 1, 2]
