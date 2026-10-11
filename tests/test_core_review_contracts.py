"""Independent witnesses and JSON/worker boundaries from the S02 core review."""
import json
import sys
import time
from fractions import Fraction
from pathlib import Path

import mpmath as mp
import numpy as np
import pytest

from modeling import calibrate, regression, structure, experiment, decision_models
from scripts import mcp_server as server
from scripts.bounded_execution import run_with_deadline

ROOT = Path(__file__).resolve().parents[1]


def conjecture(lhs, rhs, relation='==', **extra):
    return server.call('test_conjecture', dict(lhs=lhs, rhs=rhs, relation=relation, names=['x'], bounds=[[0, 1]], points=20, **extra))


def test_catastrophic_cancellation_is_not_a_mathematical_refutation():
    r = conjecture('(x+10000000000000000)-10000000000000000', 'x')
    assert not r['numerical_holds'] and not r['proved'] and r['claim_status'] == 'unresolved'
    assert r['verification']['status'] == 'candidate_rejected'
    x = Fraction.from_float(r['at'][0])
    assert (x + 10**16) - 10**16 == x  # independent exact identity at the actual witness


def test_real_rational_counterexample_has_exact_evidence():
    r = conjecture('x**2', 'x', '>=')
    assert r['proved'] and r['claim_status'] == 'refuted'
    x = Fraction(r['verification']['at'][0])
    assert 0 < x < 1 and x*x < x
    assert Fraction(r['verification']['difference']) == x*x-x


def test_decimal_rounding_and_unsupported_function_are_not_proofs():
    r = conjecture('0.1+0.2', '0.3', tolerance=0)
    assert not r['proved'] and r['verification']['difference'] == '0'
    r = conjecture('sin(x)', '0')
    assert not r['proved'] and r['verification']['status'] == 'unverified'


def test_exact_witness_must_be_inside_exact_decimal_box():
    from modeling.evidence import rational_witness
    # The binary float spelling of 0.1 is greater than exact 1/10. It cannot
    # refute a statement on the singleton decimal box by claiming membership.
    r = rational_witness('x', '0', ['x'], [.1], '==', [[.1,.1]])
    assert r['status']=='unverified' and 'outside' in r['reason']


def test_high_precision_rounding_remains_a_candidate():
    r = experiment.test_conjecture(lambda x: (x+mp.mpf(10)**30)-mp.mpf(10)**30, lambda x:x,
                                   '==', [[0, 1]], points=4, dps=15)
    assert not r['holds'] and not r['proved'] and r['evidence'] == 'numerical_candidate'


def test_all_numerical_structure_violations_need_certification():
    results = [structure.check_convexity(lambda x: -x[0]**2, [[-1, 1]], trials=20),
               structure.check_monotone(lambda x: x[0]**2, [[-1, 1]], 0, trials=100),
               structure.check_symmetry(lambda x:x[0]-x[1], [[0, 1], [0, 1]], [1, 0], trials=20),
               structure.check_power_law(lambda x:x[0]+x[1], [[1, 3], [1, 3]], trials=20),
               structure.check_invariant(lambda x:np.array([1.]), lambda x:x[0], [[0, 1]], trials=20)]
    assert all(not r['proved'] and r['evidence'] == 'numerical_candidate' for r in results)
    w = results[1]['direction_witnesses']
    assert w['against_nondecreasing']['change'] < 0 < w['against_nonincreasing']['change']
    # Exact combinatorial certification is retained, rather than clearing all proved flags.
    assert structure.is_network_matrix([[1], [-1]])['proved']


def test_noiseless_calibration_delivers_estimates_and_reasoned_diagnostics():
    r = server.call('calibrate_curve', dict(expression='a*x+b', parameters=['a', 'b'],
                                          x=[0, 1, 2, 3], y=[1, 3, 5, 7], theta0=[2, 1]))
    assert [p['estimate'] for p in r['parameters']] == [2, 1] and r['rmse'] == 0 and r['converged']
    assert r['max_parameter_correlation'] is None
    assert r['diagnostics']['max_parameter_correlation']['status'] == 'undefined'
    assert r['diagnostics']['max_parameter_correlation']['reason']
    json.dumps(r, allow_nan=False)


def test_rank_deficient_calibration_keeps_fit_but_not_individual_intervals():
    r = calibrate.calibrate(lambda t,x:(t[0]+t[1])*x, [0,1,2,3], [0,6,12,18], [3,3])
    assert r['rmse'] == pytest.approx(0) and r['jacobian_rank'] == 1
    assert all(p['ci_low'] is None and p['inference']['status']=='not_reported_rank_deficient' for p in r['parameters'])
    json.dumps(r, allow_nan=False)


def test_failed_fit_is_not_washed_into_convergence(monkeypatch):
    original = calibrate.least_squares
    def failed(*a, **k):
        r = original(*a, **k)
        r.success = False
        return r
    monkeypatch.setattr(calibrate, 'least_squares', failed)
    r = calibrate.calibrate(lambda t,x:t[0]*x, [0,1,2,3], [0,2,4,6], [2])
    assert not r['converged'] and r['fit_status']=='failed' and r['parameters'][0]['std_error'] is None
    assert r['parameters'][0]['inference']['status']=='fit_failed'
    json.dumps(r, allow_nan=False)


@pytest.mark.parametrize('X,y', [([[i,i] for i in range(10)], [2*i+(-1)**i*.1 for i in range(10)]),
                                   ([[i,0] for i in range(10)], [i for i in range(10)]),
                                   ([[0] for _ in range(10)], [0]*10)])
def test_singular_and_zero_response_regression_is_strict_json(X,y):
    r = regression.ols_report(X,y)
    json.dumps(r, allow_nan=False)
    assert r['design_rank'] < r['parameters']
    assert all(c['inference']['status']=='not_reported_rank_deficient' for c in r['coefficients'])
    assert any(v['status'] in ('unbounded','undefined') for v in r['diagnostics']['vif_status'].values())
    if all(v==0 for v in y):
        assert r['r2'] is None and r['diagnostics']['status']['r2']['reason']


def test_degenerate_nash_count_is_not_a_total_equilibrium_count():
    A = B = np.zeros((2,2))
    r = decision_models.bimatrix_nash(A,B)
    assert r['count']==4 and r['completeness']['status']=='not_certified'
    x,y = np.array([.25,.75]), np.array([.6,.4])
    assert (A@y == x@A@y).all() and (x@B == x@B@y).all()
    assert not any(np.allclose(e['row'],x) and np.allclose(e['column'],y) for e in r['equilibria'])


def test_finite_enumeration_does_not_certify_a_rounded_predicate():
    r = server.call('find_counterexample', dict(claim='0.1+0.2>0.3', names=['n'], domain=[['int',0,3]]))
    assert r['exhaustive'] and not r['found'] and not r['proved_for_domain']
    assert Fraction(1,10)+Fraction(2,10)==Fraction(3,10)
    exact = server.call('find_counterexample', dict(claim='n*n>=0', names=['n'], domain=[['int',-3,3]]))
    assert exact['proved_for_domain'] and exact['evaluation_method']=='exact_integer_predicate'


@pytest.mark.parametrize('claim', ['n**(-1)>0', 'n**n>0'])
def test_negative_or_variable_integer_powers_do_not_inherit_exact_predicate_proof(claim):
    r=server.call('find_counterexample',dict(claim=claim,names=['n'],domain=[['int',1,3]]))
    assert not r['proved_for_domain'] and r['evaluation_method']=='numerical_predicate'


def test_ordinary_nash_independent_best_responses_are_unchanged():
    r = decision_models.bimatrix_nash([[1,-1],[-1,1]],[[-1,1],[1,-1]])
    assert r['count']==1
    assert r['equilibria'][0]['row']==pytest.approx([.5,.5])
    assert r['equilibria'][0]['column']==pytest.approx([.5,.5])


@pytest.mark.parametrize('expression', ['2**202', '2**(201+1)', '2**(-202)', '2**(101*2)'])
def test_every_expression_entry_rejects_equivalent_large_exponents(expression):
    with pytest.raises(ValueError): server._compile(expression,['x'])
    with pytest.raises(ValueError): server._predicate(expression+'>0',['x'])
    with pytest.raises(ValueError): experiment._safe_eval(expression,{'x':1})


@pytest.mark.parametrize('value', ['nan','inf','1e100000', '1'*4097])
def test_relation_numeric_shortcut_does_not_bypass_limits(value):
    with pytest.raises(ValueError): experiment.find_relation(value,{'one':'1'})


def test_private_power_name_cannot_be_supplied_by_client():
    with pytest.raises(ValueError): server._compile('__praxis_bounded_power__',['__praxis_bounded_power__'])


def test_real_subprocess_deadline_kills_controlled_wait():
    started=time.monotonic()
    with pytest.raises(TimeoutError,match='no result accepted'):
        run_with_deadline([sys.executable,'-c','import time; time.sleep(5)'], '', cwd=ROOT,timeout=.05)
    assert time.monotonic()-started < 3


def test_mcp_timeout_and_bad_expression_leave_service_usable(monkeypatch):
    monkeypatch.setattr(server,'EXPRESSION_TIMEOUT_SECONDS',.001)
    r=server.handle({'id':1,'method':'tools/call','params':{'name':'test_conjecture','arguments':dict(lhs='x',rhs='x',names=['x'],relation='==',bounds=[[0,1]],points=1)}})
    assert r['result']['isError'] and 'TimeoutError' in r['result']['content'][0]['text']
    assert server.handle({'id':2,'method':'ping'})['result']=={}
