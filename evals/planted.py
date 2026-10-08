"""Public synthetic tool-regression tasks with known or independently computed answers.

    python -m evals.planted new queue 7
    python -m evals.planted check queue 7 '{"mean_wait": 0.42}'

Generators and seeds are public: this is not an isolated or blind Agent benchmark.
solve_with_tools tests computation, not Agent behavior or plugin effectiveness.
See ORACLES.md for oracle independence, mathematical scope and tolerances.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from fractions import Fraction
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import minimize_scalar

from modeling import decision_models, epidemic, optimize, pde, queueing, structure


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
                dict(c=c.tolist(), A=A.tolist(), b=b.tolist()), ['value', 'x'])
    return task, dict(value=value)


def _queue_wait_oracle(lam, mu, c):
    """Birth-death stationary weights and geometric tail, in exact rational arithmetic."""
    arrival, service = Fraction(str(lam)), Fraction(str(mu))
    rho = arrival / (c * service)
    if not (0 < rho < 1):
        raise ValueError('The stationary oracle requires 0 < lam < c*mu')
    weights = [Fraction(1)]
    for n in range(1, c + 1):
        weights.append(weights[-1] * arrival / (n * service))
    normalizer = sum(weights[:-1]) + weights[-1] / (1 - rho)
    queue_length = weights[-1] * rho / (1 - rho)**2 / normalizer
    return float(queue_length / arrival)


def _sir_attack_oracle(r0, susceptible=0.99999):
    """Finite initial infection: solve log(s/s0)+R0*(1-s)=0 by bisection."""
    lo, hi = 1e-300, min(susceptible, 1 / r0)
    for _ in range(100):
        mid = (lo + hi) / 2
        if math.log(mid / susceptible) + r0 * (1 - mid) > 0:
            hi = mid
        else:
            lo = mid
    return 1 - (lo + hi) / 2


def gen_queue(seed):
    r = _rng('queue', seed)
    c = int(r.integers(1, 5))
    mu = float(r.integers(2, 6))
    lam = float(round(c * mu * r.uniform(.4, .85), 2))
    wait = _queue_wait_oracle(lam, mu, c)
    task = Task('queue', seed, 'Customers arrive at rate lam (Poisson); each of c servers serves at rate mu (exponential). Report the steady-state mean waiting time before service.',
                dict(lam=lam, mu=mu, c=c), ['mean_wait'])
    return task, dict(mean_wait=wait)


def gen_sir(seed):
    r = _rng('sir', seed)
    beta, gamma = float(round(r.uniform(.3, .7), 3)), float(round(r.uniform(.1, .25), 3))
    out = epidemic.simulate_sir(beta, gamma, 1_000_000., 10., 120)
    final = _sir_attack_oracle(beta / gamma)
    task = Task('sir', seed, 'A closed SIR epidemic has S(0)=999990, I(0)=10, R(0)=0, population 1000000. Daily infected counts are given. Estimate R0 and the final fraction ever infected (including initial infections). Time is in days.',
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


def _family_properties(family: int, a: int, b: int) -> list[str]:
    """Exact labels for these nine families only, on [1,3]^2; proofs in ORACLES.md."""
    if a not in (1, 2, 3) or b not in (1, 2, 3) or family not in range(9):
        raise ValueError('Outside the proved finite family')
    labels = (
        (True, a == b, False, True),
        (False, True, False, True),
        (b >= a + 1, False, True, True),
        (False, False, False, False),
        (False, a == b, False, True),
        (False, True, True, True),
        (True, a == b, False, True),
        (b <= 2 * a, True, False, True),
        (False, False, False, True),
    )[family]
    return sorted(key for key, applies in zip(PROPERTIES, labels) if applies)


def gen_structure(seed):
    """A function on 1<=x,y<=3 built from a random family; say which of four properties hold (all that apply)."""
    r = _rng('structure', seed)
    a, b = int(r.integers(1, 4)), int(r.integers(1, 4))
    family = int(r.integers(len(FAMILIES)))
    expr = FAMILIES[family].format(a=a, b=b)
    task = Task('structure', seed, f'For f on the box 1<=x,y<=3, list every property that holds, from {list(PROPERTIES)}. Report properties as a list.',
                dict(expression=expr), ['properties'])
    return task, dict(properties=_family_properties(family, a, b))


def gen_pde(seed):
    """Heat decay of a sum of sine modes with fixed zero ends: the temperature at a point is known in closed form."""
    r = _rng('pde', seed)
    L, k, rc = float(r.integers(1, 4)), float(r.integers(1, 5)), float(r.integers(1, 4))
    coeffs = [float(c) for c in r.integers(-3, 4, 3)]
    if not any(coeffs):
        coeffs[0] = 2.0
    t_end = float(round(r.uniform(.05, .4) * rc * L ** 2 / k, 4))
    x0 = float(round(r.uniform(.2, .8) * L, 3))
    truth = sum(a * np.exp(-k * (m * np.pi / L) ** 2 * t_end / rc) * np.sin(m * np.pi * x0 / L) for m, a in enumerate(coeffs, 1))
    task = Task('pde', seed, 'A rod of length L with both ends held at temperature 0 has conductivity k and volumetric heat capacity rho_c. Its initial temperature is the sum over m=1..3 of coeffs[m-1]*sin(m*pi*x/L). Report the temperature at x0 at time t_end.',
                dict(L=L, k=k, rho_c=rc, coeffs=coeffs, x0=x0, t_end=t_end), ['temperature'])
    return task, dict(temperature=float(truth))


def gen_markov(seed):
    r = _rng('markov', seed)
    P = r.random((4, 4)) + .05
    P /= P.sum(axis=1, keepdims=True)
    w, v = np.linalg.eig(P.T)
    pi = np.real(v[:, np.argmin(abs(w - 1))])
    pi = pi / pi.sum()
    task = Task('markov', seed, 'A system moves among 4 states with the given one-step transition matrix. Report the long-run fraction of time spent in state 0 (index 0).',
                dict(P=np.round(P, 6).tolist()), ['state0'])
    P = np.round(P, 6)
    P /= P.sum(axis=1, keepdims=True)          # the matrix the solver sees is the rounded one, renormalised
    w, v = np.linalg.eig(P.T)
    pi = np.real(v[:, np.argmin(abs(w - 1))])
    task.data['P'] = np.round(P, 9).tolist()
    P = np.array(task.data['P'])
    w, v = np.linalg.eig(P.T)
    pi = np.real(v[:, np.argmin(abs(w - 1))])
    pi = pi / pi.sum()
    return task, dict(state0=float(pi[0]))


def gen_game(seed):
    """A 2x2 zero-sum game without a saddle point: the value has the closed form (ad - bc)/(a + d - b - c)."""
    r = _rng('game', seed)
    while True:
        A = r.integers(-9, 10, (2, 2)).astype(float)
        if A.min(axis=1).max() == A.max(axis=0).min():      # a saddle point: the closed form below does not apply
            continue
        break
    a, b, c, d = A[0, 0], A[0, 1], A[1, 0], A[1, 1]
    value = (a * d - b * c) / (a + d - b - c)
    task = Task('game', seed, 'Two players play a zero-sum matrix game; the row player picks a row and receives the entry. Report the value of the game under optimal mixed strategies.', dict(payoff=A.tolist()), ['value'])
    return task, dict(value=float(value))


def gen_inventory(seed):
    """Newsvendor: the best order quantity is found here by numerical quadrature and scalar optimization of expected profit, not by the critical-fractile formula."""
    r = _rng('inventory', seed)
    price = float(r.integers(8, 15))
    cost = float(r.integers(3, int(price) - 2))
    salvage = float(r.integers(0, int(cost)))
    mean, sd = float(r.integers(80, 200)), float(r.integers(10, 40))
    xs = np.linspace(mean - 8 * sd, mean + 8 * sd, 20001)
    pdf = np.exp(-.5 * ((xs - mean) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))

    def expected_loss(q):
        return -np.trapezoid((np.where(xs < q, price * xs + salvage * (q - xs), price * q) - cost * q) * pdf, xs)

    best = minimize_scalar(expected_loss, bounds=(mean - 4 * sd, mean + 4 * sd), method='bounded', options={'xatol': 1e-6})
    task = Task('inventory', seed, 'Demand is an untruncated normal mathematical approximation with the given mean and standard deviation (negative demand is not clipped). Each unit costs `cost`, sells at `price`, and unsold units return `salvage`. Report the order quantity that maximises expected profit.',
                dict(price=price, cost=cost, salvage=salvage, mean=mean, sd=sd), ['order_quantity'])
    return task, dict(order_quantity=float(best.x))


GENERATORS: dict[str, Callable] = dict(lp=gen_lp, queue=gen_queue, sir=gen_sir, assignment=gen_assignment, structure=gen_structure, pde=gen_pde, markov=gen_markov, game=gen_game, inventory=gen_inventory)


# ----------------------------------------------------------------------------------------------- scoring

TOLERANCE = dict(value=1e-6, mean_wait=1e-6, total=1e-9, r0=0.1, final_size=0.03, temperature=2e-3, state0=1e-6, order_quantity=0.2)


SCORE_VERSION = 'planted-v2'


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def score(kind: str, seed: int, answer: dict) -> dict:
    if kind not in GENERATORS or type(seed) is not int or seed < 0:
        raise ValueError('Expected a known task kind and a nonnegative integer seed')
    task, truth = GENERATORS[kind](seed)
    if not isinstance(answer, dict):
        raise ValueError(f'The answer must be a JSON object with the keys {task.answer_keys}, e.g. {json.dumps(_template(truth))}')
    detail = {}
    for key, want in truth.items():
        got = answer.get(key)
        if key not in answer:
            detail[key] = dict(ok=False, reason='missing')
        elif isinstance(want, list):
            valid = (isinstance(got, list) and all(type(v) is str and v in PROPERTIES for v in got)
                     and len(set(got)) == len(got))
            detail[key] = dict(ok=valid and sorted(got) == want,
                               reason='match' if valid and sorted(got) == want else 'invalid or incorrect property list')
        elif not _finite_number(got):
            detail[key] = dict(ok=False, reason='expected a finite JSON number (not bool or string)')
        else:
            tol = TOLERANCE[key] * (1 if key in ('r0', 'final_size', 'order_quantity') else max(1., abs(want)))
            detail[key] = dict(ok=abs(got - want) <= tol, absolute_tolerance=tol)
    if kind == 'lp':
        x = answer.get('x')
        d = task.data
        valid = isinstance(x, list) and len(x) == len(d['c']) and all(_finite_number(v) for v in x)
        if not valid:
            detail['x'] = dict(ok=False, reason='expected a finite vector of length ' + str(len(d['c'])))
        else:
            x, A, b, c = map(np.asarray, (x, d['A'], d['b'], d['c']))
            feasible = bool(np.all(x >= -1e-8) and np.all(A @ x >= b - 1e-6 * np.maximum(1., abs(b))))
            objective = float(c @ x)
            tol = TOLERANCE['value'] * max(1., abs(truth['value']))
            consistent = _finite_number(answer.get('value')) and abs(objective - answer['value']) <= tol
            optimal = abs(objective - truth['value']) <= tol
            detail['x'] = dict(ok=feasible and consistent and optimal, feasible=feasible,
                               objective_consistent=consistent, optimal=optimal)
    return dict(score_version=SCORE_VERSION, kind=kind, seed=seed,
                correct=all(d['ok'] for d in detail.values()), detail=detail)


# ----------------------------------------------------------------------------------------------- reference solvers (what the tools can recover)

def solve_with_tools(task: Task) -> dict:
    """The answer Praxis's own tools give for a planted task; used by regression tests."""
    d = task.data
    if task.kind == 'lp':
        A = np.array(d['A'])
        r = optimize.solve_lp(d['c'], A_ub=(-A).tolist(), b_ub=(-np.array(d['b'])).tolist())
        return dict(value=r['objective'], x=r['x'])
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
    if task.kind == 'pde':
        r = pde.solve_diffusion(d['L'], 400, d['k'], d['rho_c'], lambda x: sum(c * np.sin((m + 1) * np.pi * x / d['L']) for m, c in enumerate(d['coeffs'])), d['t_end'], 400,
                                left=('dirichlet', 0.0), right=('dirichlet', 0.0), theta=.5)
        return dict(temperature=float(np.interp(d['x0'], r['x'], r['u'])))
    if task.kind == 'markov':
        return dict(state0=decision_models.markov_stationary(d['P'])['stationary'][0])
    if task.kind == 'game':
        return dict(value=decision_models.matrix_game(d['payoff'])['value'])
    if task.kind == 'inventory':
        return dict(order_quantity=decision_models.newsvendor(d['price'], d['cost'], d['salvage'], d['mean'], d['sd'])['order_quantity'])
    raise KeyError(task.kind)


def _template(truth: dict) -> dict:
    return {k: ([] if isinstance(v, list) else '' if isinstance(v, str) else 0.0) for k, v in truth.items()}


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
        t, truth = GENERATORS[a.kind](a.seed)
        template = _template(truth)
        if a.kind == 'lp':
            template['x'] = [0.0] * len(t.data['c'])
        print(json.dumps(dict(statement=t.statement, data=t.data, report=t.answer_keys, answer_template=template, score_version=SCORE_VERSION), ensure_ascii=False))
    else:
        print(json.dumps(score(a.kind, a.seed, json.loads(a.answer))))


if __name__ == '__main__':
    main()
