"""Refusal, latency, invalid evidence and real archived answer checks."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
spec=importlib.util.spec_from_file_location('bath_recourse',HERE/'recourse_values.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def files():
    with np.load(HERE/'reference/recourse-study.npz',allow_pickle=False) as a:return {n:a[n].tobytes() for n in a.files}
def test_real_answer_scope_and_counterexample():
    r=module.recourse_values(HERE)
    assert len(r['checks']['rows'])==57
    assert [len(x['survivors']) for x in r['rows']]==[1,8,4,6]
    assert [len(x['preterminal_survivors']) for x in r['rows']]==[1,15,6,7]
    assert [x['selected']['q_lpm'] for x in r['rows']]==[0,.8,.8,1.05]
    assert r['rows'][-1]['selected']['total_command_l']>26.09
    counter=json.loads(r['files']['rejected-checks.json']);assert counter['status']=='completed'
    assert all(x['actual']['min_temp']<39 for x in counter['rows'])
@pytest.mark.parametrize('defect',['prefix','empty','timeout','coverage','water','reading','bridge','physical','catalog'])
def test_rebinding_does_not_promote_bad_evidence(tmp_path,defect):
    data=files();run=json.loads(data['results-lagged.json']);check=json.loads(data['checks-lagged.json']);row=run['rows'][0]
    if defect=='prefix':row['prefix_flows'][0]+=.1
    elif defect=='empty':row['survivors']=[]
    elif defect=='timeout':row['decision_elapsed_s']=60
    elif defect=='coverage':check['rows'].pop()
    elif defect=='water':row['selected']['total_command_l']+=1
    elif defect=='reading':row['readings'][0][0]+=.1
    elif defect=='bridge':row['bridge_records']=[]
    elif defect=='catalog':run['catalog'][0]['parameters']['D']*=2
    else:check['rows'][0]['actual']['min_temp']=38.9
    data['results-lagged.json']=json.dumps(run).encode();check['source_sha256']['results-lagged.json']=hashlib.sha256(data['results-lagged.json']).hexdigest();data['checks-lagged.json']=json.dumps(check).encode()
    screen=json.loads(data['screen-checks-lagged.json']);screen['source_sha256']['results-lagged.json']=hashlib.sha256(data['results-lagged.json']).hexdigest();data['screen-checks-lagged.json']=json.dumps(screen).encode()
    manifest=json.loads(data['manifest.json']);manifest['members']={n:hashlib.sha256(data[n]).hexdigest() for n in manifest['members']};data['manifest.json']=json.dumps(manifest).encode();(tmp_path/'reference').mkdir()
    np.savez_compressed(tmp_path/'reference/recourse-study.npz',**{n:np.frombuffer(b,dtype=np.uint8) for n,b in data.items()})
    with pytest.raises(ValueError):module.recourse_values(tmp_path)
@pytest.mark.parametrize('duration', [60, 61])
def test_actual_deadline_regression_and_archived_producer_identity(tmp_path, duration):
    data=files();p=tmp_path/'candidate_search.py';p.write_bytes(data[p.name]);spec=importlib.util.spec_from_file_location('recourse_deadline',p);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);clock_value=[0]
    def evaluate(q):clock_value[0]=duration;return [{'passed':True}]
    result=helper.select_candidate([.8],evaluate,clock=lambda:clock_value[0])
    assert result['status']=='decision_timeout' and result['selected'] is None
    assert result['candidates'][0]['rejected_reason']=='decision_timeout'
    assert b"row['status']=selection['status']" in data['run-lagged-deadline.py']


@pytest.fixture
def selector(tmp_path):
    path = tmp_path / 'candidate_search.py'
    path.write_bytes(files()[path.name])
    spec = importlib.util.spec_from_file_location('archived_selector', path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper.select_candidate


def test_expired_decision_does_not_start_solver(selector):
    calls = []
    ticks = iter([0, 60, 60])
    result = selector([0], lambda q: calls.append(q), clock=lambda: next(ticks))
    assert result['status'] == 'decision_timeout' and not calls


def test_failed_then_timely_candidate_keeps_first_valid_choice(selector):
    clock = [0]
    def evaluate(q):
        clock[0] += 1
        return [{'passed': q == .8}]
    result = selector([.7, .8, .9], evaluate, clock=lambda: clock[0])
    assert result['status'] == 'tail_qualified'
    assert result['selected']['q_lpm'] == .8 and len(result['candidates']) == 2


def test_empty_scope_and_solver_exception_never_produce_action(selector):
    result = selector([0], lambda q: [])
    assert result['selected'] is None and result['status'] == 'no_qualified_constant_tail'
    def fail(q):
        raise RuntimeError('solver failed')
    with pytest.raises(RuntimeError):
        selector([0], fail)
