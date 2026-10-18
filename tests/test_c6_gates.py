"""C6 regressions for schema-2 modeling-gate bypasses (G-1..G-8 and checker usability).

Each gate has a passing declaration and the reproduced bypass that must now fail.
Schema-1 cases keep their original behaviour.
"""
import json
from pathlib import Path

import pytest

from modeling import lessons
from modeling.schema_contracts import check_model_contract
from scripts import pipeline
from scripts import workflow as w


PROBLEM = ('Problem B: Managing Water.\nYour team should develop a model to\ncalculate the stored water in the reser-\n'
           'voir over time. Forecast the next year volume.\nDiscuss the policy impact on residents.\n'
           'See https://www.comap.com/contests/mcm-icm for the contest summary sheet.\n')


def contract():
    return {
        'symbols': [{'symbol': 'x', 'unit': 'L', 'object': 'stored water',
                     'uses': [{'equation': 'eq1', 'object': 'stored water'}]},
                    {'symbol': 'cap', 'unit': 'L', 'object': 'reservoir capacity',
                     'uses': [{'equation': 'eq2', 'object': 'reservoir capacity'}]}],
        'parameters': [{'symbol': 'cap', 'value': 10, 'unit': 'L', 'source_level': 'measured', 'source': 'gauge',
                        'real_world_quantity': True,
                        'reference_magnitude': {'value': 12, 'unit': 'L', 'source': 'vessel label'}}],
        'mechanisms': [{'id': 'M1', 'cause': 'supply', 'effect_variable': 'x', 'sign': '+', 'equation': 'eq1'}],
        'conserved_quantities': [{'name': 'water', 'check_name': 'balance:water'}],
        'probability_combinations': [], 'logical_claims': [],
        'limiting_cases': [{'case': 'empty', 'expected': 'zero water'}],
        'cheapest_refutation': {'method': 'hand_calc', 'result': '2 + 3 = 5 L'},
        'information_time': 'initial supply only', 'spatial': False}


def requirements():
    return {'problem_items': [
                {'id': 'P1', 'quote': 'calculate the stored water in the reser- voir over time.', 'page': 1},
                {'id': 'P2', 'quote': 'Forecast the next year volume.', 'page': 1},
                {'id': 'P3', 'quote': 'Discuss the policy impact on residents.', 'page': 1}],
            'requirements': [
                {'id': 'Q1', 'question': 'volume', 'unit': 'L', 'result_pointer': '/volume', 'kind': 'answer',
                 'checks': ['balance:water'], 'problem_item_ids': ['P1', 'P3']},
                {'id': 'Q2', 'question': 'forecast', 'unit': 'L', 'result_pointer': '/volume', 'kind': 'forecast',
                 'checks': ['balance:water', 'baseline'], 'problem_item_ids': ['P2']}]}


def checks():
    return [{'name': 'balance:water', 'passed': True, 'evidence': '2+3=5', 'method': 'conservation', 'independent': True},
            {'name': 'baseline', 'passed': True, 'evidence': 'MAE', 'method': 'naive_baseline', 'independent': True,
             'baseline_score': 2, 'model_score': 1, 'metric': 'MAE', 'lower_is_better': True}]


def write_code(case, rows):
    (case / 'code/model.py').write_text(
        "import argparse,json\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()\n"
        "(a.output/'results.json').write_text(json.dumps({'volume':5}))\n", encoding='utf-8')
    (case / 'code/validate.py').write_text(
        "import argparse,json\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--results');p.add_argument('--output',type=Path);a=p.parse_args()\n"
        f"a.output.write_text({json.dumps(json.dumps(rows))})\n", encoding='utf-8')


@pytest.fixture
def make(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'PROJECT', tmp_path)
    counter = iter(range(1000))

    def build(schema=2, c=None, req=None, ch=None, text=PROBLEM):
        problem = tmp_path / 'problem.txt'
        problem.write_text(text, encoding='utf-8')
        case = Path(pipeline.init_case(tmp_path / 'cases', f'c6-{next(counter)}', problem, schema=schema)['case'])
        if schema == 2:
            pipeline.save(case / 'planning/model-contract.json', contract() if c is None else c)
        pipeline.save(case / 'planning/requirements.json', requirements() if req is None else req)
        write_code(case, checks() if ch is None else ch)
        return case
    return build


def kinds(problems):
    return [p for p in problems if 'kind' in p]


# G-1 ---------------------------------------------------------------------------------------------

def test_g1_kind_declared_and_forecast_wording_matches_kind(make):
    case = make()
    assert pipeline.problem_item_problems(case, requirements()) == []
    definition = requirements()
    definition['requirements'][1]['kind'] = 'answer'
    definition['requirements'][1]['kind_justification'] = 'The table asks only for the recorded value, not a projection.'
    assert pipeline.problem_item_problems(case, definition) == []


def test_g1_missing_kind_or_relabeled_forecast_is_rejected(make):
    case = make()
    definition = requirements(); del definition['requirements'][0]['kind']
    assert any('Q1' in p and 'kind' in p for p in pipeline.problem_item_problems(case, definition))
    definition = requirements(); definition['requirements'][1]['kind'] = 'answer'
    assert any('Q2' in p and 'kind_justification' in p for p in pipeline.problem_item_problems(case, definition))
    definition['requirements'][1]['kind_justification'] = '.'
    assert any('kind_justification' in p for p in pipeline.problem_item_problems(case, definition))
    # Chinese forecast wording and an entirely omitted kind both fail the gate.
    chinese = '请建立模型预测未来五年的水库蓄水量变化趋势并给出建议。'
    case = make(text=chinese)
    definition = {'problem_items': [{'id': 'P1', 'quote': chinese, 'page': 1}],
                  'requirements': [{'id': 'Q1', 'question': 'v', 'unit': 'L', 'result_pointer': '/volume',
                                    'kind': 'decision', 'checks': ['balance:water'], 'problem_item_ids': ['P1']}]}
    assert any('kind_justification' in p for p in pipeline.problem_item_problems(case, definition))


# G-2 ---------------------------------------------------------------------------------------------

def test_g2_declared_symbols_and_normalized_identity_pass():
    c = contract()
    c['symbols'][0]['symbol'] = 'H_{z}'
    c['mechanisms'][0]['effect_variable'] = 'H_z'
    assert check_model_contract(c) == []


def test_g2_empty_or_undeclared_symbols_rejected_and_top_object_warns():
    c = contract()
    c['symbols'] = []; c['parameters'] = []; c['mechanisms'] = []; c['conserved_quantities'] = []
    assert any('at least one symbol' in p for p in check_model_contract(c))
    c = contract(); c['mechanisms'][0]['effect_variable'] = 'y'
    assert any('effect_variable' in p and 'y' in p for p in check_model_contract(c))
    c = contract(); c['parameters'][0]['symbol'] = 'R0'
    assert any('R0' in p and 'not declared' in p for p in check_model_contract(c))
    c = contract(); c['symbols'][0]['symbol'] = 'H_z'
    c['symbols'][1]['symbol'] = 'H_{z}'; c['parameters'][0]['symbol'] = 'H_z'; c['mechanisms'][0]['effect_variable'] = 'H_z'
    assert any('duplicate symbol' in p for p in check_model_contract(c))
    c = contract(); c['symbols'][0]['object'] = 'grazing pressure'
    warnings = []
    assert check_model_contract(c, warnings) == []
    assert any('symbol x' in p and 'grazing pressure' in p for p in warnings)


# G-3 ---------------------------------------------------------------------------------------------

def test_g3_widened_ratio_ok_needs_justification():
    c = contract(); c['parameters'][0].update(value=8e7)
    c['parameters'][0]['reference_magnitude'].update(value=3e9, ratio_ok=[1e-3, 1e12])
    assert any('wider than the default' in p for p in check_model_contract(c))
    c['parameters'][0]['magnitude_justification'] = 'Only the regional subsidy line is modelled, by design.'
    assert check_model_contract(c) == []


def test_g3_zero_lower_bound_is_rejected_even_with_justification():
    c = contract(); c['parameters'][0]['reference_magnitude']['ratio_ok'] = [0, 1e12]
    c['parameters'][0]['magnitude_justification'] = 'Wide tolerance for a declared scenario.'
    assert any('lower bound must be positive' in p for p in check_model_contract(c))


# G-4 ---------------------------------------------------------------------------------------------

@pytest.fixture
def wcase(make):
    req = requirements()
    case = make(req=req)
    w.init(case, 'Check a known sum', query='reservoir storage balance', budget_seconds=120,
           max_attempts=3, per_run_timeout=5, lessons_path='no-lessons.jsonl')
    return case


def execute(case):
    return w.run(case, w.canonical_hash(pipeline.source_snapshot(case)))


def review(case, receipt, symbols_checked):
    value = {'verdict': 'pass', 'actor': 'independent reviewer', 'scope': 'all',
             'run_id': Path(receipt['run']).name, 'receipt_sha256': pipeline.digest(Path(receipt['run']) / 'receipt.json'),
             'quality_decision': {'decision': 'stop', 'reason': 'known answer'},
             'problem_items_ticked': [{'id': p, 'location': 'sec 1'} for p in ('P1', 'P2', 'P3')],
             'attacks': [{'type': 'units', 'target': 'eq1', 'result': 'survived'},
                         {'type': 'limit_case', 'target': 'eq1', 'result': 'survived'},
                         {'type': 'magnitude', 'target': 'cap', 'result': 'survived'}],
             'mechanism_audit': {'symbols_checked': symbols_checked, 'double_meaning_found': []}}
    path = case / 'planning/review.json'
    pipeline.save(path, value)
    return path


def test_g4_mechanism_audit_covering_all_symbols_is_accepted(wcase):
    receipt = execute(wcase)
    assert receipt['automatic_checks_passed']
    w.accept(wcase, review(wcase, receipt, 2))
    assert w.next(wcase)['action'] == 'report'


@pytest.mark.parametrize('count', [0, 1])
def test_g4_mechanism_audit_below_declared_symbols_is_rejected(wcase, count):
    receipt = execute(wcase)
    with pytest.raises(ValueError, match='symbols_checked'):
        w.accept(wcase, review(wcase, receipt, count))


# G-5 ---------------------------------------------------------------------------------------------

def test_g5_valid_contract_consumes_one_attempt(wcase):
    assert w.next(wcase)['action'] == 'run'
    execute(wcase)
    assert w.read_state(wcase)[0]['attempts'] == 1


def test_g5_contract_rejection_does_not_consume_attempt_and_next_prepares(wcase):
    c = contract(); c['information_time'] = ''; c['mechanisms'][0]['effect_variable'] = 'q'
    pipeline.save(wcase / 'planning/model-contract.json', c)
    for _ in range(3):
        with pytest.raises(ValueError, match='Model contract rejected'):
            execute(wcase)
    state = w.read_state(wcase)[0]
    assert state['attempts'] == 0 and state['attempt_history'] == []
    assert not list((wcase / 'runs').iterdir())
    step = w.next(wcase)
    assert step['action'] == 'prepare'
    assert any('information_time' in p for p in step['contract_problems'])
    assert any('effect_variable' in p for p in step['contract_problems'])
    (wcase / 'planning/model-contract.json').unlink()
    assert w.next(wcase)['action'] == 'prepare'
    with pytest.raises(ValueError, match='model-contract'):
        execute(wcase)
    assert w.read_state(wcase)[0]['attempts'] == 0


# G-6 ---------------------------------------------------------------------------------------------

def test_g6_long_distinct_and_hyphenated_quotes_pass(make):
    case = make()
    definition = requirements()
    for quote in ('calculate the stored water in the reservoir over time.',
                  'calculate the stored water in the reser-\nvoir over time.'):
        definition['problem_items'][0]['quote'] = quote
        assert pipeline.problem_item_problems(case, definition) == []
    chinese = '请建立数学模型计算水库中的蓄水量随时间的变化。'
    case = make(text=chinese)
    item = {'id': 'P1', 'quote': '计算水库中的蓄水量随时间的变化', 'page': 1}
    assert pipeline.problem_item_problems(case, {'problem_items': [item], 'requirements': [
        {'id': 'Q1', 'question': 'v', 'unit': 'L', 'result_pointer': '/v', 'kind': 'answer',
         'checks': ['c'], 'problem_item_ids': ['P1']}]}) == []


@pytest.mark.parametrize('quote', ['a', 'water', 'Forecast the', '蓄水量'])
def test_g6_short_quotes_are_rejected(make, quote):
    case = make()
    definition = requirements(); definition['problem_items'][1]['quote'] = quote
    assert any('P2' in p and 'too short' in p for p in pipeline.problem_item_problems(case, definition))


def test_g6_duplicate_quotes_are_rejected(make):
    case = make()
    definition = requirements()
    definition['problem_items'][2]['quote'] = ' forecast  the next year volume. '
    assert any('same quote' in p for p in pipeline.problem_item_problems(case, definition))


# 7: report every contract problem; explicit unknown values ----------------------------------------

def test_checker_reports_all_type_and_semantic_problems():
    c = contract()
    c['parameters'][0]['value'] = 'unknown'
    c['parameters'][0]['real_world_quantity'] = 'yes'
    c['symbols'][0]['uses'].append({'equation': 'eq9', 'object': 'grazing pressure'})
    c['information_time'] = ''
    warnings = []
    problems = check_model_contract(c, warnings)
    assert any('parameters[0].value' in p for p in problems)
    assert any('real_world_quantity' in p for p in problems)
    assert any('symbol x' in p and 'grazing pressure' in p for p in warnings)
    assert not any('symbol x' in p for p in problems)
    assert any('information_time' in p for p in problems)


def test_unknown_parameter_value_is_a_warning_not_a_rejection(make):
    c = contract()
    c['parameters'][0].update(value=None, source_level='unknown')
    del c['parameters'][0]['reference_magnitude']
    warnings = []
    assert check_model_contract(c, warnings) == []
    assert any('cap' in text and 'unknown' in text for text in warnings)
    c['parameters'][0]['reference_magnitude'] = {'value': 12, 'unit': 'L', 'source': 'label'}
    warnings = []
    assert check_model_contract(c, warnings) == []
    assert any('magnitude check skipped' in text for text in warnings)
    receipt = pipeline.run_case(make(c=c))
    assert receipt['automatic_checks_passed']
    assert any('magnitude check skipped' in text for text in receipt['model_contract_warnings'])


@pytest.mark.parametrize('value,level', [(None, 'measured'), (10, 'unknown')])
def test_null_value_requires_unknown_source_level(value, level):
    c = contract(); c['parameters'][0].update(value=value, source_level=level)
    assert any('unknown' in p for p in check_model_contract(c))


# 8: minor items ------------------------------------------------------------------------------------

def test_punctuation_justifications_are_rejected():
    c = contract(); c['symbols'][0]['uses'].append({'equation': 'eq9', 'object': 'stored water volume'})
    c['symbols'][0]['same_object_justification'] = '.'
    warnings = []
    assert check_model_contract(c, warnings) == []
    assert any('same_object_justification' in p for p in warnings)
    c['symbols'][0]['same_object_justification'] = '同一水体'
    assert check_model_contract(c) == []
    c['probability_combinations'] = [{'expression': 'p*q', 'independence': 'assumed', 'justification': '..'}]
    assert any('justification' in p for p in check_model_contract(c))


def test_huge_integer_ratio_is_a_problem_not_a_traceback():
    c = contract(); c['parameters'][0]['value'] = 10 ** 400
    problems = check_model_contract(c)
    assert any('cap' in p and 'too large' in p for p in problems)


def test_balance_check_method_must_be_conservation_analytic_or_bound(make):
    rows = checks(); rows[0]['method'] = 'hand_calc'
    case = make(ch=rows)
    assert pipeline.run_case(case)['automatic_checks_passed']
    evidence = pipeline.evidence_index(case)
    assert evidence['status'] == 'evidence-incomplete'
    assert any('balance:water' in p and 'conservation' in p for p in evidence['problem_item_problems'])
    rows[0]['method'] = 'analytic'
    case = make(ch=rows)
    assert pipeline.run_case(case)['automatic_checks_passed']
    assert pipeline.evidence_index(case)['status'] == 'evidence-linked'


def test_problem_query_drops_urls_and_contest_boilerplate(make):
    case = make()
    terms = w.problem_query(case).split()
    assert 'water' in terms and 'reservoir' in terms and 'voir' not in terms
    banned = {'comap', 'www', 'com', 'page', 'summary', 'sheet', 'team', 'report', 'mcm', 'icm',
              'problem', 'contest', 'contests', 'https'}
    assert not banned & set(terms)


def test_lesson_tags_match_whole_words_and_legacy_tag_lists_are_capped(tmp_path):
    path = tmp_path / 'lessons.jsonl'
    base = dict(problem='alpha', structure='beta', recognized='r', routes_tried=['a'], what_failed='f',
                what_worked='w', verified_by='v', principle='gamma.', evidence='observed once')
    legacy = dict(base, id='L0001', tags=['ode'] + [f'tag{i}' for i in range(1, 12)])
    path.write_text(json.dumps(legacy) + '\n', encoding='utf-8')
    assert lessons.search_lessons(path, 'ode')[0]['id'] == 'L0001'
    assert lessons.search_lessons(path, 'tag7')[0]['id'] == 'L0001'
    assert lessons.search_lessons(path, 'model node') == []   # 'ode' is not a whole word here
    assert lessons.search_lessons(path, 'tag11') == []        # beyond the first eight legacy tags


# 9: G-7 / G-8 --------------------------------------------------------------------------------------

def test_g7_extracted_text_hash_and_declared_corrections(make):
    case = make()
    config = pipeline.read_case_config(case)
    extracted = case / 'planning/problem-extracted.txt'
    assert config['problem_extracted_sha256'] == pipeline.digest(extracted)
    assert pipeline.problem_item_problems(case, requirements()) == []
    extracted.write_text(extracted.read_text(encoding='utf-8') + 'Assume the dam never fails at any time.\n',
                         encoding='utf-8')
    assert any('problem_text_corrections' in p for p in pipeline.problem_item_problems(case, requirements()))
    definition = requirements()
    definition['problem_text_corrections'] = [{'before': '', 'after': 'Assume the dam never fails at any time.',
                                               'reason': 'Restored a sentence the PDF extractor dropped.'}]
    assert pipeline.problem_item_problems(case, definition) == []
    definition['problem_text_corrections'][0]['after'] = 'Something not in the text at all.'
    assert any('problem_text_corrections' in p for p in pipeline.problem_item_problems(case, definition))


def test_g7_g8_schema1_cases_are_unchanged(make):
    case = make(schema=1, req={'requirements': [{'id': 'Q1', 'question': 'v', 'unit': 'L',
                                                 'result_pointer': '/volume', 'checks': ['balance:water']}]},
                ch=[{'name': 'balance:water', 'passed': True, 'evidence': 'e'}])
    assert 'problem_extracted_sha256' not in pipeline.read_case_config(case)
    assert pipeline.run_case(case)['automatic_checks_passed']
    assert pipeline.evidence_index(case)['status'] == 'evidence-linked'
    state = w.init(case, 'g', budget_seconds=120, per_run_timeout=5, lessons_path='none.jsonl')['state']
    assert state['case_schema'] == 1
    assert w.next(case)['action'] == 'review'


def test_g8_workflow_and_status_detect_schema_downgrade(wcase):
    assert w.read_state(wcase)[0]['case_schema'] == 2
    receipt = execute(wcase)
    assert receipt['automatic_checks_passed']
    assert pipeline.status(wcase)['runs'][-1]['usable_automatic_evidence']
    config = pipeline.read_json(wcase / 'case.json')
    for change in ({'schema': 1}, None):
        if change is None:
            config.pop('schema')
        else:
            config.update(change)
        pipeline.save(wcase / 'case.json', config)
        latest = pipeline.status(wcase)['runs'][-1]
        assert not latest['usable_automatic_evidence']
        assert any('schema' in reason for reason in latest['stale'])
        with pytest.raises(ValueError, match='case schema'):
            w.next(wcase)
        with pytest.raises(ValueError, match='case schema'):
            execute(wcase)
