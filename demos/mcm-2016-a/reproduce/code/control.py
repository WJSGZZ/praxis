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

def margins(p,net,Y,buffer=0.):
    """Constraint slack with the numerical reserve; `buffer` adds a further safety distance to all three limits.
    The floor holds in every cell; the ceiling and the spread hold outside the inlet jet zone."""
    V=model.view(net,Y)
    return np.r_[Y.min(1)-(p['floor']+RESERVE+buffer),p['ceiling']-buffer-V.max(1),p['span']-buffer-np.ptp(V,axis=1)]

def optimize(p,net,segments,starts=None,dt=5.,bound=3.,buffer=0.):
    """Multi-start SLSQP over piecewise-constant flow. Local optimum of a non-convex problem: no global claim."""
    K=segments;seg=p['horizon']/K
    starts=starts or [np.full(K,.7),np.linspace(1.4,.1,K),np.linspace(.1,1.4,K),np.r_[np.zeros(K//3),np.full(K-2*(K//3),1.2),np.zeros(K//3)]]
    best=None
    for x0 in starts:
        r=minimize(lambda x:float(np.sum(x)*seg/60),x0,method='SLSQP',bounds=[(0,bound)]*K,
                   constraints=[{'type':'ineq','fun':lambda x:margins(p,net,piecewise(p,net,x,dt),buffer)}],options={'maxiter':300,'ftol':1e-9})
        Y=piecewise(p,net,r.x,5.);m=margins(p,net,Y,buffer).min()
        if m>=-1e-6 and (best is None or r.fun<best['water_l']):
            best=dict(segments=K,segment_s=seg,flow_lpm=[float(v) for v in r.x],water_l=float(r.fun),min_margin_c=float(m),min_temp=float(Y.min()),max_temp=float(model.view(net,Y).max()),max_span=float(np.ptp(model.view(net,Y),axis=1).max()))
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


def _physical_slack(p,net,Y):
    """Distance to the stated limits themselves (no reserve): the quantity a user actually experiences."""
    V=model.view(net,Y)
    return float(min(Y.min()-p['floor'],p['ceiling']-V.max(),p['span']-np.ptp(V,axis=1).max()))

def execution_tolerance(p,net,flows,draws=200,seed=11):
    """How wrong may the tap be before a limit is crossed? Uniform scale error, random per-segment error, and the most critical segment."""
    flows=np.asarray(flows,float);rng=np.random.default_rng(seed)
    slack=lambda f:_physical_slack(p,net,piecewise(p,net,np.clip(f,0,None),5.))
    nominal=slack(flows)
    scales={f"{k:.2f}":slack(flows*k) for k in (.8,.9,1.,1.1,1.2)}
    def edge(lo,hi):  # bisection on the scale factor where slack changes sign; None when the sign does not change on the bracket
        a,b=slack(flows*lo),slack(flows*hi)
        if a*b>0:return None
        for _ in range(20):
            mid=(lo+hi)/2
            if slack(flows*mid)*a>0:lo=mid
            else:hi=mid
        return (lo+hi)/2
    scale_low=edge(.5,1.) if nominal>=0 else None;scale_high=edge(1.,1.6) if nominal>=0 else None
    random={}
    for sigma in (.1,.2):
        ok=0;worst=[]
        for _ in range(draws):
            sl=slack(flows*np.clip(rng.normal(1.,sigma,len(flows)),0,None));ok+=sl>=-1e-9;worst.append(sl)
        random[f"{sigma:.2f}"]=dict(share_within_limits=ok/draws,median_slack_c=float(np.median(worst)),p05_slack_c=float(np.quantile(worst,.05)))
    critical=[]
    for i in range(len(flows)):
        if flows[i]<=1e-9:continue
        lo=flows.copy();lo[i]*=.8;hi=flows.copy();hi[i]*=1.2
        critical.append(dict(segment=i,slack_minus20=slack(lo),slack_plus20=slack(hi)))
    return dict(nominal_slack_c=nominal,uniform_scale_slack_c=scales,scale_low_edge=scale_low,scale_high_edge=scale_high,random_error=random,segments=critical)
