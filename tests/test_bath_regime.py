from pathlib import Path
import importlib.util,json,shutil,sys
import pytest
ROOT=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
sys.path.insert(0,str(ROOT));spec=importlib.util.spec_from_file_location('bath_regime',ROOT/'regime_values.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def test_discrete_decisions_keep_proof_sampling_and_unknown_separate():
    rows={r['scenario']:r for r in mod.regime_values(ROOT)['rows']}
    assert len(rows)==11 and rows['weak mixing']['safe_time_upper_s']==1717
    assert rows['strong mixing']['delay_min']==10 and rows['moving with added surface loss']['delay_min']==8
    assert rows['high loss']['action']=='Unresolved'
    assert all('sampled' in r['evidence'] for r in rows.values() if r['water_l'] is not None)

@pytest.mark.parametrize('defect',['loss','delay','nan','replay','coupled_policy','route'])
def test_changed_conditions_or_actions_refuse_old_evidence(tmp_path,defect):
    shutil.copytree(ROOT/'code',tmp_path/'code',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'reference/spatial-functional',tmp_path/'reference/spatial-functional')
    for name in ['results.json','checks.json','whole-horizon-exclusion.npz','fixed-region-exclusion.npz','regime-binding.json']:
        shutil.copyfile(ROOT/'reference'/name,tmp_path/'reference'/name)
    p=tmp_path/'reference/results.json';d=json.loads(p.read_text())
    if defect=='loss':d['parameters']['h_surface']=26
    elif defect=='delay':d['scenarios']['strong mixing']['policy']['delay_s']=0
    elif defect=='coupled_policy':
        d['scenarios']['strong mixing']['policy']['flow_lpm']*=1.01;d['scenarios']['strong mixing']['policy']['water_l']*=1.01
    elif defect=='route':
        q=tmp_path/'code/model.py';text=q.read_text();assert 'ny//2,nz-1' in text;q.write_text(text.replace('ny//2,nz-1','0,nz-1'))
    elif defect=='nan':d['scenarios']['strong mixing']['policy']['flow_lpm']=float('nan')
    else:
        q=tmp_path/'reference/checks.json';c=json.loads(q.read_text());next(t for t in c if t['name']=='independent_scenario_RK45_replay')['passed']=False;q.write_text(json.dumps(c))
    p.write_text(json.dumps(d))
    if defect in ['loss','delay','nan','route']:
        import hashlib
        q=tmp_path/'reference/regime-binding.json';b=json.loads(q.read_text());b['files_sha256']={name:hashlib.sha256((tmp_path/name).read_bytes()).hexdigest() for name in b['files_sha256']};q.write_text(json.dumps(b))
    with pytest.raises(ValueError):mod.regime_values(tmp_path)


def test_roundoff_bridge_uses_exact_certificate_margin():
    import numpy as np,io
    with np.load(ROOT/'reference/whole-horizon-exclusion.npz',allow_pickle=False) as z:
        with np.load(io.BytesIO(z['network96/primitives.npz'].tobytes()),allow_pickle=False) as z2:original={k:z2[k] for k in z2.files}
    changed={k:v.copy() for k,v in original.items()}
    # Simulate a platform-dependent exp/normalization last-bit difference.
    changed['cap']=np.nextafter(changed['cap'],np.inf)
    changed['hb']=np.nextafter(changed['hb'],np.inf)
    changed['ha']=np.nextafter(changed['ha'],np.inf)
    changed['G']=np.where(changed['G']!=0,np.nextafter(changed['G'],np.inf),changed['G'])
    mod.certified_primitive_match(changed,original,ROOT)


def test_large_or_nonfinite_perturbation_cannot_inherit_time_bound():
    import numpy as np,io
    with np.load(ROOT/'reference/whole-horizon-exclusion.npz',allow_pickle=False) as z:
        with np.load(io.BytesIO(z['network96/primitives.npz'].tobytes()),allow_pickle=False) as z2:original={k:z2[k] for k in z2.files}
    for defect in ['loss','nonfinite','region']:
        changed={k:v.copy() for k,v in original.items()}
        if defect=='loss':changed['ha']*=.1;changed['hb']*=.1
        elif defect=='nonfinite':changed['cap'][0]=np.nan
        else:changed['region'][0]=not changed['region'][0]
        with pytest.raises(ValueError):mod.certified_primitive_match(changed,original,ROOT)
