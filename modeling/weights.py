"""Index weights: AHP consistency and entropy dispersion. Both are conventions, not measurements of importance."""
import numpy as np

# Saaty's random-index table; it is a convention and only defined here up to order 10.
RANDOM_INDEX = {1: 0., 2: 0., 3: .58, 4: .90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def ahp(matrix, *, tolerance=1e-6):
    """Weights from the principal eigenvector of a positive reciprocal pairwise-comparison matrix.

    The conventional rule CR < 0.1 is a screening heuristic, not a proof that the judgements are sound."""
    a = np.asarray(matrix, float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or not 1 <= a.shape[0] <= 10:
        raise ValueError('Pairwise matrix must be square with order 1-10')
    if (a <= 0).any() or not np.allclose(a * a.T, 1., atol=tolerance):
        raise ValueError('Matrix must be positive and reciprocal (a_ij * a_ji = 1)')
    values, vectors = np.linalg.eig(a)
    k = int(np.argmax(values.real))
    w = np.abs(vectors[:, k].real); w /= w.sum()
    n = a.shape[0]
    lam = float(values[k].real)
    ci = (lam - n) / (n - 1) if n > 1 else 0.
    cr = ci / RANDOM_INDEX[n] if RANDOM_INDEX[n] else 0.
    return dict(weights=w.tolist(), lambda_max=lam, consistency_index=ci, consistency_ratio=cr, acceptable=bool(cr < .1))


def entropy_weights(matrix, directions=None):
    """Weights from the dispersion of each column after min-max scaling.

    A column with no spread gets weight zero. A large weight means the column differs a lot among
    alternatives, not that it matters more to the decision."""
    x = np.asarray(matrix, float)
    if x.ndim != 2 or x.shape[0] < 2 or not np.isfinite(x).all():
        raise ValueError('Need a finite matrix with at least two alternatives')
    m, n = x.shape
    directions = np.ones(n) if directions is None else np.asarray(directions, float)
    if directions.shape != (n,) or not np.isin(directions, (-1., 1.)).all():
        raise ValueError('directions must be +1 (larger is better) or -1 per column')
    span = x.max(0) - x.min(0)
    scaled = np.zeros_like(x)
    live = span > 0
    z = (x[:, live] - x[:, live].min(0)) / span[live]
    scaled[:, live] = np.where(directions[live] > 0, z, 1. - z)
    p = (scaled + 1e-12) / (scaled + 1e-12).sum(0)
    entropy = -(p * np.log(p)).sum(0) / np.log(m)
    d = np.where(live, 1. - entropy, 0.)
    if d.sum() <= 0:
        raise ValueError('No column has spread; weights are undefined')
    return dict(weights=(d / d.sum()).tolist(), entropy=entropy.tolist(), columns_without_spread=[int(i) for i in np.flatnonzero(~live)])
