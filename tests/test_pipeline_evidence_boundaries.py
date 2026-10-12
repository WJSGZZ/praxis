"""Reject ambiguous evidence without treating independence labels as certificates."""
import json
from pathlib import Path
import textwrap

import pytest

from test_pipeline import make_case, pipeline


def record(case, *, claims=None):
    task = {'id': 'Q1', 'question': 'Predict y=1+2*x at x=4',
            'unit': 'dimensionless', 'result_pointer': '/prediction',
            'checks': ['independent arithmetic']}
    value = {'requirements': [task]}
    if claims is not None:
        value['claims'] = claims
    pipeline.save(case / 'planning/requirements.json', value)
    return task


@pytest.mark.parametrize('checks', ['c', None, {}, [1], [True], [{}], [[]], [''], ['  ']])
def test_claim_check_references_need_a_real_string_list(checks):
    task = {'id': 'Q1'}
    claim = {'id': 'K1', 'requirement': 'Q1', 'text': 'known answer',
             'strength': 'checked', 'checks': checks}
    lookup = {'c': {'name': 'c', 'passed': True, 'evidence': 'exact arithmetic'}}
    problems = pipeline.claim_problems([task], [claim], lookup, {'prediction': 9})
    assert any('checks' in p and 'list' in p and 'strings' in p for p in problems)


@pytest.mark.parametrize('checks', [[], ['c', 'c']])
def test_legal_empty_and_repeated_claim_references_keep_their_old_meaning(checks):
    claim = {'id': 'K1', 'requirement': 'Q1', 'text': 'known answer',
             'strength': 'computed' if not checks else 'checked',
             'result_pointer': '/prediction', 'checks': checks}
    lookup = {'c': {'name': 'c', 'passed': True, 'evidence': 'exact arithmetic'}}
    assert pipeline.claim_problems([{'id': 'Q1'}], [claim], lookup, {'prediction': 9}) == []


@pytest.mark.parametrize('raw', [
    '{"passed": false, "passed": true}',
    '{"outer": {"value": 1, "value": 2}}',
    '{"passed": false, "pa\\u0073sed": true}',
])
def test_duplicate_json_keys_are_rejected_after_json_name_decoding(tmp_path, raw):
    path = tmp_path / 'ambiguous.json'
    path.write_text(raw)
    with pytest.raises(ValueError, match='Duplicate JSON key'):
        pipeline.read_json(path)


@pytest.mark.parametrize('number', ['NaN', 'Infinity', '-Infinity', '1e400'])
def test_strict_json_keeps_nonfinite_rejection(tmp_path, number):
    path = tmp_path / 'invalid.json'
    path.write_text('{"metric": ' + number + '}')
    with pytest.raises(ValueError, match='Non-finite'):
        pipeline.read_json(path)


@pytest.mark.parametrize('layer', ['case', 'results', 'checks', 'requirements'])
def test_duplicate_keys_are_refused_at_the_real_evidence_readers(tmp_path, layer):
    case, _, _ = make_case(tmp_path)
    task = record(case)
    if layer == 'case':
        path = case / 'case.json'
        path.write_text(path.read_text().replace('"schema": 1', '"schema": 999, "schema": 1', 1))
        with pytest.raises(ValueError, match='Duplicate JSON key'):
            pipeline.run_case(case)
        assert not list((case / 'runs').iterdir())
    elif layer in {'results', 'checks'}:
        raw = ('{"prediction": 0, "prediction": 9}' if layer == 'results' else
               '[{"name":"independent arithmetic","passed":false,"passed":true,"evidence":"contradictory flags"}]')
        target = 'code/model.py' if layer == 'results' else 'code/validate.py'
        script = '''import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--results');a=p.parse_args()
'''
        destination = "(a.output/'results.json')" if layer == 'results' else 'a.output'
        (case / target).write_text(script + destination + '.write_text(' + repr(raw) + ')\n')
        receipt = pipeline.run_case(case)
        assert receipt['status'] == 'failed' and not receipt['automatic_checks_passed']
        assert 'Duplicate JSON key' in receipt['error']
        assert len(receipt['steps']) == (1 if layer == 'results' else 2)
        retained = Path(receipt['run']) / ('output/results.json' if layer == 'results' else 'checks.json')
        assert retained.read_text() == raw
    else:
        path = case / 'planning/requirements.json'
        path.write_text('{"requirements": [], "requirements": ' + json.dumps([task]) + '}')
        assert pipeline.run_case(case)['automatic_checks_passed']
        with pytest.raises(ValueError, match='Duplicate JSON key'):
            pipeline.evidence_index(case)


@pytest.mark.parametrize('schema', [999, True, False, 1.0, '1', None, {}, []])
@pytest.mark.parametrize('operation', ['run', 'status', 'evidence'])
def test_unsupported_case_schema_never_reaches_usable_evidence(tmp_path, schema, operation):
    case, _, _ = make_case(tmp_path)
    record(case)
    config = pipeline.read_json(case / 'case.json')
    config['schema'] = schema
    pipeline.save(case / 'case.json', config)
    action = {'run': pipeline.run_case, 'status': pipeline.status, 'evidence': pipeline.evidence_index}[operation]
    with pytest.raises(ValueError, match='schema'):
        action(case)
    assert not list((case / 'runs').iterdir())


@pytest.mark.parametrize('has_schema', [True, False])
def test_known_v1_and_missing_legacy_marker_keep_read_only_compatibility(tmp_path, has_schema):
    case, _, _ = make_case(tmp_path)
    record(case)
    config = pipeline.read_json(case / 'case.json')
    if not has_schema:
        del config['schema']
        pipeline.save(case / 'case.json', config)
    before = (case / 'case.json').read_bytes()
    assert pipeline.run_case(case)['automatic_checks_passed']
    assert pipeline.status(case)['runs'][-1]['usable_automatic_evidence']
    assert pipeline.evidence_index(case)['status'] == 'evidence-linked'
    assert (case / 'case.json').read_bytes() == before


def test_shared_definition_import_and_same_method_family_still_allow_known_answer(tmp_path):
    case, _, _ = make_case(tmp_path)
    model = case / 'code/model.py'
    head, body = model.read_text().split('p=argparse.ArgumentParser()', 1)
    body = ('p=argparse.ArgumentParser()' + body).replace("{'prediction':", "{'method_family':'affine-evaluation','prediction':")
    model.write_text(head + "\nUNIT='dimensionless'\ndef main():\n" + textwrap.indent(body, '    ')
                     + "\nif __name__=='__main__':\n    main()\n")
    validator = case / 'code/validate.py'
    validator.write_text('from model import UNIT\n' + validator.read_text().replace(
        "'passed':ok", "'passed':ok,'independent':True,'method_family':'affine-evaluation','unit':UNIT"))
    record(case, claims=[{'id': 'K1', 'requirement': 'Q1', 'text': 'prediction9',
                         'strength': 'independent', 'result_pointer': '/prediction',
                         'checks': ['independent arithmetic']}])
    receipt = pipeline.run_case(case)
    assert receipt['automatic_checks_passed']
    results = pipeline.read_json(Path(receipt['run']) / 'output/results.json')
    checks = pipeline.read_json(Path(receipt['run']) / 'checks.json')
    assert results['prediction'] == pytest.approx(9)
    assert results['method_family'] == checks[0]['method_family']
    report = pipeline.evidence_index(case)
    assert report['status'] == 'evidence-linked' and not report['paper_ready']
