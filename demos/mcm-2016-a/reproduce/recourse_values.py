"""Consume scoped recovery evidence; hashes do not replace mathematical checks."""
import hashlib
import io
import json
import math
from pathlib import Path
import numpy as np


def require(condition, message):
    if not condition:
        raise ValueError(message)


def recourse_values(root):
    with np.load(Path(root)/'reference/recourse-study.npz', allow_pickle=False) as archive:
        files = {name: archive[name].tobytes() for name in archive.files}
    read = lambda name: json.loads(files[name])
    manifest = read('manifest.json')
    require(set(files) == set(manifest['members']) | {'manifest.json'}, 'Recourse members differ')
    for name, digest in manifest['members'].items():
        require(hashlib.sha256(files[name]).hexdigest() == digest, 'Recourse member changed: '+name)
    names = ['results-expanded.json', 'checks-expanded.json', 'screen-checks.json',
             'results-lagged.json', 'checks-lagged.json', 'screen-checks-lagged.json',
             'rejected-checks.json']
    for name in names:
        record = read(name)
        require(record['status'] == 'completed', 'Recourse evidence incomplete')
        for source, digest in record['source_sha256'].items():
            require(source in files and hashlib.sha256(files[source]).hexdigest() == digest,
                    'Recourse source or result stale: '+source)
    run, checks, screen = [read(n) for n in names[3:6]]
    require(run['design'] == read('design-lagged.json'), 'Recourse design differs')
    require(run['design']['physical_limits'] == dict(floor=39, outside_ceiling=41, spread=1.5),
            'Recourse physical limits changed')
    catalog = {x['id']:x for x in run['catalog']}
    require(len(catalog) == len(run['catalog']) == 54, 'Recourse catalog identity differs')
    with np.load(io.BytesIO(files['frozen/feedback-transfer.npz']), allow_pickle=False) as old:
        original = json.loads(old['results.json'].tobytes())
    expected_catalog = {}
    for truth in original['results']:
        for di, scale in enumerate([.975, 1, 1.025]):
            for hi, offset in enumerate([-.625, 0, .625]):
                parameters = dict(truth['parameters'])
                parameters['D'] *= scale
                parameters['h_surface'] += offset
                identity = f"{truth['case']}/D{di}H{hi}"
                expected_catalog[identity] = dict(id=identity, parameters=parameters,
                    route=truth['route'], capacity=truth['body_capacity'])
    require(catalog == expected_catalog, 'Recourse catalog is not the declared Cartesian expansion')
    original = {x['case']:x for x in original['results'] if x['status']=='observations_inconsistent'}
    require(len(run['rows']) == len(original) == 4 and set(x['case'] for x in run['rows']) == set(original),
            'Recourse fault coverage differs')
    screening = {x['case']:x for x in screen['rows']}
    expected = set()
    for row in run['rows']:
        old = original[row['case']]
        require(row['prefix_flows'] == old['flows'] and row['refusal_s'] == old['detected_s'] and
                row['readings'] == [x['readings'] for x in old['steps']]+[old['terminal_observation']['readings']],
                'Recourse original history changed')
        ids, previous = row['survivors'], row['preterminal_survivors']
        require(ids and len(ids)==len(set(ids)) and set(ids)<=set(previous)<=set(catalog) and
                len(previous)==len(set(previous)), 'Recourse compatible identities invalid')
        sr = screening[row['case']]
        require(sr['retained']==ids and sr['preterminal']==previous and
                {x['id'] for x in sr['records']}==set(catalog) and len(sr['records'])==54,
                'Independent history coverage differs')
        bridge = row['bridge_records']
        require(len(bridge)==len(previous) and {x['id'] for x in bridge}==set(previous), 'Bridge coverage differs')
        records = bridge + [x for c in row['candidates'] for x in c['records']]
        for x in records:
            low, high, spread = x['bounds_c']
            require(all(math.isfinite(v) for v in [low,high,spread]), 'Nonfinite recourse bound')
            if x['passed']:
                require(low>=39 and high<=41 and spread<=1.5, 'Recourse physical bound violated')
        require(all(x['passed'] is True for x in bridge), 'Bridge unqualified')
        require(row['status']=='tail_qualified' and row['selected'] is not None and
                0 <= row['decision_elapsed_s'] < 60, 'Timed-out or failed recourse promoted')
        candidates = row['candidates']
        require(candidates and [c['q_lpm'] for c in candidates]==[i/20 for i in range(len(candidates))],
                'Recourse finite ascending search differs')
        for c in candidates:
            require(len(c['records'])==len(ids) and {x['id'] for x in c['records']}==set(ids) and
                    c['qualified']==all(x['passed'] is True for x in c['records']), 'Recourse candidate scope differs')
        chosen = row['selected']
        require(candidates[-1]['qualified'] and not any(c['qualified'] for c in candidates[:-1]) and
                chosen['q_lpm']==candidates[-1]['q_lpm'], 'Recourse choice is not first qualifying rate')
        remaining = (1800-row['refusal_s']-60)/60
        require(remaining>0 and math.isclose(chosen['remainder_command_l'],remaining*chosen['q_lpm'],abs_tol=1e-9) and
                math.isclose(chosen['total_command_l'],math.fsum(row['prefix_flows'])+chosen['remainder_command_l'],abs_tol=1e-9),
                'Recourse water or delay units differ')
        expected.update((row['case'],identity,grid) for identity in ids for grid in [(8,4,3),(12,6,4),(16,8,6)])
    keys = [(x['case'],x['hypothesis'],tuple(x['grid'])) for x in checks['rows']]
    require(len(keys)==len(set(keys)) and set(keys)==expected, 'Recourse independent replay coverage differs')
    for row in checks['rows']:
        actual = row['actual']
        require(row['passed'] is True and actual['sampled_passed'] is True and actual['min_temp']>=39 and
                actual['max_temp']<=41 and actual['max_span']<=1.5 and
                actual['instantaneous_balance_residual_w']<1e-6 and actual['integrated_balance_residual_j']<.1,
                'Recourse independent trajectory failed')
        chosen = next(x['selected'] for x in run['rows'] if x['case']==row['case'])
        require(math.isclose(row['command_l'],chosen['total_command_l'],abs_tol=1e-9),
                'Independent replay command does not match selected continuation')
        spec = catalog[row['hypothesis']]
        require(math.isclose(actual['water_l'],row['command_l']*spec['parameters']['flow_multiplier'],abs_tol=1e-8),
                'Recourse actual water differs')
    negative = screening['synthetic_impossible_initial_readings']
    require(len(negative['records'])==54 and not negative['retained'], 'Empty-model negative control differs')
    return dict(run=run,checks=checks,screen=screen,rows=run['rows'],files=files,
                deadline_revision=read('deadline-revision.json'))
