"""Finite sensor diagnostics and independently checked mixing-specific schedules.

Uses the archived accepted baseline. It does not regenerate expensive baseline
optimization or infer real-bath parameters. All new candidates remain conditional.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
import sys

import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'code'))
import model
from policy_validation import replay_schedule

DEADLINE = None


def budget():
    if DEADLINE is not None and time.monotonic() >= DEADLINE:
        raise TimeoutError('Control study time budget exhausted')


def sampled(p, net, flows, step=5.):
    budget()
    y = np.r_[np.full(len(net['cap']), p['initial']), 1.]
    temperatures = [y[:-1].copy()]
    for q in flows:
        propagation = expm(model.system(p, net, q/60000.).toarray()*step)
        for _ in range(int(300/step)):
            y = propagation@y
            temperatures.append(y[:-1].copy())
        budget()
    return np.array(temperatures)


def study(seconds):
    global DEADLINE
    started = time.monotonic()
    DEADLINE = started+seconds
    ref = HERE/'reference'
    archived = json.loads((ref/'mesh_check.json').read_text())
    parameters = json.loads((ref/'results.json').read_text())['parameters']
    flows = np.array(archived['accepted_schedule']['flow_lpm'])
    nominal_net = model.network(parameters)
    nominal = sampled(parameters, nominal_net, flows)
    cold_probe = int(np.unravel_index(np.argmin(nominal), nominal.shape)[1])
    region_indices = np.flatnonzero(nominal_net['region'])
    hot_probe = int(region_indices[np.unravel_index(np.argmax(nominal[:,region_indices]),
                                                   nominal[:,region_indices].shape)[1]])
    probes = np.array([cold_probe, hot_probe])
    sensor_rows = []
    for diffusion in (.0007, .001, .0013):
        p = {**parameters, 'D': diffusion}
        net = model.network(p)
        for bias in (.9, 1., 1.1):
            values = sampled(p, net, flows*bias)
            region = values[:,net['region']]
            observed = values[:,probes]
            lo, hi, span = values.min(1), region.max(1), np.ptp(region, axis=1)
            obs_lo, obs_hi, obs_span = observed.min(1), observed.max(1), np.ptp(observed,axis=1)
            violation = (lo < p['floor']) | (hi > p['ceiling']) | (span > p['span'])
            alarm = (obs_lo < p['floor']) | (obs_hi > p['ceiling']) | (obs_span > p['span'])
            sensor_rows.append(dict(D_m2_s=diffusion,flow_multiplier=bias,
                min_temp_c=float(lo.min()),max_temp_c=float(hi.max()),max_span_c=float(span.max()),
                sample_feasible=bool(not violation.any()),
                max_cold_omission_c=float(np.max(obs_lo-lo)),
                max_hot_omission_c=float(np.max(hi-obs_hi)),
                max_spread_omission_c=float(np.max(span-obs_span)),
                missed_violation_times_s=(np.flatnonzero(violation & ~alarm)*5).tolist()))
    conditional = []
    for diffusion in (.0007, .0013):
        p = {**parameters, 'D': diffusion}
        net = model.network(p)
        def margin(q):
            values = sampled(p, net, q,30.)
            region = values[:,net['region']]
            return np.r_[values.min(1)-39.13,40.9-region.max(1),1.4-np.ptp(region,axis=1)]
        attempts = []
        for seed in (flows,np.full(6,.8)):
            answer = minimize(lambda q:5.*sum(q),seed,method='SLSQP',bounds=[(0.,2.)]*6,
                constraints=[dict(type='ineq',fun=margin)],options=dict(maxiter=80,ftol=1e-8))
            fine = sampled(p,net,answer.x,5.)
            visible = fine[:,net['region']]
            physical_slack = float(min(fine.min()-39.,41.-visible.max(),1.5-np.ptp(visible,axis=1).max()))
            attempts.append(dict(optimizer_success=bool(answer.success),message=str(answer.message),
                seed_lpm=seed.tolist(),iterations=int(answer.nit),flow_lpm=answer.x.tolist(),
                water_l=float(5*sum(answer.x)),coarse_sampled_physical_slack_c=physical_slack))
        feasible = [a for a in attempts if a['coarse_sampled_physical_slack_c'] >= 0.]
        if not feasible:
            conditional.append(dict(D_m2_s=diffusion,attempts=attempts,accepted=False,
                                     reason='No physically feasible coarse candidate'))
            continue
        chosen = min(feasible,key=lambda a:a['water_l'])
        independent = []
        for grid in ((8,4,3),(12,6,4),(16,8,6)):
            budget()
            independent.append(replay_schedule(p,model.network(p,grid),chosen['flow_lpm'],grid,
                                                sample_s=1.,tolerance_c=0.))
        conditional.append(dict(D_m2_s=diffusion,attempts=attempts,chosen=chosen,
            independent=independent,accepted=all(a['continuous_passed'] for a in independent)))
    sources = [Path(__file__), HERE/'code/model.py', HERE/'code/policy_validation.py',
               ref/'mesh_check.json',ref/'results.json']
    return dict(schema_version=1,elapsed_s=time.monotonic()-started,time_budget_s=seconds,
        source_sha256={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        baseline_flow_lpm=flows.tolist(),
        sensor_probes=[dict(index=int(i),coordinate_m=nominal_net['xyz'][i].tolist()) for i in probes],
        sensor_sample_s=5.,sensor_rows=sensor_rows,conditional_schedules=conditional,
        scope='Finite conditional thermal-network development study; noiseless fixed probes; known D and exact flow for reoptimization. No identification or real-bath reliability guarantee. Independent floating-point continuous envelopes share physical conductances and are not interval arithmetic.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=180.)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose a new path to preserve previous evidence')
    if not np.isfinite(args.seconds) or args.seconds <= 0:
        parser.error('Time budget must be finite and positive')
    result = study(args.seconds)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(sensor_cases=len(result['sensor_rows']),
        accepted_schedules=sum(r['accepted'] for r in result['conditional_schedules']),
        elapsed_s=result['elapsed_s'])))
