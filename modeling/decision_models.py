"""Small decision models with closed forms or linear programs: Markov chains, matrix games, EOQ, newsvendor, CVaR portfolios, Pareto fronts."""
from __future__ import annotations

import itertools
import math
from fractions import Fraction

import numpy as np
from scipy.stats import norm

from modeling import optimize
from modeling.contracts import stochastic_matrix


def _finite_economic_result(result):
    if not all(np.isfinite(value) for value in result.values()):
        raise ValueError('Economic model outputs exceed finite numerical range')
    return result


def markov_stationary(P) -> dict:
    """Stationary distribution of an irreducible finite chain: solve pi P = pi, sum pi = 1. Reports irreducibility and the residual."""
    P = stochastic_matrix(P)
    n = P.shape[0]
    reach = np.linalg.matrix_power((P > 0).astype(float) + np.eye(n), n) > 0
    irreducible = bool(reach.all())
    A = np.vstack([P.T - np.eye(n), np.ones(n)])
    b = np.r_[np.zeros(n), 1.0]
    pi = np.linalg.lstsq(A, b, rcond=None)[0]
    return dict(stationary=pi.tolist(), irreducible=irreducible, residual=float(np.abs(pi @ P - pi).max()),
                note=None if irreducible else 'Chain is reducible: the stationary distribution may not be unique.')


def markov_absorption(P, absorbing) -> dict:
    """Absorption probabilities and expected steps to absorption from each transient state (fundamental matrix N = (I - Q)^-1)."""
    P = stochastic_matrix(P)
    n = P.shape[0]
    if not absorbing or any(isinstance(i, bool) or not isinstance(i, (int, np.integer)) or not 0 <= i < n for i in absorbing):
        raise ValueError('absorbing must contain valid integer state indices')
    absorbing = sorted(set(absorbing))
    for i in absorbing:
        if P[i, i] != 1.0 or np.any(np.delete(P[i], i) != 0.0):
            raise ValueError(f'State {i} is not absorbing (its row must be a point mass at itself)')
    transient = [i for i in range(n) if i not in absorbing]
    Q, R = P[np.ix_(transient, transient)], P[np.ix_(transient, absorbing)]
    # Every state must have a positive-probability path to the declared absorbing set.
    reachable = set(absorbing)
    for _ in range(n):
        reachable.update(i for i in range(n) if any(P[i, j] > 0 for j in reachable))
    if len(reachable) != n:
        return dict(transient=transient, absorbing=absorbing, fully_absorbing=False, expected_steps=None, absorption_probabilities=None, note='A closed class cannot reach the declared absorbing states')
    N = np.linalg.solve(np.eye(len(transient)) - Q, np.eye(len(transient)))
    return dict(transient=transient, absorbing=absorbing, fully_absorbing=True, expected_steps=(N @ np.ones(len(transient))).tolist(), absorption_probabilities=(N @ R).tolist())


def matrix_game(payoff) -> dict:
    """Zero-sum minimax game with centered/scaled payoffs and checked strategies.

    Affine transformation is formed with exact binary-input differences before
    numerical solution, so a unit shift cannot swallow small payoff differences.
    Original-unit exploitability is recomputed from the actual returned strategies.
    """
    A = np.asarray(payoff, float)
    if A.ndim != 2 or not all(A.shape) or not np.isfinite(A).all():
        raise ValueError('payoff must be a nonempty finite matrix')
    m, n = A.shape
    raw = np.asarray(payoff, object)
    original = [[Fraction(int(v)) if isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_)) else Fraction.from_float(float(v)) for v in row] for row in raw]
    origin = original[0][0]
    span = max(abs(v-origin) for row in original for v in row)
    saddle = max(min(row) for row in original) == min(max(original[i][j] for i in range(m)) for j in range(n))
    if span == 0:
        return dict(value=float(origin), value_exact=str(origin), row_strategy=[1/m]*m, column_strategy=[1/n]*n,
                    has_saddle=True, exploitability=0.0, exploitability_exact='0', certified=True,
                    certificate_scope='Constant supplied payoff matrix has this exact game value.')
    B = np.array([[float((v-origin)/span) for v in row] for row in original])
    # p and unrestricted guaranteed value t; q and unrestricted upper value u.
    row = optimize.solve_lp([0]*m+[1], A_ub=np.c_[-B.T, np.ones(n)], b_ub=np.zeros(n),
                            A_eq=[([1]*m+[0])], b_eq=[1], bounds=[(0, None)]*m+[(None, None)], maximize=True)
    col = optimize.solve_lp([0]*n+[1], A_ub=np.c_[B, -np.ones(m)], b_ub=np.zeros(m),
                            A_eq=[([1]*n+[0])], b_eq=[1], bounds=[(0, None)]*n+[(None, None)])
    if not all(r.get('success') and r.get('certified') for r in [row, col]):
        raise ValueError('No numerically verified minimax strategies accepted for the supplied payoff matrix')
    p, q = np.array(row['x'][:m]), np.array(col['x'][:n])
    if (p < 0).any() or (q < 0).any() or p.sum() <= 0 or q.sum() <= 0:
        raise ValueError('Minimax solver returned invalid probabilities')
    p, q = p/p.sum(), q/q.sum()
    fp, fq = [Fraction.from_float(float(v)) for v in p], [Fraction.from_float(float(v)) for v in q]
    ps, qs = sum(fp), sum(fq)
    fp, fq = [v/ps for v in fp], [v/qs for v in fq]
    low = min(sum((fp[i]*original[i][j] for i in range(m)), Fraction(0)) for j in range(n))
    high = max(sum((fq[j]*original[i][j] for j in range(n)), Fraction(0)) for i in range(m))
    gap = max(Fraction(0), high-low)
    if gap/span > Fraction.from_float(1e-7):
        raise ValueError('Returned minimax strategies fail the original-payoff exploitability check')
    return dict(value=float((low+high)/2), value_exact=str((low+high)/2), row_strategy=p.tolist(), column_strategy=q.tolist(),
                has_saddle=bool(saddle), row_guaranteed_value=float(low), column_upper_value=float(high),
                exploitability=float(gap), exploitability_exact=str(gap), normalized_exploitability=float(gap/span), certified=True,
                certificate_scope='Numerical minimax strategies within 1e-7 of the exact supplied payoff range; exploitability recomputed in original units.')


def eoq(demand: float, order_cost: float, holding_cost: float, *, stockout_cost: float | None = None) -> dict:
    """Economic order quantity Q* = sqrt(2 D S / H); with planned shortages (backorder cost b per unit-year) Q* = sqrt(2DS/H) sqrt((H+b)/b)."""
    if not np.isfinite([demand, order_cost, holding_cost]).all() or min(demand, order_cost, holding_cost) <= 0:
        raise ValueError('demand, order_cost and holding_cost must be positive')
    q = math.sqrt(2 * demand * order_cost / holding_cost)
    if stockout_cost is None:
        return _finite_economic_result(dict(order_quantity=q, cycle_time=q / demand, annual_cost=math.sqrt(2 * demand * order_cost * holding_cost)))
    b = float(stockout_cost)
    if not np.isfinite(b) or b <= 0:
        raise ValueError('stockout_cost must be positive')
    q = q * math.sqrt((holding_cost + b) / b)
    s = q * b / (holding_cost + b)                  # maximum on-hand inventory; the rest of the cycle is backordered
    cost = order_cost * demand / q + holding_cost * s ** 2 / (2 * q) + b * (q - s) ** 2 / (2 * q)
    return _finite_economic_result(dict(order_quantity=q, max_inventory=s, max_backorder=q - s, annual_cost=cost))


def newsvendor(price: float, cost: float, salvage: float, mean: float, sd: float) -> dict:
    """Optimal order for normal demand: critical fractile F(Q*) = (p - c) / (p - s); expected profit by the standard loss function."""
    if not np.isfinite([price, cost, salvage, mean, sd]).all() or not price > cost > salvage or sd <= 0:
        raise ValueError('Need price > cost > salvage and sd > 0')
    ratio = (price - cost) / (price - salvage)
    z = float(norm.ppf(ratio))
    unconstrained_q = mean + sd * z
    q = max(0.0, unconstrained_q)
    z = (q - mean) / sd
    loss = sd * (norm.pdf(z) - z * (1 - norm.cdf(z)))      # expected lost sales E[(D - Q)+]
    sales = mean - loss
    profit = price * sales + salvage * (q - sales) - cost * q
    result = _finite_economic_result(dict(critical_fractile=float(ratio), order_quantity=float(q), unconstrained_order_quantity=float(unconstrained_q),
                                          expected_lost_sales=float(loss), expected_profit=float(profit), service_level=float(norm.cdf(z))))
    result['note'] = 'Nonnegative order quantity under an untruncated normal demand approximation; negative demand mass is a modeling limitation.'
    return result


def cvar_portfolio(returns, target: float, *, alpha: float = 0.95, long_only: bool = True) -> dict:
    """Minimum-CVaR portfolio for scenario returns (rows = scenarios) with expected return >= target (Rockafellar-Uryasev LP).

    Loss is the negative portfolio return; CVaR_alpha is the mean of the worst (1 - alpha) share of scenarios. The answer is
    conditional on the scenarios supplied; it is not a forecast."""
    R = np.asarray(returns, float)
    if R.ndim != 2 or not all(R.shape) or not np.isfinite(R).all() or not np.isfinite(target):
        raise ValueError('returns must be a nonempty finite scenario matrix and target finite')
    S, n = R.shape
    if not 0 < alpha < 1:
        raise ValueError('alpha must lie in (0, 1)')
    # variables: w (n), zeta (1), u (S); minimise zeta + 1/((1-alpha)S) sum u
    c = np.r_[np.zeros(n), 1.0, np.full(S, 1 / ((1 - alpha) * S))]
    A_ub = np.vstack([np.hstack([-R, -np.ones((S, 1)), -np.eye(S)]), np.r_[-R.mean(axis=0), 0, np.zeros(S)][None, :]])
    b_ub = np.r_[np.zeros(S), -target]
    A_eq = [np.r_[np.ones(n), 0, np.zeros(S)].tolist()]
    bounds = [(0, None) if long_only else (None, None)] * n + [(None, None)] + [(0, None)] * S
    r = optimize.solve_lp(c.tolist(), A_ub=A_ub.tolist(), b_ub=b_ub.tolist(), A_eq=A_eq, b_eq=[1.0], bounds=bounds)
    if not r['success']:
        return r
    w = np.array(r['x'][:n])
    losses = -(R @ w)
    # A fractional tail includes only the necessary fraction of the next
    # ordered scenario, exactly as the empirical Rockafellar-Uryasev LP does.
    mass = (1 - alpha) * S
    k = int(math.floor(mass))
    ordered = np.sort(losses)[::-1]
    tail_sum = ordered[:k].sum()
    if k < S:
        tail_sum += (mass - k) * ordered[k]
    tail_mean = tail_sum / mass
    return dict(success=True, status=r['status'], message=r['message'], certified=r['certified'], weights=w.tolist(), cvar=float(r['objective']), var=float(r['x'][n]), expected_return=float(R.mean(axis=0) @ w),
                empirical_tail_mean=float(tail_mean), empirical_tail_mass=float(mass))


def pareto_front(points, senses) -> dict:
    """Non-dominated rows of a table of objective values. senses: +1 to maximise a column, -1 to minimise."""
    raw = np.asarray(points, float)
    directions = np.asarray(senses, float)
    if raw.ndim != 2 or not all(raw.shape) or not np.isfinite(raw).all() or directions.shape != (raw.shape[1],) or not np.isin(directions, [-1, 1]).all():
        raise ValueError('points must be a nonempty finite objective matrix with one sense +1 or -1 per column')
    X = raw * directions
    n = len(X)
    keep = []
    for i in range(n):
        dominated = any(np.all(X[j] >= X[i]) and np.any(X[j] > X[i]) for j in range(n) if j != i)
        if not dominated:
            keep.append(i)
    return dict(indices=keep, points=np.asarray(points, float)[keep].tolist(), dominated=[i for i in range(n) if i not in keep])


def bimatrix_nash(A, B, *, max_support: int = 6, tol: float = 1e-9) -> dict:
    """Numerically enumerate equal-support Nash candidates of a two-player game.

    Nondegenerate games have equal-support equilibria; degeneracy is not certified
    here, singular systems are skipped, and continuous families are not represented.
    Neither complete enumeration nor exact arithmetic is claimed. Say which one
    the players are expected to play and why, or give a guarantee that holds in all of them."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    if A.ndim != 2 or A.shape != B.shape or not all(A.shape) or not np.isfinite(A).all() or not np.isfinite(B).all():
        raise ValueError('A and B must have the same nonempty finite matrix shape')
    if not np.isfinite(tol) or tol < 0:
        raise ValueError('tol must be finite and nonnegative')
    m, n = A.shape
    if max(m, n) > max_support:
        raise ValueError(f'Game too large for support enumeration (limit {max_support} actions per player)')
    found = []
    for k in range(1, min(m, n) + 1):
        for rows in itertools.combinations(range(m), k):
            for cols in itertools.combinations(range(n), k):
                x = _indifference(B[np.ix_(rows, cols)].T, k)           # row mix making the column player indifferent on cols
                y = _indifference(A[np.ix_(rows, cols)], k)             # column mix making the row player indifferent on rows
                if x is None or y is None:
                    continue
                xf, yf = np.zeros(m), np.zeros(n)
                xf[list(rows)], yf[list(cols)] = x, y
                row_payoffs, col_payoffs = A @ yf, xf @ B
                if row_payoffs.max() - row_payoffs[list(rows)].min() > tol or col_payoffs.max() - col_payoffs[list(cols)].min() > tol:
                    continue
                if not any(np.allclose(xf, e['row']) and np.allclose(yf, e['column']) for e in found):
                    found.append(dict(row=xf, column=yf, row_payoff=float(xf @ A @ yf), column_payoff=float(xf @ B @ yf)))
    return dict(equilibria=[dict(row=e['row'].tolist(), column=e['column'].tolist(), row_payoff=e['row_payoff'], column_payoff=e['column_payoff'],
                                 pure=bool((e['row'] > 0).sum() == 1 and (e['column'] > 0).sum() == 1)) for e in found], count=len(found),
                completeness=dict(status='not_certified', count_scope='returned_candidates_only',
                                  method='floating_point_equal_support_enumeration', tolerance=tol,
                                  reason='Degeneracy is not certified; singular supports and continuous equilibrium families may be missed. Even nondegenerate results are subject to numerical tolerance.'))


def _indifference(M: np.ndarray, k: int):
    """Probability vector z (k entries, all positive) with M z equal in every row; None if there is no such strictly mixed vector."""
    system = np.zeros((k + 1, k + 1))
    system[:k, :k] = M
    system[:k, k] = -1.0
    system[k, :k] = 1.0
    rhs = np.zeros(k + 1)
    rhs[k] = 1.0
    try:
        solution = np.linalg.solve(system, rhs)
    except np.linalg.LinAlgError:
        return None
    z = solution[:k]
    return z if (z > 1e-12).all() else None
