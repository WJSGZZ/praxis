"""Observed banks change decisions; failure is not an infeasibility theorem."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

HERE = Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
SPEC = importlib.util.spec_from_file_location('observation_values', HERE/'observation_values.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_archive_has_physical_checks_without_relabeling_optimizer_failure():
    values = module.observation_values(HERE)
    assert values['independent_checks'] == 255
    rows = values['rows']
    strong = [rows[('strong_mixing_low_loss', d)] for d in ['passive','pulse']]
    delta = strong[0]['selected']['command_l']-strong[1]['selected']['command_l']
    assert 5*delta < 6 < 6*delta
    weak = rows[('weak_mixing_high_loss','pulse')]
    assert weak['accepted'] and not weak['selected']['optimizer_success']
    assert not rows[('weak_mixing_high_loss','passive')]['accepted']


@pytest.mark.parametrize('error', ['missing_envelope','wrong_prior','wrong_water'])
def test_consumption_rejects_incomplete_or_misbound_evidence(monkeypatch, error):
    text = (HERE/'reference/observation-control.json').read_text()
    original = json.loads(text); broken = copy.deepcopy(original)
    row = broken['completed'][0]
    if error == 'missing_envelope': row['independent'].pop()
    elif error == 'wrong_prior': row['independent'][0]['prior_index'] = -1
    else: row['independent'][0]['water_l'] += .1
    loads = json.loads
    monkeypatch.setattr(module.json, 'loads', lambda value: broken if value == text else loads(value))
    with pytest.raises(ValueError): module.observation_values(HERE)


def test_control_budget_preserves_partial_and_cannot_overwrite(tmp_path):
    output = tmp_path/'partial.json'
    command = [sys.executable,str(HERE/'study_observation_control.py'),'--output',str(output),'--seconds','1e-12']
    run = subprocess.run(command,capture_output=True,text=True,timeout=15)
    assert run.returncode == 0
    result = json.loads(output.read_text())
    assert result['status'] == 'budget exhausted' and not result['completed']
    saved = output.read_bytes()
    assert subprocess.run(command,capture_output=True,text=True,timeout=15).returncode != 0
    assert saved == output.read_bytes()
