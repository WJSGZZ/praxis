"""C6 regression checks: observation intervals under robust covariance, leverage and estimability."""
import json

import numpy as np
import pytest
import statsmodels.api as sm
from scipy.stats import t as student

from modeling import regression


def _heteroskedastic(seed=1, n=60):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 10, (n, 2))
    y = 1+2*x[:, 0]-x[:, 1]+rng.normal(0, 0.2+0.5*x[:, 0])
    return x, y


@pytest.mark.parametrize('covariance,extra', [('HC3', {}), ('cluster', dict(groups=list(np.repeat(np.arange(12), 5))))])
def test_robust_covariance_withholds_observation_interval_but_keeps_mean_interval(covariance, extra):
    x, y = _heteroskedastic()
    result = regression.ols_report(x, y, covariance=covariance, X_new=[[5, 5], [9, 1]], **extra)
    prediction = result['prediction']
    assert prediction['status'] == 'computed'
    assert prediction['observation_ci'] is None
    assert prediction['observation_interval']['status'] == 'not_reported_heteroskedastic_noise_model_required'
    assert prediction['observation_interval']['reason']
    assert 'pooled_noise_variance' not in prediction
    # Mean interval: x_new' V x_new with the reported robust covariance and its t df.
    design = np.array([[1, 5, 5], [1, 9, 1]], float)
    V = np.array(result['covariance']['matrix'])
    b = np.array([c['estimate'] for c in result['coefficients']])
    df = result['covariance']['df_inference']
    half = student.ppf(.975, df)*np.sqrt(np.einsum('ij,jk,ik->i', design, V, design))
    np.testing.assert_allclose(prediction['mean_ci'], np.c_[design@b-half, design@b+half], rtol=1e-10)
    json.dumps(result, allow_nan=False)


def test_hc3_covariance_matches_hand_sandwich():
    x, y = _heteroskedastic()
    D = np.column_stack([np.ones(len(y)), x])
    inverse = np.linalg.inv(D.T@D)
    e = y-D@(inverse@D.T@y)
    h = np.einsum('ij,jk,ik->i', D, inverse, D)
    V = inverse@(D.T@(D*(e**2/(1-h)**2)[:, None]))@inverse
    result = regression.ols_report(x, y, covariance='HC3', X_new=[[5, 5]])
    np.testing.assert_allclose(result['covariance']['matrix'], V, rtol=1e-9)


def test_nonrobust_observation_interval_matches_statsmodels_prediction():
    x, y = _heteroskedastic()
    new = np.array([[5, 5], [9, 1]], float)
    result = regression.ols_report(x, y, X_new=new.tolist())
    frame = sm.OLS(y, sm.add_constant(x)).fit().get_prediction(sm.add_constant(new, has_constant='add')).summary_frame(alpha=.05)
    prediction = result['prediction']
    np.testing.assert_allclose(prediction['observation_ci'], frame[['obs_ci_lower', 'obs_ci_upper']].values, rtol=1e-12)
    np.testing.assert_allclose(prediction['mean_ci'], frame[['mean_ci_lower', 'mean_ci_upper']].values, rtol=1e-12)
    assert prediction['observation_interval']['status'] == 'computed'
    assert prediction['pooled_noise_variance'] > 0


def test_near_unit_leverage_is_flagged_for_hc3():
    rng = np.random.default_rng(2)
    x = rng.normal(size=20)
    x[0] = 1e7
    y = x+rng.normal(size=20)
    result = regression.ols_report(x[:, None], y, covariance='HC3')
    leverage = sm.OLS(y, sm.add_constant(x)).fit().get_influence().hat_matrix_diag
    assert 1-leverage.max() < 1e-8
    report = result['covariance']['leverage']
    assert report['status'] == 'near_unit_leverage'
    assert report['rows'] == [0]
    assert any('near-unit leverage' in flag for flag in result['flags'])
    ordinary = regression.ols_report(rng.normal(size=(20, 1)), rng.normal(size=20), covariance='HC3')
    assert ordinary['covariance']['leverage']['status'] == 'checked'
    assert not any('near-unit leverage' in flag for flag in ordinary['flags'])
    json.dumps(result, allow_nan=False)


def test_rank_deficient_prediction_reports_only_estimable_rows():
    rng = np.random.default_rng(3)
    x = rng.normal(size=20)
    y = 1+3*x+rng.normal(size=20)
    # Design columns [1, x, 2x]: new design [1, a, b] is estimable iff b == 2a.
    result = regression.ols_report(np.c_[x, 2*x], y, X_new=[[1, 2], [1, 3], [0, 0]])
    simple = sm.OLS(y, sm.add_constant(x)).fit().params
    prediction = result['prediction']
    assert prediction['estimable'] == [True, False, True]
    assert prediction['predicted'][0] == pytest.approx(simple[0]+simple[1]*1, rel=1e-10)
    assert prediction['predicted'][1] is None
    assert prediction['predicted'][2] == pytest.approx(simple[0], rel=1e-10)
    assert prediction['non_estimable_rows'] == [1]
    assert 'row space' in prediction['estimability_reason']
    assert prediction['status'] == 'not_reported_rank_deficient'
    json.dumps(result, allow_nan=False)


def test_full_rank_prediction_marks_every_row_estimable():
    x, y = _heteroskedastic()
    prediction = regression.ols_report(x, y, X_new=[[1, 2], [3, 4]])['prediction']
    assert prediction['estimable'] == [True, True]
    assert prediction['non_estimable_rows'] == []
