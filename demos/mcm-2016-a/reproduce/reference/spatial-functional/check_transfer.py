"""Independent rational state-support verification; never calls a solver."""
from pathlib import Path
from fractions import Fraction as F
import io,json,hashlib,time,sys
sys.set_int_max_str_digits(20000)  # Standalone checker process only; long exact receipts are bounded.
import numpy as np
ROOT=Path(__file__).resolve().parent;repo=Path(__file__).resolve().parents[5]
start=time.monotonic();payload=(ROOT/'transfer-results.json').read_bytes();record=json.loads(payload);cache={}
def f(x):
 x=float(x)
 if not np.isfinite(x):raise ValueError('nonfinite')
 if x not in cache:cache[x]=F.from_float(x)
 return cache[x]
def check(row,mutation=None):
 with np.load(repo/'demos/mcm-2016-a/reproduce/reference'/(row['archive']+'.npz'),allow_pickle=False) as z:raw={n:z[n].tobytes() for n in z.files}
 for name,digest in row['input_sha256'].items():assert hashlib.sha256(raw[row['network']+'/'+name]).hexdigest()==digest
 with np.load(io.BytesIO(raw[row['network']+'/primitives.npz']),allow_pickle=False) as z:n={k:z[k] for k in z.files}
 with np.load(io.BytesIO(raw[row['network']+'/problem.npz']),allow_pickle=False) as z:path=list(z['path'])
 N=len(n['cap']);w=[f(x) for x in row['weights']];assert len(w)==N and any(w)
 if mutation=='zero_weight':w=[F(0)]*N
 if mutation=='wrong_floor':floor=F(38)
 else:floor=F(39)
 upper=[F(41 if v else 50)-floor for v in n['region']]+[F(2)]*2
 rr=[]
 for i in np.flatnonzero(n['region']):rr += [({int(i):F(1),N:F(-1)},F(0)),({N+1:F(1),int(i):F(-1)},F(0))]
 rr.append(({N:F(1),N+1:F(-1)},F(3,2)))
 a=[F(0)]*N;d=F(0);ss=[F(0)]*N;hh=F(0)
 for i in range(N):
  v=w[i]/f(n['cap'][i]);rowsum=F(0)
  for j in np.flatnonzero(n['G'][i]):
   g=f(n['G'][i,j])*F(row['diffusion_scale']);a[int(j)]+=v*g;rowsum+=g
  a[i]-=v*(f(n['ha'][i])+f(n['hb'][i]))
  d+=v*(floor*rowsum-(floor-22)*f(n['ha'][i])-(floor-34)*f(n['hb'][i]))
 for k,i in enumerate(path):
  b=w[i]*F(209,3)/f(n['cap'][i]);ss[i]-=b
  if k:ss[path[k-1]]+=b
  else:hh+=b*(50-floor)
 out={}
 for rec in row['supports']:
  kind=rec['kind'];c=(w if kind=='end' else [-v for v in a] if kind=='q0' else [-v-3*s for v,s in zip(a,ss)])+[F(0)]*2
  mu=[min(f(x),F(0)) for x in rec['dual_ub']];nu=[max(f(x),F(0)) for x in rec['dual_lower']];eta=[min(f(x),F(0)) for x in rec['dual_upper']]
  assert len(mu)==len(rr) and len(nu)==len(eta)==len(c)
  if mutation=='zero_dual':mu=[F(0)]*len(mu);nu=[F(0)]*len(nu);eta=[F(0)]*len(eta)
  residual=[c[i]-nu[i]-eta[i] for i in range(N+2)]
  val=sum(bound*v for (_,bound),v in zip(rr,mu))+sum(u*v for u,v in zip(upper,eta))
  for (coeff,_),v in zip(rr,mu):
   for j,coef in coeff.items():residual[j]-=coef*v
  val+=sum(min(F(0),r*u) for r,u in zip(residual,upper))
  out[kind]=val
 R0=-out['q0']+d;R3=-out['q3']+d+3*hh;rate=max(R0,R3);initial=(40-floor)*sum(w);gap=out['end']-initial-1800*rate
 ratio=(initial-out['end'])/(-rate) if rate<0 else None
 bound=ratio.numerator//ratio.denominator+1 if ratio is not None else None
 if bound is not None:assert ratio<F(bound)
 return {'gap_exact_numerator':str(gap.numerator),'gap_exact_denominator':str(gap.denominator),'safe_time_exact_numerator':str(ratio.numerator) if ratio is not None else None,'safe_time_exact_denominator':str(ratio.denominator) if ratio is not None else None,'strict_safe_time_upper_integer_s':bound,'exact_time_below_integer':ratio<F(bound) if bound is not None else None,'gap_display':float(gap),'strict_gap_gt':str(gap.numerator//gap.denominator) if gap>0 else None,'positive':gap>0,'initial':float(initial),'end_lower':float(out['end']),'flux_upper_q0':float(R0),'flux_upper_q3':float(R3),'horizon_upper_s':float((initial-out['end'])/(-rate)) if rate<0 else None,'scope':'signed spatial-temperature functional, not physical shortfall; exact archived binary coefficient network'}
checks=[]
for row in record['records']:
 if time.monotonic()-start>60:raise TimeoutError('exact60s')
 r=check(row);checks.append({'archive':row['archive'],'network':row['network'],'sign':row['sign'],**r})
negatives=[]
for row in record['records']:
 if row['sign']!= -1:continue
 for mutation in ['zero_weight','zero_dual']:
  actual=check(row,mutation);assert not actual['positive'];negatives.append({'archive':row['archive'],'network':row['network'],'mutation':mutation,'positive':actual['positive']})
result={'source_sha256':hashlib.sha256(payload).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'elapsed_s':time.monotonic()-start,'checks':checks,'negative_checks':negatives,'exact_rational_verification':True}
print(json.dumps(result,indent=2))
