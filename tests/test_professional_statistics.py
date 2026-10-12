"""Exact family answers and independent cluster sandwich checks on synthetic data."""
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from scipy import stats

from modeling import inference, regression
from scripts import mcp_server


FAMILY = dict(pvalues=[.01, .04, .03, .2], hypothesis_ids=['A', 'B', 'C', 'D'], family_id='prespecified')


@pytest.mark.parametrize('method,expected,control', [
    ('bh', [Q(1, 25), Q(4, 75), Q(4, 75), Q(1, 5)], 'FDR'),
    ('by', [Q(1, 12), Q(1, 9), Q(1, 9), Q(5, 12)], 'FDR'),
    ('holm', [Q(1, 25), Q(9, 100), Q(9, 100), Q(1, 5)], 'FWER'),
    ('bonferroni', [Q(1, 25), Q(4, 25), Q(3, 25), Q(4, 5)], 'FWER'),
])
def test_adjustment_against_exact_four_hypothesis_answers(method, expected, control):
    report = inference.adjust_pvalues(**FAMILY, method=method, effects=[1., None, -2., .1], effect_definition='difference in centimetres')
    rows = report['hypotheses']
    assert [row['adjusted_p_value'] for row in rows] == pytest.approx([float(value) for value in expected], abs=1e-15)
    assert [row['p_value'] for row in rows] == FAMILY['pvalues']
    assert [row['hypothesis_id'] for row in rows] == FAMILY['hypothesis_ids']
    assert [row['reject'] for row in rows] == ([True, False, False, False] if method != 'by' else [False] * 4)
    assert report['family_size'] == 4 and report['error_control'] == control
    assert report['conditions'] and report['backend']['version']
    assert rows[1]['effect_estimate'] is None and rows[1]['effect_status'] == 'not_supplied'
    assert rows[2]['effect_estimate'] == -2 and rows[2]['effect_status'] == 'caller_supplied'
    json.dumps(report, allow_nan=False)


def test_adjustment_ties_boundaries_permutation_and_bh_conditions():
    result = inference.adjust_pvalues([0., 1., .5, .5], hypothesis_ids=['zero', 'one', 'tie1', 'tie2'], family_id='ties', method='bh')
    assert [row['adjusted_p_value'] for row in result['hypotheses']] == pytest.approx([0., 1., 2/3, 2/3])
    assert 'positive dependence' in result['conditions'][0]
    exact_cutoff = inference.adjust_pvalues([.05], hypothesis_ids=['one'], family_id='singleton')
    assert exact_cutoff['hypotheses'][0]['reject']
    order = [2, 0, 3, 1]
    permuted = inference.adjust_pvalues([FAMILY['pvalues'][i] for i in order], hypothesis_ids=[FAMILY['hypothesis_ids'][i] for i in order], family_id='prespecified', method='holm')
    assert [row['adjusted_p_value'] for row in permuted['hypotheses']] == pytest.approx([.09, .04, .2, .09])


@pytest.mark.parametrize('bad', [[], [[.1]], [.1, np.nan], [.1, np.inf], [-.1], [1.01], [True], ['0.1'], [1j], [10 ** 500]])
def test_adjustment_rejects_invalid_probabilities_before_statsmodels(bad):
    with pytest.raises(ValueError):
        inference.adjust_pvalues(bad, hypothesis_ids=['x'] * len(bad), family_id='bad')


@pytest.mark.parametrize('override', [
    dict(alpha=0), dict(alpha=1), dict(alpha=True), dict(alpha='0.05'), dict(alpha=np.nan),
    dict(method='fdr_bh'), dict(method=[]), dict(family_id=' '), dict(family_id=None),
    dict(hypothesis_ids=['A', 'A', 'C', 'D']), dict(hypothesis_ids=['A']), dict(hypothesis_ids='ABCD'),
    dict(hypothesis_ids=None), dict(hypothesis_ids=4), dict(hypothesis_ids=['A', '', 'C', 'D']),
    dict(effects=[1., 2.]), dict(effects=[1., 2., 3., 4.]),
    dict(effects=[1., True, 3., 4.], effect_definition='change'),
    dict(effect_definition='change'),
])
def test_adjustment_rejects_invalid_family_alpha_and_effect_contract(override):
    with pytest.raises(ValueError):
        inference.adjust_pvalues(**{**FAMILY, **override})


def test_cluster_mean_has_exact_group_level_variance_and_g_minus_one_interval():
    # Six groups have means 2,3,4,5,6,7. Var(mean)=sample variance(group means)/6=7/12.
    # This independent closed form differs from treating twelve rows as independent.
    y = [1., 3., 2., 4., 3., 5., 4., 6., 5., 7., 6., 8.]
    arguments = dict(X=[[1.]] * 12, y=y, add_constant=False, names=['mean'])
    ordinary = regression.ols_report(**arguments)
    cluster = regression.ols_report(**arguments, covariance='cluster', groups=np.repeat(np.arange(6), 2))
    coefficient = cluster['coefficients'][0]
    assert coefficient['estimate'] == pytest.approx(4.5)
    assert coefficient['std_error'] ** 2 == pytest.approx(float(Q(7, 12)), abs=1e-12)
    critical = stats.t.ppf(.975, 5)
    assert coefficient['ci_low'] == pytest.approx(4.5 - critical * np.sqrt(7/12))
    assert coefficient['ci_high'] == pytest.approx(4.5 + critical * np.sqrt(7/12))
    assert coefficient['p_value'] == pytest.approx(2 * stats.t.sf(4.5 / np.sqrt(7/12), 5))
    assert cluster['covariance']['df_inference'] == 5
    assert cluster['covariance']['finite_sample_correction'] == pytest.approx(6/5)
    assert ordinary['coefficients'][0]['std_error'] != pytest.approx(coefficient['std_error'])
    for key in ('n', 'parameters', 'design_rank', 'r2', 'adj_r2', 'rmse', 'diagnostics'):
        assert ordinary[key] == cluster[key]
    assert any('few clusters' in flag for flag in cluster['flags'])
    json.dumps(cluster, allow_nan=False)


def test_cluster_linear_regression_matches_exact_rational_normal_equations_and_sandwich():
    # Hand two-column normal equations and group score outer products, using exact rationals.
    x = list(map(Q, range(24)))
    y = [Q(2) + Q(3, 2) * value + Q(3, 5) * (i // 4 - 2) + Q(1, 5) * (-1) ** i for i, value in enumerate(x)]
    n, g = 24, 6
    xx = sum(value * value for value in x)
    sx, sy, sxy = sum(x), sum(y), sum(a * b for a, b in zip(x, y))
    determinant = n * xx - sx * sx
    bread = [[xx / determinant, -sx / determinant], [-sx / determinant, Q(n) / determinant]]
    beta = [bread[0][0] * sy + bread[0][1] * sxy, bread[1][0] * sy + bread[1][1] * sxy]
    residual = [b - beta[0] - beta[1] * a for a, b in zip(x, y)]
    scores = [[sum(residual[i:i+4]), sum(x[j] * residual[j] for j in range(i, i+4))] for i in range(0, n, 4)]
    meat = [[sum(score[a] * score[b] for score in scores) for b in range(2)] for a in range(2)]
    correction = Q(g, g-1) * Q(n-1, n-2)
    sandwich = [[sum(bread[a][i] * meat[i][j] * bread[j][b] for i in range(2) for j in range(2)) * correction for b in range(2)] for a in range(2)]
    report = regression.ols_report([float(value) for value in x], [float(value) for value in y], covariance='cluster', groups=np.repeat(np.arange(g), 4))
    assert [item['estimate'] for item in report['coefficients']] == pytest.approx([float(value) for value in beta], abs=1e-12)
    np.testing.assert_allclose(report['covariance']['matrix'], [[float(value) for value in row] for row in sandwich], atol=1e-12, rtol=1e-10)
    np.testing.assert_allclose([item['std_error'] ** 2 for item in report['coefficients']], [float(sandwich[i][i]) for i in range(2)], atol=1e-12)


@pytest.mark.parametrize('groups', [[0] * 12, list(range(12))])
def test_cluster_boundary_one_group_is_null_singletons_are_valid(groups):
    report = regression.ols_report(np.arange(12.), [i + (-1) ** i for i in range(12)], covariance='cluster', groups=groups)
    if len(set(groups)) == 1:
        assert report['covariance']['status'] == 'undefined' and report['covariance']['matrix'] is None
        assert report['covariance']['df_inference'] is None
        assert all(item['std_error'] is None and item['p_value'] is None and item['ci_low'] is None for item in report['coefficients'])
        assert all(item['inference']['reason'] for item in report['coefficients'])
    else:
        assert report['covariance']['status'] == 'computed' and report['covariance']['clusters'] == 12
    json.dumps(report, allow_nan=False)


def test_rank_deficient_cluster_fit_keeps_point_solution_without_individual_inference():
    x = np.arange(12.)
    report = regression.ols_report(np.column_stack([x, 2*x]), x + np.sin(x), covariance='cluster', groups=np.repeat(np.arange(4), 3))
    assert report['design_rank'] == 2 and report['parameters'] == 3
    assert report['covariance']['status'] == 'not_reported_rank_deficient'
    assert report['covariance']['matrix'] is None
    assert all(item['inference']['status'] == 'not_reported_rank_deficient' and item['p_value'] is None for item in report['coefficients'])
    json.dumps(report, allow_nan=False)


def test_zero_cluster_scores_and_singular_covariance_do_not_claim_full_inference():
    # Every group mean equals two, so the cluster score for this constant model
    # is exactly zero despite variation within each group.
    zero = regression.ols_report([[1.]]*12, [1., 3.]*6, add_constant=False, covariance='cluster', groups=np.repeat(np.arange(6), 2))
    assert abs(zero['covariance']['matrix'][0][0]) < 1e-28
    assert zero['covariance']['joint_inference_status'] == 'numerically_degenerate'
    assert zero['coefficients'][0]['inference']['status'] == 'undefined'
    assert zero['coefficients'][0]['p_value'] is None and zero['coefficients'][0]['ci_low'] is None
    assert 'standard error' in zero['coefficients'][0]['inference']['reason']
    json.dumps(zero, allow_nan=False)
    x = np.arange(12.)
    singular = regression.ols_report(x, 2*x + np.cos(x), covariance='cluster', groups=[0]*6 + [1]*6)
    assert singular['covariance']['rank'] <= 1
    assert singular['covariance']['joint_inference_status'] == 'singular_covariance'
    assert any('singular' in flag for flag in singular['flags'])


@pytest.mark.parametrize('scale', [1e-12, 1., 1e12])
def test_cluster_roundoff_guard_respects_response_units_and_keeps_resolvable_small_variance(scale):
    groups = np.repeat(np.arange(6), 2)
    degenerate = regression.ols_report([[1.]]*12, np.array([1.,3.]*6)*scale, add_constant=False, covariance='cluster', groups=groups)
    assert degenerate['coefficients'][0]['inference']['status'] == 'undefined'
    # Tiny group differences are real compared with floating-point precision.
    y = np.array([1.,3.]*6) + np.repeat(np.arange(6), 2) * 1e-8
    resolvable = regression.ols_report([[1.]]*12, y*scale, add_constant=False, covariance='cluster', groups=groups)
    assert resolvable['coefficients'][0]['inference']['status'] == 'computed'
    assert resolvable['coefficients'][0]['std_error'] / scale == pytest.approx(np.sqrt(7/12) * 1e-8, rel=1e-6)


@pytest.mark.parametrize('override', [dict(covariance='HC3'), dict(groups=[0]*12), dict(covariance='cluster'),
    dict(covariance='cluster', groups=[0]*11), dict(covariance='cluster', groups=[[0]]*12),
    dict(covariance='cluster', groups=[False]*12), dict(covariance='cluster', groups=[None]*12),
    dict(covariance='cluster', groups=[' ']*12), dict(covariance='cluster', groups=[1.2]*12)])
def test_cluster_bad_inputs_do_not_silently_fall_back_to_independent_errors(override):
    with pytest.raises(ValueError):
        regression.ols_report(np.arange(12.), np.sin(np.arange(12.)), **override)


def test_original_ols_default_contract_and_typed_cluster_identifiers():
    x = np.arange(12.)
    y = 2*x + np.sin(x)
    assert regression.ols_report(x, y) == regression.ols_report(x, y, covariance='nonrobust')
    report = regression.ols_report(x, y, covariance='cluster', groups=[1]*6 + ['1']*6)
    assert report['covariance']['clusters'] == 2


def test_new_statistics_mcp_adapters_match_python_and_reject_bool_p():
    assert mcp_server.call('adjust_pvalues', FAMILY) == inference.adjust_pvalues(**FAMILY)
    with pytest.raises(ValueError):
        mcp_server.call('adjust_pvalues', {**FAMILY, 'pvalues': [True, .1, .2, .3]})
    arguments = dict(X=[[1.]]*12, y=[1.,3.,2.,4.,3.,5.,4.,6.,5.,7.,6.,8.], add_constant=False,
                     covariance='cluster', groups=list(np.repeat(np.arange(6), 2).astype(int).tolist()))
    assert mcp_server.call('ols_report', arguments) == regression.ols_report(**arguments)


def test_statistics_over_real_stdio_and_error_recovery():
    def tool(identifier, name, arguments):
        return dict(jsonrpc='2.0', id=identifier, method='tools/call', params=dict(name=name, arguments=arguments))
    messages = [tool(1, 'adjust_pvalues', {**FAMILY, 'method': 'by'}),
                tool(2, 'adjust_pvalues', {**FAMILY, 'alpha': 0}),
                tool(3, 'ols_report', dict(X=[[1.]]*12, y=[1.,3.,2.,4.,3.,5.,4.,6.,5.,7.,6.,8.], add_constant=False,
                                         covariance='cluster', groups=np.repeat(np.arange(6), 2).tolist())),
                dict(jsonrpc='2.0', id=4, method='ping'),
                tool(5, 'solve_lp', dict(c=[3, 2], A_ub=[[1, 1], [1, 3]], b_ub=[4, 6], maximize=True))]
    process = subprocess.run([sys.executable, '-m', 'scripts.mcp_server'], cwd=Path(__file__).resolve().parents[1],
                             input='\n'.join(json.dumps(message, allow_nan=False) for message in messages) + '\n',
                             capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    replies = [json.loads(line) for line in process.stdout.splitlines()]
    assert [reply['id'] for reply in replies] == [1,2,3,4,5]
    adjusted = json.loads(replies[0]['result']['content'][0]['text'])
    assert [row['adjusted_p_value'] for row in adjusted['hypotheses']] == pytest.approx([1/12,1/9,1/9,5/12])
    assert replies[1]['result']['isError']
    cluster = json.loads(replies[2]['result']['content'][0]['text'])
    assert cluster['coefficients'][0]['std_error'] ** 2 == pytest.approx(7/12)
    assert replies[3]['result'] == {}
    solved = json.loads(replies[4]['result']['content'][0]['text'])
    assert solved['certified'] and solved['objective'] == pytest.approx(12)


@pytest.mark.parametrize('kind', ['welch_t', 'paired_t'])
def test_normality_flags_do_not_switch_the_mean_estimand_or_sampling_design(kind):
    # Difference mean=1, variance=10, se(mean)=1 gives t=1 with nine df.
    a, b = [0.]*9 + [10.], [0.]*10
    report = inference.hypothesis_test(kind, a, b)
    assert report['kind'] == kind and report['statistic'] == pytest.approx(1.)
    assert report['p'] == pytest.approx(2 * stats.t.sf(1., 9))
    assert report['ci'] == pytest.approx([1-stats.t.ppf(.975,9), 1+stats.t.ppf(.975,9)])
    assert 'mean' in report['estimand'].lower()
    assert report['sample_design']['status'] == 'not_checked'
    assert any('diagnostic' in flag and ('not' in flag or 'Do not' in flag) for flag in report['flags'])
    assert not any('consider mann_whitney' in flag or 'consider a Wilcoxon' in flag for flag in report['flags'])


def test_levene_flag_does_not_substitute_a_rank_target_for_unequal_variance_means():
    report = inference.hypothesis_test('anova', None, groups=[[-1.,0.,1.]*4, [-10.,0.,10.]*4])
    # Both means are zero, so between-group variation and classic F are exactly zero.
    assert report['statistic'] == 0 and report['p'] == 1 and report['effect_size_eta_squared'] == 0
    assert report['sample_design']['status'] == 'not_checked'
    assert any('Levene' in flag and 'does not select a method' in flag for flag in report['flags'])
    assert not any('use kruskal' in flag for flag in report['flags'])


def test_time_comparison_baseline_uses_one_training_origin_for_the_whole_test_block():
    # With 12 points and two expanding folds, the test blocks are [4,5,6,7]
    # and [8,9,10,11], and their training endpoints are 3 and 7. Each block's
    # baseline errors are [1,2,3,4], giving RMSE=sqrt(30/4), not one-step RMSE=1.
    report = regression.compare_models([[i] for i in range(12)], list(range(12)), scheme='time', folds=2)
    assert report['models']['baseline']['rmse'] == pytest.approx(np.sqrt(7.5))
    assert report['models']['baseline']['rmse_se'] == 0
    assert report['evaluation_design'] == 'fixed_origin_test_blocks'
    assert 'several horizons' in report['note']


def test_time_baseline_never_uses_previous_test_targets_as_predictions():
    # A step within a test block changes measured errors, not its predictions.
    # Constant baseline origins: zero for block [0,10,10,10], ten for block
    # [10,10,10,10]. The two hand RMSEs are sqrt(300/4) and zero.
    y = [0.]*5 + [10.]*7
    report = regression.compare_models([[i] for i in range(12)], y, scheme='time', folds=2)
    assert report['models']['baseline']['rmse'] == pytest.approx(np.sqrt(75)/2)
    assert report['models']['baseline']['rmse_se'] == pytest.approx(np.sqrt(75)/2)
