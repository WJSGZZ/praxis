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
