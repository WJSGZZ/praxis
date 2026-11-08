import numpy as np
import pytest

from modeling import calibrate


def decay(theta, x):
    return theta[0] * np.exp(-theta[1] * x) + theta[2]


def test_calibration_recovers_planted_parameters_with_honest_intervals_and_holdout():
    rng = np.random.default_rng(5)
    x = np.linspace(0, 6, 120)
    y = decay([4.0, 0.7, 1.0], x) + rng.normal(0, 0.05, x.size)
    r = calibrate.calibrate(decay, x, y, [1, 1, 0], names=['A', 'k', 'c'], holdout=20)
    for p, truth in zip(r['parameters'], (4.0, 0.7, 1.0)):
        assert p['ci_low'] < truth < p['ci_high']
    assert not r['flags'] and r['holdout']['rmse'] < 0.2 and r['converged']


def test_unidentifiable_and_misspecified_models_are_flagged():
    x = np.linspace(1, 5, 40)
    y = 6 * x
    product = calibrate.calibrate(lambda t, x: t[0] * t[1] * x, x, y + np.random.default_rng(1).normal(0, 0.01, x.size), [1, 5])
    assert any('weakly identified' in f for f in product['flags'])
    wrong = calibrate.calibrate(lambda t, x: t[0] + t[1] * x, np.linspace(0, 3, 80), np.sin(np.linspace(0, 3, 80)) ** 2 * 4, [0, 1])
    assert any('autocorrelated' in f for f in wrong['flags'])
    bounded = calibrate.calibrate(lambda t, x: t[0] * x, x, 6 * x, [1], bounds=[[0, 3]])
    assert any('bound' in f for f in bounded['flags'])
    with pytest.raises(ValueError):
        calibrate.calibrate(decay, x, y, [1, 1, 0], holdout=39)


@pytest.mark.parametrize('scale', [1., 1e-9])
def test_parameter_units_rescale_uncertainty_without_changing_predictions(scale):
    # Two independent group means. The second is parametrized as scale*b.
    # Six unit residuals in the first group give SSE=6 and 10 residual df.
    x = [0]*6 + [1]*6
    y = [0, 2]*3 + [0]*6
    fit = calibrate.calibrate(lambda t, x: t[0]*(1-x) + scale*t[1]*x, x, y, [1, 0])
    expected_mean_se = np.sqrt((6/10)/6)
    assert fit['jacobian_rank'] == 2
    assert fit['rmse'] == pytest.approx(np.sqrt(6/12))
    assert fit['parameters'][0]['std_error'] == pytest.approx(expected_mean_se)
    assert fit['parameters'][1]['std_error'] * scale == pytest.approx(expected_mean_se)


def test_active_bound_keeps_joint_estimates_but_withholds_interior_intervals():
    # All observations have unconstrained slope -1. The constrained slope is 0
    # and the best intercept is the mean response, 3.5.
    x = np.arange(6.)
    fitted = calibrate.calibrate(lambda t, x: t[0] + t[1]*x, x, 6 - x, [1, 1],
                                 names=['intercept', 'slope'], bounds=[[-10, 10], [0, 10]])
    assert fitted['jacobian_rank'] == 2 and fitted['converged']
    assert [row['estimate'] for row in fitted['parameters']] == pytest.approx([3.5, 0], abs=1e-8)
    assert 'slope sits on its lower bound' in fitted['flags']
    assert fitted['max_parameter_correlation'] is None
    assert fitted['diagnostics']['max_parameter_correlation']['status'] == 'active_bound'
    for row in fitted['parameters']:
        assert row['inference']['status'] == 'active_bound'
        assert row['std_error'] is row['ci_low'] is row['ci_high'] is None
