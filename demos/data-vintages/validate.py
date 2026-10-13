"""Independent timestamp scans and exact integer answers for the synthetic task.

No Pandas, optimizer, model import or producer output is used to form answers.
The original input definitions are shared; metadata truth is not certified.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / 'raw' / 'data'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def instant(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(timezone.utc)


def independent_answers():
    queries, versions, outcomes, plan = [load(DATA / name) for name in
                                       ['queries.json', 'versions.json', 'outcomes.json', 'plan.json']]
    selected = []
    for query in queries:
        group = [(i, row) for i, row in enumerate(versions)
                 if (row['day'], row['sku']) == (query['day'], query['sku'])]
        if any(row['available_at'] is None for _, row in group):
            state, chosen = 'unknown_availability', None
        else:
            eligible = [(instant(row['available_at']), i) for i, row in group
                        if instant(row['available_at']) < instant(query['cutoff'])]
            latest = max((t for t, _ in eligible), default=None)
            winners = [i for t, i in eligible if t == latest]
            state, chosen = (('not_available', None) if not winners else
                             ('ambiguous_latest', None) if len(winners) > 1 else
                             ('matched', winners[0]))
        selected.append({'query_index': len(selected), 'status': state,
                         'matched_version_index': chosen})
    truth = {(row['day'], row['sku']): row['demand'] for row in outcomes}

    def loss(order, demand):
        return sum(plan['shortage_penalty'][sku] * max(demand[sku] - order[sku], 0)
                   + plan['overage_penalty'][sku] * max(order[sku] - demand[sku], 0)
                   for sku in ['A', 'B'])

    def allocate(forecast):
        # All 861 nonnegative integer pairs under qA+qB<=40, not HiGHS.
        capacity = plan['capacity_units_per_day']
        pairs = [(loss({'A': a, 'B': b}, forecast), a, b)
                 for a in range(capacity + 1) for b in range(capacity + 1 - a)]
        value = min(cost for cost, _, _ in pairs)
        winners = [{'A': a, 'B': b} for cost, a, b in pairs if cost == value]
        if len(winners) != 1:
            raise ValueError('Fixture unexpectedly has nonunique minimizers; check all winners')
        return winners[0], value

    forecasts = {}
    daily = []
    for day in sorted({q['day'] for q in queries}):
        indices = [i for i, q in enumerate(queries) if q['day'] == day]
        if any(selected[i]['status'] != 'matched' for i in indices):
            daily.append({'day': day, 'orders': None})
            continue
        forecast = {queries[i]['sku']: versions[selected[i]['matched_version_index']]['forecast']
                    for i in indices}
        forecasts[day] = forecast
        order, _ = allocate(forecast)
        daily.append({'day': day, 'orders': order})
    comparison = {}
    for condition in ['asof', 'baseline', 'final_snapshot']:
        rows, error_sum = [], 0
        for day in plan['common_evaluation_days']:
            if condition == 'asof':
                forecast = forecasts[day]
            elif condition == 'baseline':
                forecast = dict(plan['baseline_forecast'])
            else:
                forecast = {sku: max((row for row in versions if row['day'] == day and
                                     row['sku'] == sku and row['available_at'] is not None),
                                    key=lambda row: instant(row['available_at']))['forecast']
                            for sku in ['A', 'B']}
            order, value = allocate(forecast)
            actual = {sku: truth[day, sku] for sku in ['A', 'B']}
            error_sum += sum(abs(forecast[s] - actual[s]) for s in ['A', 'B'])
            rows.append({'day': day, 'forecast': forecast, 'orders': order,
                         'forecast_cost': value, 'realized_cost': loss(order, actual),
                         'demand': actual,
                         'shortage': {**{s: max(actual[s] - order[s], 0) for s in ['A', 'B']}, 'total': sum(max(actual[s] - order[s], 0) for s in ['A', 'B'])},
                         'overage': {**{s: max(order[s] - actual[s], 0) for s in ['A', 'B']}, 'total': sum(max(order[s] - actual[s], 0) for s in ['A', 'B'])}})
        comparison[condition] = {'days': rows, 'absolute_error_sum': error_sum,
                                 'mae': error_sum / (len(rows) * 2),
                                 **{key: sum(r[key]['total'] if isinstance(r[key], dict) else r[key] for r in rows)
                                    for key in ['realized_cost', 'shortage', 'overage']}}
    return selected, daily, comparison


def validate(results):
    selected, daily, comparison = independent_answers()
    checks = []

    def check(name, passed, evidence):
        checks.append({'name': name, 'passed': bool(passed), 'independent': True,
                       'method_family': 'stdlib timestamp scan and exact integer enumeration',
                       'evidence': evidence})

    actual = results.get('mapping', {}).get('mappings', [])
    keys = ['query_index', 'status', 'matched_version_index']
    mapped = [{k: row.get(k) for k in keys} for row in actual]
    check('independent version selection', mapped == selected,
          'All20 original queries compared with a separate per-key UTC scan; unknown, tie and future states retained.')
    expected_counts = {s: sum(row['status'] == s for row in selected)
                       for s in ['matched', 'not_available', 'unknown_availability', 'ambiguous_latest']}
    check('fixed query roster', results.get('mapping', {}).get('counts') == expected_counts
          and results.get('mapping', {}).get('query_rows') == len(selected)
          and results.get('query_coverage') == {'query_rows': len(selected), **expected_counts},
          f'Fixed20 queries, independently counted states={expected_counts}; no unresolved row deletion.')
    actual_daily = results.get('daily_actions', [])
    check('independent allocation and abstention',
          [{'day': row.get('day'), 'orders': row.get('orders')} for row in actual_daily] == daily
          and results.get('daily_actionable_days') == 8 and results.get('daily_decision_days') == 10
          and all(row.get('actionable') is (row.get('orders') is not None)
                  and row.get('status') == ('actionable' if row.get('orders') is not None else 'abstain')
                  for row in actual_daily),
          'All10 days preserved; eight supported orders independently minimize over all861 feasible integer pairs, two days unresolved.')
    for condition, expected in comparison.items():
        got = results.get('comparison', {}).get(condition, {})
        check(f'independent {condition} diagnostics',
              all(got.get(k) == v for k, v in expected.items())
              and got.get('target_count') == 16 and got.get('evaluation_days') == 8
              and got.get('eligible_at_cutoff_under_declared_metadata') is (condition != 'final_snapshot'),
              f'Original16 common targets/8days; exact totals MAE={expected["mae"]}, cost={expected["realized_cost"]}, shortage={expected["shortage"]}, overage={expected["overage"]}.')
    mutation = results.get('future_value_perturbation_check', {})
    expected_indices = selected
    expected_orders = {row['day']: row['orders'] for row in daily}
    check('future-value invariance',
          mutation.get('before_query_mappings') == expected_indices == mutation.get('after_query_mappings')
          and mutation.get('before_daily_orders') == expected_orders == mutation.get('after_daily_orders'),
          'Producer reruns mapping/order calculation after changing only post-cutoff payloads; both sides independently equal the declared-input scan/enumeration. Source inspection is also required.')
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    checks = validate(load(args.results))
    args.output.write_text(json.dumps(checks, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    if not all(row['passed'] for row in checks):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
