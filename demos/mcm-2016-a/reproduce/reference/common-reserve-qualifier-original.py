"""Streaming affine qualification with local subdivision of unresolved intervals."""
import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent/'structure-fair-control'))
import batch_checked, batch
import numpy as np
from scipy.sparse import block_diag
from scipy.sparse.linalg import expm_multiply

def replay(params,grid,route,capacity,flows,budget):
 # Same guard as archived replay, without doing that archived full computation.
 if not params or len(flows)!=6 or any(not math.isfinite(float(v)) or v<0 for v in flows):raise ValueError('Invalid bank/flows')
 varying={'D','h_surface','h_body','flow_multiplier'}
 for p in params:
  if any(p.get(k)!=v for k,v in batch.model.BASE.items() if k not in varying):raise ValueError('Frozen geometry changed')
  if any(isinstance(p.get(k),bool) or not math.isfinite(float(p[k])) or p[k]<=0 for k in varying):raise ValueError('Invalid bank coefficient')
 A,Q,net=batch.matrices(params,grid,route,capacity);N=len(net['cap']);count=len(params)
 y=np.array([np.r_[np.full(N,p['initial']),p['body_temp'],1.] for p in params]).reshape(-1)
 lower=np.full(count,np.inf);upper=np.full(count,-np.inf);spread=upper.copy();sl=lower.copy();sh=upper.copy();ss=upper.copy();premises=[];refinements=np.zeros(count,dtype=int)
 def sampled(states,ids):
  water=states[:,:N];v=water[:,net['region']]
  np.minimum.at(sl,ids,water.min(1));np.maximum.at(sh,ids,v.max(1));np.maximum.at(ss,ids,np.ptp(v,axis=1))
 def accumulate(lb,ub,sb,ids):
  np.minimum.at(lower,ids,lb);np.maximum.at(upper,ids,ub);np.maximum.at(spread,ids,sb)
 for flow in flows:
  budget();local=[a+float(flow)*q for a,q in zip(A,Q)];premises.extend(batch.check_premise(b,N) for b in local)
  B=block_diag(local,format='csr');trace=float(B.diagonal().sum())
  for _ in range(10):
   budget();values=expm_multiply(B,y,start=0.,stop=30.,num=31,traceA=trace)
   if not np.isfinite(values).all():raise ValueError('Nonfinite trajectory')
   shaped=values.reshape(-1,count,N+2)
   if np.max(abs(shaped[:,:,-1]-1.))>1e-10:raise ValueError('Constant drift')
   rates=(B@values.T).T.reshape(shaped.shape);curv=(B@((B@values.T))).T.reshape(shaped.shape)
   lb,ub,sb,_,_,_=batch.segment_bounds(shaped,rates,curv,net,1.)
   sampled(shaped.reshape(-1,N+2),np.tile(np.arange(count),31))
   valid=(lb>=39.13)&(ub<=40.9)&(sb<=1.4)
   good_time,good_ids=np.where(valid);accumulate(lb[good_time,good_ids],ub[good_time,good_ids],sb[good_time,good_ids],good_ids)
   times,ids=np.where(~valid);left=shaped[times,ids].copy();right=shaped[times+1,ids].copy();width=1.
   # Only unresolved intervals are propagated again, including multiple
   # different time intervals for the same model as separate block copies.
   for level in range(1,5):
    if not len(ids):break
    budget();operator=block_diag([local[int(i)] for i in ids],format='csr')
    mids=expm_multiply(operator*(width/2),left.reshape(-1),traceA=float(operator.diagonal().sum())*width/2).reshape(-1,N+2)
    sampled(mids,ids);np.add.at(refinements,ids,1)
    pairs=np.array([np.concatenate([left,mids]),np.concatenate([mids,right])]);pair_ids=np.tile(ids,2)
    flat=pairs.reshape(2,-1);op=block_diag([local[int(i)] for i in pair_ids],format='csr')
    rr=(op@flat.T).T.reshape(pairs.shape);cc=(op@(op@flat.T)).T.reshape(pairs.shape)
    lo,hi,sp,_,_,_=batch.segment_bounds(pairs,rr,cc,net,width/2);lo,hi,sp=lo[0],hi[0],sp[0]
    accept=(lo>=39.13)&(hi<=40.9)&(sp<=1.4)
    if level==4:accept=np.ones(len(pair_ids),dtype=bool)
    accumulate(lo[accept],hi[accept],sp[accept],pair_ids[accept])
    pending=~accept;left=pairs[0,pending].copy();right=pairs[1,pending].copy();ids=pair_ids[pending];width/=2
   y=values[-1]
 return [dict(lower_bound_c=float(lower[i]),upper_bound_c=float(upper[i]),span_bound_c=float(spread[i]),min_temp=float(sl[i]),max_temp=float(sh[i]),max_span=float(ss[i]),sampled_passed=bool(sl[i]>=39 and sh[i]<=41 and ss[i]<=1.5),continuous_passed=bool(lower[i]>=39 and upper[i]<=41 and spread[i]<=1.5),fair_sample_passed=bool(sl[i]>=39.13 and sh[i]<=40.9 and ss[i]<=1.4),fair_reserve_passed=bool(lower[i]>=39.13 and upper[i]<=40.9 and spread[i]<=1.4),water_l=float(5*sum(flows)*params[i]['flow_multiplier']),max_initial_gap_s=1.,max_refinement_depth=4,midpoint_count=int(refinements[i]),min_off_diagonal=min(x[0] for x in premises),max_row_sum=max(x[1] for x in premises)) for i in range(count)]
