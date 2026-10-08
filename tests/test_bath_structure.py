import importlib.util
from pathlib import Path

import numpy as np
import pytest


def test_finite_contact_storage_matches_two_reservoir_closed_form():
    path = Path(__file__).resolve().parents[1] / 'demos/mcm-2016-a/reproduce/check_structure.py'
    spec = importlib.util.spec_from_file_location('bath_structure', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Two identical water cells exchange with a body node of equal total capacity.
    # No inlet, environmental loss or intercell transport: the mean stays 35 C
    # and the water/body difference decays with rate H*(1/Cw+1/Cb)=0.02 /s.
    net = dict(grid=[2, 1, 1], cap=np.array([1000., 1000.]),
               ha=np.zeros(2), hb=np.array([10., 10.]), G=np.zeros((2, 2)),
               region=np.ones(2, dtype=bool))
    p = dict(initial=40., body_temp=30., horizon=100., rho=1000., cp=4180.,
             air_temp=22., inlet_temp=50., floor=30., ceiling=50., span=2.)
    result = module.replay(p, net, [0.], body_capacity=2000.)
    assert result['min_temp'] == pytest.approx(35+5*np.exp(-2), abs=1e-8)
    assert result['final_body_temp_c'] == pytest.approx(35-5*np.exp(-2), abs=1e-8)
    assert result['integrated_balance_residual_j'] < 1e-6


def test_archived_constant_envelope_meets_unrelaxed_limits():
    import json
    path = Path(__file__).resolve().parents[1] / 'demos/mcm-2016-a/reproduce/reference/checks.json'
    checks = json.loads(path.read_text())
    item = next(c for c in checks if c['name'] == 'continuous_time_policy_envelope')
    evidence = json.loads(item['evidence'])
    assert item['passed']
    assert evidence['feasibility_tolerance_c'] == 0
    assert evidence['largest_sample_gap_s'] <= .5
    assert evidence['lower_temperature_bound_c'] >= evidence['floor_c']
    assert evidence['upper_temperature_bound_c'] <= evidence['ceiling_c']
    assert evidence['span_upper_bound_c'] <= evidence['span_limit_c']
