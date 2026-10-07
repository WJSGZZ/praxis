import math

import mpmath as mp
import pytest

from modeling import experiment as ex


def test_counterexample_search_exhaustive_and_shrunk():
    # Euler's polynomial n^2 + n + 41 is prime for n = 0..39 and fails first at n = 40
    prime = lambda m: m > 1 and all(m % k for k in range(2, int(math.isqrt(m)) + 1))
    r = ex.find_counterexample(lambda n: prime(n * n + n + 41), [('int', 0, 100)])
    assert r['found'] and r['exhaustive'] and r['counterexample'] == [40]
    ok = ex.find_counterexample(lambda n: n * n + n + 41 > 0, [('int', 0, 50)])
    assert not ok['found'] and ok['proved_for_domain']
    # a false inequality over the reals is found and shrunk toward the simplest failing point
    r = ex.find_counterexample(lambda x, y: x * y <= (x + y) ** 2 / 4 + 1e-12 and x + y < 1.9, [('real', 0, 2), ('real', 0, 2)])
    assert r['found']
    assert sum(r['shrunk']) <= sum(r['counterexample']) + 1e-9
    # claims that raise count as failures
    assert ex.find_counterexample(lambda n: 10 // n > 0, [('int', 0, 5)])['counterexample'] == [0]


def test_conjecture_testing_with_high_precision():
    assert ex.test_conjecture(lambda x: mp.sin(x) ** 2 + mp.cos(x) ** 2, lambda x: mp.mpf(1), '==', [[-5, 5]])['holds']
    assert ex.test_conjecture(lambda x, y: (x + y) ** 2, lambda x, y: 4 * x * y, '>=', [[-3, 3], [-3, 3]])['holds']
    bad = ex.test_conjecture(lambda x: x ** 2, lambda x: x, '<=', [[0, 3]])
    assert not bad['holds'] and bad['worst_violation'] > 1
    near = ex.test_conjecture(lambda x: mp.mpf(1) + mp.mpf(10) ** -12 * x, lambda x: mp.mpf(1), '==', [[1, 2]])
    assert not near['holds']  # double precision would call this equal


def test_recurrence_and_polynomial_guessing():
    fib = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    r = ex.guess_linear_recurrence(fib)
    assert r['found'] and r['order'] == 2 and r['coefficients'] == ['1', '1']
    pell = [0, 1, 2, 5, 12, 29, 70, 169, 408, 985]
    assert ex.guess_linear_recurrence(pell)['coefficients'] == ['2', '1']
    catalan = [1, 1, 2, 5, 14, 42, 132, 429, 1430, 4862, 16796, 58786, 208012]
    assert not ex.guess_linear_recurrence(catalan, max_order=4)['found']
    assert 'need at least' in ex.guess_linear_recurrence([1, 2, 3, 5])['reason']
    squares_sum = [sum(k * k for k in range(n + 1)) for n in range(10)]
    p = ex.guess_polynomial(squares_sum)
    assert p['found'] and p['degree'] == 3
    assert not ex.guess_polynomial([2 ** n for n in range(12)], max_degree=6)['found']


def test_integer_relations_and_safe_evaluation():
    r = ex.find_relation('zeta(2)', {'pi2': 'pi**2'})
    assert r['found'] and r['coefficients'] == {'value': 6, 'pi2': -1} or r['coefficients'] == {'value': -6, 'pi2': 1}
    assert r['residual'] < 1e-40
    none = ex.find_relation('pi', {'e': 'e', 'one': '1'}, max_coeff=50)
    assert not none['found'] or max(abs(c) for c in none['coefficients'].values()) > 20
    with pytest.raises(ValueError):
        ex.find_relation('().__class__', {'one': '1'})


def test_holdout_and_finite_check_proof_of_a_recurrence():
    tilings = [1, 3, 11, 41, 153, 571, 2131, 7953, 29681, 110771, 413403, 1542841, 5757961, 21489003, 80198051, 299303201, 1117014753]  # 3 x 2n domino tilings
    r = ex.guess_linear_recurrence(tilings[:13], holdout=0)
    assert r['coefficients'] == ['4', '-1'] and r['equations'] == 11
    held = ex.guess_linear_recurrence(tilings, holdout=4)
    assert held['holdout_ok'] and held['holdout_mismatches'] == [] and held['holdout_terms'] == 4
    wrong = ex.guess_linear_recurrence([1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 99, 144], max_order=2, holdout=2)
    assert not wrong['found'] or not wrong.get('holdout_ok', True)
    # transfer-matrix bound: 8 states, candidate of order 2 -> 10 consecutive terms of the difference must vanish
    proof = ex.check_linear_recurrence(tilings, [4, -1], order_bound=8)
    assert proof['holds_on_data'] and proof['terms_needed'] == 10 and proof['proof_by_finite_check']
    short = ex.check_linear_recurrence(tilings[:9], [4, -1], order_bound=8)
    assert short['holds_on_data'] and not short['proof_by_finite_check']
    bad = ex.check_linear_recurrence([1, 3, 11, 41, 152], [4, -1])
    assert bad['mismatches'] == [4] and not bad['holds_on_data']
    with pytest.raises(ValueError):
        ex.guess_linear_recurrence([1, 2, 3], holdout=3)
