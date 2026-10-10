"""Join archived policy evidence to a discrete conditional decision map."""
from pathlib import Path
import io,json,importlib.util,math,hashlib
import numpy as np
from spatial_functional_values import spatial_functional_values

SCENARIOS=('weak mixing','strong mixing','moving with added surface loss','stratified','convective surface layer','foam','tight comfort','loose comfort','low loss','high loss','cool supply')

def regime_values(root,run=None):
    root=Path(root);run=Path(run) if run is not None else root/'reference'
    binding=json.loads((root/'reference/regime-binding.json').read_text())
    for name,digest in binding['files_sha256'].items():
        file=run/Path(name).name if name.startswith('reference/') else root/name
        if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise ValueError('Scenario evidence binding stale')
    r=json.loads((run/'results.json').read_text())
    p=r['parameters'];checks=json.loads((run/'checks.json').read_text())
    case=next(c for c in checks if c['name']=='independent_scenario_RK45_replay')
    if not case['passed']:raise ValueError('Scenario replay failed')
    sample=json.loads(case['evidence'])
    if not 0<sample['maximum_sampling_interval_s']<=5:raise ValueError('Scenario sampling scope changed')
    # Join the proof only after exact primitive identity and boundary checks.
    weak=r['scenarios']['weak mixing'];wp={**p,**weak['changes']}
    conditions={'D':.0003,'initial':40.,'body_temp':34.,'inlet_temp':50.,'air_temp':22.,'horizon':1800.,'floor':39.,'ceiling':41.,'span':1.5,'rho':1000.,'cp':4180.}
    if any(wp[k]!=v for k,v in conditions.items()) or r['grid']!=[8,4,3]:raise ValueError('Exclusion conditions changed')
    spec=importlib.util.spec_from_file_location('bath_regime_model',root/'code/model.py')
    model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
    n=model.network(wp,tuple(r['grid']))
    with np.load(root/'reference/whole-horizon-exclusion.npz',allow_pickle=False) as z:
        with np.load(io.BytesIO(z['network96/primitives.npz'].tobytes()),allow_pickle=False) as original:
            if any(not np.array_equal(n[k],original[k]) for k in original.files):raise ValueError('Exclusion physical primitives differ')
        with np.load(io.BytesIO(z['network96/problem.npz'].tobytes()),allow_pickle=False) as problem:path=list(problem['path'])
    adv=np.zeros_like(n['adv']);hot=np.zeros_like(n['hot']);rho_cp=4180000.
    for i in path:adv[i,i]=-rho_cp
    for a,b in zip(path,path[1:]):adv[b,a]=rho_cp
    hot[path[0]]=rho_cp*50
    if not np.array_equal(n['adv'],adv) or not np.array_equal(n['hot'],hot):raise ValueError('Exclusion stream route differs')
    bound=spatial_functional_values(root)['safe_time_upper_s'][('whole-horizon-exclusion','network96')]
    rows=[]
    for key in SCENARIOS:
        v=r['scenarios'][key];policy=v['policy'];pp={**p,**v['changes']}
        if key=='weak mixing':
            if policy['feasible']:raise ValueError('Policy conflicts with exclusion')
            rows.append({'scenario':key,'water_l':None,'delay_min':None,'action':'Change conditions (E96)','evidence':'exact exclusion on matched96-cell network','safe_time_upper_s':bound});continue
        if not policy['feasible']:
            rows.append({'scenario':key,'water_l':None,'delay_min':None,'action':'Unresolved','evidence':'finite search, not impossibility'});continue
        q=sample['scenarios'][key];m=q['independent_metrics']
        if not q['passed'] or not q['sampled_constraints_passed'] or m['min_temp']<pp['floor'] or m['max_temp']>pp['ceiling'] or m['max_span']>pp['span']:raise ValueError('Scenario constraints not qualified at samples')
        if not all(math.isfinite(policy[k]) for k in ['delay_s','flow_lpm','water_l']) or policy['flow_lpm']<0:raise ValueError('Nonfinite or negative scenario action')
        delay=policy['delay_s']/60
        if not 0<=delay<pp['horizon']/60 or policy['flow_lpm']>3 or abs(policy['water_l']-policy['flow_lpm']*(pp['horizon']/60-delay))>1e-8:raise ValueError('Scenario action differs from policy')
        rows.append({'scenario':key,'water_l':policy['water_l'],'delay_min':delay,'action':(f'Wait {delay:g} min; supply (S)' if delay else 'Supply now (S)'),'evidence':'independent sampled RK45; not continuous guarantee'})
    return {'rows':rows,'scope':'Discrete scenario decisions; no interpolation or continuous phase boundary; E96 exact exclusion, S sampled qualification, unresolved not infeasible'}
