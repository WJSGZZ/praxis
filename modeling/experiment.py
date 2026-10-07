"""Experimental mathematics: hunt for counterexamples, test conjectures at high precision, guess recurrences, polynomials and relations.

Everything here produces candidates and refutations. A pattern that survives the search is a conjecture until it is proved."""
from __future__ import annotations

import ast
import itertools
from fractions import Fraction
from typing import Callable, Sequence

import mpmath as mp
import numpy as np
import sympy as sp


def find_counterexample(claim: Callable, domain: Sequence[tuple], *, trials: int = 20000, exhaustive_limit: int = 200000, seed: int = 2027) -> dict:
    """Search for an input where claim(*x) is False (or raises).

    domain: one entry per argument: ('int', lo, hi) inclusive, or ('real', lo, hi). If every argument is an integer range and the
    product of sizes is at most exhaustive_limit, all cases are checked and 'no counterexample' is a proof for that domain.
    Otherwise points are sampled, edges first. A found counterexample is shrunk to a simpler one that still fails."""
    for spec in domain:
        if spec[0] not in ('int', 'real') or spec[1] > spec[2]:
            raise ValueError("Each domain entry must be ('int'|'real', lo, hi) with lo <= hi")

    def fails(x):
        try:
            return not bool(claim(*x))
        except Exception:
            return True

    all_int = all(s[0] == 'int' for s in domain)
    size = int(np.prod([s[2] - s[1] + 1 for s in domain], dtype=float)) if all_int else None
    if all_int and size <= exhaustive_limit:
        for x in itertools.product(*[range(s[1], s[2] + 1) for s in domain]):
            if fails(x):
                return dict(found=True, counterexample=list(x), shrunk=list(_shrink(fails, list(x), domain)), cases=None, exhaustive=True)
        return dict(found=False, proved_for_domain=True, cases=size)
    rng = np.random.default_rng(seed)
    corners = [[s[1], s[2]] for s in domain]
    candidates = [list(c) for c in itertools.product(*corners)][:256]
    tried = 0
    for x in candidates:
        tried += 1
        if fails(x):
            return dict(found=True, counterexample=x, shrunk=list(_shrink(fails, list(x), domain)), cases=tried, exhaustive=False)
    for _ in range(trials):
        x = [int(rng.integers(s[1], s[2] + 1)) if s[0] == 'int' else float(rng.uniform(s[1], s[2])) for s in domain]
        tried += 1
        if fails(x):
            return dict(found=True, counterexample=x, shrunk=list(_shrink(fails, x, domain)), cases=tried, exhaustive=False)
    return dict(found=False, proved_for_domain=False, cases=tried, note='No counterexample among the cases tried; the claim is not proved.')


def _shrink(fails, x, domain):
    """Greedy shrinking toward zero (or the nearest bound), keeping the failure."""
    x = list(x)
    changed = True
    while changed:
        changed = False
        for i, spec in enumerate(domain):
            target = min(max(0, spec[1]), spec[2])
            for candidate in _steps(x[i], target, spec[0]):
                y = x.copy()
                y[i] = candidate
                if fails(y):
                    x, changed = y, True
                    break
    return x


def _steps(value, target, kind):
    if value == target:
        return
    if kind == 'int':
        seen = []
        step = abs(value - target)
        while step >= 1:
            c = value - int(np.sign(value - target)) * step
            if c != value and c not in seen:
                seen.append(c)
            step //= 2
        yield from sorted(seen, key=lambda c: abs(c - target))
    else:
        for frac in (1.0, 0.5, 0.25, 0.1):
            c = target + (value - target) * (1 - frac)
            if c != value:
                yield round(c, 6)


def test_conjecture(lhs: Callable, rhs: Callable, relation: str, bounds: Sequence[Sequence[float]], *, points: int = 2000, dps: int = 40,
                    tolerance: float = 1e-25, seed: int = 2027) -> dict:
    """Test lhs(*x) (relation) rhs(*x) at random points with mpmath at dps digits. relation: '==', '<=', '>='.

    lhs and rhs receive mpmath numbers; use mpmath functions (mp.sin, mp.exp...) inside them. An equation is judged
    by the worst absolute difference, an inequality by the worst violation."""
    if relation not in ('==', '<=', '>='):
        raise ValueError("relation must be '==', '<=' or '>='")
    rng = np.random.default_rng(seed)
    old = mp.mp.dps
    mp.mp.dps = dps
    try:
        worst, where = mp.mpf(0), None
        for _ in range(points):
            x = [mp.mpf(float(rng.uniform(lo, hi))) for lo, hi in bounds]
            a, b = lhs(*x), rhs(*x)
            gap = abs(a - b) if relation == '==' else (a - b if relation == '<=' else b - a)
            if gap > worst:
                worst, where = gap, [float(v) for v in x]
        if worst > tolerance:
            return dict(holds=False, proved=True, worst_violation=float(worst), at=where)
        return dict(holds=True, proved=False, points=points, digits=dps, note='Holds at every tested point; a conjecture, not a theorem.')
    finally:
        mp.mp.dps = old


def guess_linear_recurrence(sequence: Sequence, max_order: int = 6, holdout: int = 0) -> dict:
    """Smallest constant-coefficient linear recurrence a_n = c_1 a_{n-1} + ... + c_d a_{n-d} fitting the data exactly (rationals).

    Needs at least 2d+2 terms so that the fit is checked on more equations than unknowns; otherwise the order is not tested."""
    full = [sp.Rational(Fraction(x).limit_denominator(10 ** 12)) if not isinstance(x, sp.Basic) else x for x in sequence]
    if holdout < 0 or holdout >= len(full):
        raise ValueError('holdout must be between 0 and len(sequence) - 1')
    a, held = (full[:len(full) - holdout], full[len(full) - holdout:]) if holdout else (full, [])
    for d in range(1, max_order + 1):
        if len(a) < 2 * d + 2:
            return dict(found=False, reason=f'need at least {2 * d + 2} terms to test order {d}', tested_up_to=d - 1)
        rows = [[a[n - i] for i in range(1, d + 1)] for n in range(d, len(a))]
        rhs = [a[n] for n in range(d, len(a))]
        m, b = sp.Matrix(rows), sp.Matrix(rhs)
        try:
            sol, params = m.gauss_jordan_solve(b)
        except ValueError:
            continue
        if params.shape[0] == 0:
            out = dict(found=True, order=d, coefficients=[str(c) for c in sol], equations=len(rhs), unknowns=d,
                       note='Fits every equation; still a conjecture beyond the data.')
            if holdout:
                coeffs = [sp.Rational(c) for c in sol]
                bad = [len(a) + i for i, v in enumerate(held) if v != sum(coeffs[j] * (a + held)[len(a) + i - 1 - j] for j in range(d))]
                out.update(holdout_terms=holdout, holdout_mismatches=bad, holdout_ok=not bad)
            return out
    return dict(found=False, tested_up_to=max_order)


def guess_polynomial(sequence: Sequence, max_degree: int = 8) -> dict:
    """Is a_n (n = 0, 1, ...) a polynomial in n? Uses finite differences; needs degree+3 terms to test a degree."""
    a = [sp.nsimplify(x) for x in sequence]
    diffs = a
    for d in range(0, max_degree + 1):
        if len(a) < d + 3:
            return dict(found=False, reason=f'need at least {d + 3} terms to test degree {d}', tested_up_to=d - 1)
        if all(v == diffs[0] for v in diffs):
            n = sp.symbols('n')
            poly = sp.interpolate(list(zip(range(len(a[:d + 1])), a[:d + 1])), n) if d > 0 else a[0]
            if all(poly.subs(n, i) == a[i] for i in range(len(a))):
                return dict(found=True, degree=d, polynomial=str(sp.factor(poly)), expanded=str(sp.expand(poly)))
        diffs = [diffs[i + 1] - diffs[i] for i in range(len(diffs) - 1)]
    return dict(found=False, tested_up_to=max_degree)


def _safe_eval(expression, scope):
    """Evaluate arithmetic on the names in scope; any other syntax (attribute access, subscripts, lambdas...) is rejected."""
    tree = ast.parse(expression, mode='eval')
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise ValueError('Only numeric constants are allowed')
        elif isinstance(node, ast.Name):
            if node.id not in scope:
                raise ValueError(f'Unknown name: {node.id}')
        elif isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in scope and not node.keywords):
                raise ValueError('Only simple calls to the listed functions are allowed')
        elif not isinstance(node, allowed):
            raise ValueError(f'Disallowed syntax: {type(node).__name__}')
    return eval(compile(tree, '<expression>', 'eval'), {'__builtins__': {}}, dict(scope))


def find_relation(value: str, constants: dict[str, str], *, dps: int = 50, max_coeff: int = 1000) -> dict:
    """Integer relation c0*value + sum ci*constant_i = 0 by PSLQ. value and constants are decimal strings or mpmath expressions
    (e.g. 'pi**2/6', 'zeta(2)'), evaluated at dps digits. A relation with small coefficients and a tiny residual is a strong hint
    but is not a proof; very long coefficient vectors mean 'no relation found'."""
    old = mp.mp.dps
    mp.mp.dps = dps
    try:
        scope = {k: getattr(mp, k) for k in ('pi', 'e', 'euler', 'catalan', 'zeta', 'log', 'sqrt', 'exp', 'phi', 'sin', 'cos', 'atan')}
        v = mp.mpmathify(_safe_eval(value, scope)) if not _is_number(value) else mp.mpf(value)
        values = [v] + [mp.mpmathify(_safe_eval(c, scope)) if not _is_number(c) else mp.mpf(c) for c in constants.values()]
        rel = mp.pslq(values, maxcoeff=max_coeff, maxsteps=100000)
        if rel is None:
            return dict(found=False, digits=dps)
        residual = abs(sum(r * x for r, x in zip(rel, values)))
        return dict(found=True, coefficients={'value': int(rel[0]), **{k: int(r) for k, r in zip(constants, rel[1:])}},
                    residual=float(residual), digits=dps, note='Relation found by PSLQ; verify analytically before using it.')
    finally:
        mp.mp.dps = old


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def check_linear_recurrence(sequence: Sequence, coefficients: Sequence, *, order_bound: int | None = None) -> dict:
    """Does a_n = c_1 a_{n-1} + ... + c_d a_{n-d} hold for every n >= d in the data? Reports the failing indices.

    If the sequence is known to satisfy SOME constant-coefficient linear recurrence of order at most `order_bound` (for example it equals
    u^T M^n v for an N x N matrix M, so N is a bound by Cayley-Hamilton), then the difference b_n = a_n - sum c_i a_{n-i} satisfies one of
    order at most order_bound + d. Vanishing on order_bound + d consecutive terms then proves it vanishes for all n, so a clean check on
    that many terms is a complete proof, not just evidence."""
    a = [sp.nsimplify(x) for x in sequence]
    c = [sp.nsimplify(x) for x in coefficients]
    d = len(c)
    if len(a) <= d:
        raise ValueError('Need more terms than coefficients')
    bad = [n for n in range(d, len(a)) if a[n] != sum(c[i] * a[n - 1 - i] for i in range(d))]
    out = dict(order=d, equations=len(a) - d, mismatches=bad, holds_on_data=not bad)
    if order_bound is not None:
        needed = order_bound + d
        out.update(order_bound=order_bound, terms_needed=needed, proof_by_finite_check=bool(not bad and len(a) - d >= needed),
                   statement='Complete proof if the order bound is itself justified (e.g. by a transfer matrix of that size); otherwise it is evidence.')
    return out
