"""Streaming sparse affine replay with first/second derivative envelopes.

Finite bank validation only; shared geometry is checked separately against fresh
networks. Interpolation bounds are conditional floating-point evidence.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,time
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix,block_diag,diags,bmat
from scipy.sparse.linalg import expm_multiply
ROOT=Path(__file__).resolve().parents[3]/'packages/praxis/demos/mcm-2016-a/reproduce'
sys.path[:0]=[str(ROOT),str(ROOT/'code')]
import model

GEOMETRY={}
def geometry(grid):
 key=tuple(grid)
 if key not in GEOMETRY:
  net=model.network(model.BASE,grid);nx,ny,nz=grid;N=len(net['cap'])
  area=model.BASE['L']/nx*model.BASE['W']/ny
  surf=np.array([area*model.BASE['foam'] if i%nz==nz-1 else 0. for i in range(N)])
  GEOMETRY[key]=(net,csr_matrix(net['G'])/model.BASE['D'],surf,net['ha']-model.BASE['h_surface']*surf,net['hb']/model.BASE['h_body'])
 return GEOMETRY[key]

def matrices(params,grid,route,capacity):
 net,g,surface,fixed,hb_unit=geometry(grid);cap=net['cap'];N=len(cap);nx,ny,nz=grid
 idx=lambda i,j,k:(i*ny+j)*nz+k
 path=[idx(i,ny//2,nz-1) for i in range(nx)]
 if route=='deep':path=[idx(0,ny//2,k) for k in range(nz-1,-1,-1)]+[idx(i,ny//2,0) for i in range(1,nx)]+[idx(nx-1,ny//2,k) for k in range(1,nz)]
 elif route!='surface':raise ValueError('Unknown route')
 A=[];Q=[]
 for p in params:
  ha=fixed+p['h_surface']*surface;hb=p['h_body']*hb_unit
  water=diags(1/cap)@(p['D']*g-diags(ha+hb))
  body=csr_matrix(hb.reshape(1,-1)/capacity) if capacity is not None else csr_matrix((1,N))
  body_self=csr_matrix([[-hb.sum()/capacity]]) if capacity is not None else csr_matrix((1,1))
  a=bmat([[water,csr_matrix((hb/cap).reshape(-1,1)),csr_matrix((ha*p['air_temp']/cap).reshape(-1,1))],
          [body,body_self,csr_matrix((1,1))],[csr_matrix((1,N)),csr_matrix((1,1)),csr_matrix((1,1))]],format='csr')
  rows=[];cols=[];values=[]
  for j,c in enumerate(path):
   f=p['rho']*p['cp']/60000/cap[c]*p['flow_multiplier']
   rows.extend([c,c]);cols.extend([c,path[j-1] if j else N+1]);values.extend([-f,f if j else f*p['inlet_temp']])
  q=csr_matrix((values,(rows,cols)),shape=(N+2,N+2))
  A.append(a);Q.append(q)
 return A,Q,net

def check_premise(b,N):
 m=b[:N+1,:N+1];off=m-diags(m.diagonal());minimum=float(off.data.min()) if off.nnz else 0.
 rowsum=float(np.asarray(m.sum(1)).max())
 if minimum < -1e-12 or rowsum > 1e-12:raise ValueError('No derivative contraction')
 return minimum,rowsum

def segment_bounds(states,rates,curvatures,net,dt):
 N=len(net['cap']);water=states[:,:,:N];visible=water[:,:,net['region']]
 lo=water.min(2);hi=visible.max(2);span=np.ptp(visible,axis=2)
 # Constant coordinates have identically zero derivatives; body is included.
 first=np.max(abs(rates[:,:,:N+1]),axis=2);second=np.max(abs(curvatures[:,:,:N+1]),axis=2)
 radius=np.minimum(first[:-1]*dt/2,second[:-1]*dt*dt/8)
 return (np.minimum(lo[:-1],lo[1:])-radius-2e-6,
         np.maximum(hi[:-1],hi[1:])+radius+2e-6,
         np.maximum(span[:-1],span[1:])+2*radius+4e-6,
         lo.min(0),hi.max(0),span.max(0))

def replay(params,grid,route,capacity,flows,budget,dt=1.):
 if len(flows)!=6 or 300/dt != round(300/dt):raise ValueError('Six300s stages and divisible sample required')
 A,Q,net=matrices(params,grid,route,capacity);N=len(net['cap']);count=len(params)
 y=np.array([np.r_[np.full(N,p['initial']),p['body_temp'],1.] for p in params]).reshape(-1)
 lower=np.full(count,np.inf);upper=-lower;spread=upper.copy();sample_lo=lower.copy();sample_hi=upper.copy();sample_span=upper.copy();premises=[]
 for flow in flows:
  budget();local=[a+float(flow)*q for a,q in zip(A,Q)]
  premises.extend(check_premise(b,N) for b in local)
  B=block_diag(local,format='csr');trace=float(B.diagonal().sum())
  for _ in range(10):
   budget();values=expm_multiply(B,y,start=0.,stop=30.,num=round(30/dt)+1,traceA=trace)
   rates=(B@values.T).T;curv=(B@rates.T).T
   shaped=values.reshape(-1,count,N+2);r=rates.reshape(shaped.shape);c=curv.reshape(shaped.shape)
   if np.max(abs(shaped[:,:,-1]-1.))>1e-10:raise ValueError('Constant coordinate drift')
   lo,hi,sp,sl,sh,ss=segment_bounds(shaped,r,c,net,dt)
   lower=np.minimum(lower,lo.min(0));upper=np.maximum(upper,hi.max(0));spread=np.maximum(spread,sp.max(0))
   sample_lo=np.minimum(sample_lo,sl);sample_hi=np.maximum(sample_hi,sh);sample_span=np.maximum(sample_span,ss)
   y=values[-1]
 return [dict(lower_bound_c=float(lower[i]),upper_bound_c=float(upper[i]),span_bound_c=float(spread[i]),
              min_temp=float(sample_lo[i]),max_temp=float(sample_hi[i]),max_span=float(sample_span[i]),
              sampled_passed=bool(sample_lo[i]>=39 and sample_hi[i]<=41 and sample_span[i]<=1.5),
              continuous_passed=bool(lower[i]>=39 and upper[i]<=41 and spread[i]<=1.5),
              fair_reserve_passed=bool(lower[i]>=39.13 and upper[i]<=40.9 and spread[i]<=1.4),
              water_l=float(5*sum(flows)*params[i]['flow_multiplier']),
              sample_s=dt,min_off_diagonal=min(x[0] for x in premises),max_row_sum=max(x[1] for x in premises)) for i in range(count)]
