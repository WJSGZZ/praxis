"""Independent minimax examples and unsafe-entry checks for calibration study."""
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1] / 'demos/mcm-2016-a/reproduce'
spec = importlib.util.spec_from_file_location('bath_calibration', HERE / 'study_calibration.py')
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def test_constant_offset_is_not_independent_pointwise_error():
    # All readings within +/- .04 does not suffice: a constant offset cannot
    # explain a trace ranging from -.04 to .04 with +/- .02 reading error.
    correction, residual, accepted = study.compatible_offset(np.array([[-.04], [.04]]))
    assert correction[0] == 0 and residual == pytest.approx(.04)
    assert not accepted
    correction, residual, accepted = study.compatible_offset(np.array([[.03], [.04]]))
    assert correction[0] == pytest.approx(.02) and residual == pytest.approx(.02)
    assert accepted
    # Physical sensor bias has the opposite sign to the model correction.
    assert -.02 + .04 == pytest.approx(.02)


@pytest.mark.parametrize('seconds', ['0', '-1', 'nan', 'inf', '1e-12'])
def test_invalid_or_exhausted_budget_cannot_create_accepted_evidence(tmp_path, seconds):
    output = tmp_path / 'result.json'
    result = subprocess.run([sys.executable, str(HERE / 'study_calibration.py'),
                             '--output', str(output), '--seconds', seconds],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert not output.exists()


def test_no_overwrite(tmp_path):
    output = tmp_path / 'accepted.json'
    output.write_text('previous accepted artifact')
    result = subprocess.run([sys.executable, str(HERE / 'study_calibration.py'),
                             '--output', str(output)], capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert output.read_text() == 'previous accepted artifact'


def test_archived_study_has_complete_bound_inputs_and_independent_coverage():
    result = json.loads((HERE / 'reference/calibration-study.json').read_text())
    assert result['accepted'] and result['status'] == 'completed'
    for name, digest in result['source_sha256'].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest
    bank = result['rows']
    assert len(bank) == result['compatible_models']
    assert len({tuple(row['parameters'].values()) for row in bank}) == len(bank)
    checks = result['independent']
    keys = [(row['model_index'], tuple(row['grid'])) for row in checks]
    assert len(keys) == len(set(keys))
    assert set(keys) == {(i, tuple(grid)) for i in range(len(bank)) for grid in study.GRIDS}
    command = 5 * sum(result['rounds'][-1]['flow_lpm'])
    assert command == pytest.approx(result['commanded_water_l'])
    assert result['calibration_command_l'] == 5 * sum(result['pulse_flow_lpm'])
    for row in checks:
        assert row['continuous_passed'] and row['sampled_passed']
        assert row['lower_temperature_bound_c'] >= 39
        assert row['upper_temperature_bound_c'] <= 41
        assert row['span_upper_bound_c'] <= 1.5
        assert row['water_l'] == pytest.approx(command * bank[row['model_index']]['parameters']['flow_multiplier'])


def test_transfer_cannot_overwrite_or_publish_stale_inputs(tmp_path):
    import shutil
    entry = HERE / 'check_calibration_transfer.py'
    output = tmp_path / 'receipt.json'
    output.write_text('keep accepted evidence')
    result = subprocess.run([sys.executable, str(entry), '--output', str(output)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and output.read_text() == 'keep accepted evidence'
    # Isolated caller with intentionally stale source binding, not a mutation
    # of shared scientific inputs. It must fail before simulation/output.
    local = tmp_path / 'reproduce'
    (local / 'reference').mkdir(parents=True)
    shutil.copytree(HERE / 'code', local / 'code')
    shutil.copy(entry, local / entry.name)
    shutil.copy(HERE / 'check_structure.py', local / 'check_structure.py')
    shutil.copy(HERE / 'reference/results.json', local / 'reference/results.json')
    data = json.loads((HERE / 'reference/calibration-study.json').read_text())
    data['source_sha256'] = {'code/model.py': '0' * 64}
    (local / 'reference/calibration-study.json').write_text(json.dumps(data))
    output = tmp_path / 'stale.json'
    result = subprocess.run([sys.executable, str(local / entry.name), '--output', str(output)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0 and 'Stale calibration study' in result.stderr
    assert not output.exists()


def test_transfer_receipt_keeps_finite_scope_and_policy_accounting():
    data = json.loads((HERE / 'reference/calibration-transfer.json').read_text())
    bank = json.loads((HERE / 'reference/calibration-study.json').read_text())
    for name, digest in data['source_sha256'].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest
    assert [r['model_index'] for r in data['constant_rows']] == list(range(178))
    # Known comparison is archived on the original bank; do not extrapolate
    # this count to real-bath probability or cross-structure coverage.
    assert sum(r['sampled_passed'] for r in data['constant_rows']) == 130
    for row in data['constant_rows']:
        assert row['water_l'] == pytest.approx(data['constant_command_l'] * bank['rows'][row['model_index']]['parameters']['flow_multiplier'])
    pairs = {(r['model_index'], r['route'], r['body_capacity_j_per_k']) for r in data['structure_rows']}
    assert len(pairs) == len(data['structure_rows']) == 40
    assert pairs == {(i, route, cap) for i in data['selected_model_indices'] for route in ('surface', 'deep') for cap in (None, 253310.)}
    command = 5 * sum(data['new_policy_flow_lpm'])
    for row in data['structure_rows']:
        assert row['water_l'] == pytest.approx(command * row['parameters']['flow_multiplier'])
        assert row['sampled_passed']
        assert row['instantaneous_balance_residual_w'] < 1e-6
        assert row['integrated_balance_residual_j'] < .1
