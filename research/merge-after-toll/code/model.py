"""Conditional toll-plaza design, MCM 2017 B. No empirical calibration claimed.

All scenario values are in config.json. Exact cut enumeration selects a layout;
LP only constructs its routing witness. A separate event model checks queues.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import itertools
import json
import math
from pathlib import Path
import time
import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent


def compositions(total, parts):
    if parts == 1:
        yield (total,)
    else:
        for first in range(total + 1):
            for rest in compositions(total - first, parts - 1):
                yield (first,) + rest


def headway(av, cfg):
    # Only adjacent AV-AV pairs enjoy the shorter headway in this scenario.
    return cfg['human_headway_s'] * (1-av*av) + cfg['av_pair_headway_s'] * av*av


def capacity(counts, shares, service_s, lane_cap):
    """Exact feasible fluid arrival-rate threshold under within-type routing.

    For every nonempty subset S of payment types, demand lambda*p(S) must
    cross type-to-lane booth capacities or lane discharge arcs. Enumerate
    the 2^T-1 reduced cuts; equality is a feasible max-flow threshold.
    """
    counts = np.asarray(counts, float)
    mu = 3600 / np.asarray(service_s)
    p = np.asarray(shares)
    bounds = []
    for mask in range(1, 1 << len(p)):
        take = np.array([(mask >> t) & 1 for t in range(len(p))], bool)
        if p[take].sum() == 0:
            continue
        cut = np.minimum(lane_cap, (counts[:, take] * mu[take]).sum(axis=1)).sum()
        bounds.append((float(cut / p[take].sum()), mask))
    bound, active = min(bounds)
    return bound, active


def geometry(counts, cfg):
    counts = np.asarray(counts, int)
    sizes = counts.sum(axis=1)
    b, lanes = int(sizes.sum()), len(sizes)
    w = cfg['lane_width_m']
    pitch = cfg['booth_pitch_m']
    start = (np.arange(b) - (b-1)/2)*pitch
    ends = np.repeat((np.arange(lanes)-(lanes-1)/2)*w, sizes)
    displacement = ends - start
    d = float(np.max(np.abs(displacement)))
    # f=10u^3-15u^4+6u^5, max f'=15/8, max |f''|=10sqrt(3)/3.
    length = max(1.875*d/cfg['max_path_slope'],
                 cfg['departure_speed_m_s']*math.sqrt((10*math.sqrt(3)/3)*d/cfg['lateral_accel_m_s2']))
    # FHWA 2006 conventional departure-taper recommendation, <=40 mph.
    # A screening constraint; not a complete or current engineering standard.
    speed_mph = cfg['departure_speed_m_s']/0.44704
    if speed_mph > 40:
        raise ValueError('The adopted historical taper formula applies only at <=40 mph')
    edge_offset = (b*pitch-lanes*w)/2
    guidance_length = edge_offset*(1.5*speed_mph**2/105+5)
    length = max(length,guidance_length)
    length = math.ceil(length / 5)*5.0
    recovery = cfg['recovery_length_m']
    if recovery < cfg['departure_speed_m_s']**2/(2*cfg['cash_acceleration_m_s2']):
        raise ValueError('Recovery area too short for assumed acceleration from rest')
    area = recovery*b*pitch+length*(b*pitch+lanes*w)/2
    equipment = float(np.asarray(cfg['equipment_cost_usd']) @ counts.sum(axis=0))
    capital = area*cfg['road_cost_usd_m2'] + equipment
    return dict(length_m=length+recovery, taper_length_m=length,
                recovery_length_m=recovery, guidance_taper_min_m=guidance_length,
                area_m2=area, max_displacement_m=d,
                capital_usd=capital, booth_start_y_m=start.tolist(),
                exit_y_m=ends.tolist(), group_sizes=sizes.tolist())


def routing(counts, shares, cfg, av=0):
    counts = np.asarray(counts, int)
    cap = 3600/headway(av, cfg)
    throughput, active = capacity(counts, shares, cfg['mean_service_s'], cap)
    n, t = counts.shape
    aeq = np.zeros((t, n*t))
    for k in range(t):
        aeq[k, k::t] = 1
    aub = np.kron(np.eye(n), np.ones((1, t)))
    lp = linprog(np.zeros(n*t), A_ub=aub, b_ub=np.repeat(cap, n),
                 A_eq=aeq, b_eq=throughput*np.asarray(shares),
                 bounds=list(zip(np.zeros(n*t), (counts*3600/np.asarray(cfg['mean_service_s'])).ravel())),
                 method='highs')
    if not lp.success:
        raise RuntimeError(lp.message)
    return dict(capacity_vph=throughput, active_type_mask=active,
                type_lane_flow_vph=lp.x.reshape(n, t).tolist())


def operating_routing(counts, shares, cfg, rate, av=0, slots=None, design=None):
    """Minimize maximum resource load for the actual demand, not a max-flow witness.

    z>1 explicitly describes overload; the returned demands are route proportions,
    not a feasible service-rate certificate. Finite travel-occupancy is a necessary
    resource condition, not a sufficient stochastic delay/safety guarantee.
    """
    counts=np.asarray(counts,int); n,t=counts.shape
    dims=n*t+1; aeq=np.zeros((t,dims))
    for k in range(t):aeq[k,k:n*t:t]=1
    rows=[]
    for g in range(n):
        for k in range(t):
            row=np.zeros(dims);row[g*t+k]=1;row[-1]=-counts[g,k]*3600/cfg['mean_service_s'][k];rows.append(row)
        row=np.zeros(dims);row[g*t:g*t+t]=1;row[-1]=-3600/headway(av,cfg);rows.append(row)
    if slots is not None:
        travel=np.repeat(design['length_m']/cfg['departure_speed_m_s'],3)
        travel[:2]+=cfg['departure_speed_m_s']/(2*cfg['cash_acceleration_m_s2'])
        for g in range(n):
            row=np.zeros(dims);row[g*t:g*t+t]=travel;row[-1]=-slots*3600;rows.append(row)
    objective=np.zeros(dims);objective[-1]=1
    fit=linprog(objective,A_ub=rows,b_ub=np.zeros(len(rows)),A_eq=aeq,b_eq=rate*np.asarray(shares),bounds=[(0,None)]*dims,method='highs')
    if not fit.success:raise RuntimeError(fit.message)
    return dict(type_lane_flow_vph=fit.x[:-1].reshape(n,t).tolist(),maximum_resource_load=float(fit.x[-1]),
                rate_vph=rate,occupancy_condition='necessary only; excludes queueing time' if slots else None)


def minimum_slots(design, shares, cfg, rate):
    """Little's-law lower bound: occupancy includes at least free traversal time.

    Minimize a uniform per-group slot requirement over all feasible fluid routes.
    Queuing adds occupancy, so this is necessary, never a sufficient buffer size.
    """
    n=np.asarray(design['counts']);g,t=n.shape;dims=g*t+1
    travel=np.repeat(design['length_m']/cfg['departure_speed_m_s'],3)
    travel[:2]+=cfg['departure_speed_m_s']/(2*cfg['cash_acceleration_m_s2'])
    aeq=np.zeros((t,dims));aub=[];bub=[]
    for k in range(t):aeq[k,k:g*t:t]=1
    for j in range(g):
        lane=np.zeros(dims);lane[j*t:j*t+t]=1;aub.append(lane);bub.append(3600/headway(0,cfg))
        occ=np.zeros(dims);occ[j*t:j*t+t]=travel;occ[-1]=-3600;aub.append(occ);bub.append(0)
    bounds=list(zip(np.zeros(g*t),(n*3600/np.array(cfg['mean_service_s'])).ravel()))+[(0,None)]
    c=np.zeros(dims);c[-1]=1
    fit=linprog(c,A_ub=aub,b_ub=bub,A_eq=aeq,b_eq=rate*np.array(shares),bounds=bounds,method='highs')
    return dict(continuous_lower_bound=float(fit.x[-1]),rounded_necessary_slots=math.ceil(fit.x[-1]-1e-10),
                flow_vph=fit.x[:-1].reshape(g,t).tolist(),scope='necessary steady-flow traversal occupancy; excludes waiting') if fit.success else dict(continuous_lower_bound=None,solver_status=int(fit.status),reason=('Requested payment demand is infeasible even with unlimited occupancy' if fit.status==2 else 'Occupancy solver failed; infeasibility not established'))


def designs(cfg, fixed_counts=None):
    if cfg.get('cluster_payment_types'):
        # ETC left, exact in the middle, staffed right: payment types clustered
        # before contiguous exit partitions, consistent with historical guidance.
        totals=[fixed_counts] if fixed_counts is not None else [x for x in compositions(cfg['booths'],3) if min(x)>0]
        for ntypes in totals:
            sequence=[2]*ntypes[2]+[1]*ntypes[1]+[0]*ntypes[0]
            for cuts in itertools.combinations(range(1,len(sequence)),cfg['lanes']-1):
                bounds=(0,)+cuts+(len(sequence),)
                counts=np.array([[sequence[bounds[g]:bounds[g+1]].count(t) for t in range(3)] for g in range(cfg['lanes'])])
                yield counts
        return
    if fixed_counts is None:
        candidates = (np.array(x, int).reshape(cfg['lanes'], 3)
                      for x in compositions(cfg['booths'], 3*cfg['lanes']))
    else:
        columns = [list(compositions(n, cfg['lanes'])) for n in fixed_counts]
        candidates = (np.array(x, int).T for x in itertools.product(*columns))
    for n in candidates:
        if np.any(n.sum(axis=1) == 0) or np.any(n.sum(axis=0) == 0):
            continue
        yield n


def choose(cfg, fixed_counts=None, required=None):
    scores = []
    lane_cap = 3600/headway(0, cfg)
    for counts in designs(cfg, fixed_counts):
        caps = [capacity(counts, p, cfg['mean_service_s'], lane_cap)[0]
                for p in cfg['payment_scenarios'].values()]
        g = geometry(counts, cfg)
        scores.append((counts, caps, g))
    # Max throughput, then least capital. No arbitrary weighted safety score.
    def pack(row):
        n, caps, geo = row
        return dict(counts=n.tolist(), capacities_vph=dict(zip(cfg['payment_scenarios'], caps)), **geo)
    # Resolve equal throughput/cost by fewer booth streams at the busiest merge;
    # this is an explicit operational tie-break, not a calibrated crash model.
    def tie(r):
        return (r[2]['capital_usd'], max(r[2]['group_sizes']), tuple(r[0].ravel()))
    nominal = min(scores, key=lambda r: (-round(r[1][0], 8), *tie(r)))
    robust = min(scores, key=lambda r: (-round(min(r[1]), 8), *tie(r)))
    feasible = [r for r in scores if min(r[1]) >= (required or 0)-1e-8]
    expansion = min(feasible, key=tie) if feasible and required is not None else None
    # Capacity/cost nondominance, unique points, sorted by capital.
    by_cost = {}
    for r in scores:
        cost = round(r[2]['capital_usd'], 4)
        by_cost[cost] = max(by_cost.get(cost, -1), round(min(r[1]), 8))
    pts = sorted(by_cost.items())
    frontier, best = [], -1
    for cost, rate in pts:
        if rate > best + 1e-7:
            frontier.append([cost, rate]); best = rate
    return dict(enumerated=len(scores), nominal=pack(nominal), robust=pack(robust),
                feasible_expansion=pack(expansion) if expansion else None, frontier=frontier)


def arrival_stream(rate, shares, cfg, seed):
    rng = np.random.default_rng(seed)
    arrivals = []
    now = 0.0
    while True:
        now += rng.exponential(3600/rate)
        if now >= cfg['horizon_s']:
            break
        typ = int(rng.choice(3, p=shares))
        cv = cfg['service_cv'][typ]
        sigma = math.sqrt(math.log1p(cv*cv))
        duration = float(rng.lognormal(math.log(cfg['mean_service_s'][typ])-sigma*sigma/2, sigma))
        arrivals.append((now, typ, duration, float(rng.random())))
    return arrivals


def simulate(design, shares, cfg, rate, seed, av=0, stream=None):
    counts = np.asarray(design['counts'], int)
    route = (operating_routing(counts,shares,cfg,rate,av) if cfg.get('routing_strategy')=='balanced'
             else routing(counts, shares, cfg, av))
    flows = np.asarray(route['type_lane_flow_vph'])
    booth_types, booth_groups, weights = [], [], []
    for g in range(len(counts)):
        for t in range(3):
            for _ in range(counts[g, t]):
                booth_types.append(t); booth_groups.append(g)
                weights.append(flows[g, t]/counts[g, t])
    booth_types = np.array(booth_types)
    weights = np.array(weights)
    options = []
    for t in range(3):
        ids = np.where(booth_types == t)[0]
        probs = weights[ids]/weights[ids].sum()
        options.append((ids, np.cumsum(probs)))
    available = np.zeros(len(booth_types))
    ready = []
    travel = np.repeat(design['length_m']/cfg['departure_speed_m_s'],3)
    if cfg.get('recovery_length_m',0)>0:
        travel[:2] += cfg['departure_speed_m_s']/(2*cfg['cash_acceleration_m_s2'])
    stream = arrival_stream(rate, shares, cfg, seed) if stream is None else stream
    for vehicle, (arrive, typ, duration, coin) in enumerate(stream):
        ids, cumulative = options[typ]
        booth = int(ids[min(int(np.searchsorted(cumulative, coin)), len(ids)-1)])
        finish = max(arrive, available[booth])+duration
        available[booth] = finish
        ready.append((finish+travel[typ], booth_groups[booth], arrive, duration, vehicle,typ))
    exits, delays, waits = [], [], []; exit_types=[]
    last = np.full(cfg['lanes'], -math.inf)
    h = headway(av, cfg)
    for at, lane, arrive, duration, vehicle,typ in sorted(ready):
        depart = max(at, last[lane]+h)
        last[lane] = depart
        exits.append(depart)
        exit_types.append(typ)
        delays.append(depart-arrive-duration-travel[typ])
        # Post-toll waiting (transport completed); unlimited holding assumed.
        if depart > at:
            waits += [(at, 1), (depart, -1)]
    queue, maxqueue = 0, 0
    for _, change in sorted(waits, key=lambda e: (e[0], e[1])):
        queue += change; maxqueue = max(maxqueue, queue)
    completed = int(sum(t <= cfg['horizon_s'] for t in exits))
    arrived_types=[sum(job[1]==t for job in stream) for t in range(3)]
    completed_types=[sum(int(typ==t and depart<=cfg['horizon_s']) for typ,depart in zip(exit_types,exits)) for t in range(3)]
    return dict(seed=seed, arrivals=len(stream), completed=completed,
                arrivals_by_type=arrived_types,completed_by_type=completed_types,
                residual_by_type=[a-d for a,d in zip(arrived_types,completed_types)],
                observed_output_vph=completed*3600/cfg['horizon_s'],
                residual=len(stream)-completed, clearance_s=float(max(0, max(exits, default=0)-cfg['horizon_s'])),
                mean_delay_s=float(np.mean(delays)) if delays else 0.0,
                p95_delay_s=float(np.quantile(delays, .95)) if delays else 0.0,
                max_post_toll_waiting=int(maxqueue), first_arrival_s=stream[0][0] if stream else None)


def execute(cfg, phase):
    baseline_counts = np.asarray(cfg['baseline_counts'])
    baseline = dict(counts=baseline_counts.tolist(), **geometry(baseline_counts, cfg))
    p = cfg['payment_scenarios']['nominal']
    mu = 3600/np.asarray(cfg['mean_service_s'])
    totals = baseline_counts.sum(axis=0)
    baseline['pooled_upper_vph'] = float(min(totals@mu, cfg['lanes']*3600/headway(0,cfg)))
    baseline['type_upper_vph'] = float(np.min(totals*mu/np.asarray(p)))
    baseline.update(routing(baseline_counts, p, cfg))
    result = dict(config=cfg, phase=phase, baseline=baseline)
    if phase == 'baseline':
        return result
    selected = choose(cfg)
    unrestricted = choose({**cfg,'cluster_payment_types':False})
    # Necessary booth counts for required demand under every declared mixture.
    maxshares = np.max(list(cfg['payment_scenarios'].values()), axis=0)
    minimum = np.ceil(cfg['heavy_vph']*maxshares/mu-1e-12).astype(int)
    expanded_cfg = {**cfg, 'booths': int(minimum.sum())}
    expanded = choose(expanded_cfg, fixed_counts=minimum.tolist(), required=cfg['heavy_vph'])
    expansion = expanded['feasible_expansion']
    result.update(search=selected, unrestricted_search=unrestricted,minimum_robust_counts=minimum.tolist(),
                  expansion=expansion, expanded_enumerated=expanded['enumerated'])
    policies = dict(baseline=baseline, nominal=selected['nominal'], robust=selected['robust'])
    if expansion is not None:
        policies['expanded'] = expansion
    simulations = []
    for scenario, shares in cfg['payment_scenarios'].items():
        for load, rate in [('light', cfg['light_vph']), ('heavy', cfg['heavy_vph'])]:
            streams = {s: arrival_stream(rate, shares, cfg, s) for s in cfg['seeds']}
            for policy, design in policies.items():
                replicas = [simulate(design, shares, cfg, rate, seed, stream=streams[seed]) for seed in cfg['seeds']]
                simulations.append(dict(scenario=scenario, load=load, policy=policy, replicas=replicas,
                                        mean_delay_s=float(np.mean([r['mean_delay_s'] for r in replicas])),
                                        mean_clearance_s=float(np.mean([r['clearance_s'] for r in replicas])),
                                        mean_output_vph=float(np.mean([r['observed_output_vph'] for r in replicas]))))
    automation = []
    for av in cfg['av_shares']:
        for name, design in policies.items():
            automation.append(dict(av_share=av, policy=name, headway_s=headway(av,cfg),
                                   **routing(design['counts'], p, cfg, av)))
    from finite_queue import run as finite_run
    finite=[]
    for slots in cfg['finite_occupancy_slots']:
        for scenario,shares in cfg['payment_scenarios'].items():
            for name in ['robust','expanded']:
                design=policies[name];n=np.asarray(design['counts'])
                route=(operating_routing(n,shares,cfg,cfg['heavy_vph'],slots=slots,design=design) if cfg.get('routing_strategy')=='balanced' else routing(n,shares,cfg))
                flows=np.array(route['type_lane_flow_vph'])
                types=[];groups=[];weights=[]
                for g in range(cfg['lanes']):
                    for t in [2,1,0]:
                        for _ in range(n[g,t]):
                            types.append(t);groups.append(g);weights.append(flows[g,t]/n[g,t])
                travel=np.repeat(design['length_m']/cfg['departure_speed_m_s'],3)
                travel[:2]+=cfg['departure_speed_m_s']/(2*cfg['cash_acceleration_m_s2'])
                reps=[]
                for seed in cfg['seeds']:
                    stream=arrival_stream(cfg['heavy_vph'],shares,cfg,seed)
                    reps.append(dict(seed=seed,**finite_run(stream,types,groups,weights,travel,headway(0,cfg),cfg['horizon_s'],slots)))
                finite.append(dict(policy=name,scenario=scenario,slots=slots,replicas=reps,
                                   maximum_resource_load=route.get('maximum_resource_load'),
                                   mean_delay_s=float(np.mean([x['mean_delay_s'] for x in reps])),
                                   mean_output_vph=float(np.mean([x['observed_output_vph'] for x in reps])),
                                   mean_blocked_s=float(np.mean([x['total_booth_blocked_s'] for x in reps]))))
    service_stress={name:{s:capacity(d['counts'],p,cfg['service_stress_s'],3600/headway(0,cfg))[0] for s,p in cfg['payment_scenarios'].items()} for name,d in policies.items()}
    stressed_minimum=np.ceil(cfg['heavy_vph']*maxshares/(3600/np.array(cfg['service_stress_s']))-1e-12).astype(int)
    occupancy_bounds={name:{s:minimum_slots(d,p,cfg,cfg['heavy_vph']) for s,p in cfg['payment_scenarios'].items()} for name,d in policies.items()}
    land_costs={name:[dict(land_price_usd_m2=price,total_capital_usd=d['capital_usd']+price*d['area_m2']) for price in cfg['land_price_scenarios_usd_m2']] for name,d in policies.items()}
    result.update(simulations=simulations, automation=automation,finite_buffers=finite,occupancy_bounds=occupancy_bounds,
                  service_stress=service_stress,stressed_minimum_robust_counts=stressed_minimum.tolist(),land_cost_scenarios=land_costs)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=['baseline', 'improved'], default='improved')
    args = parser.parse_args()
    start = time.perf_counter()
    cfg = json.loads((HERE/'config.json').read_text())
    result = execute(cfg, args.phase)
    result['compute_seconds'] = time.perf_counter()-start
    result['computed_utc'] = datetime.now(timezone.utc).isoformat()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'results.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(dict(phase=args.phase, compute_seconds=result['compute_seconds'], baseline=result['baseline'])))


if __name__ == '__main__':
    main()
