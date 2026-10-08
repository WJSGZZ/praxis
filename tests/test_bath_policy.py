"""Independent known-solution checks for the schedule acceptance validator."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

CODE = Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce/code'
SPEC = importlib.util.spec_from_file_location('bath_policy_validation', CODE/'policy_validation.py')
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


def fixture():
    # One exactly mixed cell: at 1 L/min T'=50-T; no inflow holds T=40.
    p = dict(L=1., W=1., H=1., inlet_exclusion=-1., initial=40., air_temp=22.,
             body_temp=34., horizon=2., floor=39., ceiling=41., span=1.5)
    net = dict(cap=np.ones(1), ha=np.zeros(1), hb=np.zeros(1), G=np.zeros((1, 1)),
               adv=np.array([[-60000.]]), hot=np.array([3000000.]))
    return p, net


def test_known_overheated_schedule_rejected_and_safe_margin_accepted():
    p, net = fixture()
    hot = validation.replay_schedule(p, net, [1.], (1, 1, 1))
    # Independent exact answer for T'=50-T, T(0)=40.
    assert hot['max_temp'] == pytest.approx(50-10*np.exp(-2), abs=2e-7)
    assert hot['max_temp'] > p['ceiling']+.002
    assert not hot['sampled_passed'] and not hot['continuous_passed']
    safe = validation.replay_schedule(p, net, [0.], (1, 1, 1))
    assert safe['min_temp'] == safe['max_temp'] == 40
    assert safe['sampled_passed'] and safe['continuous_passed']


def test_exact_cooling_solution_has_accepted_continuous_margin():
    p, net = fixture()
    p['air_temp'] = 39.5
    net['ha'][:] = 1.
    result = validation.replay_schedule(p, net, [0.], (1, 1, 1))
    assert result['min_temp'] == pytest.approx(39.5+.5*np.exp(-2), abs=2e-8)
    assert result['lower_temperature_bound_c'] > p['floor']
    assert result['upper_temperature_bound_c'] < p['ceiling']
    assert result['continuous_passed']


def test_switch_is_a_boundary_and_derivative_bound_restarts():
    p, net = fixture()
    p['ceiling'] = 60.
    p['horizon'] = 3.  # switch at a noninteger 1.5 s
    result = validation.replay_schedule(p, net, [1., 0.], (1, 1, 1))
    first, second = result['segments']
    assert first['stop_s'] == second['start_s'] == 1.5
    assert first['initial_derivative_norm_c_per_s'] == 10.
    assert second['initial_derivative_norm_c_per_s'] == 0.
    assert second['min_temp'] == pytest.approx(50-10*np.exp(-1.5), abs=2e-7)
    assert result['continuous_passed']
    assert all(segment['largest_sample_gap_s'] <= 1 for segment in result['segments'])


def test_invalid_contraction_premise_cannot_certify_even_wide_limits():
    p, net = fixture()
    p.update(floor=-1e6, ceiling=1e6)
    net['adv'][0, 0] = 60000.
    result = validation.replay_schedule(p, net, [1.], (1, 1, 1))
    assert result['sampled_passed']
    assert not result['segments'][0]['contraction_premise']
    assert not result['continuous_passed']


@pytest.mark.parametrize('flows', [[], [-1.], [float('nan')], [float('inf')]])
def test_invalid_flows_are_refused(flows):
    p, net = fixture()
    with pytest.raises(ValueError):
        validation.replay_schedule(p, net, flows, (1, 1, 1))


def test_cli_selects_lowest_accepted_water_and_fails_when_none_pass(tmp_path):
    import json
    import os
    import subprocess
    import sys

    root = CODE.parent
    # Real network assembly on all three prescribed meshes. For this one-second
    # fixture both schedules have ample thermal margin, so the independent
    # accounting answer is the zero-flow candidate, using exactly zero litres.
    parameters = json.loads((root/'reference/extended.json').read_text())['parameters']
    parameters.update(horizon=1., floor=0., ceiling=100., span=100.)
    data = dict(parameters=parameters, control=dict(
        best=dict(flow_lpm=[1.], water_l=1/60),
        buffer_price=[dict(flow_lpm=[0.], water_l=0., buffer_c=.1)]))
    source, output = tmp_path/'extended.json', tmp_path/'mesh.json'
    source.write_text(json.dumps(data))
    command = [sys.executable, str(root/'run_mesh_check.py'), '--extended', str(source), '--output', str(output)]
    env = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
    result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=30)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report['accepted_schedule']['water_l'] == 0.
    assert report['accepted_schedule']['source'] == 'buffer_price[0]'
    assert len(report['accepted_independent']['meshes']) == 3
    assert len(report['candidate_diagnostics']) == 2
    assert all(check['passed'] for check in report['checks'])
    import hashlib
    assert report['input_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    for name, digest in report['source_sha256'].items():
        assert digest == hashlib.sha256((root/name).read_bytes()).hexdigest()
    # Initial T=40 already violates a floor of 100, independently of any solver.
    data['parameters']['floor'] = 100.
    source.write_text(json.dumps(data))
    result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=30)
    assert result.returncode == 1
    failed = json.loads(output.read_text())
    assert failed['accepted_schedule'] is None and failed['accepted_independent'] is None
    assert not any(check['passed'] for check in failed['checks'])
    assert not any(candidate['accepted'] for candidate in failed['candidate_diagnostics'])


@pytest.mark.parametrize('mutation', ['source_changed', 'source_missing', 'input_changed'])
def test_report_refuses_stale_schedule_evidence(tmp_path, mutation):
    import json
    import shutil
    import subprocess
    import sys

    root = CODE.parent
    for path in (root/'reference').iterdir():
        if path.is_file():
            shutil.copyfile(path, tmp_path/path.name)
    if mutation == 'input_changed':
        extended = tmp_path/'extended.json'
        extended.write_text(extended.read_text()+'\n')
    else:
        path = tmp_path/'mesh_check.json'
        receipt = json.loads(path.read_text())
        if mutation == 'source_changed':
            receipt['source_sha256']['code/model.py'] = '0'*64
        else:
            del receipt['source_sha256']['code/policy_validation.py']
        path.write_text(json.dumps(receipt))
    result = subprocess.run([sys.executable, str(root/'build_report.py'), '--run', str(tmp_path)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert 'evidence is stale' in result.stderr
