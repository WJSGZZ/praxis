"""Analytic physics checks and bounded finite-information accounting."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parents[1] / 'demos/mcm-2016-a/reproduce'


def test_finite_volume_against_independent_continuum_and_cascade_answers(monkeypatch):
    spec = importlib.util.spec_from_file_location('fv_check', HERE/'check_finite_volume.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.verification()
    assert result['accepted']
    assert result['observed_orders'][-1] == pytest.approx(2., abs=.03)
    # First grid is genuinely pre-asymptotic; do not erase it to claim all
    # observed orders are exactly two.
    assert result['observed_orders'][0] < 1.8
    assert max(x['max_error_c'] for x in result['advection_rows']) < 1e-10
    network = module.model.network
    def wrong_diffusivity(p, grid=(8,4,3)):
        net = network(p, grid)
        net['G'] *= 1.01
        return net
    monkeypatch.setattr(module.model, 'network', wrong_diffusivity)
    assert not module.verification()['accepted']


def test_information_budget_and_overwrite_cannot_accept_a_partial_run(tmp_path):
    entry = HERE/'study_information_value.py'
    output = tmp_path/'result.json'
    run = subprocess.run([sys.executable, str(entry), '--output', str(output), '--seconds', '1e-12'], capture_output=True, text=True, timeout=15)
    assert run.returncode == 0
    result = json.loads(output.read_text())
    assert result['status'] == 'budget exhausted' and not result['accepted']
    saved = output.read_bytes()
    repeat = subprocess.run([sys.executable, str(entry), '--output', str(output)], capture_output=True, text=True, timeout=15)
    assert repeat.returncode != 0 and output.read_bytes() == saved


def test_passive_archive_retains_all_delivery_biases_and_full_grid_coverage():
    result = json.loads((HERE/'reference/information-value.json').read_text())
    assert result['status'] == 'completed' and result['accepted']
    bank = result['rows']
    assert len(bank) == 510
    groups = {}
    for row in bank:
        p = row['parameters']
        key = (p['D'], p['h_surface'], p['h_body'])
        groups.setdefault(key, set()).add(p['flow_multiplier'])
    assert all(m == {.95, .975, 1., 1.025, 1.05} for m in groups.values())
    records = result['independent']
    keys = {(r['model_index'], tuple(r['grid'])) for r in records}
    assert len(keys) == len(records) == 1530
    assert keys == {(i,g) for i in range(510) for g in [(8,4,3),(12,6,4),(16,8,6)]}
    control = 5*sum(result['rounds'][-1]['flow_lpm'])
    for r in records:
        assert r['continuous_passed']
        assert r['lower_temperature_bound_c'] >= 39.
        assert r['upper_temperature_bound_c'] <= 41.
        assert r['span_upper_bound_c'] <= 1.5
        assert r['water_l'] == pytest.approx(control*bank[r['model_index']]['parameters']['flow_multiplier'])
    # Candidate arithmetic, not a fabricated award threshold or proof that
    # the two observation-compatible banks are nested.
    pulse = json.loads((HERE/'reference/calibration-study.json').read_text())
    delta = control-pulse['commanded_water_l']
    assert delta == pytest.approx(.9098362997090739)
    assert 6*delta < 6 < 7*delta


def test_historical_receipt_retains_actual_source_and_current_guard_rejects_stale_input(tmp_path):
    result = json.loads((HERE/'reference/information-value.json').read_text())
    for name,digest in result['source_sha256'].items():
        source = HERE/name
        if name == 'study_information_value.py':
            source = HERE/'reference/information-study-27f9e95.py'
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    import shutil
    local = tmp_path/'reproduce'
    (local/'reference').mkdir(parents=True)
    shutil.copytree(HERE/'code',local/'code')
    for name in ['study_information_value.py','study_calibration.py']:
        shutil.copy(HERE/name,local/name)
    bad = json.loads((HERE/'reference/calibration-study.json').read_text())
    bad['source_sha256'] = {'code/model.py':'0'*64}
    (local/'reference/calibration-study.json').write_text(json.dumps(bad))
    output = tmp_path/'stale.json'
    run = subprocess.run([sys.executable,str(local/'study_information_value.py'),'--output',str(output)],capture_output=True,text=True,timeout=15)
    assert run.returncode != 0 and 'Stale calibration input' in run.stderr
    assert not output.exists()
