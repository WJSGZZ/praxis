"""Real archived answers and rejection of rebound but invalid scientific claims."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
spec=importlib.util.spec_from_file_location('bath_research',ROOT/'research_values.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def test_real_conditional_cover_and_excluded_truth():
    result=mod.constant_exclusion(ROOT)
    assert [len(x['excluded_intervals']) for x in result['runs'][:3]] == [9,18,30]
    assert result['runs'][-1]['status'] == 'incomplete_unresolved'
    assert result['runs'][-1]['records'][-1]['center_lpm'] == 1.125
    transfer=mod.recourse_transfer(ROOT)
    assert len(transfer['checks']['rows']) == 18
    assert len(transfer['row']['survivors']) == 5
    assert transfer['row']['selected']['total_command_l'] == pytest.approx(30.759960914868827)

@pytest.mark.parametrize('defect',['cover','margin','scope','control','centers','timeout','truth','water','history'])
def test_rehashing_cannot_promote_bad_research(tmp_path,defect):
    name='constant-exclusion' if defect in ['cover','margin','scope','control','centers'] else 'recourse-transfer'
    with np.load(ROOT/'reference'/f'{name}.npz',allow_pickle=False) as a:data={n:a[n].tobytes() for n in a.files}
    read=lambda n:json.loads(data[n])
    if name=='constant-exclusion':
        run=read('results.json');checks=read('checks.json')
        if defect=='cover':run['excluded_intervals'].pop()
        elif defect=='margin':run['records'][0]['witness']['margin_c']+=1
        elif defect=='scope':run['design']['rate_interval_lpm']=[0,4];data['design.json']=json.dumps(run['design']).encode();run['source_sha256']['design.json']=hashlib.sha256(data['design.json']).hexdigest()
        elif defect=='centers':checks['rows'].pop()
        else:
            control=read('feasible-control/results.json');control['status']='conditional_interval_exclusion_complete';data['feasible-control/results.json']=json.dumps(control).encode()
        data['results.json']=json.dumps(run).encode()
        for key in checks['source_sha256']:
            if key in data:checks['source_sha256'][key]=hashlib.sha256(data[key]).hexdigest()
        data['checks.json']=json.dumps(checks).encode()
    else:
        run=read('results.json');checks=read('checks.json');screen=read('screen-checks.json')
        if defect=='timeout':run['rows'][0]['decision_elapsed_s']=60
        elif defect=='truth':checks['rows']=[x for x in checks['rows'] if x['hypothesis']!='excluded_actual_truth']
        elif defect=='water':checks['rows'][-1]['actual']['water_l']+=1
        else:screen['rows'][0]['retained']=[]
        data['results.json']=json.dumps(run).encode()
        for record,key in [(checks,'checks.json'),(screen,'screen-checks.json')]:
            record['source_sha256']['results.json']=hashlib.sha256(data['results.json']).hexdigest();data[key]=json.dumps(record).encode()
    manifest=read('manifest.json');manifest['members']={n:hashlib.sha256(data[n]).hexdigest() for n in manifest['members']};data['manifest.json']=json.dumps(manifest).encode()
    (tmp_path/'reference').mkdir();np.savez_compressed(tmp_path/'reference'/f'{name}.npz',**{n:np.frombuffer(b,dtype=np.uint8) for n,b in data.items()})
    with pytest.raises(ValueError):
        (mod.constant_exclusion if name=='constant-exclusion' else mod.recourse_transfer)(tmp_path)


def test_manuscript_retains_the_actual_sampling_scope_and_strategy_quantifiers():
    from pypdf import PdfReader
    pdf=ROOT.parent/'deliverables/7391856.pdf'
    import unicodedata
    text=unicodedata.normalize('NFKC', ' '.join(p.extract_text() for p in PdfReader(pdf).pages))
    compact=''.join(text.replace('- ', '').split())
    assert 'Dislog-uniform' in compact
    assert 'scrambledseed7' in compact and '17–37/4.5–8.5/12–40' in compact
    assert 'defines their ranges' not in text
    assert 'min/max/spread/final-body' in text
    assert 'remainingbath,foreverycompatiblemodel' in compact
    assert 'zeroflowfollowedbyaqualifiedbackup' in compact
    assert 'Nomeasurable' in compact and 'fixed-networkimpossibility' in compact


def test_rational_all_control_certificate_and_feasible_control():
    cert=mod.all_control_exclusion(ROOT)
    assert cert['exact']['rational_rows']==61869
    assert cert['exact']['corrected_bound_float_display']>1/5000
    assert cert['run']['rows'][1]['success'] is False  # Timeout is not solved.
    assert cert['checks']['known_feasible_flux_integral_matrix_residual']<1e-7


def test_whole_horizon_certificate_same_model_distinct_residual():
    result=mod.whole_horizon_exclusion(ROOT)
    assert result['exact']['rows']==1332 and result['exact']['variables']==298
    assert result['exact']['exact_bound_display']>1/25
    assert result['scope']['conditions']['horizon_s']==1800
    assert result['files']['network96/primitives.npz']==mod.all_control_exclusion(ROOT)['files']['primitives.npz']


@pytest.mark.parametrize('defect',['none','zero_dual','wrong_initial','wrong_units','wrong_primitive'])
def test_integral_certificate_replay_rejects_corruptions(tmp_path,defect):
    import subprocess,sys
    from scipy.sparse import load_npz,save_npz
    for name,raw in mod.whole_horizon_exclusion(ROOT)['files'].items():
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    if defect=='wrong_units':
        p=tmp_path/'network96/A.npz';a=load_npz(p);a.data[0]*=1000;save_npz(p,a)
    elif defect!='none':
        p=tmp_path/'network96'/('solution.npz' if defect=='zero_dual' else 'problem.npz' if defect=='wrong_initial' else 'primitives.npz')
        with np.load(p,allow_pickle=False) as z:data={k:z[k] for k in z.files}
        if defect=='zero_dual':
            for key in ('inequality_dual','lower_dual','upper_dual'):data[key][:]=0
        elif defect=='wrong_initial':data['b'][0]+=1
        else:data['ha'][0]*=2
        np.savez(p,**data)
    run=subprocess.run([sys.executable,str(tmp_path/'verify_exact.py')],capture_output=True,text=True,timeout=65)
    if defect=='none':
        assert run.returncode==0,run.stderr
        result=json.loads(run.stdout)
        assert result['network96']['exact_bound_display']>1/25 and 'network288' not in result
    else:assert run.returncode!=0 and 'AssertionError' in run.stderr


@pytest.mark.parametrize('defect',['scope','bound','display','negative','primitive'])
def test_rebound_integral_receipt_cannot_change_claim(tmp_path,defect):
    data=mod.whole_horizon_exclusion(ROOT)['files'].copy()
    name='archive-scope.json' if defect=='scope' else 'portable-exact-checks.json'
    row=json.loads(data[name])
    if defect=='scope':row['conditions']['rate_lpm']=[0,4]
    elif defect=='bound':row['network96']['exact_bound_numerator']='0'
    elif defect=='display':row['network96']['exact_bound_display']=100
    elif defect=='negative':row['negative_checks']['wrong_units']['rejected']=False
    else:
        import io
        key='network96/primitives.npz'
        with np.load(io.BytesIO(data[key]),allow_pickle=False) as z:primitive={k:z[k] for k in z.files}
        primitive['cap'][0]*=2;stream=io.BytesIO();np.savez(stream,**primitive);data[key]=stream.getvalue()
        row['network96']['sha256']['primitives.npz']=hashlib.sha256(data[key]).hexdigest()
    data[name]=json.dumps(row).encode();manifest=json.loads(data['manifest.json']);manifest['members']={n:hashlib.sha256(data[n]).hexdigest() for n in manifest['members']};data['manifest.json']=json.dumps(manifest).encode()
    (tmp_path/'reference').mkdir();np.savez_compressed(tmp_path/'reference/whole-horizon-exclusion.npz',**{n:np.frombuffer(b,dtype=np.uint8) for n,b in data.items()})
    (tmp_path/'reference/all-control-exclusion.npz').write_bytes((ROOT/'reference/all-control-exclusion.npz').read_bytes())
    with pytest.raises(ValueError):mod.whole_horizon_exclusion(tmp_path)


@pytest.mark.parametrize('defect',['none','zero_dual','wrong_balance','wrong_initial','wrong_primitive'])
def test_exact_certificate_replay_rejects_independent_corruptions(tmp_path,defect):
    import subprocess,sys
    from scipy.sparse import load_npz,save_npz
    files=mod.all_control_exclusion(ROOT)['files']
    for name,raw in files.items():
        dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    if defect=='zero_dual':
        path=tmp_path/'weak96/solution.npz'
        with np.load(path,allow_pickle=False) as z:data={k:z[k] for k in z.files}
        for k in ('inequality_dual','lower_dual','upper_dual'):data[k]=np.zeros_like(data[k])
        np.savez(path,**data)
    elif defect=='wrong_balance':
        path=tmp_path/'weak96/A.npz';a=load_npz(path);a.data[0]+=.01;save_npz(path,a)
    elif defect=='wrong_initial':
        path=tmp_path/'weak96/problem.npz'
        with np.load(path,allow_pickle=False) as z:data={k:z[k] for k in z.files}
        data['bounds'][0,0]=39;np.savez(path,**data)
    elif defect=='wrong_primitive':
        path=tmp_path/'primitives.npz'
        with np.load(path,allow_pickle=False) as z:data={k:z[k] for k in z.files}
        data['cap'][0]*=1.01;np.savez(path,**data)
    result=subprocess.run([sys.executable,str(tmp_path/'verify_exact.py')],capture_output=True,text=True,timeout=70)
    if defect=='none':
        assert result.returncode==0,result.stderr
        actual=json.loads(result.stdout)
        assert actual['status']=='completed' and actual['corrected_bound_float_display']>1/5000
    else:
        assert result.returncode!=0 and 'AssertionError' in result.stderr


def test_active_report_has_parallel_numbered_subsections_and_resolved_references():
    from pypdf import PdfReader
    import re
    pages=PdfReader(ROOT.parent/'deliverables/7391856.pdf').pages
    contents=pages[1].extract_text()
    groups={}
    for parent,child in re.findall(r'(?m)^\s*(\d+)\.(\d+)\s',contents):
        groups.setdefault(parent,[]).append(child)
    assert all(len(children)>=2 for children in groups.values()),groups
    text=' '.join(p.extract_text() for p in pages)
    assert 'Section 2.1' not in text and '??' not in text
    assert 'Problem formulation' in contents
    assert 'Optimality and energy bounds' in contents
    assert 'Delivery-error sensitivity' in contents
