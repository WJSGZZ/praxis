"""Numerical probes for mathematical structure: dimensions, convexity, monotonicity, symmetry, scaling, invariants, network matrices.

A probe returns numerical candidate violations or sampled supporting evidence.
Neither floating-point arithmetic nor finite differences certify a refutation."""
from __future__ import annotations

import itertools
from typing import Callable, Sequence

import numpy as np
import sympy as sp
from modeling.contracts import finite_real


def _finite_function(f):
    return lambda x: finite_real(f(x))


def _finite_array(value):
    raw = np.asarray(value)
    if np.iscomplexobj(raw):
        raise ValueError('Probe comparison must be real')
    a = np.asarray(raw, float)
    if not np.isfinite(a).all():
        raise ValueError('Probe comparison must be finite')
    return a


def _points(bounds, n, rng):
    box = np.asarray(bounds, float)
    if box.ndim != 2 or box.shape[1] != 2 or not len(box) or isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 1:
        raise ValueError('A nonempty box and positive integer trials are required')
    lo, hi = box.T
    if (lo >= hi).any() or not np.isfinite(lo).all() or not np.isfinite(hi).all():
        raise ValueError('Each bound needs finite lower < upper')
    return lo + (hi - lo) * rng.random((n, len(lo)))


def check_convexity(f: Callable, bounds: Sequence[Sequence[float]], *, trials: int = 4000, tol: float = 1e-9, seed: int = 2027) -> dict:
    """Random midpoint/chord test of f(x) on a box. A violation is a numerical candidate, not a proof.

    Convex if f(t x + (1-t) y) <= t f(x) + (1-t) f(y) for all pairs; here only sampled pairs are tried."""
    f = _finite_function(f)
    if finite_real(tol, 'tol') < 0:
        raise ValueError('tol must be nonnegative')
    rng = np.random.default_rng(seed)
    x, y = _points(bounds, trials, rng), _points(bounds, trials, rng)
    t = rng.random(trials)
    fx = np.array([f(p) for p in x], float)
    fy = np.array([f(p) for p in y], float)
    fm = np.array([f(a * p + (1 - a) * q) for a, p, q in zip(t, x, y)], float)
    excess = _finite_array(fm - (t * fx + (1 - t) * fy))
    worst = int(np.argmax(excess))
    scale = max(1.0, float(np.abs(fx).max()))
    if excess[worst] > tol * scale:
        return dict(convex=False, proved=False, evidence='numerical_candidate', witness=dict(x=x[worst].tolist(), y=y[worst].tolist(), t=float(t[worst])),
                    violation=float(excess[worst]), note='Recheck this chord with exact arithmetic or a certified error bound before refuting convexity.')
    fneg = -fm - (t * -fx + (1 - t) * -fy)
    concave = bool(fneg.max() <= tol * scale)
    return dict(convex=True, proved=False, concave_also=concave, max_excess=float(excess[worst]), pairs=int(trials),
                note='No violation on sampled chords; this is evidence of convexity, not a proof.')


def check_monotone(f: Callable, bounds: Sequence[Sequence[float]], variable: int, *, trials: int = 2000, seed: int = 2027) -> dict:
    """Is f nondecreasing/nonincreasing in one variable, others fixed at random points?"""
    if isinstance(variable, bool) or not isinstance(variable, (int, np.integer)) or not 0 <= variable < len(bounds):
        raise ValueError('variable must index one of the declared bounds')
    f = _finite_function(f)
    rng = np.random.default_rng(seed)
    base = _points(bounds, trials, rng)
    lo, hi = bounds[variable]
    up = base.copy()
    a = lo + (hi - lo) * rng.random(trials)
    b = lo + (hi - lo) * rng.random(trials)
    base[:, variable], up[:, variable] = np.minimum(a, b), np.maximum(a, b)
    d = _finite_array([f(q) - f(p) for p, q in zip(base, up)])
    inc, dec = bool((d >= -1e-12).all()), bool((d <= 1e-12).all())
    if inc and dec:
        kind = 'constant'
    elif inc:
        kind = 'nondecreasing'
    elif dec:
        kind = 'nonincreasing'
    else:
        kind = 'not monotone'
    out = dict(kind=kind, proved=False, evidence='numerical_candidate' if kind == 'not monotone' else 'sampled_evidence', trials=int(trials),
               note='Sampled numerical changes are not a proof. Refuting monotonicity in both directions needs two certified violations; prove a direction by the derivative sign.')
    if kind == 'not monotone':
        i = int(np.argmax(np.abs(d)))
        out['witness'] = dict(low_point=base[i].tolist(), high_point=up[i].tolist(), change=float(d[i]))
        out['direction_witnesses'] = {direction: dict(low_point=base[j].tolist(), high_point=up[j].tolist(), change=float(d[j]))
                                     for direction, j in [('against_nondecreasing', int(np.argmin(d))), ('against_nonincreasing', int(np.argmax(d)))]}
    return out


def check_symmetry(f: Callable, bounds: Sequence[Sequence[float]], permutation: Sequence[int], *, trials: int = 2000, tol: float = 1e-9, seed: int = 2027) -> dict:
    """Is f(x) = f(x[permutation])? The box must be symmetric under the permutation for the test to be meaningful."""
    perm = list(permutation)
    if sorted(perm) != list(range(len(bounds))):
        raise ValueError('permutation must rearrange 0..n-1')
    if any(bounds[i] != bounds[j] for i, j in enumerate(perm)):
        raise ValueError('Bounds must be identical for variables exchanged by the permutation')
    f = _finite_function(f)
    if finite_real(tol, 'tol') < 0:
        raise ValueError('tol must be nonnegative')
    rng = np.random.default_rng(seed)
    x = _points(bounds, trials, rng)
    d = _finite_array([f(p) - f(p[perm]) for p in x])
    worst = int(np.argmax(np.abs(d)))
    scale = max(1.0, float(np.abs([f(p) for p in x[:50]]).max()))
    if abs(d[worst]) > tol * scale:
        return dict(symmetric=False, proved=False, evidence='numerical_candidate', witness=x[worst].tolist(), difference=float(d[worst]),
                    note='Numerical mismatch; exact arithmetic or certified error bounds are needed for a refutation.')
    return dict(symmetric=True, proved=False, trials=int(trials), note='No violation found; evidence, not proof.')


def scaling_exponents(f: Callable, point: Sequence[float], *, step: float = 1e-4) -> dict:
    """Local elasticity d log f / d log x_i at a positive point. Constant exponents across points suggest a power law."""
    f = _finite_function(f)
    x = np.asarray(point, float)
    if not np.isfinite(x).all() or finite_real(step, 'step') <= 0 or (x <= 0).any():
        raise ValueError('Elasticity needs positive coordinates')
    f0 = float(f(x))
    if f0 <= 0:
        raise ValueError('Elasticity needs f > 0 at the point')
    out = []
    for i in range(len(x)):
        up, dn = x.copy(), x.copy()
        up[i] *= np.exp(step)
        dn[i] *= np.exp(-step)
        out.append((np.log(float(f(up))) - np.log(float(f(dn)))) / (2 * step))
    return dict(exponents=_finite_array(out).tolist(), f=f0)


def check_power_law(f: Callable, bounds: Sequence[Sequence[float]], *, trials: int = 50, tol: float = 1e-5, seed: int = 2027) -> dict:
    """Does f(x) = C * prod x_i^a_i hold? Exponents must be the same at every sampled point."""
    f = _finite_function(f)
    if finite_real(tol, 'tol') < 0:
        raise ValueError('tol must be nonnegative')
    rng = np.random.default_rng(seed)
    pts = _points(bounds, trials, rng)
    if (pts <= 0).any():
        raise ValueError('Power-law test needs positive bounds')
    ex = np.array([scaling_exponents(f, p)['exponents'] for p in pts])
    spread = ex.max(0) - ex.min(0)
    if (spread < tol).all():
        return dict(power_law=True, proved=False, exponents=[float(v) for v in ex.mean(0)], max_spread=float(spread.max()),
                    criterion=f'elasticities equal at all {trials} sampled points within {tol:g}')
    return dict(power_law=False, proved=False, evidence='numerical_candidate', exponent_range=[[float(a), float(b)] for a, b in zip(ex.min(0), ex.max(0))],
                criterion=f'elasticities equal at all {trials} sampled points within {tol:g}', note='Finite-difference elasticities are numerical evidence, not a certified refutation.')


def check_invariant(rhs: Callable, invariant: Callable, bounds: Sequence[Sequence[float]], *, trials: int = 500, step: float = 1e-6,
                    tol: float = 1e-5, seed: int = 2027) -> dict:
    """For dx/dt = rhs(x), is g(x) conserved? Test dg/dt = grad g . rhs ~ 0 at random states (central differences).

    The rate is judged relative to |grad g| |rhs|, so the verdict does not depend on the units of g."""
    if finite_real(tol, 'tol') < 0:
        raise ValueError('tol must be nonnegative')
    if finite_real(step, 'step') <= 0:
        raise ValueError('step must be positive')
    rng = np.random.default_rng(seed)
    x = _points(bounds, trials, rng)
    n = x.shape[1]
    invariant = _finite_function(invariant)
    rel, raw = [], []
    for p in x:
        grad = np.empty(n)
        for i in range(n):
            up, dn = p.copy(), p.copy()
            up[i] += step
            dn[i] -= step
            grad[i] = (invariant(up) - invariant(dn)) / (2 * step)
        v = _finite_array(rhs(p))
        if v.shape != p.shape:
            raise ValueError('rhs must have one finite component per state')
        grad = _finite_array(grad)
        rate = finite_real(grad @ v)
        raw.append(rate)
        rel.append(finite_real(abs(rate) / (np.linalg.norm(grad) * np.linalg.norm(v) + 1e-300)))
    worst = int(np.argmax(rel))
    if rel[worst] <= tol:
        return dict(conserved=True, proved=False, max_relative_rate=float(rel[worst]), trials=int(trials),
                    note='Rate of change is zero at every sampled state; evidence, not proof.')
    return dict(conserved=False, proved=False, evidence='numerical_candidate', witness=x[worst].tolist(), rate=float(raw[worst]), relative_rate=float(rel[worst]),
                note='The rate uses finite differences; certify the derivative and its error before refuting conservation.')


def buckingham_pi(dimension_matrix: Sequence[Sequence[float]], names: Sequence[str]) -> dict:
    """Dimensionless groups from a dimension matrix (rows: base dimensions, columns: variables) by exact null-space computation.

    Each group is a vector of exponents; the number of groups is n_variables - rank. Dimensional analysis finds candidate
    groups; it does not tell which of them matter."""
    array = np.asarray(dimension_matrix, dtype=object)
    if array.ndim != 2 or not all(array.shape):
        raise ValueError('dimension_matrix must be a nonempty 2-D matrix')
    if array.shape[1] != len(names) or any(not isinstance(name, str) or not name.strip() for name in names) or len(set(names)) != len(names):
        raise ValueError('One unique nonempty name per column')
    try:
        # Decimal spellings of dimensions are exact rationals, including 1.0.
        # Do not send SymPy Float terms to integer-denominator extraction.
        m = sp.Matrix([[sp.Rational(str(value)) for value in row] for row in array])
    except (ValueError, TypeError) as error:
        raise ValueError('Dimension exponents must be finite rational numbers') from error
    if any(value.is_finite is not True for value in m):
        raise ValueError('Dimension exponents must be finite rational numbers')
    basis = m.nullspace()
    groups = []
    for v in basis:
        v = v * sp.ilcm(*[term.q for term in v])
        g = sp.gcd(list(v))
        v = v / g if g != 0 else v
        groups.append({n: int(e) for n, e in zip(names, v) if e != 0})
    return dict(rank=int(m.rank()), n_groups=len(groups), groups=groups)


def _two_per_column_partition(A):
    """Commoner/Heller-Tompkins: a {0,+-1} matrix with at most two nonzeros per column is totally unimodular iff its rows can be split
    into two classes so that, in every column with two nonzeros, equal signs fall in different classes and opposite signs in the same."""
    m, n = A.shape
    parent = list(range(m))
    parity = [0] * m  # parity relative to parent

    def find(i):
        if parent[i] == i:
            return i, 0
        root, par = find(parent[i])
        parent[i] = root
        parity[i] ^= par
        return root, parity[i]

    for j in range(n):
        rows = np.flatnonzero(A[:, j])
        if len(rows) == 2:
            r1, r2 = rows
            need = 1 if A[r1, j] == A[r2, j] else 0
            (a, pa), (b, pb) = find(r1), find(r2)
            if a == b:
                if pa ^ pb != need:
                    return False
            else:
                parent[a] = b
                parity[a] = pa ^ pb ^ need
    return True


def is_network_matrix(a: Sequence[Sequence[float]], *, brute_limit: int = 12) -> dict:
    """Is the constraint matrix totally unimodular (so LP vertices are integral when the right-hand side is integral)?

    Exact for matrices with entries in {-1,0,1} and at most two nonzeros per column (directed or bipartite incidence matrices
    pass); for other small matrices every square submatrix determinant is checked; larger ones are reported as undecided."""
    A = np.asarray(a, float)
    if A.ndim != 2 or not all(A.shape) or not np.isfinite(A).all():
        raise ValueError('A must be a nonempty finite 2-D matrix')
    if isinstance(brute_limit, bool) or not isinstance(brute_limit, (int, np.integer)) or not 1 <= brute_limit <= 12:
        raise ValueError('brute_limit must be an integer from 1 to 12')
    if not np.isin(A, [-1, 0, 1]).all():
        return dict(totally_unimodular=False, proved=True, reason='entry outside {-1,0,1}')
    if (np.count_nonzero(A, axis=0) <= 2).all():
        ok = _two_per_column_partition(A)
        return dict(totally_unimodular=bool(ok), proved=True, method='at most two nonzeros per column: row-partition criterion')
    m, n = A.shape
    if max(m, n) <= brute_limit:
        for k in range(1, min(m, n) + 1):
            for rows in itertools.combinations(range(m), k):
                for cols in itertools.combinations(range(n), k):
                    determinant = sp.Matrix(A[np.ix_(rows, cols)].astype(int).tolist()).det()
                    if abs(determinant) > 1:
                        return dict(totally_unimodular=False, proved=True, witness=dict(rows=list(rows), columns=list(cols), determinant=int(determinant)))
        return dict(totally_unimodular=True, proved=True, method='every square submatrix checked with exact integer determinants')
    return dict(totally_unimodular=None, proved=False, note='Too large to enumerate; look for an incidence or interval structure.')
