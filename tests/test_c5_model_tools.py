"""C5 model-tool checks against analytic answers and explicit rejected inputs."""
import json

import numpy as np
import pytest
from scipy.stats import t as student

from modeling import calibrate, decision_models, graph, regression, sensitivity


def test_ols_fitted_residuals_and_prediction_intervals_from_scalar_formula():
    x = np.arange(8.)
    residual = np.tile([-1., 1., 1., -1.], 2)
    y = 2+3*x+residual
    result = regression.ols_report(x, y, X_new=[0., 3.5, 10.])
    np.testing.assert_allclose(result['fitted'], 2+3*x)
    np.testing.assert_allclose(result['residuals'], residual)
    prediction = result['prediction']
    sigma2 = 8/6
    z = np.array([0., 3.5, 10.])
    mean = 2+3*z
    half = student.ppf(.975, 6)*np.sqrt(sigma2*(1/8+(z-3.5)**2/42))
    obs_half = student.ppf(.975, 6)*np.sqrt(sigma2*(1+1/8+(z-3.5)**2/42))
    np.testing.assert_allclose(prediction['predicted'], mean)
    np.testing.assert_allclose(prediction['mean_ci'], np.c_[mean-half, mean+half])
    np.testing.assert_allclose(prediction['observation_ci'], np.c_[mean-obs_half, mean+obs_half])
    json.dumps(result, allow_nan=False)


def test_ols_hc3_sandwich_against_hand_leverage_formula_and_rank_nulls():
    x = np.arange(8.)
    residual = np.tile([-1., 1., 1., -1.], 2)
    y = 2+3*x+residual
    result = regression.ols_report(x, y, covariance='HC3', X_new=[3.5])
    # Each coefficient's OLS row influence: intercept = 1/n-xbar*(x-xbar)/Sxx,
    # slope = (x-xbar)/Sxx; HC3 inflates squared residual by (1-h_i)^-2.
    influence = np.array([1/8-3.5*(x-3.5)/42, (x-3.5)/42])
    leverage = 1/8+(x-3.5)**2/42
    covariance = (influence*(residual/(1-leverage))**2) @ influence.T
    np.testing.assert_allclose(result['covariance']['matrix'], covariance)
    np.testing.assert_allclose([c['std_error'] for c in result['coefficients']], np.sqrt(np.diag(covariance)))
    assert 'homoscedastic reference' in result['prediction']['note']
    bad = regression.ols_report(np.c_[x, 2*x], y, covariance='HC3', X_new=[[1, 2]])
    assert bad['prediction']['status'] == 'not_reported_rank_deficient'
    assert bad['prediction']['mean_ci'] is None
    assert all(c['std_error'] is None for c in bad['coefficients'])
    json.dumps(bad, allow_nan=False)


@pytest.mark.parametrize('kwargs', [dict(X_new=[[1, 2]]), dict(X_new=[np.nan]), dict(X_new=[]),
                                    dict(covariance='HC0'), dict(covariance='HC3', groups=[0]*8)])
def test_ols_new_options_reject_bad_inputs(kwargs):
    with pytest.raises(ValueError):
        regression.ols_report(np.arange(8.), np.sin(np.arange(8.)), **kwargs)


def test_sobol_second_order_product_has_only_interaction():
    report = sensitivity.sobol_sensitivity(lambda X: X[:, 0]*X[:, 1], ['x', 'y'], [[-1, 1]]*2,
                                           n=2048, second_order=True)
    assert report['evaluations'] == 2048*6
    np.testing.assert_allclose([p['S1'] for p in report['parameters']], 0, atol=.03)
    np.testing.assert_allclose([p['ST'] for p in report['parameters']], 1, atol=.03)
    assert report['pairs'][0]['S2'] == pytest.approx(1., abs=.04)
    json.dumps(report, allow_nan=False)


def test_sobol_nonuniform_normal_variance_and_second_order_convergence_budget():
    # Independent normals with sd 1 and 2: additive variance shares 1/5 and 4/5.
    report = sensitivity.sobol_sensitivity(lambda X: X[:, 0]+X[:, 1], ['x', 'y'], [[10, 1], [-10, 2]],
                                           distributions=['norm', 'norm'], n=2048)
    np.testing.assert_allclose([p['S1'] for p in report['parameters']], [.2, .8], atol=.02)
    convergence = sensitivity.sobol_convergence(lambda X: X[:, 0]*X[:, 1], ['x', 'y'], [[-1, 1]]*2,
                                               n=512, second_order=True)
    assert convergence['total_evaluations'] == 3*512*6
    assert convergence['pair_changes'][0]['names'] == ['x', 'y']
    assert convergence['converged']
    calls = []
    with pytest.raises(ValueError, match='budget'):
        sensitivity.sobol_convergence(lambda X: calls.append(X), ['x', 'y'], [[-1, 1]]*2,
                                       n=512, second_order=True, max_evaluations=3*512*6-1)
    assert calls == []


@pytest.mark.parametrize('dist,bounds', [('unif', [-2, -1]), ('logunif', [.1, 5]), ('norm', [10, 1]),
                                         ('lognorm', [1, .5]), ('triang', [-1, 3, .5]),
                                         ('truncnorm', [-2, 2, 0, 1]), ('weibull', [2, 3, -1])])
def test_sobol_each_supported_salib_marginal_is_finite_with_one_input(dist, bounds):
    report = sensitivity.sobol_sensitivity(lambda X: X[:, 0], ['x'], [bounds], distributions=[dist], n=256)
    assert report['parameters'][0]['S1'] == pytest.approx(1., abs=.05)
    assert report['parameters'][0]['distribution'] == dist


@pytest.mark.parametrize('bounds,dists', [([[0, 1]], []), ([[0, 1]], ['unknown']), ([[1, 0]], ['unif']),
                                         ([[0, 1]], ['logunif']), ([[0, 0]], ['norm']),
                                         ([[0, 1, .5, 0]], ['truncnorm']), ([[0, 1]], ['triang']),
                                         ([[0, 1, 1]], ['triang']), ([[0, 1]], ['weibull']),
                                         ([[0, np.inf]], ['norm'])])
def test_sobol_bad_marginals_are_rejected_before_model_call(bounds, dists):
    with pytest.raises(ValueError):
        sensitivity.sobol_sensitivity(lambda X: pytest.fail('invalid marginal reached model'), ['x'], bounds,
                                     distributions=dists, n=64)


def test_calibration_multistart_reports_both_symmetric_basins_and_initials():
    x = np.linspace(1, 3, 24)
    # Closed-form LS solutions theta = +/-sqrt(sum(x*y)/sum(x*x)).
    y = 4*x + .05*np.cos(np.arange(24.))
    expected = np.sqrt(x@y/(x@x))
    result = calibrate.calibrate(lambda theta, x: theta[0]**2*x, x, y, [.1], bounds=[[-3, 3]], multistart=16, seed=41)
    assert abs(result['parameters'][0]['estimate']) == pytest.approx(expected, abs=1e-6)
    report = result['multistart']
    assert report['total_starts'] == 17
    assert report['attempts'][0]['theta_initial'] == [.1]
    assert 0 < report['best_basin_fraction'] < 1
    assert report['best_basin_fraction'] == report['best_basin_random_hits']/16
    assert 'global optimum' in report['note']
    json.dumps(result, allow_nan=False)


def test_random_holdout_is_seeded_and_never_selects_on_holdout_responses():
    x = np.linspace(0, 3, 40)
    y = 1+2*x+.02*np.sin(x*5)
    model = lambda theta, x: theta[0]+theta[1]*x
    kwargs = dict(bounds=[[-10, 10], [-10, 10]], holdout=10, holdout_scheme='random', multistart=8, seed=22)
    first = calibrate.calibrate(model, x, y, [0., 0.], **kwargs)
    hold = first['holdout']['holdout_indices']
    changed = y.copy()
    changed[hold] += 1000
    second = calibrate.calibrate(model, x, changed, [0., 0.], **kwargs)
    assert first['parameters'] == second['parameters']
    assert first['multistart'] == second['multistart']
    assert second['holdout']['rmse'] > 900
    assert sorted(first['holdout']['fit_indices']+hold) == list(range(40))
    assert hold != list(range(30, 40))
    design = np.c_[np.ones(30), x[first['holdout']['fit_indices']]]
    expected = np.linalg.lstsq(design, y[first['holdout']['fit_indices']], rcond=None)[0]
    np.testing.assert_allclose([p['estimate'] for p in first['parameters']], expected, atol=1e-6)


@pytest.mark.parametrize('kwargs', [dict(multistart=7), dict(multistart=True), dict(multistart=8),
                                    dict(bounds=[[2, 1]]), dict(bounds=[[0, np.nan]]),
                                    dict(holdout_scheme='unknown'), dict(seed=-1)])
def test_calibration_new_options_reject_bad_inputs(kwargs):
    with pytest.raises(ValueError):
        calibrate.calibrate(lambda theta, x: theta[0]*x, np.arange(12.), np.arange(12.), [1.], **kwargs)


def test_pagerank_star_from_stationary_equations_and_betweenness_path():
    edges = [['c', leaf, 1.] for leaf in ['a', 'b', 'd']]
    result = graph.pagerank(edges, directed=False, alpha=.85)
    assert {key: result[key] for key in ('directed', 'nodes', 'edges')} == dict(directed=False, nodes=4, edges=3)
    scores = {p['node']: p['score'] for p in result['scores']}
    # p_c = (1-a)/4 + a*(1-p_c), leaves share remaining probability.
    center = ((1-.85)/4+.85)/(1+.85)
    assert scores['c'] == pytest.approx(center, abs=1e-9)
    assert scores['a'] == pytest.approx((1-center)/3, abs=1e-9)
    between = graph.betweenness([[0, 1, 1], [1, 2, 1]])
    assert {p['node']: p['score'] for p in between['scores']} == {0: 0., 1: 1., 2: 0.}
    isolated = graph.pagerank([], nodes=['a', 'b'])
    assert [p['score'] for p in isolated['scores']] == [.5, .5]


def test_modularity_two_disjoint_triangles_and_seeded_explicit_null():
    edges = [[u, v, 1] for base in [0, 3] for u, v in [(base, base+1), (base, base+2), (base+1, base+2)]]
    result = graph.greedy_modularity_communities(edges, baseline_trials=5, seed=13)
    assert {frozenset(c) for c in result['communities']} == {frozenset([0, 1, 2]), frozenset([3, 4, 5])}
    # Each component has 3/6 edges and half of total degree: Q=2*(.5-.5^2)=.5.
    assert result['modularity'] == pytest.approx(.5)
    assert result == graph.greedy_modularity_communities(edges, baseline_trials=5, seed=13)
    assert 'Degrees and strengths are not preserved' in result['baseline']['null_model']
    assert 'p_value' not in result['baseline']
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('edges', [[[0, 1, 1], [1, 0, 2]], [[0, 1, 0]], [[0, 1, -1]], [[0, 1, np.inf]],
                                  [[0, 1, True]], [[0, 1]], [[0, 0, 1]], [[0, [], 1]]])
@pytest.mark.parametrize('tool', [graph.betweenness, graph.greedy_modularity_communities])
def test_new_graph_tools_reject_invalid_simple_graphs(tool, edges):
    with pytest.raises(ValueError):
        tool(edges)


def test_epsilon_lp_matches_analytic_line_and_retains_infeasible_threshold():
    # Min x subject to x+y>=1, x,y>=0 and min y<=epsilon: x*=max(0,1-epsilon).
    result = decision_models.epsilon_constraint_lp([[1, 0], [0, 1]], [-1, -1], [[0], [.25], [.5], [1], [-.1]],
                                                  A_ge=[[1, 1]], b_ge=[1])
    assert len(result['frontier']) == 4
    for point, epsilon in zip(result['points'][:4], [0, .25, .5, 1]):
        assert point['accepted'] and point['feasible'] and point['scalar_optimum_verified']
        np.testing.assert_allclose(point['objectives'], [1-epsilon, epsilon])
    assert not result['points'][-1]['accepted']
    assert result['coverage']['attempted_points'] == 5
    assert result['coverage']['complete_frontier'] is False
    assert decision_models.pareto_front([[1, 2], [2, 1], [3, 3]], [-1, -1]) == dict(indices=[0, 1], points=[[1., 2.], [2., 1.]], dominated=[2])
    json.dumps(result, allow_nan=False)


def test_epsilon_lp_mixed_senses_and_primary_order():
    # Max y (primary index 1) subject to min x <=epsilon and y<=x: y*=epsilon.
    result = decision_models.epsilon_constraint_lp([[1, 0], [0, 1]], [-1, 1], [[.2], [.8]], primary=1,
                                                  A_ub=[[-1, 1]], b_ub=[0], bounds=[[0, 1], [0, 1]])
    assert result['epsilon_objectives'] == [0]
    np.testing.assert_allclose([p['objectives'] for p in result['points']], [[.2, .2], [.8, .8]])


def test_epsilon_nlp_matches_two_quadratic_tradeoff_and_marks_local_scope():
    # min x^2 with (x-1)^2<=eps, x in [0,1]: x*=1-sqrt(eps).
    result = decision_models.epsilon_constraint_nlp([lambda x: x[0]**2, lambda x: (x[0]-1)**2], [-1, -1],
                                                   [[.04], [.25], [1.]], [[0, 1]], starts=8)
    for point, epsilon in zip(result['points'], [.04, .25, 1.]):
        assert point['accepted'] and point['feasible']
        assert not point['scalar_optimum_verified']
        assert point['x'][0] == pytest.approx(1-np.sqrt(epsilon), abs=1e-5)
        assert point['feasibility']['max_violation'] <= point['feasibility']['tolerance']
    assert len(result['frontier']) == 3
    assert result['coverage']['complete_frontier'] is False
    json.dumps(result, allow_nan=False)


def test_epsilon_nlp_failed_feasible_incumbents_are_not_frontier(monkeypatch):
    from modeling import nonlinear
    monkeypatch.setattr(nonlinear, 'minimize_nlp', lambda *args, **kwargs: dict(feasible=True, converged=False, status='feasible_incumbent',
                      x=[.5], attempts=[dict(success=False, feasible=True, x=[.5])]))
    result = decision_models.epsilon_constraint_nlp([lambda x: x[0], lambda x: 1-x[0]], [-1, -1], [[1]], [[0, 1]])
    assert result['frontier'] == []
    assert len(result['points'][0]['failed_feasible_incumbents']) == 1
    assert result['points'][0]['feasible'] and not result['points'][0]['accepted']


@pytest.mark.parametrize('kwargs', [dict(senses=[1, 0]), dict(epsilon_grid=[[np.nan]]), dict(epsilon_grid=[0., 1.]),
                                    dict(primary=2), dict(max_points=1, epsilon_grid=[[0], [1]]), dict(tol=-1)])
def test_epsilon_lp_rejects_bad_input(kwargs):
    arguments = dict(objectives=[[1], [-1]], senses=[-1, -1], epsilon_grid=[[1]])
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        decision_models.epsilon_constraint_lp(**arguments)


@pytest.mark.parametrize('kwargs', [dict(objectives=[lambda x: [1], lambda x: 1]),
                                    dict(objectives=[lambda x: np.inf, lambda x: 1]),
                                    dict(bounds=[[0, np.inf]]), dict(constraints=[dict(type='bad', fun=lambda x: 1)]),
                                    dict(starts=0), dict(seed=-1)])
def test_epsilon_nlp_rejects_bad_input(kwargs):
    arguments = dict(objectives=[lambda x: x[0], lambda x: 1-x[0]], senses=[-1, -1], epsilon_grid=[[1]], bounds=[[0, 1]])
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        decision_models.epsilon_constraint_nlp(**arguments)


@pytest.mark.parametrize('kwargs', [dict(alpha=1), dict(alpha=np.nan), dict(max_iter=0), dict(tol=0),
                                    dict(nodes=[0, 0]), dict(nodes=[0]), dict(directed=1)])
def test_pagerank_rejects_invalid_controls_and_node_declarations(kwargs):
    with pytest.raises(ValueError):
        graph.pagerank([[0, 1, 1]], **kwargs)


@pytest.mark.parametrize('directed', [True, False])
def test_pagerank_rejects_exact_duplicate_directed_edges_and_reports_nonconvergence(directed):
    with pytest.raises(ValueError, match='duplicate'):
        graph.pagerank([[0, 1, 1], [0, 1, 2]])
    edges = [[0, 1, 1], [1, 2, 1]]
    result = graph.pagerank(edges, nodes=[0, 1, 2, 3], directed=directed, max_iter=1, tol=1e-16)
    assert result['converged'] is False and result['scores'] is None
    normal = graph.pagerank(edges, nodes=[0, 1, 2, 3], directed=directed)
    assert normal['converged'] is True
    for reply in (result, normal):
        assert {key: reply[key] for key in ('directed', 'nodes', 'edges')} == dict(directed=directed, nodes=4, edges=2)


@pytest.mark.parametrize('kwargs', [dict(resolution=0), dict(baseline_trials=0), dict(baseline_trials=True), dict(seed=-1)])
def test_modularity_rejects_invalid_controls(kwargs):
    with pytest.raises(ValueError):
        graph.greedy_modularity_communities([[0, 1, 1]], **kwargs)


def test_sobol_second_order_budget_is_checked_before_model_and_flag_is_boolean():
    for kwargs in [dict(second_order=True, max_evaluations=64*6-1), dict(second_order=1)]:
        with pytest.raises(ValueError):
            sensitivity.sobol_sensitivity(lambda X: pytest.fail('preflight failed'), ['x', 'y'], [[0, 1]]*2, n=64, **kwargs)


def test_calibration_multistart_keeps_failed_random_start_receipt():
    def model(theta, x):
        if theta[0] < 0:
            raise ValueError('Model is defined only on the nonnegative branch')
        return theta[0]*x
    result = calibrate.calibrate(model, np.arange(12.), 2*np.arange(12.), [1.], bounds=[[-3, 3]], multistart=8, seed=10)
    assert result['parameters'][0]['estimate'] == pytest.approx(2.)
    assert any('error' in attempt for attempt in result['multistart']['attempts'])
    assert len(result['multistart']['attempts']) == 9


def test_hc3_unit_leverage_is_explicitly_undefined_without_nan_output():
    result = regression.ols_report([1., 0., 0., 0., 0., 0., 0., 0.], np.arange(8.), covariance='HC3', X_new=[0., 1.])
    assert result['covariance']['status'] == 'undefined'
    assert 'unit-leverage' in result['covariance']['reason']
    assert result['prediction']['observation_ci'] is None
    assert all(c['std_error'] is None for c in result['coefficients'])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('kwargs', [dict(objectives=[[True], [-1]]), dict(senses=[True, -1])])
def test_epsilon_lp_rejects_mixed_boolean_numeric_objectives_or_senses(kwargs):
    arguments = dict(objectives=[[1], [-1]], senses=[-1, -1], epsilon_grid=[[1]])
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        decision_models.epsilon_constraint_lp(**arguments)
