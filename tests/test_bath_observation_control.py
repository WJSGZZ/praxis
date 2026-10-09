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


def test_structural_screen_keeps_fit_and_fixed_policy_scope_separate():
    values = module.structure_observation_values(HERE)
    assert values['observation_count'] == 8 and values['replay_count'] == 6
    assert values['all_banks_nonempty']
    assert values['maximum_summary_difference_c'] < 2e-6
    rows = values['receipt']['observations']
    # All five supply multipliers remain compatible together in a passive trial:
    # there is no supply term to identify, even with the whole observed trace.
    for row in rows:
        if row['design'] != 'passive':
            continue
        indices = set(row['compatible_indices'])
        assert all({5*(i//5)+j for j in range(5)} <= indices for i in indices)


@pytest.mark.parametrize('error', ['missing_bank','duplicate_index','wrong_policy','wrong_structure','violating_temperature'])
def test_structural_consumption_rejects_broken_or_relabelled_diagnostics(monkeypatch, error):
    text = (HERE/'reference/structure-inference.json').read_text()
    broken = copy.deepcopy(json.loads(text))
    if error == 'missing_bank':
        broken['observations'].pop()
    elif error == 'duplicate_index':
        row = broken['observations'][0]
        row['compatible_indices'][0] = row['compatible_indices'][1]
    elif error == 'wrong_policy':
        broken['checks'][0]['flow_lpm'][0] += .1
    elif error == 'wrong_structure':
        broken['checks'][0]['rk45']['route'] = 'surface'
    else:
        broken['checks'][0]['rk45']['max_span'] = 1.6
    loads = json.loads
    monkeypatch.setattr(module.json,'loads',lambda value: broken if value == text else loads(value))
    with pytest.raises(ValueError):
        module.structure_observation_values(HERE)
