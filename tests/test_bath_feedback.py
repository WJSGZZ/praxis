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
