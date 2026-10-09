"""Bounded structural synthetic observation challenge; fixed-policy replay only.

Two declared thermal endpoints, two alternative structures and two trials.
No new policy inference or optimization; no real-bath/continuous guarantee.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,hashlib,itertools,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from scipy.integrate import solve_ivp
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'code')]
import model
from study_calibration import compatible_offset
from check_structure import replay
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--seconds',type=float,default=150.)
args=parser.parse_args()
OUT=args.output
if OUT.exists():parser.error('Preserve existing evidence')
if not np.isfinite(args.seconds) or args.seconds<=0:parser.error('Finite positive budget required')
OUT.parent.mkdir(parents=True,exist_ok=True)
start=time.monotonic();rows=[];checks=[]
def budget():
 if time.monotonic()-start>args.seconds:raise TimeoutError('cooperative time boundary')
cal=json.loads((HERE/'reference/calibration-study.json').read_text())
control=json.loads((HERE/'reference/observation-control.json').read_text())
truths={'strong_mixing_low_loss':dict(D=.00115,h_surface=20.,h_body=15.,flow_multiplier=1.),'weak_mixing_high_loss':dict(D=.00085,h_surface=30.,h_body=35.,flow_multiplier=1.)}
designs={'passive':[0.]*6,'pulse':[0.,0.,1.2,0.,0.,0.]}
structures={'deep_fixed':('deep',None),'surface_finite':('surface',253310.)}
keys=list(cal['parameter_grid']);params=[dict(zip(keys,v)) for v in itertools.product(*cal['parameter_grid'].values())]
def affine(p,route,capacity):
 n=model.network(p);N=len(n['cap']);A=np.zeros((N+2,N+2));cap=n['cap'];ha=n['ha'];hb=n['hb']
 A[:N,:N]=(n['G']-np.diag(ha+hb))/cap[:,None]
 A[:N,N]=hb/cap;A[:N,-1]=ha*p['air_temp']/cap
 if capacity is not None:A[N,:N]=hb/capacity;A[N,N]=-hb.sum()/capacity
 nx,ny,nz=n['grid'];idx=lambda i,j,k:(i*ny+j)*nz+k
 path=[idx(i,ny//2,nz-1) for i in range(nx)]
 if route=='deep':path=[idx(0,ny//2,k) for k in range(nz-1,-1,-1)]+[idx(i,ny//2,0) for i in range(1,nx)]+[idx(nx-1,ny//2,k) for k in range(1,nz)]
 Q=np.zeros_like(A)
 for j,c in enumerate(path):
  f=p['rho']*p['cp']/60000/cap[c];Q[c,c]-=f
  if j:Q[c,path[j-1]]+=f
  else:Q[c,-1]+=f*p['inlet_temp']
 return A,Q,n
def alt(p,q,route,capacity,dt):
 budget();A,Q,n=affine(p,route,capacity);y=np.r_[np.full(len(n['cap']),p['initial']),p['body_temp'],1.];ys=[y.copy()]
 for v in q:
  E=expm((A+v*p.get('flow_multiplier',1.)*Q)*dt)
  for _ in range(round(300/dt)):y=E@y;ys.append(y.copy())
 return np.array(ys),n
def original(p,q):
 budget();n=model.network(p);y=np.r_[np.full(len(n['cap']),40.),1.];ys=[y[:-1].copy()]
 for v in q:
  E=expm(model.system(p,n,v*p.get('flow_multiplier',1.)/60000).toarray()*30)
  for _ in range(10):y=E@y;ys.append(y[:-1].copy())
 return np.array(ys)[:,cal['probes']]
def save(status):
 inputs=['code/model.py','check_structure.py','study_calibration.py','reference/calibration-study.json','reference/observation-control.json']
 OUT.write_text(json.dumps(dict(status=status,elapsed_s=time.monotonic()-start,time_budget_s=args.seconds,base_commit='2779845361312452b5c13b935158262b39a3f080',workspace_state='Base plus hash-bound portable study; not clean HEAD-only identity',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inputs={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in inputs},truths=truths,structures=structures,designs=designs,probes=cal['probes'],parameter_count=len(params),reading_bound_c=.02,constant_bias_bound_c=.02,observations=rows,checks=checks,scope='Structural synthetic screening and fixed-policy diagnostic only; no new policy inference/optimization, empirical truth, continuous certificate or award test.'),indent=2)+'\n')
try:
 observations={}
 for name,t in truths.items():
  p={**model.BASE,**t}
  for structure,(route,capacity) in structures.items():
   for design,q in designs.items():
    y,n=alt(p,q,route,capacity,30);key=(name,structure,design);observations[key]=y[:,cal['probes']]
    rows.append(dict(truth=name,structure=structure,design=design,compatible_indices=[],minimum_residual_c=float('inf')))
   # Initial slope: diffusion contributes exactly zero at uniform initial temperature.
   A,Q,n=affine(p,route,capacity);state=np.r_[np.full(len(n['cap']),40.),34.,1.]
   analytic=(n['ha']*(p['air_temp']-40.)+n['hb']*(34.-40.))/n['cap']
   slope=(A@state)[:len(analytic)]
   numeric=((expm(A*1e-4)@state)[:len(analytic)]-40.)/1e-4
   assert np.max(abs(slope-analytic))<1e-12
   assert np.max(abs(numeric-analytic))<1e-7
   for x in control['completed']:
    if x['truth']!=name or not x['accepted']:continue
    q=x['selected']['flow_lpm'];yy,nn=alt(p,q,route,capacity,1.);water=yy[:,:len(nn['cap'])];visible=water[:,nn['region']]
    exact=dict(min_temp=float(water.min()),max_temp=float(visible.max()),max_span=float(np.ptp(visible,axis=1).max()),final_body_temp_c=float(yy[-1,-2]))
    independent=replay(p,nn,q,route,capacity,1.)
    delta=max(abs(exact[k]-independent[k]) for k in exact)
    assert delta<2e-6,delta
    checks.append(dict(truth=name,structure=structure,policy_design=x['design'],flow_lpm=q,exact=exact,rk45=independent,maximum_method_difference_c=delta,initial_slope_difference=float(np.max(abs(slope-analytic))),finite_difference_slope_error=float(np.max(abs(numeric-analytic)))))
   save('checkpoint')
 cache={}
 for i,t in enumerate(params):
  p={**model.BASE,**t};thermal=tuple(t[k] for k in keys if k!='flow_multiplier')
  if thermal not in cache:cache[thermal]=original(p,designs['passive'])
  values={'passive':cache[thermal],'pulse':original(p,designs['pulse'])}
  for row in rows:
   key=(row['truth'],row['structure'],row['design']);a,residual,accepted=compatible_offset(values[row['design']]-observations[key])
   if residual<row['minimum_residual_c']:row.update(minimum_residual_c=residual,best_parameters=t,best_correction_c=a.tolist())
   if accepted:row['compatible_indices'].append(i)
  if i%250==0:save('checkpoint')
 for row in rows:row['compatible_count']=len(row['compatible_indices'])
 save('completed')
except Exception as e:
 save('failed: '+repr(e));raise
print(json.dumps(dict(elapsed_s=time.monotonic()-start,observations=[{k:v for k,v in r.items() if k!='compatible_indices'} for r in rows],policy_checks=[{k:v for k,v in r.items() if k not in ('rk45','flow_lpm')} for r in checks]),indent=2))
