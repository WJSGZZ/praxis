"""Linear and mixed-integer programs with solver status and a checkable certificate."""
import numpy as np
from fractions import Fraction
from scipy.optimize import linprog, milp, linear_sum_assignment, LinearConstraint, Bounds
from scipy.sparse import issparse, vstack as sp_vstack
from modeling.contracts import finite_real, diagnostic


def _bounds(bounds, n):
    if bounds is None:
        return [(0, None)] * n
    if len(bounds) != n or any(len(bound) != 2 for bound in bounds):
        raise ValueError('bounds must contain one lower/upper pair per variable')
    normalized = []
    for lo, hi in bounds:
        lo = None if lo is None or lo == -np.inf else float(lo)
        hi = None if hi is None or hi == np.inf else float(hi)
        if ((lo is not None and not np.isfinite(lo)) or (hi is not None and not np.isfinite(hi))
                or lo is not None and hi is not None and lo > hi):
            raise ValueError('bounds must be ordered finite endpoints or unbounded None/-inf/+inf')
        normalized.append((lo, hi))
    return normalized


def _with_ge(A_ub, b_ub, A_ge, b_ge):
    """Append rows A_ge x >= b_ge to the <= rows (as -A_ge x <= -b_ge); returns the merged matrices and the number of original <= rows."""
    n_ub = 0 if b_ub is None else len(b_ub)
    if A_ge is None:
        return A_ub, b_ub, n_ub
    sparse = issparse(A_ge) or (A_ub is not None and issparse(A_ub))
    A = -(A_ge if issparse(A_ge) else np.asarray(A_ge, float))
    b = -np.asarray(b_ge, float)
    if A_ub is not None:
        A = sp_vstack([A_ub, A], format='csr') if sparse else np.vstack([np.asarray(A_ub, float), A])
        b = np.r_[np.asarray(b_ub, float), b]
    return A, b, n_ub


def _scaled_rows(A, b, n):
    """Scale each complete row before HiGHS can discard tiny coefficients."""
    if A is None:
        if b is not None and len(b):
            raise ValueError('A constraint right-hand side requires its matrix')
        return None, None, None
    matrix = A.astype(float) if issparse(A) else np.asarray(A, float)
    rhs = np.asarray(b, float)
    if not matrix.size and rhs.shape == (0,):
        return None, None, None
    if matrix.ndim != 2 or matrix.shape[1] != n or rhs.shape != (matrix.shape[0],):
        raise ValueError('Constraint matrices and right-hand sides must match the objective dimensions')
    coefficients = matrix.data if issparse(matrix) else matrix
    if not np.isfinite(coefficients).all() or not np.isfinite(rhs).all():
        raise ValueError('Constraint coefficients and right-hand sides must be finite')
    # Scale by the smallest nonzero coefficient/RHS, rather than the largest:
    # a large coefficient on a fixed-zero variable must not erase a small active
    # coefficient. Every nonzero transformed coefficient then has magnitude >=1.
    if issparse(matrix):
        matrix = matrix.tocsr()
        row_ids = np.repeat(np.arange(matrix.shape[0]), np.diff(matrix.indptr))
        smallest = np.full(matrix.shape[0], np.inf)
        nonzero = matrix.data != 0
        np.minimum.at(smallest, row_ids[nonzero], np.abs(matrix.data[nonzero]))
    else:
        smallest = np.where(matrix != 0, np.abs(matrix), np.inf).min(axis=1)
    scale = np.minimum(smallest, np.where(rhs != 0, np.abs(rhs), np.inf))
    scale[np.isinf(scale)] = 1
    if issparse(matrix):
        scaled = matrix.tocsr(copy=True)
        row_ids = np.repeat(np.arange(matrix.shape[0]), np.diff(scaled.indptr))
        scaled.data /= scale[row_ids]
    else:
        scaled = matrix/scale[:, None]
    normalized_rhs = rhs/scale
    coefficients = scaled.data if issparse(scaled) else scaled
    if not np.isfinite(coefficients).all() or not np.isfinite(normalized_rhs).all():
        raise ValueError('Constraint dynamic range exceeds finite numerical scaling')
    return scaled, normalized_rhs, scale


def _primal_violation(x, A, b, E, e, bounds):
    values = [0.0]
    if A is not None:
        activity = abs(A) @ np.abs(x)
        reference = np.maximum(np.abs(b), activity)
        reference = np.where(reference > 0, reference, 1)
        values.append(float(np.max((A @ x - b)/reference)))
    if E is not None:
        activity = abs(E) @ np.abs(x)
        reference = np.maximum(np.abs(e), activity)
        reference = np.where(reference > 0, reference, 1)
        values.append(float(np.max(np.abs(E @ x - e)/reference)))
    for i, (lo, hi) in enumerate(bounds):
        if lo is not None:
            values.append((lo - x[i])/max(1.0, abs(lo)))
        if hi is not None:
            values.append((x[i] - hi)/max(1.0, abs(hi)))
    return max(values)


def _fraction(value):
    return Fraction.from_float(float(value))


def _origin(box, codes=None):
    """Shift ordinary variables by finite bounds, preserving integer lattices."""
    values, fixed = [], []
    for i, (lo, hi) in enumerate(box):
        code = 0 if codes is None else codes[i]
        if code in (2, 3):  # zero is a separate semi-continuous/integer branch
            value = 0.0
        elif lo is not None:
            value = float(np.ceil(lo)) if code == 1 else lo
        elif hi is not None:
            value = float(np.floor(hi)) if code == 1 else hi
        else:
            value = 0.0
        values.append(value)
        fixed.append(code not in (2, 3) and lo is not None and hi is not None and lo == hi)
    shifted = [(None if lo is None else float(_fraction(lo)-_fraction(o)),
                None if hi is None else float(_fraction(hi)-_fraction(o))) for (lo, hi), o in zip(box, values)]
    return np.array(values), np.array(fixed), shifted


def _center_rows(A, b, n, origin, fixed):
    """Retain original rational rows; subtract the bound origin exactly."""
    if A is None:
        if b is not None and len(b):
            raise ValueError('A constraint right-hand side requires its matrix')
        return None, None, [], [], []
    matrix = A.astype(float) if issparse(A) else np.asarray(A, float)
    rhs = np.asarray(b, float)
    if not matrix.size and rhs.shape == (0,):
        return None, None, [], [], []
    if matrix.ndim != 2 or matrix.shape[1] != n or rhs.shape != (matrix.shape[0],):
        raise ValueError('Constraint matrices and right-hand sides must match the objective dimensions')
    data = matrix.data if issparse(matrix) else matrix
    if not np.isfinite(data).all() or not np.isfinite(rhs).all():
        raise ValueError('Constraint coefficients and right-hand sides must be finite')
    if issparse(matrix):
        matrix = matrix.tocsr()
        rows = [[(int(j), _fraction(v)) for j, v in zip(matrix.indices[matrix.indptr[i]:matrix.indptr[i+1]],
                                                       matrix.data[matrix.indptr[i]:matrix.indptr[i+1]]) if v != 0]
                for i in range(matrix.shape[0])]
        working = matrix.copy()
        working.data[fixed[working.indices]] = 0
        working.eliminate_zeros()
    else:
        rows = [[(int(j), _fraction(matrix[i, j])) for j in np.flatnonzero(matrix[i])] for i in range(len(matrix))]
        working = matrix.copy()
        working[:, fixed] = 0
    original_rhs = [_fraction(value) for value in rhs]
    origins = [_fraction(value) for value in origin]
    centered_rhs = [value-sum((coefficient*origins[j] for j, coefficient in row), Fraction(0))
                    for value, row in zip(original_rhs, rows)]
    converted = np.array([float(value) for value in centered_rhs])
    if not np.isfinite(converted).all() or any(value != 0 and f == 0 for value, f in zip(centered_rhs, converted)):
        raise ValueError('Centered constraint RHS cannot be represented in finite numerical range')
    return working, converted, rows, original_rhs, centered_rhs


def _exact_primal(x, origin, box, rows, rhs, eq_rows, eq_rhs):
    """Avoid cancellation of the actual point with a large bound offset."""
    centered = [_fraction(v)-_fraction(o) for v, o in zip(x, origin)]
    worst = Fraction(0)
    for collection, targets, equality in [(rows, rhs, False), (eq_rows, eq_rhs, True)]:
        for row, target in zip(collection, targets):
            terms = [coefficient*centered[j] for j, coefficient in row]
            difference = sum(terms, Fraction(0))-target
            error = abs(difference) if equality else max(Fraction(0), difference)
            scale = max(abs(target), sum(map(abs, terms), Fraction(0)))
            if error:
                worst = max(worst, error/scale if scale else Fraction(1))
    for z, o, (lo, hi) in zip(centered, origin, box):
        for endpoint, lower in [(lo, True), (hi, False)]:
            if endpoint is None:
                continue
            boundary = _fraction(endpoint)-_fraction(o)
            error = boundary-z if lower else z-boundary
            if error > 0:
                scale = max(abs(boundary), abs(z))
                worst = max(worst, error/scale if scale else Fraction(1))
    return worst


def _exact_lp_account(c, sign, x, box, fixed, rows, rhs, eq_rows, eq_rhs, result, objective_scale, row_scale, eq_scale):
    """Original-unit objective and dual account from supplied binary numbers."""
    sign = int(sign)
    objective = [_fraction(value)*sign for value in c]
    factor = _fraction(objective_scale)
    prices = [] if row_scale is None else [_fraction(v)*factor/_fraction(s) for v, s in zip(result.ineqlin.marginals, row_scale)]
    eq_prices = [] if eq_scale is None else [_fraction(v)*factor/_fraction(s) for v, s in zip(result.eqlin.marginals, eq_scale)]
    lower = [_fraction(v)*factor for v in result.lower.marginals]
    upper = [_fraction(v)*factor for v in result.upper.marginals]
    residual, magnitude = objective.copy(), list(map(abs, objective))
    for collection, multipliers in [(rows, prices), (eq_rows, eq_prices)]:
        for row, multiplier in zip(collection, multipliers):
            for j, coefficient in row:
                residual[j] -= coefficient*multiplier
                magnitude[j] += abs(coefficient*multiplier)
    for j in range(len(c)):
        if fixed[j]:
            lower[j], upper[j] = (residual[j], Fraction(0)) if residual[j] >= 0 else (Fraction(0), residual[j])
        residual[j] -= lower[j]+upper[j]
        magnitude[j] += abs(lower[j])+abs(upper[j])
    relative = max([Fraction(0)]+[abs(value)/scale if scale else abs(value) for value, scale in zip(residual, magnitude)])
    primal = sum((a*_fraction(v) for a, v in zip(objective, x)), Fraction(0))
    dual = sum((a*b for a, b in zip(prices, rhs)), Fraction(0))+sum((a*b for a, b in zip(eq_prices, eq_rhs)), Fraction(0))
    for (lo, hi), lm, um in zip(box, lower, upper):
        if lo is not None:
            dual += _fraction(lo)*lm
        if hi is not None:
            dual += _fraction(hi)*um
    return primal, dual, abs(primal-dual), relative, prices


def solve_lp(c, *, A_ub=None, b_ub=None, A_ge=None, b_ge=None, A_eq=None, b_eq=None, bounds=None, maximize=False, tol=1e-7):
    """Solve an LP with HiGHS and compare the primal objective with the dual objective.

    Constraints: A_ub x <= b_ub, A_ge x >= b_ge, A_eq x = b_eq. Shadow prices are reported as the change in the optimal objective
    per unit increase of the right-hand side: `ineq_duals` for the <= rows, `ge_duals` for the >= rows (non-negative for a binding
    >= row of a minimisation, as in textbooks).

    Row/objective scaling, a small gap and checked primal/stationarity residuals
    support the solver's numerical optimum within the reported tolerance. This
    is not an exact-arithmetic proof or evidence that the LP represents reality."""
    c = np.asarray(c, float)
    if c.ndim != 1 or not len(c) or not np.isfinite(c).all() or not np.isfinite(tol) or tol < 0:
        raise ValueError('c must be a nonempty finite vector and tol finite and nonnegative')
    sign = -1 if maximize else 1
    box = _bounds(bounds, len(c))
    origin, fixed, shifted_box = _origin(box)
    A_ub, b_ub, n_ub = _with_ge(A_ub, b_ub, A_ge, b_ge)
    work_A, work_b, rows, rhs, centered_rhs = _center_rows(A_ub, b_ub, len(c), origin, fixed)
    work_E, work_e, eq_rows, eq_rhs, centered_eq_rhs = _center_rows(A_eq, b_eq, len(c), origin, fixed)
    A, b, row_scale = _scaled_rows(work_A, work_b, len(c))
    E, e, eq_scale = _scaled_rows(work_E, work_e, len(c))
    working_cost = c.copy()
    working_cost[fixed] = 0
    objective_scale = float(np.max(np.abs(working_cost))) or 1.0
    result = linprog(sign * working_cost/objective_scale, A_ub=A, b_ub=b, A_eq=E, b_eq=e, bounds=shifted_box, method='highs')
    out = dict(status=int(result.status), message=result.message, success=bool(result.success))
    if not result.success:
        return out
    point = result.x+origin
    if not np.isfinite(point).all():
        raise ValueError('Solver point exceeds finite numerical range')
    primal_residual = _exact_primal(point, origin, box, rows, centered_rhs, eq_rows, centered_eq_rhs)
    primal, dual, gap, dual_relative, prices = _exact_lp_account(c, sign, point, box, fixed, rows, rhs, eq_rows, eq_rhs,
                                                              result, objective_scale, row_scale, eq_scale)
    # Judge the gap in the variable objective rather than a large fixed offset.
    offset = sum((_fraction(a)*_fraction(o)*sign for a, o in zip(c, origin)), Fraction(0))
    gap_scale = max(_fraction(objective_scale), abs(primal-offset), abs(dual-offset))
    accepted = primal_residual <= _fraction(tol)
    dual_signs_valid = (np.all(result.ineqlin.marginals <= 0)
                        and np.all(result.lower.marginals >= 0)
                        and np.all(result.upper.marginals <= 0))
    certified = accepted and dual_signs_valid and dual_relative <= _fraction(tol) and gap <= _fraction(tol)*gap_scale
    dual_prices, dual_price_status = [], []
    for value in prices:
        try:
            price = float(value)
        except OverflowError:
            price = np.inf if value > 0 else -np.inf
        price, info = diagnostic(price, status=None if np.isfinite(price) else 'not_representable',
                                 reason='RHS shadow price exceeds finite numerical range in the original constraint units')
        dual_prices.append(price)
        dual_price_status.append(info)
    out.update(x=point.tolist(), objective=finite_real(float(primal*sign), 'objective'),
               dual_objective=finite_real(float(dual*sign), 'dual objective'),
               duality_gap=finite_real(float(gap), 'duality gap'), certified=bool(certified), incumbent_feasible=bool(accepted),
               certificate=dict(kind='numerical_primal_dual_check', tolerance=tol,
                                scaled_primal_violation=float(primal_residual), scaled_stationarity_residual=float(dual_relative),
                                relative_stationarity_residual=float(dual_relative),
                                dual_signs_valid=bool(dual_signs_valid),
                                arithmetic='exact_binary_rational_residuals_and_objective_account',
                                coordinate_shift='finite_bound_origin; fixed coordinates removed from solver rows; RHS subtraction exact before numeric conversion',
                                note='Supplied binary values are retained in residual/gap checks; nonzero tolerance and numerical solver bounds do not constitute an exact-optimality proof.'),
               ineq_duals=[None if value is None else value*sign for value in dual_prices[:n_ub]] if n_ub else None,
               ge_duals=[None if value is None else -value*sign for value in dual_prices[n_ub:]] if A_ge is not None else None)
    if any(info['status'] != 'computed' for info in dual_price_status):
        out['diagnostics'] = dict(rhs_shadow_prices=dual_price_status)
    if not accepted:
        out.update(success=False, solver_success=True,
                   verification_error='The solver candidate violates the original binary-number constraints relative to centered activity/RHS; it is not accepted as a feasible solution')
    return out



def solve_milp(c, *, A_ub=None, b_ub=None, A_ge=None, b_ge=None, A_eq=None, b_eq=None, bounds=None, integrality=None, maximize=False, time_limit=None):
    """Mixed-integer program via HiGHS, with its bound/gap and checked incumbent.

    A_ub x <= b_ub, A_ge x >= b_ge, A_eq x = b_eq. proved_optimal requires
    solver status zero, a closed finite solver bound and numerical feasibility
    and integrality checks; it is not an exact-arithmetic proof.
    """
    c = np.asarray(c, float)
    if c.ndim != 1 or not len(c) or not np.isfinite(c).all():
        raise ValueError('c must be a nonempty finite vector')
    n = len(c)
    codes = np.zeros(n, int) if integrality is None else np.asarray(integrality)
    if codes.shape != (n,) or codes.dtype.kind == 'b' or not np.isin(codes, [0, 1, 2, 3]).all():
        raise ValueError('integrality must have one code 0, 1, 2 or 3 per variable')
    box = _bounds(bounds, n)
    origin, fixed, shifted_box = _origin(box, codes)
    A_ub, b_ub, _ = _with_ge(A_ub, b_ub, A_ge, b_ge)
    work_A, work_b, rows, rhs, centered_rhs = _center_rows(A_ub, b_ub, n, origin, fixed)
    work_E, work_e, eq_rows, eq_rhs, centered_eq_rhs = _center_rows(A_eq, b_eq, n, origin, fixed)
    A, b, _ = _scaled_rows(work_A, work_b, n)
    E, e, _ = _scaled_rows(work_E, work_e, n)
    working_cost = c.copy()
    working_cost[fixed] = 0
    objective_scale = float(np.max(np.abs(working_cost))) or 1.0
    sign = -1 if maximize else 1
    constraints = []
    if A is not None:
        constraints.append(LinearConstraint(A, -np.inf, b))
    if E is not None:
        constraints.append(LinearConstraint(E, e, e))
    lo = [-np.inf if pair[0] is None else pair[0] for pair in shifted_box]
    hi = [np.inf if pair[1] is None else pair[1] for pair in shifted_box]
    options = {} if time_limit is None else {'time_limit': float(time_limit)}
    result = milp(sign * working_cost/objective_scale, constraints=constraints, bounds=Bounds(lo, hi),
                  integrality=codes, options=options)
    out = dict(status=int(result.status), message=result.message, success=bool(result.success))
    if result.x is None:
        return out
    point = result.x+origin
    if not np.isfinite(point).all():
        raise ValueError('Solver point exceeds finite numerical range')
    active_box = [(None, None) if codes[i] in (2, 3) and point[i] == 0 else pair for i, pair in enumerate(box)]
    primal = _exact_primal(point, origin, active_box, rows, centered_rhs, eq_rows, centered_eq_rhs)
    integer_residual = max([Fraction(0)]+[abs(_fraction(point[i])-round(point[i])) for i in range(n) if codes[i] in (1, 3)])
    checked = primal <= _fraction(1e-7) and integer_residual <= _fraction(1e-7)
    objective = sum((_fraction(a)*_fraction(v) for a, v in zip(c, point)), Fraction(0))
    offset = sum((_fraction(a)*_fraction(v) for a, v in zip(c, origin)), Fraction(0))
    bound = getattr(result, 'mip_dual_bound', None)
    if bound is None or not np.isfinite(bound):
        exact_bound = None
        bound_value, bound_status = diagnostic(0, status='not_reported' if bound is None else 'undefined', reason='The solver did not report a finite bound')
    else:
        exact_bound = _fraction(bound)*_fraction(objective_scale)*sign+offset
        bound_value = finite_real(float(exact_bound), 'best bound')
        bound_status = dict(status='computed')
    raw_gap = getattr(result, 'mip_gap', None)
    gap_value, gap_status = diagnostic(0, status='not_reported', reason='The solver did not report a MIP gap') if raw_gap is None else diagnostic(raw_gap, reason='The reported MIP gap is not finite')
    gap_scale = max(_fraction(objective_scale), abs(objective-offset))
    bound_closed = exact_bound is not None and abs(objective-exact_bound) <= _fraction(1e-7)*gap_scale
    out.update(x=point.tolist(), objective=finite_real(float(objective), 'objective'), best_bound=bound_value, mip_gap=gap_value,
               proved_optimal=bool(result.status == 0 and checked and bound_closed), incumbent_feasible=bool(checked),
               diagnostics=dict(best_bound=bound_status, mip_gap=gap_status),
               certificate=dict(kind='numerical_solver_bound_and_incumbent_check', scaled_primal_violation=float(primal),
                                integrality_residual=float(integer_residual), tolerance=1e-7,
                                arithmetic='exact_binary_rational_residuals_and_objective_account',
                                coordinate_shift='finite_bound_origin; integer lattices preserved; semi-variable zero branches kept',
                                note='Original binary-number incumbent checks and a numerical solver bound; not an exact-optimality proof.'))
    if not checked:
        out.update(success=False, solver_success=bool(result.success),
                   verification_error='The solver incumbent failed original binary-number centered primal feasibility or integrality checks')
    return out



def assignment(cost, *, maximize=False):
    """Optimal one-to-one assignment (Hungarian algorithm) for a rectangular cost matrix."""
    c = np.asarray(cost, float)
    if c.ndim != 2 or not np.isfinite(c).all():
        raise ValueError('cost must be a finite 2-D matrix')
    rows, cols = linear_sum_assignment(c, maximize=maximize)
    return dict(pairs=[[int(r), int(k)] for r, k in zip(rows, cols)], total=float(c[rows, cols].sum()))


def _tour_length(d, tour):
    return float(sum(d[tour[i], tour[(i + 1) % len(tour)]] for i in range(len(tour))))


def _two_opt(d, tour):
    improved = True
    while improved:
        improved = False
        for i in range(1, len(tour) - 1):
            for j in range(i + 1, len(tour)):
                a, b, c, e = tour[i - 1], tour[i], tour[j], tour[(j + 1) % len(tour)]
                if d[a, c] + d[b, e] < d[a, b] + d[c, e] - 1e-12:
                    tour[i:j + 1] = tour[i:j + 1][::-1]
                    improved = True
    return tour


def _one_tree_bound(d):
    """Held-Karp style lower bound without multipliers: MST of the other nodes plus the two cheapest edges at the removed node."""
    import networkx as nx
    n = len(d)
    best = 0.
    for v in range(n):
        g = nx.Graph()
        rest = [u for u in range(n) if u != v]
        g.add_weighted_edges_from((a, b, d[a, b]) for i, a in enumerate(rest) for b in rest[i + 1:])
        mst = nx.minimum_spanning_tree(g).size(weight='weight') if len(rest) > 1 else 0.
        best = max(best, mst + float(np.sort(d[v, rest])[:2].sum()))
    return best


def tsp(distance, *, starts=None):
    """Round-trip tour by nearest neighbour from several starts plus 2-opt, with a 1-tree lower bound.

    This is a heuristic: the tour is feasible, the bound proves how far from optimal it can be."""
    d = np.asarray(distance, float)
    if d.ndim != 2 or d.shape[0] != d.shape[1] or len(d) < 3 or not np.isfinite(d).all() or (d < 0).any() or not np.array_equal(d, d.T):
        raise ValueError('Need a finite nonnegative exactly symmetric square distance matrix with at least 3 nodes')
    n = len(d)
    origins = list(range(n)) if starts is None else list(starts)
    if not origins or any(isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or not 0 <= value < n for value in origins):
        raise ValueError('starts must contain valid integer node indices')
    best = None
    for s0 in origins:
        tour, left = [s0], set(range(n)) - {s0}
        while left:
            nxt = min(left, key=lambda u: d[tour[-1], u]); tour.append(nxt); left.remove(nxt)
        tour = _two_opt(d, tour)
        length = _tour_length(d, tour)
        if best is None or length < best[1] - 1e-12:
            best = (tour[:], length)
    bound = _one_tree_bound(d)
    if not np.isfinite(best[1]) or not np.isfinite(bound):
        raise ValueError('Tour length or lower bound exceeds finite numerical range')
    return dict(tour=[int(x) for x in best[0]], length=best[1], lower_bound=float(bound),
                gap=float((best[1] - bound) / bound) if bound > 0 else None, heuristic=True)
