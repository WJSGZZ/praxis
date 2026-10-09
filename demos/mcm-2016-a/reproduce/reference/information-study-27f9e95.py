"""Compare information from passive cooling with the archived paid pulse, same prior and errors."""
import argparse,hashlib,itertools,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parent;H=ROOT;sys.path.insert(0,str(H/'code'));sys.path.insert(0,str(H));import model
from study_calibration import compatible_offset
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seconds',type=float,default=360.);args=parser.parse_args()
if args.output.exists():parser.error('Output exists; preserve earlier evidence')
if not np.isfinite(args.seconds) or args.seconds<=0:parser.error('Finite positive budget required')
OUT=args.output.parent;OUT.mkdir(parents=True,exist_ok=True);target=args.output;start=time.monotonic();limit=args.seconds;rows=[];rounds=[];screen=[];complete=False;independent=[]
from policy_validation import replay_schedule
cal=json.loads((H/'reference/calibration-study.json').read_text());keys=list(cal['parameter_grid']);tuples=list(itertools.product(*cal['parameter_grid'].values()));probes=cal['probes'];plants=[]
def budget():
 if time.monotonic()-start>limit:raise TimeoutError('Cooperative study budget exhausted')
def simulate(p,q,dt,net=None):
 budget();n=model.network(p) if net is None else net;y=np.r_[np.full(len(n['cap']),p['initial']),1.];values=[y[:-1].copy()]
 for flow in q:
  A=expm(model.system(p,n,float(flow*p.get('flow_multiplier',1.))/60000.).toarray()*dt)
  for _ in range(round(300/dt)):y=A@y;values.append(y[:-1].copy())
 return np.array(values),n
def slack(i,q,dt):
 p,n=plants[i];y,_=simulate(p,q,dt,n);v=y[:,n['region']];return np.r_[y.min(1)-39.,41-v.max(1),1.5-np.ptp(v,axis=1)]
def save(status):
 r=dict(schema_version=1,status=status,accepted_sampled=complete,accepted=complete and len(independent)==3*len(rows) and all(x['continuous_passed'] for x in independent),independent=independent,elapsed_s=time.monotonic()-start,time_budget_s=limit,parameter_grid=cal['parameter_grid'],candidate_models=len(tuples),compatible_models=len(rows),rows=rows,rounds=rounds,screened_slacks_c=screen,observation_flow_lpm=[0.]*6,observation_sample_s=30.,probes=probes,reading_bound_c=.02,constant_offset_bound_c=.02,observation_command_l=0.,reset_cost_l='unknown',control_command_l=None if not rounds else rounds[-1]['command_l'],pulse_control_command_l=cal['commanded_water_l'],pulse_observation_command_l=6.,scope='Synthetic nominal passive 30-minute cooling, same finite prior, geometry, initial state, fixed probes and error bounds as pulse. Flow multiplier remains unidentifiable. Same six stages / 2 L/min / selected .1 C and extra .03 C floor design targets. Five-second candidate screening and independent three-grid conditional floating-point envelopes; reset not free, no real physical or global-optimal claim.',source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),H/'reference/calibration-study.json',H/'code/model.py',H/'study_calibration.py',H/'code/policy_validation.py']},research_base_commit='27f9e95',workspace_state='Research base plus this hash-bound new study; not a clean HEAD-only snapshot')
 target.write_text(json.dumps(r,indent=2)+'\n')
try:
 nominal,_=simulate({**model.BASE,'flow_multiplier':1.},[0.]*6,30.)
 # Passive response is exactly independent of the unknown multiplier: cache
 # only identical thermal-parameter combinations, not approximate neighbors.
 cached={}
 for t in tuples:
  budget();p={**model.BASE,**dict(zip(keys,t))};thermal=tuple(t[j] for j,k in enumerate(keys) if k!='flow_multiplier')
  if thermal not in cached:
   values,n=simulate(p,[0.]*6,30.);correction,residual,compatible=compatible_offset(values[:,probes]-nominal[:,probes]);cached[thermal]=(n,correction,residual,compatible)
  n,correction,residual,compatible=cached[thermal]
  if compatible:
   rows.append(dict(parameters=dict(zip(keys,t)),model_correction_c=correction.tolist(),physical_sensor_bias_c=(-correction).tolist(),measurement_max_residual_c=float(residual)))
   plants.append((p,n))
 save('screened observations')
 selected=set()
 for key in keys:
  selected.add(min(range(len(rows)),key=lambda i:rows[i]['parameters'][key]));selected.add(max(range(len(rows)),key=lambda i:rows[i]['parameters'][key]))
 q=np.array(cal['rounds'][-1]['flow_lpm'])
 for round_no in range(3):
  ids=[int(i) for i in sorted(selected)]
  def constraints(q):
   parts=[]
   for i in ids:
    v=slack(i,q,30.)-.1;v[:len(v)//3]-=.03;parts.append(v)
   return np.concatenate(parts)
  ans=minimize(lambda q:5*sum(q),q,method='SLSQP',bounds=[(0.,2.)]*6,constraints=[dict(type='ineq',fun=constraints)],callback=lambda _:budget(),options=dict(maxiter=60,ftol=1e-8))
  q=ans.x;screen=[float(slack(i,q,5.).min()) for i in range(len(rows))];fail=[i for i,s in enumerate(screen) if s<0]
  rounds.append(dict(selected_indices=ids,optimizer_success=bool(ans.success),message=str(ans.message),flow_lpm=q.tolist(),command_l=float(5*sum(q)),sampled_failed_indices=fail,min_sampled_slack_c=float(min(screen))))
  complete=not fail;save('candidate checkpoint')
  if complete:break
  selected.update(sorted(fail,key=lambda i:screen[i])[:6])
 if complete:
  for i,row in enumerate(rows):
   p={**model.BASE,**row['parameters']}
   for grid in [(8,4,3),(12,6,4),(16,8,6)]:
    budget();result=replay_schedule(p,model.network(p,grid),q*p['flow_multiplier'],grid,sample_s=1.,tolerance_c=0.)
    independent.append(dict(model_index=i,grid=list(grid),water_l=float(5*sum(q)*p['flow_multiplier']),**{key:result[key] for key in ['continuous_passed','sampled_passed','lower_temperature_bound_c','upper_temperature_bound_c','span_upper_bound_c']}))
    if len(independent)%40==0:save('validation checkpoint')
 save('completed')
except TimeoutError:
 save('budget exhausted')
print(json.dumps(dict(compatible_models=len(rows),accepted_sampled=complete,continuous_checks=len(independent),continuous_failures=sum(not x['continuous_passed'] for x in independent),rounds=rounds,elapsed_s=time.monotonic()-start),indent=2))
