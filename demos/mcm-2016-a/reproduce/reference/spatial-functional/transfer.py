from pathlib import Path
import io, json,hashlib,time
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
repo=Path(__file__).resolve().parents[5];root=args.output;root.mkdir(parents=True,exist_ok=False)
started=time.monotonic();records=[]
for scale in [1.,10/3,10.]:
 archive='whole-horizon-exclusion'
 with np.load(repo/'demos/mcm-2016-a/reproduce/reference'/f'{archive}.npz',allow_pickle=False) as z:files={n:z[n].tobytes() for n in z.files}
 labels=['network96'] if archive.startswith('whole') else ['network96','network288','network768']
 for label in labels:
  load=lambda n:dict(np.load(io.BytesIO(files[label+'/'+n]),allow_pickle=False))
  prim=load('primitives.npz');sol=load('solution.npz');prob=load('problem.npz');N=len(prim['cap'])
  K=(scale*prim['G']-np.diag(prim['ha']+prim['hb']))/prim['cap'][:,None];d=(39*scale*prim['G'].sum(1)-17*prim['ha']-5*prim['hb'])/prim['cap']
  S=np.zeros((N,N));source=np.zeros(N);path=prob['path'];beta=(209/3)/prim['cap']
  for j,i in enumerate(path):
   S[i,i]=-beta[i]
   if j:S[i,path[j-1]]=beta[i]
   else:source[i]=11*beta[i]
  region=prim['region'];bounds=[(0,2 if x else 11) for x in region]+[(0,2),(0,2)];rr=[];cc=[];vv=[];b=[]
  for i in np.flatnonzero(region):
   k=len(b);rr.extend([k,k,k+1,k+1]);cc.extend([int(i),N,N+1,int(i)]);vv.extend([1,-1,1,-1]);b.extend([0.,0.])
  k=len(b);rr.extend([k,k]);cc.extend([N,N+1]);vv.extend([1,-1]);b.append(1.5)
  A=coo_matrix((vv,(rr,cc)),shape=(len(b),N+2)).tocsr();b=np.array(b)
  raw=sol['inequality_dual'][:2*N].reshape(N,2);w=raw[:,0]-raw[:,1]
  norm=np.abs(w).sum();assert norm>0;w/=norm
  for sign in [-1]:
   if time.monotonic()-started>120:raise TimeoutError('phase120s')
   ww=sign*w;support=[]
   for kind,c in [('end',ww),('q0',-(ww@K)),('q3',-(ww@(K+3*S)))]:
    c=np.r_[c,0,0];out=linprog(c,A_ub=A,b_ub=b,bounds=bounds,method='highs',options={'time_limit':3})
    assert out.success,(kind,out.message)
    support.append(dict(kind=kind,value=float(out.fun),dual_ub=out.ineqlin.marginals.tolist(),dual_lower=out.lower.marginals.tolist(),dual_upper=out.upper.marginals.tolist()))
   F0=-support[1]['value']+ww@d;F3=-support[2]['value']+ww@(d+3*source);gap=support[0]['value']-ww.sum()-1800*max(F0,F3)
   records.append(dict(archive=archive,network=label,sign=sign,diffusion_scale=str(scale),D=.0003*scale,weights=ww.tolist(),end_lower=support[0]['value'],initial=float(ww.sum()),flux_upper_q0=float(F0),flux_upper_q3=float(F3),gap=float(gap),supports=support,input_sha256={n:hashlib.sha256(files[label+'/'+n]).hexdigest() for n in ['primitives.npz','solution.npz','problem.npz']}))
print([(r['archive'],r['network'],r['sign'],r['gap']) for r in records])
(root/'transfer-results.json').write_text(json.dumps({'elapsed_s':time.monotonic()-started,'records':records},indent=2)+'\n')
