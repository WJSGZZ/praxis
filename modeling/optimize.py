"""Linear and mixed-integer programs with solver status and a checkable certificate."""
import numpy as np
from scipy.optimize import linprog, milp, LinearConstraint, Bounds


def _bounds(bounds, n):
    if bounds is None:
        return [(0, None)] * n
    return [tuple(b) for b in bounds]


def solve_lp(c, *, A_ub=None, b_ub=None, A_eq=None, b_eq=None, bounds=None, maximize=False, tol=1e-7):
    """Solve an LP with HiGHS and compare the primal objective with the dual objective.

    A zero gap with finite bounds certifies optimality of this LP; it says nothing about whether
    the LP represents the real problem."""
    c = np.asarray(c, float)
    sign = -1. if maximize else 1.
    result = linprog(sign * c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=_bounds(bounds, len(c)), method='highs')
    out = dict(status=int(result.status), message=result.message, success=bool(result.success))
    if not result.success:
        return out
    dual = 0.
    if A_ub is not None:
        dual += float(np.dot(result.ineqlin.marginals, b_ub))
    if A_eq is not None:
        dual += float(np.dot(result.eqlin.marginals, b_eq))
    for (lo, hi), lm, um in zip(_bounds(bounds, len(c)), result.lower.marginals, result.upper.marginals):
        if lo is not None:
            dual += float(lm) * lo
        if hi is not None:
            dual += float(um) * hi
    gap = abs(result.fun - dual)
    out.update(x=result.x.tolist(), objective=float(sign * result.fun), dual_objective=float(sign * dual),
               duality_gap=float(gap), certified=bool(gap <= tol * max(1., abs(result.fun))),
               ineq_duals=(result.ineqlin.marginals * sign).tolist() if A_ub is not None else None)
    return out


def solve_milp(c, *, A_ub=None, b_ub=None, A_eq=None, b_eq=None, bounds=None, integrality=None, maximize=False, time_limit=None):
    """Mixed-integer program via HiGHS. Reports the proved bound and the remaining gap, not just the incumbent."""
    c = np.asarray(c, float)
    n = len(c)
    sign = -1. if maximize else 1.
    constraints = []
    if A_ub is not None:
        constraints.append(LinearConstraint(np.asarray(A_ub, float), -np.inf, np.asarray(b_ub, float)))
    if A_eq is not None:
        constraints.append(LinearConstraint(np.asarray(A_eq, float), np.asarray(b_eq, float), np.asarray(b_eq, float)))
    b = _bounds(bounds, n)
    lo = [-np.inf if x[0] is None else x[0] for x in b]
    hi = [np.inf if x[1] is None else x[1] for x in b]
    options = {} if time_limit is None else {'time_limit': float(time_limit)}
    result = milp(sign * c, constraints=constraints, bounds=Bounds(lo, hi),
                  integrality=np.zeros(n) if integrality is None else np.asarray(integrality), options=options)
    out = dict(status=int(result.status), message=result.message, success=bool(result.success))
    if result.x is None:
        return out
    bound = getattr(result, 'mip_dual_bound', None)
    out.update(x=result.x.tolist(), objective=float(sign * result.fun),
               best_bound=None if bound is None else float(sign * bound),
               mip_gap=None if getattr(result, 'mip_gap', None) is None else float(result.mip_gap),
               proved_optimal=bool(result.status == 0))
    return out
