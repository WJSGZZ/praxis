"""Optional extension: time-varying control and literature-range analysis. About 5-10 minutes; writes reproduced/extended.json."""
from pathlib import Path
import json,sys
import numpy as np
from scipy.integrate import solve_ivp
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'code'))
import model,control,literature
p=model.BASE.copy();net=model.network(p);a=model.analytic(p,net)
constant=model.search(p,net);constant.pop('candidates',None)
frontier=[]
for floor in (37.0,37.5,38.0,38.5,39.0,39.25,39.5,39.75):
    pf={**p,'floor':floor};nf=model.network(pf);rf=model.search(pf,nf);af=model.analytic(pf,nf)
    frontier.append(dict(floor=floor,fall=p['initial']-floor,constant_l=float(rf['water_l']) if rf.get('feasible') else None,mixed_l=float(af['mixed_optimum_l']),bound_l=float(af['energy_lower_bound_l'])))
runs=[control.optimize(p,net,k) for k in (3,6,12)]
best=min((r for r in runs if r),key=lambda r:r['water_l'])
# Independent replay: separately assembled right-hand side, RK45, one-second samples, compared with the matrix-exponential result.
cap,ha,hb,g,adv=net['cap'],net['ha'],net['hb'],net['G'],net['adv']
def rhs(t,y,flow):return (g@y+ha*(p['air_temp']-y)+hb*(p['body_temp']-y)+flow*(adv@y+net['hot']))/cap
seg=best['segment_s'];y=np.full(len(cap),p['initial']);samples=[y[None,:]]
for q in best['flow_lpm']:
    sol=solve_ivp(lambda t,v:rhs(t,v,q/60000.),(0,seg),y,method='RK45',rtol=2e-9,atol=2e-10,t_eval=np.arange(1.,seg+.5,1.),max_step=5.)
    samples.append(sol.y.T);y=sol.y[:,-1]
Y=np.vstack(samples);ref=control.piecewise(p,net,best['flow_lpm'],1.)
independent=dict(min_temp=float(Y.min()),max_temp=float(Y.max()),max_span=float(np.ptp(Y,axis=1).max()),max_difference_c=float(np.abs(Y[:len(ref)]-ref).max()) if Y.shape==ref.shape else None,
                 water_l=float(sum(best['flow_lpm'])*seg/60))
checks=[dict(name='control_independent_RK45_replay',passed=bool(independent['min_temp']>=p['floor']-.002 and independent['max_temp']<=p['ceiling']+.002 and independent['max_span']<=p['span']+.002 and independent['max_difference_c'] is not None and independent['max_difference_c']<2e-6),evidence=independent),
        dict(name='control_respects_energy_lower_bound',passed=bool(best['water_l']>=a['energy_lower_bound_l']-1e-9),evidence=dict(water_l=best['water_l'],bound_l=a['energy_lower_bound_l']))]
out=dict(parameters=p,provenance=literature.provenance(),constant_rate=constant,frontier=frontier,analytic=a,control=dict(runs=runs,best=best,independent=independent),literature_ranges=control.literature_ranges(p),checks=checks)
(HERE/'reproduced').mkdir(exist_ok=True);(HERE/'reproduced/extended.json').write_text(json.dumps(out,indent=1))
print(json.dumps(dict(constant=constant['water_l'],control=[r and round(r['water_l'],3) for r in runs],checks=[c['passed'] for c in checks],feasible=out['literature_ranges']['feasible'],q=out['literature_ranges']['water_quantiles_l']),indent=1))
