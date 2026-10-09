"""Execution error, safety margin price and independent parameter errors around each recommended knee portfolio."""
import csv,importlib.util,json
from pathlib import Path
import numpy as np
base=Path(__file__).resolve().parent;ref=base/'reference'
spec=importlib.util.spec_from_file_location('model',base/'code/model.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
rec=json.loads((ref/'recommendation.json').read_text())
rng=np.random.default_rng(20261007);M=1e6;N=200
def load(name):
    return np.array([[float(d[k]) for k in ['return_pct','risk_pct','fee_pct','threshold_yuan']] for d in csv.DictReader((base/'data'/name).open())])
def net(data,x):
    r,q,p,u=data.T.copy();r/=100;p/=100
    fees=np.where(x>1e-7,p*np.maximum(x,u),0);return float((.05*(M-x.sum()-fees.sum())+r@x-fees.sum())/M)
def risk(data,x):return float(np.max(data[:,1]/100*x)/M)
def spent(data,x):
    r,q,p,u=data.T.copy();p/=100
    return float(x.sum()+np.where(x>1e-7,p*np.maximum(x,u),0).sum())
def within_budget(data,x):
    """A noisy execution cannot spend more than M: scale the purchases down (bisection, fees depend on the amounts) until it fits."""
    if spent(data,x)<=M*(1+1e-12):return x,False
    lo,hi=0.,1.
    for _ in range(80):
        mid=(lo+hi)/2
        if spent(data,x*mid)<=M:lo=mid
        else:hi=mid
    return x*lo,True
out={'seed':20261007,'draws':N,'groups':{}}
for key,name in [('four','assets4.csv'),('fifteen','assets15.csv')]:
    data=load(name);g=rec['groups'][key];cap=g['knee_risk'];x0=np.array(g['investments_yuan']);nom=model.solve(data,M,cap)
    res={'cap':cap,'nominal_net_return':nom['net_return'],'nominal_risk':risk(data,x0)}
    ex={}
    for e in (.05,.10):
        rs=[];nr=[];cut=0
        for _ in range(N):
            x,scaled=within_budget(data,x0*(1+rng.uniform(-e,e,len(x0))));cut+=scaled
            rs.append(risk(data,x)/cap-1);nr.append(net(data,x))
        rs=np.array(rs);ex[f'{e:.2f}']={'share_within_cap':float((rs<=1e-9).mean()),'median_overshoot':float(np.median(rs)),'p95_overshoot':float(np.quantile(rs,.95)),'median_net_return':float(np.median(nr)),'share_scaled_to_budget':cut/N}
    res['execution_error']=ex
    res['buffer_price']=[{'buffer':b,'cap':cap*(1-b),'net_return':model.solve(data,M,cap*(1-b))['net_return']} for b in (0,.05,.10)]
    dr=[];same=[];over=[];short=[];overspent=[];risk_scaled=[];budget_scaled=[];executed_spent=[];executed_risk=[]
    sel=set(np.flatnonzero(x0>1e-6))
    for _ in range(N):
        d=data*(1+rng.uniform(-.10,.10,data.shape));d[:,3]=data[:,3]
        s=model.solve(d,M,cap);dr.append(s['net_return'])
        same.append(set(np.flatnonzero(np.array(s['investments_yuan'])>1e-6))==sel)
        over.append(risk(d,x0)/cap-1);overspent.append(max(0.,spent(d,x0)-M))
        # Keep the original proportions, but do not compare an infeasible purchase.
        factor=min(1.,cap/risk(d,x0)) if risk(d,x0)>0 else 1.
        kept,scaled=within_budget(d,x0*factor)
        risk_scaled.append(factor<1.);budget_scaled.append(scaled)
        executed_spent.append(spent(d,kept));executed_risk.append(risk(d,kept))
        assert executed_spent[-1]<=M*(1+1e-12) and executed_risk[-1]<=cap+1e-12
        short.append(s['net_return']-net(d,kept))
    res['parameter_error_10pct']={'reoptimized_net_return':{'median':float(np.median(dr)),'p05':float(np.quantile(dr,.05)),'p95':float(np.quantile(dr,.95))},
        'share_same_assets':float(np.mean(same)),'kept_plan_risk_overshoot':{'median':float(np.median(over)),'p95':float(np.quantile(over,.95))},
        'kept_plan_return_shortfall':{'median':float(np.median(short)),'p95':float(np.quantile(short,.95))},
        'kept_plan_execution':{'rule':'Keep proportions; reduce to perturbed risk cap, then reduce to budget with actual minimum fees. Unadjusted risk overshoot is a diagnostic, not an executed plan.',
            'raw_over_budget_count':int(np.count_nonzero(np.array(overspent)>1e-6)),'raw_max_overspend_yuan':float(max(overspent)),
            'share_risk_reduced':float(np.mean(risk_scaled)),'share_budget_reduced_after_risk':float(np.mean(budget_scaled)),
            'maximum_spent_yuan':float(max(executed_spent)),'maximum_risk':float(max(executed_risk)),
            'minimum_return_shortfall':float(min(short))}}
    out['groups'][key]=res
(base/'reproduced').mkdir(exist_ok=True);(base/'reproduced/robustness.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=1))
