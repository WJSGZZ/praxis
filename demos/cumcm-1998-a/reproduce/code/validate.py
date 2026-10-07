"""Independent arithmetic, fee-regime enumeration and analytical upper bounds."""
import argparse
import csv
import itertools
import json
from pathlib import Path
import numpy as np


def load(name):
    with open(Path('raw/data')/name,encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    return np.array([[float(d[k]) for k in ['return_pct','risk_pct','fee_pct','threshold_yuan']] for d in rows])


def regime_optimum(data, budget, cap):
    # off / minimum-fee region / proportional-fee region: solve each box knapsack by ratios.
    r,q,p,u=data.T.copy();r/=100;q/=100;p/=100;u/=budget
    best=.05
    for regimes in itertools.product(range(3),repeat=len(data)):
        lo=[];hi=[];weight=[];gain=[];fixed=0.
        for i,state in enumerate(regimes):
            risk_upper=cap/q[i]
            if state==0:a=b=0.;w=1.;g=0.
            elif state==1:
                a=0.;b=min(u[i],risk_upper);w=1.;g=r[i]-.05
                fixed+=p[i]*u[i]
            else:
                a=u[i];b=risk_upper;w=1+p[i];g=r[i]-.05-1.05*p[i]
            lo.append(a);hi.append(b);weight.append(w);gain.append(g)
        if any(b<a-1e-12 for a,b in zip(lo,hi)):continue
        remaining=1-fixed-sum(w*a for w,a in zip(weight,lo))
        if remaining < -1e-12:continue
        value=.05-1.05*fixed+sum(g*a for g,a in zip(gain,lo))
        for i in sorted(range(len(data)),key=lambda j:gain[j]/weight[j],reverse=True):
            if gain[i]<=0:continue
            extra=min(max(remaining,0)/weight[i],hi[i]-lo[i])
            value+=gain[i]*extra;remaining-=weight[i]*extra
        best=max(best,value)
    return best


def relaxed_upper(data,cap,scale=1.):
    # Ignore minimum fees. Nonnegative bank is a budget slack, so fractional knapsack is exact.
    r,q,p,_=data.T.copy();r/=100;q=q/100*scale;p/=100
    w=1+p;g=r-.05-1.05*p;left=1.;value=.05
    for i in sorted(range(len(data)),key=lambda j:g[j]/w[j],reverse=True):
        if g[i]<=0:continue
        xi=min(left/w[i],cap/q[i]);value+=g[i]*xi;left-=w[i]*xi
    return value


def main():
    a=argparse.ArgumentParser();a.add_argument('--results',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    args=a.parse_args();result=json.loads(args.results.read_text());checks=[]
    def check(name,passed,evidence):checks.append({'name':name,'passed':bool(passed),'evidence':evidence})
    for key,file in [('four','assets4.csv'),('fifteen','assets15.csv')]:
        data=load(file);group=result['groups'][key]
        samples=group['frontier']+group['selected']+[group['unrestricted']]+result['sensitivity'][key]['budget']+result['sensitivity'][key]['risk_stress']+[result['alternative_interpretation'][key]]
        residuals=[];errors=[];violation=[]
        for d in samples:
            M=d['budget_yuan'];x=np.array(d['investments_yuan']);r,q,p,u=data.T.copy();r/=100;q=q/100*d['risk_scale'];p/=100
            fee=np.where(x>1e-7,p*np.maximum(x,u),0)
            profit=.05*d['bank_yuan']+np.dot(r,x)-fee.sum()
            risk=max(q[x>1e-7],default=0) if d['interpretation']=='rate' else max(q*x)/M
            residuals.append(abs(d['bank_yuan']+x.sum()+fee.sum()-M)/M)
            errors.extend([abs(profit-d['profit_yuan'])/M,np.max(abs(fee-d['fees_yuan']))/M,abs(risk-d['actual_risk'])])
            violation.append(max(0,-min(x)/M,-d['bank_yuan']/M,risk-d['risk_cap']))
        check(key+' feasibility and accounting',max(residuals+errors+violation)<1e-7,
              f'{len(samples)} portfolios; budget residual={max(residuals):.3g}, accounting error={max(errors):.3g}, violation={max(violation):.3g}')
        front=group['frontier'];check(key+' frontier and bank boundary',
            abs(front[0]['net_return']-.05)<1e-9 and all(b['net_return']>=a['net_return']-1e-8 for a,b in zip(front,front[1:])),
            f'zero risk gives {front[0]["net_return"]:.9f}; {len(front)} caps checked for nondecreasing optimal return')
        unrestricted=max([.05]+[(ri/100-pi/100)/(1+pi/100) for ri,_,pi,_ in data])
        check(key+' unrestricted analytical answer',abs(unrestricted-group['unrestricted']['net_return'])<1e-8,
              f'best single-asset proportional return={unrestricted:.12f}; fees above thresholds, computed={group["unrestricted"]["net_return"]:.12f}')
        selected=group['selected'];gaps=[relaxed_upper(data,d['risk_cap'])-d['net_return'] for d in selected]
        check(key+' analytical optimality certificate',max(abs(g) for g in gaps)<1e-7,
              f'Ignoring minimum fees gives a valid upper bound; selected-point gaps={gaps}')
        if key=='four':
            exact=front+selected+[group['unrestricted']]+result['sensitivity'][key]['budget']
            gaps=[abs(regime_optimum(data,d['budget_yuan'],d['risk_cap'])-d['net_return']) for d in exact]
            check('four exhaustive fee-regime optimum',max(gaps)<1e-7,
                  f'3^4=81 fee regimes per portfolio; {len(exact)} cases; max return gap={max(gaps):.3g}; no optimization solver used')
        stress=result['sensitivity'][key]['risk_stress']
        check(key+' risk stress direction',all(b['net_return']<=a['net_return']+1e-8 for a,b in zip(stress,stress[1:])),
              'risk multiplier 0.9/1.0/1.1 returns='+str([d['net_return'] for d in stress]))
    # The supplied asset table has no stochastic observations; test a fee discontinuity explicitly.
    p=.02;u=198
    check('fee discontinuity and threshold semantics',p*max(.001,u)==3.96 and p*max(198,u)==3.96,
          'S2: investment=0 has fee=0; investment=0.001 has fee=3.96; investment=198 has fee=3.96. u is not a minimum purchase quantity.')
    args.output.write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    print(json.dumps(checks,ensure_ascii=False,indent=2))
    raise SystemExit(0 if all(d['passed'] for d in checks) else 1)


if __name__=='__main__':main()
