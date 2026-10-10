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
    assert 'delayed/time-varyingcontrols' in compact
