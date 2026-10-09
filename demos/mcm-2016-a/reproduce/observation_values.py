"""Validate the finite observation-control evidence before report consumption."""
import hashlib
import itertools
import json
from pathlib import Path


def observation_values(root):
    root = Path(root)
    screening = json.loads((root/'reference/observation-screening.json').read_text())
    control = json.loads((root/'reference/observation-control.json').read_text())
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(screening['status'] == control['status'] == 'completed', 'Observation study incomplete')
    require(hashlib.sha256((root/'screen_observations.py').read_bytes()).hexdigest() == screening['research_source_sha256'], 'Observation screening source stale')
    require(hashlib.sha256((root/'study_observation_control.py').read_bytes()).hexdigest() == control['source_sha256'], 'Observation control source stale')
    require(hashlib.sha256((root/'reference/observation-screening.json').read_bytes()).hexdigest() == control['input_sha256'], 'Observation bank stale')
    for hashes in [screening['input_sha256'], control['physical_source_sha256']]:
        require(all(hashlib.sha256((root/name).read_bytes()).hexdigest() == digest for name,digest in hashes.items()), 'Observation physical evidence stale')
    cal = json.loads((root/'reference/calibration-study.json').read_text())
    keys = list(cal['parameter_grid'])
    prior = [dict(zip(keys, values)) for values in itertools.product(*cal['parameter_grid'].values())]
    banks = {(r['truth'],r['design']): r for r in screening['results']}
    rows = {(r['truth'],r['design']): r for r in control['completed']}
    expected = {(t,d) for t in screening['truths'] for d in screening['designs']}
    require(set(rows) == set(banks) == expected and len(rows) == len(control['completed']) == len(screening['results']), 'Observation groups missing or duplicated')
    checked = 0
    for key, row in rows.items():
        bank = banks[key]; indices = bank['indices']
        require(len(indices) == len(set(indices)) == row['models'] == bank['compatible_models'], 'Observation bank coverage differs')
        require(all(0 <= i < len(prior) for i in indices), 'Observation prior index invalid')
        if not row['accepted']:
            require(not row['independent'], 'Rejected search has ambiguous accepted evidence')
            continue
        candidate = row['selected']; q = candidate['flow_lpm']; water = candidate['command_l']
        require(len(q) == 6 and all(0 <= v <= 2 for v in q) and abs(water - 5*sum(q)) < 1e-8, 'Observation candidate arithmetic differs')
        records = row['independent']
        record_keys = {(r['model_index'], tuple(r['grid'])) for r in records}
        require(len(records) == len(record_keys) and record_keys == {(i,g) for i in range(len(indices)) for g in [(8,4,3),(12,6,4),(16,8,6)]}, 'Observation envelope coverage incomplete')
        for record in records:
            prior_index = indices[record['model_index']]
            require(record['prior_index'] == prior_index, 'Observation prior binding differs')
            require(record['continuous_passed'] and record['lower_temperature_bound_c'] >= 39 and record['upper_temperature_bound_c'] <= 41 and record['span_upper_bound_c'] <= 1.5, 'Observation physical envelope failed')
            require(abs(record['water_l'] - water*prior[prior_index]['flow_multiplier']) < 1e-8, 'Observation delivered water differs')
        checked += len(records)
    # Report conditional physical acceptance separately from solver convergence.
    return dict(screening=screening, rows=rows, independent_checks=checked)


def structure_observation_values(root):
    """Bind structural fit diagnostics separately from policy-bank certification."""
    root = Path(root)
    receipt = json.loads((root/'reference/structure-inference.json').read_text())
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(receipt['status'] == 'completed', 'Structural observation study incomplete')
    require(hashlib.sha256((root/'study_structure_inference.py').read_bytes()).hexdigest() == receipt['source_sha256'], 'Structural observation source stale')
    require(all(hashlib.sha256((root/name).read_bytes()).hexdigest() == digest for name,digest in receipt['inputs'].items()), 'Structural observation inputs stale')
    cal = json.loads((root/'reference/calibration-study.json').read_text())
    control = json.loads((root/'reference/observation-control.json').read_text())
    prior_size = 1
    for values in cal['parameter_grid'].values():
        prior_size *= len(values)
    require(receipt['parameter_count'] == prior_size and receipt['probes'] == cal['probes'], 'Structural observation prior/probes differ')
    expected = {(t,s,d) for t in receipt['truths'] for s in receipt['structures'] for d in receipt['designs']}
    rows = receipt['observations']
    require(len(rows) == len(expected) and {(r['truth'],r['structure'],r['design']) for r in rows} == expected, 'Structural observation coverage incomplete')
    for row in rows:
        indices = row['compatible_indices']
        require(row['compatible_count'] == len(indices) == len(set(indices)) and all(isinstance(i,int) and 0 <= i < prior_size for i in indices), 'Structural observation bank differs')
        require(row['minimum_residual_c'] >= 0 and (not indices or row['minimum_residual_c'] <= receipt['reading_bound_c']), 'Structural observation residual differs')
    accepted = {(r['truth'],r['design']): r for r in control['completed'] if r['accepted']}
    checks = receipt['checks']
    expected_checks = {(t,s,d) for t,d in accepted for s in receipt['structures']}
    require(len(checks) == len(expected_checks) and {(r['truth'],r['structure'],r['policy_design']) for r in checks} == expected_checks, 'Structural fixed-policy coverage incomplete')
    for row in checks:
        policy = accepted[(row['truth'],row['policy_design'])]['selected']
        replay = row['rk45']; exact = row['exact']
        require(row['flow_lpm'] == policy['flow_lpm'] and abs(replay['water_l'] - policy['command_l']) < 1e-8, 'Structural fixed-policy binding differs')
        route, capacity = receipt['structures'][row['structure']]
        require(replay['route'] == route and replay['body_capacity_j_per_k'] == capacity and replay['sample_s'] == 1., 'Structural replay mechanism/sampling differs')
        require(replay['sampled_passed'] and replay['min_temp'] >= 39 and replay['max_temp'] <= 41 and replay['max_span'] <= 1.5, 'Structural sampled replay failed')
        difference = max(abs(exact[k]-replay[k]) for k in exact)
        require(abs(difference-row['maximum_method_difference_c']) < 1e-12 and difference < 2e-6, 'Structural four-summary comparison differs')
        require(replay['instantaneous_balance_residual_w'] < 1e-6 and replay['integrated_balance_residual_j'] < .1, 'Structural energy check failed')
    return dict(receipt=receipt, observation_count=len(rows), replay_count=len(checks), all_banks_nonempty=all(r['compatible_count'] > 0 for r in rows), maximum_summary_difference_c=max(r['maximum_method_difference_c'] for r in checks))
