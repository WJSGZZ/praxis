"""Independent answers and real invalid-input witnesses from the full plugin audit."""
import itertools
import json
from fractions import Fraction

import mpmath as mp
import numpy as np
import pytest

from modeling import calibrate, decision_models as dm, dynamics, epidemic, experiment
from modeling import inference, layered, nonlinear, pde, queueing, structure
from modeling import evidence, forecast, graph, optimize, weights


@pytest.mark.parametrize('stay, leave', [(1.0 - 1e-11, 1e-11), (1.0, 1e-11)])
def test_absorption_rejects_any_actual_exit_probability(stay, leave):
    from modeling.decision_models import markov_absorption
    with pytest.raises(ValueError, match='not absorbing'):
        markov_absorption([[stay, leave], [1.0, 0.0]], [0])


def test_invalid_dual_sign_cannot_certify_a_zero_gap_candidate(monkeypatch):
    from types import SimpleNamespace
    from modeling import optimize
    fake = SimpleNamespace(status=0, success=True, message='Controlled invalid dual',
        x=np.array([1.]), ineqlin=SimpleNamespace(marginals=np.array([1.])),
        eqlin=SimpleNamespace(marginals=np.array([])),
        lower=SimpleNamespace(marginals=np.array([0.])),
        upper=SimpleNamespace(marginals=np.array([0.])))
    monkeypatch.setattr(optimize, 'linprog', lambda *args, **kwargs: fake)
    result = optimize.solve_lp([1], A_ub=[[1]], b_ub=[1])
    # Independent optimum is x=0. The feasible x=1 has an invalid positive
    # <= multiplier despite a zero displayed gap and stationarity residual.
    assert result['success'] and result['duality_gap'] == 0
    assert result['certified'] is False
    assert result['certificate']['dual_signs_valid'] is False



def test_knapsack_does_not_discard_a_small_positive_gain_or_round_values():
    result = nonlinear.knapsack([1e-13], [1], 1)
    assert result['chosen'] == [1] and result['value'] == 1e-13
    assert Fraction(result['value_exact']) == Fraction.from_float(1e-13)
    # The second value is genuinely larger although both round to 1e16 as floats.
    result = nonlinear.knapsack([10**16, 10**16+1], [1, 1], 1)
    assert result['chosen'] == [0, 1]
    assert Fraction(result['value_exact']) == 10**16+1


def test_bounded_knapsack_matches_exact_cartesian_enumeration_with_zero_weights():
    rng = np.random.default_rng(719)
    for _ in range(30):
        values = [float(x)/7 for x in rng.integers(-3, 8, 5)]
        weights = rng.integers(0, 5, 5).tolist()
        copies = rng.integers(0, 3, 5).tolist()
        capacity = int(rng.integers(0, 9))
        candidates = list(itertools.product(*(range(c+1) for c in copies)))
        exact = max(sum((Fraction.from_float(v)*k for v, k in zip(values, selection)), Fraction(0))
                    for selection in candidates if sum(w*k for w, k in zip(weights, selection)) <= capacity)
        result = nonlinear.knapsack(values, weights, capacity, copies=copies)
        assert Fraction(result['value_exact']) == exact
        assert sum(Fraction.from_float(v)*k for v, k in zip(values, result['chosen'])) == exact
        assert result['weight'] <= capacity
    assert nonlinear.knapsack([], [], 0)['chosen'] == []


@pytest.mark.parametrize('changes', [dict(weights=[1, 2]), dict(capacity=-1), dict(copies=[1.9]),
                                        dict(copies=[-1]), dict(copies=[]), dict(weights=[True]),
                                        dict(values=[np.nan]), dict(capacity=1_000_001)])
def test_knapsack_invalid_problem_is_not_a_proved_solution(changes):
    with pytest.raises(ValueError):
        nonlinear.knapsack(**{**dict(values=[10], weights=[1], capacity=2), **changes})


@pytest.mark.parametrize('changes', [dict(gamma=-1), dict(gamma=2), dict(delta=[[-.2]]),
                                        dict(delta=[[np.nan]]), dict(A_ub=[[1, 2]]), dict(b_ub=[])])
def test_robust_lp_rejects_an_invalid_uncertainty_set(changes):
    with pytest.raises(ValueError):
        nonlinear.robust_lp(**{**dict(c=[1], A_ub=[[1]], b_ub=[1], delta=[[.2]], gamma=1), **changes})


def test_fractional_budget_robust_constraint_has_a_closed_form():
    # Single coefficient with gamma=.5 adds exactly half its radius .2.
    result = nonlinear.robust_lp([1], [[1]], [1], [[.2]], .5, maximize=True)
    assert result['x'] == pytest.approx([10/11])
    assert result['worst_case_row_use'] == pytest.approx([1])


@pytest.mark.parametrize('kind', ['paired_t', 'correlation'])
def test_paired_statistics_require_actual_pairs_instead_of_broadcasting(kind):
    with pytest.raises(ValueError, match='matching sample lengths'):
        inference.hypothesis_test(kind, [1, 2, 3], [1, 2])


@pytest.mark.parametrize('kind,a,b', [('welch_t', [1, 1, 1], [2, 2, 2]),
                                     ('paired_t', [1, 2, 3], [2, 3, 4]),
                                     ('correlation', [1, 1, 1], [2, 3, 4])])
def test_undefined_statistics_are_explicit_without_false_significance(kind, a, b):
    result = inference.hypothesis_test(kind, a, b)
    assert result['significant'] is None
    assert result['diagnostics']
    json.dumps(result, allow_nan=False)


def test_bca_degeneracy_does_not_destroy_the_finite_estimate():
    result = inference.bootstrap_ci([4, 4, 4, 4], n_resamples=30)
    assert result['estimate'] == 4 and result['standard_error'] == 0
    assert result['ci'] is None and result['diagnostics']['ci']['status'] == 'undefined'
    json.dumps(result, allow_nan=False)
    simple = inference.bootstrap_ci([4, 4, 4, 4], method='percentile', n_resamples=30)
    assert simple['ci'] == [4, 4]


def test_large_queue_matches_independent_high_precision_sum_and_littles_law():
    result = queueing.mmc(900, 1, 1000)
    with mp.workdps(60):
        a, c, rho = mp.mpf(900), 1000, mp.mpf('.9')
        tail = a**c/(mp.factorial(c)*(1-rho))
        exact = tail/(mp.fsum(a**k/mp.factorial(k) for k in range(c))+tail)
    assert result['prob_wait'] == pytest.approx(float(exact), rel=1e-12)
    assert result['mean_in_system'] == pytest.approx(900*result['mean_system_time'])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('arrival,service,servers', [(np.nan, 1, 1), (1, np.inf, 2), (1, 1, True)])
def test_queue_refuses_nonfinite_rates_or_boolean_servers(arrival, service, servers):
    with pytest.raises(ValueError):
        queueing.mmc(arrival, service, servers)


def test_sir_initial_state_and_final_size_follow_the_conservation_invariant():
    with pytest.raises(ValueError, match='initial compartments'):
        epidemic.simulate_sir(.4, .2, 100, 10, 3, recovered0=95)
    with pytest.raises(ValueError, match='positive integer'):
        epidemic.simulate_sir(.4, .2, 100, 10, 2.5)
    assert epidemic.simulate_sir(.4, .2, 100, 0, 3, recovered0=30)['I'] == [0, 0, 0, 0]
    final = epidemic.final_size(2, susceptible_fraction=.6, infected_fraction=.1)
    assert final == pytest.approx(.1+.6*(1-np.exp(-2*final)), abs=1e-13)
    result = epidemic.simulate_sir(.4, .2, 1000, 100, 400, recovered0=300)
    assert (result['R'][-1]-300)/1000 == pytest.approx(final, abs=1e-9)
    assert epidemic.final_size(2, susceptible_fraction=.6, infected_fraction=0) == 0
    assert epidemic.final_size(1.000001) == pytest.approx(1.999997333e-6, rel=1e-6)


def test_sir_optional_recovered_observations_are_actually_fitted():
    truth = epidemic.simulate_sir(.4, .12, 2000, 20, 25, recovered0=300)
    result = epidemic.fit_sir(truth['I'], 2000, recovered=truth['R'])
    assert [result['beta'], result['gamma']] == pytest.approx([.4, .12], abs=2e-5)
    assert result['assumptions']['initial_recovered'] == 300
    assert result['fitted_observations'] == ['infected', 'recovered']
    assert result['rmse'] < 1e-6
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('name,value', [('Q', [[-1]]), ('R', [[-1]]), ('P0', [[-1]])])
def test_kalman_covariance_is_a_mathematical_precondition(name, value):
    args = dict(F=[[1]], H=[[1]], Q=[[1]], R=[[2]], x0=[0], P0=[[1]], observations=[1])
    with pytest.raises(ValueError, match='positive semidefinite'):
        dynamics.kalman_filter(**{**args, name: value})


def test_kalman_scalar_steps_match_bayesian_precision_combination():
    result = dynamics.kalman_filter([[1]], [[1]], [[1]], [[2]], [0], [[1]], [1, 2])
    assert np.asarray(result['filtered_mean']).ravel() == pytest.approx([.5, 1.25])
    assert np.asarray(result['filtered_cov']).ravel() == pytest.approx([1, 1])


def test_calibration_cannot_invent_observation_predictions_by_broadcasting():
    with pytest.raises(ValueError, match='one finite prediction'):
        calibrate.calibrate(lambda t, x: t[0], [0, 1, 2, 3], [1, 1, 1, 1], [0])
    result = calibrate.calibrate(lambda t, x: np.full(len(x), t[0]), [0, 1, 2, 3], [1, 1, 1, 1], [0])
    assert result['parameters'][0]['estimate'] == pytest.approx(1)


def test_laplace_inversion_restores_precision_even_with_multiple_calls():
    before = mp.mp.dps
    result = layered.laplace_layered([dict(thickness=1, k=1, rho_c=1)], times=[1],
                t_initial=10, left=['dirichlet', 10], right=['dirichlet', 10], dps=40)
    assert result['surface_left'] == [10] and result['surface_right'] == [10]
    assert mp.mp.dps == before


def test_pca_constant_features_contribute_zero_and_total_variance_is_required():
    result = inference.pca_report([[1, 1], [1, 2], [1, 3]])
    assert result['explained_ratio'][0] == pytest.approx(1)
    assert result['constant_features'] == [0]
    assert result['loadings'][0]['x0'] == pytest.approx(0)
    with pytest.raises(ValueError, match='every feature is constant'):
        inference.pca_report([[1, 1], [1, 1], [1, 1]], standardise=False)
    clustered = inference.cluster_report([[0, 1], [0, 1.1], [0, 1.2], [0, 9], [0, 9.1], [0, 9.2]], [2])
    assert clustered['best_k'] == 2 and clustered['constant_features'] == [0]


def test_fractional_empirical_cvar_tail_is_consistent_with_the_lp():
    result = dm.cvar_portfolio([[-10], [0], [0]], target=-10, alpha=.5)
    # The worst half of three scenarios has mass 1.5, hence (10+.5*0)/1.5.
    assert result['cvar'] == pytest.approx(20/3)
    assert result['empirical_tail_mean'] == pytest.approx(20/3)
    assert result['empirical_tail_mass'] == 1.5


def test_newsvendor_respects_nonnegative_orders_and_reports_the_actual_service_level():
    result = dm.newsvendor(1, .99, 0, 0, 1)
    assert result['order_quantity'] == 0 and result['unconstrained_order_quantity'] < 0
    assert result['service_level'] == .5
    assert 'negative demand mass' in result['note']


def test_recurring_proof_does_not_replace_its_data_with_nearby_nice_rationals():
    result = experiment.check_linear_recurrence([1, 2, 4, 8.000000000001], [2], order_bound=2)
    assert result['mismatches'] == [3] and not result['proof_by_finite_check']
    for bound in [-1, 0, 1.5, True]:
        with pytest.raises(ValueError, match='order_bound'):
            experiment.check_linear_recurrence([1, 2, 4, 8], [2], order_bound=bound)
    assert experiment.check_linear_recurrence(['0.1', '0.2', '0.4', '0.8'], [2], order_bound=2)['proof_by_finite_check']


def test_probability_contract_rejects_nearby_nonstochastic_or_nonabsorbing_rows():
    with pytest.raises(ValueError, match='stochastic'):
        dm.markov_stationary([[1.000001, 0], [0, 1.000001]])
    with pytest.raises(ValueError, match='not absorbing'):
        dm.markov_absorption([[.999999, .000001], [0, 1]], [0, 1])
    with pytest.raises(ValueError):
        dm.pareto_front([[np.nan, 1], [2, 3]], [1, 1])


def test_dimensional_nullspace_accepts_exact_decimal_exponent_spellings():
    result = structure.buckingham_pi([[1.0, 0.0, 1.0], [0.0, 1.0, 1.0]], ['x', 't', 'v'])
    assert result['rank'] == 2 and result['groups'] == [{'x': -1, 't': -1, 'v': 1}]
    matrix = np.array([[1, 1, 1], [1, 0, -1], [0, 1, -1]])
    result = structure.is_network_matrix(matrix)
    assert not result['totally_unimodular']
    witness = result['witness']
    minor = matrix[np.ix_(witness['rows'], witness['columns'])]
    # The first violating minor is 2x2 (-2), before the full determinant 3.
    assert minor.shape == (2, 2)
    assert witness['determinant'] == int(minor[0, 0]*minor[1, 1]-minor[0, 1]*minor[1, 0]) == -2


def test_diffusion_requires_a_real_field_and_accounts_for_single_cell_flux():
    with pytest.raises(ValueError, match='one finite value per cell'):
        pde.solve_diffusion(1, 2, 1, 1, lambda x: np.array([np.nan, 1]), 1, 2)
    result = pde.solve_diffusion(1, 1, 1, 1, lambda x: np.zeros_like(x), 2, 10,
                                 left=['neumann', 2], right=['neumann', 3], source=lambda x: np.ones_like(x))
    assert result['u'] == pytest.approx([12])
    assert result['boundary_energy'] == pytest.approx(10)
    assert result['source_energy'] == pytest.approx(2)
    assert result['energy_residual'] == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize('scale', [1e-10, 1., 1e10])
def test_lp_scale_changes_cannot_remove_the_actual_constraint_or_change_its_solution(scale):
    result = optimize.solve_lp([1], A_ge=[[scale]], b_ge=[scale])
    assert result['x'] == [1] and result['objective'] == 1 and result['certified']
    assert result['ge_duals'] == pytest.approx([1/scale])
    assert result['certificate']['scaled_primal_violation'] == 0
    integer = optimize.solve_milp([1], A_ge=[[scale]], b_ge=[scale], integrality=[1])
    assert integer['x'] == [1] and integer['objective'] == 1 and integer['proved_optimal']


def test_lp_objective_units_and_free_bounds_are_preserved():
    result = optimize.solve_lp([1e-10], A_ub=[[1]], b_ub=[2], maximize=True)
    assert result['x'] == [2] and result['objective'] == 2e-10 and result['certified']
    free = optimize.solve_lp([1], A_eq=[[1]], b_eq=[2], bounds=[(-np.inf, np.inf)])
    assert free['dual_objective'] == free['objective'] == 2 and free['certified']
    json.dumps(free, allow_nan=False)


def test_sparse_very_small_rows_scale_by_division_without_reciprocal_overflow():
    from scipy.sparse import csr_matrix
    result = optimize.solve_lp([1e-308], A_ge=csr_matrix([[1e-308]]), b_ge=[1e-308])
    assert result['x'] == [1] and result['ge_duals'] == pytest.approx([1])
    assert result['objective'] == 1e-308
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('integer', [False, True])
@pytest.mark.parametrize('fixed', [True, False])
def test_a_large_inactive_coefficient_cannot_hide_a_small_active_lp_constraint(integer, fixed):
    # x=0, or optimal x=0 under nonnegative x, leaves 1e-10*y<=1e-10.
    # Therefore max y=1; max-row normalization formerly returned y=2 certified.
    args = dict(c=[0, 1], A_ub=[[1, 1e-10]], b_ub=[1e-10],
                bounds=[(0, 0 if fixed else None), (0, 2)], maximize=True)
    result = optimize.solve_milp(**args, integrality=[1, 1]) if integer else optimize.solve_lp(**args)
    assert result['success'] and result['x'] == [0, 1] and result['objective'] == 1
    assert result['proved_optimal'] if integer else result['certified']


def test_robust_lp_uses_the_same_verified_scaled_lp_contract():
    result = nonlinear.robust_lp([0, 1], [[1, 1e-10]], [1e-10], [[0, 0]], 0, maximize=True)
    assert result['feasible'] and result['certified'] and result['x'] == [0, 1]
    assert result['value'] == 1 and result['worst_case_row_use'] == [1e-10]


def test_tsp_refuses_inputs_that_invalidate_its_lower_bound():
    for matrix in [[[0, -1, -1], [-1, 0, -1], [-1, -1, 0]],
                   [[0, np.inf, 1], [np.inf, 0, 1], [1, 1, 0]],
                   [[0, 1, 1], [1.000000001, 0, 1], [1, 1, 0]]]:
        with pytest.raises(ValueError, match='nonnegative exactly symmetric'):
            optimize.tsp(matrix)
    for starts in [[], [3], [True], [1.5]]:
        with pytest.raises(ValueError, match='starts'):
            optimize.tsp([[0, 1, 1], [1, 0, 1], [1, 1, 0]], starts=starts)


def test_reciprocal_matrix_uses_the_declared_absolute_tolerance():
    with pytest.raises(ValueError, match='reciprocal'):
        weights.ahp([[1, 2.00001], [.5, 1]], tolerance=1e-6)


def test_unknown_relation_cannot_receive_an_exact_refutation_label():
    with pytest.raises(ValueError, match='relation'):
        evidence.rational_witness('x', '2', ['x'], [1.], 'invalid', [[0, 2]])


@pytest.mark.parametrize('kwargs', [dict(horizon=0), dict(horizon=True), dict(horizon=2, min_train=1),
                                   dict(horizon=2, season=0), dict(horizon=2, season=1.5)])
def test_rolling_origin_refuses_empty_forecasts_or_an_invalid_training_design(kwargs):
    with pytest.raises(ValueError):
        forecast.rolling_origin([1]*20, **kwargs)


def test_finite_inputs_do_not_publish_infinite_economic_or_graph_objectives():
    with pytest.raises(ValueError, match='finite numerical range'):
        dm.eoq(1e308, 1e308, 1)
    with pytest.raises(ValueError, match='finite numerical range'):
        graph.shortest_path([['a', 'b', 1e308], ['b', 'c', 1e308]], 'a', 'c')


def test_unrepresentable_shadow_price_is_a_reasoned_null_not_a_failed_valid_solution():
    result = optimize.solve_lp([1], A_ge=[[1e-320]], b_ge=[1e-320])
    assert result['x'] == [1] and result['objective'] == 1 and result['certified']
    assert result['ge_duals'] == [None]
    assert result['diagnostics']['rhs_shadow_prices'][0]['status'] == 'not_representable'
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('coefficient', [1e-12, 1e-14])
@pytest.mark.parametrize('sparse', [False, True])
def test_lp_fixed_bound_cancellation_uses_actual_binary_rhs(coefficient, sparse):
    from scipy.sparse import csr_matrix
    rhs = -1+coefficient
    exact_upper = (Fraction.from_float(rhs)+1)/Fraction.from_float(coefficient)
    matrix = [[-1, coefficient]]
    result = optimize.solve_lp([0, 1], A_ub=csr_matrix(matrix) if sparse else matrix, b_ub=[rhs],
                               bounds=[(1, 1), (0, 2)], maximize=True)
    assert result['success'] and result['certified']
    assert result['x'] == pytest.approx([1, float(exact_upper)], rel=1e-13, abs=1e-15)
    assert result['objective'] == pytest.approx(float(exact_upper), rel=1e-13)
    assert result['dual_objective'] == pytest.approx(float(exact_upper), rel=1e-13)
    # The actual binary RHS makes this maximum strictly smaller than one.
    assert result['objective'] < 1


@pytest.mark.parametrize('integer_y', [False, True])
@pytest.mark.parametrize('coefficient', [1e-12, 1e-14])
def test_milp_cancellation_matches_exact_lattice_or_continuous_bound(coefficient, integer_y):
    rhs = -1+coefficient
    upper = (Fraction.from_float(rhs)+1)/Fraction.from_float(coefficient)
    expected = int(upper) if integer_y else float(upper)
    result = optimize.solve_milp([0, 1], A_ub=[[-1, coefficient]], b_ub=[rhs],
                                 bounds=[(1, 1), (0, 2)], integrality=[1, int(integer_y)], maximize=True)
    assert result['success'] and result['incumbent_feasible'] and result['proved_optimal']
    assert result['x'] == pytest.approx([1, expected], abs=1e-13)
    assert result['objective'] == pytest.approx(expected, abs=1e-13)
    assert result['best_bound'] == pytest.approx(expected, abs=1e-13)


def test_milp_origin_shift_preserves_integer_and_semi_continuous_domains():
    integer = optimize.solve_milp([1], bounds=[(1.2, 2.8)], integrality=[1], maximize=True)
    assert integer['proved_optimal'] and integer['x'] == [2]
    # Code2 includes zero, even when the nonzero interval starts strictly above0.
    semi = optimize.solve_milp([1], bounds=[(2, 3)], integrality=[2])
    assert semi['proved_optimal'] and semi['x'] == [0]


def test_robust_lp_derived_fixed_variable_cancellation_is_correct_or_explicitly_refused():
    k = 1e-12
    upper = (Fraction.from_float(-1+k)+1)/Fraction.from_float(k)
    result = nonlinear.robust_lp([0, 1], [[1, 0], [-1, 0], [-1, k]], [1, -1, -1+k],
                                 [[0, 0], [0, 0], [0, 0]], 0, maximize=True)
    if result['feasible']:
        assert result['certified']
        assert result['x'][1] == pytest.approx(float(upper), rel=1e-13)
    else:
        assert not result['lp_result'].get('certified', False)
        assert 'No numerically verified optimum' in result['note']


def test_finite_mdp_cancellation_matches_independent_full_action_paths():
    P = [[[0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1], [0, 0, 0, 1]],
         [[0, 0, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1], [0, 0, 0, 1]]]
    R = [[1e16, .5], [1, 1], [-1e16, -1e16], [0, 0]]
    rewards = []
    for actions in itertools.product(range(2), repeat=3):
        state, total = 0, Fraction(0)
        for action in actions:
            total += Fraction(R[state][action])
            state = P[action][state].index(1)
        rewards.append((total, actions))
    best = max(rewards)
    assert best[0] == 1 and best[1][0] == 0
    result = nonlinear.solve_mdp(P, R, horizon=3)
    assert result['exact'] and result['value'][0] == 1
    assert Fraction(result['value_exact'][0]) == best[0]
    assert result['policy_by_stages_remaining'][-1][0] == 0
    integers = nonlinear.solve_mdp([[[1]], [[1]]], [[10**16, 10**16+1]], horizon=1)
    assert Fraction(integers['value_exact'][0]) == 10**16+1
    assert integers['policy_by_stages_remaining'] == [[1]]


def test_finite_mdp_stochastic_branch_value_matches_expanded_paths_and_normalization():
    # No floating addition is used in the oracle's probabilities or path rewards.
    P = [[[.1, .9], [.3, .7]]]
    R = [[.125], [.625]]
    terminal = [.25, -.125]
    P_original = np.asarray(P).copy()
    total = Fraction(0)
    for path in itertools.product(range(2), repeat=2):
        state, probability, reward = 0, Fraction(1), Fraction(0)
        for nxt in path:
            reward += Fraction(R[state][0])
            denominator = sum(map(Fraction, P[0][state]))
            probability *= Fraction(P[0][state][nxt])/denominator
            state = nxt
        total += probability*(reward+Fraction(terminal[state]))
    result = nonlinear.solve_mdp(P_original, R, horizon=2, terminal=terminal)
    assert np.array_equal(P_original, np.asarray(P))
    assert result['transition_rows_normalized']
    assert Fraction(result['value_exact'][0]) == total
    assert result['value'][0] == pytest.approx(float(total))


def test_infinite_mdp_exact_residual_bound_covers_closed_form_value():
    result = nonlinear.solve_mdp([[[1]]], [[.1]], discount=.9, tol=1e-12)
    exact = Fraction(.1)/(1-Fraction(.9))
    error = abs(exact-Fraction(result['value'][0]))
    assert error <= Fraction(result['error_bound_exact'])
    assert result['error_bound'] == pytest.approx(float(error), rel=1e-12)
    assert Fraction(result['error_bound']) >= Fraction(result['error_bound_exact'])
    assert result['converged']
    with pytest.raises(ValueError, match='operation budget'):
        nonlinear.solve_mdp([[[1]]], [[1]], horizon=1_000_001)


@pytest.mark.parametrize('scale', [1e-17, 1e-200, 1, 1e200])
def test_matrix_game_scale_does_not_change_analytical_matching_pennies_strategy(scale):
    result = dm.matrix_game([[scale, 0], [0, scale]])
    assert result['row_strategy'] == pytest.approx([.5, .5], rel=1e-13)
    assert result['column_strategy'] == pytest.approx([.5, .5], rel=1e-13)
    assert Fraction(result['value_exact']) == Fraction(scale)/2
    assert result['value']/scale == pytest.approx(.5)
    assert not result['has_saddle']
    assert result['exploitability'] == 0 and result['certified']


def test_matrix_game_large_common_offset_preserves_exact_payoff_differences():
    origin = 1e16
    result = dm.matrix_game([[origin+2, origin], [origin, origin+2]])
    assert result['row_strategy'] == [.5, .5] and result['column_strategy'] == [.5, .5]
    assert Fraction(result['value_exact']) == 10**16+1
    assert not result['has_saddle']
    assert dm.matrix_game([[3, 3], [3, 3]])['has_saddle']
    integers = dm.matrix_game([[10**16+1, 10**16], [10**16, 10**16+1]])
    assert integers['row_strategy'] == [.5, .5] and not integers['has_saddle']
    assert Fraction(integers['value_exact']) == Fraction(2*10**16+1, 2)
