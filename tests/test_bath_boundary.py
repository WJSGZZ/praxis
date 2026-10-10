from pathlib import Path
import sys,importlib.util,json,hashlib,shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
sys.path.insert(0,str(ROOT));spec=importlib.util.spec_from_file_location('bath_boundary',ROOT/'boundary_values.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_continuous_exclusion_keeps_strict_certificates_and_scope():
    from fractions import Fraction as F
    v=m.boundary_values(ROOT)
    assert v['gap'](F(1),F(1),F(3,2))>0
    assert v['gap'](F(10,3),F(1),F(3,2))<0
    assert F(9789,10000)<v['roots']['loss_root'][0]<F(9790,10000)
    assert F(15324,10000)<v['roots']['span_root_c'][0]<F(15325,10000)

@pytest.mark.parametrize('defect',['root','refit'])
def test_rehashed_boundary_cannot_promote_changed_claim(tmp_path,defect):
    folder=tmp_path/'reference/spatial-functional';shutil.copytree(ROOT/'reference/spatial-functional',folder)
    for n in ['whole-horizon-exclusion.npz','fixed-region-exclusion.npz']:shutil.copyfile(ROOT/'reference'/n,folder.parent/n)
    p=folder/('boundary-thresholds.json' if defect=='root' else 'boundary.json');v=json.loads(p.read_text())
    if defect=='root':v['loss_root']['lower']='1/2';v['loss_root']['upper']='5000000000001/10000000000000'
    else:v['weights'][0]=['0','1']
    p.write_text(json.dumps(v))
    if defect=='refit':
        for n in ['boundary-checks.json','boundary-thresholds.json']:
            p2=folder/n;c=json.loads(p2.read_text());c['source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();p2.write_text(json.dumps(c))
    p2=folder/'manifest.json';v=json.loads(p2.read_text());v['members']={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in v['members']};p2.write_text(json.dumps(v))
    with pytest.raises(ValueError):m.boundary_values(tmp_path)
