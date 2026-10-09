"""Complete-service, fault, identity and stale-source guards for the feedback case."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import pytest

HERE = Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
spec = importlib.util.spec_from_file_location('bath_feedback',HERE/'feedback_study.py')
module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@pytest.fixture(scope='module')
def valid():
    return module.feedback_values(HERE)


def test_complete_rows_survive_outer_timeout_without_promoting_fault(valid):
    assert valid['runs']['variants']['status'] == 'budget exhausted'
    assert valid['runs']['variants-resume']['status'] == 'budget exhausted'
    assert len(valid['completed']) == 9 and valid['recorded_mesh_checks'] == 18
    zero = valid['completed'][('variants','zero_noise')]
    assert sum(zero['flows']) == pytest.approx(23.592853665976513)
    assert zero['steps'][-1]['retained_models'] == 114
    assert valid['terminal']['high_loss']['detected_s'] == 660
    assert ('loss-branch','high_loss') not in valid['completed']


@pytest.mark.parametrize('defect',['partial','water','nan','bool','time','growing','action','false_pass','reserve'])
def test_bad_service_rejected(valid,defect):
    row=copy.deepcopy(valid['completed'][('variants','zero_noise')])
    bank=valid['runs']['variants']['model_bank']
    backup=[s['baseline_flow_lpm'] for s in row['steps']]
    if defect=='partial':row['flows'].pop();row['steps'].pop()
    elif defect=='water':row['saved_command_l']+=.1
    elif defect=='nan':row['independent']['min_temp']=float('nan')
    elif defect=='bool':row['flows'][0]=True
    elif defect=='time':row['steps'][2]['time_s']=61
    elif defect=='growing':row['steps'][2]['retained_models']=1466
    elif defect=='action':row['flows'][0]=.123;row['steps'][0]['flow_lpm']=.123
    elif defect=='false_pass':row['independent']['sampled_passed']=False
    else:row['independent']['min_temp']=39.1299
    with pytest.raises(ValueError):module.validate_case(row,bank,backup)


@pytest.mark.parametrize('defect',['identities','interval','nonfinite','not_empty','saved_water'])
def test_bad_fault_evidence_rejected(valid,defect):
    row=copy.deepcopy(valid['runs']['terminal-identity']['results'][2]);t=row['terminal_observation']
    if defect=='identities':t['model_ids_before'][0]=t['model_ids_before'][1]
    elif defect=='interval':t['bias_lo'][0][0]+=.001
    elif defect=='nonfinite':t['predicted_readings'][0][0]=float('inf')
    elif defect=='not_empty':t['model_ids_after']=[0]
    else:
        row['saved_command_l']=15.
        bank=valid['runs']['terminal-identity']['model_bank']
        with pytest.raises(ValueError):module.validate_case(row,bank,[s['baseline_flow_lpm'] for s in row['steps']])
        return
    with pytest.raises(ValueError):module.validate_terminal(row)


def test_replay_refuses_overwrite_and_records_budget_stop(tmp_path,monkeypatch):
    sys.path.insert(0,str(HERE))
    import study_feedback
    out=tmp_path/'receipt.json';out.write_text('original')
    with pytest.raises(ValueError):study_feedback.run(out,'audit',10.)
    assert out.read_text()=='original'
    out.unlink()
    clock=iter((0.,1.,2.,3.))
    monkeypatch.setattr(study_feedback.time,'monotonic',lambda:next(clock))
    with pytest.raises(TimeoutError):study_feedback.run(out,'audit',.5)
    r=json.loads(out.read_text())
    assert r['status']=='budget exhausted' and r['rows']==[]


def test_offbank_transfer_preserves_completion_and_rejection_boundaries():
    result = module.transfer_values(HERE)
    assert len(result['completed']) == 2 and len(result['refused']) == 4
    assert len(result['checks']) == 10
    assert [row['detected_s'] for row in result['refused'].values()] == [1680,300,660,540]
    assert all(not row['actual_independent_trace']['full_service']
               for row in result['refused'].values())


@pytest.mark.parametrize('defect',['partial_as_full','wrong_units','false_envelope','wrong_prefix','changed_backup'])
def test_transfer_semantics_reject_rebound_corrupt_receipts(tmp_path,defect):
    import hashlib
    import shutil
    import numpy as np
    ref = tmp_path/'reference';ref.mkdir()
    m = json.loads((HERE/'reference/feedback-transfer.json').read_text())
    with np.load(HERE/'reference/feedback-transfer.npz',allow_pickle=False) as z:
        blobs = {k:bytes(z[k]) for k in z.files}
    design = json.loads(blobs['design.json'])
    for name in design['source_snapshot']:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(HERE/name,target)
    run=json.loads(blobs['results.json']);check=json.loads(blobs['check-results.json'])
    if defect=='partial_as_full':run['results'][2]['status']='completed_model_conditional_service'
    elif defect=='changed_backup':run['results'][0]['steps'][0]['baseline_flow_lpm']+=.1
    elif defect=='wrong_units':check['rows'][0]['actual_l']=check['rows'][0]['command_l']
    elif defect=='false_envelope':check['rows'][0]['numeric_envelope_c'][1]=42.
    else:check['rows'][2]['covered_s']=1800
    blobs['results.json']=json.dumps(run).encode()
    check['producer_results_sha256']=hashlib.sha256(blobs['results.json']).hexdigest()
    blobs['check-results.json']=json.dumps(check).encode()
    archive=ref/'feedback-transfer.npz'
    np.savez_compressed(archive,**{k:np.frombuffer(v,dtype=np.uint8) for k,v in blobs.items()})
    m['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
    m['members']={k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()}
    (ref/'feedback-transfer.json').write_text(json.dumps(m))
    with pytest.raises(ValueError):module.transfer_values(tmp_path)


def test_continuum_archive_retains_failed_bound_and_frozen_action_scope():
    r=module.continuous_values(HERE)
    assert r['scale']==.25 and len(r['checks'])==102
    assert all(not s['physical_passed'] for row in r['previous']['rows'] for s in row['scales'])
    assert any(not next(s for s in row['scales'] if s['scale']==.25)['reserve_passed'] for row in r['rows'])


@pytest.mark.parametrize('defect',['missing_corner','changed_parameter','water_units','false_pass'])
def test_continuum_rejects_semantically_rebound_archive(tmp_path,defect):
    import hashlib
    import numpy as np
    ref=tmp_path/'reference';ref.mkdir()
    m=json.loads((HERE/'reference/continuous-transfer.json').read_text())
    with np.load(HERE/'reference/continuous-transfer.npz',allow_pickle=False) as z:
        blobs={k:bytes(z[k]) for k in z.files}
    check=json.loads(blobs['structured/check-results.json'])
    if defect=='missing_corner':check['rows'].pop()
    elif defect=='changed_parameter':check['rows'][0]['parameters']['D']+=1e-7
    elif defect=='water_units':check['rows'][0]['result']['water_l']=22.59338886521566
    else:
        run=json.loads(blobs['structured/results.json']);run['rows'][0]['scales'][0]['physical_passed']=True
        blobs['structured/results.json']=json.dumps(run).encode()
        check['source_sha256']['structured/results.json']=hashlib.sha256(blobs['structured/results.json']).hexdigest()
    blobs['structured/check-results.json']=json.dumps(check).encode()
    archive=ref/'continuous-transfer.npz'
    np.savez_compressed(archive,**{k:np.frombuffer(v,dtype=np.uint8) for k,v in blobs.items()})
    m['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
    m['members']={k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()}
    (ref/'continuous-transfer.json').write_text(json.dumps(m))
    with pytest.raises(ValueError):module.continuous_values(tmp_path)
