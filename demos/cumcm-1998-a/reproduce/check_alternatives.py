"""Baselines, asset-by-asset substitution and an independent-risk reading, around each recommended knee portfolio."""
import csv,importlib.util,json
from pathlib import Path
import numpy as np
base=Path(__file__).resolve().parent;ref=base/'reference'
spec=importlib.util.spec_from_file_location('model',base/'code/model.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
rec=json.loads((ref/'recommendation.json').read_text());M=1e6
def load(name):
    return np.array([[float(d[k]) for k in ['return_pct','risk_pct','fee_pct','threshold_yuan']] for d in csv.DictReader((base/'data'/name).open())])
def net(data,x):
    r,q,p,u=data.T.copy();r/=100;p/=100
    fees=np.where(x>1e-7,p*np.maximum(x,u),0);return float((.05*(M-x.sum()-fees.sum())+r@x-fees.sum())/M)
def greedy(data,cap,key):
    # buy assets in order of key, each up to the cap-implied amount, while the budget (with fees) allows
    r,q,p,u=data.T.copy();r/=100;q/=100;p/=100
    x=np.zeros(len(r));left=M
    for i in np.argsort(-key(r,q,p)):
        if r[i]-p[i]<=.05*(1+p[i]):continue
        amt=min(cap*M/q[i],left/(1+p[i]))
        if amt>=u[i]:x[i]=amt;left-=amt*(1+p[i])
    return x
def equal_weight(data,cap):
    r,q,p,u=data.T.copy();r/=100;q/=100;p/=100
    ok=[i for i in range(len(r)) if r[i]-p[i]>.05*(1+p[i])]
    if not ok:return np.zeros(len(r))
    t=min(cap*M/max(q[i] for i in ok),M/(sum(1+p[i] for i in ok)))
    x=np.zeros(len(r));x[ok]=t;return x
def std_risk(data,cap):
    r,q,p,u=data.T.copy();r/=100;q/=100;p/=100;n=len(r);g=(r-p-.05*(1+p))
    # Cauchy-Schwarz gives the exact relaxed optimum when cash is slack and
    # every active purchase is above its fee threshold. Check those premises.
    v=np.maximum(g,0)/q;length=np.linalg.norm(v)
    z=np.zeros(n) if length==0 else cap*v/(q*length)
    x=z*M;active=x>1e-7
    fees=np.where(active,p*np.maximum(x,u),0)
    if (x[active]<u[active]).any() or x.sum()+fees.sum()>M+1e-6:
        raise ValueError('Analytic independent-risk allocation is outside its fee/budget regime')
    return x

out={'groups':{}}
for key,name in [('four','assets4.csv'),('fifteen','assets15.csv')]:
    data=load(name);g=rec['groups'][key];cap=g['knee_risk'];x0=np.array(g['investments_yuan']);q=data[:,1]/100
    caps=[cap/2,cap,2*cap];res={'cap':cap,'baselines':[]}
    for c in caps:
        opt=model.solve(data,M,c)['net_return']
        res['baselines'].append({'cap':c,'optimal':opt,'bank_only':.05,
            'greedy_return_over_risk':net(data,greedy(data,c,lambda r,q,p:(r-p)/np.maximum(q,1e-9))),
            'greedy_net_return':net(data,greedy(data,c,lambda r,q,p:r-p)),
            'greedy_eta':net(data,greedy(data,c,lambda r,q,p:(r-p)/(1+p))),
            'equal_weight_eligible':net(data,equal_weight(data,c))})
    chosen=[int(i) for i in np.flatnonzero(x0>1e-6)];nom=model.solve(data,M,cap)['net_return']
    res['drop_one']=[{'asset':i+1,'net_return_without':model.solve(np.delete(data,i,axis=0),M,cap)['net_return']} for i in chosen]
    z=std_risk(data,cap);res['independent_risk_reading']={'cap':cap,'net_return':net(data,z),
        'knee_plan_std_risk':float(np.sqrt(np.sum((q*x0)**2))/M),'std_plan_max_item_risk':float(np.max(q*z)/M),
        'overlap_assets':len(set(np.flatnonzero(z>1))&set(chosen)),'std_plan_assets':int((z>1).sum()),'knee_plan_assets':len(chosen)}
    # the other reading of "risk": every held asset must have loss rate q_i <= cap (a cap on a rate, not on an amount), swept on its own scale
    steps=[];last=None
    for c in sorted({0.005,*(q/1.0).tolist(),*((q+1e-6).tolist()),0.7}):
        sol=model.solve(data,M,float(c),interpretation='rate');held=[i+1 for i,v in enumerate(sol['investments_yuan']) if v>1e-6]
        k=(round(sol['net_return'],5),tuple(held))
        if k!=last:steps.append({'cap':float(c),'net_return':sol['net_return'],'held_assets':held});last=k
    res['rate_reading_frontier']=steps
    res['nominal']=nom;out['groups'][key]=res
(base/'reproduced').mkdir(exist_ok=True);(base/'reproduced/alternatives.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=1))
