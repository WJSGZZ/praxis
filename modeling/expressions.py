"""Shared size limits for restricted mathematical expressions.

These guards bound syntax, constant arithmetic and individual powers. They do
not establish a wall-clock deadline or make arbitrary functions cheap. Callers
must still check their syntax/name whitelist *before* compiling the transformed
tree and impose execution/input budgets where appropriate.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
import math
import operator

import mpmath as mp
import numpy as np


@dataclass(frozen=True)
class ExpressionLimits:
    max_chars: int = 4096
    max_nodes: int = 512
    max_depth: int = 64
    max_integer_bits: int = 4096
    max_abs_exponent: int = 200

    def __post_init__(self):
        for value in vars(self).values():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError('Expression limits must be positive integers')


DEFAULT_LIMITS = ExpressionLimits()
POWER_NAME = '__praxis_bounded_power__'
_UNKNOWN = object()
_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}


def _checked_constant(value, limits):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Only real numeric constants are allowed')
    if isinstance(value, int):
        if value.bit_length() > limits.max_integer_bits:
            raise ValueError(f'Integer constants/intermediates exceed {limits.max_integer_bits} bits')
    elif not math.isfinite(value):
        raise ValueError('Constants/intermediates must be finite real numbers')
    return value


def _checked_runtime(value, limits):
    """Reject unsupported/nonfinite scalars and numeric arrays before powering."""
    if isinstance(value, (bool, np.bool_)):
        raise ValueError('Power operands must be real numeric values, not booleans')
    if isinstance(value, (int, np.integer)):
        if int(value).bit_length() > limits.max_integer_bits:
            raise ValueError(f'Integer power operands/results exceed {limits.max_integer_bits} bits')
    elif isinstance(value, np.ndarray):
        if value.dtype.kind not in 'iuf' or not np.isfinite(value).all():
            raise ValueError('Power operands/results must be finite real numeric arrays')
    elif isinstance(value, mp.mpf):
        if not mp.isfinite(value):
            raise ValueError('Power operands/results must be finite real values')
    elif isinstance(value, (float, np.floating)):
        if not math.isfinite(value):
            raise ValueError('Power operands/results must be finite real values')
    else:
        raise ValueError('Power operands/results must be real numeric scalars or arrays')
    return value


def bounded_power(base, exponent, *, limits=DEFAULT_LIMITS):
    """Real finite power with bounded exponent and Python integer result size.

    Fractional exponents remain available; complex/nonfinite results are errors.
    This is an operand/result bound, not an execution timeout. NumPy arrays use
    floating arithmetic; exact integer overflow checks apply to Python int.
    """
    _checked_runtime(base, limits)
    _checked_runtime(exponent, limits)
    # Converting numeric arrays before abs also avoids the signed-minimum
    # integer overflow of np.abs(np.int64(-2**63)). Scalar mpmath comparisons
    # retain their precision instead of rounding a value just above the limit.
    magnitude = (np.abs(exponent.astype(float)) if isinstance(exponent, np.ndarray)
                 else abs(int(exponent)) if isinstance(exponent, (int, np.integer)) else abs(exponent))
    outside = np.any(magnitude > limits.max_abs_exponent)
    if outside:
        raise ValueError(f'Absolute exponents above {limits.max_abs_exponent} are not allowed')
    if isinstance(base, (int, np.integer)) and isinstance(exponent, (int, np.integer)):
        # Convert fixed-width scalars so integer powers cannot silently overflow.
        base, exponent = int(base), int(exponent)
        if exponent >= 0 and abs(base) > 1:
            lower_bits = (abs(base).bit_length() - 1) * exponent + 1
            if lower_bits > limits.max_integer_bits:
                raise ValueError(f'Integer power results exceed {limits.max_integer_bits} bits')
    if isinstance(base, np.ndarray):
        base = base.astype(float, copy=False)
    if isinstance(exponent, np.ndarray):
        exponent = exponent.astype(float, copy=False)
    try:
        with np.errstate(all='ignore'):
            result = base ** exponent
    except (ArithmeticError, TypeError, ValueError) as error:
        raise ValueError(f'Invalid real power: {error}') from error
    return _checked_runtime(result, limits)


def bounded_isprime(value):
    """Primality predicate on integer inputs of at most 64 bits.

    The argument limit bounds a known expensive predicate. It is not a timeout
    for arbitrary expressions or a proof about other user-defined callables.
    """
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError('isprime requires an integer argument')
    value = int(value)
    if value.bit_length() > 64:
        raise ValueError('isprime arguments must have at most 64 bits')
    import sympy
    return bool(sympy.isprime(value))


def parse_bounded_expression(expression, *, limits=DEFAULT_LIMITS):
    """Parse bounded syntax and inspect constant arithmetic without using eval.

    This does not authorize names, calls or syntax: callers retain the whitelist
    appropriate to numerical expressions, predicates or mpmath relations.
    """
    if not isinstance(expression, str):
        raise ValueError('Expression must be a string')
    if len(expression) > limits.max_chars:
        raise ValueError(f'Expression exceeds {limits.max_chars} characters')
    try:
        tree = ast.parse(expression, mode='eval')
    except (SyntaxError, RecursionError, ValueError) as error:
        raise ValueError(f'Invalid expression syntax: {error}') from error
    check_expression_tree(tree, limits=limits)
    return tree


def check_expression_tree(tree, *, limits=DEFAULT_LIMITS):
    """Check tree size, nested powers and all evaluable constant subexpressions."""
    if not isinstance(tree, ast.Expression):
        raise ValueError('Expected an expression AST')
    ordered = []
    stack = [(tree, 1, False)]
    while stack:
        node, depth, inside_power = stack.pop()
        ordered.append(node)
        if len(ordered) > limits.max_nodes:
            raise ValueError(f'Expression exceeds {limits.max_nodes} AST nodes')
        if depth > limits.max_depth:
            raise ValueError(f'Expression exceeds AST depth {limits.max_depth}')
        is_power = isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow)
        if is_power and inside_power:
            raise ValueError('A power inside a power is not allowed')
        if isinstance(node, ast.Constant):
            _checked_constant(node.value, limits)
        stack.extend((child, depth + 1, inside_power or is_power) for child in ast.iter_child_nodes(node))

    # Child-before-parent traversal. Names/functions stay unknown; only a small
    # arithmetic whitelist is evaluated, with checked operands at every step.
    values = {}
    for node in reversed(ordered):
        value = _UNKNOWN
        if isinstance(node, ast.Constant):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = values.get(node.operand, _UNKNOWN)
            if operand is not _UNKNOWN:
                value = operand if isinstance(node.op, ast.UAdd) else -operand
        elif isinstance(node, ast.BinOp):
            left, right = values.get(node.left, _UNKNOWN), values.get(node.right, _UNKNOWN)
            if isinstance(node.op, ast.Pow) and right is not _UNKNOWN:
                if abs(right) > limits.max_abs_exponent:
                    raise ValueError(f'Absolute exponents above {limits.max_abs_exponent} are not allowed')
            if left is not _UNKNOWN and right is not _UNKNOWN:
                try:
                    if isinstance(node.op, ast.Pow):
                        value = bounded_power(left, right, limits=limits)
                    elif type(node.op) in _BINARY:
                        # A multiplication allocates at most twice the permitted
                        # operand bits before the result check; no unbounded pow.
                        value = _BINARY[type(node.op)](left, right)
                except (ArithmeticError, TypeError) as error:
                    raise ValueError(f'Invalid constant arithmetic: {error}') from error
        if value is not _UNKNOWN:
            _checked_constant(value, limits)
        values[node] = value


def compile_bounded_expression(tree, *, filename='<expression>'):
    """Compile an already size-checked and syntax-whitelisted expression tree.

    Callers must include RUNTIME_FUNCTIONS in the eval scope, after user values,
    and reject POWER_NAME in their original name whitelist. The original tree is
    preserved. This function is not a substitute for either preceding check.
    """
    class Powers(ast.NodeTransformer):
        def visit_BinOp(self, node):
            node = self.generic_visit(node)
            if isinstance(node.op, ast.Pow):
                return ast.copy_location(ast.Call(func=ast.Name(id=POWER_NAME, ctx=ast.Load()),
                                                  args=[node.left, node.right], keywords=[]), node)
            return node
    transformed = ast.fix_missing_locations(Powers().visit(copy.deepcopy(tree)))
    return compile(transformed, filename, 'eval')


RUNTIME_FUNCTIONS = {POWER_NAME: bounded_power}
