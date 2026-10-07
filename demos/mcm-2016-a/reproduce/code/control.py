"""Time-varying replenishment and literature-range analysis for the spatial model (extension of model.py)."""
import numpy as np
from scipy.optimize import minimize
from scipy.stats import qmc, spearmanr
import model

RESERVE=.03  # same numerical reserve as the constant-rate candidate search

def piecewise(p,net,flows_lpm,dt=5.):
    """Cell temperatures for equal-length constant segments (L/min); exact matrix-exponential propagation."""
    seg=p['horizon']/len(flows_lpm);y=np.full(len(net['cap']),p['initial']);out=[y[None,:]]
    for q in flows_lpm:
        _,yy=model.evolve(p,net,q/60000.,y,seg,dt);out.append(yy[1:]);y=yy[-1]
    return np.vstack(out)

def margins(p,Y):
    return np.r_[Y.min(1)-(p['floor']+RESERVE),p['ceiling']-Y.max(1),p['span']-np.ptp(Y,axis=1)]

def optimize(p,net,segments,starts=None,dt=15.,bound=3.):
    """Multi-start SLSQP over piecewise-constant flow. Local optimum of a non-convex problem: no global claim."""
    K=segments;seg=p['horizon']/K
    starts=starts or [np.full(K,.7),np.linspace(1.4,.1,K),np.linspace(.1,1.4,K),np.r_[np.zeros(K//3),np.full(K-2*(K//3),1.2),np.zeros(K//3)]]
    best=None
    for x0 in starts:
        r=minimize(lambda x:float(np.sum(x)*seg/60),x0,method='SLSQP',bounds=[(0,bound)]*K,
                   constraints=[{'type':'ineq','fun':lambda x:margins(p,piecewise(p,net,x,dt))}],options={'maxiter':300,'ftol':1e-9})
        Y=piecewise(p,net,r.x,5.);m=margins(p,Y).min()
        if m>=-1e-6 and (best is None or r.fun<best['water_l']):
            best=dict(segments=K,segment_s=seg,flow_lpm=[float(v) for v in r.x],water_l=float(r.fun),min_margin_c=float(m),min_temp=float(Y.min()),max_temp=float(Y.max()),max_span=float(np.ptp(Y,axis=1).max()))
    return best

RANGES=dict(h_surface=(17.,37.),h_wall=(4.5,8.5),h_body=(12.,40.),D=(3e-4,3e-3),air_temp=(20.,26.),body_temp=(32.,36.))
def literature_ranges(base,samples=64,seed=7):
    """Scrambled-Sobol draws over the stated ranges (D log-uniform); constant-rate delayed-start search for each."""
    names=list(RANGES);u=qmc.Sobol(len(names),scramble=True,seed=seed).random(samples);rows=[]
    for point in u:
        changes={}
        for value,name in zip(point,names):
            lo,hi=RANGES[name];changes[name]=float(np.exp(np.log(lo)+value*(np.log(hi)-np.log(lo)))) if name=='D' else float(lo+value*(hi-lo))
        pp={**base,**changes};s=model.search(pp,model.network(pp))
        rows.append(dict(inputs=changes,feasible=bool(s['feasible']),water_l=s.get('water_l'),flow_lpm=s.get('flow_lpm'),delay_s=s.get('delay_s')))
    ok=[r for r in rows if r['feasible']];water=np.array([r['water_l'] for r in ok])
    corr={n:float(spearmanr([r['inputs'][n] for r in ok],water)[0]) for n in names} if len(ok)>5 else {}
    return dict(ranges=RANGES,samples=samples,feasible=len(ok),water_quantiles_l={q:float(np.quantile(water,q)) for q in (.05,.25,.5,.75,.95)} if len(ok) else {},spearman_with_water=corr,rows=rows)
