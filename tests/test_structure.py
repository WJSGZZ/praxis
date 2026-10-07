import itertools

import numpy as np
import pytest

from modeling import structure as st


def test_convexity_finds_witness_or_fails_to_refute():
    assert st.check_convexity(lambda x: x[0] ** 2 + abs(x[1]), [[-2, 2], [-2, 2]])['convex']
    assert st.check_convexity(lambda x: np.log(np.exp(x[0]) + np.exp(x[1])), [[-3, 3], [-3, 3]])['convex']
    bad = st.check_convexity(lambda x: np.sin(x[0]), [[0, 2 * np.pi]])
    assert not bad['convex'] and bad['proved']
    assert st.check_convexity(lambda x: -x[0] ** 2, [[-1, 1]])['convex'] is False
    assert st.check_convexity(lambda x: 3 * x[0] + 1, [[-1, 1]])['concave_also']


def test_monotone_and_symmetry_and_power_law():
    assert st.check_monotone(lambda x: x[0] * x[1], [[1, 2], [1, 2]], 0)['kind'] == 'nondecreasing'
    assert st.check_monotone(lambda x: -x[0] + 0 * x[1], [[1, 2], [1, 2]], 0)['kind'] == 'nonincreasing'
    assert st.check_monotone(lambda x: x[0] ** 2, [[-1, 1]], 0)['kind'] == 'not monotone'
    f = lambda x: x[0] * x[1] + x[0] + x[1]
    assert st.check_symmetry(f, [[0, 1], [0, 1]], [1, 0])['symmetric']
    assert not st.check_symmetry(lambda x: x[0] - x[1], [[0, 1], [0, 1]], [1, 0])['symmetric']
    with pytest.raises(ValueError):
        st.check_symmetry(f, [[0, 1], [0, 2]], [1, 0])
    law = st.check_power_law(lambda x: 3.0 * x[0] ** 2 / x[1], [[1, 4], [1, 4]])
    assert law['power_law'] and np.allclose(law['exponents'], [2, -1], atol=1e-4)
    assert not st.check_power_law(lambda x: x[0] + x[1], [[1, 4], [1, 4]])['power_law']


def test_invariants_of_known_systems():
    oscillator = lambda x: np.array([x[1], -x[0]])
    assert st.check_invariant(oscillator, lambda x: x[0] ** 2 + x[1] ** 2, [[-2, 2], [-2, 2]])['conserved']
    assert not st.check_invariant(oscillator, lambda x: x[0] + x[1], [[-2, 2], [-2, 2]])['conserved']
    a, b, c, d = 1.1, 0.4, 0.4, 0.1  # Lotka-Volterra x' = a x - b x y, y' = d x y - c y
    lv = lambda z: np.array([a * z[0] - b * z[0] * z[1], d * z[0] * z[1] - c * z[1]])
    V = lambda z: d * z[0] - c * np.log(z[0]) + b * z[1] - a * np.log(z[1])
    assert st.check_invariant(lv, V, [[0.5, 5], [0.5, 5]])['conserved']
    assert not st.check_invariant(lv, lambda z: z[0] + z[1], [[0.5, 5], [0.5, 5]])['conserved']


def test_buckingham_pi_pendulum_and_drag():
    # rows: mass, length, time; variables: period, length, g, mass
    pend = st.buckingham_pi([[0, 0, 0, 1], [0, 1, 1, 0], [1, 0, -2, 0]], ['T', 'L', 'g', 'm'])
    assert pend['n_groups'] == 1 and pend['groups'][0] in ({'T': 2, 'L': -1, 'g': 1}, {'T': -2, 'L': 1, 'g': -1})
    # drag force F, density rho, speed v, diameter D, viscosity mu -> two groups (drag coefficient and Reynolds number)
    drag = st.buckingham_pi([[1, 1, 0, 0, 1], [1, -3, 1, 1, -1], [-2, 0, -1, 0, -1]], ['F', 'rho', 'v', 'D', 'mu'])
    assert drag['n_groups'] == 2 and drag['rank'] == 3


def _tu_bruteforce(A):
    m, n = A.shape
    for k in range(1, min(m, n) + 1):
        for rows in itertools.combinations(range(m), k):
            for cols in itertools.combinations(range(n), k):
                if round(abs(np.linalg.det(A[np.ix_(rows, cols)]))) > 1:
                    return False
    return True


def test_network_matrix_criterion_agrees_with_brute_force():
    incidence = np.array([[1, 1, 0, 0], [-1, 0, 1, 0], [0, -1, -1, 1], [0, 0, 0, -1]])  # directed graph, one column per arc
    assert st.is_network_matrix(incidence)['totally_unimodular']
    odd_cycle = np.array([[1, 1, 0], [0, 1, 1], [1, 0, 1]])  # det = 2
    assert not st.is_network_matrix(odd_cycle)['totally_unimodular']
    rng = np.random.default_rng(3)
    for _ in range(300):
        A = np.zeros((5, 6))
        for j in range(6):
            rows = rng.choice(5, size=rng.integers(0, 3), replace=False)
            A[rows, j] = rng.choice([-1, 1], size=len(rows))
        got = st.is_network_matrix(A)
        assert got['proved'] and got['totally_unimodular'] == _tu_bruteforce(A), A
    assert st.is_network_matrix(np.array([[2, 0], [0, 1]]))['totally_unimodular'] is False
