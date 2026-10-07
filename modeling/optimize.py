"""Linear and mixed-integer programs with solver status and a checkable certificate."""
import numpy as np
from scipy.optimize import linprog, milp, linear_sum_assignment, LinearConstraint, Bounds


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
    n = len(d)
    if d.ndim != 2 or d.shape[0] != d.shape[1] or n < 3 or not np.allclose(d, d.T):
        raise ValueError('Need a symmetric square distance matrix with at least 3 nodes')
    best = None
    for s0 in (range(n) if starts is None else starts):
        tour, left = [s0], set(range(n)) - {s0}
        while left:
            nxt = min(left, key=lambda u: d[tour[-1], u]); tour.append(nxt); left.remove(nxt)
        tour = _two_opt(d, tour)
        length = _tour_length(d, tour)
        if best is None or length < best[1] - 1e-12:
            best = (tour[:], length)
    bound = _one_tree_bound(d)
    return dict(tour=[int(x) for x in best[0]], length=best[1], lower_bound=float(bound),
                gap=float((best[1] - bound) / bound) if bound > 0 else None, heuristic=True)
