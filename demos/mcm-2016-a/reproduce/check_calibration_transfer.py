import hashlib, importlib.util, json, sys, time
from pathlib import Path
import numpy as np
from scipy.linalg import expm
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H/'code'));sys.path.insert(0,str(H))
import model
from check_structure import replay
import argparse
parser=argparse.ArgumentParser(description='Replay frozen policies on the same finite calibration bank and selected structural alternatives; no optimization.')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists(): parser.error('Output exists; preserve previous evidence')
start=time.monotonic(); study=json.loads((H/'reference/calibration-study.json').read_text()); base=json.loads((H/'reference/results.json').read_text())
assert study['status']=='completed' and study['accepted']
assert all(hashlib.sha256((H/name).read_bytes()).hexdigest()==digest for name,digest in study['source_sha256'].items()), 'Stale calibration study'
q=np.array(study['rounds'][-1]['flow_lpm']); indices=study['rounds'][-1]['selected_indices']; rows=[]
for i in indices:
 p={**model.BASE,**study['rows'][i]['parameters']};net=model.network(p); actual=q*p['flow_multiplier']
 for route,capacity in [('surface',None),('deep',None),('surface',73000*3.47),('deep',73000*3.47)]:
  a=replay(p,net,actual,route,capacity,sample_s=2.);b=replay(p,net,actual,route,capacity,sample_s=1.)
  delta=max(abs(a[k]-b[k]) for k in ('min_temp','max_temp','max_span','final_body_temp_c'))
  assert delta<2e-4,(i,route,delta)
  assert a['instantaneous_balance_residual_w']<1e-6 and a['integrated_balance_residual_j']<.1
  rows.append(dict(model_index=i,parameters=study['rows'][i]['parameters'],**a,step_check_delta_c=delta))
  if time.monotonic()-start>180:raise TimeoutError('Bounded replay exceeded 180s')
constant=[]
for i,row in enumerate(study['rows']):
 p={**model.BASE,**row['parameters']};net=model.network(p);flow=base['policy']['flow_lpm']*p['flow_multiplier'];y=np.r_[np.full(len(net['cap']),p['initial']),1.];A=expm(model.system(p,net,flow/60000.).toarray()*5.)
 vals=[y[:-1].copy()]
 for _ in range(360):y=A@y;vals.append(y[:-1].copy())
 v=np.array(vals);view=v[:,net['region']];s=min(v.min()-p['floor'],p['ceiling']-view.max(),p['span']-np.ptp(view,axis=1).max())
 constant.append(dict(model_index=i,sampled_slack_c=float(s),sampled_passed=bool(s>=0),water_l=float(flow*30)))
files=[H/'reference/calibration-study.json',H/'reference/results.json',H/'code/model.py',H/'check_structure.py',Path(__file__)]
out=dict(source_sha256={str(f.relative_to(H)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},elapsed_s=time.monotonic()-start,new_policy_flow_lpm=q.tolist(),selected_model_indices=indices,structure_rows=rows,constant_rows=constant,constant_command_l=float(base['policy']['flow_lpm']*30),scope='10 previously selected parameter models, 4 structure scenarios, 2/1s sampled RK45 and energy checks on one mesh. Not a continuous envelope or full 178-model structural certificate. Constant policy 178 models on original network at 5s; no optimization.')
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n')
print('elapsed',out['elapsed_s'],'constant failures',sum(not r['sampled_passed'] for r in constant))
for route,cap in [('surface',None),('deep',None),('surface',73000*3.47),('deep',73000*3.47)]:
 rs=[r for r in rows if r['route']==route and r['body_capacity_j_per_k']==cap]
 print(route,cap,'passes',sum(r['sampled_passed'] for r in rs),'/',len(rs),'min',min(r['min_temp'] for r in rs),'max',max(r['max_temp'] for r in rs),'span',max(r['max_span'] for r in rs))
