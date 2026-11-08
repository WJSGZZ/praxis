"""Scope a proof claim. Exact checks here concern only the declared polynomial relation."""
from fractions import Fraction
import re


def _rational(value):
    if type(value) is int and value.bit_length() <= 256:
        return Fraction(value)
    if isinstance(value, str) and len(value) <= 80 and re.fullmatch(r'-?[0-9]+(?:/[1-9][0-9]*|\.[0-9]+)?', value):
        return Fraction(value)
    raise ValueError('Use a bounded integer or exact rational string such as "1/3" or "0.25".')


def _formal_check(record):
    method = record.get('method')
    if method not in ('enumeration', 'witness', 'quadratic_extrema'):
        raise ValueError('Unrecognized proof method.')
    required = {'method', 'quantifier', 'domain', 'interval', 'coefficients'}
    if method == 'witness':
        required.add('point')
    if set(record) != required:
        raise ValueError(f'Expected precisely these fields for {method}: {sorted(required)}.')
    quantifier, domain = record['quantifier'], record['domain']
    if quantifier not in ('forall', 'exists') or domain not in ('integer_interval', 'real_interval'):
        raise ValueError('Declare forall or exists over an integer_interval or real_interval.')
    if not isinstance(record['interval'], list) or len(record['interval']) != 2:
        raise ValueError('The domain must have two inclusive interval endpoints.')
    lo, hi = map(_rational, record['interval'])
    if lo > hi or domain == 'integer_interval' and (lo.denominator != 1 or hi.denominator != 1):
        raise ValueError('Expected ordered endpoints, integral for an integer interval.')
    raw = record['coefficients']
    if not isinstance(raw, list) or not 1 <= len(raw) <= 13:
        raise ValueError('Give 1 to 13 coefficients, constant first, for p(x) >= 0.')
    coefficients = list(map(_rational, raw))
    while len(coefficients) > 1 and coefficients[-1] == 0:
        coefficients.pop()

    if method == 'witness':
        point = _rational(record['point'])
        if not lo <= point <= hi or domain == 'integer_interval' and point.denominator != 1:
            raise ValueError('Witness outside the declared domain.')
        points = [point]
    elif method == 'enumeration':
        if domain != 'integer_interval' or hi - lo >= 128:
            raise ValueError('Enumeration covers only integer intervals of at most 128 points.')
        points = range(int(lo), int(hi) + 1)
    else:
        if domain != 'real_interval' or len(coefficients) > 3:
            raise ValueError('Quadratic extrema cover real intervals and degree at most two.')
        points = [lo] if lo == hi else [lo, hi]
        if len(coefficients) == 3:
            vertex = -coefficients[1] / (2 * coefficients[2])
            if lo < vertex < hi:
                points.append(vertex)

    result = dict(relation='p(x) >= 0', method=method, quantifier=quantifier, domain=domain,
                  interval=[str(lo), str(hi)], coefficients=[str(v) for v in coefficients],
                  scope='The formal relation on this domain only. Check that it is the statement and premises of the paper.')
    evaluated = []
    for point in points:
        value = Fraction(0)
        for coefficient in reversed(coefficients):
            value = value * point + coefficient
        row = {'point': str(point), 'value': str(value)}
        evaluated.append(row)
        if (quantifier == 'forall' and value < 0) or (quantifier == 'exists' and value >= 0):
            return dict(result, status='formal_refutation' if value < 0 else 'formal_support',
                        checked=evaluated, reason='An exact witness decides the declared quantifier.')
    if method == 'witness':
        if lo == hi:
            return dict(result, status='formal_support' if quantifier == 'forall' else 'formal_refutation',
                        checked=evaluated, reason='The point is the entire singleton domain.')
        return dict(result, status='open', checked=evaluated, reason='The point does not decide this quantifier.')
    reason = ('All integer points were checked.' if method == 'enumeration' else
              'A polynomial of degree at most two attains its extrema at an endpoint or its interior stationary point.')
    return dict(result, status='formal_support' if quantifier == 'forall' else 'formal_refutation',
                checked=evaluated, reason=reason)


def review(record):
    """Never convert independence, a proof reference, or free prose into theorem certification."""
    if record is None:
        return {'status': 'open', 'reason': 'No proof obligation recorded. Linked checks alone do not establish its scope.'}
    if not isinstance(record, dict):
        return {'status': 'open', 'reason': 'Expected a proof_obligation object.'}
    if record.get('method') == 'derivation':
        fields = ('statement', 'domain', 'argument')
        if all(isinstance(record.get(key), str) and record[key].strip() for key in fields):
            return {'status': 'needs_mathematical_review', 'reason': 'Check each implication, hypothesis and boundary case in the stated derivation.'}
        return {'status': 'open', 'reason': 'A derivation needs a statement with its hypotheses, domain and argument.'}
    try:
        asserted_truth = record.get('asserted_truth', True)
        if type(asserted_truth) is not bool:
            raise ValueError('asserted_truth must be a Boolean.')
        result = _formal_check({k: v for k, v in record.items() if k != 'asserted_truth'})
        truth = {'formal_support': True, 'formal_refutation': False}.get(result['status'])
        result['asserted_truth'] = asserted_truth
        result['agrees_with_assertion'] = None if truth is None else truth == asserted_truth
        return result
    except ValueError as error:
        return {'status': 'open', 'reason': str(error)}


def main():
    """Check the same obligation without creating a numerical modeling case."""
    import argparse
    import json
    from pathlib import Path
    from modeling.schema_contracts import unique_object_pairs

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path, help='UTF-8 JSON proof obligation')
    args = parser.parse_args()
    try:
        record = json.loads(args.record.read_text(encoding='utf-8'), object_pairs_hook=unique_object_pairs)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'{exc}\n')
    print(json.dumps(review(record), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
