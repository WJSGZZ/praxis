"""Independent baseline answers and visible incomplete rolling-origin comparisons."""
import json
import warnings

import numpy as np
import pytest
from statsmodels.tsa.holtwinters import Holt
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from modeling.forecast import rolling_origin
from scripts import mcp_server


@pytest.mark.parametrize('length,min_train,horizon', [(3, 2, 1), (8, 2, 3), (20, 10, 2)])
def test_holt_participates_on_short_and_long_exact_linear_series(length, min_train, horizon):
    # The continuation of 1, 2, ... is exact; naive h-step MAE is (h+1)/2.
    result = rolling_origin(np.arange(1., length + 1), horizon, min_train=min_train)
    origins = length - horizon - min_train + 1
    assert result['origins'] == origins
    assert result['mae']['naive'] == (horizon + 1) / 2
    assert result['mae']['drift'] == 0
    assert result['mae']['linear_trend'] < 1e-10
    assert result['mae']['holt'] < 1e-5
    for name in ('naive', 'drift', 'linear_trend', 'holt'):
        assert result['methods'][name] == dict(origins=origins, failures=[], skipped=[], status='complete')
    assert result['methods']['seasonal_naive']['status'] == 'skipped'


def test_one_failed_holt_origin_is_visible_and_excluded_from_full_origin_ranking(monkeypatch):
    def fail_one(train, **kwargs):
        if len(train) == 11:
            raise RuntimeError('controlled single-origin failure')
        return Holt(train, **kwargs)

    monkeypatch.setattr('statsmodels.tsa.holtwinters.Holt', fail_one)
    result = rolling_origin(np.arange(1., 21.), 2, min_train=10)
    assert result['origins'] == 9
    assert result['methods']['holt'] == dict(
        status='partial', origins=8, skipped=[],
        failures=[dict(origin=11, error_type='RuntimeError', reason='controlled single-origin failure')])
    assert 'holt' not in result['mae'] and result['best'] != 'holt'
    assert result['mae']['naive'] == 1.5 and result['mae']['drift'] == 0


def test_all_failed_holt_origins_are_visible_without_breaking_other_baselines(monkeypatch):
    def fail_all(*args, **kwargs):
        raise RuntimeError('controlled Holt failure')

    monkeypatch.setattr('statsmodels.tsa.holtwinters.Holt', fail_all)
    result = rolling_origin(np.arange(1., 21.), 2, min_train=10)
    detail = result['methods']['holt']
    assert detail['status'] == 'failed' and detail['origins'] == 0
    assert detail['skipped'] == []
    assert detail['failures'] == [dict(origin=i, error_type='RuntimeError', reason='controlled Holt failure')
                                  for i in range(10, 19)]
    assert set(result['mae']) == {'naive', 'drift', 'linear_trend'}
    assert result['mae']['naive'] == 1.5 and result['mae']['drift'] == 0


@pytest.mark.parametrize('failure', ['nonconvergent', 'nonfinite', 'wrong_shape'])
def test_unusable_holt_fit_does_not_enter_the_numeric_comparison(monkeypatch, failure):
    class UnusableHolt:
        def __init__(self, *args, **kwargs):
            pass

        def fit(self):
            if failure == 'nonconvergent':
                warnings.warn('controlled optimizer failure', ConvergenceWarning)
            return self

        def forecast(self, horizon):
            return [float('nan')] * horizon if failure == 'nonfinite' else [1.] * (horizon + 1)

    monkeypatch.setattr('statsmodels.tsa.holtwinters.Holt', UnusableHolt)
    result = rolling_origin([1., 2., 3.], 1, min_train=2)
    assert result['methods']['holt']['status'] == 'failed'
    assert result['methods']['holt']['origins'] == 0 and 'holt' not in result['mae']
    error = result['methods']['holt']['failures'][0]
    assert error['origin'] == 2 and error['error_type'] == ('ConvergenceWarning' if failure == 'nonconvergent' else 'ValueError')
    assert result['mae']['naive'] == 1 and result['mae']['drift'] == 0


def test_incomplete_seasonal_origins_cannot_appear_as_fair_comparison():
    y = np.tile([1., 4., 2., 8.], 2)
    partial = rolling_origin(y, 1, min_train=2, season=4)
    detail = partial['methods']['seasonal_naive']
    assert partial['origins'] == 6 and detail['origins'] == 4 and detail['status'] == 'partial'
    assert [item['origin'] for item in detail['skipped']] == [2, 3]
    assert detail['failures'] == [] and 'seasonal_naive' not in partial['mae']
    complete = rolling_origin(y, 1, min_train=4, season=4)
    assert complete['methods']['seasonal_naive']['status'] == 'complete'
    assert complete['mae']['seasonal_naive'] == 0
    skipped = rolling_origin(y, 1, min_train=2, season=9)
    assert skipped['methods']['seasonal_naive']['status'] == 'skipped'
    assert skipped['methods']['seasonal_naive']['origins'] == 0


@pytest.mark.parametrize('series,kwargs', [([1., 2., 3.], dict(horizon=1)),
                                         ([1., 2., 3.], dict(horizon=2, min_train=2))])
def test_too_short_for_requested_training_and_horizon_is_rejected(series, kwargs):
    with pytest.raises(ValueError, match='too short'):
        rolling_origin(series, **kwargs)


def test_mcp_reply_preserves_numeric_mae_consumer_and_separate_diagnostics():
    reply = mcp_server.handle(dict(jsonrpc='2.0', id=1, method='tools/call', params=dict(
        name='backtest_baselines', arguments=dict(series=list(range(1, 21)), horizon=2, min_train=10))))
    assert not reply['result'].get('isError', False)
    result = json.loads(reply['result']['content'][0]['text'])
    # Existing consumers can still select and display the numeric metric table.
    assert min(result['mae'], key=result['mae'].get) == result['best']
    assert all(isinstance(value, float) for value in result['mae'].values())
    assert result['mae']['naive'] == 1.5 and result['origins'] == 9
    assert result['methods']['holt']['status'] == 'complete'
