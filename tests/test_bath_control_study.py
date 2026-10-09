"""Preserve archived evidence and reject unsafe study entry conditions."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parents[1] / 'demos/mcm-2016-a/reproduce'


@pytest.mark.parametrize('seconds', ['0', '-1', 'nan', 'inf'])
def test_invalid_budget_cannot_create_evidence(tmp_path, seconds):
    output = tmp_path / 'result.json'
    result = subprocess.run([sys.executable, str(HERE / 'study_control.py'),
                             '--output', str(output), '--seconds', seconds],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert 'finite and positive' in result.stderr
    assert not output.exists()


def test_existing_evidence_is_never_overwritten(tmp_path):
    output = tmp_path / 'result.json'
    output.write_text('accepted prior evidence')
    result = subprocess.run([sys.executable, str(HERE / 'study_control.py'),
                             '--output', str(output)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert 'already exists' in result.stderr
    assert output.read_text() == 'accepted prior evidence'


def test_exhausted_budget_cannot_publish_partial_success(tmp_path):
    output = tmp_path / 'result.json'
    result = subprocess.run([sys.executable, str(HERE / 'study_control.py'),
                             '--output', str(output), '--seconds', '1e-12'],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert 'budget exhausted' in result.stderr
    assert not output.exists()


def test_archived_volume_and_envelopes_meet_declared_conditions():
    receipt = json.loads((HERE / 'reference/control-study.json').read_text())
    for row in receipt['conditional_schedules']:
        assert row['chosen']['water_l'] == pytest.approx(5 * sum(row['chosen']['flow_lpm']))
        assert len(row['independent']) == 3
        for replay in row['independent']:
            assert replay['continuous_passed']
            assert replay['lower_temperature_bound_c'] >= 39
            assert replay['upper_temperature_bound_c'] <= 41
            assert replay['span_upper_bound_c'] <= 1.5
