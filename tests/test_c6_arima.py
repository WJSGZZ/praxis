"""C6 regressions for arima_forecast: drift after differencing (C5-1) and convergence-aware selection (C5-2)."""
import numpy as np
import pytest

from modeling import inference
from scripts import mcp_server


def test_registered_example_trend_is_not_forecast_flat():
    # Schema example: 10,12,11,13,... rises by 2 every three steps (slope 2/3), so the true
    # continuation after 24 is 23,25,26. A flat forecast [24,24,24] ignores the trend.
    r = mcp_server.call('arima_forecast', dict(mcp_server.EXAMPLES['arima_forecast'], backtest=True))
    f = np.array(r['forecast'])
    assert np.all(np.diff(f) > .2) and f[-1] > 25
    assert r['trend'] in {'ct', 't'} and r['converged']
    mae = r['backtest']['mae']
    assert 'arima' in mae and mae['arima'] <= mae['naive'] and mae['arima'] <= mae['drift']


def test_trend_stationary_series_keeps_increasing_and_matches_true_continuation():
    # y = 5 + 0.8 t + N(0, 0.3^2). The conditional mean of the next three values is known exactly.
    n = 60
    y = 5 + .8 * np.arange(n) + np.random.default_rng(11).normal(0, .3, n)
    r = inference.arima_forecast(y, 3, max_p=1, max_d=1, max_q=1)
    truth = 5 + .8 * np.arange(n, n + 3)
    assert np.all(np.diff(r['forecast']) > .5)
    # Estimation error of mean and slope is about 0.05 here; 0.3 is one noise standard deviation.
    assert r['forecast'] == pytest.approx(truth, abs=.3)
    assert r['order'][1] == 0 and r['trend'] == 'ct'


def test_random_walk_with_drift_uses_drift_term_after_differencing():
    # y_t = y_{t-1} + 0.5 + e_t. For ARIMA(0,1,0) with drift, the Gaussian MLE drift is the mean
    # first difference, so the h-step forecast is y[-1] + h * mean(diff(y)).
    rng = np.random.default_rng(2)
    y = np.cumsum(.5 + rng.normal(size=120))
    r = inference.arima_forecast(y, 10, max_p=0, max_d=1, max_q=0)
    assert r['order'] == [0, 1, 0] and r['trend'] == 't' and 'drift' in r['parameters']
    expected = y[-1] + np.diff(y).mean() * np.arange(1, 11)
    assert r['forecast'] == pytest.approx(expected, abs=1e-3)
    wide = inference.arima_forecast(y, 10, max_p=2, max_d=1, max_q=2)
    assert wide['order'][1] == 1 and wide['trend'] == 't'
    assert (wide['forecast'][-1] - y[-1]) / 10 > .25


def test_random_walk_without_drift_stays_without_drift():
    y = np.cumsum(np.random.default_rng(4).normal(size=150))
    r = inference.arima_forecast(y, 3, max_p=0, max_d=1, max_q=0)
    assert r['order'] == [0, 1, 0] and r['trend'] == 'n'
    assert r['forecast'] == pytest.approx([y[-1]] * 3, abs=1e-6)


def _ar1(n=90, seed=5):
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    for t in range(1, n):
        y[t] = .6 * y[t - 1] + rng.normal()
    return y + 20


def _force_nonconverged(monkeypatch, predicate):
    from statsmodels.tsa.arima.model import ARIMA
    original = ARIMA.fit

    def fit(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if predicate(self.order):
            result.mle_retvals['converged'] = False
        return result
    monkeypatch.setattr(ARIMA, 'fit', fit)


def test_nonconverged_aicc_best_falls_back_to_best_converged(monkeypatch):
    y = _ar1()
    free = inference.arima_forecast(y, 2, max_p=1, max_d=0, max_q=1)
    assert free['converged']
    bad = tuple(free['order'])
    _force_nonconverged(monkeypatch, lambda order: order == bad)
    r = inference.arima_forecast(y, 2, max_p=1, max_d=0, max_q=1)
    assert r['converged'] and tuple(r['order']) != bad
    s = r['selection']
    assert s['fallback_from_nonconverged']['order'] == list(bad)
    assert s['fallback_from_nonconverged']['aicc'] <= r['aicc']
    assert s['converged_candidates'] < s['candidates_fitted']


def test_backtest_keeps_arima_ranked_when_best_order_never_converges(monkeypatch):
    y = _ar1()
    free = inference.arima_forecast(y, 2, max_p=1, max_d=0, max_q=1)
    bad = tuple(free['order'])
    _force_nonconverged(monkeypatch, lambda order: order == bad)
    r = inference.arima_forecast(y, 2, max_p=1, max_d=0, max_q=1, backtest=dict(min_train=82))
    bt = r['backtest']
    assert bt['methods']['arima']['status'] == 'complete' and not bt['methods']['arima']['failures']
    assert 'arima' in bt['mae'] and bt['origins'] == 7


def test_no_converged_candidate_is_reported_and_backtest_records_reason(monkeypatch):
    y = _ar1()
    _force_nonconverged(monkeypatch, lambda order: True)
    r = inference.arima_forecast(y, 2, max_p=1, max_d=0, max_q=0, backtest=dict(min_train=85))
    assert not r['converged'] and r['selection']['converged_candidates'] == 0
    assert r['selection']['reason']
    bt = r['backtest']
    arima = bt['methods']['arima']
    assert arima['status'] == 'failed' and len(arima['failures']) == bt['origins'] == 4
    assert all('converge' in f['reason'] for f in arima['failures'])
    # Ranking stays on methods complete over the same origins, as rolling_origin defines.
    assert 'arima' not in bt['mae'] and bt['best'] in bt['mae']


def test_exog_trend_parameters_are_named_without_shifting_exog_names():
    rng = np.random.default_rng(8)
    n = 70
    x = rng.normal(size=n + 2)
    y = 3 + .4 * np.arange(n) + 2 * x[:n] + rng.normal(0, .2, n)
    r = inference.arima_forecast(y, 2, max_p=0, max_d=0, max_q=0, exog=x[:n], future_exog=x[n:])
    assert r['trend'] == 'ct'
    assert set(r['parameters']) == {'const', 'trend', 'x1', 'sigma2'}
    assert r['parameters']['x1'] == pytest.approx(2, abs=.1)
    assert r['parameters']['trend'] == pytest.approx(.4, abs=.02)


def test_spurious_first_nonconvergence_is_restarted_and_kept(monkeypatch):
    from statsmodels.tsa.arima.model import ARIMA
    original = ARIMA.fit

    def fit(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if 'start_params' not in kwargs and self.k_trend == 2:
            result.mle_retvals['converged'] = False
        return result
    monkeypatch.setattr(ARIMA, 'fit', fit)
    y = 10+.2*np.arange(30)+.4*np.sin(np.arange(30))
    r = inference.arima_forecast(y, 2, max_p=0, max_q=0, max_d=0)
    assert r['trend'] == 'ct' and r['converged']
    assert r['selection']['restarted_to_convergence'] == 1
    assert r['selection']['fallback_from_nonconverged'] is None
