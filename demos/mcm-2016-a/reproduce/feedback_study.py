"""Read finite-bank feedback evidence without executing historical producers.

An archive audit establishes identity, scope and arithmetic, not the correctness
of every historical future-feasibility calculation. Realized-policy replay is
a separate independent-RHS sampled check, not a fine-grid feedback certificate.
"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
STAGES = ('root', 'expanded', 'no-observer', 'variants', 'variants-resume',
          'drift-counter', 'loss-branch', 'terminal-identity')
STRUCTURES = ('surface_fixed', 'deep_fixed', 'surface_finite')
MODEL_FILES = {'common_reserve.py', 'check_structure.py', 'code/model.py',
               'reference/common-reserve.json', 'reference/common-reserve.npz',
               'reference/structure-decision.json'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_case(row, bank, backup):
    """Never promote a partial fault or timed-out row to a complete service."""
    flows, steps = row['flows'], row['steps']
    require(len(flows) == len(steps) <= 30, 'Incomplete action log')
    require(all(number(q) and 0 <= q <= 2 for q in flows), 'Invalid flow')
    previous, previous_ids = len(bank), set(range(len(bank)))
    for i, (q, step) in enumerate(zip(flows, steps)):
        require(type(step['time_s']) is int and step['time_s'] == i*60,
                'Wrong observation time')
        require(step['flow_lpm'] == q and step['baseline_flow_lpm'] == backup[i],
                'Changed action or backup')
        require(any(abs(q-r*backup[i]) < 1e-12 for r in (0, .8, .9, 1)),
                'Action outside the studied family')
        readings = step['readings']
        require(len(readings) == 2 and all(number(x) for x in readings), 'Invalid reading')
        count = step['retained_models']
        require(type(count) is int and 0 < count <= previous, 'Model set grew or emptied before action')
        previous = count
        if 'model_ids' in step:
            ids = step['model_ids']
            require(len(ids) == len(set(ids)) == count and
                    all(type(x) is int and 0 <= x < len(bank) for x in ids), 'Invalid model identities')
            require(set(ids) <= previous_ids, 'Rejected identity returned')
            previous_ids = set(ids)
    actual = row.get('actual_independent_trace')
    if actual:
        require(actual['recorded_until_s'] == 60*len(flows) and
                actual['full_service'] == (len(flows) == 30) and
                abs(actual['command_water_l']-sum(flows)) < 1e-8, 'Wrong service extent')
    if row['status'] == 'completed':
        require(len(flows) == 30 and (actual is None or actual['full_service']), 'Partial service marked completed')
        metrics = row['independent']
        require(all(number(metrics[k]) for k in ('min_temp','max_temp','max_span','water_l',
                    'instantaneous_balance_residual_w','integrated_balance_residual_j')), 'Invalid replay metric')
        require(metrics['sampled_passed'] is True and metrics['min_temp'] >= 39.13 and
                metrics['max_temp'] <= 40.9 and metrics['max_span'] <= 1.4,
                'Independent trajectory violates common targets')
        multiplier = row['parameters']['flow_multiplier']
        require(number(multiplier) and multiplier > 0 and
                abs(metrics['water_l']-sum(flows)*multiplier) < 1e-8 and
                abs(row['saved_command_l']-(sum(backup)-sum(flows))) < 1e-8,
                'Water arithmetic differs')
        require(metrics['instantaneous_balance_residual_w'] < 1e-6 and
                metrics['integrated_balance_residual_j'] < .1, 'Energy check failed')
    elif row['status'] == 'observations_inconsistent':
        require(len(flows) < 30 and actual and not actual['full_service'] and
                row['detected_s'] == 60*len(flows) and 'saved_command_l' not in row,
                'Fault is not a complete saving')
    else:
        require(row['status'] in ('running', 'prefix_reconstructed'), 'Unknown row status')


def validate_terminal(row):
    t = row['terminal_observation']
    ids = t['model_ids_before']
    require(ids == row['steps'][-1]['model_ids'] and len(set(ids)) == len(ids) and
            t['model_ids_after'] == [] and t['time_s'] == row['detected_s'], 'Wrong terminal identity')
    names = ('predicted_readings', 'previous_bias_lo', 'previous_bias_hi', 'bias_lo', 'bias_hi')
    arrays = {k: np.asarray(t[k], dtype=float) for k in names}
    require(all(x.shape == (len(ids), 2) and np.isfinite(x).all() for x in arrays.values()),
            'Invalid terminal interval shape')
    oldlo, oldhi = arrays['previous_bias_lo'], arrays['previous_bias_hi']
    require(np.all(oldlo <= oldhi) and np.all(oldlo >= -.02) and np.all(oldhi <= .02),
            'Invalid previous bias interval')
    readings = np.asarray(t['readings'], dtype=float)
    require(readings.shape == (2,) and np.isfinite(readings).all(), 'Invalid terminal reading')
    diff = readings-arrays['predicted_readings']
    lo = np.maximum(oldlo, diff-.020002)
    hi = np.minimum(oldhi, diff+.020002)
    require(np.max(abs(lo-arrays['bias_lo'])) < 1e-13 and
            np.max(abs(hi-arrays['bias_hi'])) < 1e-13 and np.all(np.any(lo > hi, axis=1)),
            'Empty set is not supported by stored intervals')
    return float(np.max(lo-hi, axis=1).min())


def feedback_values(root=ROOT):
    root = Path(root)
    manifest = json.loads((root/'reference/feedback-study.json').read_text())
    require(manifest['stages'] == list(STAGES) and manifest['schema_version'] == 1 and
            manifest['status'] == 'archived', 'Changed study scope')
    require(set(manifest['model_source_sha256']) == MODEL_FILES and
            manifest['common_reserve'] == dict(floor=39.13,ceiling=40.9,span=1.4) and
            manifest['physical_limits'] == dict(floor=39,ceiling=41,span=1.5) and
            manifest['probes'] == [89,6] and manifest['sampling_s'] == .5 and
            manifest['reading_noise_bound_c'] == manifest['constant_bias_bound_c'] == .02 and
            manifest['numerical_allowance_c'] == 2e-6, 'Changed conditions or dependencies')
    archive = root/'reference/feedback-study.npz'
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['archive_sha256'], 'Changed feedback archive')
    blobs = {}
    with np.load(archive, allow_pickle=False) as z:
        require(set(z.files) == set(manifest['members']), 'Archive coverage changed')
        for name in z.files:
            require(z[name].dtype == np.uint8 and z[name].ndim == 1, 'Invalid byte archive')
            data = z[name].tobytes()
            require(hashlib.sha256(data).hexdigest() == manifest['members'][name], 'Changed archive member')
            blobs[name] = data
    for name, digest in manifest['model_source_sha256'].items():
        require(hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, 'Stale physical model')
    reserve = json.loads((root/'reference/common-reserve.json').read_text())
    backup = np.repeat(reserve['policies']['passive'], 5).tolist()
    runs, completed = {}, {}
    for stage in STAGES:
        r = json.loads(blobs[stage+'/results.json'])
        require(hashlib.sha256(blobs[stage+'/run.py']).hexdigest() == r['source_sha256'], 'Wrong producer binding')
        bank = r['model_bank']
        keys = [(x['structure'], x['prior_index']) for x in bank]
        require(len(set(keys)) == len(keys), 'Duplicate hypotheses')
        for row in r['results']:
            index = row['truth_bank_index']
            require(type(index) is int and 0 <= index < len(bank) and bank[index]['structure'] == row['truth'],
                    'Invalid truth identity')
            validate_case(row, bank, backup)
            if row['status'] == 'completed':
                completed[(stage, row.get('case', row['truth']))] = row
        runs[stage] = r
    expected = {(s, t) for s in ('root', 'no-observer') for t in STRUCTURES} | {
        ('expanded', 'surface_fixed'), ('variants', 'zero_noise'), ('variants-resume', 'random_noise')}
    require(set(completed) == expected, 'Missing or unexpected complete study cases')
    require(all(len(runs[s]['model_bank']) == 12 for s in ('root', 'no-observer')) and
            runs['root']['model_bank'] == runs['no-observer']['model_bank'], 'Unmatched ablation bank')
    require(all(step['retained_models'] == 12 for row in runs['no-observer']['results']
                for step in row['steps']), 'Ablation silently used readings')
    require(len(runs['expanded']['model_bank']) == len(runs['variants']['model_bank']) ==
            len(runs['variants-resume']['model_bank']) == 1465, 'Wrong expanded-bank size')
    nominal = runs['terminal-identity']['results'][0]
    require(nominal['status'] == 'prefix_reconstructed' and len(nominal['flows']) == 11 and
            nominal['truth_bank_index'] in nominal['terminal_model_ids'], 'Nominal prefix lost truth')
    terminal = {}
    for row in runs['terminal-identity']['results'][1:]:
        require([s['model_ids'] for s in row['steps']] == [s['model_ids'] for s in nominal['steps']],
                'Pre-fault model identities differ')
        terminal[row['case']] = dict(gap_c=validate_terminal(row), detected_s=row['detected_s'])
    require(set(terminal) == {'cool_supply', 'high_loss'}, 'Missing fault evidence')
    mesh_count = 0
    for name in ('mesh-replays.json', 'noise-mesh-replays.json'):
        data = json.loads(blobs[name])
        # These independent fixed-schedule checks retain their original format.
        rows = data['rows']
        require(data['status'] == 'completed', 'Incomplete mesh replay')
        identities = [(x.get('study', 'noise'), x.get('case', x.get('truth')), tuple(x['grid'])) for x in rows]
        require(len(set(identities)) == len(rows) and all(
            x['common_reserve_sampled_pass'] is True and x['sample_s'] == .5 and
            number(x['min_temp']) and x['min_temp'] >= 39.13 and
            number(x['max_temp']) and x['max_temp'] <= 40.9 and
            number(x['max_span']) and x['max_span'] <= 1.4 for x in rows), 'Mesh sample check failed')
        mesh_count += len(rows)
    require(mesh_count == 18, 'Missing realized-policy mesh checks')
    return dict(manifest=manifest, runs=runs, completed=completed, terminal=terminal,
                backup_command_l=sum(backup), recorded_mesh_checks=mesh_count)


def transfer_values(root=ROOT):
    """Audit predeclared off-bank transfer archive; never rerun the search.

    Checks source/receipt identity and declared coverage/arithmetic. Recorded
    interval emptiness is not independent reconstruction of past predictions.
    """
    root = Path(root)
    manifest = json.loads((root/'reference/feedback-transfer.json').read_text())
    archive = root/'reference/feedback-transfer.npz'
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['archive_sha256'],
            'Changed transfer archive')
    with np.load(archive, allow_pickle=False) as z:
        require(set(z.files) == set(manifest['members']), 'Changed transfer members')
        blobs = {name: bytes(z[name]) for name in z.files}
    require(all(hashlib.sha256(blobs[k]).hexdigest() == v for k,v in manifest['members'].items()),
            'Changed transfer member bytes')
    design = json.loads(blobs['design.json'])
    run = json.loads(blobs['results.json'])
    check = json.loads(blobs['check-results.json'])
    require(run['status'] == check['status'] == 'completed' and run['design'] == design,
            'Incomplete or changed transfer conditions')
    require(run['source_sha256'] == hashlib.sha256(blobs['run.py']).hexdigest() and
            check['source_sha256'] == hashlib.sha256(blobs['check.py']).hexdigest() and
            check['producer_results_sha256'] == hashlib.sha256(blobs['results.json']).hexdigest(),
            'Transfer producer/check identity differs')
    require(all(hashlib.sha256(blobs['frozen/'+k]).hexdigest() == h
                for k,h in design['source_snapshot'].items()), 'Transfer input snapshot differs')
    require(all(hashlib.sha256((root/k).read_bytes()).hexdigest() == h
                for k,h in design['source_snapshot'].items()), 'Current transfer dependencies differ')
    require(0 < run['elapsed_s'] <= design['external_watchdog_s'] and
            0 < check['elapsed_s'] <= design['reserve_checks_s'], 'Transfer budget exceeded')
    cases = {x['case']:x for x in run['results']}
    require(len(cases) == len(run['results']) == len(design['cases']) == 6,
            'Missing or repeated transfer case')
    complete, refused = {}, {}
    backup = np.repeat(json.loads(blobs['frozen/reference/common-reserve.json'])['policies']['passive'],5)
    for spec in design['cases']:
        row = cases[spec['id']]
        require(row['route'] == spec['route'] and row['body_capacity'] == spec['capacity'] and
                all(row['parameters'][k] == v for k,v in spec['changes'].items()) and
                row['truth_is_bank_member'] is False, 'Changed transfer truth')
        require(len(row['flows']) == len(row['steps']), 'Missing transfer actions')
        previous = set(range(1465))
        for i,(q,step) in enumerate(zip(row['flows'],row['steps'])):
            ids = set(step['model_ids'])
            require(number(q) and q >= 0 and step['time_s'] == i*60 and
                    step['flow_lpm'] == q and step['baseline_flow_lpm'] == backup[i] and len(ids) == step['retained_models'] and
                    ids and ids <= previous and len(ids) == len(step['model_ids']) and
                    any(abs(q-r*step['baseline_flow_lpm']) < 1e-12 for r in (0,.8,.9,1)),
                    'Transfer action/identity differs')
            previous = ids
        actual = row['actual_independent_trace']
        require(actual['recorded_until_s'] == 60*len(row['flows']) and
                abs(actual['command_water_l']-sum(row['flows'])) < 1e-8,
                'Transfer extent or command arithmetic differs')
        if row['status'] == 'completed_model_conditional_service':
            require(len(row['flows']) == 30 and actual['full_service'] is True and
                    row['independent']['sampled_passed'] is True and
                    abs(row['independent']['water_l']-sum(row['flows'])*row['parameters']['flow_multiplier']) < 1e-8,
                    'Incomplete service called complete')
            complete[row['case']] = row
        else:
            require(row['status'] == 'observations_inconsistent' and len(row['flows']) < 30 and
                    actual['full_service'] is False and row['detected_s'] == 60*len(row['flows']),
                    'Partial transfer service counted as complete')
            terminal = row['terminal_observation']
            lo,hi = (np.asarray(terminal[k],dtype=float) for k in ('bias_lo','bias_hi'))
            require(terminal['model_ids_after'] == [] and set(terminal['model_ids_before']) == previous and
                    lo.shape == hi.shape == (len(previous),2) and
                    np.isfinite(lo).all() and np.isfinite(hi).all() and np.any(lo>hi,axis=1).all(),
                    'Recorded terminal intervals not empty')
            refused[row['case']] = row
    expected = {(name,(8,4,3)) for name in cases} | {
        (name,grid) for name in complete for grid in ((12,6,4),(16,8,6))}
    keys = [(x['case'],tuple(x['grid'])) for x in check['rows']]
    require(len(keys) == len(set(keys)) and set(keys) == expected and len(complete) == 2 and len(refused) == 4,
            'Incomplete transfer replay coverage')
    for r in check['rows']:
        source = cases[r['case']]
        require(r['actions'] == len(source['flows']) and r['covered_s'] == 60*r['actions'] and
                r['complete_service'] == (source['case'] in complete) and r['sample_s'] == .5 and
                abs(r['command_l']-sum(source['flows'])) < 1e-8 and
                abs(r['actual_l']-r['command_l']*source['parameters']['flow_multiplier']) < 1e-8,
                'Replay changed action extent or delivered water')
        require(r['instantaneous_balance_residual_w'] < 1e-6 and
                r['integrated_balance_residual_j'] < .1 and r['max_dynamic_row_sum'] <= 1e-12 and
                r['min_offdiag'] >= 0, 'Transfer balance/contraction premise failed')
        low,high,span = r['numeric_envelope_c']
        require(all(number(v) for v in (low,high,span)) and low <= high and span >= 0 and
                r['physical_numeric_envelope_passed'] == (low >= 39 and high <= 41 and span <= 1.5) and
                r['reserve_numeric_envelope_passed'] == (low >= 39.13 and high <= 40.9 and span <= 1.4) and
                r['reserve_numeric_envelope_passed'], 'Transfer envelope flags differ from bounds')
    return dict(manifest=manifest,design=design,completed=complete,refused=refused,checks=check['rows'])


def continuous_values(root=ROOT):
    """Audit fixed-action parameter-box evidence; no numerical recomputation."""
    root = Path(root)
    manifest = json.loads((root/'reference/continuous-transfer.json').read_text())
    archive = root/'reference/continuous-transfer.npz'
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['archive_sha256'], 'Changed continuum archive')
    with np.load(archive, allow_pickle=False) as z:
        require(set(z.files) == set(manifest['members']), 'Changed continuum members')
        blobs = {k:bytes(z[k]) for k in z.files}
    require(all(hashlib.sha256(blobs[k]).hexdigest() == h for k,h in manifest['members'].items()), 'Changed continuum bytes')
    design = json.loads(blobs['structured/design.json'])
    run = json.loads(blobs['structured/results.json'])
    prior = json.loads(blobs['results.json'])
    check = json.loads(blobs['structured/check-results.json'])
    require(run['status'] == prior['status'] == check['status'] == 'completed' and run['design'] == design,
            'Incomplete continuum experiment')
    require(run['source_sha256'] == hashlib.sha256(blobs['structured/derive.py']).hexdigest() and
            prior['source_sha256'] == hashlib.sha256(blobs['derive.py']).hexdigest() and
            design['previous_result_sha256'] == hashlib.sha256(blobs['results.json']).hexdigest(), 'Changed continuum producer')
    require(all(hashlib.sha256(blobs[k]).hexdigest() == h for k,h in design['source_sha256'].items()), 'Changed continuum dependency')
    for k,h in check['source_sha256'].items():
        require(hashlib.sha256(blobs[k]).hexdigest() == h, 'Changed continuum checker dependency')
    require(design['parameters'] == ['D','h_surface','h_body','flow_multiplier'] and
            design['scales'] == [1,.5,.25,.1] and design['base_halfwidths'] == [2.5e-5,.625,1.25,.0125] and
            design['sample_s'] == .5, 'Changed predeclared box')
    expected = {(c,tuple(g)) for c in design['cases'] for g in design['grids']}
    keys = [(r['case'],tuple(r['grid'])) for r in run['rows']]
    require(len(keys) == 6 and len(set(keys)) == 6 and set(keys) == expected, 'Missing continuum objects')
    frozen = {r['case']:r for r in json.loads(blobs['frozen/transfer-results.json'])['results']}
    indexed = dict(zip(keys,run['rows']))
    for row in run['rows']:
        original = frozen[row['case']]
        require(row['flows'] == original['flows'] and row['parameters'] == original['parameters'] and row['route'] == original['route'], 'Changed frozen actions or truth')
        require([s['scale'] for s in row['scales']] == design['scales'], 'Changed continuum scale coverage')
        for s in row['scales']:
            require(s['halfwidths'] == {k:w*s['scale'] for k,w in zip(design['parameters'],design['base_halfwidths'])}, 'Changed continuum halfwidths')
            low,high,span = s['temperature_bounds_c']
            require(all(number(v) for v in (low,high,span)) and low <= high and span >= 0 and
                    s['physical_passed'] == (low>=39 and high<=41 and span<=1.5) and
                    s['reserve_passed'] == (low>=39.13 and high<=40.9 and span<=1.4), 'Continuum flags differ from bounds')
            q = sum(row['flows']);alpha = row['parameters']['flow_multiplier'];width = s['halfwidths']['flow_multiplier']
            require(abs(s['command_l']-q)<1e-9 and np.allclose(s['actual_l_range'],[q*(alpha-width),q*(alpha+width)],atol=1e-9,rtol=0), 'Changed continuum water units')
    qualified = [s for s in design['scales'] if all(next(x for x in r['scales'] if x['scale']==s)['physical_passed'] for r in run['rows'])]
    chosen = max(qualified) if qualified else min(design['scales'])
    require(check['selected_scale'] == chosen, 'Checker selected another scale')
    from itertools import product
    points = set(product((-1,1),repeat=4)) | {(0,0,0,0)}
    identities = [(r['case'],tuple(r['grid']),tuple(r['point'])) for r in check['rows']]
    require(len(identities)==102 and len(set(identities))==102 and set(identities)=={(c,g,p) for c,g in expected for p in points}, 'Missing independent corners')
    for row in check['rows']:
        source = indexed[(row['case'],tuple(row['grid']))]
        s = next(x for x in source['scales'] if x['scale']==chosen)
        p = dict(source['parameters'])
        for k,z in zip(design['parameters'],row['point']):p[k] += z*s['halfwidths'][k]
        require(row['parameters'] == p and row['certificate_bounds_c'] == s['temperature_bounds_c'], 'Changed checked corner')
        actual = row['result'];lo,hi,sp = row['certificate_bounds_c']
        require(actual['sample_s']==.5 and actual['route']==source['route'] and actual['body_capacity_j_per_k'] is None and
                actual['min_temp']>=lo-2e-6 and actual['max_temp']<=hi+2e-6 and actual['max_span']<=sp+4e-6 and
                actual['instantaneous_balance_residual_w']<1e-6 and actual['integrated_balance_residual_j']<.1 and
                abs(actual['water_l']-sum(source['flows'])*p['flow_multiplier'])<1e-9, 'Independent continuum challenge failed')
    require(run['cumulative_producer_s']<=design['producer_budget_s'] and check['elapsed_s']<=design['independent_check_budget_s'], 'Continuum budget exceeded')
    return dict(manifest=manifest,rows=run['rows'],scale=chosen,checks=check['rows'],previous=prior)
