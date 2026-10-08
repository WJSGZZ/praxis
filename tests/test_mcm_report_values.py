"""Report-level dependencies must change with evidence, or reject stale joins."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'demos/mcm-2016-a/reproduce'
spec = importlib.util.spec_from_file_location('mcm_report_values', HERE / 'report_values.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def evidence():
    return [json.loads((HERE / 'reference' / (name + '.json')).read_text())
            for name in ('results', 'extended', 'mesh_check', 'structure')]


def test_geometry_and_structural_counterfactuals_propagate_without_new_solver():
    original = evidence()
    altered = deepcopy(original)
    altered[0]['parameters']['body_volume'] += .001  # 1 litre less water
    body = next(row for row in altered[3]['rows'] if row['policy'] == 'scheduled'
                and row['route'] == 'surface' and row['body_capacity_j_per_k'] is not None)
    body['min_temp'] -= .1  # formerly positive improvement must become negative
    body['final_body_temp_c'] += 1
    altered[1]['control']['robust_tolerance']['random_error']['0.10']['share_within_limits'] = .4
    before = module.report_values(*original)
    after = module.report_values(*altered)
    assert after['water_volume_l'] == pytest.approx(before['water_volume_l'] - 1)
    assert before['body_minimum_change_c'] > 0 > after['body_minimum_change_c']
    assert after['final_body_temp_c'] == pytest.approx(before['final_body_temp_c'] + 1)
    assert after['tap_error_share'] == .4
    assert altered[2] == original[2]  # no optimization record was changed


def test_refuse_a_report_whose_scheduled_water_disagrees_with_flow():
    inputs = evidence()
    inputs[2]['accepted_schedule']['water_l'] += 1
    with pytest.raises(ValueError, match='volume'):
        module.report_values(*inputs)


def test_refuse_transferring_tap_error_results_to_a_different_schedule():
    inputs = evidence()
    accepted = inputs[2]['accepted_schedule']
    accepted['flow_lpm'][1] += .1
    accepted['water_l'] += .1 * accepted['segment_s'] / 60
    with pytest.raises(ValueError, match='different buffered policy'):
        module.report_values(*inputs)


def test_report_helper_is_in_explicit_plugin_export():
    from scripts.build_plugin import public_files
    assert HERE / 'report_values.py' in public_files(ROOT)


def test_reject_a_real_other_buffer_whose_error_distribution_was_not_replayed():
    inputs = evidence()
    other = next(row for row in inputs[1]['control']['buffer_price']
                 if row['buffer_c'] == .2)
    assert other['water_l'] is not None
    inputs[2]['accepted_schedule'].update(other)
    with pytest.raises(ValueError, match='different buffered policy'):
        module.report_values(*inputs)
