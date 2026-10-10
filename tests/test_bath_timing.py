from pathlib import Path
import sys,json,hashlib,shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce';sys.path.insert(0,str(ROOT))
from timing_values import timing_values

def test_timing_local_comparison_keeps_scope():
 v=timing_values(ROOT)
 assert v['baseline_slope']>0>v['strong_slope'] and .00137<v['local_D']<.00138

@pytest.mark.parametrize('defect',['derivative','envelope','branch'])
def test_rehashed_timing_cannot_promote_changed_claim(tmp_path,defect):
 shutil.copytree(ROOT/'reference/spatial-functional',tmp_path/'reference/spatial-functional');shutil.copytree(ROOT/'code',tmp_path/'code',ignore=shutil.ignore_patterns('__pycache__'))
 for name in ['whole-horizon-exclusion.npz','fixed-region-exclusion.npz']:shutil.copyfile(ROOT/'reference'/name,tmp_path/'reference'/name)
 folder=tmp_path/'reference/spatial-functional';p=folder/'timing-checks.json';v=json.loads(p.read_text())
 if defect=='derivative':v['independent_rows'][1]['slope']*=-1
 elif defect=='envelope':v['independent_rows'][1]['envelope']['spread']=1.6
 else:v['independent_rows'][1]['terminal_cell']=88
 p.write_text(json.dumps(v));p=folder/'manifest.json';v=json.loads(p.read_text());v['members']={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in v['members']};p.write_text(json.dumps(v))
 with pytest.raises(ValueError):timing_values(tmp_path)
