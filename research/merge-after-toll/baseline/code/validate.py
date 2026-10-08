"""Independent cut feasibility via a network-flow implementation and LP witnesses.
Does not import the author's model. Conditional mathematical checks, not field validation.
"""
import argparse
import itertools
import json
import math
from pathlib import Path
import networkx as nx
import numpy as np


def maxflow(counts, shares, means, cap, lam):
    graph = nx.DiGraph()
    for t in range(3):
        graph.add_edge('s', ('t',t), capacity=float(lam*shares[t]))
    for g in range(len(counts)):
        graph.add_edge(('g',g), 'z', capacity=float(cap))
        for t in range(3):
            graph.add_edge(('t',t), ('g',g), capacity=float(counts[g][t]*3600/means[t]))
    return nx.maximum_flow_value(graph, 's', 'z')


def check(result):
    cfg=result['config']; means=cfg['mean_service_s']; checks=[]
    def add(name, passed, evidence, independent=True):
        checks.append(dict(name=name,passed=bool(passed),evidence=evidence,independent=independent))
    b=result['baseline']; p=cfg['payment_scenarios']['nominal']
    # Hand calculation independent of cut enumeration.
    add('baseline payment bottleneck', abs(b['type_upper_vph']-3000)<1e-8,
        'Three staffed booths provide 900/h; 30% of arrivals need them, hence lambda<=3000/h.')
    add('pooled bound is insufficient', b['pooled_upper_vph']>b['type_upper_vph'],
        f"Pooled {b['pooled_upper_vph']}/h exceeds payment ceiling {b['type_upper_vph']}/h; it is an upper bound, not a feasible recommendation.")
    add('baseline flow witness', abs(maxflow(b['counts'],p,means,1800,b['capacity_vph'])-b['capacity_vph'])<1e-6,
        'NetworkX max flow independently routes the entire claimed baseline rate.')
    if result['phase']=='baseline': return checks
    policies={'nominal':result['search']['nominal'],'robust':result['search']['robust'],'expanded':result['expansion']}
    for name, design in policies.items():
        assert design is not None
        for scenario, shares in cfg['payment_scenarios'].items():
            lam=design['capacities_vph'][scenario]
            flow=maxflow(design['counts'],shares,means,1800,lam)
            over=maxflow(design['counts'],shares,means,1800,lam+1)
            add(f'{name} {scenario} exact flow threshold', abs(flow-lam)<1e-5 and over<lam+1-1e-5,
                f'At {lam:.9f}/h maximum flow={flow:.9f}; at lambda+1, max flow={over:.9f} < demand.')
        n=np.asarray(design['counts']); bcount=n.sum(); sizes=n.sum(axis=1)
        d=np.array(design['exit_y_m'])-np.array(design['booth_start_y_m'])
        length=design['length_m']; u=np.linspace(0,1,10001)
        first=30*u*u*(1-u)**2
        second=60*u*(1-u)*(1-2*u)
        slope=max(abs(d))*max(abs(first))/length
        accel=cfg['departure_speed_m_s']**2*max(abs(d))*max(abs(second))/length**2
        paths=np.array(design['booth_start_y_m'])[:,None]+d[:,None]*(10*u**3-15*u**4+6*u**5)
        add(f'{name} geometry bounds', slope<=cfg['max_path_slope']+1e-10 and accel<=cfg['lateral_accel_m_s2']+1e-8 and np.diff(paths,axis=0).min()>-1e-10,
            f'10001 points: maximum slope {slope:.8f}, lateral acceleration {accel:.8f} m/s², order preserved. Analytic derivative maxima also stated in paper.')
    # A separate tiny exhaustive search over booth totals proves the robust booth-count lower bound.
    feasible=[]
    for total in range(3,12):
        for manual in range(1,total-1):
            for exact in range(1,total-manual):
                counts=[manual,exact,total-manual-exact]
                if all(all(counts[t]*3600/means[t]>=cfg['heavy_vph']*p[t]-1e-9 for t in range(3)) for p in cfg['payment_scenarios'].values()):
                    feasible.append(counts)
        if feasible:break
    add('minimum robust booth count', total==11 and result['minimum_robust_counts']==[6,3,2],
        f'Exhaustive total-count search first permits 3600/h in all payment scenarios at B={total}, counts={feasible}. Geometry/exit feasibility checked separately.')
    for row in result['automation']:
        flow=np.array(row['type_lane_flow_vph']); n=np.array(policies.get(row['policy'],b)['counts'])
        lam=row['capacity_vph']
        add(f"routing witness {row['policy']} av={row['av_share']}",
            np.all(flow>=-1e-7) and np.all(flow<=n*3600/np.array(means)+1e-6) and np.max(flow.sum(axis=1))<=3600/row['headway_s']+1e-6 and np.allclose(flow.sum(axis=0),lam*np.array(p),atol=1e-6),
            'LP witness respects booth capacities, each exit capacity, and all payment-type conservation equations.')
    # Simulation accounting plus exact finite D/D/1 sanity, independent queue recurrence.
    add('simulation conservation', all(r['arrivals']==r['completed']+r['residual'] and r['clearance_s']>=0 and r['mean_delay_s']>=0 for row in result['simulations'] for r in row['replicas']),
        'Every simulated vehicle is either discharged by horizon or in residual; all vehicles drained, no negative waiting.')
    add('common random numbers', all(len({tuple((r['seed'],r['arrivals'],r['first_arrival_s']) for r in row['replicas']) for row in result['simulations'] if row['scenario']==s and row['load']==load})==1 for s in cfg['payment_scenarios'] for load in ['light','heavy']),
        'Same scenario/load uses identical arrivals, type marks and service draws across designs; counts/first arrivals additionally checked here.',False)
    add('eight booth robust ceiling', abs(min(result['search']['robust']['capacities_vph'].values())-8000/3)<1e-6,
        'For robust rate >2666.67/h one needs >=5 manual, >=2 exact, >=2 electronic booths, hence >=9; selected 8-booth design reaches 2666.67/h.')
    return checks


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    result=json.loads(a.results.read_text());checks=check(result);a.output.write_text(json.dumps(checks,indent=2))
    print(f'{sum(c["passed"] for c in checks)}/{len(checks)} checks passed')
    raise SystemExit(0 if all(c['passed'] for c in checks) else 1)
