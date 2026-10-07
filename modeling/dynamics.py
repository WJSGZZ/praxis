"""Equilibria and their stability for dx/dt = f(x), and a linear-Gaussian Kalman filter."""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
from scipy.optimize import fsolve


def jacobian(f: Callable, x: np.ndarray, step: float = 1e-6) -> np.ndarray:
    x = np.asarray(x, float)
    n = len(x)
    J = np.empty((n, n))
    for j in range(n):
        h = step * max(1.0, abs(x[j]))
        up, dn = x.copy(), x.copy()
        up[j] += h
        dn[j] -= h
        J[:, j] = (np.asarray(f(up), float) - np.asarray(f(dn), float)) / (2 * h)
    return J


def classify(eigenvalues: np.ndarray, tol: float = 1e-7) -> str:
    re, im = eigenvalues.real, eigenvalues.imag
    if (np.abs(re) <= tol).any():
        return 'non-hyperbolic (linearization is inconclusive)'
    if (re < 0).all():
        return 'stable focus' if (np.abs(im) > tol).any() else 'stable node'
    if (re > 0).all():
        return 'unstable focus' if (np.abs(im) > tol).any() else 'unstable node'
    return 'saddle'


def equilibria(f: Callable, bounds: Sequence[Sequence[float]], *, starts: int = 200, seed: int = 2027, tol: float = 1e-8) -> dict:
    """Find roots of f in a box from random starts and classify them by the Jacobian's eigenvalues.

    A search from finitely many starts can miss equilibria; the list is what was found, not a proof of completeness."""
    rng = np.random.default_rng(seed)
    lo, hi = np.asarray(bounds, float).T
    found: list[np.ndarray] = []
    for _ in range(starts):
        x0 = lo + (hi - lo) * rng.random(len(lo))
        x, info, ok, _ = fsolve(lambda v: np.asarray(f(v), float), x0, full_output=True, xtol=1e-12)
        if ok == 1 and np.abs(f(x)).max() < tol and (x >= lo - 1e-9).all() and (x <= hi + 1e-9).all():
            if not any(np.linalg.norm(x - y) < 1e-6 * max(1, np.linalg.norm(y)) for y in found):
                found.append(x)
    out = []
    for x in sorted(found, key=lambda v: tuple(np.round(v, 9))):
        eig = np.linalg.eigvals(jacobian(f, x))
        out.append(dict(point=x.tolist(), eigenvalues=[complex(v).__repr__() if abs(v.imag) > 1e-12 else float(v.real) for v in eig], kind=classify(eig)))
    return dict(equilibria=out, starts=starts, note='Found from random starts inside the box; completeness is not guaranteed.')


def kalman_filter(F, H, Q, R, x0, P0, observations) -> dict:
    """Linear-Gaussian filter x_{t+1} = F x_t + w (cov Q), y_t = H x_t + v (cov R). Missing observations (NaN rows) skip the update.

    Returns filtered means and covariances, the one-step predictions, and the Gaussian log-likelihood of the observations."""
    F, H, Q, R = (np.atleast_2d(np.asarray(a, float)) for a in (F, H, Q, R))
    x, P = np.asarray(x0, float).reshape(-1), np.atleast_2d(np.asarray(P0, float))
    Y = np.asarray(observations, float)
    Y = Y.reshape(len(Y), -1)
    means, covs, preds, ll = [], [], [], 0.0
    for y in Y:
        x_pred, P_pred = F @ x, F @ P @ F.T + Q
        preds.append(x_pred.copy())
        if np.isnan(y).any():
            x, P = x_pred, P_pred
        else:
            S = H @ P_pred @ H.T + R
            K = P_pred @ H.T @ np.linalg.inv(S)
            r = y - H @ x_pred
            x, P = x_pred + K @ r, (np.eye(len(x)) - K @ H) @ P_pred
            ll += -.5 * (len(y) * np.log(2 * np.pi) + np.linalg.slogdet(S)[1] + r @ np.linalg.solve(S, r))
        means.append(x.copy())
        covs.append(P.copy())
    return dict(filtered_mean=np.array(means).tolist(), filtered_cov=np.array(covs).tolist(), predicted_mean=np.array(preds).tolist(), log_likelihood=float(ll))
