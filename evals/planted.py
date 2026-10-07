"""Planted-truth problems: synthetic tasks whose correct answer is known by construction, for blind self-checks and regression tests.

    python -m evals.planted list
    python -m evals.planted new queue 7            # prints the task (data and question) without the answer
    python -m evals.planted check queue 7 '{"mean_wait": 0.42}'

A problem is generated from (kind, seed). The statement never contains the truth; `check` recomputes it from the seed and scores the
submitted answer against a tolerance. Use it to test a method or an agent on cases it cannot have seen, and to catch regressions
after changing tools or guidance. Passing planted problems shows the pipeline recovers known structure; it is not evidence of
performance on real problems."""
from __future__ import annotations

import argparse
import itertools
import json
import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from modeling import epidemic, optimize, queueing, structure


@dataclass
class Task:
    kind: str
    seed: int
    statement: str
    data: dict
    answer_keys: list[str]


def _rng(kind, seed):
    return np.random.default_rng([abs(hash(kind)) % (2 ** 31) if False else sum(map(ord, kind)) * 1000003, seed])


# ----------------------------------------------------------------------------------------------- generators: (task, truth)

def gen_lp(seed):
    """Planted LP: x* and dual y* are chosen first and the data are built so that complementary slackness holds, so the optimum is known."""
    r = _rng('lp', seed)
    n, m = 6, 4
    A = r.integers(1, 6, (m, n)).astype(float)
    x = np.where(r.random(n) < .6, r.integers(1, 5, n), 0).astype(float)
    if not x.any():
        x[0] = 2
    slack = A @ x
    tight = r.random(m) < .6
    tight[0] = True
    b = np.where(tight, slack, slack - r.integers(1, 4, m))
    y = np.where(tight, r.integers(1, 4, m), 0).astype(float)
    c = A.T @ y + np.where(x > 0, 0, r.integers(1, 4, n))  # reduced costs >= 0, zero where x > 0
    value = float(c @ x)
    task = Task('lp', seed, 'Minimise c.x subject to A x >= b, x >= 0. Report the optimal value and an optimal x.',
                dict(c=c.tolist(), A=A.tolist(), b=b.tolist()), ['value'])
    return task, dict(value=value)


def gen_queue(seed):
    r = _rng('queue', seed)
    c = int(r.integers(1, 5))
    mu = float(r.integers(2, 6))
    lam = float(round(c * mu * r.uniform(.4, .85), 2))
    q = queueing.mmc(lam, mu, c)
    task = Task('queue', seed, 'Customers arrive at rate lam (Poisson); each of c servers serves at rate mu (exponential). Report the steady-state mean waiting time before service.',
                dict(lam=lam, mu=mu, c=c), ['mean_wait'])
    return task, dict(mean_wait=q['mean_wait'])


def gen_sir(seed):
    r = _rng('sir', seed)
    beta, gamma = float(round(r.uniform(.3, .7), 3)), float(round(r.uniform(.1, .25), 3))
    out = epidemic.simulate_sir(beta, gamma, 1_000_000., 10., 120)
    final = epidemic.final_size(beta / gamma)
    task = Task('sir', seed, 'An SIR epidemic in a population of 1,000,000 starts with 10 infected. Daily infected counts are given. Estimate the basic reproduction number R0 and the final attack rate.',
                dict(infected=[float(v) for v in np.round(out['I'], 3)], population=1_000_000., dates='days 0..120'), ['r0', 'final_size'])
    return task, dict(r0=beta / gamma, final_size=final)


def gen_assignment(seed):
    r = _rng('assignment', seed)
    n = 6
    cost = r.integers(1, 30, (n, n)).astype(float)
    best = min(sum(cost[i, p[i]] for i in range(n)) for p in itertools.permutations(range(n)))
    task = Task('assignment', seed, 'Assign each of 6 workers to a distinct job at minimum total cost. Report the minimum total cost.', dict(cost=cost.tolist()), ['total'])
    return task, dict(total=float(best))


PROPERTIES = ('convex', 'symmetric', 'power_law', 'increasing_in_x')
FAMILIES = ('{a}*x**2 + {b}*y**2', '{a}*(x + y) + {b}*x*y', '{a}*x**{b}/y**{a}', '{a}*sin(x) + {b}*y**2', '{a}*x + {b}*y + exp(x*y/4)',
            'x*y', 'exp({a}*x) + exp({b}*y)', '{a}*x**2 + {b}*x*y + {a}*y**2', 'log(x) + {a}*y')


def _true_properties(expr: str) -> list[str]:
    """Ground truth by symbolic algebra and dense grids, independent of the sampled probes the solver uses."""
    import sympy as sp
    x, y = sp.symbols('x y', positive=True)
    f = sp.sympify(expr, locals=dict(x=x, y=y))
    out = []
    grid = np.linspace(1, 3, 81)
    X, Y = np.meshgrid(grid, grid)
    h = [sp.lambdify((x, y), sp.diff(f, *v), 'numpy') for v in ((x, x), (x, y), (y, y))]
    h00, h01, h11 = (np.broadcast_to(g(X, Y), X.shape) for g in h)
    if (h00 >= -1e-9).all() and (h11 >= -1e-9).all() and (h00 * h11 - h01 ** 2 >= -1e-9).all():
        out.append('convex')
    if sp.simplify(f - f.subs({x: y, y: x}, simultaneous=True)) == 0:
        out.append('symmetric')
    ex, ey = sp.simplify(x * sp.diff(f, x) / f), sp.simplify(y * sp.diff(f, y) / f)
    if not ex.free_symbols and not ey.free_symbols:
        out.append('power_law')
    fx = np.broadcast_to(sp.lambdify((x, y), sp.diff(f, x), 'numpy')(X, Y), X.shape)
    if (fx >= -1e-12).all():
        out.append('increasing_in_x')
    return sorted(out)


def gen_structure(seed):
    """A function on 1<=x,y<=3 built from a random family; say which of four properties hold (all that apply)."""
    r = _rng('structure', seed)
    a, b = int(r.integers(1, 4)), int(r.integers(1, 4))
    expr = FAMILIES[int(r.integers(len(FAMILIES)))].format(a=a, b=b)
    task = Task('structure', seed, f'For f on the box 1<=x,y<=3, list every property that holds, from {list(PROPERTIES)}. Report properties as a list.',
                dict(expression=expr), ['properties'])
    return task, dict(properties=_true_properties(expr))


GENERATORS: dict[str, Callable] = dict(lp=gen_lp, queue=gen_queue, sir=gen_sir, assignment=gen_assignment, structure=gen_structure)


# ----------------------------------------------------------------------------------------------- scoring

TOLERANCE = dict(value=1e-6, mean_wait=1e-6, total=1e-9, r0=0.1, final_size=0.03)


def score(kind: str, seed: int, answer: dict) -> dict:
    _, truth = GENERATORS[kind](seed)
    detail = {}
    for key, want in truth.items():
        got = answer.get(key)
        if got is None:
            detail[key] = dict(ok=False, reason='missing')
        elif isinstance(want, list):
            detail[key] = dict(ok=sorted(got) == want)
        elif isinstance(want, str):
            detail[key] = dict(ok=str(got) == want)
        else:
            tol = TOLERANCE[key]
            detail[key] = dict(ok=abs(float(got) - want) <= tol * max(1.0, abs(want)) if key in ('value', 'mean_wait', 'total') else abs(float(got) - want) <= tol)
    return dict(kind=kind, seed=seed, correct=all(d['ok'] for d in detail.values()), detail=detail)


# ----------------------------------------------------------------------------------------------- reference solvers (what the tools can recover)

def solve_with_tools(task: Task) -> dict:
    """The answer Praxis's own tools give for a planted task; used by regression tests."""
    d = task.data
    if task.kind == 'lp':
        A = np.array(d['A'])
        r = optimize.solve_lp(d['c'], A_ub=(-A).tolist(), b_ub=(-np.array(d['b'])).tolist())
        return dict(value=r['objective'])
    if task.kind == 'queue':
        return dict(mean_wait=queueing.mmc(d['lam'], d['mu'], d['c'])['mean_wait'])
    if task.kind == 'sir':
        fit = epidemic.fit_sir(d['infected'], d['population'])
        r0 = fit['beta'] / fit['gamma']
        return dict(r0=r0, final_size=epidemic.final_size(r0))
    if task.kind == 'assignment':
        return dict(total=optimize.assignment(d['cost'])['total'])
    if task.kind == 'structure':
        from scripts.mcp_server import _scalar
        f = _scalar(d['expression'], ['x', 'y'])
        box = [[1, 3], [1, 3]]
        found = []
        if structure.check_convexity(f, box)['convex']:
            found.append('convex')
        if structure.check_symmetry(f, box, [1, 0])['symmetric']:
            found.append('symmetric')
        if structure.check_power_law(f, box)['power_law']:
            found.append('power_law')
        if structure.check_monotone(f, box, 0)['kind'] in ('nondecreasing', 'constant'):
            found.append('increasing_in_x')
        return dict(properties=sorted(found))
    raise KeyError(task.kind)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    n = sub.add_parser('new')
    n.add_argument('kind', choices=GENERATORS)
    n.add_argument('seed', type=int)
    c = sub.add_parser('check')
    c.add_argument('kind', choices=GENERATORS)
    c.add_argument('seed', type=int)
    c.add_argument('answer')
    a = p.parse_args()
    if a.cmd == 'list':
        print('\n'.join(GENERATORS))
    elif a.cmd == 'new':
        t = GENERATORS[a.kind](a.seed)[0]
        print(json.dumps(dict(statement=t.statement, data=t.data, report=t.answer_keys), ensure_ascii=False))
    else:
        print(json.dumps(score(a.kind, a.seed, json.loads(a.answer))))


if __name__ == '__main__':
    main()
