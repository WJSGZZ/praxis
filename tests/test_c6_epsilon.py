"""C6: epsilon-constraint frontiers exclude weakly efficient LP points and merge duplicates; graph label identity."""
import json

import numpy as np
import pytest
from scipy.optimize import linprog

from modeling import decision_models, graph


def test_weakly_efficient_lp_scalar_optimum_is_replaced_by_efficient_point():
    # min x, min y, x+y>=1, y<=1.5: every (0,y) with y in [1,1.5] minimizes x; only (0,1) is efficient.
    result = decision_models.epsilon_constraint_lp([[1, 0], [0, 1]], [-1, -1], [[1.5]], A_ge=[[1, 1]], b_ge=[1], bounds=[[0, 2], [0, 2]])
    point = result['points'][0]
    assert point['accepted'] and point['feasible'] and point['scalar_optimum_verified']
    np.testing.assert_allclose(point['objectives'], [0, 1], atol=1e-9)
    assert [q['objectives'] for q in result['frontier']] == [point['objectives']]
    assert point['weakly_efficient_possible'] is False
    stage = point['lexicographic_stage']
    assert stage['status'] == 'certified' and stage['primary_optimum'] == pytest.approx(0, abs=1e-12)
    json.dumps(result, allow_nan=False)


def test_analytic_front_and_duplicate_points_keep_their_epsilon_rows():
    # max 3x+y, max x+2y>=eps, x+y<=4, 0<=x,y<=3: f1=10 for eps<=5 (vertex (3,1), f2=5), f1=20-2eps up to eps=7.
    grid = [[4], [5], [5.5], [6], [6.5], [7], [7.5]]
    result = decision_models.epsilon_constraint_lp([[3, 1], [1, 2]], [1, 1], grid, A_ub=[[1, 1]], b_ub=[4], bounds=[[0, 3], [0, 3]])
    for point, (epsilon,) in zip(result['points'], grid):
        if epsilon <= 7:
            assert point['accepted']
            expected = [10, 5] if epsilon <= 5 else [20-2*epsilon, epsilon]
            np.testing.assert_allclose(point['objectives'], expected, atol=1e-9)
        else:
            assert not point['accepted']
    frontier = result['frontier']
    assert len(frontier) == 5
    np.testing.assert_allclose(frontier[0]['objectives'], [10, 5], atol=1e-9)
    assert frontier[0]['grid_indices'] == [0, 1] and frontier[0]['epsilon_rows'] == [[4.], [5.]]
    assert all(len(q['grid_indices']) == 1 for q in frontier[1:])
    assert result['coverage']['frontier_points'] == 5 and result['coverage']['accepted_points'] == 6


def test_existing_analytic_line_still_matches():
    result = decision_models.epsilon_constraint_lp([[1, 0], [0, 1]], [-1, -1], [[0], [.25], [.5], [1], [-.1]], A_ge=[[1, 1]], b_ge=[1])
    assert len(result['frontier']) == 4
    for point, epsilon in zip(result['points'][:4], [0, .25, .5, 1]):
        np.testing.assert_allclose(point['objectives'], [1-epsilon, epsilon])
        assert point['weakly_efficient_possible'] is False


def _dominated(C, senses, values, A_ub, b_ub, A_eq, b_eq, bounds):
    """Independent Benson test: largest total improvement over all objectives at once."""
    k, n = C.shape
    D = np.asarray(senses, float)[:, None]*C              # all maximized
    # variables x (n), s (k) >= 0: maximize sum s, D x - s >= D values
    cost = np.r_[np.zeros(n), -np.ones(k)]
    rows = [np.c_[A_ub, np.zeros((len(A_ub), k))], np.c_[-D, np.eye(k)]]
    rhs = [b_ub, -np.asarray(senses, float)*np.asarray(values, float)]
    res = linprog(cost, A_ub=np.vstack(rows), b_ub=np.concatenate(rhs), A_eq=np.c_[A_eq, np.zeros((len(A_eq), k))], b_eq=b_eq,
                  bounds=list(bounds) + [(0, 10)]*k, method='highs')
    assert res.status == 0
    return -res.fun


def test_random_lp_frontiers_contain_no_dominated_points():
    rng = np.random.default_rng(6)
    checked = 0
    for _ in range(25):
        n = 4
        # Coarse integer data creates ties and weakly efficient faces often.
        C = rng.integers(-1, 2, size=(3, n)).astype(float)
        C[0, 0] = 1
        A = rng.integers(0, 2, size=(3, n)).astype(float)
        A[:, 0] = 1
        b = rng.integers(1, 4, 3).astype(float)
        Ae, be = np.ones((1, n)), [1.]
        senses = [-1, 1, -1]
        grid = rng.integers(-1, 2, size=(4, 2)).astype(float)
        bounds = [[-2, 2]]*n
        result = decision_models.epsilon_constraint_lp(C.tolist(), senses, grid.tolist(), A_ub=A.tolist(), b_ub=b.tolist(),
                                                       A_eq=Ae.tolist(), b_eq=be, bounds=bounds)
        for point in result['frontier']:
            assert _dominated(C, senses, point['objectives'], A, b, Ae, be, bounds) <= 1e-6
            checked += 1
    assert checked >= 20


def test_nlp_points_are_labelled_and_duplicate_frontier_points_merged():
    # min x, min (x-1)^2 on [0,1]: both thresholds give x=0, objectives (0,1).
    result = decision_models.epsilon_constraint_nlp([lambda x: x[0], lambda x: (x[0]-1)**2], [-1, -1], [[1.], [2.], [.25]], [[0, 1]], starts=4)
    assert all(p['weakly_efficient_possible'] is True for p in result['points'] if p['accepted'])
    assert len(result['frontier']) == 2
    merged = next(q for q in result['frontier'] if len(q['grid_indices']) == 2)
    assert merged['grid_indices'] == [0, 1] and merged['epsilon_rows'] == [[1.], [2.]]
    np.testing.assert_allclose(merged['objectives'], [0, 1], atol=1e-7)
    assert 'weakly efficient' in result['coverage']['scope']
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('call', [lambda: graph.pagerank([[1, '1', 1]]), lambda: graph.betweenness([[1, 2, 1], ['2', 3, 1]]),
                                  lambda: graph.greedy_modularity_communities([[0, 1, 1]], nodes=[0, 1, '0'], baseline_trials=1)])
def test_graph_rejects_integer_and_string_spelling_of_one_node(call):
    with pytest.raises(ValueError, match='Ambiguous node labels'):
        call()


def test_graph_distinct_string_and_integer_labels_still_work():
    assert [s['node'] for s in graph.pagerank([[1, 2, 1], ['a', 1, 1]])['scores']] == [1, 2, 'a']
