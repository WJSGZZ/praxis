"""Conditional candidates for predeclared alternative observations; preserve failures."""
import argparse,hashlib,itertools,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'code'))
import model
from policy_validation import replay_schedule
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,default=HERE/'reference/observation-screening.json');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seconds',type=float,default=180.);args=parser.parse_args()
INPUT=args.input;OUT=args.output
if OUT.exists():parser.error('Output exists; preserve earlier evidence')
if not np.isfinite(args.seconds) or args.seconds<=0:parser.error('Finite positive budget required')
OUT.parent.mkdir(parents=True,exist_ok=True)
original=json.loads(INPUT.read_text());assert original['status']=='completed'
cal=json.loads((HERE/'reference/calibration-study.json').read_text());keys=list(cal['parameter_grid']);parameters=[dict(zip(keys,t)) for t in itertools.product(*cal['parameter_grid'].values())]
start=time.monotonic();limit=args.seconds;results=[];current=None
sources=['code/model.py','code/policy_validation.py','reference/calibration-study.json','reference/information-value.json']
assert all(hashlib.sha256((HERE/s).read_bytes()).hexdigest()==original['input_sha256'][s] for s in original['input_sha256'])
def budget():
 if time.monotonic()-start>limit:raise TimeoutError('cooperative study boundary')
def simulate(p,n,q,dt):
 budget();y=np.r_[np.full(len(n['cap']),40.),1.];values=[y[:-1].copy()]
 for flow in q:
  A=expm(model.system(p,n,float(flow*p['flow_multiplier'])/60000.).toarray()*dt)
  for _ in range(round(300/dt)):y=A@y;values.append(y[:-1].copy())
 return np.array(values)
def slack(plant,q,dt):
 p,n=plant;y=simulate(p,n,q,dt);v=y[:,n['region']];return np.r_[y.min(1)-39.,41.-v.max(1),1.5-np.ptp(v,axis=1)]
def save(status):
 OUT.write_text(json.dumps(dict(status=status,elapsed_s=time.monotonic()-start,time_budget_s=limit,base_commit='9ca3f21',workspace_state='Base plus hash-bound new observation study, not clean HEAD-only identity',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),input_sha256=hashlib.sha256(INPUT.read_bytes()).hexdigest(),physical_source_sha256={s:hashlib.sha256((HERE/s).read_bytes()).hexdigest() for s in sources},completed=results,current=current,scope='Four nominal alternative observation banks, common six stages/2Lmin/.1C design plus .03C floor reserve; two starting candidates, constraint generation, local search. Selected-target margin not all-model .1C guarantee. Three-grid independent floating-point envelope only for sample-accepted candidates; no full parameter-domain or real-bath certification.'),indent=2)+'\n')
try:
 for group in original['results']:
  plants=[({**model.BASE,**parameters[i]},model.network({**model.BASE,**parameters[i]})) for i in group['indices']]
  current={'truth':group['truth'],'design':group['design'],'models':len(plants),'attempts':[],'accepted':False,'independent':[]}
  best=None
  for initial_name,initial in original['policies'].items():
   selected=set()
   for key in keys:
    selected.add(min(range(len(plants)),key=lambda i:plants[i][0][key]));selected.add(max(range(len(plants)),key=lambda i:plants[i][0][key]))
   q=np.array(initial)
   for round_no in range(3):
    def constraints(q):
     parts=[]
     for i in sorted(selected):
      s=slack(plants[i],q,30.)-.1;s[:len(s)//3]-=.03;parts.append(s)
     return np.concatenate(parts)
    ans=minimize(lambda q:5*sum(q),q,method='SLSQP',bounds=[(0.,2.)]*6,constraints=[dict(type='ineq',fun=constraints)],callback=lambda _:budget(),options=dict(maxiter=60,ftol=1e-8))
    q=ans.x;slacks=[float(slack(plant,q,5.).min()) for plant in plants];failed=[i for i,s in enumerate(slacks) if s<0]
    attempt=dict(initial=initial_name,round=round_no,optimizer_success=bool(ans.success),message=str(ans.message),flow_lpm=q.tolist(),command_l=float(5*sum(q)),sampled_failures=failed,min_slack_c=min(slacks));current['attempts'].append(attempt);save('optimization checkpoint')
    if not failed:
     if best is None or attempt['command_l']<best['command_l']:best=attempt
     break
    selected.update(sorted(failed,key=lambda i:slacks[i])[:6])
  if best is not None:
   current['selected']=best;q=np.array(best['flow_lpm'])
   for i,(p,n) in enumerate(plants):
    for grid in [(8,4,3),(12,6,4),(16,8,6)]:
     budget();r=replay_schedule(p,model.network(p,grid),q*p['flow_multiplier'],grid,sample_s=1.,tolerance_c=0.)
     current['independent'].append(dict(model_index=i,prior_index=group['indices'][i],grid=list(grid),water_l=float(5*sum(q)*p['flow_multiplier']),**{k:r[k] for k in ['continuous_passed','sampled_passed','lower_temperature_bound_c','upper_temperature_bound_c','span_upper_bound_c']}))
     if len(current['independent'])%40==0:save('validation checkpoint')
   current['accepted']=len(current['independent'])==len(plants)*3 and all(r['continuous_passed'] for r in current['independent'])
  results.append(current);current=None;save('group completed')
 save('completed')
except TimeoutError:save('budget exhausted')
print(json.dumps(dict(elapsed_s=time.monotonic()-start,completed=[{k:r.get(k) for k in ['truth','design','models','accepted','selected']} for r in results],current=None if current is None else {k:current.get(k) for k in ['truth','design','models','accepted']}),indent=2))
