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
    if season and n >= season:
        out['seasonal_naive'] = np.array([train[n - season + (i % season)] for i in range(h)])
    try:
        from statsmodels.tsa.holtwinters import Holt
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            out['holt'] = np.asarray(Holt(train).fit().forecast(h))
    except Exception:
        pass
    return out


def rolling_origin(series, horizon, *, min_train=None, season=None):
    """Mean absolute error of each baseline over every origin with `horizon` held-out points.

    A candidate model must beat the best baseline here, with the final test period kept apart
    from anything used to choose the candidate."""
    y = np.asarray(series, float)
    min_train = min_train or max(8, len(y) // 2)
    if len(y) < min_train + horizon:
        raise ValueError('Series too short for the requested training size and horizon')
    errors = {}
    for origin in range(min_train, len(y) - horizon + 1):
        for name, f in _forecasts(y[:origin], horizon, season).items():
            errors.setdefault(name, []).append(float(np.abs(f - y[origin:origin + horizon]).mean()))
    mae = {k: float(np.mean(v)) for k, v in errors.items()}
    return dict(mae=mae, best=min(mae, key=mae.get), origins=len(next(iter(errors.values()))))
