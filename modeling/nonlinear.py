"""Optimisation beyond linear programs: nonlinear programs, knapsack, min-cost flow, budget-robust LP, finite-state decision processes.

Each function returns what it can certify and says what it cannot: a multi-start nonlinear solver reports candidates and how
often the best one was found, never "global"."""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
from scipy.optimize import linprog, minimize
from modeling.contracts import finite_real, stochastic_matrix


def minimize_nlp(objective: Callable, bounds: Sequence[Sequence[float]], constraints: Sequence[dict] = (), *, starts: int = 20, seed: int = 2027,
                 maximize: bool = False, tol: float = 1e-8) -> dict:
    """Multi-start SLSQP. constraints: [{'fun': callable, 'type': 'ineq'|'eq'}] with ineq meaning fun(x) >= 0.

    Returns converged feasible candidates separately from failed feasible incumbents, with solver statuses, the constraint
    violation and which constraints are active. Agreement of many starts is evidence of a global optimum, not a proof."""
    box = np.asarray(bounds, float)
    if box.ndim != 2 or box.shape[1] != 2 or not len(box) or not np.isfinite(box).all() or (box[:, 0] > box[:, 1]).any():
        raise ValueError('bounds must be a nonempty finite ordered box')
    if isinstance(starts, bool) or not isinstance(starts, (int, np.integer)) or starts < 1 or not np.isfinite(tol) or tol < 0:
        raise ValueError('positive integer starts and finite nonnegative tol required')
    if any(c['type'] not in ('eq', 'ineq') for c in constraints):
        raise ValueError('constraint type must be eq or ineq')
    lo, hi = box.T
    rng = np.random.default_rng(seed)
    sign = -1.0 if maximize else 1.0
    cons = [dict(type=c['type'], fun=c['fun']) for c in constraints]
    found, incumbents, attempts = [], [], []
    for start in range(starts):
        record = dict(start=start, success=False, feasible=False)
        attempts.append(record)
        x0 = lo + rng.random(len(lo)) * (hi - lo)
        try:
            res = minimize(lambda x: sign * finite_real(objective(x), 'objective'), x0, method='SLSQP', bounds=list(zip(lo, hi)), constraints=cons, options=dict(ftol=1e-12, maxiter=500))
            record.update(success=bool(res.success), status=int(res.status), message=str(res.message))
            x = np.asarray(res.x, float)
            if x.shape != lo.shape or not np.isfinite(x).all():
                raise ValueError('solver point must be a finite vector matching bounds')
            finite_real(res.fun, 'solver objective')
            val = finite_real(objective(x), 'recomputed objective')
            values = [finite_real(c['fun'](x), 'constraint') for c in constraints]
            viol = max([0.0, float(np.max(lo - x)), float(np.max(x - hi))] + [max(0.0, -v) if c['type'] == 'ineq' else abs(v) for c, v in zip(constraints, values)])
            record.update(x=x.tolist(), value=val, max_violation=viol, feasible=viol <= max(tol, 1e-7))
            if record['feasible']:
                incumbents.append((val, x, viol))
                if res.success:
                    found.append((val, x, viol))
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}: {exc}'
    if not incumbents:
        return dict(feasible=False, converged=False, starts=starts, attempts=attempts, distinct_optima=[], note='No finite feasible point found; this does not prove infeasibility.')
    found.sort(key=lambda t: sign * t[0])
    incumbents.sort(key=lambda t: sign * t[0])
    best = found[0] if found else incumbents[0]
    groups: list[dict] = []
    for val, x, _ in found:
        for g in groups:
            if abs(g['value'] - val) <= 1e-6 * (1 + abs(val)) and np.linalg.norm(g['x'] - x) <= 1e-4 * (1 + np.linalg.norm(x)):
                g['count'] += 1
                break
        else:
            groups.append(dict(value=float(val), x=x, count=1))
    active = [i for i, c in enumerate(constraints) if abs(finite_real(c['fun'](best[1]))) <= 1e-6]
    at_bounds = [i for i in range(len(lo)) if min(abs(best[1][i] - lo[i]), abs(hi[i] - best[1][i])) <= 1e-7]
    return dict(feasible=True, converged=bool(found), status='converged_candidate' if found else 'feasible_incumbent',
                x=best[1].tolist(), value=float(best[0]), max_violation=float(best[2]), active_constraints=active, variables_at_bounds=at_bounds,
                feasible_starts=len(incumbents), converged_starts=len(found), starts=starts, attempts=attempts,
                feasible_incumbent=dict(value=float(incumbents[0][0]), x=incumbents[0][1].tolist()),
                distinct_optima=[dict(value=g['value'], x=g['x'].tolist(), starts=g['count']) for g in groups],
                best_found_by=groups[0]['count'] if groups else 0,
                note='Converged SLSQP candidates are not certified optima. Failed feasible attempts are retained as incumbents only; a sampled convexity probe cannot certify global optimality.')


def knapsack(values: Sequence[float], weights: Sequence[int], capacity: int, *, copies: Sequence[int] | None = None) -> dict:
    """Exact 0/1 (or bounded) knapsack by dynamic programming over integer weights."""
    w = [int(x) for x in weights]
    if any(x != y for x, y in zip(w, weights)) or int(capacity) != capacity or min(w) < 0:
        raise ValueError('Weights and capacity must be non-negative integers (scale decimals first)')
    n, cap = len(values), int(capacity)
    items = []
    for i in range(n):
        for _ in range(1 if copies is None else int(copies[i])):
            items.append(i)
    best = np.zeros(cap + 1)
    take = np.zeros((len(items), cap + 1), bool)
    for j, i in enumerate(items):
        wi, vi = w[i], float(values[i])
        for c in range(cap, wi - 1, -1):
            if best[c - wi] + vi > best[c] + 1e-12:
                best[c] = best[c - wi] + vi
                take[j, c] = True
    c, chosen = cap, [0] * n
    for j in range(len(items) - 1, -1, -1):
        if take[j, c]:
            chosen[items[j]] += 1
            c -= w[items[j]]
    return dict(value=float(best[cap]), chosen=chosen, weight=int(sum(w[i] * k for i, k in enumerate(chosen))), proved=True)


def min_cost_flow(edges: Sequence[Sequence[float]], demand: dict) -> dict:
    """Minimum-cost flow on a simple directed graph; duplicate endpoints are rejected.

    edges: [u, v, capacity, cost]; demand: {node: net demand} (negative for supply), summing to zero. Integer data give an integer flow."""
    import networkx as nx
    g = nx.DiGraph()
    for node, d in demand.items():
        g.add_node(node, demand=d)
    for u, v, cap, cost in edges:
        if g.has_edge(u, v):
            raise ValueError('Parallel or duplicate edges are not supported; supply a simple graph')
        if not np.isfinite([cap, cost]).all() or cap < 0:
            raise ValueError('Finite edge costs and finite nonnegative capacities required')
        g.add_edge(u, v, capacity=cap, weight=cost)
    try:
        cost, flow = nx.network_simplex(g)
    except nx.NetworkXUnfeasible:
        return dict(feasible=False, note='Demands cannot be met within the capacities.')
    return dict(feasible=True, cost=float(cost), flow=[[u, v, flow[u][v]] for u, v in g.edges if flow[u][v]], proved=True)


def robust_lp(c, A_ub, b_ub, delta, gamma, *, maximize: bool = False) -> dict:
    """LP with x >= 0 whose constraint coefficients are uncertain within A +/- delta, at most `gamma` of them per row at their worst (Bertsimas-Sim).

    gamma = 0 is the nominal problem; gamma = number of columns is the full box. The price of robustness is the objective difference."""
    c, A, b, D = (np.asarray(v, float) for v in (c, A_ub, b_ub, delta))
    m, n = A.shape
    g = float(gamma)
    # variables: x (n), z (m), p (m*n); row i: A_i x + g z_i + sum_j p_ij <= b_i ; z_i + p_ij - D_ij x_j >= 0
    nv = n + m + m * n
    rows, rhs = [], []
    for i in range(m):
        r = np.zeros(nv)
        r[:n] = A[i]
        r[n + i] = g
        r[n + m + i * n: n + m + (i + 1) * n] = 1
        rows.append(r); rhs.append(b[i])
        for j in range(n):
            r = np.zeros(nv)
            r[j] = D[i, j]
            r[n + i] = -1
            r[n + m + i * n + j] = -1
            rows.append(r); rhs.append(0.0)
    cost = np.r_[-c if maximize else c, np.zeros(m + m * n)]
    res = linprog(cost, A_ub=np.array(rows), b_ub=np.array(rhs), bounds=[(0, None)] * nv, method='highs')
    if res.status != 0:
        return dict(feasible=False, status=res.message)
    x = res.x[:n]

    def worst(i):
        d = np.sort(D[i] * x)[::-1]
        k = int(np.floor(g))
        return float(A[i] @ x + d[:k].sum() + ((g - k) * d[k] if k < n else 0.0))
    return dict(feasible=True, x=x.tolist(), value=float(c @ x), gamma=g, worst_case_row_use=[worst(i) for i in range(m)])


def solve_mdp(P, R, *, horizon: int | None = None, discount: float = 1.0, terminal=None, maximize: bool = True, tol: float = 1e-10) -> dict:
    """Finite-state decision process. P[a][s][s'] transition probabilities, R[s][a] rewards.

    With `horizon` it does exact backward induction (policy per stage); without, value iteration for discount < 1 (error bound reported)."""
    P, R = np.asarray(P, float), np.asarray(R, float)
    if P.ndim != 3 or not P.shape[0]:
        raise ValueError('P must have shape (actions, states, states)')
    for matrix in P:
        stochastic_matrix(matrix)
    na, ns, _ = P.shape
    if R.shape != (ns, na) or not np.isfinite(R).all():
        raise ValueError('R must be a finite (states, actions) reward matrix')
    if not np.isfinite(discount) or not 0 <= discount <= 1 or not np.isfinite(tol) or tol <= 0:
        raise ValueError('discount must lie in [0,1] and tol must be finite and positive')
    if horizon is not None and (isinstance(horizon, bool) or not isinstance(horizon, (int, np.integer)) or horizon < 0):
        raise ValueError('horizon must be a nonnegative integer')
    if terminal is not None and (np.asarray(terminal).shape != (ns,) or not np.isfinite(terminal).all()):
        raise ValueError('terminal must be a finite vector with one value per state')
    pick = np.argmax if maximize else np.argmin
    if horizon is not None:
        V = np.zeros(ns) if terminal is None else np.asarray(terminal, float)
        policy, values = [], [V.copy()]
        for _ in range(int(horizon)):
            Q = np.array([[R[s, a] + discount * P[a, s] @ V for a in range(na)] for s in range(ns)])
            policy.append(pick(Q, axis=1).tolist())
            V = Q.max(axis=1) if maximize else Q.min(axis=1)
            values.append(V.copy())
        return dict(value=V.tolist(), policy_by_stages_remaining=policy, method='backward induction', exact=True)
    if not 0 <= discount < 1:
        raise ValueError('Infinite horizon needs discount in [0, 1)')
    V = np.zeros(ns)
    for it in range(1, 100001):
        Q = np.array([[R[s, a] + discount * P[a, s] @ V for a in range(na)] for s in range(ns)])
        Vn = Q.max(axis=1) if maximize else Q.min(axis=1)
        delta = np.max(np.abs(Vn - V))
        V = Vn
        if delta < tol:
            break
    return dict(value=V.tolist(), policy=pick(Q, axis=1).tolist(), iterations=it, error_bound=float(discount * delta / (1 - discount)), method='value iteration')
