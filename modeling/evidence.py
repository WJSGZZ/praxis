"""Exact checking of one rational-expression witness, not a general theorem prover."""
import ast
from fractions import Fraction


def rational_witness(lhs, rhs, names, point, relation, bounds):
    """Check exact decimal literals and binary-rational sample coordinates.

    Only rational arithmetic and bounded integer powers are supported. Unsupported
    functions remain unverified. Box endpoints use their JSON decimal spellings;
    membership is checked exactly rather than assumed from a float comparison.
    """
    scope = dict(zip(names, map(Fraction.from_float, point)))
    if any(not Fraction(str(lo)) <= scope[name] <= Fraction(str(hi)) for name, (lo, hi) in zip(names, bounds)):
        return dict(status='unverified', method='exact_rational_witness', reason='The binary-rational sample is outside an exact decimal box endpoint')

    def evaluate(expression):
        tree = ast.parse(expression, mode='eval')
        if len(expression) > 4096 or len(list(ast.walk(tree))) > 512:
            raise ValueError('exact witness expression exceeds its budget')

        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                value = Fraction(ast.get_source_segment(expression, node).replace('_', ''))
            elif isinstance(node, ast.Name) and node.id in scope:
                value = scope[node.id]
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
            elif isinstance(node, ast.BinOp):
                a, b = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.Add): value = a + b
                elif isinstance(node.op, ast.Sub): value = a - b
                elif isinstance(node.op, ast.Mult): value = a * b
                elif isinstance(node.op, ast.Div): value = a / b
                elif isinstance(node.op, ast.Pow) and b.denominator == 1 and abs(b) <= 200:
                    if max(a.numerator.bit_length(), a.denominator.bit_length()) * abs(b) > 4096:
                        raise ValueError('exact witness power exceeds its budget')
                    value = a ** int(b)
                else: raise ValueError('exact witness supports rational arithmetic and bounded integer powers only')
            else:
                raise ValueError('exact witness does not support this expression')
            if max(value.numerator.bit_length(), value.denominator.bit_length()) > 4096:
                raise ValueError('exact witness fraction exceeds its budget')
            return value

        return visit(tree.body)

    try:
        difference = evaluate(lhs) - evaluate(rhs)
        violated = difference != 0 if relation == '==' else (difference > 0 if relation == '<=' else difference < 0)
        return dict(status='refuted' if violated else 'candidate_rejected', method='exact_rational_witness',
                    difference=str(difference), at=[str(scope[n]) for n in names],
                    scope='One exact point in the declared box; no universal positive conclusion.')
    except (ValueError, ZeroDivisionError, OverflowError, RecursionError) as exc:
        return dict(status='unverified', method='exact_rational_witness', reason=str(exc))
