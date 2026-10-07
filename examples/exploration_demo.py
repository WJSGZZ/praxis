"""Three small explorations that use the structure probes, the route record and experimental-mathematics tools together.

    uv run --locked python -m examples.exploration_demo

The cases are synthetic and small enough to check by hand. They show the working pattern (name a structure, test it, attack the route,
keep what survives); they are not a classifier of real problems."""
import json

import numpy as np

from modeling import experiment, routes, structure


def transport_case():
    """A shipping problem whose constraint matrix is a directed-graph incidence matrix: the integer program is unnecessary."""
    arcs = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)]
    A = np.zeros((4, len(arcs)))
    for j, (u, v) in enumerate(arcs):
        A[u, j], A[v, j] = 1, -1                      # flow conservation rows, one column per arc
    unimodular = structure.is_network_matrix(A)
    graph = routes.apply(None, [
        dict(op='add_structure', key='flow', text='conservation at every node; arcs are columns of an incidence matrix', evidence='checked'),
        dict(op='add_assumption', key='integral_supply', text='supplies and capacities are integers', evidence='assumed', if_false='solve the integer program'),
        dict(op='add_path', key='lp', title='linear program (min-cost flow)', structure='flow', assumptions=['integral_supply']),
        dict(op='add_path', key='milp', title='mixed-integer program on arc flows'),
        dict(op='add_path', key='sim', title='simulation of dispatch rules'),
        dict(op='attack', key='lp', claim='LP vertices are integral', method='total unimodularity of the constraint matrix', outcome='survived' if unimodular['totally_unimodular'] else 'killed'),
        dict(op='kill', key='milp', reason='unneeded: the LP already returns integral vertices; keep as a cross-check'),
        dict(op='keep_result', key='tu', statement='constraint matrix is totally unimodular', status='checked', source_path='lp'),
        dict(op='choose', key='lp', why='integral optimum from a polynomial method, with a dual certificate'),
    ], question='Ship goods over a small network at least cost')
    return dict(total_unimodular=unimodular['totally_unimodular'], chosen=[k for k, p in graph['graph']['paths'].items() if p['status'] == 'chosen'], issues=graph['issues'])


def structure_case():
    """Which properties does a function have? A refutation is a proof; survival is evidence."""
    f = lambda x: x[0] ** 2 + x[0] * x[1] + x[1] ** 2
    box = [[-2, 2], [-2, 2]]
    return dict(convex=structure.check_convexity(f, box)['convex'],
                symmetric=structure.check_symmetry(f, box, [1, 0])['symmetric'],
                monotone_in_x=structure.check_monotone(f, box, 0)['kind'])


def experiment_case():
    """Euler's polynomial looks prime-generating; the search finds where it stops. A recurrence is guessed from data."""
    is_prime = lambda m: m > 1 and all(m % k for k in range(2, int(m ** .5) + 1))
    first_failure = experiment.find_counterexample(lambda n: is_prime(n * n + n + 41), [('int', 0, 100)])
    pell = experiment.guess_linear_recurrence([0, 1, 2, 5, 12, 29, 70, 169, 408, 985])
    return dict(euler_polynomial_fails_at=first_failure['counterexample'], pell_recurrence=pell['coefficients'])


def main():
    print(json.dumps(dict(transport=transport_case(), structure=structure_case(), experiment=experiment_case()), indent=1, default=str))


if __name__ == '__main__':
    main()
