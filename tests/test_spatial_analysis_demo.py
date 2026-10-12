import json

import pytest

from examples.spatial_analysis_demo import SPECIFICATION, run_demo


def test_fixed_spatial_demo_attains_independent_bounds_and_preserves_input(tmp_path):
    source = tmp_path / 'fixture.json'
    original = json.dumps(SPECIFICATION, indent=2).encode()
    source.write_bytes(original)
    explicit = run_demo(tmp_path / 'explicit', source)
    default = run_demo(tmp_path / 'default')
    # v requires B>=5; u+w requires A+C>=7. Cost is >=17+2A.
    assert explicit['nominal_minimum_cost'] == 17
    assert explicit['nominal_capacity'] == {'A': 0, 'B': 5, 'C': 7}
    # C=(0,8.1),u=(0,2.9) removes Cu, forcing A>=4,B>=5,C>=3.
    assert explicit['guaranteed_minimum_cost'] == 25
    assert explicit['guaranteed_capacity'] == {'A': 4, 'B': 5, 'C': 3}
    assert explicit['maximum_service_after_b_failure_with_total_capacity_12'] == 7
    assert default['original_input_sha256'] == explicit['original_input_sha256']
    assert source.read_bytes() == original == (tmp_path / 'default/input.json').read_bytes()
    audit = json.loads((tmp_path / 'explicit/necessity-audit.json').read_text())
    assert audit['coordinatewise_minima_jointly_feasible'] is False
    edges = json.loads((tmp_path / 'explicit/edge-audit.json').read_text())['edges']
    boundary = next(r for r in edges if r['site'] == 'C' and r['demand'] == 'u')
    assert boundary['distance_km'] == 5 and boundary['nominal_allowed']
    assert boundary['possibly_allowed'] and not boundary['always_allowed']


def test_spatial_demo_refuses_existing_output_and_unknown_angular_units(tmp_path):
    output = tmp_path / 'existing'
    output.mkdir()
    marker = output / 'original.txt'
    marker.write_bytes(b'Keep existing user data')
    with pytest.raises(FileExistsError):
        run_demo(output)
    assert marker.read_bytes() == b'Keep existing user data'
    bad = json.loads(json.dumps(SPECIFICATION))
    bad['coordinates'] = {'system': 'unknown longitude/latitude', 'unit': 'degrees'}
    source = tmp_path / 'bad.json'
    original = json.dumps(bad).encode()
    source.write_bytes(original)
    rejected = tmp_path / 'rejected'
    with pytest.raises(ValueError, match='Cartesian'):
        run_demo(rejected, source)
    assert not rejected.exists() and source.read_bytes() == original
