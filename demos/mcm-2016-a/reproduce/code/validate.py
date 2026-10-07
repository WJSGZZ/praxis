"""Independent arithmetic and integration checks, not a second physical model.

Reuses the published network coefficients, but independently forms the heat-flow
RHS and integrates it with adaptive RK45. No experimental accuracy is inferred.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

import model


def jet_zone_mask(p, grid):
    """Cells outside the inlet jet zone, from the geometry alone (independent of the model's own mask)."""
    nx, ny, nz = grid
    dx, dy, dz = p['L']/nx, p['W']/ny, p['H']/nz
    inlet = np.array([.5*dx, (ny//2+.5)*dy, (nz-.5)*dz])
    centres = np.array([[(i+.5)*dx, (j+.5)*dy, (k+.5)*dz] for i in range(nx) for j in range(ny) for k in range(nz)])
    return np.sqrt(((centres-inlet)**2).sum(axis=1)) > p['inlet_exclusion']


def validate(results_path):
    result = json.loads(results_path.read_text())
    p = result['parameters']
    net = model.network(p, tuple(result['grid']))
    policy = result['policy']
    checks = []

    def check(name, passed, requirements=None, **evidence):
        item = dict(name=name, passed=bool(passed),
                    evidence=json.dumps(evidence, ensure_ascii=False, sort_keys=True))
        if requirements is not None:
            item['requirements'] = requirements
        checks.append(item)

    if not policy.get('feasible'):
        check('policy_available', False, reason='No feasible selected policy')
        return checks
    q = policy['flow_lpm'] / 60000
    delay = policy['delay_s']
    cap, ha, hb = net['cap'], net['ha'], net['hb']
    g, adv = net['G'], net['adv']
    n = len(cap)

    def rhs(t, y, flow):
        # Independently summed sensible heat inputs, W, divided by J/K.
        internal = g @ y
        environmental = ha * (p['air_temp'] - y)
        body = hb * (p['body_temp'] - y)
        stream = flow * (adv @ y + net['hot'])
        return (internal + environmental + body + stream) / cap

    def integrate(flow, initial, start, stop, samples):
        if stop <= start:
            return np.asarray(initial)[None, :]
        sol = solve_ivp(lambda t, y: rhs(t, y, flow), (start, stop), initial,
                        method='RK45', rtol=2e-9, atol=2e-10,
                        t_eval=samples, max_step=5.)
        if not sol.success:
            raise RuntimeError(sol.message)
        return sol.y.T

    # Split at the control discontinuity, preserving it exactly in both grids.
    before = np.unique(np.r_[np.arange(0, delay, 1.), delay])
    after = np.unique(np.r_[delay, np.arange(np.ceil(delay), p['horizon'], 1.), p['horizon']])
    coast = integrate(0., np.full(n, p['initial']), 0., delay, before)
    hold = integrate(q, coast[-1], delay, p['horizon'], after)
    times = np.r_[before, after[1:]]
    states = np.vstack([coast, hold[1:]])
    check('finite_positive_heat_capacities', np.isfinite(states).all() and (cap > 0).all(),
          smallest_capacity_j_per_k=float(cap.min()), samples=len(times))

    # Raw physical heat accounting explicitly includes overflow at local outlet T.
    defects = []
    powers = []
    for t, y in zip(times, states):
        flow = 0. if t < delay else q
        storage = float(cap @ rhs(t, y, flow))
        external = float(np.sum(ha * (p['air_temp'] - y)) + np.sum(hb * (p['body_temp'] - y))
                         + p['rho'] * p['cp'] * flow * (p['inlet_temp'] - y[net['outlet']]))
        defects.append(abs(storage - external))
        powers.append(abs(external))
    max_defect = max(defects)
    check('instantaneous_energy_balance_with_overflow', max_defect < 1e-7,
          max_residual_w=max_defect, formulation='sum(C_i dT_i/dt) = air + body + rho cp q (Tin - Tout)',
          tolerance_w=1e-7)
    # Integrate each constant-control segment separately; the inlet jump is not
    # smeared across a trapezoid. This checks cumulative sensible-energy storage.
    def boundary_power(y, flow):
        return (np.sum(ha*(p['air_temp']-y), axis=1)
                + np.sum(hb*(p['body_temp']-y), axis=1)
                + p['rho']*p['cp']*flow*(p['inlet_temp']-y[:,net['outlet']]))
    def trapezoid(values, t):
        return float(np.sum((values[:-1]+values[1:])*.5*np.diff(t)))
    integrated = trapezoid(boundary_power(coast,0.),before)+trapezoid(boundary_power(hold,q),after)
    storage_change = float(cap @ (states[-1]-states[0]))
    cumulative_error = abs(storage_change-integrated)
    check('cumulative_energy_balance_with_overflow', cumulative_error < 30.,
          stored_energy_change_j=storage_change, integrated_boundary_energy_j=integrated,
          residual_j=cumulative_error, tolerance_j=30.,
          quadrature='One-second trapezoids, split exactly at control switch')
    check('internal_exchange_is_conservative', np.max(np.abs(g.sum(axis=0))) < 1e-8,
          max_column_sum_w_per_k=float(np.max(np.abs(g.sum(axis=0)))))
    outlet_sum = np.zeros(n); outlet_sum[net['outlet']] = -p['rho'] * p['cp']
    check('advection_has_only_one_overflow_sink', np.max(np.abs(adv.sum(axis=0)-outlet_sum)) < 1e-8,
          max_column_sum_defect=float(np.max(np.abs(adv.sum(axis=0)-outlet_sum))))

    saved = np.load(results_path.parent / 'trajectory.npz')
    saved_t, saved_y = saved['t'], saved['T']
    # Replay precisely the archived time stamps: avoid interpolating the reference.
    left = saved_t[saved_t <= delay]
    right = saved_t[saved_t > delay]
    replay_left = integrate(0., np.full(n, p['initial']), 0., delay, left)
    initial_hold = coast[-1]
    replay_right = integrate(q, initial_hold, delay, p['horizon'], right) if len(right) else np.empty((0,n))
    replay = np.vstack([replay_left, replay_right])
    error = float(np.max(np.abs(saved_y - replay)))
    check('independent_RK45_vs_archived_matrix_exponential', error < 2e-6,
          maximum_temperature_difference_c=error, tolerance_c=2e-6,
          independence='Same physical coefficients; independently assembled RHS and adaptive integration')
    zone = jet_zone_mask(p, tuple(result['grid']))
    minimum, maximum = float(states.min()), float(states[:, zone].max())
    span = float(np.ptp(states[:, zone], axis=1).max())
    check('one_second_sampled_policy_constraints', minimum >= p['floor']-.002 and maximum <= p['ceiling']+.002 and span <= p['span']+.002,
          minimum_c=minimum, maximum_c=maximum, max_span_c=span,
          floor_c=p['floor'], ceiling_c=p['ceiling'], span_limit_c=p['span'],
          numerical_tolerance_c=.002, limitation='Sampled check, not a continuous-time feasibility certificate')

    stored_metrics = dict(min_temp=minimum,max_temp=maximum,max_span=span)
    sampling_differences = {key:float(abs(policy[key]-value)) for key,value in stored_metrics.items()}
    check('policy_summary_vs_one_second_replay', all(value<.002 for value in sampling_differences.values()),
          absolute_metric_differences_c=sampling_differences, tolerance_c=.002,
          interpretation='Checks reporting and coarse-time sampling bias; does not prove the policy is globally optimal')

    # In a constant-control segment, w=T' obeys w'=Aw. For a Metzler
    # A with nonpositive row sums its infinity-norm semigroup is contractive.
    # Hence |T_i'| <= the derivative norm at the segment start. At most half
    # the largest sample gap separates a time from its nearest sample; a span
    # has Lipschitz constant at most 2L. Check the premise before using it.
    premises = []
    for flow in (0., q):
        a = (g+flow*adv-np.diag(ha+hb))/cap[:,None]
        off = a.copy(); np.fill_diagonal(off,0.)
        premises.append(dict(min_off_diagonal=float(off.min()),
                             max_row_sum=float(a.sum(axis=1).max())))
    premise_ok = all(item['min_off_diagonal'] >= -1e-12 and item['max_row_sum'] <= 1e-12 for item in premises)
    check('continuous_envelope_contraction_premise',premise_ok,
          segment_matrices=premises,condition='Metzler A and nonpositive row sums')
    rates = [float(np.max(np.abs(rhs(0.,np.full(n,p['initial']),0.)))),
             float(np.max(np.abs(rhs(delay,coast[-1],q))))]
    lipschitz = max(rates)
    gap = max(float(np.diff(before).max()) if len(before)>1 else 0.,
              float(np.diff(after).max()) if len(after)>1 else 0.)
    integration_allowance = 2e-6
    lower_envelope = minimum-lipschitz*gap/2-integration_allowance
    upper_envelope = maximum+lipschitz*gap/2+integration_allowance
    span_envelope = span+lipschitz*gap+2*integration_allowance
    check('continuous_time_policy_envelope',premise_ok
          and lower_envelope >= p['floor']-.002
          and upper_envelope <= p['ceiling']+.002
          and span_envelope <= p['span']+.002,
          derivative_bound_c_per_s=lipschitz,segment_initial_derivative_norms_c_per_s=rates,
          largest_sample_gap_s=gap,lower_temperature_bound_c=lower_envelope,
          upper_temperature_bound_c=upper_envelope,span_upper_bound_c=span_envelope,
          floor_c=p['floor'],ceiling_c=p['ceiling'],span_limit_c=p['span'],
          feasibility_tolerance_c=.002,integration_allowance_c=integration_allowance,
          proof='Contractive positive semigroup bounds derivative norm; nearest-sample distance <= gap/2.',
          scope='Conditional continuous-time envelope for the stated thermal network; floating-point integration is not interval arithmetic or empirical validation')

    # A uniform artificial loss k C_i gives an exact uniform exponential solution,
    # irrespective of unequal heat capacities or internal exchange coefficients.
    simplified = dict(net)
    decay = 1/900
    simplified['ha'] = decay * cap
    simplified['hb'] = np.zeros(n)
    exact_t, computed = model.evolve(p, simplified, 0., np.full(n, p['initial']), 1800., 15.)
    exact = p['air_temp']+(p['initial']-p['air_temp'])*np.exp(-decay*exact_t)
    uniform_error = float(np.max(np.abs(computed-exact[:,None])))
    check('uniform_zero_flow_analytic_cooling', uniform_error < 2e-8,
          max_error_c=uniform_error, decay_per_s=decay,
          simplified_problem='No body loss; ha_i = k C_i; initially uniform temperature')

    # Verify positivity and invariant-temperature bounds algebraically at both modes.
    for flow, label in [(0., 'coast'), (q, 'flow')]:
        a = (g + flow*adv - np.diag(ha+hb))/cap[:,None]
        off = a.copy(); np.fill_diagonal(off, 0.)
        low = min(p['air_temp'],p['body_temp'],p['initial'],p['inlet_temp'])
        high = max(p['air_temp'],p['body_temp'],p['initial'],p['inlet_temp'])
        low_derivative = rhs(0.,np.full(n,low),flow)
        high_derivative = rhs(0.,np.full(n,high),flow)
        steady = np.linalg.solve(-a, (ha*p['air_temp']+hb*p['body_temp']+flow*net['hot'])/cap)
        check('positive_system_and_steady_bounds_'+label,
              off.min()>=-1e-12 and low_derivative.min()>=-1e-10 and high_derivative.max()<=1e-10
              and steady.min()>=low-1e-8 and steady.max()<=high+1e-8,
              min_off_diagonal_per_s=float(off.min()), steady_min_c=float(steady.min()),
              steady_max_c=float(steady.max()), invariant_bounds_c=[low,high])

    # Compute aggregate conductances from physical dimensions instead of ha/hb sums.
    h_air = p['h_surface']*p['foam']*p['L']*p['W'] + p['h_wall']*(p['L']*p['W']+2*p['H']*(p['L']+p['W']))
    h_body = p['h_body']*p['body_area']
    total_c = p['rho']*p['cp']*(p['L']*p['W']*p['H']-p['body_volume'])
    eq = (h_air*p['air_temp']+h_body*p['body_temp'])/(h_air+h_body)
    coast_time = total_c/(h_air+h_body)*np.log((p['initial']-eq)/(p['floor']-eq))
    loss_floor = h_air*(p['floor']-p['air_temp'])+h_body*(p['floor']-p['body_temp'])
    heat_per_litre = p['rho']*p['cp']*(p['inlet_temp']-p['floor'])/1000
    lower = max(0.,(loss_floor*p['horizon']-total_c*(p['initial']-p['floor']))/heat_per_litre)
    ideal = loss_floor*max(0.,p['horizon']-coast_time)/heat_per_litre
    flow_lpm = loss_floor/heat_per_litre*60
    pairs = dict(air_conductance=h_air,body_conductance=h_body,coast_s=coast_time,
                 energy_lower_bound_l=lower,mixed_optimum_l=ideal,hold_lpm=flow_lpm,
                 volume_l=(p['L']*p['W']*p['H']-p['body_volume'])*1000)
    differences = {k:float(abs(result['analytic'][k]-v)) for k,v in pairs.items()}
    check('independent_closed_form_arithmetic', all(v<1e-8 for v in differences.values()),
          independent_values={k:float(v) for k,v in pairs.items()}, absolute_differences=differences)
    check('policy_respects_optimistic_energy_lower_bound', policy['water_l'] >= lower-1e-6 and ideal >= lower-1e-6,
          selected_policy_water_l=policy['water_l'], ideal_mixed_water_l=ideal, energy_lower_bound_l=lower,
          assumptions='All cells at least floor; inlet fixed; overflow at least floor; constant thermal coefficients')
    geometry_evidence = {}
    replay_evidence = {}
    no_accepted_candidate = []
    for label, scenario in result['scenarios'].items():
        pp = {**p, **scenario['changes']}
        nn = model.network(pp, tuple(result['grid']))
        expected_geometry = dict(
            volume_l=1000*(pp['L']*pp['W']*pp['H']-pp['body_volume']),
            air_conductance=pp['h_surface']*pp['foam']*pp['L']*pp['W']
                +pp['h_wall']*(pp['L']*pp['W']+2*pp['H']*(pp['L']+pp['W'])),
            body_conductance=pp['h_body']*pp['body_area'])
        deviations = {key:float(abs(scenario['analytic'][key]-value))
                      for key,value in expected_geometry.items()}
        geometry_evidence[label] = dict(independent_values=expected_geometry,
                                       absolute_differences=deviations,
                                       passed=all(v<1e-8 for v in deviations.values()))
        selected = scenario['policy']
        if not selected.get('feasible'):
            no_accepted_candidate.append(label)
            continue
        flow = selected['flow_lpm']/60000
        switch = selected['delay_s']
        def scenario_rhs(t,y,local_flow):
            return (nn['G']@y + nn['ha']*(pp['air_temp']-y)
                    +nn['hb']*(pp['body_temp']-y)
                    +local_flow*(nn['adv']@y+nn['hot']))/nn['cap']
        def segment(start,end,initial,local_flow):
            if end <= start:
                return np.asarray(initial)[None,:]
            sample_times = np.linspace(start,end,int(np.ceil((end-start)/5.))+1)
            sol = solve_ivp(lambda t,y:scenario_rhs(t,y,local_flow),(start,end),initial,
                            t_eval=sample_times,method='RK45',rtol=2e-9,atol=2e-10,max_step=5.)
            if not sol.success:
                raise RuntimeError('Scenario '+label+': '+sol.message)
            return sol.y.T
        cy = segment(0.,switch,np.full(len(nn['cap']),pp['initial']),0.)
        hy = segment(switch,pp['horizon'],cy[-1],flow)
        yy = np.vstack([cy,hy[1:]])
        zone = jet_zone_mask(pp, tuple(result['grid']))
        independent_metrics = dict(min_temp=float(yy.min()),max_temp=float(yy[:,zone].max()),
            max_span=float(np.ptp(yy[:,zone],axis=1).max()),
            final_mean=float(yy[-1]@nn['vol']/nn['vol'].sum()),
            final_min=float(yy[-1].min()),final_max=float(yy[-1].max()))
        deviations = {key:float(abs(selected[key]-value)) for key,value in independent_metrics.items()}
        constraints = independent_metrics['min_temp'] >= pp['floor']-.002 \
            and independent_metrics['max_temp'] <= pp['ceiling']+.002 \
            and independent_metrics['max_span'] <= pp['span']+.002
        replay_evidence[label] = dict(independent_metrics=independent_metrics,
            absolute_summary_differences_c=deviations, sampled_constraints_passed=constraints,
            passed=constraints and all(v<.002 for v in deviations.values()), samples=len(yy))
    check('all_scenario_geometry_arithmetic',bool(geometry_evidence)
          and all(item['passed'] for item in geometry_evidence.values()),requirements=['Q2','Q3'],
          scenarios=geometry_evidence,tolerance=1e-8,
          independence='Physical dimensions and coefficients used directly, not sums of the assembled network')
    check('independent_scenario_RK45_replay',bool(replay_evidence)
          and all(item['passed'] for item in replay_evidence.values()),requirements=['Q2','Q3'],
          scenarios=replay_evidence,summary_tolerance_c=.002,maximum_sampling_interval_s=5.,
          no_accepted_candidate=no_accepted_candidate,
          interpretation='Feasible scenarios independently integrated with RK45; constraints are sampled only. Cases with no accepted candidate are search outcomes, not proofs of physical or mathematical infeasibility.')
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        checks = validate(args.results)
    except Exception as exc:
        checks = [dict(name='validator_execution', passed=False,
                       evidence=json.dumps(dict(exception=type(exc).__name__, message=str(exc)), ensure_ascii=False))]
    passed = bool(checks) and all(c['passed'] for c in checks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(checks, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(dict(passed=passed, checks=len(checks))))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
