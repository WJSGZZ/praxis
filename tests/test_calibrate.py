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
