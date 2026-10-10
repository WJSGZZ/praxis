from pathlib import Path
from fractions import Fraction as F
import json,itertools,argparse
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
ROOT=args.output;ROOT.mkdir(parents=True,exist_ok=False)
# Independent explicit vertices for0<=x,y<=2,|x-y|<=3/2.
vertices=[(F(0),F(0)),(F(3,2),F(0)),(F(2),F(1,2)),(F(2),F(2)),(F(1,2),F(2)),(F(0),F(3,2))]
rows=[]
for g,l in [(F(1,1000),F(1,5000)),(F(3,1000),F(1,5000)),(F(1,1000),F(0))]:
 # Uncontrolled remote node: y'=g(x-y)-l*(y+17).
 brute=max(g*(x-y)-l*(y+17) for x,y in vertices)
 analytic=F(3,2)*g-17*l;assert brute==analytic
 horizon=F(1)/(-analytic) if analytic<0 else None
 rows.append({'diffusion_s_inv':str(g),'loss_s_inv':str(l),'max_remote_flux':str(brute),'safe_time_bound_s':str(horizon) if horizon else None,'excludes1800s':analytic<0 and F(1)+1800*analytic<0})
# Every q endpoint dominates intermediate q; exact safe-state vertices and arbitrary signed weights.
checked=0
for w in [(F(1),F(0)),(F(0),F(1)),(F(1),F(-1)),(F(-1),F(1)),(F(2),F(3)),(F(-3),F(-2))]:
 for x,y in vertices:
  v0=w[0]*(y-x)+w[1]*(x-y-F(1,10));v3=v0+3*w[0]*(11-x)
  for q in [F(0),F(1,3),F(3,2),F(3)]:assert v0+q*w[0]*(11-x)<=max(v0,v3);checked+=1
assert rows[0]['excludes1800s'] and not rows[1]['excludes1800s'] and not rows[2]['excludes1800s']
(ROOT/'analytic-checks.json').write_text(json.dumps({'remote_flux_cases':rows,'exact_endpoint_examples':checked,'scope':'artificial two-node analytic special cases, not actual bath or PDE'},indent=2)+'\n')
print(rows,checked)
