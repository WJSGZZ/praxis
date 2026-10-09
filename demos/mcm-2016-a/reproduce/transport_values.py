"""Read the frozen closure study, retaining failures and explicit evidence scope."""
import hashlib
import json
import math
from pathlib import Path


def transport_values(root):
    root = Path(root)
    folder = root/'reference/transport'
    read = lambda n: json.loads((folder/n).read_text())
    for name,digest in read('manifest.json')['members'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Transport archive changed: '+name)
    design, run, check = [read(n) for n in ['design.json','results.json','checks.json']]
    if run['status'] != 'completed' or check['status'] != 'completed':
        raise ValueError('Transport evidence incomplete')
    for record in [run,check]:
        for name,digest in record['source_sha256'].items():
            if hashlib.sha256((folder/name).read_bytes()).hexdigest() != digest:
                raise ValueError('Transport source or result is stale: '+name)
    for name,digest in design['inputs_sha256'].items():
        suffix = name.split('/reproduce/',1)[1]
        if hashlib.sha256((root/suffix).read_bytes()).hexdigest() != digest:
            raise ValueError('Transport baseline input is stale')
    expected = {(profile,D,n,policy) for profile in design['profiles']
                for D in design['diffusivities'] for n in design['cells']
                for policy in design['policies']}
    keys = [(r['profile'],r['D'],r['cells'],r['policy']) for r in run['rows']]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError('Transport replay coverage differs')
    groups = {(r['profile'],r['D']):r for r in run['search']}
    if len(groups) != len(run['search']) or set(groups) != {(a,b) for a in design['profiles'] for b in design['diffusivities']}:
        raise ValueError('Transport search coverage differs')
    for group in groups.values():
        chosen = group['selected']
        if chosen is None:
            if group['candidates'] or group['refinement']:
                raise ValueError('Failed transport search was promoted')
            continue
        if chosen not in group['candidates'] or chosen['command_l'] != min(c['command_l'] for c in group['candidates']):
            raise ValueError('Transport choice does not match finite candidates')
        if not math.isclose(chosen['command_l'],(1800-chosen['delay_s'])*chosen['rate_lpm']/60,abs_tol=1e-9):
            raise ValueError('Transport water units differ')
        if len(group['refinement']) != 6 or not all(r['sampled_physical_passed'] for r in group['refinement']):
            raise ValueError('Selected transport refinement is incomplete or failed')
    independent = [r for r in check['records'] if r['check']=='independent_flux_RK45']
    if len(independent)!=6 or len(check['records'])!=24:
        raise ValueError('Independent transport checks incomplete')
    original=read('original-overflow.json')
    for name,digest in original['source_sha256'].items():
        suffix=name.split('/reproduce/',1)[1]
        if hashlib.sha256((root/suffix).read_bytes()).hexdigest()!=digest:
            raise ValueError('Original overflow evidence stale')
    if original['outlet_index'] != 92 or original['grid'] != [8,4,3]:
        raise ValueError('Original overflow outlet identity differs')
    return dict(design=design,run=run,checks=check,groups=groups,independent=independent,
                original_overflow=original,matched_overflow=read('matched-overflow.json'))
