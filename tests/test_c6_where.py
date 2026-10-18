"""C6: one rule for invalid values inside restricted expressions and where().

Rule: log, sqrt, exp, sin, cos, tan, division and power must give finite real
values at every evaluated point. where() evaluates both branches, so an invalid
value in the unselected branch is an error, as it already was for power.
"""
import math

import numpy as np
import pytest

from scripts import mcp_server as server

X = np.array([[-1.], [0.], [4.]])


@pytest.mark.parametrize('expression, operation', [
    ('where(x>0, log(x), 0)', 'log'),
    ('where(x>0, sqrt(x), 0)', 'sqrt'),
    ('where(x>0, 1/x, 0)', 'division'),
    ('where(x>=0, 1/x, -1)', 'division'),
    ('where(x>0, exp(1000*x), 0)', 'exp'),
    ('log(x)', 'log'),
    ('x/(x-x)', 'division'),
])
def test_invalid_value_in_any_branch_is_an_error_naming_the_operation(expression, operation):
    with pytest.raises(ValueError, match=operation):
        server._compile(expression, ['x'])(X)


def test_power_behaviour_is_unchanged():
    with pytest.raises(ValueError, match='Power'):
        server._compile('where(x>0, x**0.5, 0)', ['x'])(X)
    np.testing.assert_allclose(server._compile('where(x>0, where(x>0, x, 1)**0.5, 0)', ['x'])(X), [0, 0, 2])
    np.testing.assert_allclose(server._compile('x**2 + 2**x', ['x'])(X), [1.5, 1, 32])


def test_documented_safe_idiom_returns_exact_piecewise_values():
    np.testing.assert_allclose(server._compile('where(x>0, log(where(x>0, x, 1)), 0)', ['x'])(X), [0, 0, math.log(4)])
    np.testing.assert_allclose(server._compile('where(x>0, sqrt(where(x>0, x, 0)), 0)', ['x'])(X), [0, 0, 2])
    np.testing.assert_allclose(server._compile('where(x != 0, 1/where(x != 0, x, 1), 0)', ['x'])(X), [-1, 0, .25])
    assert server._scalar('where(x > 0, x, -x)', ['x'])([-3.]) == 3.


def test_valid_arithmetic_is_unchanged():
    np.testing.assert_allclose(server._compile('exp(x)/2 + log(abs(x)+1) - sqrt(x*x) + sin(x)*cos(x) + tan(x/8)', ['x'])(X),
                               np.exp(X[:, 0])/2 + np.log(np.abs(X[:, 0])+1) - np.abs(X[:, 0]) + np.sin(X[:, 0])*np.cos(X[:, 0]) + np.tan(X[:, 0]/8))
    np.testing.assert_allclose(server._compile('7/2 + minimum(x, 1) + maximum(x, 1)', ['x'])(X), [3.5, 4.5, 8.5])


def test_scalar_dead_branch_log_zero_is_an_error():
    with pytest.raises(ValueError, match='log'):
        server._scalar('where(x>0, x, log(0))', ['x'])([2.0])


@pytest.mark.parametrize('expression', [
    'x>0', '(x>0)*3 + (x<=0)*(-1)', 'where(x>0, x<1, 0)', 'where(x>0, 1, 0) + (x<0)',
    'where(x, 1, 0)', 'where(where(x>0, 1, 0), 1, 0)', 'where((x>0) > 0, 1, 0)', 'where',
    'where(x<0<2, 1, 0)', 'where(x>0 and x<1, 1, 0)', 'where(x>0, 1)', 'where(True, 1, 0)',
    'x.real', '(1).__class__', 'x**x**2', 'where(x>0, x**2, 0)**2', 'np.where(x<0, 1, 0)',
    'where(x>0, x**201, 0)', 'exp', 'log(x, 2)',
])
def test_rejected_syntax(expression):
    with pytest.raises(ValueError):
        server._compile(expression, ['x'])


def test_comparison_messages_name_the_actual_rule():
    with pytest.raises(ValueError, match='only as the first argument of where'):
        server._compile('x>0', ['x'])
    with pytest.raises(ValueError, match='condition must be one comparison'):
        server._compile('where(x, 1, 0)', ['x'])


def test_accepted_conditions():
    np.testing.assert_allclose(server._compile('where(1 < 2, x, 0)', ['x'])(X), [-1, 0, 4])
    np.testing.assert_allclose(server._compile('where(where(x>0, x, 0) >= 4, 1, 0)', ['x'])(X), [0, 0, 1])
    np.testing.assert_allclose(server._compile('where(x == 0, 5, where(x < 0, -5, x))', ['x'])(X), [-5, 5, 4])


def test_internal_helper_names_cannot_be_declared_variables():
    for name in ['__praxis_checked_divide__', '__praxis_bounded_power__', 'where']:
        with pytest.raises(ValueError):
            server._compile('1', [name])


def test_external_route_reports_the_rule_through_the_deadline_worker():
    arguments = dict(expression='where(x>0, log(x), 0)', distributions={'x': dict(dist='uniform', params=dict(loc=-1, scale=2))}, n=64)
    with pytest.raises(Exception, match='log'):
        server.bounded_call('monte_carlo', arguments)
    safe = dict(arguments, expression='where(x>0, log(where(x>0, x, 1)), 0)')
    assert server.bounded_call('monte_carlo', safe)['mean'] <= 0


@pytest.mark.parametrize('tool, base', [
    ('minimize_nlp', dict(objective='x**2', names=['x'], bounds=[[-1, 1]], starts=2)),
    ('epsilon_constraint_nlp', dict(objectives=['x', '(x-1)**2'], names=['x'], senses=[-1, -1], epsilon_grid=[[1]], bounds=[[0, 1]], starts=2)),
])
@pytest.mark.parametrize('constraint', [dict(type='ineq'), dict(expression='x', type='bad'), dict(expression='x', kind='ineq'), dict(expression=1)])
def test_nlp_constraint_objects_are_validated_before_use(tool, base, constraint):
    with pytest.raises(ValueError) as error:
        server.call(tool, dict(base, constraints=[constraint]))
    assert not isinstance(error.value, KeyError)


def test_sobol_rejects_nonfinite_final_arithmetic_output():
    with pytest.raises(ValueError, match='finite'):
        server.call('sobol_sensitivity', dict(expression='x*x+y', names=['x', 'y'],
                    bounds=[[1e200, 1e201], [0, 1]], n=64))
