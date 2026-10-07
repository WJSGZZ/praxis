"""Original solution to a historical CUMCM problem; parameters are demo scenarios."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load(name):
    rows=list(csv.DictReader(open(Path('raw/data')/name,encoding='utf-8')))
    return rows, np.array([[float(d[k]) for k in ['return_pct','risk_pct','fee_pct','threshold_yuan']] for d in rows])


def solve(data, budget, cap, risk_scale=1.0, interpretation='amount'):
    n=len(data);r,q,p,u=data.T.copy();r/=100;q=q/100*risk_scale;p/=100;u/=budget
    # v = [bank, investments, fees, activation binaries], all money scaled by budget.
    size=1+3*n;ix=np.arange(1,1+n);jf=ix+n;ky=jf+n
    c=np.r_[-.05,-r,np.ones(n),np.zeros(n)]
    upper=np.r_[1,np.ones(n),p*np.maximum(1,u),np.ones(n)]
    if interpretation=='rate':
        upper[ix[q>cap+1e-12]]=0
    rows=[];lb=[];ub=[]
    a=np.zeros(size);a[0]=1;a[ix]=1;a[jf]=1
    rows.append(a);lb.append(1);ub.append(1)
    for i in range(n):
        for coeffs,hi in [({int(ix[i]):p[i],int(jf[i]):-1},0),
                          ({int(ky[i]):p[i]*u[i],int(jf[i]):-1},0),
                          ({int(ix[i]):1,int(ky[i]):-1},0),
                          ({int(jf[i]):1,int(ky[i]):-upper[jf[i]]},0)]:
            a=np.zeros(size)
            for j,value in coeffs.items():a[j]=value
            rows.append(a);lb.append(-np.inf);ub.append(hi)
        if interpretation=='amount':
            a=np.zeros(size);a[ix[i]]=q[i]
            rows.append(a);lb.append(-np.inf);ub.append(cap)
    res=milp(c,integrality=np.r_[np.zeros(1+2*n),np.ones(n)],
             bounds=Bounds(np.zeros(size),upper),
             constraints=LinearConstraint(np.array(rows),np.array(lb),np.array(ub)),
             options={'mip_rel_gap':1e-9,'time_limit':20})
    if not res.success:raise RuntimeError(res.message)
    active=res.x[ky]>.5  # the solver's binaries decide which assets are bought; a residual x on an inactive asset is rounding noise
    x=np.where(active,np.maximum(res.x[ix],0),0)*budget
    fees=np.where(active,p*np.maximum(x,data[:,3]),0)
    bank=budget-x.sum()-fees.sum()
    if bank<0:
        assert bank>-1e-6*budget,'budget exceeded beyond solver tolerance'
        bank=0.0
    profit=.05*bank+np.dot(r,x)-fees.sum()
    risk=float(np.max(q*x)/budget) if interpretation=='amount' else float(max(q[x>1e-7],default=0))
    return {'budget_yuan':budget,'risk_cap':float(cap),'risk_scale':risk_scale,
            'interpretation':interpretation,'investments_yuan':x.tolist(),
            'fees_yuan':fees.tolist(),'bank_yuan':float(bank),
            'profit_yuan':float(profit),'net_return':float(profit/budget),
            'actual_risk':risk,'mip_gap':float(res.mip_gap),
            'solver_message':res.message}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output
    results={'historical_demo':True,'bank_rate':.05,'primary_budget_yuan':1e6,
             'risk_definition':'max_i(q_i*x_i)/M; x_i is purchased principal; fees paid from M',
             'groups':{},'sensitivity':{},'alternative_interpretation':{}}
    for key,name,end,caps in [('four','assets4.csv',.03,[.005,.01,.02]),
                              ('fifteen','assets15.csv',.6,[.05,.1,.2])]:
        rows,data=load(name)
        frontier=[solve(data,1e6,cap) for cap in np.linspace(0,end,61)]
        selected=[solve(data,1e6,cap) for cap in caps]
        results['groups'][key]={'assets':rows,'frontier':frontier,'selected':selected,
            'unrestricted':solve(data,1e6,1.0)}
        results['sensitivity'][key]={'budget':[solve(data,m,caps[1]) for m in [100,1000,10000,1e6]],
            'risk_stress':[solve(data,1e6,caps[1],scale) for scale in [.9,1,1.1]]}
        results['alternative_interpretation'][key]=solve(data,1e6,caps[1],interpretation='rate')
        with open(out/f'{key}-frontier.csv','w',newline='') as f:
            w=csv.writer(f);w.writerow(['risk_cap','actual_risk','net_return','profit_yuan','bank_yuan'])
            w.writerows([d[k] for k in ['risk_cap','actual_risk','net_return','profit_yuan','bank_yuan']] for d in frontier)
        fig,ax=plt.subplots(figsize=(6.8,3.8))
        ax.plot([100*d['risk_cap'] for d in frontier],[100*d['net_return'] for d in frontier],color='#245B61',lw=2)
        ax.scatter([100*d['actual_risk'] for d in selected],[100*d['net_return'] for d in selected],color='#BA6238',zorder=3)
        ax.set(xlabel='Risk cap (% of initial budget)',ylabel='Net return (%)',title=f'{len(rows)} assets | budget = 1,000,000 yuan')
        ax.grid(alpha=.2);fig.tight_layout();fig.savefig(out/f'{key}-frontier.png',dpi=180);plt.close(fig)
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':main()
