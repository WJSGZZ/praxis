"""Boundary tests for optional feedback, using synthetic local material only."""
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

import pytest
from scripts import feedback, pipeline


def event(kind='stage', **extra):
    return {'type': kind, 'phase': 'research', 'actor': 'executor', 'description': 'Actual synthetic operation', 'source': 'assistant-recorded', **extra}


@pytest.mark.parametrize('number', ['NaN', 'Infinity', '-Infinity', '1e999', '-1e999'])
def test_nonfinite_json_is_rejected_even_when_number_uses_valid_exponent_syntax(number):
    with pytest.raises(ValueError, match='Non-finite'):
        feedback.loads('{"cost": {"tokens": {"value": ' + number + ', "source": "artifact"}}}')
    assert feedback.loads('{"seconds": 1.25e2}') == {'seconds': 125.0}


def make_local(tmp_path, status='completed'):
    case = tmp_path / 'legacy-case'
    case.mkdir()
    (case / 'model.py').write_text('print(9)\n')
    (case / 'results.json').write_text('{"prediction": 9}\n')
    feedback.init(case, mode='autonomous', goal='Synthetic feedback boundary check')
    feedback.record(case, event('stop'), status=status)
    return case


@pytest.mark.parametrize('status', ['completed', 'failed', 'timeout', 'interrupted', 'budget-exhausted', 'user-stopped'])
def test_stop_states_unknown_identity_missing_pdf_and_directory_zip_equivalence(tmp_path, status):
    case = make_local(tmp_path, status)
    feedback.record(case, event('review', candidate_id='candidate-1'))
    feedback.record(case, event('intervention', intervention_kind='environment-assistance', source='user-provided'))
    stage = tmp_path / 'share'
    result = feedback.stage(case, stage, ['model.py', 'results.json', 'absent.pdf'], exclusions=['private chat: permission not granted'])
    assert result['inspection']['status'] == status
    assert 'identity.reported_model' in result['inspection']['unknown_fields']
    assert any('No PDF' in value for value in result['inspection']['missing'])
    assert 'Selected file missing: absent.pdf' in result['inspection']['missing']
    assert result['inspection']['interventions'][0]['source'] == 'user-provided'
    assert not result['inspection']['complete_task_certified']
    archive = tmp_path / 'share.zip'
    feedback.pack(stage, archive, confirm_manifest_sha256=result['manifest_sha256'])
    assert feedback.inspect(stage) == feedback.inspect(archive)


def test_explicit_selection_literal_redaction_separate_hashes_and_original_preservation(tmp_path):
    case = make_local(tmp_path)
    path_literal = '/Users/SyntheticPerson/Projects/Case'
    (case / 'receipt.json').write_text(json.dumps({'path': path_literal + '/model.py', 'number': 9, 'status': 'failed'}))
    (case / '.env').write_text('API_KEY=FAKE-DO-NOT-SHARE')
    (case / 'other-case').mkdir()
    (case / 'other-case' / 'secret.txt').write_text('ANOTHER-CASE-NOT-SELECTED')
    feedback.record(case, event('failure', description='Failed at ' + path_literal))
    originals = {str(p.relative_to(case)): p.read_bytes() for p in case.rglob('*') if p.is_file()}
    result = feedback.stage(case, tmp_path / 'share', ['receipt.json'], aliases={path_literal: '<WORKSPACE>'}, exclusions=['.env: credentials', 'other-case: unrelated'])
    manifest = json.loads((tmp_path / 'share' / 'manifest.json').read_text())
    shared = (tmp_path / 'share' / 'files/receipt.json').read_bytes()
    assert path_literal.encode() not in shared
    assert json.loads(shared)['number'] == 9
    assert json.loads(shared)['status'] == 'failed'
    assert manifest['files'][0]['original_sha256'] == hashlib.sha256(originals['receipt.json']).hexdigest()
    assert manifest['files'][0]['sha256'] == hashlib.sha256(shared).hexdigest()
    assert manifest['files'][0]['original_sha256'] != manifest['files'][0]['sha256']
    assert '<WORKSPACE>' in manifest['events'][-1]['description']
    archive = tmp_path / 'share.zip'
    feedback.pack(tmp_path / 'share', archive, confirm_manifest_sha256=result['manifest_sha256'])
    with zipfile.ZipFile(archive) as zipped:
        assert set(zipped.namelist()) == {'manifest.json', 'summary.md', 'files/receipt.json'}
        all_bytes = b''.join(zipped.read(name) for name in zipped.namelist())
        assert b'FAKE-DO-NOT-SHARE' not in all_bytes
        assert b'ANOTHER-CASE-NOT-SELECTED' not in all_bytes
        assert path_literal.encode() not in all_bytes
    assert originals == {str(p.relative_to(case)): p.read_bytes() for p in case.rglob('*') if p.is_file()}


def test_pack_requires_confirmation_of_actual_reviewed_manifest(tmp_path):
    case = make_local(tmp_path)
    result = feedback.stage(case, tmp_path / 'share', ['model.py'])
    with pytest.raises(ValueError, match='confirmation'):
        feedback.pack(tmp_path / 'share', tmp_path / 'bad.zip', confirm_manifest_sha256='0' * 64)
    assert not (tmp_path / 'bad.zip').exists()
    (tmp_path / 'share' / 'files/model.py').write_text('changed')
    with pytest.raises(ValueError, match='mismatch'):
        feedback.pack(tmp_path / 'share', tmp_path / 'bad.zip', confirm_manifest_sha256=result['manifest_sha256'])


def test_inspection_rejects_corrupt_hash_in_both_readers(tmp_path):
    case = make_local(tmp_path)
    feedback.stage(case, tmp_path / 'share', ['model.py'])
    manifest = json.loads((tmp_path / 'share' / 'manifest.json').read_text())
    manifest['files'][0]['sha256'] = '0' * 64
    (tmp_path / 'share' / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='mismatch'):
        feedback.inspect(tmp_path / 'share')
    archive = tmp_path / 'corrupt.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        for name in ['manifest.json', 'summary.md', 'files/model.py']:
            zipped.writestr(name, (tmp_path / 'share' / name).read_bytes())
    with pytest.raises(ValueError, match='mismatch'):
        feedback.inspect(archive)


@pytest.mark.parametrize('name', ['../outside.txt', '/outside.txt', 'a/../../b', 'a\\b', 'C:/outside.txt', 'a//b', 'a/./b'])
def test_zip_traversal_is_rejected_before_any_attachment_read(tmp_path, name):
    archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(name, 'not read')
    with pytest.raises(ValueError, match='path'):
        feedback.inspect(archive)
    assert not (tmp_path / 'outside.txt').exists()


def test_zip_symlinks_duplicate_members_and_abnormal_size_rejected(tmp_path, monkeypatch):
    archive = tmp_path / 'bad.zip'
    info = zipfile.ZipInfo('link')
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(info, '/outside')
    with pytest.raises(ValueError, match='Non-regular'):
        feedback.inspect(archive)
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('duplicate', 'a')
        with pytest.warns(UserWarning):
            zipped.writestr('duplicate', 'b')
    with pytest.raises(ValueError, match='Duplicate ZIP'):
        feedback.inspect(archive)
    monkeypatch.setattr(feedback, 'MAX_FILE_BYTES', 8)
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('large', b'a' * 9)
    with pytest.raises(ValueError, match='expansion'):
        feedback.inspect(archive)


def test_zip_undeclared_safe_members_are_not_read_or_executed(tmp_path, monkeypatch):
    case = make_local(tmp_path)
    feedback.stage(case, tmp_path / 'share')
    archive = tmp_path / 'extra.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('manifest.json', (tmp_path / 'share/manifest.json').read_bytes())
        zipped.writestr('summary.md', (tmp_path / 'share/summary.md').read_bytes())
        zipped.writestr('run-me.py', 'raise RuntimeError("must never execute")')
    original = zipfile.ZipFile.read
    read_names = []
    def trace_read(self, name, *args, **kwargs):
        read_names.append(name.filename if isinstance(name, zipfile.ZipInfo) else name)
        return original(self, name, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, 'read', trace_read)
    report = feedback.inspect(archive)
    assert report['unread_members'] == ['run-me.py']
    assert 'run-me.py' not in read_names


def test_stage_symlink_sensitive_path_and_outside_rejection(tmp_path):
    case = make_local(tmp_path)
    (case / 'link.py').symlink_to(case / 'model.py')
    for name in ['link.py', '../outside', '.env', '.venv/config.json']:
        with pytest.raises(ValueError):
            feedback.stage(case, tmp_path / 'share', [name])
        assert not (tmp_path / 'share').exists()
    with pytest.raises(ValueError, match='outside'):
        feedback.stage(case, case / 'share')
    with pytest.raises(ValueError, match='Aliases'):
        feedback.stage(case, tmp_path / 'share', ['model.py'], aliases={'9': '<VALUE>'})


def test_identity_requires_actual_source_and_unknown_remains_unknown(tmp_path):
    case = tmp_path / 'case'; case.mkdir()
    with pytest.raises(ValueError, match='Unknown source'):
        feedback.init(case, metadata={'identity': {'reported_model': feedback.known('invented-model')}})
    assert not (case / 'feedback').exists()
    manifest = feedback.init(case, metadata={'identity': {'requested_model': feedback.known('user-selection', 'ui-setting')}})
    assert manifest['identity']['reported_model'] == feedback.known()
    assert manifest['identity']['requested_model']['source'] == 'ui-setting'
    with pytest.raises(ValueError, match='Candidate'):
        feedback.record(case, event('review'))
    with pytest.raises(ValueError, match='Intervention'):
        feedback.record(case, event('intervention'))


@pytest.mark.parametrize('group', ['identity', 'exposure', 'cost', 'user_observation'])
def test_required_source_fields_cannot_disappear_even_when_unknown(tmp_path, group):
    case = tmp_path / 'case'; case.mkdir()
    manifest = feedback.init(case)
    assert set(feedback.SOURCED_FIELDS[group]) <= set(manifest[group])
    assert all(manifest[group][name] == feedback.known() for name in feedback.SOURCED_FIELDS[group])
    manifest[group] = {}
    with pytest.raises(ValueError, match='Missing sourced field: ' + group):
        feedback.validate_manifest(manifest)
    (case / 'feedback/manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='Missing sourced field: ' + group):
        feedback.inspect(case)


def test_omitted_reported_model_is_rejected_by_directory_and_zip(tmp_path):
    case = make_local(tmp_path)
    share = tmp_path / 'share'; feedback.stage(case, share)
    path = share / 'manifest.json'
    manifest = json.loads(path.read_text())
    del manifest['identity']['reported_model']
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='identity.reported_model'):
        feedback.inspect(share)
    archive = tmp_path / 'missing-identity.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('manifest.json', path.read_bytes())
        zipped.writestr('summary.md', (share / 'summary.md').read_bytes())
    with pytest.raises(ValueError, match='identity.reported_model'):
        feedback.inspect(archive)


@pytest.mark.parametrize('started,ended', [
    ('2026-10-09T10:00:00+00:00', '2026-10-09T09:00:00+00:00'),
    ('2026-10-09T10:00:00+00:00', '2026-10-09T10:30:00+01:00'),
])
def test_end_before_start_rejected_using_actual_time_not_timestamp_text(tmp_path, started, ended):
    case = tmp_path / 'case'; case.mkdir()
    with pytest.raises(ValueError, match='must not precede'):
        feedback.init(case, metadata={'started_utc': started, 'ended_utc': ended, 'status': 'failed'})
    assert not (case / 'feedback').exists()


@pytest.mark.parametrize('started,ended', [
    ('2026-10-09T10:00:00+00:00', '2026-10-09T10:00:00+00:00'),
    ('2026-10-09T10:00:00+08:00', '2026-10-09T02:00:00Z'),
    ('2026-10-09T10:00:00+01:00', '2026-10-09T09:30:00Z'),
    ('unknown', '2000-01-01T00:00:00+00:00'),
    ('2026-10-09T10:00:00+00:00', 'unknown'),
    ('unknown', 'unknown'),
])
def test_equal_ordered_or_genuinely_unknown_times_remain_valid(tmp_path, started, ended):
    case = tmp_path / 'case'; case.mkdir()
    manifest = feedback.init(case, metadata={'started_utc': started, 'ended_utc': ended, 'status': 'failed'})
    assert feedback.validate_manifest(manifest) is manifest
    report = feedback.inspect(case)
    assert report['started_utc'] == started
    assert report['ended_utc'] == ended
    assert not report['complete_task_certified']


def test_invalid_stop_never_persists_and_unknown_start_allows_historical_stop(tmp_path):
    case = tmp_path / 'case'; case.mkdir()
    feedback.init(case, metadata={'started_utc': '2026-10-09T10:00:00+00:00'})
    path = case / 'feedback/manifest.json'; before = path.read_bytes()
    with pytest.raises(ValueError, match='must not precede'):
        feedback.record(case, event('stop', at_utc='2026-10-09T09:00:00+00:00'), status='failed')
    assert path.read_bytes() == before
    feedback.record(case, event('stop', at_utc='2026-10-09T10:00:00+00:00'), status='failed')
    assert feedback.inspect(case)['ended_utc'] == '2026-10-09T10:00:00+00:00'
    legacy = tmp_path / 'legacy'; legacy.mkdir()
    feedback.init(legacy, metadata={'started_utc': 'unknown'})
    feedback.record(legacy, event('stop', at_utc='2000-01-01T00:00:00+00:00'), status='failed')
    assert feedback.inspect(legacy)['ended_utc'] == '2000-01-01T00:00:00+00:00'


@pytest.mark.parametrize('kind', ['review', 'candidate', 'acceptance', 'revision'])
@pytest.mark.parametrize('candidate', ['', ' \n\t'])
def test_empty_or_whitespace_candidate_ids_do_not_persist(tmp_path, kind, candidate):
    case = tmp_path / 'case'; case.mkdir(); feedback.init(case)
    path = case / 'feedback/manifest.json'; before = path.read_bytes()
    with pytest.raises(ValueError, match='Candidate identity required'):
        feedback.record(case, event(kind, candidate_id=candidate))
    assert path.read_bytes() == before
    feedback.record(case, event(kind, candidate_id='draft-1'))
    assert feedback.inspect(case)['events'][-1]['candidate_id'] == 'draft-1'


def test_local_legacy_case_adapts_without_pipeline_and_missing_fields_are_explicit(tmp_path):
    original = tmp_path / 'untouched-legacy'; original.mkdir()
    (original / 'legacy-notes.txt').write_text('Existing custom case')
    before = (original / 'legacy-notes.txt').read_bytes()
    assert feedback.inspect(original)['coverage'] == 'legacy directory; no feedback descriptor'
    assert (original / 'legacy-notes.txt').read_bytes() == before
    assert not (original / 'feedback').exists()
    case = make_local(tmp_path)
    report = feedback.inspect(case)
    assert 'Share summary not recorded; local/legacy descriptor only.' in report['missing']
    assert report['verified_files'] == []
    assert not report['reproducibility_certified']
    assert 'exposure.pretraining_exposure' in report['unknown_fields']


@pytest.mark.parametrize('model,expected', [('raise SystemExit(3)', 'failed'), ('import time; time.sleep(3)', 'timeout')])
def test_actual_pipeline_failure_and_timeout_can_export_without_pdf(tmp_path, model, expected):
    problem = tmp_path / 'problem.md'; problem.write_text('Synthetic failure boundary')
    case = Path(pipeline.init_case(tmp_path / 'cases', 'failure', problem, [])['case'])
    (case / 'code/model.py').write_text(model)
    (case / 'code/validate.py').write_text('raise RuntimeError("must not reach validation")')
    receipt = pipeline.run_case(case, timeout=1)
    assert receipt['status'] == 'failed'
    if expected == 'timeout':
        assert 'TimeoutExpired' in receipt['error']
    feedback.init(case)
    feedback.record(case, event('failure', source='artifact', description=receipt.get('error', 'Model exit recorded in receipt')), status=expected)
    relative = (Path(receipt['run']) / 'receipt.json').relative_to(case).as_posix()
    result = feedback.stage(case, tmp_path / 'share', [relative])
    assert result['inspection']['status'] == expected
    archive = tmp_path / 'failure.zip'
    feedback.pack(tmp_path / 'share', archive, confirm_manifest_sha256=result['manifest_sha256'])
    assert feedback.inspect(archive) == feedback.inspect(tmp_path / 'share')


def test_computation_before_start_failure_is_exportable_and_resume_clears_end(tmp_path):
    case = tmp_path / 'case'; case.mkdir()
    feedback.init(case)
    feedback.record(case, event('failure', description='Synthetic missing required input before model execution'), status='failed')
    result = feedback.stage(case, tmp_path / 'share')
    assert result['inspection']['status'] == 'failed'
    assert result['inspection']['verified_files'] == []
    feedback.record(case, event('resume'), status='running')
    assert feedback.inspect(case)['ended_utc'] == 'unknown'


def test_pipeline_real_run_feedback_does_not_stale_but_inputs_still_do(tmp_path):
    problem = tmp_path / 'problem.md'; problem.write_text('Synthetic: compute 1+2*4')
    case = Path(pipeline.init_case(tmp_path / 'cases', 'feedback', problem, [])['case'])
    (case / 'code/model.py').write_text('''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
(a.output/'results.json').write_text(json.dumps({'answer':9}))
''')
    (case / 'code/validate.py').write_text('''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--results',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
r=json.loads(a.results.read_text());ok=r['answer']==1+2*4
a.output.write_text(json.dumps([{'name':'independent arithmetic','passed':ok,'evidence':'1+2*4=9'}]))
raise SystemExit(0 if ok else 1)
''')
    receipt = pipeline.run_case(case)
    assert receipt['status'] == 'automatic-checks-passed'
    snapshot = pipeline.source_snapshot(case)
    receipt_path = Path(receipt['run']) / 'receipt.json'
    original_receipt = receipt_path.read_bytes()
    feedback.init(case, mode='autonomous')
    feedback.record(case, event('stop'), status='completed')
    (case / 'contributions.jsonl').write_text('{"synthetic":"feedback contribution"}\n')
    relative_receipt = receipt_path.relative_to(case).as_posix()
    feedback.stage(case, tmp_path / 'share', [relative_receipt])
    assert pipeline.source_snapshot(case) == snapshot
    assert receipt_path.read_bytes() == original_receipt
    assert pipeline.status(case)['runs'][0]['usable_automatic_evidence']
    raw = case / 'raw/problem/problem.md'; raw.chmod(0o644); raw.write_text('changed actual input')
    assert not pipeline.status(case)['runs'][0]['usable_automatic_evidence']
    assert pipeline.status(case)['raw_input_changes']


def test_cli_external_case_and_error_status(tmp_path):
    case = tmp_path / 'external'; case.mkdir()
    script = Path(feedback.__file__)
    result = subprocess.run([sys.executable, str(script), 'init', '--case', str(case), '--mode', 'autonomous'], capture_output=True, text=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)['schema'] == feedback.SCHEMA
    result = subprocess.run([sys.executable, str(script), 'inspect', str(case)], capture_output=True, text=True)
    assert result.returncode == 0
    assert not json.loads(result.stdout)['complete_task_certified']
    result = subprocess.run([sys.executable, str(script), 'pack', '--source', str(case), '--output', str(tmp_path / 'x.zip'), '--confirm-manifest-sha256', '0'*64], capture_output=True, text=True)
    assert result.returncode == 2
    (case / 'result.json').write_text('{"answer":9}')
    event_file = tmp_path / 'actual-event.json'; event_file.write_text(json.dumps(event('stop')))
    result = subprocess.run([sys.executable, str(script), 'record', '--case', str(case), '--event', str(event_file), '--status', 'completed'], capture_output=True, text=True)
    assert result.returncode == 0
    share = tmp_path / 'share'
    result = subprocess.run([sys.executable, str(script), 'stage', '--case', str(case), '--output', str(share), '--include', 'result.json'], capture_output=True, text=True)
    assert result.returncode == 0
    staged = json.loads(result.stdout)
    archive = tmp_path / 'feedback.zip'
    result = subprocess.run([sys.executable, str(script), 'pack', '--source', str(share), '--output', str(archive), '--confirm-manifest-sha256', staged['manifest_sha256']], capture_output=True, text=True)
    assert result.returncode == 0
    result = subprocess.run([sys.executable, str(script), 'inspect', str(archive)], capture_output=True, text=True)
    assert result.returncode == 0
    assert json.loads(result.stdout) == feedback.inspect(share)
