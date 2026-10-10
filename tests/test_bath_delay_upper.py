from pathlib import Path
import sys,json,hashlib,shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce';sys.path.insert(0,str(ROOT))
from delay_upper_values import delay_upper_values

def test_delayed_upper_is_sufficient_fixed_network_exclusion():
    v=delay_upper_values(ROOT)
    assert v['delay_s']==790 and v['upper_display_c']==38.998 and v['qualified_delay_s']==780 and v['qualified_floor_c']>39 and 'not a sharp threshold' in v['scope']

@pytest.mark.parametrize('defect',['flow_cap','time','false_upper','radius','rounding','prefix_failure','primitive','missing','pulse_false_pass','pulse_duration','pulse_unsafe','pulse_water'])
def test_delayed_upper_rehashed_false_claim_rejected(tmp_path,defect):
    folder=tmp_path/'reference/delayed-upper';shutil.copytree(ROOT/'reference/delayed-upper',folder)
    shutil.copytree(ROOT/'code',tmp_path/'code',ignore=shutil.ignore_patterns('__pycache__'))
    p=folder/'checked-enclosure.json';r=json.loads(p.read_text())
    if defect=='flow_cap':r['contract']['q_max_l_min']=4
    elif defect=='time':r['contract']['relative_s']=1900
    elif defect=='false_upper':r['strict_upper_c']={'numerator':'40','denominator':'1','display':40.}
    elif defect=='radius':r['error_radius']={'numerator':'1','denominator':'1000000','display':.000001}
    elif defect=='rounding':r['rounding_active']={'numerator':'1','denominator':'1','display':1.}
    elif defect=='prefix_failure':r['passive900_strict_upper_c']={'numerator':'40','denominator':'1','display':40.}
    elif defect=='primitive':(folder/'primitives.npz').write_bytes(b'changed identity')
    elif defect=='missing':(folder/'rounding-proof.md').unlink()
    else:
        pp=folder/'pulse-checks.json';pulse=json.loads(pp.read_text())
        if defect=='pulse_false_pass':pulse['rows'][2]['qualified']=False
        elif defect=='pulse_duration':pulse['rows'][2]['envelopes'][1]['duration_s']=100
        elif defect=='pulse_unsafe':pulse['rows'][2]['envelopes'][1]['floor_c']=38.9
        else:pulse['rows'][2]['water_l']=1.
        pp.write_text(json.dumps(pulse))
    p.write_text(json.dumps(r));m=json.loads((folder/'manifest.json').read_text());m['members']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file() and p.name!='manifest.json'};(folder/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError):delay_upper_values(tmp_path)
