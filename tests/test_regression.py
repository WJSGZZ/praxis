import numpy as np
import pytest

from modeling import regression


def coefficient(report, name):
    return next(c for c in report['coefficients'] if c['name'] == name)


def test_ols_recovers_planted_coefficients_and_is_clean_on_clean_data():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(400, 2))
    y = 2 + 3 * X[:, 0] - 1 * X[:, 1] + rng.normal(0, .5, 400)
    r = regression.ols_report(X, y, names=['a', 'b'])
    for name, truth in (('const', 2), ('a', 3), ('b', -1)):
        c = coefficient(r, name)
        assert c['ci_low'] < truth < c['ci_high']
    assert r['r2'] > .9 and not r['flags']


def test_diagnostics_flag_the_planted_problems():
    rng = np.random.default_rng(2)
    x = rng.uniform(1, 10, 400)
    hetero = regression.ols_report(x, 1 + 2 * x + rng.normal(0, 1, 400) * x)
    assert any('heteroscedasticity' in f for f in hetero['flags'])
    x1 = rng.normal(size=300)
    collinear = regression.ols_report(np.column_stack([x1, x1 + rng.normal(0, .02, 300)]), x1 + rng.normal(0, 1, 300))
    assert any('multicollinearity' in f for f in collinear['flags'])
    noise = np.zeros(300)
    for t in range(1, 300):
        noise[t] = .9 * noise[t - 1] + rng.normal()
    auto = regression.ols_report(np.arange(300.), .01 * np.arange(300) + noise)
    assert any('autocorrelation' in f for f in auto['flags'])
    skewed = regression.ols_report(x, 1 + 2 * x + rng.exponential(3, 400))
    assert any('not normal' in f for f in skewed['flags'])
    with pytest.raises(ValueError):
        regression.ols_report([[1, 2], [2, 3], [3, 5]], [1, 2, 3])


def test_model_comparison_prefers_the_right_model_and_refuses_to_reward_noise():
    rng = np.random.default_rng(3)
    X = rng.uniform(-3, 3, size=(600, 1))
    linear = regression.compare_models(X, 2 * X[:, 0] + rng.normal(0, .5, 600))
    assert linear['models']['ols']['beats_baseline'] and linear['models']['ridge']['beats_baseline']
    nonlinear = regression.compare_models(X, np.sin(2 * X[:, 0]) * 3 + rng.normal(0, .3, 600))
    assert nonlinear['models']['boosting']['rmse'] < nonlinear['models']['ols']['rmse'] and nonlinear['models']['boosting']['beats_baseline']
    noise = regression.compare_models(rng.normal(size=(300, 3)), rng.normal(size=300))
    assert not any(v['beats_baseline'] for k, v in noise['models'].items() if k != 'baseline')
    t = np.arange(400.)
    series = regression.compare_models(t[:, None], .05 * t + rng.normal(0, .5, 400), scheme='time')
    assert series['models']['ols']['beats_baseline']
    with pytest.raises(ValueError):
        regression.compare_models(X, X[:, 0], scheme='shuffle')
