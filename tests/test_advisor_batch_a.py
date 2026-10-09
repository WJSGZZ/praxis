import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from scipy.optimize import OptimizeResult
from modeling import layered, structure, nonlinear, decision_models
from scripts import mcp_server, pipeline


@pytest.mark.parametrize('fn', [lambda f: structure.check_convexity(f, [[0, 1]], trials=3), lambda f: structure.check_monotone(f, [[0, 1]], 0, trials=3), lambda f: structure.check_symmetry(f, [[0, 1]], [0], trials=3), lambda f: structure.check_power_law(f, [[1, 2]], trials=3)])
@pytest.mark.parametrize('bad', [float('nan'), float('inf'), 1j])
def test_probes_reject_invalid_real_evaluations(fn, bad):
    with pytest.raises((ValueError, TypeError)):
        fn(lambda x: bad)


@pytest.mark.parametrize('prop', ['convexity', 'monotone'])
def test_invalid_log_domain_is_tool_error(prop):
    args = dict(property=prop, expression='log(x)', names=['x'], bounds=[[-2, -1]])
    if prop == 'monotone':
        args['variable'] = 'x'
    with np.errstate(invalid='ignore'):
        reply = mcp_server.handle(dict(id=1, method='tools/call', params=dict(name='probe_structure', arguments=args)))
    assert reply['result']['isError']


def test_single_cell_equilibrium_and_grid_contract():
    layers = [dict(thickness=1., k=1., rho_c=1.)]
    for n in [1, 2, 4]:
        r = layered.solve_layered(layers, t_end=10, t_initial=10, left=['dirichlet',10], right=['dirichlet',10], cells_per_layer=n)
        assert r['final_cells'] == pytest.approx([10]*n)
    for counts in [[], [1,2], [0], [1.5], [True]]:
        with pytest.raises(ValueError):
            layered.solve_layered(layers,t_end=1,t_initial=10,left=['dirichlet',10],right=['dirichlet',10],cells_per_layer=counts)


def test_probability_inputs_and_closed_class():
    with pytest.raises(ValueError):
        nonlinear.solve_mdp([[[2,-1],[0,1]]], [[0],[0]], horizon=1, terminal=[0,1])
    with pytest.raises(ValueError):
        decision_models.markov_absorption([[0,2],[0,1]], [1])
    r = decision_models.markov_absorption([[1,0,0],[0,1,0],[0,0,1]], [2])
    assert not r['fully_absorbing'] and r['expected_steps'] is None
    r = decision_models.markov_absorption([[.5,.5],[0,1]], [1])
    assert r['absorption_probabilities'] == [[1.]] and r['expected_steps'] == [2.]
    for horizon in [-1, 1.5, True]:
        with pytest.raises(ValueError):
            nonlinear.solve_mdp([[[1]]], [[0]], horizon=horizon)


@pytest.mark.parametrize('x,fun', [([0.],1.), ([3.],4.), ([float('nan')],float('nan'))])
def test_failed_optimizer_does_not_become_optimum(x, fun):
    failed = OptimizeResult(x=np.array(x),fun=fun,success=False,status=9,message='Iteration limit reached')
    with patch.object(nonlinear,'minimize',return_value=failed):
        r = nonlinear.minimize_nlp(lambda x:(x[0]-1)**2,[[0,2]],starts=1)
    assert not r['converged'] and r['distinct_optima'] == []
    assert r['attempts'][0]['status'] == 9
    assert r['feasible'] is (x == [0.])
    if r['feasible']:
        assert r['status'] == 'feasible_incumbent' and r['value'] == 1


def test_json_overflow_and_invalid_relation_rejected(tmp_path):
    p = tmp_path/'x.json';p.write_text('{"x":1e400}')
    with pytest.raises(ValueError):
        pipeline.read_json(p)
    with pytest.raises(ValueError):
        mcp_server._json({'x':float('inf')})
    with pytest.raises(ValueError,match='relation'):
        mcp_server.call('test_conjecture',dict(lhs='1',rhs='1',relation='>',names=['x'],bounds=[[0,1]],points=1))


def test_bad_rpc_does_not_terminate_service():
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable,'-m','scripts.mcp_server'],cwd=root,input='[]\n{"id":2,"method":"ping"}\n',capture_output=True,text=True,timeout=30)
    replies=[json.loads(x) for x in r.stdout.splitlines()]
    assert r.returncode == 0 and replies[0]['error']['code'] == -32600 and replies[1]['result'] == {}


def test_registered_input_version_and_dependency_set_invalidate(tmp_path, monkeypatch):
    from test_pipeline import make_case
    # Independent expected result in make_case is y(4)=1+2*4=9.
    import test_pipeline
    p = test_pipeline.pipeline
    monkeypatch.setattr(p,'PROJECT', tmp_path)
    case,_,_ = make_case(tmp_path)
    r=p.run_case(case)
    assert r['automatic_checks_passed']
    raw=case/'raw/data/measurements.csv';raw.chmod(0o644);raw.write_text('x,y\n0,100\n1,102\n')
    cfg=p.read_json(case/'case.json')
    entry=next(i for i in cfg['inputs'] if i['path'].endswith('measurements.csv'))
    entry['sha256']=p.digest(raw);p.save(case/'case.json',cfg)
    state=p.status(case)['runs'][0]
    assert not state['usable_automatic_evidence'] and 'registered input version changed' in state['stale']
    receipt=Path(r['run'])/'receipt.json';saved=p.read_json(receipt);saved.pop('inputs');p.save(receipt,saved)
    assert 'run input binding missing; validity unknown' in p.status(case)['runs'][0]['stale']


def test_new_dependency_files_invalidate_receipt(tmp_path, monkeypatch):
    from test_pipeline import make_case
    import test_pipeline
    p=test_pipeline.pipeline
    monkeypatch.setattr(p,'PROJECT',tmp_path)
    case,_,_=make_case(tmp_path)
    r=p.run_case(case)
    assert r['automatic_checks_passed']
    original=p.dependency_snapshot()
    monkeypatch.setattr(p,'dependency_snapshot',lambda: {**original,'modeling/new.py':'0'*64})
    state=p.status(case)['runs'][0]
    assert not state['usable_automatic_evidence']
    assert any('dependency file set' in x for x in state['stale'])


def test_actual_pipeline_failure_then_recovery_and_fresh_process(tmp_path, monkeypatch):
    from test_pipeline import make_case
    import test_pipeline
    p=test_pipeline.pipeline
    monkeypatch.setattr(p,'PROJECT',tmp_path)
    case,_,_=make_case(tmp_path)
    success=p.run_case(case)
    source=case/'code/model.py';valid=source.read_text()
    source.write_text("raise RuntimeError('synthetic interrupted candidate')")
    failed=p.run_case(case)
    assert failed['status']=='failed'
    assert Path(success['run']).is_dir() and Path(failed['run']).is_dir()
    source.write_text(valid)
    recovered=p.run_case(case)
    assert recovered['automatic_checks_passed']
    cmd=[sys.executable,'-c', 'import json,sys;from pathlib import Path;from scripts import pipeline;p=Path(sys.argv[1]);pipeline.PROJECT=p;print(json.dumps(pipeline.status(sys.argv[2])))',str(tmp_path),str(case)]
    r=subprocess.run(cmd,cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=30)
    assert r.returncode == 0,r.stderr
    states=json.loads(r.stdout)['runs']
    assert states[-1]['usable_automatic_evidence'] and states[-2]['status']=='failed'
    # A prose-only edit preserves computation evidence.
    (case/'paper').mkdir(exist_ok=True)
    (case/'paper/main.tex').write_text('Pure prose without numerical changes')
    assert p.status(case)['runs'][-1]['usable_automatic_evidence']


def test_pipeline_overflow_never_reaches_validator(tmp_path, monkeypatch):
    from test_pipeline import make_case
    import test_pipeline
    p=test_pipeline.pipeline
    monkeypatch.setattr(p,'PROJECT',tmp_path)
    case,_,_=make_case(tmp_path)
    (case/'code/model.py').write_text('import argparse\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument("--output",type=Path);a=p.parse_args();(a.output/"results.json").write_text(\'{"prediction":1e400}\')')
    r=p.run_case(case)
    assert r['status']=='failed' and 'Non-finite JSON' in r['error']
    assert len(r['steps']) == 1 and not p.status(case)['runs'][-1]['usable_automatic_evidence']


def test_archived_mesh_validator_keeps_original_identity():
    import hashlib
    root=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
    receipt=json.loads((root/'reference/mesh_check.json').read_text())
    old=root/'reference/mesh-validator-335052c.py'
    assert hashlib.sha256(old.read_bytes()).hexdigest()==receipt['source_sha256']['run_mesh_check.py']
    assert old.read_bytes() != (root/'run_mesh_check.py').read_bytes()
