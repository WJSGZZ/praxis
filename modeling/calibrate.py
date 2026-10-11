"""Fit model parameters to data, and say honestly what the data can and cannot determine."""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
from scipy.optimize import least_squares
from modeling.contracts import diagnostic


def calibrate(model: Callable[[np.ndarray, np.ndarray], np.ndarray], x: Sequence[float], y: Sequence[float], theta0: Sequence[float], *,
              bounds: Sequence[Sequence[float]] | None = None, names: Sequence[str] | None = None, holdout: int = 0, alpha: float = 0.05) -> dict:
    """Least-squares calibration of model(theta, x) to (x, y), with an identifiability and hold-out report.

    Reported: estimates with approximate confidence intervals (local, from the Jacobian, valid if the model is right and the noise
    independent), the Jacobian's condition number and the largest parameter correlation (large values mean the data cannot separate the
    parameters), the residual lag-1 autocorrelation (structure left in the residuals), the rms error, and, if `holdout` > 0, the rms
    error on the last `holdout` points that were kept out of the fit. Undefined diagnostics are null with explicit reasons;
    rank-deficient or failed fits do not report individual parameter intervals. Flags list each warning."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    theta0 = np.asarray(theta0, float)
    if x.ndim != 1 or y.shape != x.shape or theta0.ndim != 1 or not len(theta0) or not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(theta0).all():
        raise ValueError('x and y must be matching finite vectors, and theta0 a nonempty finite vector')
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError('alpha must be between zero and one')
    k = len(theta0)
    labels = list(names) if names else [f'p{i + 1}' for i in range(k)]
    if len(labels) != k:
        raise ValueError('names must match the parameters')
    if holdout < 0 or holdout >= len(x) - k:
        raise ValueError('holdout must leave more fitted points than parameters')
    n_fit = len(x) - holdout
    lo, hi = (np.full(k, -np.inf), np.full(k, np.inf)) if bounds is None else (np.asarray([b[0] for b in bounds], float), np.asarray([b[1] for b in bounds], float))

    def residual(theta, upto):
        return np.asarray(model(theta, x[:upto]), float) - y[:upto]

    fit = least_squares(residual, theta0, args=(n_fit,), bounds=(lo, hi))
    J = fit.jac
    rank = int(np.linalg.matrix_rank(J))
    identified = rank == k
    dof = max(1, n_fit - k)
    sigma2 = 2 * fit.cost / dof
    cond = float(np.linalg.cond(J))
    cov = np.linalg.pinv(J.T @ J) * sigma2
    se = np.sqrt(np.diag(cov))
    from scipy.stats import t as student
    crit = float(student.ppf(1 - alpha / 2, dof))
    diagnostics = {}
    cond_value, diagnostics['jacobian_condition'] = diagnostic(cond, reason='Jacobian has zero singular values; condition is unbounded')
    if k == 1:
        max_corr, diagnostics['max_parameter_correlation'] = diagnostic(0, status='not_applicable', reason='A single parameter has no off-diagonal correlation')
    elif not identified or not fit.success:
        max_corr, diagnostics['max_parameter_correlation'] = diagnostic(0, status='not_identifiable' if not identified else 'fit_failed', reason='Individual parameter covariance is unavailable for a rank-deficient Jacobian or an unconverged fit')
    elif not (se > 0).all():
        max_corr, diagnostics['max_parameter_correlation'] = diagnostic(0, status='undefined', reason='Zero estimated parameter variance makes covariance normalization undefined; a zero-residual fit does not establish uncertainty')
    else:
        corr = cov / np.outer(se, se)
        max_corr, diagnostics['max_parameter_correlation'] = diagnostic(np.abs(corr - np.eye(k)).max(), reason='Parameter covariance normalization is not finite')
    res = fit.fun
    lag1, diagnostics['residual_lag1_autocorrelation'] = diagnostic(
        np.corrcoef(res[:-1], res[1:])[0, 1] if len(res) > 3 and res.std() > 0 else 0,
        status=None if len(res) > 3 and res.std() > 0 else 'undefined', reason='Residual correlation needs at least four observations and nonzero residual variation')
    rmse = float(np.sqrt(np.mean(res ** 2)))
    if not np.isfinite(fit.x).all() or not np.isfinite(rmse):
        raise ValueError('Calibration did not produce finite parameter estimates and fit error')
    flags = []
    if not identified or cond > 1e6 or max_corr is not None and max_corr > 0.98:
        flags.append(f'weakly identified (Jacobian rank {rank}/{k}, condition {cond:.2g}): the data cannot separate the parameters')
    if not fit.success:
        flags.append('fit did not converge; parameter inference is unavailable')
    for i in range(k):
        if np.isfinite(lo[i]) and abs(fit.x[i] - lo[i]) < 1e-6 * max(1, abs(lo[i])) or np.isfinite(hi[i]) and abs(fit.x[i] - hi[i]) < 1e-6 * max(1, abs(hi[i])):
            flags.append(f'{labels[i]} sits on its bound')
    if lag1 is not None and abs(lag1) > 0.5:
        flags.append(f'residuals are strongly autocorrelated (lag-1 {lag1:.2f}): the model misses structure the data contain')
    inference_status = 'computed' if identified and fit.success else ('not_reported_rank_deficient' if not identified else 'fit_failed')
    parameters = []
    for i in range(k):
        item = dict(name=labels[i], estimate=float(fit.x[i]), inference=dict(status=inference_status))
        if inference_status != 'computed':
            item['inference']['reason'] = 'Local individual intervals require a full-rank Jacobian and a converged fit'
        elif sigma2 == 0:
            item['inference'] = dict(status='zero_residual_variance', reason='Estimated noise variance is zero; degenerate local intervals exclude structural and measurement error')
        for field, value in [('std_error', se[i]), ('ci_low', fit.x[i] - crit * se[i]), ('ci_high', fit.x[i] + crit * se[i])]:
            item[field], info = diagnostic(value, status=None if inference_status == 'computed' else inference_status,
                                           reason='Individual inference is unavailable for this fitted Jacobian or fit status')
            if info['status'] not in ('computed', inference_status):
                item['inference'] = info
        parameters.append(item)
    out = dict(parameters=parameters, rmse=rmse, points_fitted=n_fit, jacobian_condition=cond_value, max_parameter_correlation=max_corr,
               residual_lag1_autocorrelation=lag1, converged=bool(fit.success), flags=flags,
               diagnostics=diagnostics, jacobian_rank=rank, fit_status='converged' if fit.success else 'failed',
               note='Confidence intervals are local and conditional on the model being right; they do not include structural error.')
    if holdout:
        pred = np.asarray(model(fit.x, x[n_fit:]), float)
        out['holdout'] = dict(points=holdout, rmse=float(np.sqrt(np.mean((pred - y[n_fit:]) ** 2))), fit_rmse=rmse)
    return out
