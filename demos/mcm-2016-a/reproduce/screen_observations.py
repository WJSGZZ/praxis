"""Frozen-policy sampled transfer to two predeclared synthetic observations.
Not new optimization, continuous certification, or empirical prediction.
"""
import argparse,hashlib,itertools,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import expm
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'code'))
import model
from study_calibration import compatible_offset
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seconds',type=float,default=120.);args=parser.parse_args()
OUT=args.output
if OUT.exists():parser.error('Output exists; preserve earlier evidence')
if not np.isfinite(args.seconds) or args.seconds<=0:parser.error('Finite positive budget required')
OUT.parent.mkdir(parents=True,exist_ok=True)
start=time.monotonic();budget_s=args.seconds
cal=json.loads((HERE/'reference/calibration-study.json').read_text())
iv=json.loads((HERE/'reference/information-value.json').read_text())
keys=list(cal['parameter_grid']);parameters=[dict(zip(keys,t)) for t in itertools.product(*cal['parameter_grid'].values())]
policies={'passive_candidate':iv['rounds'][-1]['flow_lpm'],'pulse_candidate':cal['rounds'][-1]['flow_lpm']}
truths={'strong_mixing_low_loss':dict(D=.00115,h_surface=20.,h_body=15.,flow_multiplier=1.),'weak_mixing_high_loss':dict(D=.00085,h_surface=30.,h_body=35.,flow_multiplier=1.)}
designs={'passive':[0.]*6,'pulse':[0.,0.,1.2,0.,0.,0.]};results=[]
def check_time():
 if time.monotonic()-start>budget_s:raise TimeoutError('cooperative study boundary')
def simulate(p,q,dt,net=None):
 check_time();n=model.network(p) if net is None else net;y=np.r_[np.full(len(n['cap']),40.),1.];values=[y[:-1].copy()]
 for flow in q:
  A=expm(model.system(p,n,float(flow*p.get('flow_multiplier',1.))/60000.).toarray()*dt)
  for _ in range(round(300/dt)):y=A@y;values.append(y[:-1].copy())
 return np.array(values),n
nominals={(truth,design):simulate({**model.BASE,**p},q,30.)[0][:,cal['probes']] for truth,p in truths.items() for design,q in designs.items()}
compatible={k:[] for k in nominals};cache={}
def save(status):
 sources=['code/model.py','study_calibration.py','reference/calibration-study.json','reference/information-value.json']
 record=dict(status=status,elapsed_s=time.monotonic()-start,time_budget_s=budget_s,base_commit='9ca3f21',workspace_state='Base plus hash-bound new observation study, not clean HEAD-only identity',research_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),input_sha256={s:hashlib.sha256((HERE/s).read_bytes()).hexdigest() for s in sources},truths=truths,designs=designs,probes=cal['probes'],reading_bound_c=.02,constant_bias_bound_c=.02,policies=policies,results=results,scope='Two predeclared endpoint nominal synthetic observations, same 2835-point finite prior. Frozen policies, 5-second base-grid screening only; no reoptimized cost comparison, empirical calibration, interval certificate or award test.')
 OUT.write_text(json.dumps(record,indent=2)+'\n')
try:
 for i,parameters_i in enumerate(parameters):
  p={**model.BASE,**parameters_i};thermal=tuple(parameters_i[k] for k in keys if k!='flow_multiplier');n=model.network(p)
  if thermal not in cache:cache[thermal]=simulate(p,designs['passive'],30.,n)[0][:,cal['probes']]
  values={'passive':cache[thermal],'pulse':simulate(p,designs['pulse'],30.,n)[0][:,cal['probes']]}
  for key,observed in nominals.items():
   correction,residual,accepted=compatible_offset(values[key[1]]-observed)
   if accepted:compatible[key].append(i)
 for (truth,design),indices in compatible.items():
  record=dict(truth=truth,design=design,compatible_models=len(indices),indices=indices,policies={})
  for policy,q in policies.items():
   slacks=[]
   for i in indices:
    y,n=simulate({**model.BASE,**parameters[i]},q,5.);v=y[:,n['region']];slacks.append(float(min((y.min(1)-39.).min(),(41.-v.max(1)).min(),(1.5-np.ptp(v,axis=1)).min())))
   record['policies'][policy]=dict(command_l=float(5*sum(q)),sampled_passed=sum(s>=0 for s in slacks),sampled_failed=sum(s<0 for s in slacks),min_slack_c=min(slacks),failed_parameters=[parameters[i] for i,s in zip(indices,slacks) if s<0])
  results.append(record);save('checkpoint')
 save('completed')
except TimeoutError:save('budget exhausted')
print(json.dumps(dict(elapsed_s=time.monotonic()-start,results=[{**r,'policies':{k:{kk:vv for kk,vv in v.items() if kk!='failed_parameters'} for k,v in r['policies'].items()},'indices':None} for r in results]),indent=2))
