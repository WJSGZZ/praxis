"""Fit model parameters to data, and say honestly what the data can and cannot determine."""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
from scipy.optimize import least_squares
from modeling.contracts import diagnostic


def calibrate(model: Callable[[np.ndarray, np.ndarray], np.ndarray], x: Sequence[float], y: Sequence[float], theta0: Sequence[float], *,
              bounds: Sequence[Sequence[float]] | None = None, names: Sequence[str] | None = None, holdout: int = 0, alpha: float = 0.05,
              multistart: int = 0, holdout_scheme: str = 'tail', seed: int = 2027) -> dict:
    """Least-squares calibration of model(theta, x) to (x, y), with an identifiability and hold-out report.

    Reported: estimates with approximate confidence intervals (local, from the Jacobian, valid if the model is right and the noise
    independent), the Jacobian's condition number and the largest parameter correlation (large values mean the data cannot separate the
    parameters), the residual lag-1 autocorrelation (structure left in the residuals), the rms error, and, if `holdout` > 0, the rms
    error on the last `holdout` points that were kept out of the fit. Undefined diagnostics are null with explicit reasons;
    rank-deficient or failed fits do not report individual parameter intervals. Flags list each warning.
    multistart=0 retains one theta0 fit; a value >=8 adds that many uniform random starts in a finite box.
    The best converged training fit is selected before any holdout response is evaluated. Random holdout uses the
    seeded split; it is appropriate for exchangeable observations, not automatically for ordered/time data.
    A best-basin fraction describes these sampled starts, never a global-optimality probability."""
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
    if isinstance(holdout, bool) or not isinstance(holdout, (int, np.integer)) or holdout < 0 or holdout >= len(x) - k:
        raise ValueError('holdout must leave more fitted points than parameters')
    n_fit = len(x) - holdout
    if holdout_scheme not in ('tail', 'random'):
        raise ValueError("holdout_scheme must be 'tail' or 'random'")
    if isinstance(multistart, (bool, np.bool_)) or not isinstance(multistart, (int, np.integer)) or multistart != 0 and not 8 <= multistart <= 1000:
        raise ValueError('multistart must be 0 or an integer from 8 to 1000 random starts, in addition to theta0')
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError('seed must be a nonnegative integer')
    box = np.column_stack([np.full(k, -np.inf), np.full(k, np.inf)]) if bounds is None else np.asarray(bounds, float)
    if box.shape != (k, 2) or np.isnan(box).any() or np.any(box[:, 0] >= box[:, 1]):
        raise ValueError('bounds must contain one strictly ordered lower/upper pair per parameter')
    lo, hi = box.T
    if (theta0 < lo).any() or (theta0 > hi).any():
        raise ValueError('theta0 must lie within the parameter bounds')
    if multistart and not np.isfinite(box).all():
        raise ValueError('multistart requires finite parameter bounds for uniform random starts')
    rng_split, rng_starts = [np.random.default_rng(s) for s in np.random.SeedSequence(int(seed)).spawn(2)]
    hold_indices = np.arange(n_fit, len(x)) if holdout_scheme == 'tail' else np.sort(rng_split.choice(len(x), holdout, replace=False))
    fit_indices = np.setdiff1d(np.arange(len(x)), hold_indices)
    x_fit, y_fit = x[fit_indices], y[fit_indices]

    def residual(theta):
        prediction = np.asarray(model(theta, x_fit.copy()), float)
        if prediction.shape != y_fit.shape or not np.isfinite(prediction).all():
            raise ValueError('model must return one finite prediction per x value; broadcasting is not allowed')
        result = prediction - y_fit
        if not np.isfinite(result).all():
            raise ValueError('model residuals exceed finite numerical range')
        return result

    starts = [theta0] + [rng_starts.uniform(lo, hi) for _ in range(multistart)]
    attempts, fits = [], []
    for index, start in enumerate(starts):
        record = dict(start=index, kind='theta0' if index == 0 else 'random', theta_initial=start.tolist())
        attempts.append(record)
        try:
            candidate = least_squares(residual, start, bounds=(lo, hi))
            if not np.isfinite(candidate.cost) or not np.isfinite(candidate.x).all():
                raise ValueError('Calibration produced a nonfinite cost or parameter vector')
            record.update(converged=bool(candidate.success), status=int(candidate.status),
                          cost=float(candidate.cost), theta=candidate.x.tolist(), message=str(candidate.message))
            fits.append((index, candidate))
        except ValueError as exc:
            if index == 0:
                raise
            record.update(converged=False, error=str(exc))
    accepted = [(index, candidate) for index, candidate in fits if candidate.success]
    best_index, fit = min(accepted or fits, key=lambda pair: pair[1].cost)
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
    if multistart:
        # A basin needs agreement in parameter location as well as objective.
        # Equivalent but distinct symmetric minimizers remain distinct basins.
        same_basin = [i for i, candidate in accepted
                      if abs(candidate.cost-fit.cost) <= 1e-6*(1+abs(fit.cost))
                      and np.linalg.norm(candidate.x-fit.x) <= 1e-4*(1+np.linalg.norm(fit.x))]
        random_hits = sum(index != 0 for index in same_basin)
        out['multistart'] = dict(random_starts=int(multistart), total_starts=len(starts), seed=int(seed),
                                 best_start=best_index, best_cost=float(fit.cost), attempts=attempts,
                                 best_basin_random_hits=random_hits, best_basin_fraction=random_hits/int(multistart),
                                 converged_starts=len(accepted),
                                 basin_definition='Converged fits within 1e-6*(1+abs(best_cost)) in cost and 1e-4*(1+norm(best_theta)) in Euclidean parameter distance.',
                                 note='Best-basin fraction uses all random starts as denominator, including failed starts; theta0 is reported separately. Uniform finite-box starts and local least squares do not certify a global optimum.')
    if holdout:
        pred = np.asarray(model(fit.x, x[hold_indices].copy()), float)
        if pred.shape != y[hold_indices].shape or not np.isfinite(pred).all():
            raise ValueError('model must return one finite holdout prediction per x value')
        holdout_rmse = float(np.sqrt(np.mean((pred - y[hold_indices]) ** 2)))
        if not np.isfinite(holdout_rmse):
            raise ValueError('Holdout error exceeds finite numerical range')
        out['holdout'] = dict(points=holdout, rmse=holdout_rmse, fit_rmse=rmse,
                              scheme=holdout_scheme, seed=int(seed), fit_indices=fit_indices.tolist(),
                              holdout_indices=hold_indices.tolist(), selection='Training residual sum of squares only; holdout responses are used once after selecting the fit.')
    return out
