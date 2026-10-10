from pathlib import Path
import sys,json,hashlib,shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce';sys.path.insert(0,str(ROOT))
from delay_path_values import delay_path_values

def test_terminal_pass_does_not_qualify_interior_failure():
 v=delay_path_values(ROOT)
 assert v['qualified_delay_s']==700 and v['failed_delay_s']==720 and v['failed_min_c']<39

@pytest.mark.parametrize('defect',['false_pass','missing_violation','terminal','prefix'])
def test_rehashed_delay_path_cannot_change_claim(tmp_path,defect):
 shutil.copytree(ROOT/'reference/spatial-functional',tmp_path/'reference/spatial-functional');shutil.copytree(ROOT/'code',tmp_path/'code',ignore=shutil.ignore_patterns('__pycache__'))
 for name in ['whole-horizon-exclusion.npz','fixed-region-exclusion.npz']:shutil.copyfile(ROOT/'reference'/name,tmp_path/'reference'/name)
 folder=tmp_path/'reference/spatial-functional';p=folder/'delay-path-checks.json';v=json.loads(p.read_text())
 if defect=='false_pass':v['rows'][1]['qualified']=True
 elif defect=='missing_violation':v['rows'][1]['sample_min_c']=39.001
 elif defect=='terminal':v['rows'][0]['terminal_min_c']=38.9
 else:v['rows'][1]['envelopes'][0]['floor']=38.9
 p.write_text(json.dumps(v));p=folder/'manifest.json';v=json.loads(p.read_text());v['members']={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in v['members']};p.write_text(json.dumps(v))
 with pytest.raises(ValueError):delay_path_values(tmp_path)
