"""Small decision models with closed forms or linear programs: Markov chains, matrix games, EOQ, newsvendor, CVaR portfolios, Pareto fronts."""
from __future__ import annotations

import itertools
import math

import numpy as np
from scipy.stats import norm

from modeling import optimize


def markov_stationary(P) -> dict:
    """Stationary distribution of an irreducible finite chain: solve pi P = pi, sum pi = 1. Reports irreducibility and the residual."""
    P = np.asarray(P, float)
    n = P.shape[0]
    if P.ndim != 2 or P.shape[1] != n or (P < -1e-12).any() or not np.allclose(P.sum(axis=1), 1, atol=1e-9):
        raise ValueError('P must be a square row-stochastic matrix')
    reach = np.linalg.matrix_power((P > 0).astype(float) + np.eye(n), n) > 0
    irreducible = bool(reach.all())
    A = np.vstack([P.T - np.eye(n), np.ones(n)])
    b = np.r_[np.zeros(n), 1.0]
    pi = np.linalg.lstsq(A, b, rcond=None)[0]
    return dict(stationary=pi.tolist(), irreducible=irreducible, residual=float(np.abs(pi @ P - pi).max()),
                note=None if irreducible else 'Chain is reducible: the stationary distribution may not be unique.')


def markov_absorption(P, absorbing) -> dict:
    """Absorption probabilities and expected steps to absorption from each transient state (fundamental matrix N = (I - Q)^-1)."""
    P = np.asarray(P, float)
    n = P.shape[0]
    absorbing = sorted(set(int(i) for i in absorbing))
    for i in absorbing:
        if not np.isclose(P[i, i], 1.0):
            raise ValueError(f'State {i} is not absorbing (P[i,i] must be 1)')
    transient = [i for i in range(n) if i not in absorbing]
    Q, R = P[np.ix_(transient, transient)], P[np.ix_(transient, absorbing)]
    N = np.linalg.inv(np.eye(len(transient)) - Q)
    return dict(transient=transient, absorbing=absorbing, expected_steps=(N @ np.ones(len(transient))).tolist(), absorption_probabilities=(N @ R).tolist())


def matrix_game(payoff) -> dict:
    """Value and optimal mixed strategies of a zero-sum matrix game (row player maximises), by linear programming."""
    A = np.asarray(payoff, float)
    m, n = A.shape
    shift = 1 - A.min()          # make all payoffs positive so the value is positive
    B = A + shift
    # row player: minimise sum(u) s.t. B^T u >= 1, u >= 0; value = 1/sum(u)
    row = optimize.solve_lp(np.ones(m), A_ub=(-B.T).tolist(), b_ub=(-np.ones(n)).tolist())
    col = optimize.solve_lp(-np.ones(n), A_ub=B.tolist(), b_ub=np.ones(m).tolist())
    u, v = np.array(row['x']), np.array(col['x'])
    value = 1 / u.sum()
    return dict(value=float(value - shift), row_strategy=(u * value).tolist(), column_strategy=(v / v.sum()).tolist(),
                has_saddle=bool(np.isclose(A.min(axis=1).max(), A.max(axis=0).min())))


def eoq(demand: float, order_cost: float, holding_cost: float, *, stockout_cost: float | None = None) -> dict:
    """Economic order quantity Q* = sqrt(2 D S / H); with planned shortages (backorder cost b per unit-year) Q* = sqrt(2DS/H) sqrt((H+b)/b)."""
    if min(demand, order_cost, holding_cost) <= 0:
        raise ValueError('demand, order_cost and holding_cost must be positive')
    q = math.sqrt(2 * demand * order_cost / holding_cost)
    if stockout_cost is None:
        return dict(order_quantity=q, cycle_time=q / demand, annual_cost=math.sqrt(2 * demand * order_cost * holding_cost))
    b = float(stockout_cost)
    if b <= 0:
        raise ValueError('stockout_cost must be positive')
    q = q * math.sqrt((holding_cost + b) / b)
    s = q * b / (holding_cost + b)                  # maximum on-hand inventory; the rest of the cycle is backordered
    cost = order_cost * demand / q + holding_cost * s ** 2 / (2 * q) + b * (q - s) ** 2 / (2 * q)
    return dict(order_quantity=q, max_inventory=s, max_backorder=q - s, annual_cost=cost)


def newsvendor(price: float, cost: float, salvage: float, mean: float, sd: float) -> dict:
    """Optimal order for normal demand: critical fractile F(Q*) = (p - c) / (p - s); expected profit by the standard loss function."""
    if not price > cost > salvage or sd <= 0:
        raise ValueError('Need price > cost > salvage and sd > 0')
    ratio = (price - cost) / (price - salvage)
    z = float(norm.ppf(ratio))
    q = mean + sd * z
    loss = sd * (norm.pdf(z) - z * (1 - norm.cdf(z)))      # expected lost sales E[(D - Q)+]
    sales = mean - loss
    profit = price * sales + salvage * (q - sales) - cost * q
    return dict(critical_fractile=float(ratio), order_quantity=float(q), expected_lost_sales=float(loss), expected_profit=float(profit), service_level=float(ratio))


def cvar_portfolio(returns, target: float, *, alpha: float = 0.95, long_only: bool = True) -> dict:
    """Minimum-CVaR portfolio for scenario returns (rows = scenarios) with expected return >= target (Rockafellar-Uryasev LP).

    Loss is the negative portfolio return; CVaR_alpha is the mean of the worst (1 - alpha) share of scenarios. The answer is
    conditional on the scenarios supplied; it is not a forecast."""
    R = np.asarray(returns, float)
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
    w = np.array(r['x'][:n])
    losses = -(R @ w)
    k = max(1, int(math.ceil((1 - alpha) * S)))
    return dict(weights=w.tolist(), cvar=float(r['objective']), var=float(r['x'][n]), expected_return=float(R.mean(axis=0) @ w),
                empirical_tail_mean=float(np.sort(losses)[::-1][:k].mean()))


def pareto_front(points, senses) -> dict:
    """Non-dominated rows of a table of objective values. senses: +1 to maximise a column, -1 to minimise."""
    X = np.asarray(points, float) * np.asarray(senses, float)
    n = len(X)
    keep = []
    for i in range(n):
        dominated = any(np.all(X[j] >= X[i]) and np.any(X[j] > X[i]) for j in range(n) if j != i)
        if not dominated:
            keep.append(i)
    return dict(indices=keep, points=np.asarray(points, float)[keep].tolist(), dominated=[i for i in range(n) if i not in keep])


def bimatrix_nash(A, B, *, max_support: int = 6, tol: float = 1e-9) -> dict:
    """All Nash equilibria of a two-player game (payoff matrices A for the row player, B for the column player) by support enumeration.

    Exact for nondegenerate games up to `max_support` actions per player; a degenerate game can have continua of equilibria, which
    enumeration reports only through their extreme points on the supports it tries. Many games have several equilibria: say which one
    the players are expected to play and why, or give a guarantee that holds in all of them."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    if A.shape != B.shape:
        raise ValueError('A and B must have the same shape')
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
                                 pure=bool((e['row'] > 0).sum() == 1 and (e['column'] > 0).sum() == 1)) for e in found], count=len(found))


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
