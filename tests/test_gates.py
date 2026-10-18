"""Schema-2 scientific declaration gates, with legacy evidence kept separate."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from modeling.schema_contracts import MODEL_CONTRACT_V2, check_model_contract, validate
from scripts import pipeline


def model_contract():
    return {
        'symbols': [{'symbol': 'x', 'unit': 'L', 'object': 'stored water',
                     'uses': [{'equation': 'volume balance', 'object': 'stored water'}]},
                    {'symbol': 'capacity', 'unit': 'L', 'object': 'vessel capacity',
                     'uses': [{'equation': 'capacity bound', 'object': 'vessel capacity'}]}],
        'parameters': [{'symbol': 'capacity', 'value': 10, 'unit': 'L',
                        'source_level': 'measured', 'source': 'measured cylinder',
                        'real_world_quantity': True,
                        'reference_magnitude': {'value': 12, 'unit': 'L', 'source': 'vessel label'}}],
        'mechanisms': [{'id': 'M1', 'cause': 'supply', 'effect_variable': 'x',
                        'sign': '+', 'equation': 'volume balance'}],
        'conserved_quantities': [{'name': 'water', 'check_name': 'balance:water'}],
        'probability_combinations': [], 'logical_claims': [],
        'limiting_cases': [{'case': 'empty vessel', 'expected': 'zero water'}],
        'cheapest_refutation': {'method': 'hand_calc', 'result': '2 + 3 = 5 L'},
        'information_time': 'only initial supply is observed', 'spatial': False,
    }


def make_schema2_case(tmp_path, monkeypatch, *, checks=None, requirements=None):
    monkeypatch.setattr(pipeline, 'PROJECT', tmp_path)
    problem = tmp_path / 'problem.txt'
    problem.write_text('Calculate stored water. Forecast next volume.', encoding='utf-8')
    case = Path(pipeline.init_case(tmp_path / 'cases', 'gated', problem, schema=2)['case'])
    pipeline.save(case / 'planning/model-contract.json', model_contract())
    definition = requirements or {
        'problem_items': [{'id': 'P1', 'quote': 'Calculate stored water.', 'page': 1}],
        'requirements': [{'id': 'Q1', 'question': 'Stored volume', 'unit': 'L',
                          'result_pointer': '/volume', 'checks': ['balance:water'],
                          'problem_item_ids': ['P1'], 'kind': 'answer'}],
    }
    pipeline.save(case / 'planning/requirements.json', definition)
    (case / 'code/model.py').write_text(
        "import argparse,json\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()\n"
        "(a.output/'results.json').write_text(json.dumps({'volume':5}))\n", encoding='utf-8')
    checks = checks or [{'name': 'balance:water', 'passed': True, 'evidence': '2 + 3 = 5 L',
                         'method': 'conservation', 'independent': True}]
    (case / 'code/validate.py').write_text(
        "import argparse,json\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--results');p.add_argument('--output',type=Path);a=p.parse_args()\n"
        f"a.output.write_text(json.dumps({checks!r}))\n", encoding='utf-8')
    return case


def test_model_contract_valid_and_different_object_wording_warns():
    contract = model_contract()
    validate(contract, MODEL_CONTRACT_V2)
    assert check_model_contract(contract) == []
    contract['symbols'][0]['uses'].append({'equation': 'demand', 'object': 'grazing pressure'})
    warnings = []
    assert check_model_contract(contract, warnings) == []
    assert any('symbol x' in p and 'grazing pressure' in p for p in warnings)
    contract['symbols'][0]['same_object_justification'] = 'These are transformed measures of the same stored volume.'
    assert check_model_contract(contract) == []


def test_duplicate_symbol_rows_cannot_hide_different_physical_objects():
    contract = model_contract()
    contract['symbols'].append({'symbol': 'x', 'unit': 'head', 'object': 'grazing pressure',
                                'uses': [{'equation': 'demand', 'object': 'grazing pressure'}]})
    assert any('duplicate symbol' in problem for problem in check_model_contract(contract))


def test_question_extraction_change_invalidates_schema2_evidence(tmp_path, monkeypatch):
    case = make_schema2_case(tmp_path, monkeypatch)
    assert pipeline.run_case(case)['automatic_checks_passed']
    original = case / 'planning/problem-extracted.txt'
    original.write_text('An edited, weaker question.', encoding='utf-8')
    latest = pipeline.status(case)['runs'][-1]
    assert not latest['usable_automatic_evidence']
    assert 'planning/problem-extracted.txt' in latest['stale']


def test_parameter_reference_magnitude_and_units_are_checked():
    contract = model_contract()
    param = contract['parameters'][0]
    param['value'] = 1000
    assert any('magnitude ratio' in p for p in check_model_contract(contract))
    param['magnitude_justification'] = 'A declared scale-up experiment with a 100-fold vessel.'
    assert check_model_contract(contract) == []
    param['reference_magnitude']['unit'] = 'm3'
    assert any('unit must match' in p for p in check_model_contract(contract))
    del param['reference_magnitude']
    assert any('needs reference_magnitude' in p for p in check_model_contract(contract))


def test_independence_assumption_requires_reason_and_logical_type_is_explicit():
    contract = model_contract()
    contract['probability_combinations'] = [{'expression': 'p_a * p_b', 'independence': 'assumed',
                                            'justification': ''}]
    assert any('independence needs justification' in p for p in check_model_contract(contract))
    contract['probability_combinations'][0]['justification'] = 'Independent randomized supply generators.'
    assert check_model_contract(contract) == []
    contract['logical_claims'] = [{'claim': 'positive supply ensures refill', 'type': 'likely',
                                 'proof_ref': 'equation 1'}]
    assert any('outside enum' in p for p in check_model_contract(contract))


def test_new_cases_default_to_schema2_and_cli_can_select_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'PROJECT', tmp_path)
    problem = tmp_path / 'problem.txt'; problem.write_text('Synthetic problem')
    case = Path(pipeline.init_case(tmp_path / 'cases', 'default', problem)['case'])
    assert pipeline.read_case_config(case)['schema'] == 2
    command = [sys.executable, str(pipeline.BUNDLE / 'scripts/pipeline.py'), '--workspace', str(tmp_path),
               'init', '--name', 'legacy', '--problem', str(problem), '--schema', '1']
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    assert pipeline.read_case_config(Path(json.loads(result.stdout)['case']))['schema'] == 1
    for marker in [True, False, 2.0, '2', None, 3]:
        config = pipeline.read_json(case / 'case.json'); config['schema'] = marker
        pipeline.save(case / 'case.json', config)
        with pytest.raises(ValueError, match='Unsupported case schema'):
            pipeline.read_case_config(case)


def test_contract_rejection_prevents_model_execution(tmp_path, monkeypatch):
    case = make_schema2_case(tmp_path, monkeypatch)
    (case / 'planning/model-contract.json').unlink()
    with pytest.raises(ValueError, match='requires planning/model-contract'):
        pipeline.run_case(case)
    assert list((case / 'runs').iterdir()) == []
    contract = model_contract(); contract['information_time'] = ''
    pipeline.save(case / 'planning/model-contract.json', contract)
    with pytest.raises(ValueError, match='information_time'):
        pipeline.run_case(case)
    assert list((case / 'runs').iterdir()) == []


def test_balance_check_is_required_and_valid_run_contract_becomes_stale(tmp_path, monkeypatch):
    case = make_schema2_case(tmp_path, monkeypatch)
    result = pipeline.run_case(case)
    assert result['automatic_checks_passed']
    assert 'planning/model-contract.json' in result['code']
    assert pipeline.evidence_index(case)['status'] == 'evidence-linked'
    contract = model_contract(); contract['information_time'] = 'a revised information boundary'
    pipeline.save(case / 'planning/model-contract.json', contract)
    assert not pipeline.status(case)['runs'][-1]['usable_automatic_evidence']
    assert 'planning/model-contract.json' in pipeline.status(case)['runs'][-1]['stale']
    contract['conserved_quantities'].append({'name': 'energy', 'check_name': 'balance:energy'})
    pipeline.save(case / 'planning/model-contract.json', contract)
    failed = pipeline.run_case(case)
    assert failed['status'] == 'failed'
    assert 'Missing passed conservation check: balance:energy' in failed['error']


def test_declared_parameter_majority_warns_without_blocking(tmp_path, monkeypatch):
    case = make_schema2_case(tmp_path, monkeypatch)
    contract = model_contract(); contract['parameters'][0]['source_level'] = 'declared'
    pipeline.save(case / 'planning/model-contract.json', contract)
    result = pipeline.run_case(case)
    assert result['automatic_checks_passed']
    assert result['model_contract_warnings'] and '>70%' in result['model_contract_warnings'][0]


def test_problem_items_require_verbatim_quotes_and_complete_mapping(tmp_path, monkeypatch):
    case = make_schema2_case(tmp_path, monkeypatch)
    definition = pipeline.read_json(case / 'planning/requirements.json')
    definition['problem_items'].append({'id': 'P2', 'quote': 'Forecast next volume.', 'page': 1})
    definition['problem_items'][0]['quote'] = '  Calculate   stored\nwater. '
    assert any('P2: no requirement mapping' in p for p in pipeline.problem_item_problems(case, definition))
    definition['problem_items'][1]['conditional_answer'] = 'Requires an external future supply model.'
    assert pipeline.problem_item_problems(case, definition) == []
    definition['problem_items'][0]['quote'] = 'Invented stronger question'
    pipeline.save(case / 'planning/requirements.json', definition)
    assert pipeline.run_case(case)['automatic_checks_passed']
    evidence = pipeline.evidence_index(case)
    assert evidence['status'] == 'evidence-incomplete'
    assert any('quote not found verbatim' in p for p in evidence['problem_item_problems'])


@pytest.mark.parametrize('method,independent', [('replay', True), ('analytic', False)])
def test_requirement_needs_independent_nonreplay_check(tmp_path, monkeypatch, method, independent):
    checks = [{'name': 'balance:water', 'passed': True, 'evidence': '2 + 3 = 5 L',
               'method': method, 'independent': independent}]
    case = make_schema2_case(tmp_path, monkeypatch, checks=checks)
    assert pipeline.run_case(case)['automatic_checks_passed']
    evidence = pipeline.evidence_index(case)
    assert evidence['status'] == 'evidence-incomplete'
    assert 'non-replay' in evidence['entries'][0]['errors'][0]


@pytest.mark.parametrize('method', [None, 'trust_me', [], True])
def test_every_schema2_check_has_an_enumerated_method(tmp_path, monkeypatch, method):
    checks = [{'name': 'balance:water', 'passed': True, 'evidence': '2 + 3 = 5 L',
               'method': method, 'independent': True}]
    case = make_schema2_case(tmp_path, monkeypatch, checks=checks)
    receipt = pipeline.run_case(case)
    assert receipt['status'] == 'failed'
    assert 'method must be one of' in receipt['error']


def test_forecast_baseline_scores_and_disclosure_are_enforced(tmp_path, monkeypatch):
    checks = [{'name': 'balance:water', 'passed': True, 'evidence': '2 + 3 = 5 L',
               'method': 'naive_baseline', 'independent': True,
               'baseline_score': 1, 'model_score': 2, 'metric': 'MAE', 'lower_is_better': True}]
    case = make_schema2_case(tmp_path, monkeypatch, checks=checks)
    definition = pipeline.read_json(case / 'planning/requirements.json')
    definition['requirements'][0]['kind'] = 'forecast'
    pipeline.save(case / 'planning/requirements.json', definition)
    assert pipeline.run_case(case)['automatic_checks_passed']
    evidence = pipeline.evidence_index(case)
    assert evidence['status'] == 'evidence-incomplete'
    assert any('worse than naive baseline' in p for p in evidence['claim_problems'])
    lookup = {check['name']: check for check in checks}
    checks[0]['disclosed'] = True
    assert pipeline.claim_problems(definition['requirements'], [], lookup, {}, schema=2) == []
    checks[0]['model_score'] = 0.5; checks[0].pop('disclosed')
    assert pipeline.claim_problems(definition['requirements'], [], lookup, {}, schema=2) == []
    checks[0]['lower_is_better'] = False
    assert pipeline.claim_problems(definition['requirements'], [], lookup, {}, schema=2)
    checks[0]['method'] = 'analytic'
    assert any('requires a naive_baseline' in p for p in pipeline.claim_problems(
        definition['requirements'], [], lookup, {}, schema=2))


def test_dependency_snapshot_only_omitted_for_schema2_clean_checkout(tmp_path, monkeypatch):
    case = make_schema2_case(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline, 'clean_bundle_commit', lambda: 'a' * 40)
    receipt = pipeline.run_case(case)
    run = Path(receipt['run'])
    assert receipt['automatic_checks_passed']
    assert receipt['bundle_git_commit'] == 'a' * 40
    assert receipt['dependencies'] and (run / 'source-snapshot/planning/model-contract.json').is_file()
    assert not (run / 'dependency-snapshot').exists()
    monkeypatch.setattr(pipeline, 'clean_bundle_commit', lambda: None)
    receipt = pipeline.run_case(case)
    assert receipt['automatic_checks_passed'] and 'bundle_git_commit' not in receipt
    assert 'planning/model-contract.json' in receipt['code']
    assert (Path(receipt['run']) / 'dependency-snapshot/scripts/pipeline.py').is_file()
    config = pipeline.read_json(case / 'case.json'); config['schema'] = 1
    pipeline.save(case / 'case.json', config)
    monkeypatch.setattr(pipeline, 'clean_bundle_commit', lambda: 'a' * 40)
    receipt = pipeline.run_case(case)
    assert receipt['automatic_checks_passed'] and 'bundle_git_commit' not in receipt
    assert 'planning/model-contract.json' not in receipt['code']
    assert (Path(receipt['run']) / 'dependency-snapshot/scripts/pipeline.py').is_file()


def test_clean_bundle_detection_requires_own_clean_git_root(tmp_path, monkeypatch):
    bundle = tmp_path / 'bundle'; bundle.mkdir()
    monkeypatch.setattr(pipeline, 'BUNDLE', bundle)
    assert pipeline.clean_bundle_commit() is None
    subprocess.run(['git', 'init', '-q', str(bundle)], check=True)
    subprocess.run(['git', '-C', str(bundle), 'config', 'user.name', 'Gate Test'], check=True)
    subprocess.run(['git', '-C', str(bundle), 'config', 'user.email', 'gate@example.invalid'], check=True)
    (bundle / 'source.py').write_text('x=1\n')
    subprocess.run(['git', '-C', str(bundle), 'add', 'source.py'], check=True)
    subprocess.run(['git', '-C', str(bundle), 'commit', '-qm', 'fixture'], check=True)
    assert len(pipeline.clean_bundle_commit()) == 40
    (bundle / 'untracked.txt').write_text('new')
    assert pipeline.clean_bundle_commit() is None
    (bundle / 'untracked.txt').unlink()
    (bundle / 'source.py').write_text('x=2\n')
    assert pipeline.clean_bundle_commit() is None
    nested = bundle / 'installed-copy'; nested.mkdir()
    monkeypatch.setattr(pipeline, 'BUNDLE', nested)
    assert pipeline.clean_bundle_commit() is None
