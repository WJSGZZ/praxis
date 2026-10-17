"""Schema-2 review and pre-run lesson decisions are bound to actual snapshots."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import workflow as w


@pytest.fixture
def case2(tmp_path, monkeypatch):
    monkeypatch.setattr(w.pipeline, 'PROJECT', tmp_path)
    problem = tmp_path / 'problem.txt'
    problem.write_text('Calculate stored water. Determine water capacity. Water water storage capacity.', encoding='utf-8')
    case = Path(w.pipeline.init_case(tmp_path / 'cases', 'review-gates', problem, schema=2)['case'])
    contract = {'symbols': [{'symbol': 'V', 'unit': 'L', 'object': 'stored water',
                             'uses': [{'equation': 'addition', 'object': 'stored water'}]}],
                'parameters': [], 'mechanisms': [], 'conserved_quantities': [],
                'probability_combinations': [], 'logical_claims': [],
                'limiting_cases': [{'case': 'zero supply', 'expected': 'zero added water'}],
                'cheapest_refutation': {'method': 'hand_calc', 'result': '2 + 3 = 5 L'},
                'information_time': 'initial supply', 'spatial': False}
    w.pipeline.save(case / 'planning/model-contract.json', contract)
    w.pipeline.save(case / 'planning/requirements.json', {
        'problem_items': [{'id': 'P1', 'quote': 'Calculate stored water.', 'page': 1},
                          {'id': 'P2', 'quote': 'Determine water capacity.', 'page': 1}],
        'requirements': [{'id': 'Q1', 'question': 'stored water', 'unit': 'L', 'result_pointer': '/volume',
                          'checks': ['arithmetic'], 'problem_item_ids': ['P1', 'P2'], 'kind': 'answer'}],
    })
    (case / 'code/model.py').write_text(
        "import argparse,json\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()\n"
        "(a.output/'results.json').write_text(json.dumps({'volume':5}))\n", encoding='utf-8')
    (case / 'code/validate.py').write_text(
        "import argparse,json\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--results');p.add_argument('--output',type=Path);a=p.parse_args()\n"
        "a.output.write_text(json.dumps([{'name':'arithmetic','passed':True,'evidence':'2+3=5 L',"
        "'independent':True,'method':'hand_calc'}]))\n", encoding='utf-8')
    return case


def initialise(case, **kwargs):
    return w.init(case, 'Check a known sum', budget_seconds=120, max_attempts=3, per_run_timeout=5, **kwargs)


def execute(case):
    return w.run(case, w.canonical_hash(w.pipeline.source_snapshot(case)))


def review_file(case, receipt):
    value = {'verdict': 'pass', 'actor': 'independent test reviewer', 'scope': 'answer and mechanism',
             'run_id': Path(receipt['run']).name,
             'receipt_sha256': w.pipeline.digest(Path(receipt['run']) / 'receipt.json'),
             'quality_decision': {'decision': 'stop', 'reason': 'known arithmetic answer'},
             'problem_items_ticked': [{'id': 'P1', 'location': 'results.json /volume'},
                                      {'id': 'P2', 'location': 'results.json /volume'}],
             'attacks': [{'type': 'units', 'target': 'volume addition', 'result': 'survived'},
                         {'type': 'limit_case', 'target': 'zero supply', 'result': 'survived'},
                         {'type': 'independent_recompute', 'target': '2+3', 'result': 'survived'}],
             'mechanism_audit': {'symbols_checked': 1, 'double_meaning_found': []}}
    path = case / 'planning/review.json'
    w.pipeline.save(path, value)
    return path, value


def seed_lesson(case, identity='L0001'):
    path = w.pipeline.PROJECT / 'lessons.jsonl'
    row = {'id': identity, 'date': '2026-10-16', 'problem': 'water capacity', 'structure': 'water storage',
           'recognized': 'volume addition', 'routes_tried': ['addition'], 'what_failed': 'no bound',
           'what_worked': 'compare capacity', 'verified_by': 'hand addition',
           'principle': 'Check water capacity before accepting additions.',
           'checklist': ['Check water capacity.'], 'tags': ['water']}
    path.write_text(json.dumps(row) + '\n', encoding='utf-8')
    return path


def test_schema2_full_review_accepts_and_remains_bound_to_its_fields(case2):
    initialise(case2)
    receipt = execute(case2)
    assert receipt['automatic_checks_passed']
    path, value = review_file(case2, receipt)
    w.accept(case2, path)
    assert w.next(case2)['action'] == 'report'
    value['attacks'][0]['target'] = 'a newly scoped attack'
    w.pipeline.save(path, value)
    assert w.next(case2)['action'] == 'review'


def test_legacy_case_keeps_empty_query_and_original_review_contract(case2):
    config = w.pipeline.read_json(case2 / 'case.json'); config['schema'] = 1
    w.pipeline.save(case2 / 'case.json', config)
    state = initialise(case2)['state']
    assert state['lesson_retrieval']['query'] == ''
    assert 'query_source' not in state['lesson_retrieval']
    receipt = execute(case2)
    path, value = review_file(case2, receipt)
    for field in ('problem_items_ticked', 'attacks', 'mechanism_audit'):
        value.pop(field)
    w.pipeline.save(path, value)
    w.accept(case2, path)
    assert w.next(case2)['action'] == 'report'


@pytest.mark.parametrize('ticks', [None, [], [{'id': 'P1', 'location': 'result'}],
    [{'id': 'P1', 'location': 'result'}, {'id': 'P1', 'location': 'another result'}],
    [{'id': 'P1', 'location': 'result'}, {'id': 'P3', 'location': 'result'}],
    [{'id': 'P1', 'location': 'result'}, {'id': 'P2', 'location': '   '}],
    ['P1', 'P2']])
def test_review_ticking_rejects_missing_forged_duplicate_or_unlocated_items(case2, ticks):
    initialise(case2); receipt = execute(case2)
    path, value = review_file(case2, receipt)
    value['problem_items_ticked'] = ticks; w.pipeline.save(path, value)
    before = (case2 / 'planning/progress.md').read_bytes()
    with pytest.raises(ValueError, match='problem_items_ticked'):
        w.accept(case2, path)
    assert (case2 / 'planning/progress.md').read_bytes() == before


@pytest.mark.parametrize('attack', [None, {}, {'type': 'invented', 'target': 'x', 'result': 'survived'},
    {'type': [], 'target': 'x', 'result': 'survived'},
    {'type': 'units', 'target': 'x', 'result': 'maybe'},
    {'type': 'units', 'target': ' ', 'result': 'survived'},
    {'type': 'units', 'target': 'x', 'result': ['survived']}])
def test_review_rejects_malformed_unknown_or_untargeted_attacks(case2, attack):
    initialise(case2); receipt = execute(case2)
    path, value = review_file(case2, receipt)
    value['attacks'][0] = attack; w.pipeline.save(path, value)
    with pytest.raises(ValueError, match='allowed type/result'):
        w.accept(case2, path)


def test_review_needs_three_attacks_and_refutation_cannot_pass(case2):
    initialise(case2); receipt = execute(case2)
    path, value = review_file(case2, receipt)
    good = deepcopy(value)
    value['attacks'] = value['attacks'][:2]; w.pipeline.save(path, value)
    with pytest.raises(ValueError, match='at least three'):
        w.accept(case2, path)
    good['attacks'][1]['result'] = 'refuted'; w.pipeline.save(path, good)
    with pytest.raises(ValueError, match='refuted attack'):
        w.accept(case2, path)


@pytest.mark.parametrize('mechanism', [None, {}, {'symbols_checked': True, 'double_meaning_found': []},
    {'symbols_checked': -1, 'double_meaning_found': []},
    {'symbols_checked': 1.0, 'double_meaning_found': []},
    {'symbols_checked': 1, 'double_meaning_found': None},
    {'symbols_checked': 1, 'double_meaning_found': ['V means stored volume and grazing pressure']}])
def test_review_rejects_malformed_audit_or_unresolved_double_meaning(case2, mechanism):
    initialise(case2); receipt = execute(case2)
    path, value = review_file(case2, receipt)
    value['mechanism_audit'] = mechanism; w.pipeline.save(path, value)
    with pytest.raises(ValueError, match='mechanism_audit|double meanings'):
        w.accept(case2, path)


@pytest.mark.parametrize('query', ['', 'MCM generic prior lessons', 'GENERIC water'])
def test_empty_or_generic_query_is_derived_from_problem_and_used_in_actual_search(case2, query):
    history = seed_lesson(case2)
    state = initialise(case2, query=query, lessons_path=history)['state']
    retrieval = state['lesson_retrieval']
    assert retrieval['query'].split()[0] == 'water'
    assert 1 <= len(retrieval['query'].split()) <= 15
    assert not {'the', 'and', 'determine'} & set(retrieval['query'].split())
    assert retrieval['query_source'] == 'problem-extracted-top15-content-terms'
    assert 'heuristic' in retrieval['query_tokenization']
    assert retrieval['hits'] == [{'id': row['id'], 'sha256': w.canonical_hash(row)}
                                 for row in w.lessons.search_lessons(history, retrieval['query'], limit=3)]
    assert w.read_state(case2)[0]['lesson_retrieval'] == retrieval


def test_specific_query_is_preserved_and_top15_limits_distinct_terms(case2):
    state = initialise(case2, query='unit-consistent storage')['state']
    assert state['lesson_retrieval']['query'] == 'unit-consistent storage'
    assert 'query_source' not in state['lesson_retrieval']
    terms = 'alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec'
    (case2 / 'planning/problem-extracted.txt').write_text('alpha alpha ' + terms)
    result = w.problem_query(case2).split()
    assert len(result) == 15 and result[0] == 'alpha' and 'quebec' not in result


def test_chinese_query_uses_documented_bigram_approximation(case2):
    (case2 / 'planning/problem-extracted.txt').write_text('水资源水资源水资源。供水模型供水模型。', encoding='utf-8')
    retrieval = initialise(case2)['state']['lesson_retrieval']
    assert {'水资', '资源', '供水', '模型'} <= set(retrieval['query'].split())
    assert 'Chinese character-bigram heuristic' in retrieval['query_tokenization']


def test_empty_extracted_text_needs_a_specific_query(case2):
    (case2 / 'planning/problem-extracted.txt').write_text('the and to 1234', encoding='utf-8')
    before = (case2 / 'planning/progress.md').read_bytes() if (case2 / 'planning/progress.md').exists() else None
    with pytest.raises(ValueError, match='provide a specific query'):
        initialise(case2)
    assert not (case2 / 'planning/progress.md').exists() if before is None else (case2 / 'planning/progress.md').read_bytes() == before


@pytest.mark.parametrize('line', ['- L0001 applied: Compare water capacity with the computed sum.',
                                 '- applied: L0001 Compare water capacity with the computed sum.',
                                 '- not_applied: L0001 No capacity limit is part of this synthetic question.'])
def test_lesson_decision_is_present_before_first_run_and_accepts_from_snapshot(case2, line):
    history = seed_lesson(case2)
    initialise(case2, lessons_path=history)
    (case2 / 'planning/tasks.md').write_text(line + '\n', encoding='utf-8')
    receipt = execute(case2)
    path, _ = review_file(case2, receipt)
    w.accept(case2, path)
    assert w.next(case2)['action'] == 'report'
    snapshot = Path(receipt['run']) / 'source-snapshot/planning/tasks.md'
    assert snapshot.read_text(encoding='utf-8').strip() == line


@pytest.mark.parametrize('line', ['- L0001 is relevant.', '- applied: Use the lesson.',
                                 '- applied: L0002 Compare capacity.', '- L0001 applied: ...',
                                 '- L0001 applied:', '- PrefixL0001 applied: Compare capacity.',
                                 '- L0001 applied:\nAn unrelated paragraph.'])
def test_lesson_mention_without_exact_id_decision_and_action_blocks_first_run(case2, line):
    history = seed_lesson(case2)
    initialise(case2, lessons_path=history)
    (case2 / 'planning/tasks.md').write_text(line + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='applied: or not_applied:'):
        execute(case2)
    assert not list((case2 / 'runs').iterdir())
    assert w.read_state(case2)[0]['attempts'] == 0


def test_lesson_decision_added_after_first_run_cannot_retroactively_accept(case2):
    history = seed_lesson(case2)
    initialise(case2, lessons_path=history)
    first = w.pipeline.run_case(case2)  # Deliberately bypass the controller's preflight.
    assert first['automatic_checks_passed']
    (case2 / 'planning/tasks.md').write_text('- L0001 applied: Compare capacity before addition.\n', encoding='utf-8')
    latest = execute(case2)
    assert latest['automatic_checks_passed']
    path, _ = review_file(case2, latest)
    with pytest.raises(ValueError, match='first run source-snapshot'):
        w.accept(case2, path)
    assert w.read_state(case2)[0]['accepted'] is None


def test_first_failed_attempt_retains_valid_lesson_decision_binding(case2):
    history = seed_lesson(case2)
    initialise(case2, lessons_path=history)
    (case2 / 'planning/tasks.md').write_text('- L0001 applied: Compare capacity before addition.\n', encoding='utf-8')
    original = (case2 / 'code/model.py').read_text()
    (case2 / 'code/model.py').write_text('raise SystemExit(7)\n')
    assert execute(case2)['status'] == 'failed'
    (case2 / 'code/model.py').write_text(original)
    receipt = execute(case2)
    path, _ = review_file(case2, receipt)
    w.accept(case2, path)
    assert w.next(case2)['action'] == 'report'


def test_first_tasks_snapshot_tampering_is_rejected(case2):
    history = seed_lesson(case2)
    initialise(case2, lessons_path=history)
    (case2 / 'planning/tasks.md').write_text('- L0001 applied: Compare capacity.\n', encoding='utf-8')
    first = execute(case2)
    (Path(first['run']) / 'source-snapshot/planning/tasks.md').write_text('- applied: L0001 Forged addition.\n')
    second = execute(case2)
    path, _ = review_file(case2, second)
    with pytest.raises(ValueError, match='does not match its receipt hashes'):
        w.accept(case2, path)
