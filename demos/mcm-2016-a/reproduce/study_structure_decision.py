"""Same-observation structural banks, base-grid envelopes and selected mesh failures.

Two frozen candidates and one bounded passive*.99 repair; no global optimization.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,hashlib,itertools,json,sys,time
from pathlib import Path
import numpy as np
from scipy.linalg import expm
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'code')]
import model
from study_calibration import compatible_offset
from check_structure import replay

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

def simulate(p,q,route,capacity,dt=30.):
 A,Q,n=affine(p,route,capacity)
 y=np.r_[np.full(len(n['cap']),p['initial']),p['body_temp'],1.]
 ys=[y.copy()]
 for v in q:
  E=expm((A+float(v)*p.get('flow_multiplier',1.)*Q)*dt)
  for _ in range(round(300/dt)):
   y=E@y;ys.append(y.copy())
 return np.array(ys),n

def certificate(p,q,route,capacity,budget):
 A,Q,n=affine(p,route,capacity);N=len(n['cap']);y=np.r_[np.full(N,p['initial']),p['body_temp'],1.];pieces=[]
 for v in q:
  budget();B=A+float(v)*p['flow_multiplier']*Q;M=B[:-1,:-1].copy();sums=M.sum(1);np.fill_diagonal(M,0.)
  assert M.min()>=-1e-12 and sums.max()<=1e-12
  E=expm(B);states=[y.copy()]
  for _ in range(300):y=E@y;states.append(y.copy())
  yy=np.array(states);t=np.arange(301,dtype=float)
  def bounds(t,yy):
   water=yy[:,:N];visible=water[:,n['region']];lo=water.min(1);hi=visible.max(1);sp=np.ptp(visible,axis=1)
   L=np.max(abs((yy@B.T)[:,:-1]),axis=1);radius=L[:-1]*np.diff(t)/2
   lb=np.minimum(lo[:-1],lo[1:])-radius-2e-6;ub=np.maximum(hi[:-1],hi[1:])+radius+2e-6;sb=np.maximum(sp[:-1],sp[1:])+2*radius+4e-6
   return lb,ub,sb
  rounds=0
  while True:
   lb,ub,sb=bounds(t,yy);bad=(lb<39)|(ub>41)|(sb>1.5)
   if not bad.any() or rounds==8:break
   budget();mid=(t[:-1][bad]+t[1:][bad])/2
   left=yy[:-1][bad];gap=np.diff(t)[bad]/2
   inserted=np.array([expm(B*h)@state for h,state in zip(gap,left)])
   order=np.argsort(np.r_[t,mid]);t=np.r_[t,mid][order];yy=np.vstack([yy,inserted])[order];rounds+=1
  pieces.append(dict(lower_bound_c=float(lb.min()),upper_bound_c=float(ub.max()),span_bound_c=float(sb.max()),row_sum_max=float(sums.max()),off_diagonal_min=float(M.min()),refinement_rounds=rounds,envelope_points=len(t),continuous_passed=bool((lb>=39).all() and (ub<=41).all() and (sb<=1.5).all())))
 return dict(lower_bound_c=min(x['lower_bound_c'] for x in pieces),upper_bound_c=max(x['upper_bound_c'] for x in pieces),span_bound_c=max(x['span_bound_c'] for x in pieces),continuous_passed=all(x['continuous_passed'] for x in pieces),max_refinement_rounds=max(x['refinement_rounds'] for x in pieces),segments=pieces)

def metrics(states,net):
 water=states[:,:len(net['cap'])];visible=water[:,net['region']]
 return dict(min_temp=float(water.min()),max_temp=float(visible.max()),max_span=float(np.ptp(visible,axis=1).max()))

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--seconds',type=float,default=180.)
 args=parser.parse_args()
 if args.output.exists():parser.error('Preserve previous evidence')
 if not np.isfinite(args.seconds) or args.seconds<=0:parser.error('Finite positive budget required')
 args.output.parent.mkdir(parents=True,exist_ok=True)
 start=time.monotonic()
 def budget():
  if time.monotonic()-start>args.seconds:raise TimeoutError('Cooperative study budget exhausted')
 cal=json.loads((HERE/'reference/calibration-study.json').read_text());iv=json.loads((HERE/'reference/information-value.json').read_text())
 keys=list(cal['parameter_grid']);prior=[dict(zip(keys,v)) for v in itertools.product(*cal['parameter_grid'].values())]
 truth={**model.BASE,'flow_multiplier':1.}
 structures={'surface_fixed':['surface',None],'deep_fixed':['deep',None],'surface_finite':['surface',253310.]}
 designs={'passive':[0.]*6,'pulse':[0.,0.,1.2,0.,0.,0.]}
 frozen={'passive':iv['rounds'][-1]['flow_lpm'],'pulse':cal['rounds'][-1]['flow_lpm']}
 policies={'frozen':frozen,'scaled':{d:[v*(.99 if d=='passive' else 1.) for v in q] for d,q in frozen.items()}}
 receipt=dict(status='started',base_commit='8226872b6fa027d6a253d6eb469b84f66235be32',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inputs={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['code/model.py','check_structure.py','study_calibration.py','reference/calibration-study.json','reference/information-value.json']},truth=truth,structures=structures,designs=designs,policies=policies,parameter_grid=cal['parameter_grid'],probes=cal['probes'],reading_bound_c=.02,constant_bias_bound_c=.02,banks=[],base_envelopes=[],selected_replays=[],budget_s=args.seconds,integration_allowance_c=2e-6,scope='Finite same-observation banks. All-bank base-grid floating-point contraction envelopes; original candidate extrema select17 parameter/structure/design cases, each at1s on three meshes with independent RHS. No all-fine-bank/empirical/posterior/global-optimum or equal-design-reserve repaired-policy claim.')
 def save(status):
  receipt.update(status=status,elapsed_s=time.monotonic()-start)
  args.output.write_text(json.dumps(receipt,indent=2)+'\n')
 try:
  budget()
  observed={d:simulate(truth,q,'surface',None,30.)[0][:,cal['probes']] for d,q in designs.items()}
  receipt['observed']={d:v.tolist() for d,v in observed.items()}
  for structure,(route,capacity) in structures.items():
   cache={};groups={d:dict(structure=structure,design=d,indices=[]) for d in designs}
   for i,params in enumerate(prior):
    budget();p={**model.BASE,**params};thermal=tuple(params[k] for k in keys if k!='flow_multiplier')
    if thermal not in cache:cache[thermal]=simulate(p,designs['passive'],route,capacity,30.)[0][:,cal['probes']]
    readings={'passive':cache[thermal],'pulse':simulate(p,designs['pulse'],route,capacity,30.)[0][:,cal['probes']]}
    for d,values in readings.items():
     _,_,accepted=compatible_offset(values-observed[d])
     if accepted:groups[d]['indices'].append(i)
   receipt['banks'].extend(groups.values());save('screen checkpoint')
  for bank in receipt['banks']:
   d,structure=bank['design'],bank['structure'];route,capacity=structures[structure];summaries=[]
   for i in bank['indices']:
    budget();y,net=simulate({**model.BASE,**prior[i]},frozen[d],route,capacity,5.)
    summaries.append(dict(prior_index=i,**metrics(y,net)))
   selected=sorted({fn(summaries,key=lambda r:r[field])['prior_index'] for field,fn in [('min_temp',min),('max_temp',max),('max_span',max)]})
   bank['selected_indices']=selected
   for name,policy in policies.items():
    group=dict(policy=name,structure=structure,design=d,records=[]);receipt['base_envelopes'].append(group)
    for i in bank['indices']:
     budget();bounds=certificate({**model.BASE,**prior[i]},policy[d],route,capacity,budget)
     # All interval checks execute above; compact final receipt keeps extrema and premise.
     pieces=bounds.pop('segments');bounds['max_row_sum']=max(x['row_sum_max'] for x in pieces);bounds['min_off_diagonal']=min(x['off_diagonal_min'] for x in pieces)
     group['records'].append(dict(prior_index=i,**bounds))
    save('envelope checkpoint')
    for i in selected:
     p={**model.BASE,**prior[i]}
     for grid in [(8,4,3),(12,6,4),(16,8,6)]:
      budget();r=replay(p,model.network(p,grid),np.array(policy[d])*p['flow_multiplier'],route,capacity,1.)
      if r['instantaneous_balance_residual_w']>=1e-6 or r['integrated_balance_residual_j']>=.1:raise ValueError('Energy accounting failed')
      difference=None
      if grid==(8,4,3):
       states,net=simulate(p,policy[d],route,capacity,1.);exact=metrics(states,net)
       difference=max(abs(r[k]-exact[k]) for k in exact)
       if difference>=2e-6:raise ValueError('Matched-sample implementations disagree')
      receipt['selected_replays'].append(dict(policy=name,structure=structure,design=d,prior_index=i,grid=list(grid),parameters=prior[i],same_sample_summary_difference_c=difference,**r))
    save('mesh checkpoint')
  save('completed')
 except Exception as exc:
  save('failed: '+repr(exc));raise
 print(json.dumps(dict(status=receipt['status'],elapsed_s=receipt['elapsed_s'],banks=[{k:len(v) if k.endswith('indices') else v for k,v in b.items()} for b in receipt['banks']],selected_failures=[{k:r[k] for k in ['policy','structure','design','prior_index','grid','max_temp']} for r in receipt['selected_replays'] if not r['sampled_passed']]),indent=2))

if __name__=='__main__':main()
