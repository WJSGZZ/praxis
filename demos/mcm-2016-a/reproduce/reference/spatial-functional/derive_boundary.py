"""Exact parametric support certificate; no solver or thermal integration."""
from pathlib import Path
from fractions import Fraction as F
import json,io,hashlib,time,sys
import numpy as np
sys.set_int_max_str_digits(20000)
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
start=time.monotonic()
def ff(x):return F.from_float(float(x))
def encode(x):return [str(x.numerator),str(x.denominator)]
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def mul(k,a):return tuple(k*x for x in a)
def at(a,s,l,z):return a[0]+a[1]*s+a[2]*l+a[3]*z
# coefficients ordered constant, diffusion scale, common heat-loss scale, span
zero=(F(0),)*4
record=json.loads((REPO/'demos/mcm-2016-a/reproduce/reference/spatial-functional/potential-results.json').read_text())
row=next(r for r in record['records'] if r['archive']=='whole-horizon-exclusion' and r['sign']==-1)
with np.load(REPO/'demos/mcm-2016-a/reproduce/reference/whole-horizon-exclusion.npz',allow_pickle=False) as z:raw={k:z[k].tobytes() for k in z.files}
load=lambda name:dict(np.load(io.BytesIO(raw['network96/'+name]),allow_pickle=False))
n=load('primitives.npz');path=list(load('problem.npz')['path']);N=len(n['cap']);w=list(map(ff,row['weights']));upper=[F(2 if r else 11) for r in n['region']]+[F(2),F(2)]
rr=[]
for i in np.flatnonzero(n['region']):rr.extend([({int(i):F(1),N:F(-1)},zero),({N+1:F(1),int(i):F(-1)},zero)])
rr.append(({N:F(1),N+1:F(-1)},(F(0),F(0),F(0),F(1))))
a=[zero for _ in range(N)];d=zero;ss=[F(0)]*N;hh=F(0)
for i in range(N):
 v=w[i]/ff(n['cap'][i]);rowsum=F(0)
 for j in np.flatnonzero(n['G'][i]):
  g=ff(n['G'][i,j]);a[int(j)]=add(a[int(j)],(F(0),v*g,F(0),F(0)));rowsum+=g
 a[i]=add(a[i],(F(0),F(0),-v*(ff(n['ha'][i])+ff(n['hb'][i])),F(0)))
 d=add(d,(F(0),39*v*rowsum,-v*(17*ff(n['ha'][i])+5*ff(n['hb'][i])),F(0)))
for k,i in enumerate(path):
 v=w[i]*F(209,3)/ff(n['cap'][i]);ss[i]-=v
 if k:ss[path[k-1]]+=v
 else:hh+=11*v
supports={}
for rec in row['supports']:
 kind=rec['kind'];c=[(v,F(0),F(0),F(0)) for v in w] if kind=='end' else [add(mul(-1,x),(-3*y if kind=='q3' else F(0),F(0),F(0),F(0))) for x,y in zip(a,ss)]
 c+= [zero,zero];mu=[min(ff(x),F(0)) for x in rec['dual_ub']];nu=[max(ff(x),F(0)) for x in rec['dual_lower']];eta=[min(ff(x),F(0)) for x in rec['dual_upper']]
 residual=[add(x,(-v-e,F(0),F(0),F(0))) for x,v,e in zip(c,nu,eta)]
 val=(sum(u*e for u,e in zip(upper,eta)),F(0),F(0),F(0))
 for (coeff,b),v in zip(rr,mu):
  val=add(val,mul(v,b))
  for j,t in coeff.items():residual[j]=add(residual[j],(-t*v,F(0),F(0),F(0)))
 supports[kind]={'affine':val,'residuals':[mul(u,r) for u,r in zip(upper,residual)]}
def lower(kind,s,l,z):
 v=supports[kind];return at(v['affine'],s,l,z)+sum(min(F(0),at(r,s,l,z)) for r in v['residuals'])
def rate(q,s,l,z):return -lower('q0' if q==0 else 'q3',s,l,z)+at(d,s,l,z)+q*hh
def gap(s,l,z):return lower('end',s,l,z)-sum(w)-1800*max(rate(0,s,l,z),rate(3,s,l,z))
def piece(kind,q,s,l,z):
 v=supports[kind];aff=v['affine']
 for r in v['residuals']:
  if at(r,s,l,z)<0:aff=add(aff,r)
 return add(add(mul(-1,aff),d),(q*hh,F(0),F(0),F(0)))
def intervals(l,z):
 cuts={F(1,2),F(10)}
 for kind in ['q0','q3']:
  for r in supports[kind]['residuals']:
   if r[1]:
    b=-(r[0]+r[2]*l+r[3]*z)/r[1]
    if F(1,2)<b<F(10):cuts.add(b)
 cuts=sorted(cuts);pieces=[]
 E=lower('end',F(1),l,z)-sum(w)
 for lo,hi in zip(cuts,cuts[1:]):
  mid=(lo+hi)/2;left,right=lo,hi
  for q,kind in [(0,'q0'),(3,'q3')]:
   c=piece(kind,q,mid,l,z);A=E-1800*(c[0]+c[2]*l+c[3]*z);B=-1800*c[1]
   if not B:
    if A<=0:left,right=hi,lo
   elif B>0:left=max(left,-A/B)
   else:right=min(right,-A/B)
  if left<right:
   assert gap((left+right)/2,l,z)>0
   pieces.append([left,right])
 merged=[]
 for lo,hi in pieces:
  if merged and merged[-1][1]==lo and gap(lo,l,z)>0:merged[-1][1]=hi
  else:merged.append([lo,hi])
 return [{'left':encode(lo),'right':encode(hi),'left_included':gap(lo,l,z)>0,'right_included':gap(hi,l,z)>0,'D_left':float(lo*F(3,10000)),'D_right':float(hi*F(3,10000))} for lo,hi in merged]
rows=[]
for l in [F(4,5),F(1),F(6,5)]:
 for z in [F(3,4),F(1),F(3,2),F(2)]:
  if time.monotonic()-start>90:raise TimeoutError('90second exact route')
  rows.append({'loss_scale':encode(l),'span_c':encode(z),'certified_intervals':intervals(l,z)})
# Exact baseline agrees with independently archived one-point certificate.
old=json.loads((REPO/'demos/mcm-2016-a/reproduce/reference/spatial-functional/exact-checks.json').read_text()) if (REPO/'demos/mcm-2016-a/reproduce/reference/spatial-functional/exact-checks.json').exists() else None
checks=[]
for l in [F(4,5),F(1),F(6,5)]:
 for z in [F(3,4),F(1),F(3,2),F(2)]:
  for s in [F(1,2),F(1),F(2),F(10,3),F(10)]:
   # Verify support evaluation equals affine piece at a non-kink or by continuity.
   for q,kind in [(0,'q0'),(3,'q3')]:assert rate(q,s,l,z)==at(piece(kind,q,s,l,z),s,l,z)
   checks.append({'s':float(s),'loss':float(l),'span':float(z),'gap':float(gap(s,l,z))})
out={'scope':'Fixed-weight sufficient all-control exclusion; common ha/hb scaling, floor39/ceiling41 fixed; roots are certificate boundaries, not feasibility thresholds. Original96finite network only.','input_sha256':{k:hashlib.sha256(raw['network96/'+k]).hexdigest() for k in ['primitives.npz','problem.npz']},'weight_source_sha256':hashlib.sha256((REPO/'demos/mcm-2016-a/reproduce/reference/spatial-functional/potential-results.json').read_bytes()).hexdigest(),'weights':[encode(x) for x in w],'d':[encode(x) for x in d],'hh':encode(hh),'upper':[encode(x) for x in upper],'supports':{k:{'affine':[encode(x) for x in v['affine']],'residuals':[[encode(x) for x in r] for r in v['residuals']]} for k,v in supports.items()},'boundary_rows':rows,'exact_checks':checks,'baseline_gap':encode(gap(F(1),F(1),F(3,2))),'elapsed_s':time.monotonic()-start}
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists():raise FileExistsError('Preserve existing result')
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'elapsed_s':out['elapsed_s'],'rows':rows,'baseline_gap_float':float(gap(F(1),F(1),F(3,2)))},indent=2))
