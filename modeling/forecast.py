"""Forecast baselines, a grey GM(1,1) model and a rolling-origin comparison."""
import warnings
import numpy as np


def gm11(series, horizon=3):
    """Grey GM(1,1) on a short positive series, with the usual posterior-error screen.

    A small C (posterior ratio) and large P are conventional screening values; a good fit on a
    handful of points does not show that a trend continues. Compare it with a baseline first.
    C/P are undefined for constant input and returned as None, with grade not_applicable."""
    x = np.asarray(series, float)
    if x.ndim != 1 or len(x) < 4 or not np.isfinite(x).all() or (x <= 0).any():
        raise ValueError('GM(1,1) needs at least 4 strictly positive values')
    if isinstance(horizon, bool) or not isinstance(horizon, (int, np.integer)) or horizon < 1:
        raise ValueError('horizon must be a positive integer')
    x1 = np.cumsum(x)
    z = (x1[1:] + x1[:-1]) / 2
    a, b = np.linalg.lstsq(np.column_stack([-z, np.ones(len(z))]), x[1:], rcond=None)[0]
    k = np.arange(len(x) + horizon)
    # Difference the response analytically: subtracting two b/a-sized values
    # destroys precision for a near zero (including constant input).
    ratio = -np.expm1(-a) / a if a != 0 else 1.0
    with np.errstate(over='ignore', invalid='ignore'):
        xhat = np.r_[x[0], (b-a*x[0])*np.exp(-a*(k[1:]-1))*ratio]
    if not np.isfinite(xhat).all():
        raise ValueError('GM(1,1) response exceeds finite numeric range')
    resid = x - xhat[:len(x)]
    c = float(resid.std() / x.std()) if x.std() > 0 else None
    p = float(np.mean(np.abs(resid - resid.mean()) < .6745 * x.std())) if x.std() > 0 else None
    return dict(development_coefficient=float(a), grey_input=float(b), fitted=xhat[:len(x)].tolist(), forecast=xhat[len(x):].tolist(),
                posterior_ratio_c=c, small_error_probability_p=p,
                grade='not_applicable' if c is None else 'good' if c < .35 and p > .95 else 'ok' if c < .5 and p > .8 else 'marginal' if c < .65 and p > .7 else 'poor',
                mean_abs_error=float(np.abs(resid).mean()))


def _forecasts(train, h, season):
    n = len(train)
    out = {'naive': np.full(h, train[-1]),
           'drift': train[-1] + (train[-1] - train[0]) / (n - 1) * np.arange(1, h + 1)}
    t = np.arange(n)
    slope, intercept = np.polyfit(t, train, 1)
    out['linear_trend'] = intercept + slope * np.arange(n, n + h)
    failures, skipped = {}, {}
    if season and n >= season:
        out['seasonal_naive'] = np.array([train[n - season + (i % season)] for i in range(h)])
    else:
        skipped['seasonal_naive'] = 'season not supplied' if season is None else 'training size is shorter than season'
    try:
        from statsmodels.tsa.holtwinters import Holt
        from statsmodels.tools.sm_exceptions import ConvergenceWarning
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            warnings.simplefilter('error', ConvergenceWarning)
            prediction = np.asarray(Holt(train, initialization_method='estimated').fit().forecast(h), float)
        if prediction.shape != (h,) or not np.isfinite(prediction).all():
            raise ValueError('Holt must return one finite prediction per horizon step')
        out['holt'] = prediction
    except Exception as error:
        failures['holt'] = dict(error_type=type(error).__name__, reason=str(error))
    return out, failures, skipped


def rolling_origin(series, horizon, *, min_train=None, season=None):
    """Mean absolute error of baselines completing every requested rolling origin.

    A candidate model must beat the best baseline here, with the final test period kept apart
    from anything used to choose the candidate. ``mae`` and ``best`` contain only methods
    covering all ``origins``. Separate ``methods`` diagnostics preserve each method's
    successful origin count, failures and skips; partial results do not enter the ranking.
    An origin is the training-prefix length, so its first held-out item is series[origin]."""
    y = np.asarray(series, float)
    if y.ndim != 1 or not np.isfinite(y).all() or len(y) < 3:
        raise ValueError('series must be a finite one-dimensional series with at least three observations')
    if isinstance(horizon, bool) or not isinstance(horizon, (int, np.integer)) or horizon < 1:
        raise ValueError('horizon must be a positive integer')
    min_train = max(8, len(y) // 2) if min_train is None else min_train
    if isinstance(min_train, bool) or not isinstance(min_train, (int, np.integer)) or min_train < 2:
        raise ValueError('min_train must be an integer of at least two')
    if season is not None and (isinstance(season, bool) or not isinstance(season, (int, np.integer)) or season < 1):
        raise ValueError('season must be a positive integer when supplied')
    if len(y) < min_train + horizon:
        raise ValueError('Series too short for the requested training size and horizon')
    origins = len(y) - horizon - min_train + 1
    methods = {name: dict(origins=0, failures=[], skipped=[])
               for name in ('naive', 'drift', 'linear_trend', 'seasonal_naive', 'holt')}
    errors = {}
    for origin in range(min_train, len(y) - horizon + 1):
        forecasts, failures, skipped = _forecasts(y[:origin], horizon, season)
        for name, f in forecasts.items():
            errors.setdefault(name, []).append(float(np.abs(f - y[origin:origin + horizon]).mean()))
            methods[name]['origins'] += 1
        for name, failure in failures.items():
            methods[name]['failures'].append(dict(origin=origin, **failure))
        for name, reason in skipped.items():
            methods[name]['skipped'].append(dict(origin=origin, reason=reason))
    if not all(np.isfinite(values).all() for values in errors.values()):
        raise ValueError('Baseline forecasts or errors exceed finite numerical range')
    for detail in methods.values():
        detail['status'] = ('complete' if detail['origins'] == origins else
                            'partial' if detail['origins'] else
                            'failed' if detail['failures'] else 'skipped')
    mae = {k: float(np.mean(v)) for k, v in errors.items() if methods[k]['status'] == 'complete'}
    return dict(mae=mae, best=min(mae, key=mae.get), origins=origins, methods=methods)
