"""Optional release case impact reports, using synthetic local cases only."""
import json
import subprocess
import sys

import pytest

from scripts import case_refresh, pipeline, release_check, workflow


def _case_manifest(tmp_path, monkeypatch, *, stale=False):
    case = tmp_path / 'case'
    for run_id, number in [('baseline', 1), ('current', 2)]:
        directory = case / 'runs' / run_id
        (directory / 'output').mkdir(parents=True)
        result = directory / 'output/results.json'
        result.write_text(json.dumps({'answer': number}), encoding='utf-8')
        (directory / 'receipt.json').write_text(json.dumps({
            'outputs': {'output/results.json': pipeline.digest(result)}}), encoding='utf-8')
    monkeypatch.setattr(pipeline, 'status', lambda _: {'runs': [{
        'run': str(case / 'runs/current'), 'usable_automatic_evidence': not stale,
        'status': 'automatic-checks-passed', 'stale': ['input'] if stale else []}]})
    manifest = tmp_path / 'cases.json'
    manifest.write_text(json.dumps({'schema': 1, 'cases': [{
        'id': 'synthetic', 'case': 'case', 'baseline_run': 'baseline'}]}), encoding='utf-8')
    return manifest


def test_numeric_change_is_reported_for_explanation_without_executing_model(tmp_path, monkeypatch, capsys):
    manifest = _case_manifest(tmp_path, monkeypatch)
    monkeypatch.setattr(workflow, 'run', lambda *a, **k: pytest.fail('No scientific execution in release dry-run'))
    destination = tmp_path / 'report'
    assert release_check.check_main_cases(manifest, workspace=tmp_path, output=destination)
    report = json.loads((destination / 'report.json').read_text())
    assert report['dry_run'] is True
    assert report['cases'][0]['numeric_delta']['changes'] == [
        {'path': '/answer', 'kind': 'number', 'old': 1, 'new': 2}]
    assert 'numbers' in report['cases'][0]['categories']
    assert 'explanation required' in capsys.readouterr().out


def test_stale_case_keeps_uncomputed_numbers_unknown_and_does_not_execute(tmp_path, monkeypatch, capsys):
    manifest = _case_manifest(tmp_path, monkeypatch, stale=True)
    monkeypatch.setattr(workflow, 'run', lambda *a, **k: pytest.fail('Do not consume the case workflow budget'))
    destination = tmp_path / 'report'
    assert release_check.check_main_cases(manifest, workspace=tmp_path, output=destination)
    row = json.loads((destination / 'report.json').read_text())['cases'][0]
    assert row['numeric_delta'] is None and row['recompute_required']
    assert 'unknown' in capsys.readouterr().out


def test_case_assessment_error_fails_release_and_preserves_report(tmp_path, monkeypatch):
    manifest = _case_manifest(tmp_path, monkeypatch)
    (tmp_path / 'case/runs/baseline/output/results.json').write_text('{"answer":999}', encoding='utf-8')
    destination = tmp_path / 'report'
    assert not release_check.check_main_cases(manifest, workspace=tmp_path, output=destination)
    report = json.loads((destination / 'report.json').read_text())
    assert report['status'] == 'failed' and 'hash' in report['cases'][0]['error']


def test_invalid_manifest_fails_without_overwriting_an_existing_report(tmp_path, monkeypatch):
    manifest = _case_manifest(tmp_path, monkeypatch)
    destination = tmp_path / 'report'
    destination.mkdir()
    original = destination / 'report.json'
    original.write_text('existing report', encoding='utf-8')
    assert not release_check.check_main_cases(manifest, workspace=tmp_path, output=destination)
    assert original.read_text() == 'existing report'
    assert not release_check.check_main_cases(tmp_path / 'missing.json', workspace=tmp_path,
                                              output=tmp_path / 'new-report')


@pytest.mark.parametrize('case_ok, expected_exit', [(True, 0), (False, 1)])
def test_cli_integrates_optional_gate_and_keeps_default_checks(monkeypatch, tmp_path, case_ok, expected_exit):
    calls = []
    monkeypatch.setattr(release_check, 'QUICK', ['first.py', 'second.py'])
    monkeypatch.setattr(release_check, 'run_demo', lambda script: calls.append(('demo', script)) or True)
    monkeypatch.setattr(release_check, 'changed_demo_files', lambda: [])
    monkeypatch.setattr(release_check, 'run', lambda command: calls.append(('tests', command)) or True)
    def assess(manifest, *, workspace, output):
        calls.append(('cases', manifest, workspace, output))
        return case_ok
    monkeypatch.setattr(release_check, 'check_main_cases', assess)
    monkeypatch.setattr(sys, 'argv', ['release_check', '--main-cases', 'cases.json', '--workspace', str(tmp_path),
                                     '--case-report', 'outputs/report'])
    assert release_check.main() == expected_exit
    assert [call[1] for call in calls if call[0] == 'demo'] == ['first.py', 'second.py']
    case_call = next(call for call in calls if call[0] == 'cases')
    assert str(case_call[1]) == 'cases.json' and case_call[2] == tmp_path
    assert str(case_call[3]) == 'outputs/report'
    assert calls[-1][0] == 'tests'


def test_default_cli_never_touches_private_case_manifest(monkeypatch):
    monkeypatch.setattr(release_check, 'QUICK', [])
    monkeypatch.setattr(release_check, 'changed_demo_files', lambda: [])
    monkeypatch.setattr(release_check, 'run', lambda _: True)
    monkeypatch.setattr(release_check, 'check_main_cases', lambda *a, **k: pytest.fail('Optional only'))
    monkeypatch.setattr(sys, 'argv', ['release_check'])
    assert release_check.main() == 0


def test_direct_script_entry_can_import_source_from_another_workspace(tmp_path):
    script = release_check.ROOT / 'scripts/release_check.py'
    command = [sys.executable, '-I', '-c',
               "import pathlib, runpy, sys; module=runpy.run_path(sys.argv[1]); "
               "assert module['check_main_cases']('missing.json', workspace=pathlib.Path.cwd(), "
               "output=pathlib.Path('new-report')) is False", str(script)]
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'FileNotFoundError' in result.stdout
    assert 'ModuleNotFoundError' not in result.stdout


@pytest.mark.parametrize('option', ['--workspace', '--case-report'])
def test_case_specific_options_require_manifest(monkeypatch, tmp_path, option):
    monkeypatch.setattr(sys, 'argv', ['release_check', option, str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        release_check.main()
    assert exc.value.code == 2
