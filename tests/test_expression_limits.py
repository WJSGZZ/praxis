"""Independent boundary examples for shared expression guards (no exhaustion)."""
import ast
import json
import math
from pathlib import Path
import subprocess
import sys

import mpmath as mp
import numpy as np
import pytest

from modeling.expressions import (DEFAULT_LIMITS, ExpressionLimits, POWER_NAME, RUNTIME_FUNCTIONS,
                                  bounded_isprime, bounded_power, compile_bounded_expression,
                                  parse_bounded_expression)


@pytest.mark.parametrize('expression', ['2**202', '2**(201+1)', '2**(-202)', '2**(101*2)',
                                       '2**(404/2)', '2**((400+4)//2)', '2**(+202)',
                                       'x**(201+1)', 'x**(-101*2)'])
def test_equivalent_constant_exponents_are_rejected(expression):
    with pytest.raises(ValueError, match='exponents above 200'):
        parse_bounded_expression(expression)


@pytest.mark.parametrize('expression', ['9**9**9', '(9**200)**200', 'x**(y**2)', '(x**2)**y',
                                       '2**abs(3**2)'])
def test_nested_powers_are_rejected_before_execution(expression):
    with pytest.raises(ValueError, match='power inside a power'):
        parse_bounded_expression(expression)


@pytest.mark.parametrize(('expression', 'scope', 'expected'), [
    ('2**(100+100)', {}, 2 ** 200), ('2**(-100-100)', {}, 2 ** -200),
    ('9**(1/2)', {}, 3.), ('x**2+2*x+1', {'x': 3.}, 16.),
    ('sin(x)**2+cos(x)**2', {'x': .73, 'sin': math.sin, 'cos': math.cos}, 1.),
    ('abs(-3)+min(2,4)+max(1,5)', {'abs': abs, 'min': min, 'max': max}, 10),
    ('gcd(54,24)+isprime(41)', {'gcd': math.gcd, 'isprime': bounded_isprime}, 7),
])
def test_normal_arithmetic_functions_and_exact_known_answers(expression, scope, expected):
    tree = parse_bounded_expression(expression)
    original = ast.dump(tree)
    result = eval(compile_bounded_expression(tree), {'__builtins__': {}}, {**scope, **RUNTIME_FUNCTIONS})
    assert result == pytest.approx(expected)
    assert ast.dump(tree) == original


def test_vector_and_high_precision_powers_preserve_inputs():
    tree = parse_bounded_expression('x**e')
    code = compile_bounded_expression(tree)
    result = eval(code, {'__builtins__': {}}, {'x': np.array([1., 4., 9.]), 'e': .5, **RUNTIME_FUNCTIONS})
    assert np.array_equal(result, [1., 2., 3.])
    with mp.workdps(60):
        actual = eval(code, {'__builtins__': {}}, {'x': mp.mpf(2), 'e': mp.mpf('.5'), **RUNTIME_FUNCTIONS})
        assert abs(actual * actual - 2) < mp.mpf('1e-58')


@pytest.mark.parametrize('exponent', [201, -201, 202., mp.mpf(202), np.array([2., 201.]),
                                     np.int64(-(2 ** 63)), np.array([-(2 ** 63)], dtype=np.int64)])
def test_variable_exponents_are_runtime_bounded(exponent):
    code = compile_bounded_expression(parse_bounded_expression('x**e'))
    with pytest.raises(ValueError, match='exponents above 200'):
        eval(code, {'__builtins__': {}}, {'x': 2, 'e': exponent, **RUNTIME_FUNCTIONS})


def test_character_node_depth_and_integer_limits_are_independent():
    with pytest.raises(ValueError, match='characters'):
        parse_bounded_expression('1' * (DEFAULT_LIMITS.max_chars + 1))
    with pytest.raises(ValueError, match='AST nodes'):
        parse_bounded_expression('x+x+x', limits=ExpressionLimits(max_nodes=5))
    with pytest.raises(ValueError, match='AST depth'):
        parse_bounded_expression('x+x+x+x', limits=ExpressionLimits(max_depth=3))
    small = ExpressionLimits(max_integer_bits=8)
    parse_bounded_expression('255', limits=small)
    for expression in ('256', '255+1', '128*2', '255*255', '2**8', 'x+(255+1)'):
        with pytest.raises(ValueError, match='bits'):
            parse_bounded_expression(expression, limits=small)
    assert bounded_power(2, 7, limits=small) == 128
    with pytest.raises(ValueError, match='bits'):
        bounded_power(2, 8, limits=small)


@pytest.mark.parametrize('expression', ['True', 'False', '1j', '1e999', '1e300*1e300',
                                       '2**(1/0)', 'x+(1/0)', '(-1)**.5', '"2"'])
def test_invalid_nonreal_nonfinite_or_boolean_constants_are_errors(expression):
    with pytest.raises(ValueError):
        parse_bounded_expression(expression)


@pytest.mark.parametrize(('base', 'exponent'), [(2, float('inf')), (2, float('nan')),
                                             (2, True), (True, 2), (-1, .5),
                                             (float('inf'), 0), (1e300, 2),
                                             (2, complex(1, 0)),
                                             (np.array([1., float('nan')]), 2)])
def test_runtime_power_rejects_nonfinite_nonreal_and_boolean_operands(base, exponent):
    with pytest.raises(ValueError):
        bounded_power(base, exponent)


def test_primality_input_has_an_exact_small_contract():
    assert bounded_isprime(41)
    assert not bounded_isprime(40) and not bounded_isprime(-41)
    assert not bounded_isprime(2 ** 64 - 1)  # 3 divides this exactly
    for value in (2 ** 64, 41., True, mp.mpf(41)):
        with pytest.raises(ValueError):
            bounded_isprime(value)


def test_high_precision_exponent_limit_and_integer_array_do_not_round_or_overflow():
    with mp.workdps(80):
        with pytest.raises(ValueError, match='exponents above 200'):
            bounded_power(mp.mpf(2), mp.mpf(200) + mp.mpf('1e-70'))
    assert bounded_power(np.array([2], dtype=np.int64), 64)[0] == float(2 ** 64)


def test_compile_helper_requires_original_name_whitelist():
    # The shared resource guard deliberately does not authorize any syntax/name.
    # The integration layer must reject this name before power transformation.
    tree = parse_bounded_expression(f'{POWER_NAME}(2,3)')
    assert any(isinstance(node, ast.Name) and node.id == POWER_NAME for node in ast.walk(tree))


def test_large_rejected_syntax_check_finishes_in_controlled_subprocess():
    source = '''import json
from modeling.expressions import parse_bounded_expression
checks = ['2**(201+1)', '2**(-202)', '2**(101*2)', '9**9**9', '1e999']
out = []
for expression in checks:
    try:
        parse_bounded_expression(expression)
        out.append(False)
    except ValueError:
        out.append(True)
print(json.dumps(out))
'''
    child = subprocess.run([sys.executable, '-c', source], cwd=Path(__file__).resolve().parents[1],
                           capture_output=True, text=True, timeout=10, check=True)
    assert json.loads(child.stdout) == [True] * 5


@pytest.mark.parametrize('limits', [{'max_chars': True}, {'max_nodes': 0}, {'max_depth': 2.5},
                                  {'max_integer_bits': -1}, {'max_abs_exponent': 0}])
def test_invalid_limit_configurations_fail_explicitly(limits):
    with pytest.raises(ValueError, match='positive integers'):
        ExpressionLimits(**limits)
