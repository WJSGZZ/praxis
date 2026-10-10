"""Conservative rational root brackets, distinct from physical feasibility."""
from pathlib import Path
from fractions import Fraction as F
import json,time,hashlib
R=Path(__file__).resolve().parent;v=json.loads((R/'boundary.json').read_text());f=lambda p:F(*map(int,p))
w=list(map(f,v['weights']));d=list(map(f,v['d']));hh=f(v['hh']);sup={k:(list(map(f,x['affine'])),[list(map(f,r)) for r in x['residuals']]) for k,x in v['supports'].items()}
def lower(k,p):a,rr=sup[k];return sum(x*y for x,y in zip(a,p))+sum(min(F(0),sum(x*y for x,y in zip(r,p))) for r in rr)
def gap(l,z):
 p=[F(1),F(1),l,z];base=sum(x*y for x,y in zip(d,p));return lower('end',p)-sum(w)-1800*max(-lower('q0',p)+base,-lower('q3',p)+base+3*hh)
def bracket(a,b,fn):
 va,vb=fn(a),fn(b);assert va*vb<0
 for _ in range(50):
  mid=(a+b)/2;vm=fn(mid)
  if vm*va>0:a,va=mid,vm
  else:b,vb=mid,vm
 return {'lower':str(a),'upper':str(b),'lower_float':float(a),'upper_float':float(b),'lower_gap':float(va),'upper_gap':float(vb)}
s=time.monotonic();loss=bracket(F(4,5),F(1),lambda l:gap(l,F(3,2)));span=bracket(F(3,2),F(2),lambda z:gap(F(1),z))
assert gap(F(99,100),F(3,2))>0
out={'scope':'At original D=.0003; frozen certificate root brackets only, not feasibility thresholds. Common air/body loss scale, fixed39/41 bounds.','loss_root':loss,'span_root_c':span,'conservative_examples':{'loss_scale_at_least':.99,'span_c_at_most':1.5,'scope':'Separate examples at otherwise baseline parameters; no joint rectangle guarantee stated'},'seconds':time.monotonic()-s,'source_sha256':hashlib.sha256((R/'boundary.json').read_bytes()).hexdigest()};import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists():raise FileExistsError('Preserve existing result')
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n');print({k:out[k] for k in ['loss_root','span_root_c','seconds']})
