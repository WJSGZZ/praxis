"""Check scope and independent evidence before exposing new report values.

This consumes archived checks; it neither reruns a simulation nor certifies
floating-point error with interval arithmetic. Generated center traces can be
regenerated from the bundled source and stay outside the installation artifact.
"""
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def require(value, message):
    if not value:
        raise ValueError(message)


def archive(root, name):
    with np.load(Path(root)/'reference'/f'{name}.npz', allow_pickle=False) as a:
        files = {key: a[key].tobytes() for key in a.files}
    read = lambda key: json.loads(files[key])
    manifest = read('manifest.json')
    require(set(files) == set(manifest['members']) | {'manifest.json'}, 'Research members differ')
    for key, digest in manifest['members'].items():
        require(hashlib.sha256(files[key]).hexdigest() == digest, 'Research member stale: '+key)
    def bindings(record):
        for key, digest in record['source_sha256'].items():
            actual = (hashlib.sha256(files[key]).hexdigest() if key in files
                      else manifest['omitted_generated_traces'].get(key))
            require(actual == digest, 'Research source or trace stale: '+key)
    return files, read, manifest, bindings


def constant_exclusion(root):
    files, read, manifest, bindings = archive(root, 'constant-exclusion')
    checks = read('checks.json')
    require(checks['status'] == 'completed', 'Exclusion checks incomplete')
    bindings(checks)
    runs = []
    for prefix, grid in zip(['', 'mesh288/', 'mesh768/', 'feasible-control/'],
                            [(8,4,3), (12,6,4), (16,8,6), (8,4,3)]):
        run = read(prefix+'results.json'); design = read(prefix+'design.json')
        require(run['design'] == design and tuple(design['grid']) == grid,
                'Exclusion design or grid differs')
        for key, digest in run['source_sha256'].items():
            require(hashlib.sha256(files[prefix+key]).hexdigest() == digest,
                    'Exclusion producer stale')
        require(run['trace_sha256'] == manifest['omitted_generated_traces'][prefix+'centers.npz'],
                'Exclusion trace identity differs')
        p = design['parameters']
        require(design['rate_interval_lpm'] == [0,3] and design['time_witness_grid_s'] == 5
                and design['numerical_error_assumption_c'] == 2e-6
                and p['initial'] == 40 and p['body_temp'] == 34 and p['horizon'] == 1800
                and (p['floor'],p['ceiling'],p['span']) == (39,41,1.5), 'Exclusion scope differs')
        independent = [x for x in checks['rows'] if tuple(x['grid']) == grid and x['control_D'] == p['D']]
        require(run['evaluations'] == len(run['records']) == len(independent), 'Exclusion center coverage differs')
        keyed = {x['center_lpm']:x for x in independent}
        require(len(keyed) == len(independent), 'Duplicate independent center')
        for rec in run['records']:
            q = rec['center_lpm']; w = rec['witness']; h = rec['radius_lpm']
            require(q == (rec['lo_lpm']+rec['hi_lpm'])/2 and h == (rec['hi_lpm']-rec['lo_lpm'])/2,
                    'Rate center or radius differs')
            values = [w['U'], w['S'], w['R'], w['margin_c'], w['time_s']]
            require(all(math.isfinite(x) for x in values) and w['R'] >= 0
                    and 0 <= w['time_s'] <= 1800 and w['time_s'] % 5 == 0, 'Invalid exclusion witness')
            radius = h*(abs(w['S'])+2e-6)+h*h*w['R']+2e-6
            if w['kind'] == 'floor': margin = 39-w['U']-radius
            elif w['kind'] == 'ceiling': margin = w['U']-41-radius
            elif w['kind'] == 'spread': margin = w['U']-1.5-2*radius
            else: raise ValueError('Unknown exclusion witness')
            # A spread uses the sensitivity difference once; both state errors/remainders twice.
            if w['kind'] == 'spread':
                margin = w['U']-1.5-h*(abs(w['S'])+4e-6)-2*h*h*w['R']-4e-6
            require(math.isclose(margin,w['margin_c'],abs_tol=1e-9) and rec['excluded'] == (margin>1e-5),
                    'Exclusion witness arithmetic differs')
            row = keyed.get(q, {})
            require(row.get('passed') is True and row['excluded'] == rec['excluded']
                    and row['max_state_difference_c'] < 2e-6 and row['max_sensitivity_difference'] < 2e-6
                    and math.isclose(row['witness_margin_c'],margin,abs_tol=1e-7),
                    'Independent exclusion check differs')
        if prefix == 'feasible-control/':
            require(p['D'] == .001 and run['status'] == 'incomplete_unresolved'
                    and run['unresolved_intervals'] and run['records'][-1]['sampled_center_physical_passed'],
                    'Feasible control incorrectly promoted to infeasibility')
        else:
            require(p['D'] == .0003 and run['status'] == 'conditional_interval_exclusion_complete'
                    and not run['unresolved_intervals'], 'Incomplete exclusion promoted')
            edge = Decimal('0'); records = {x['trace_key']:x for x in run['records']}
            for leaf in sorted(run['excluded_intervals'],key=lambda x:x['lo_lpm']):
                require(leaf == records.get(leaf['trace_key']) and leaf['excluded']
                        and Decimal(str(leaf['lo_lpm'])) == edge, 'Exclusion cover has gap or unsupported leaf')
                edge = Decimal(str(leaf['hi_lpm']))
            require(edge == Decimal('3'), 'Exclusion cover incomplete')
        runs.append(run)
    require(len(checks['rows']) == sum(x['evaluations'] for x in runs)
            and len(checks['analytic_cases']) == 6 and all(x['passed'] for x in checks['analytic_cases']),
            'Independent or analytic coverage differs')
    return dict(runs=runs, checks=checks, files=files)


def recourse_transfer(root):
    files, read, manifest, bindings = archive(root, 'recourse-transfer')
    run = read('results.json'); design = read('design.json'); checks = read('checks.json'); screen = read('screen-checks.json')
    for record in [run,checks,screen]:
        require(record['status'] == 'completed', 'Transfer incomplete'); bindings(record)
    require(run['design'] == design and design['handoff_s'] == 540 and design['horizon_s'] == 1800
            and design['physical_limits'] == dict(floor=39,outside_ceiling=41,spread=1.5), 'Transfer scope differs')
    old = read('frozen/catalog-run.json')
    require(run['catalog'] == old['catalog'] and len(run['catalog']) == 54, 'Transfer catalog changed')
    truth = design['truth']; catalog = {x['id']:x for x in run['catalog']}
    require(all(truth['parameters'] != x['parameters'] for x in catalog.values()), 'Transfer truth is not excluded')
    require(len(run['rows']) == 1, 'Transfer is not the declared single condition')
    row = run['rows'][0]; chosen = row['selected']; ids = row['survivors']; previous = row['preterminal_survivors']
    require(row['prefix_flows'] == design['prefix_flows'] and row['refusal_s'] == design['handoff_s']
            and 'not a newly executed' in row['handoff_type'] and row['status'] == 'tail_qualified'
            and 0 <= row['decision_elapsed_s'] < 60 and ids and set(ids) <= set(previous) <= set(catalog),
            'Invalid diagnostic handoff or acceptance')
    require(len(row['bridge_records']) == len(previous)
            and {x['id'] for x in row['bridge_records']} == set(previous)
            and all(x['passed'] for x in row['bridge_records']), 'Transfer bridge differs')
    candidates = row['candidates']
    require([x['q_lpm'] for x in candidates] == [i/20 for i in range(len(candidates))]
            and candidates[-1]['qualified'] and not any(x['qualified'] for x in candidates[:-1])
            and chosen['q_lpm'] == candidates[-1]['q_lpm'], 'Transfer ascending choice differs')
    tail = (1800-540-60)/60*chosen['q_lpm']
    require(math.isclose(chosen['remainder_command_l'],tail,abs_tol=1e-9)
            and math.isclose(chosen['total_command_l'],math.fsum(row['prefix_flows'])+tail,abs_tol=1e-9),
            'Transfer command arithmetic differs')
    expected = {(identity,grid) for identity in ids+['excluded_actual_truth'] for grid in [(8,4,3),(12,6,4),(16,8,6)]}
    keys = [(x['hypothesis'],tuple(x['grid'])) for x in checks['rows']]
    require(len(keys) == len(set(keys)) and set(keys) == expected, 'Transfer independent truth coverage differs')
    for x in checks['rows']:
        a = x['actual']; parameters = truth['parameters'] if x['hypothesis'] == 'excluded_actual_truth' else catalog[x['hypothesis']]['parameters']
        require(x['passed'] is True and a['sampled_passed'] is True and a['min_temp'] >= 39
                and a['max_temp'] <= 41 and a['max_span'] <= 1.5
                and a['instantaneous_balance_residual_w'] < 1e-6 and a['integrated_balance_residual_j'] < .1
                and math.isclose(x['command_l'],chosen['total_command_l'],abs_tol=1e-9)
                and math.isclose(a['water_l'],chosen['total_command_l']*parameters['flow_multiplier'],abs_tol=1e-8),
                'Transfer trajectory or delivered water differs')
    history = screen['rows'][0]
    require(history['retained'] == ids and history['preterminal'] == previous and len(history['records']) == 54
            and len(screen['rows'][1]['records']) == 54 and not screen['rows'][1]['retained'], 'Transfer history or negative control differs')
    return dict(run=run, row=row, checks=checks, files=files)


def all_control_exclusion(root):
    """Bind a fixed-network certificate; full rational replay is verify_exact.py.

    This archive audit checks identity and scope, not the solver status alone.
    The executable verifier reconstructs every row from exact archived primitives.
    """
    files, read, manifest, bindings = archive(root, 'all-control-exclusion')
    exact=read('portable-exact-checks.json'); run=read('results.json'); independent=read('checks.json')
    require(exact['status']=='completed' and independent['status']=='completed', 'All-control checks incomplete')
    for record in (exact,run,independent):
        require(all(hashlib.sha256(files[f]).hexdigest()==h for f,h in record['sha256'].items()), 'All-control source stale')
    require(exact['rational_rows']==61869 and exact['variables']==12399
            and exact['exact_verified_threshold']==dict(numerator=1,denominator=5000,unit='C per30s integrated-balance residual')
            and exact['corrected_bound_float_display']>1/5000
            and exact['global_50c_barrier_max_rhs_c_per_s']<0 and exact['min_dynamic_sink_w_per_k']>0,
            'All-control certificate or invariant differs')
    require(len(run['rows'])==2 and run['rows'][0]['grid']==[8,4,3]
            and run['rows'][0]['D']==.0003 and run['rows'][0]['success'] is True
            and run['rows'][1]['D']==.001 and run['rows'][1]['success'] is False
            and run['rows'][1]['status']==1, 'All-control/control status differs')
    require(independent['known_feasible_flux_integral_matrix_residual']<1e-7
            and len(independent['known_feasible_stage_metrics'])==60
            and all(x[0]>=39 and x[1]<=41 and x[2]<=1.5 for x in independent['known_feasible_stage_metrics']),
            'All-control negative trajectory check differs')
    return dict(exact=exact,run=run,checks=independent,files=files)
