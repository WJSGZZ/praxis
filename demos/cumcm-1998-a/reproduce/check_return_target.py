"""Find the least single-asset risk exposure for a supplied net-return target.

Targets are illustrative preferences, not inferred company or market data.
The original minimum-fee budget and profit definitions are retained.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


def solve_target(data, budget, target):
    data = np.asarray(data, dtype=float)
    if (data.ndim != 2 or data.shape[1] != 4 or not len(data)
            or not np.isfinite(data).all() or (data[:, 1] <= 0).any()
            or (data[:, 2:] < 0).any() or not np.isfinite(budget)
            or budget <= 0 or not np.isfinite(target)):
        raise ValueError('Finite asset rows, positive risk/budget and nonnegative fees required')
    n = len(data)
    r, q, p, u = data.T.copy()
    r /= 100
    q /= 100
    p /= 100
    u /= budget
    upper_return = float(max(.05, np.max((r - p) / (1 + p))))
    result = {'budget_yuan': float(budget), 'target_net_return': float(target),
              'proportional_fee_return_upper_bound': upper_return}
    if target > upper_return:
        return {**result, 'status': 'infeasible',
                'evidence': 'target exceeds unrestricted proportional-fee upper bound'}
    if target <= .05:
        return {**result, 'status': 'optimal', 'minimum_risk': 0.,
                'investments_yuan': [0.] * n, 'fees_yuan': [0.] * n,
                'bank_yuan': float(budget), 'net_return': .05,
                'evidence': 'bank-only feasible portfolio and nonnegative-risk lower bound'}
    # Variables: bank, principals, fees, activation binaries, risk ceiling.
    size = 2 + 3 * n
    ix = np.arange(1, 1 + n)
    jf, ky, iz = ix + n, ix + 2 * n, size - 1
    upper = np.r_[1., np.ones(n), p * np.maximum(1, u), np.ones(n), max(q)]
    rows, lower, higher = [], [], []

    def constraint(coefficients, lo=-np.inf, hi=0.):
        row = np.zeros(size)
        for index, value in coefficients.items():
            row[index] = value
        rows.append(row)
        lower.append(lo)
        higher.append(hi)

    constraint({0: 1., **{int(i): 1. for i in np.r_[ix, jf]}}, lo=1., hi=1.)
    constraint({0: .05, **{int(i): float(a) for i, a in zip(ix, r)},
                **{int(i): -1. for i in jf}}, lo=target, hi=np.inf)
    for i in range(n):
        x, f, y = int(ix[i]), int(jf[i]), int(ky[i])
        constraint({x: p[i], f: -1.})
        constraint({y: p[i] * u[i], f: -1.})
        constraint({x: 1., y: -1.})
        constraint({f: 1., y: -upper[f]})
        constraint({x: q[i], iz: -1.})
    objective = np.zeros(size)
    objective[iz] = 1.
    fit = milp(objective, integrality=np.r_[np.zeros(1 + 2 * n), np.ones(n), 0.],
               bounds=Bounds(np.zeros(size), upper),
               constraints=LinearConstraint(np.asarray(rows), lower, higher),
               options={'mip_rel_gap': 1e-9, 'time_limit': 20})
    if fit.status == 2:
        return {**result, 'status': 'infeasible', 'evidence': 'MILP infeasibility status',
                'solver_message': fit.message}
    if not fit.success:
        raise RuntimeError(fit.message)
    x = np.where(fit.x[ky] > .5, np.maximum(fit.x[ix], 0.), 0.) * budget
    # Epigraph fees may exceed the actual fee under a risk-minimizing objective.
    # Recompute actual fees and put every saved yuan into the bank. This raises
    # return without changing risk, so the feasible-target formulation is exact.
    fees = np.where(x > 0, p * np.maximum(x, data[:, 3]), 0.)
    bank = budget - x.sum() - fees.sum()
    profit = .05 * bank + r @ x - fees.sum()
    risk = float(np.max(q * x) / budget)
    if bank < -budget * 1e-7 or profit / budget < target - 1e-7:
        raise RuntimeError('Reconstructed original-fee portfolio is infeasible')
    return {**result, 'status': 'optimal', 'minimum_risk': risk,
            'investments_yuan': x.tolist(), 'fees_yuan': fees.tolist(),
            'bank_yuan': float(bank), 'net_return': float(profit / budget),
            'solver_risk': float(fit.x[iz]), 'mip_gap': float(fit.mip_gap),
            'evidence': 'numeric MILP optimum; exact independent bound checked separately'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget', type=float, default=1_000_000.)
    parser.add_argument('--group', choices=['four', 'fifteen'])
    parser.add_argument('--target', type=float, action='append',
                        help='Net return as a fraction, e.g. 0.20; requires --group')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.target and not args.group:
        parser.error('--target requires --group')
    root = Path(__file__).resolve().parent
    target = args.output or root / 'reproduced/return-targets.json'
    if target.exists():
        raise FileExistsError('Refusing to replace an existing target result')
    scenarios = {'four': ('assets4.csv', [.05, .20, .22, .25, .27]),
                 'fifteen': ('assets15.csv', [.05, .30, .33, .38, .41])}
    result = {'preference_source': 'illustrative inputs, not supplied by the company',
              'risk_definition': 'max_i(q_i*x_i)/initial_budget', 'groups': {}}
    for key, (filename, defaults) in scenarios.items():
        if args.group and key != args.group:
            continue
        with (root / 'data' / filename).open(encoding='utf-8') as handle:
            data = [[float(row[k]) for k in ['return_pct', 'risk_pct', 'fee_pct',
                                            'threshold_yuan']] for row in csv.DictReader(handle)]
        result['groups'][key] = [solve_target(data, args.budget, t)
                                 for t in (args.target or defaults)]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
                      encoding='utf-8')
    print(json.dumps({k: [{a: x[a] for a in ['target_net_return', 'status',
                                          'minimum_risk'] if a in x} for x in v]
                      for k, v in result['groups'].items()}, indent=2))


if __name__ == '__main__':
    main()
