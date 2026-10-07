import numpy as np
import pytest
from modeling.decision import evaluate_alternatives
from modeling.sensitivity import sobol_sensitivity


def test_sobol_additive_known_variance_and_irrelevant_input():
    result = sobol_sensitivity(lambda x: 2*x[:,0]+x[:,1], ['a','b','irrelevant'], [[0,1]]*3, n=1024)
    for key in ['S1','ST']:
        np.testing.assert_allclose([p[key] for p in result['parameters']], [.8,.2,0], atol=.02)
    assert result['evaluations'] == 5120


def test_sobol_detects_analytic_interaction():
    # For product of independent U(0,1): Var=7/144, main effect variance=1/48.
    result = sobol_sensitivity(lambda x: x[:,0]*x[:,1], ['a','b'], [[0,1]]*2, n=1024)
    np.testing.assert_allclose([p['S1'] for p in result['parameters']], [3/7]*2, atol=.02)
    np.testing.assert_allclose([p['ST'] for p in result['parameters']], [4/7]*2, atol=.02)


@pytest.mark.parametrize('model', [lambda x: np.ones(len(x)),
                                  lambda x: np.full(len(x),np.nan),
                                  lambda x: np.ones((len(x),2))])
def test_sobol_rejects_undefined_or_invalid_outputs(model):
    with pytest.raises(ValueError):
        sobol_sensitivity(model,['a'],[[0,1]],n=64)


def test_sobol_budget_prevents_running_expensive_model():
    def never_called(x):
        pytest.fail('Over-budget model must not execute')
    with pytest.raises(ValueError,match='budget'):
        sobol_sensitivity(never_called,['a','b'],[[0,1]]*2,n=1024,max_evaluations=100)
    with pytest.raises(ValueError,match='power of two'):
        sobol_sensitivity(never_called,['a'],[[0,1]],n=100)


def test_topsis_known_ideal_distances_and_constant_criterion():
    result = evaluate_alternatives([[3,1,7],[2,2,7],[1,3,7]],[.4,.4,.2],[-1,1,1],trials=50)
    np.testing.assert_allclose([a['score'] for a in result['alternatives']], [0,.5,1])
    assert result['dropped_criteria'] == [{'criterion':'C3','reason':'constant'}]
    assert result['alternatives'][2]['first_place_scenario_share'] == 1


def test_topsis_invariant_to_unit_changes_and_weight_scaling():
    matrix=np.array([[2.,5.],[4.,7.],[3.,6.]])
    first=evaluate_alternatives(matrix,[2,3],[-1,1],trials=30)
    second=evaluate_alternatives(matrix*np.array([100,1000])+np.array([10,8]),[20,30],[-1,1],trials=30)
    np.testing.assert_allclose([a['score'] for a in first['alternatives']],
                               [a['score'] for a in second['alternatives']])
    np.testing.assert_allclose([a['first_place_scenario_share'] for a in first['alternatives']],
                               [a['first_place_scenario_share'] for a in second['alternatives']])


def test_topsis_ties_share_first_place_and_weight_choice_changes_winner():
    tied=evaluate_alternatives([[1,1],[1,1],[0,0]],[.5,.5],[1,1],trials=20)
    np.testing.assert_allclose([a['first_place_scenario_share'] for a in tied['alternatives']], [.5,.5,0])
    cost=evaluate_alternatives([[1,1],[3,3]],[.8,.2],[-1,1],trials=20,weight_sigma=0)
    benefit=evaluate_alternatives([[1,1],[3,3]],[.2,.8],[-1,1],trials=20,weight_sigma=0)
    assert cost['alternatives'][0]['base_rank'] == 1
    assert benefit['alternatives'][1]['base_rank'] == 1


@pytest.mark.parametrize('matrix,weights,directions', [
    ([[1],[1]],[1],[1]), ([[1],[2]],[-1],[1]),
    ([[1],[2]],[1],[0]), ([[1],[np.nan]],[1],[1])])
def test_topsis_rejects_unsupported_rankings(matrix,weights,directions):
    with pytest.raises(ValueError):
        evaluate_alternatives(matrix,weights,directions,trials=10)


def test_sobol_convergence_check_on_the_ishigami_function():
    import math
    from modeling.sensitivity import sobol_convergence

    def ishigami(X):
        return np.sin(X[:, 0]) + 7 * np.sin(X[:, 1]) ** 2 + 0.1 * X[:, 2] ** 4 * np.sin(X[:, 0])

    out = sobol_convergence(ishigami, ['a', 'b', 'c'], [[-math.pi, math.pi]] * 3, n=1024)
    first = out['fine']['parameters']
    assert abs(first[0]['S1'] - 0.3139) < 0.05 and abs(first[2]['S1']) < 0.05 and abs(first[2]['ST'] - 0.2437) < 0.06
    assert out['converged'] and out['n'] == 1024
