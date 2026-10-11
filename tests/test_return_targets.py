"""Exact independent answers and rejection boundaries for supplied return targets."""
import copy
import importlib.util
import json
import subprocess
import sys
from fractions import Fraction as F
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1] / 'demos/cumcm-1998-a/reproduce'
SCRIPT = ROOT / 'check_target_certificates.py'
SPEC = importlib.util.spec_from_file_location('target_certificates', SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def one_asset_certificate(budget='1000'):
    # g=.20-.05-1.05*.10=.045: A=.45, R=(.08-.05)/.45=1/15.
    return {'budget_yuan': budget, 'target_net_return': '2/25', 'lambda': '0',
            'A': '9/20', 'minimum_risk': '1/15',
            'investments_yuan': {'S1': str(F(budget) * F(2, 3))},
            'bank_yuan': str(F(budget) * F(4, 15))}


@pytest.fixture
def one_asset():
    return [checker.Asset('S1', F(1, 5), F(1, 10), F(1, 10), F(100))]


@pytest.fixture(scope='module')
def reference():
    return checker.read_json(ROOT / 'reference/target-certificates.json')


@pytest.fixture(scope='module')
def checked(reference):
    return checker.verify_bundle(reference)


def test_known_one_asset_bound_includes_bank_opportunity_cost(one_asset):
    result = checker.verify_minimum(one_asset, one_asset_certificate())
    assert result['minimum_risk'] == F(1, 15)
    assert result['portfolio']['profit_yuan'] == 80
    assert result['portfolio']['fees_yuan']['S1'] == F(200, 3)
    assert result['funding_threshold_yuan'] == 150
    bad = checker.Asset('bad', F(1, 25), F(1, 10), F(0), F(0))
    assert checker.dual_coefficient(one_asset + [bad], F(0)) == F(9, 20)


def test_small_capital_cannot_use_scaled_proportional_fee_answer(one_asset):
    actual = checker.exact_feasible(one_asset, 100, '2/25',
                                   {'investments_yuan': {'S1': 90}, 'bank_yuan': 0})
    assert actual['fees_yuan']['S1'] == 10 and actual['risk_rate'] == F(9, 100)
    with pytest.raises(ValueError, match='Original-fee budget'):
        checker.verify_minimum(one_asset, one_asset_certificate('100'))


def test_six_million_yuan_answers_and_bank_unreachable_boundaries(checked):
    result, _ = checked
    expected = {'four': [F(12870, 2190269), F(43, 4175), F(13, 668)],
                'fifteen': [F(2180078774640, 35018317294663),
                            F(7406225814, 81136277107), F(2514, 7187)]}
    for name, risks in expected.items():
        group = result['groups'][name]
        assert [c['minimum_risk'] for c in group['target_cases']] == risks
        assert all(c['portfolio']['budget_residual_yuan'] == 0 and
                   c['portfolio']['profit_yuan'] == c['target_net_return'] * 1_000_000
                   for c in group['target_cases'])
        assert all(c['minimum_risk'] == 0 for c in group['bank_boundaries'])
        assert all(c['target_net_return'] > group['maximum']['maximum_return']
                   for c in group['unreachable_targets'])
    assert result['groups']['four']['maximum']['maximum_return'] == F(27, 101)
    assert result['groups']['fifteen']['maximum']['maximum_return'] == F(217, 530)


def test_all_16_supports_exclude_small_budget_relaxation_and_beat_example(checked):
    result, _ = checked
    small = result['small_budget_counterexample']
    assert small['support_count'] == 16
    supports = {tuple(c['support']) for c in small['all_support_upper_bounds']}
    assert len(supports) == 16
    assert small['maximum_profit_at_relaxed_risk_yuan'] == F(57928792409, 4380538000)
    assert small['strict_target_shortfall_yuan'] == F(29681967591, 4380538000)
    old, better = small['feasible_only'], small['strictly_better_feasible']
    assert old['risk_rate'] == F(32163, 1840000)
    assert old['not_minimum_verified']
    assert better['risk_rate'] == F(611, 50000)
    assert better['profit_yuan'] == F(81843, 4000)
    assert better['fees_yuan']['S4'] == F(611, 200)
    assert small['relaxed_risk'] < better['risk_rate'] < old['risk_rate']
    assert not better['minimum_verified'] and not small['exact_small_budget_minimum_claimed']


def test_feasible_original_portfolio_is_not_an_optimality_certificate(reference, checked):
    _, assets = checked
    small = reference['small_budget_counterexample']
    wrong = {'budget_yuan': '100', 'target_net_return': '1/5', 'lambda': '0',
             'A': '2190269/85800', 'minimum_risk': small['feasible_only']['risk_rate'],
             **small['feasible_only']}
    with pytest.raises(ValueError, match='independent lower bound'):
        checker.verify_minimum(assets['four'], wrong)


@pytest.mark.parametrize('field,value', [('lambda', '-1'), ('A', '0'),
                                        ('minimum_risk', '1'), ('bank_yuan', '1')])
def test_corrupt_minimum_certificate_is_rejected(one_asset, field, value):
    record = one_asset_certificate()
    record[field] = value
    with pytest.raises(ValueError):
        checker.verify_minimum(one_asset, record)


@pytest.mark.parametrize('damage', ['csv', 'missing_case', 'purchase', 'maximum', 'small_maximum'])
def test_broken_public_certificate_bundle_is_rejected(reference, damage):
    record = copy.deepcopy(reference)
    if damage == 'csv':
        record['groups']['four']['csv_sha256'] = '0' * 64
    elif damage == 'missing_case':
        record['groups']['four']['cases'].pop()
    elif damage == 'purchase':
        record['groups']['four']['cases'][0]['investments_yuan']['S1'] = '1'
    elif damage == 'maximum':
        record['groups']['four']['maximum']['maximum_return'] = '1/2'
    else:
        record['small_budget_counterexample']['maximum_profit_at_relaxed_risk_yuan'] = '20'
    with pytest.raises(ValueError):
        checker.verify_bundle(record)


@pytest.mark.parametrize('row', ['S1,20,0,1,100', 'S1,20,5,-1,100',
                               'S1,20,5,1,-100', 'S1,NaN,5,1,100',
                               'S1,20,5,1,100\nS1,25,6,2,200'])
def test_invalid_asset_csv_is_rejected(tmp_path, row):
    path = tmp_path / 'assets.csv'
    path.write_text('asset,return_pct,risk_pct,fee_pct,threshold_yuan\n' + row + '\n')
    with pytest.raises(ValueError):
        checker.read_assets(path)


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '1/0', True, float('inf'), .2])
def test_exact_inputs_reject_nonfinite_and_implicit_float(value):
    with pytest.raises(ValueError, match='finite rational'):
        checker.rational(value)


def test_invalid_budget_and_nonfinite_json_are_rejected(tmp_path, one_asset):
    with pytest.raises(ValueError, match='Positive budget'):
        checker.verify_minimum(one_asset, one_asset_certificate('0'))
    path = tmp_path / 'invalid.json'
    path.write_text('{"minimum_risk": NaN}')
    with pytest.raises(ValueError, match='Nonfinite JSON'):
        checker.read_json(path)


def numeric_example(budget=1000):
    if budget == 1000:
        x, fee, bank, risk = 2000 / 3, 200 / 3, 800 / 3, 1 / 15
    else:
        x, fee, bank, risk = 90., 10., 0., .09
    row = {'budget_yuan': budget, 'target_net_return': .08,
           'proportional_fee_return_upper_bound': 1 / 11, 'status': 'optimal',
           'investments_yuan': [x], 'fees_yuan': [fee], 'bank_yuan': bank,
           'net_return': .08, 'minimum_risk': risk}
    # Match the CLI's decimal-to-Fraction JSON parsing rather than binary float exactness.
    return json.loads(json.dumps({'groups': {'four': [row]}}), parse_float=F)


def exact_one_asset_answers():
    return {'groups': {'four': {'maximum': {'maximum_return': F(1, 11)},
                               'target_cases': [{'budget_yuan': F(1000),
                                                 'target_net_return': F(2, 25),
                                                 'minimum_risk': F(1, 15)}]}}}


def test_numeric_feasibility_only_gets_same_input_exact_optimality(one_asset):
    first = checker.verify_numeric(numeric_example(), {'four': one_asset},
                                   exact_one_asset_answers())[0]
    assert first['exact_minimum_verified']
    small = checker.verify_numeric(numeric_example(100), {'four': one_asset},
                                   exact_one_asset_answers())[0]
    assert small['status'] == 'feasible_with_tolerance_optimality_unverified'
    assert not small['exact_minimum_verified']


@pytest.mark.parametrize('field,value', [('fees_yuan', [0]), ('bank_yuan', 1),
                                        ('net_return', 0), ('minimum_risk', 0),
                                        ('status', 'infeasible')])
def test_numeric_fee_budget_return_risk_or_unproved_infeasibility_fails(one_asset, field, value):
    result = numeric_example()
    result['groups']['four'][0][field] = value
    with pytest.raises(ValueError):
        checker.verify_numeric(result, {'four': one_asset}, exact_one_asset_answers())


def test_cli_checks_bundle_and_refuses_overwrite(tmp_path):
    output = tmp_path / 'target-checks.json'
    command = [sys.executable, str(SCRIPT), '--output', str(output)]
    run = subprocess.run(command, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)['exact_minimum_cases'] == 6
    before = output.read_bytes()
    rejected = subprocess.run(command, capture_output=True, text=True)
    assert rejected.returncode != 0 and 'Refusing to replace' in rejected.stderr
    assert output.read_bytes() == before
