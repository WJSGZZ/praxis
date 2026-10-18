"""Generic refresh contracts; synthetic cases, never private scientific data."""
import json
from pathlib import Path

import pytest

from scripts import case_refresh as cr


def test_compare_preserves_types_large_integers_and_json_pointer_escaping():
    old = {'a/b': {'~x': [True, 2**60, 1.0]}, 'removed': 4}
    new = {'a/b': {'~x': [1, 2**60 + 1, 1.00001]}, 'added': None}
    report = cr.compare_results(old, new, {'absolute': 0.0001, 'relative': 0})
    changes = {x['path']: x for x in report['changes']}
    assert set(changes) == {'/a~1b/~0x/0', '/a~1b/~0x/1', '/removed', '/added'}
    assert changes['/a~1b/~0x/0']['kind'] == 'type'
    assert changes['/a~1b/~0x/1']['new'] - changes['/a~1b/~0x/1']['old'] == 1
    assert report['within_tolerance'] == 1
    assert report['ignored_paths'] == []


@pytest.mark.parametrize('tolerances', [{'absolute': -1}, {'relative': True}, {'absolute': float('inf')}])
def test_comparison_rejects_bad_tolerances(tolerances):
    with pytest.raises(ValueError):
        cr.compare_results({'x': 1}, {'x': 1}, tolerances)


def test_comparison_ignores_only_explicit_paths_and_rejects_nonfinite():
    r = cr.compare_results({'created_utc': 'old', 'x': 1}, {'created_utc': 'new', 'x': 2},
                           {'ignore_paths': ['/created_utc']})
    assert [x['path'] for x in r['changes']] == ['/x']
    assert r['ignored_paths'] == ['/created_utc']
    with pytest.raises(ValueError, match='finite'):
        cr.compare_results({'x': float('nan')}, {'x': 2})


def test_threshold_and_identity_conclusion_changes_are_separate_from_numeric_differences():
    checks = [{'id': 'resource', 'pointer': '/npv', 'operator': 'gt', 'threshold': 0},
              {'id': 'policy', 'pointer': '/policy', 'operator': 'identity'}]
    assert cr.conclusion_changes({'npv': 2, 'policy': 'P1'}, {'npv': 3, 'policy': 'P1'}, checks) == []
    changed = cr.conclusion_changes({'npv': 2, 'policy': 'P1'}, {'npv': -1, 'policy': 'P2'}, checks)
    assert [x['id'] for x in changed] == ['resource', 'policy']
    with pytest.raises(ValueError, match='missing'):
        cr.conclusion_changes({'npv': 1}, {}, checks)


def test_manifest_rejects_escape_duplicate_cases_and_symlinks(tmp_path):
    outside = tmp_path.parent / 'not-a-case'
    for entries in [[{'id': '../../escape', 'case': 'case', 'baseline_run': 'r0'}],
                    [{'id': 'a', 'case': '../not-a-case'}],
                    [{'id': 'a', 'case': 'c'}, {'id': 'a', 'case': 'd'}]]:
        with pytest.raises(ValueError):
            cr.load_manifest({'schema': 1, 'cases': entries}, tmp_path)
    (tmp_path/'link').symlink_to(outside)
    with pytest.raises(ValueError, match='[Ss]ymlink'):
        cr.load_manifest({'schema': 1, 'cases': [{'id': 'a', 'case': 'link'}]}, tmp_path)


def test_dry_run_never_computes_future_numbers_and_execution_keeps_failure(tmp_path, monkeypatch):
    case = tmp_path/'case'; (case/'runs/r0/output').mkdir(parents=True)
    (case/'case.json').write_text('{"schema":1}')
    (case/'planning').mkdir(); (case/'planning/tasks.md').write_text('Synthetic task')
    result = case/'runs/r0/output/results.json'; result.write_text('{"npv":1}')
    from scripts import pipeline, workflow
    receipt = {'outputs': {'output/results.json': pipeline.digest(result)}}
    (case/'runs/r0/receipt.json').write_text(json.dumps(receipt))
    monkeypatch.setattr(pipeline, 'status', lambda path: {'runs': [{'run': str(case/'runs/r0'),
                    'stale': ['actual-input'], 'status': 'automatic-checks-passed',
                    'usable_automatic_evidence': False}]})
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(args)
        raise ValueError('Insufficient remaining budget')
    monkeypatch.setattr(workflow, 'run', forbidden)
    manifest = {'schema': 1, 'cases': [{'id': 'a', 'case': 'case', 'baseline_run': 'r0'}]}
    plan = cr.refresh(manifest, workspace=tmp_path, dry_run=True)
    row = plan['cases'][0]
    assert not calls and row['recompute_required'] is True
    assert row['numeric_delta'] is None and 'unknown' in row['categories']
    actual = cr.refresh(manifest, workspace=tmp_path, dry_run=False)
    assert len(calls) == 1
    assert actual['cases'][0]['execution']['status'] == 'failed'
    assert 'budget' in actual['cases'][0]['execution']['error']
    assert result.read_text() == '{"npv":1}'


def test_compare_current_result_and_explain_guidance_without_running_model(tmp_path, monkeypatch):
    from scripts import pipeline
    case = tmp_path/'case'
    for run, value in [('r0', 1), ('r1', -2)]:
        directory = case/f'runs/{run}'; (directory/'output').mkdir(parents=True)
        result = directory/'output/results.json'; result.write_text(json.dumps({'npv': value, 'policy': 'P1'}))
        (directory/'receipt.json').write_text(json.dumps({'outputs': {'output/results.json': pipeline.digest(result)}}))
    (case/'case.json').write_text('{"schema":1}')
    monkeypatch.setattr(pipeline, 'status', lambda p: {'runs': [{'run': str(case/'runs/r1'),
                  'stale': [], 'status': 'automatic-checks-passed', 'usable_automatic_evidence': True}]})
    guidance = tmp_path/'guidance.md'; guidance.write_text('Use matched baselines.')
    manifest = {'schema': 1, 'cases': [{'id': 'a', 'case': 'case', 'baseline_run': 'r0',
       'conclusions': [{'id': 'resource', 'pointer': '/npv', 'operator': 'gt', 'threshold': 0}],
       'guidance': [{'path': 'guidance.md', 'sha256': '0'*64, 'rule': 'matched-baseline',
                     'locations': ['Section 4'], 'suggestion': 'Check comparison inputs.'}]}]}
    row = cr.refresh(manifest, workspace=tmp_path)['cases'][0]
    assert {'numbers', 'conclusions', 'guidance'} <= set(row['categories'])
    assert row['auto_revision_allowed'] is False
    assert row['guidance_changes'][0]['locations'] == ['Section 4']
    assert row['numeric_delta']['changes'][0]['path'] == '/npv'


def test_latest_failed_attempt_is_not_hidden_by_older_success(tmp_path, monkeypatch):
    from scripts import pipeline
    case = tmp_path/'case'; (case/'runs/r0/output').mkdir(parents=True)
    result = case/'runs/r0/output/results.json'; result.write_text('{"x":1}')
    (case/'runs/r0/receipt.json').write_text(json.dumps({'outputs': {'output/results.json': pipeline.digest(result)}}))
    monkeypatch.setattr(pipeline, 'status', lambda p: {'runs': [
        {'run': str(case/'runs/r0'), 'stale': [], 'status': 'automatic-checks-passed', 'usable_automatic_evidence': True},
        {'run': str(case/'runs/r1'), 'stale': [], 'status': 'failed', 'usable_automatic_evidence': False}]})
    row = cr.refresh({'schema': 1, 'cases': [{'id': 'a', 'case': 'case', 'baseline_run': 'r0'}]}, workspace=tmp_path)['cases'][0]
    assert row['recompute_required'] is True and row['numeric_delta'] is None
    assert row['latest']['status'] == 'failed'


def test_paper_driver_requires_reviewed_bytes_and_preserves_existing_output(tmp_path):
    from scripts import pipeline
    driver=tmp_path/'build.py'
    driver.write_text("import argparse\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument('--case');p.add_argument('--run-id');p.add_argument('--output',type=Path);a=p.parse_args();a.output.mkdir();(a.output/'paper.tex').write_text(a.run_id)\n")
    destination=tmp_path/'revision'
    spec={'path':'build.py','sha256':'0'*64}
    with pytest.raises(ValueError,match='[Hh]ash'):
        cr.run_paper_driver(spec,tmp_path,'run1',destination,tmp_path)
    assert not destination.exists()
    spec['sha256']=pipeline.digest(driver)
    cr.run_paper_driver(spec,tmp_path,'run1',destination,tmp_path)
    assert (destination/'paper.tex').read_text()=='run1'
    with pytest.raises(FileExistsError):
        cr.run_paper_driver(spec,tmp_path,'run2',destination,tmp_path)
    assert (destination/'paper.tex').read_text()=='run1'
