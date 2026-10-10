"""Independent direct-network diagnostics and exact interval endpoint checks."""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib,io
import numpy as np
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[4]
payload=(ROOT/'boundary.json').read_bytes();r=json.loads(payload)
f=lambda pair:F(int(pair[0]),int(pair[1]))
floatF=lambda x:F.from_float(float(x))
w=list(map(f,r['weights']));supports={k:{'affine':list(map(f,v['affine'])),'residuals':[list(map(f,x)) for x in v['residuals']]} for k,v in r['supports'].items()}
def dot(a,p):return sum(x*y for x,y in zip(a,p))
def bound(kind,p):v=supports[kind];return dot(v['affine'],p)+sum(min(F(0),dot(x,p)) for x in v['residuals'])
def flux(q,p):return -bound('q0' if not q else 'q3',p)+dot(list(map(f,r['d'])),p)+q*f(r['hh'])
def gap(s,l,z):p=[F(1),s,l,z];return bound('end',p)-sum(w)-1800*max(flux(0,p),flux(3,p))
with np.load(REPO/'demos/mcm-2016-a/reproduce/reference/whole-horizon-exclusion.npz',allow_pickle=False) as z:raw={n:z[n].tobytes() for n in z.files}
for n,h in r['input_sha256'].items():assert hashlib.sha256(raw['network96/'+n]).hexdigest()==h
with np.load(io.BytesIO(raw['network96/primitives.npz']),allow_pickle=False) as z:n={k:z[k] for k in z.files}
with np.load(io.BytesIO(raw['network96/problem.npz']),allow_pickle=False) as z:path=list(z['path'])
N=len(w);points=[];endpoint_checks=[]
for row in r['boundary_rows']:
 l,z=map(f,[row['loss_scale'],row['span_c']])
 for interval in row['certified_intervals']:
  lo,hi=map(f,[interval['left'],interval['right']]);assert lo<hi
  for end,included in [(lo,interval['left_included']),(hi,interval['right_included'])]:assert (gap(end,l,z)>0)==included
  for t in [F(1,4),F(1,2),F(3,4)]:assert gap(lo+(hi-lo)*t,l,z)>0
  endpoint_checks.append({'loss':float(l),'span':float(z),'left_gap':float(gap(lo,l,z)),'right_gap':float(gap(hi,l,z))})
  points.append(((lo+hi)/2,l,z))
# Independently assembled physical loss/conduction/inlet network, solver diagnoses
# only (the continuous parameter theorem is the exact support/convexity argument).
diagnostics=[]
for s,l,z in points:
 K=(float(s)*n['G']-np.diag(float(l)*(n['ha']+n['hb'])))/n['cap'][:,None]
 d=(-17*float(l)*n['ha']-5*float(l)*n['hb']+39*float(s)*n['G'].sum(axis=1))/n['cap']
 B=np.zeros((N,N));h=np.zeros(N)
 for k,i in enumerate(path):
  beta=4180*1000/60000/n['cap'][i];B[i,i]-=beta
  if k:B[i,path[k-1]]+=beta
  else:h[i]+=11*beta
 A=[];b=[]
 for i in np.flatnonzero(n['region']):
  v=np.zeros(N+2);v[i]=1;v[N]=-1;A.append(v);b.append(0)
  v=np.zeros(N+2);v[N+1]=1;v[i]=-1;A.append(v);b.append(0)
 v=np.zeros(N+2);v[N]=1;v[N+1]=-1;A.append(v);b.append(float(z))
 bounds=[(0,2 if x else 11) for x in n['region']]+[(0,2),(0,2)]
 wf=np.array(list(map(float,w)))
 for q in [0,3]:
  obj=np.r_[-wf@(K+q*B),0,0]
  sol=linprog(obj,A_ub=np.array(A),b_ub=np.array(b),bounds=bounds,method='highs',options={'time_limit':2});assert sol.success
  actual=-sol.fun+wf@(d+q*h);cert=float(flux(q,[F(1),s,l,z]));assert actual<=cert+1e-10
  diagnostics.append({'s':float(s),'loss':float(l),'span':float(z),'q':q,'direct_LP_rate':float(actual),'certificate_upper':cert})
# Exact baseline replay identity, and convex interpolation of certified points.
assert gap(F(1),F(1),F(3,2))==f(r['baseline_gap'])
for a,b in zip(points,points[1:]):
 p=tuple((x+y)/2 for x,y in zip(a,b));assert gap(*p)>0
out={'status':'passed','source_sha256':hashlib.sha256(payload).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'exact_interval_checks':endpoint_checks,'direct_network_LP_diagnostics':diagnostics,'convex_interpolation_checks':max(0,len(points)-1),'scope':'Exact positive intervals/endpoints and independent network LP diagnostics; diagnostics floating, continuous certificate validity requires the independent algebra review; no feasible policy or actual bath validation'}
print(json.dumps(out,indent=2))
