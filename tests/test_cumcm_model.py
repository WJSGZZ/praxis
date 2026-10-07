"""The CUMCM demo's mixed-integer model against an independent enumeration of fee regimes (one LP per regime)."""
import importlib.util
import itertools
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

SPEC = importlib.util.spec_from_file_location('cumcm_model', Path(__file__).resolve().parents[1] / 'demos/cumcm-1998-a/reproduce/code/model.py')
model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model)


def enumerate_best(data, budget, cap):
    """Each asset is unused, bought below its threshold (fee p*u), or bought above it (fee p*x); solve an LP in every combination."""
    r, q, p, u = data[:, 0] / 100, data[:, 1] / 100, data[:, 2] / 100, data[:, 3]
    n = len(r)
    best = 0.05 * budget
    for regimes in itertools.product((0, 1, 2), repeat=n):
        cost = np.zeros(n + 1)  # variables: x_1..x_n, bank
        cost[-1] = -0.05
        a_eq, b_eq, a_ub, b_ub, bounds, fixed = np.zeros(n + 1), budget, [], [], [], 0.0
        a_eq[-1] = 1
        for i, g in enumerate(regimes):
            if g == 0:
                bounds.append((0, 0))
                continue
            cost[i] = -r[i]
            a_eq[i] = 1
            if g == 1:   # x <= u, fee p*u paid in full
                fixed += p[i] * u[i]
                bounds.append((0, u[i]))
            else:        # x >= u, fee p*x
                a_eq[i] += p[i]
                cost[i] += p[i]
                bounds.append((u[i], None))
            row = np.zeros(n + 1)
            row[i] = q[i]
            a_ub.append(row)
            b_ub.append(cap * budget)
        bounds.append((0, None))
        res = linprog(cost, A_ub=np.array(a_ub) if a_ub else None, b_ub=b_ub or None, A_eq=[a_eq], b_eq=[budget - fixed], bounds=bounds, method='highs')
        if res.status == 0:
            best = max(best, -res.fun - fixed)
    return best


def test_model_matches_enumeration_and_never_overspends():
    rng = np.random.default_rng(11)
    checked = 0
    for _ in range(25):
        n = int(rng.integers(3, 5))
        data = np.column_stack([rng.uniform(5, 40, n), rng.uniform(1, 10, n), rng.uniform(.5, 6, n), rng.uniform(20, 400, n)])
        budget = float(rng.choice([100, 300, 1000, 5000]))
        cap = float(rng.uniform(.01, .2))
        result = model.solve(data, budget, cap)
        assert result['bank_yuan'] >= -1e-9 * budget
        assert abs(result['net_return'] * budget - enumerate_best(data, budget, cap)) <= 1e-6 * budget
        checked += 1
    assert checked == 25
