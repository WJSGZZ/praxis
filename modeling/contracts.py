"""Small numerical input contracts shared by probability and probe tools."""
import numpy as np


def finite_real(value, name='evaluation'):
    a = np.asarray(value)
    if a.ndim != 0 or np.iscomplexobj(a):
        raise ValueError(f'{name} must be a finite real scalar')
    result = float(a)
    if not np.isfinite(result):
        raise ValueError(f'{name} must be a finite real scalar')
    return result


def stochastic_matrix(value):
    p = np.asarray(value, float)
    if p.ndim != 2 or not p.shape[0] or p.shape[0] != p.shape[1] or not np.isfinite(p).all() or (p < 0).any() or not np.allclose(p.sum(axis=1), 1, atol=1e-10, rtol=0):
        raise ValueError('P must be a nonempty finite nonnegative square row-stochastic matrix')
    return p


def diagnostic(value, *, reason='Diagnostic is not finite', status=None):
    """Return a JSON-safe diagnostic value and its explicit interpretation.

    This is for optional diagnostics, never objectives or solution estimates.
    The caller supplies a mathematical reason for undefined or unbounded cases.
    """
    if status is not None:
        return None, dict(status=status, reason=reason)
    value = float(value)
    if np.isfinite(value):
        return value, dict(status='computed')
    return None, dict(status='unbounded' if np.isinf(value) else 'undefined', reason=reason)
