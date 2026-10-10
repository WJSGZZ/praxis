"""Consume a fixed-network exclusion; never infer feasibility below its cutoff."""
from pathlib import Path
from fractions import Fraction
import hashlib,json,math

CONTRACT={'grid':[8,4,3],'D':.003,'initial_c':40,'contact_c':34,'ambient_c':22,'inlet_c':50,'q_max_l_min':3,'prefix_s':790,'relative_s':86.5,'horizon_s':1800,'floor_c':39,'cell':89,'passive_steps':15800,'active_steps':1000000}
def delay_upper_values(root):
    root=Path(root);folder=root/'reference/delayed-upper'
    manifest=json.loads((folder/'manifest.json').read_text())
    expected={'README.md','check.py','checked-enclosure.json','enclosure.json','enclosure-states.npz','inputs.json','primitives.npz','rounding-proof.md','check_pulse.py','pulse-policies.json','pulse-checks.json'}
    if set(manifest['members'])!=expected:raise ValueError('Delayed upper capsule incomplete')
    for name,digest in manifest['members'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:raise ValueError('Delayed upper evidence stale')
    r=json.loads((folder/'checked-enclosure.json').read_text());p=json.loads((folder/'inputs.json').read_text())
    sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
    if r['status']!='passed' or r['contract']!=CONTRACT or r['model_sha256']!=sha(root/'code/model.py') or p['model_sha256']!=r['model_sha256'] or r['checker_sha256']!=sha(folder/'check.py') or r['inputs_sha256']!=sha(folder/'inputs.json'):raise ValueError('Delayed upper contract changed')
    if p['grid']!=[8,4,3] or p['flow_max_l_min']!=3 or p['prefix_s']!=790 or p['witness_relative_s']!=86.5 or p['parameters']['D']!=.003:raise ValueError('Delayed upper inputs changed')
    for name,key in [('primitives.npz','primitives_sha256'),('enclosure-states.npz','states_sha256'),('enclosure.json','enclosure_sha256')]:
        if p[key]!=sha(folder/name):raise ValueError('Delayed upper primitive identity differs')
    def f(value):
        exact=Fraction(int(value['numerator']),int(value['denominator']))
        if not math.isfinite(value['display']) or float(exact)!=value['display']:raise ValueError('Delayed upper rational display differs')
        return exact
    radius=f(r['error_radius']);upper=f(r['strict_upper_c']);terms=r['error_terms'];R=f(terms['round_step'])
    if not math.isfinite(r['witness_c']) or R!=Fraction(1,10**9) or not radius>0 or upper!=Fraction(r['witness_c'])+radius or upper>=39:raise ValueError('Delayed upper endpoint not excluded')
    if f(terms['passive790'])<=0 or f(terms['M2'])<=0 or radius!=f(terms['passive790'])+Fraction(173,2)**2*f(terms['M2'])/2000000+1000000*R or f(r['passive900_strict_upper_c'])>=39:raise ValueError('Delayed upper error propagation differs')
    if not 0<f(r['rounding_passive'])<R or not 0<f(r['rounding_active'])<R or f(r['state_domain_cumulative_radius'])!=1018001*R or max(r['producer_replay_max_difference_c'].values())>=1e-7:raise ValueError('Delayed upper arithmetic qualification differs')
    pulse=json.loads((folder/'pulse-checks.json').read_text());policies=json.loads((folder/'pulse-policies.json').read_text())
    if pulse['model_sha256']!=r['model_sha256'] or policies['model_sha256']!=r['model_sha256'] or pulse['checker_sha256']!=sha(folder/'check_pulse.py') or pulse['policies_sha256']!=sha(folder/'pulse-policies.json') or pulse['primitive_sha256']!=sha(folder/'primitives.npz') or policies['primitive_sha256']!=pulse['primitive_sha256']:raise ValueError('Waiting witness identity differs')
    rows=pulse['rows']
    if len(rows)!=3 or [x['policy']['delay'] for x in rows]!=[720.,750.,780.] or [x['policy'] for x in rows]!=policies['selected']:raise ValueError('Waiting witnesses changed')
    for row in rows:
        policy=row['policy'];envelopes=row['envelopes'];d=policy['delay'];tail=policy['tail']
        if policy['lead']!=3 or policy['pulse']!=90 or len(envelopes)!=3 or not 0<=tail<=3:raise ValueError('Waiting policy class differs')
        for i,(e,q,dt) in enumerate(zip(envelopes,[0.,3.,tail],[d,90.,1800-d-90])):
            if not all(math.isfinite(x) for x in e.values()) or e['flow_l_min']!=q or e['duration_s']!=dt or e['allowance_c']<(i+1)*2e-6 or abs(e['sample_min_c']-e['allowance_c']-e['floor_c'])>1e-9:raise ValueError('Waiting phase arithmetic differs')
            if e['floor_c']<39 or e['ceiling_c']>41 or e['spread_c']>1.5:raise ValueError('Waiting physical qualification failed')
        water=(3*90+tail*(1800-d-90))/60
        if row['qualified'] is not True or not math.isfinite(row['water_l']) or abs(water-row['water_l'])>1e-9 or abs(water-policy['water_l'])>1e-9:raise ValueError('Waiting water qualification differs')
    return {'delay_s':790,'upper_display_c':math.ceil(float(upper)*10000)/10000,'witness_s':876.5,'qualified_delay_s':780,'pulse_rate':3,'pulse_s':90,'tail_rate':rows[-1]['policy']['tail'],'water_l':rows[-1]['water_l'],'qualified_floor_c':min(e['floor_c'] for e in rows[-1]['envelopes']),'floor_print':math.floor(min(e['floor_c'] for e in rows[-1]['envelopes'])*10000)/10000,'ceiling_print':math.ceil(max(e['ceiling_c'] for e in rows[-1]['envelopes'])*1000000)/1000000,'spread_print':math.ceil(max(e['spread_c'] for e in rows[-1]['envelopes'])*1000000)/1000000,'scope':'Fixed archived original96 at D=.003 and q in[0,3]; floating-qualified780s example, sufficient790s exclusion under IEEE64 assumptions, not a sharp threshold or PDE result'}
