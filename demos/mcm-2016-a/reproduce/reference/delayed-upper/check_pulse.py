from pathlib import Path
import sys,json,time,hashlib
import numpy as np
from scipy.integrate import solve_ivp
root=Path(__file__).resolve().parent
start=time.monotonic();screen=json.loads((root/'pulse-policies.json').read_text());assert hashlib.sha256((root/'primitives.npz').read_bytes()).hexdigest()==screen['primitive_sha256'];n=np.load(root/'primitives.npz',allow_pickle=False);C=n['cap'];N=len(C);A0=(n['G']-np.diag(n['ha']+n['hb']))/C[:,None];v0=(22*n['ha']+34*n['hb'])/C
B=np.zeros_like(A0);h=np.zeros(N);path=[(i*4+2)*3+2 for i in range(8)]
for j,i in enumerate(path):
 beta=4180000/(60000*C[i]);B[i,i]=-beta
 if j:B[i,path[j-1]]=beta
 else:h[i]=50*beta
rows=[]
for r in screen['selected']:
 y=np.full(N,40.);envelopes=[];elapsed=0.;accumulated_error=0.
 for q,duration in [(0.,r['delay']),(r['lead'],r['pulse']),(r['tail'],1800-r['delay']-r['pulse'])]:
  A=A0+q*B;v=v0+q*h
  assert (A-np.diag(np.diag(A))).min()>=0 and A.sum(axis=1).max()<0
  ystart=y.copy();curvature=float(np.max(np.abs(A@(A@ystart+v))));ts=np.linspace(0,duration,int(np.ceil(duration/.1))+1)
  sol=solve_ivp(lambda t,z:A@z+v,(0,duration),ystart,method='DOP853',rtol=1e-11,atol=1e-12,max_step=5,dense_output=True);assert sol.success
  ys=sol.sol(ts).T;y=ys[-1];accumulated_error+=2e-6
  step=duration/(len(ts)-1);allowance=curvature*step**2/8+accumulated_error
  i,j=np.unravel_index(np.argmin(ys),ys.shape)
  envelopes.append({'floor_c':float(ys.min()-allowance),'ceiling_c':float(ys[:,n['region']].max()+allowance),'spread_c':float(np.ptp(ys[:,n['region']],axis=1).max()+2*allowance),'sample_min_c':float(ys[i,j]),'sample_min_s':float(elapsed+ts[i]),'sample_min_cell':int(j),'allowance_c':allowance,'flow_l_min':q,'duration_s':duration})
  elapsed+=duration;assert time.monotonic()-start<60
 qualified=all(e['floor_c']>=39 and e['ceiling_c']<=41 and e['spread_c']<=1.5 for e in envelopes)
 assert abs(y.min()-r['terminal_floor'])<1e-7
 rows.append({'policy':r,'envelopes':envelopes,'qualified':qualified,'water_l':sum(e['flow_l_min']*e['duration_s']/60 for e in envelopes)})
assert len(rows)==3 and all(r['qualified'] for r in rows)
result={'rows':rows,'elapsed_s':time.monotonic()-start,'policies_sha256':hashlib.sha256((root/'pulse-policies.json').read_bytes()).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'model_sha256':screen['model_sha256'],'scope':'Three selected original96 strong-mixing two-stage policies, independent stream/DOP853 and0.1s chord. Each phase assumes2e-6C solver error, accumulated across nonexpansive phase boundaries; conditional floating qualification, no interval/PDE/empirical/global optimum.'}
result['primitive_sha256']=screen['primitive_sha256'];print(json.dumps(result,indent=2))
