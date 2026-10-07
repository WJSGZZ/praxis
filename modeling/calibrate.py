"""Fit model parameters to data, and say honestly what the data can and cannot determine."""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
from scipy.optimize import least_squares


def calibrate(model: Callable[[np.ndarray, np.ndarray], np.ndarray], x: Sequence[float], y: Sequence[float], theta0: Sequence[float], *,
              bounds: Sequence[Sequence[float]] | None = None, names: Sequence[str] | None = None, holdout: int = 0, alpha: float = 0.05) -> dict:
    """Least-squares calibration of model(theta, x) to (x, y), with an identifiability and hold-out report.

    Reported: estimates with approximate confidence intervals (local, from the Jacobian, valid if the model is right and the noise
    independent), the Jacobian's condition number and the largest parameter correlation (large values mean the data cannot separate the
    parameters), the residual lag-1 autocorrelation (structure left in the residuals), the rms error, and, if `holdout` > 0, the rms
    error on the last `holdout` points that were kept out of the fit. Flags list each warning."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    theta0 = np.asarray(theta0, float)
    k = len(theta0)
    labels = list(names) if names else [f'p{i + 1}' for i in range(k)]
    if holdout < 0 or holdout >= len(x) - k:
        raise ValueError('holdout must leave more fitted points than parameters')
    n_fit = len(x) - holdout
    lo, hi = (np.full(k, -np.inf), np.full(k, np.inf)) if bounds is None else (np.asarray([b[0] for b in bounds], float), np.asarray([b[1] for b in bounds], float))

    def residual(theta, upto):
        return np.asarray(model(theta, x[:upto]), float) - y[:upto]

    fit = least_squares(residual, theta0, args=(n_fit,), bounds=(lo, hi))
    J = fit.jac
    dof = max(1, n_fit - k)
    sigma2 = 2 * fit.cost / dof
    cond = float(np.linalg.cond(J))
    cov = np.linalg.pinv(J.T @ J) * sigma2
    se = np.sqrt(np.diag(cov))
    from scipy.stats import t as student
    crit = float(student.ppf(1 - alpha / 2, dof))
    corr = cov / np.outer(se, se) if (se > 0).all() else np.full((k, k), np.nan)
    off = np.abs(corr - np.eye(k)) if k > 1 else np.zeros((1, 1))
    max_corr = float(np.nanmax(off)) if k > 1 else 0.0
    res = fit.fun
    lag1 = float(np.corrcoef(res[:-1], res[1:])[0, 1]) if len(res) > 3 and res.std() > 0 else 0.0
    rmse = float(np.sqrt(np.mean(res ** 2)))
    flags = []
    if cond > 1e6 or max_corr > 0.98:
        flags.append(f'weakly identified (Jacobian condition {cond:.2g}, max |correlation| {max_corr:.3f}): the data cannot separate the parameters')
    for i in range(k):
        if np.isfinite(lo[i]) and abs(fit.x[i] - lo[i]) < 1e-6 * max(1, abs(lo[i])) or np.isfinite(hi[i]) and abs(fit.x[i] - hi[i]) < 1e-6 * max(1, abs(hi[i])):
            flags.append(f'{labels[i]} sits on its bound')
    if abs(lag1) > 0.5:
        flags.append(f'residuals are strongly autocorrelated (lag-1 {lag1:.2f}): the model misses structure the data contain')
    out = dict(parameters=[dict(name=labels[i], estimate=float(fit.x[i]), std_error=float(se[i]), ci_low=float(fit.x[i] - crit * se[i]), ci_high=float(fit.x[i] + crit * se[i]))
                           for i in range(k)], rmse=rmse, points_fitted=n_fit, jacobian_condition=cond, max_parameter_correlation=max_corr,
               residual_lag1_autocorrelation=lag1, converged=bool(fit.success), flags=flags,
               note='Confidence intervals are local and conditional on the model being right; they do not include structural error.')
    if holdout:
        pred = np.asarray(model(fit.x, x[n_fit:]), float)
        out['holdout'] = dict(points=holdout, rmse=float(np.sqrt(np.mean((pred - y[n_fit:]) ** 2))), fit_rmse=rmse)
    return out
