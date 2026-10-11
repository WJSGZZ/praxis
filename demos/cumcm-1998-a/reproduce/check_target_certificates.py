"""Check return targets with exact original fees and independent rational bounds.

For c=1+p and g=r-s-(1+s)p, every original-fee portfolio satisfies
P/M <= s + lambda + R*sum(max(g-lambda*c, 0)/q), lambda >= 0.
A feasible portfolio attaining the corresponding risk lower bound is optimal.
This checker imports neither the numerical model nor an optimization library.
Amounts are continuous; these certificates do not certify rounded orders or markets.
"""
import argparse
import csv
import hashlib
import itertools
import json
from fractions import Fraction
from pathlib import Path
from typing import NamedTuple


BANK = Fraction(1, 20)
ROOT = Path(__file__).resolve().parent
FILES = {'four': 'assets4.csv', 'fifteen': 'assets15.csv'}
TARGETS = {'four': ('1/5', '11/50', '1/4'),
           'fifteen': ('3/10', '33/100', '19/50')}


class Asset(NamedTuple):
    name: str
    r: Fraction
    q: Fraction
    p: Fraction
    u: Fraction


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rational(value):
    """Decimal strings, integers and fractions only; never silently accept NaN."""
    require(not isinstance(value, (bool, float)), 'Exact finite rational input required')
    try:
        return Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as error:
        raise ValueError('Exact finite rational input required') from error


def read_assets(path):
    columns = {'asset', 'return_pct', 'risk_pct', 'fee_pct', 'threshold_yuan'}
    with Path(path).open(encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        require(set(reader.fieldnames or ()) == columns, 'Invalid asset CSV columns')
        assets = [Asset(row['asset'], rational(row['return_pct']) / 100,
                        rational(row['risk_pct']) / 100, rational(row['fee_pct']) / 100,
                        rational(row['threshold_yuan'])) for row in reader]
    require(assets and len({a.name for a in assets}) == len(assets),
            'Nonempty distinct asset names required')
    require(all(a.name and a.q > 0 and a.p >= 0 and a.u >= 0 for a in assets),
            'Positive risk and nonnegative fee/threshold required')
    return assets


def dual_coefficient(assets, lam):
    lam = rational(lam)
    require(lam >= 0, 'Nonnegative dual lambda required')
    return sum((max(a.r - BANK - (1 + BANK) * a.p - lam * (1 + a.p), 0) / a.q
                for a in assets), Fraction(0))


def portfolio_values(assets, budget, record):
    """Recompute values before deciding exact or tolerance-qualified feasibility."""
    budget = rational(budget)
    require(budget > 0, 'Positive budget required')
    raw = record['investments_yuan']
    if isinstance(raw, list):
        require(len(raw) == len(assets), 'Wrong investment count')
        raw = dict(zip((a.name for a in assets), raw))
    require(isinstance(raw, dict) and set(raw) == {a.name for a in assets},
            'Every asset purchase must be explicit')
    x = {name: rational(value) for name, value in raw.items()}
    bank = rational(record['bank_yuan'])
    require(all(value >= 0 for value in x.values()), 'Nonnegative purchases required')
    fees = {a.name: a.p * max(x[a.name], a.u) if x[a.name] > 0 else Fraction(0)
            for a in assets}
    spent = bank + sum(x.values()) + sum(fees.values())
    profit = BANK * bank + sum(a.r * x[a.name] for a in assets) - sum(fees.values())
    risk = max(a.q * x[a.name] for a in assets) / budget
    return {'investments_yuan': x, 'fees_yuan': fees, 'bank_yuan': bank,
            'budget_residual_yuan': spent - budget, 'profit_yuan': profit,
            'net_return': profit / budget, 'risk_rate': risk}


def exact_feasible(assets, budget, target, record):
    values = portfolio_values(assets, budget, record)
    require(values['bank_yuan'] >= 0 and values['budget_residual_yuan'] == 0,
            'Original-fee budget/nonnegativity certificate fails')
    require(values['net_return'] >= rational(target), 'Return target certificate fails')
    return values


def verify_minimum(assets, record):
    budget, target = rational(record['budget_yuan']), rational(record['target_net_return'])
    lam, risk = rational(record['lambda']), rational(record['minimum_risk'])
    coefficient = dual_coefficient(assets, lam)
    require(coefficient > 0 and target > BANK + lam, 'Positive risk lower bound required')
    require(coefficient == rational(record['A']), 'Dual coefficient certificate fails')
    lower = (target - BANK - lam) / coefficient
    values = exact_feasible(assets, budget, target, record)
    require(risk == lower == values['risk_rate'],
            'Feasible risk does not attain the independent lower bound')
    require(all(values['investments_yuan'][a.name] == 0 or a.p == 0 or
                values['investments_yuan'][a.name] >= a.u for a in assets),
            'Proportional-fee equality is outside the original fee regime')
    critical = max((budget * a.u / values['investments_yuan'][a.name]
                    for a in assets if a.p > 0 and values['investments_yuan'][a.name] > 0),
                   default=Fraction(0))
    if critical > 0:
        boundary = {'investments_yuan': {k: v * critical / budget
                                        for k, v in values['investments_yuan'].items()},
                    'bank_yuan': values['bank_yuan'] * critical / budget}
        at_boundary = exact_feasible(assets, critical, target, boundary)
        require(at_boundary['risk_rate'] == risk, 'Funding boundary certificate fails')
    return {'status': 'original_fee_exact_minimum', 'budget_yuan': budget,
            'target_net_return': target, 'minimum_risk': lower,
            'dual': {'lambda': lam, 'A': coefficient}, 'portfolio': values,
            'funding_threshold_yuan': critical, 'funding_boundary_checked': critical > 0}


def verify_maximum(assets, record):
    upper = max(BANK, max((a.r - a.p) / (1 + a.p) for a in assets))
    lam = rational(record['lambda'])
    require(dual_coefficient(assets, lam) == 0 and BANK + lam == upper,
            'Global return upper-bound certificate fails')
    require(rational(record['maximum_return']) == upper, 'Maximum return mismatch')
    values = exact_feasible(assets, record['budget_yuan'], upper, record)
    require(values['net_return'] == upper, 'Global upper bound is not attained')
    return {'budget_yuan': rational(record['budget_yuan']),
            'maximum_return': upper, 'lambda': lam, 'A': Fraction(0),
            'original_fee_attainment': values}


def fixed_fee_support_bounds(assets, budget, risk):
    """Exact upper bounds for every support while all risk caps are below u.

    In each support, allowing zero purchases while still charging its fixed fees
    is optimistic for maximizing its linear objective. Enumerating all supports
    covers every real portfolio. Greedy purchase by r-s solves each such bound.
    """
    budget, risk = rational(budget), rational(risk)
    require(budget > 0 and risk >= 0 and len(assets) <= 8,
            'Positive budget, nonnegative risk and at most eight assets required')
    caps = {a.name: budget * risk / a.q for a in assets}
    require(all(caps[a.name] <= a.u for a in assets), 'Fixed-fee cap regime required')
    rows = []
    for mask in itertools.product((False, True), repeat=len(assets)):
        active = [a for a, used in zip(assets, mask) if used]
        fixed = sum((a.p * a.u for a in active), Fraction(0))
        cash = budget - fixed
        if cash < 0:
            rows.append({'support': [a.name for a in active], 'fixed_fees_yuan': fixed,
                         'profit_upper_bound_yuan': None})
            continue
        x = {a.name: Fraction(0) for a in assets}
        for a in sorted(active, key=lambda a: a.r - BANK, reverse=True):
            if a.r > BANK:
                x[a.name] = min(cash, caps[a.name])
                cash -= x[a.name]
        profit = BANK * cash + sum(a.r * x[a.name] for a in assets) - fixed
        rows.append({'support': [a.name for a in active], 'fixed_fees_yuan': fixed,
                     'profit_upper_bound_yuan': profit, 'investments_yuan': x,
                     'bank_yuan': cash,
                     'support_attained': all(x[a.name] > 0 for a in active)})
    return rows


def verify_small_budget(assets, record):
    budget, target = rational(record['budget_yuan']), rational(record['target_net_return'])
    risk, lam = rational(record['relaxed_risk']), rational(record['lambda'])
    require(budget == 100 and target == Fraction(1, 5) and len(assets) == 4,
            'Expected the four-asset 100-yuan counterexample')
    coefficient = dual_coefficient(assets, lam)
    require(coefficient > 0 and risk == (target - BANK - lam) / coefficient,
            'Relaxation lower-bound certificate fails')
    rows = fixed_fee_support_bounds(assets, budget, risk)
    best = max((r for r in rows if r['profit_upper_bound_yuan'] is not None),
               key=lambda r: r['profit_upper_bound_yuan'])
    require(best['support_attained'], 'Best support bound has no attainment certificate')
    attained = exact_feasible(assets, budget, best['profit_upper_bound_yuan'] / budget, best)
    maximum = attained['profit_yuan']
    require(maximum == best['profit_upper_bound_yuan'] ==
            rational(record['maximum_profit_at_relaxed_risk_yuan']),
            'Fixed-fee support maximum certificate fails')
    require(maximum < budget * target, 'Counterexample does not exclude the target')
    examples = [exact_feasible(assets, budget, target, record[k])
                for k in ('feasible_only', 'strictly_better_feasible')]
    for values, key in zip(examples, ('feasible_only', 'strictly_better_feasible')):
        require(values['risk_rate'] == rational(record[key]['risk_rate']),
                'Feasible example risk mismatch')
    require(risk < examples[1]['risk_rate'] < examples[0]['risk_rate'],
            'Strictly better feasible example certificate fails')
    return {'budget_yuan': budget, 'target_net_return': target, 'relaxed_risk': risk,
            'support_count': len(rows), 'all_support_upper_bounds': rows,
            'maximum_profit_at_relaxed_risk_yuan': maximum,
            'strict_target_shortfall_yuan': budget * target - maximum,
            'no_feasible_portfolio_at_or_below_relaxed_risk': True,
            'feasible_only': {**examples[0], 'not_minimum_verified': True},
            'strictly_better_feasible': {**examples[1], 'minimum_verified': False},
            'exact_small_budget_minimum_claimed': False}


def verify_bundle(reference, data_root=ROOT):
    require(reference['format'] == 'cumcm-return-target-certificates-v1' and
            rational(reference['bank_rate']) == BANK and
            reference['risk_definition'] == 'max_i(q_i*x_i)/initial_budget' and
            reference['money_unit'] == 'yuan' and
            set(reference['groups']) == set(FILES), 'Invalid certificate bundle')
    groups, inputs, assets_by_group = {}, {}, {}
    for name, filename in FILES.items():
        group = reference['groups'][name]
        require(group['csv'] == 'data/' + filename, 'Unexpected asset CSV path')
        path = Path(data_root) / 'data' / filename
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest == group['csv_sha256'], 'Asset CSV hash mismatch')
        assets = read_assets(path)
        require(len(assets) == (4 if name == 'four' else 15), 'Wrong asset count')
        cases = group['cases']
        require(len(cases) == 3 and {rational(c['target_net_return']) for c in cases} ==
                {Fraction(t) for t in TARGETS[name]} and
                all(rational(c['budget_yuan']) == 1_000_000 for c in cases),
                'The six million-yuan target cases must be complete')
        checked = [verify_minimum(assets, c) for c in cases]
        maximum = verify_maximum(assets, group['maximum'])
        bank = []
        for target in (Fraction(0), Fraction(3, 100), BANK):
            values = exact_feasible(assets, 1_000_000, target,
                                    {'investments_yuan': {a.name: 0 for a in assets},
                                     'bank_yuan': 1_000_000})
            bank.append({'target_net_return': target, 'minimum_risk': values['risk_rate'],
                         'status': 'bank_only_exact_minimum'})
        above = [rational(t) for t in group['unreachable_targets']]
        require(above, 'Unreachable target examples required')
        above.append(maximum['maximum_return'] + Fraction(1, 1_000_000))
        require(all(t > maximum['maximum_return'] for t in above),
                'An unreachable target does not exceed the global bound')
        groups[name] = {'target_cases': checked, 'maximum': maximum, 'bank_boundaries': bank,
                        'unreachable_targets': [{'target_net_return': t, 'status': 'infeasible',
                                                 'evidence': 'strict global return upper bound'}
                                                for t in above]}
        inputs[name] = {'csv': group['csv'], 'sha256': digest}
        assets_by_group[name] = assets
    small = reference['small_budget_counterexample']
    require(small['group'] == 'four', 'Small-budget group must be four')
    return {'method': 'stdlib Fraction: original-fee primal, proportional dual, full fixed-fee support enumeration',
            'risk_definition': 'max_i(q_i*x_i)/initial_budget',
            'preference_source': 'illustrative input targets, not company preferences',
            'source_csv': inputs, 'groups': groups,
            'small_budget_counterexample': verify_small_budget(assets_by_group['four'], small)}, assets_by_group


def verify_numeric(result, assets_by_group, exact, tolerance=Fraction(1, 100_000_000)):
    """Check numerical values with a stated rate/relative-money tolerance.

    An arbitrary feasible solver output receives no optimality verdict. Exact
    optimality is borrowed only from an already checked same-budget/target bound.
    """
    require(set(result['groups']) <= set(FILES) and result['groups'], 'Invalid numerical groups')
    checked = []
    for name, rows in result['groups'].items():
        assets = assets_by_group[name]
        upper = exact['groups'][name]['maximum']['maximum_return']
        known = {(c['budget_yuan'], c['target_net_return']): c['minimum_risk']
                 for c in exact['groups'][name]['target_cases']}
        require(rows, 'Empty numerical group')
        seen = set()
        for row in rows:
            budget, target = rational(row['budget_yuan']), rational(row['target_net_return'])
            require(budget > 0 and (budget, target) not in seen, 'Invalid or duplicate numerical case')
            seen.add((budget, target))
            require(abs(rational(row['proportional_fee_return_upper_bound']) - upper) <= tolerance,
                    'Numerical global return bound mismatch')
            if row['status'] == 'infeasible':
                require(target > upper, 'No independent certificate for numerical infeasibility')
                checked.append({'group': name, 'budget_yuan': budget, 'target_net_return': target,
                                'status': 'infeasible_by_exact_global_bound'})
                continue
            require(row['status'] == 'optimal', 'Unsupported numerical solver status')
            values = portfolio_values(assets, budget, row)
            money_tolerance = budget * tolerance
            require(values['bank_yuan'] >= -money_tolerance and
                    abs(values['budget_residual_yuan']) <= money_tolerance,
                    'Numerical original-fee budget fails')
            require(len(row['fees_yuan']) == len(assets) and
                    all(abs(rational(f) - values['fees_yuan'][a.name]) <= money_tolerance
                        for a, f in zip(assets, row['fees_yuan'])), 'Numerical original fee mismatch')
            require(abs(rational(row['net_return']) - values['net_return']) <= tolerance and
                    values['net_return'] >= target - tolerance, 'Numerical return fails')
            risk = rational(row['minimum_risk'])
            require(abs(risk - values['risk_rate']) <= tolerance, 'Numerical risk mismatch')
            bound = Fraction(0) if target <= BANK else known.get((budget, target))
            if bound is not None:
                require(abs(risk - bound) <= tolerance, 'Numerical risk differs from exact minimum')
            checked.append({'group': name, 'budget_yuan': budget, 'target_net_return': target,
                            'status': 'matches_exact_minimum_with_tolerance' if bound is not None
                            else 'feasible_with_tolerance_optimality_unverified',
                            'exact_minimum_verified': bound is not None,
                            'rate_and_relative_money_tolerance': tolerance,
                            'recomputed_original_fee_values': values})
    return checked


def encode(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [encode(v) for v in value]
    return value


def read_json(path):
    def reject_constant(value):
        raise ValueError('Nonfinite JSON number: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      parse_float=Fraction, parse_constant=reject_constant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=ROOT / 'reference/target-certificates.json')
    parser.add_argument('--numeric', type=Path, help='Optional numerical return-targets.json to check')
    parser.add_argument('--output', type=Path, default=ROOT / 'reproduced/target-checks.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing to replace existing target checks')
    checked, assets = verify_bundle(read_json(args.reference))
    checked['certificate_sha256'] = hashlib.sha256(args.reference.read_bytes()).hexdigest()
    if args.numeric:
        checked['numerical_checks'] = verify_numeric(read_json(args.numeric), assets, checked)
        checked['numerical_source_sha256'] = hashlib.sha256(args.numeric.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(encode(checked), handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'exact_minimum_cases': 6, 'small_budget_supports': 16,
                      'numerical_cases': len(checked.get('numerical_checks', [])), 'passed': True}))


if __name__ == '__main__':
    main()
