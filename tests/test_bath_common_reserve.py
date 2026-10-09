"""Canonical coverage, counterexamples and failures must survive report binding."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
spec = importlib.util.spec_from_file_location('bath_common_reserve',HERE/'common_reserve.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


@pytest.fixture(scope='module')
def valid():
    return module.common_reserve_values(HERE)


def test_actual_archive_and_cost_identity(valid):
    assert (valid['objects'],valid['groups'],valid['independent_cases']) == (5796,18,54)
    assert valid['volumes']['passive'] == pytest.approx(26.088119908657287)
    assert valid['volumes']['pulse'] == pytest.approx(23.626852570853657)
    # Derived cost identity: signs at 2 and 3 uses, for every common positive alpha.
    assert 2*valid['delta_l'] < 6 < 3*valid['delta_l']
    assert valid['crossover'] == 3
    assert valid['lower'] >= 39.13 and valid['upper'] <= 40.9 and valid['spread'] <= 1.4


@pytest.mark.parametrize('defect',[
    'same_count_wrong_identity','missing_grid','changed_parameters','wrong_water',
    'nonfinite','false_flag','violating_bound','missing_extremum','wrong_structure',
    'reuse_policy','reuse_input','reuse_rows','hidden_failure','changed_target'])
def test_semantic_defects_rejected_beyond_hashes(valid,defect):
    data = copy.deepcopy(valid); m=data['manifest']; rows=data['rows']; independent=data['independent']
    bank = json.loads((HERE/'reference/structure-decision.json').read_text())
    r=rows[0]['records'][0]
    if defect=='same_count_wrong_identity': r['prior_index']=0
    elif defect=='missing_grid': rows.pop()
    elif defect=='changed_parameters': r['parameters']['h_body']+=1
    elif defect=='wrong_water': r['water_l']+=.01
    elif defect=='nonfinite': r['min_temp']=float('nan')
    elif defect=='false_flag': r['continuous_passed']=False
    elif defect=='violating_bound': r['lower_bound_c']=39.1299
    elif defect=='missing_extremum': independent['rows'].pop()
    elif defect=='wrong_structure': independent['rows'][0]['actual']['route']='deep'
    elif defect=='reuse_policy': m['reuse_provenance']['policy'][0]+=.01
    elif defect=='reuse_input': m['reuse_provenance']['shared_inputs']={'code/model.py':'invalid'}
    elif defect=='reuse_rows': r['midpoint_count']+=1
    elif defect=='hidden_failure': m['rejected_candidates'][0]['actual']['min_temp']=39.14
    else: m['common_reserve']['floor']=39
    with pytest.raises(ValueError): module.validate_records(m,bank,rows,independent)


@pytest.mark.parametrize('flows',[[True,0,0,0,0,0],[float('nan')]*6,[-1]*6,[3]*6,[1]*5])
def test_replay_rejects_invalid_flows_before_computation(valid,flows):
    with pytest.raises(ValueError):
        module.replay([{**module.model.BASE,**valid['prior'][0]}],(8,4,3),'surface',None,flows,lambda:None)


def test_nonfinite_adaptive_midpoint_cannot_pass(monkeypatch,valid):
    calls=[0]
    original=module.expm_multiply
    def broken(*args,**kwargs):
        calls[0]+=1
        result=original(*args,**kwargs)
        if calls[0]==2: result[0]=float('nan')
        return result
    # Force unresolved intervals so the midpoint branch is actually exercised.
    def unresolved(states,rates,curvature,net,dt):
        shape=(len(states)-1,states.shape[1]);a=np.zeros(shape)
        return a+39,a+41,a+1.5,None,None,None
    monkeypatch.setattr(module,'expm_multiply',broken)
    monkeypatch.setattr(module,'segment_bounds',unresolved)
    with pytest.raises(ValueError,match='midpoint'):
        module.replay([{**module.model.BASE,**valid['prior'][0]}],(8,4,3),'surface',None,[1]*6,lambda:None)
    assert calls[0]==2


def test_budget_failure_preserved_and_cannot_overwrite(tmp_path):
    output=tmp_path/'partial.json'
    command=[sys.executable,str(HERE/'study_common_reserve.py'),'--output',str(output),'--seconds','1e-12']
    first=subprocess.run(command,capture_output=True,text=True,timeout=15)
    assert first.returncode!=0 and json.loads(output.read_text())['status'].startswith('failed: TimeoutError')
    preserved=output.read_bytes()
    assert subprocess.run(command,capture_output=True,text=True,timeout=15).returncode!=0
    assert output.read_bytes()==preserved
