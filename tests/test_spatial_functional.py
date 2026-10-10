from pathlib import Path
import importlib.util,json,hashlib,shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
spec=importlib.util.spec_from_file_location('spatial_functional',ROOT/'spatial_functional_values.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def test_current_exact_time_bounds_and_fixed_weight_transfer():
    result=module.spatial_functional_values(ROOT)
    assert result['safe_time_upper_s']=={('whole-horizon-exclusion','network96'):1717,('fixed-region-exclusion','network96'):1619,('fixed-region-exclusion','network288'):1481,('fixed-region-exclusion','network768'):1533}

@pytest.mark.parametrize('defect',['time','sign','identity','refitted_weight'])
def test_rehashed_receipt_does_not_promote_invalid_functional(tmp_path,defect):
    folder=tmp_path/'reference/spatial-functional';shutil.copytree(ROOT/'reference/spatial-functional',folder)
    for name in ['whole-horizon-exclusion.npz','fixed-region-exclusion.npz']:shutil.copyfile(ROOT/'reference'/name,folder.parent/name)
    name='transfer-results.json' if defect=='refitted_weight' else 'exact-checks.json'
    p=folder/name;data=json.loads(p.read_text())
    if defect=='time':data['checks'][1]['strict_safe_time_upper_integer_s']=1
    elif defect=='sign':data['checks'][0]['positive']=True
    elif defect=='identity':data['checks'][0]['network']='network288'
    else:data['records'][1]['weights'][0]+=1
    p.write_text(json.dumps(data))
    if defect=='refitted_weight':
        p=folder/'transfer-exact-checks.json';d=json.loads(p.read_text());d['source_sha256']=hashlib.sha256((folder/name).read_bytes()).hexdigest();p.write_text(json.dumps(d))
    p=folder/'manifest.json';d=json.loads(p.read_text());d['members']={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in d['members']};p.write_text(json.dumps(d))
    with pytest.raises(ValueError):module.spatial_functional_values(tmp_path)
