"""Observed Python dependencies are opt-in, never a claim of OS I/O isolation."""
import json
from pathlib import Path
import pytest
from scripts import pipeline


def make(tmp_path, monkeypatch, extra='', validation=''):
    monkeypatch.setattr(pipeline, 'PROJECT', tmp_path)
    p=tmp_path/'problem.txt';p.write_text('Synthetic arithmetic')
    case=Path(pipeline.init_case(tmp_path/'cases','trace',p,schema=1)['case'])
    (case/'code/config.json').write_text('{"x": 3}')
    (case/'code/helper.py').write_text('VALUE = 3\n')
    (case/'code/model.py').write_text('''import argparse,json,importlib.util
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
c=json.loads(Path('code/config.json').read_text())
s=importlib.util.spec_from_file_location('unregistered', 'code/helper.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
'''+extra+"\n(a.output/'results.json').write_text(json.dumps({'x':c['x']+m.VALUE}))\n")
    (case/'code/validate.py').write_text('''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--results',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
r=json.loads(a.results.read_text())
'''+validation+"\na.output.write_text(json.dumps([{'name':'sum','passed':r['x']==6,'evidence':'3+3=6'}]))\n")
    return case


def run(case):return pipeline.run_case(case, dependency_mode='python-reviewed')
def latest(case):return pipeline.status(case)['runs'][-1]


def test_actual_reads_allow_unused_code_and_bundle_edits(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch);r=run(c)
    assert r['actual_dependencies']['mode']=='python-reviewed'
    assert latest(c)['usable_automatic_evidence']
    (c/'code/unused.json').write_text('{}')
    (c/'code/not_imported.py').write_text('VALUE=999\n')
    monkeypatch.setattr(pipeline,'dependency_snapshot',lambda: dict(r['dependencies'], **{'scripts/unused.py':'a'*64}))
    assert latest(c)['usable_automatic_evidence']


@pytest.mark.parametrize('path', ['code/config.json','code/helper.py','code/validate.py'])
def test_actual_json_validator_and_unregistered_import_changes_stale(tmp_path,monkeypatch,path):
    c=make(tmp_path,monkeypatch);r=run(c);assert latest(c)['usable_automatic_evidence']
    p=c/path;p.write_text(p.read_text()+'\n ')
    assert not latest(c)['usable_automatic_evidence']


def test_failed_model_keeps_partial_trace(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch,extra='raise RuntimeError("deliberate")')
    r=run(c);assert r['status']=='failed'
    trace=json.loads((Path(r['run'])/'model.trace.json').read_text())
    assert any(p['logical_path'].endswith('config.json') for p in trace['files'])
    assert trace['completed'] is False


def test_symlink_retarget_even_equal_bytes_is_stale(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch);p=c/'code/config.json';p.rename(c/'code/one.json');p.symlink_to('one.json')
    (c/'code/two.json').write_bytes((c/'code/one.json').read_bytes());run(c)
    assert latest(c)['usable_automatic_evidence'];p.unlink();p.symlink_to('two.json')
    assert not latest(c)['usable_automatic_evidence']


def test_generated_stage_intermediate_not_required_before_run(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch,extra="(a.output/'intermediate.json').write_text('{\"v\":3}')", validation="assert json.loads((a.results.parent/'intermediate.json').read_text())['v']==3")
    r=run(c);assert latest(c)['usable_automatic_evidence']
    traces=[json.loads((Path(r['run'])/s['trace_path']).read_text()) for s in r['actual_dependencies']['stages']]
    assert any(p['role']=='generated' and p['producer_stage']=='model' for t in traces for p in t['files'] if p['logical_path'].endswith('intermediate.json'))


def test_during_run_input_mutation_fails(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch,extra="Path('code/config.json').write_text('{\"x\":4}')")
    assert run(c)['status']=='failed'


def test_subprocess_falls_back_to_conservative(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch,extra="import subprocess,sys\nsubprocess.run([sys.executable,'-c','pass'],check=True)")
    r=run(c);assert r['actual_dependencies']['mode']=='conservative'
    assert any('subprocess' in str(x) for x in r['actual_dependencies']['coverage']['uncovered'])
    (c/'code/unused.json').write_text('{}');assert not latest(c)['usable_automatic_evidence']


def test_validator_only_json_and_missing_conditional_input(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch,extra="if Path('code/conditional.json').exists():\n    json.loads(Path('code/conditional.json').read_text())",validation="assert json.loads(Path('code/review.json').read_text())['ok']")
    (c/'code/review.json').write_text('{"ok":true}');run(c)
    assert latest(c)['usable_automatic_evidence']
    (c/'code/conditional.json').write_text('{}');assert not latest(c)['usable_automatic_evidence']
    run(c);assert latest(c)['usable_automatic_evidence']
    (c/'code/review.json').write_text('{"ok": true, "note": "changed"}');assert not latest(c)['usable_automatic_evidence']


def test_existing_pyc_and_external_module_are_bound(tmp_path,monkeypatch):
    import py_compile
    c=make(tmp_path,monkeypatch)
    source=tmp_path/'external.py';source.write_text('VALUE=8\n')
    pyc=tmp_path/'external.pyc';py_compile.compile(str(source),cfile=str(pyc),doraise=True)
    model=c/'code/model.py';model.write_text(model.read_text()+f"\ns=importlib.util.spec_from_file_location('external_unregistered', {str(pyc)!r});m2=importlib.util.module_from_spec(s);s.loader.exec_module(m2)\nassert m2.VALUE==8\n")
    r=run(c);assert latest(c)['usable_automatic_evidence']
    tr=json.loads((Path(r['run'])/'model.trace.json').read_text())
    assert any(p['logical_path']==str(pyc) and p['read'] for p in tr['files'])
    pyc.write_bytes(pyc.read_bytes()+b'changed');assert not latest(c)['usable_automatic_evidence']


def test_timeout_retains_unfinished_trace_and_falls_back(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch,extra='import time;time.sleep(3)')
    r=pipeline.run_case(c,timeout=1,dependency_mode='python-reviewed')
    assert r['status']=='failed' and r['actual_dependencies']['mode']=='conservative'
    tr=json.loads((Path(r['run'])/'model.trace.json').read_text())
    assert tr['finalized'] is False and tr['files']


def test_case_mode_config_and_legacy_conservative_binding(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch);p=c/'case.json';conf=json.loads(p.read_text());conf['dependency_mode']='python-reviewed';p.write_text(json.dumps(conf))
    r=pipeline.run_case(c);assert r['actual_dependencies']['mode']=='python-reviewed'
    p=Path(r['run'])/'receipt.json';raw=json.loads(p.read_text());del raw['actual_dependencies'];p.write_text(json.dumps(raw))
    (c/'code/unused.json').write_text('{}');assert not latest(c)['usable_automatic_evidence']


def test_used_environment_and_directory_membership_are_bound(tmp_path,monkeypatch):
    monkeypatch.setenv('PRAXIS_TRACE_CONFIG','first')
    c=make(tmp_path,monkeypatch,extra="import os\nassert os.environ['PRAXIS_TRACE_CONFIG']\nassert list(Path('code/options').glob('*.json'))")
    (c/'code/options').mkdir();(c/'code/options/one.json').write_text('{}')
    run(c);assert latest(c)['usable_automatic_evidence']
    monkeypatch.setenv('PRAXIS_TRACE_CONFIG','second');assert not latest(c)['usable_automatic_evidence']
    monkeypatch.setenv('PRAXIS_TRACE_CONFIG','first');(c/'code/options/two.json').write_text('{}');assert not latest(c)['usable_automatic_evidence']


@pytest.mark.parametrize('extra, event', [("import ctypes;ctypes.CDLL(None)",'ctypes.dlopen'), ("import socket;socket.socket().close()",'socket.')])
def test_uncovered_native_or_socket_events_force_conservative(tmp_path,monkeypatch,extra,event):
    c=make(tmp_path,monkeypatch,extra=extra);r=run(c)
    assert r['status']=='automatic-checks-passed'
    assert r['actual_dependencies']['mode']=='conservative'
    assert any(event in text for text in r['actual_dependencies']['coverage']['uncovered'])


def test_missing_directory_creation_changes_exists_branch(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch,extra="assert not Path('code/optional_dir').exists()")
    run(c);assert latest(c)['usable_automatic_evidence']
    (c/'code/optional_dir').mkdir();assert not latest(c)['usable_automatic_evidence']


def test_parent_pythonpath_change_is_stale(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch);run(c);assert latest(c)['usable_automatic_evidence']
    monkeypatch.setenv('PYTHONPATH',str(tmp_path/'other_search_root'))
    assert not latest(c)['usable_automatic_evidence']


def test_only_bound_ctypes_stdlib_pythonapi_initialization_is_runtime_event(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch,extra='import ctypes')
    r=run(c);assert r['actual_dependencies']['mode']=='python-reviewed'
    tr=json.loads((Path(r['run'])/'model.trace.json').read_text())
    assert any(event['event']=='ctypes.dlopen' and event['target'] is None and event['source_line']=='pythonapi = PyDLL(None)' for event in tr['runtime_initializations'])


def test_reviewed_numpy_numeric_use_retains_exact_mode_with_bound_runtime_event(tmp_path,monkeypatch):
    c=make(tmp_path,monkeypatch,extra='import numpy as np\nassert np.sum([1,2])==3')
    r=run(c);assert r['status']=='automatic-checks-passed'
    assert r['actual_dependencies']['mode']=='python-reviewed'
    assert latest(c)['usable_automatic_evidence']
    (c/'code/unused_numpy_case.py').write_text('VALUE=999\n')
    assert latest(c)['usable_automatic_evidence']
