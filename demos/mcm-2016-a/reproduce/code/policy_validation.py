"""Independent RK45 replay and conditional continuous envelopes for schedules.

The physical network coefficients are shared with the model. The heat-flow RHS,
jet-zone mask and time integration are assembled independently; this is not a
second physical model or an interval-arithmetic certificate.
"""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import csr_matrix


def outside_jet(p, grid):
    nx, ny, nz = grid
    step = np.array([p['L']/nx, p['W']/ny, p['H']/nz])
    centres = np.array([[(i+.5)*step[0], (j+.5)*step[1], (k+.5)*step[2]]
                        for i in range(nx) for j in range(ny) for k in range(nz)])
    inlet = np.array([.5*step[0], (ny//2+.5)*step[1], (nz-.5)*step[2]])
    return np.linalg.norm(centres-inlet, axis=1) > p['inlet_exclusion']


def replay_schedule(p, net, flows_lpm, grid, sample_s=1., tolerance_c=.002):
    flows = np.asarray(flows_lpm, dtype=float)
    if flows.ndim != 1 or not len(flows) or not np.isfinite(flows).all() or (flows < 0).any():
        raise ValueError('Schedule must have finite nonnegative flows')
    if not 0 < sample_s <= 1 or p['horizon'] <= 0:
        raise ValueError('Positive horizon and sampling interval at most one second required')
    cap, ha, hb = (np.asarray(net[k]) for k in ('cap', 'ha', 'hb'))
    if not np.isfinite(cap).all() or (cap <= 0).any():
        raise ValueError('Finite positive heat capacities required')
    g, adv = csr_matrix(net['G']), csr_matrix(net['adv'])
    zone = outside_jet(p, grid)
    if len(zone) != len(cap) or not zone.any():
        raise ValueError('Independent jet mask has no constrained cells or wrong size')
    allowance = 2e-6
    duration = float(p['horizon']/len(flows))
    y = np.full(len(cap), p['initial'], dtype=float)
    segments = []
    for index, flow_lpm in enumerate(flows):
        start, stop = index*duration, (index+1)*duration
        flow = flow_lpm/60000.
        def rhs(t, state):
            return (g@state + ha*(p['air_temp']-state) + hb*(p['body_temp']-state)
                    + flow*(adv@state + net['hot']))/cap
        a = (g+flow*adv).toarray()
        a[np.diag_indices_from(a)] -= ha+hb
        a /= cap[:, None]
        row_sum = float(a.sum(axis=1).max())
        np.fill_diagonal(a, 0.)
        minimum_off = float(a.min())
        premise = minimum_off >= -1e-12 and row_sum <= 1e-12
        times = np.linspace(start, stop, int(np.ceil(duration/sample_s))+1)
        # Restart at every discontinuity. Both adjacent segments include the
        # switch state, but have their own RHS and derivative bounds.
        sol = solve_ivp(rhs, (start, stop), y, dense_output=True, method='RK45',
                        rtol=2e-9, atol=2e-10, max_step=sample_s)
        if not sol.success or not np.isfinite(sol.y).all():
            raise RuntimeError(sol.message)
        states = sol.sol(times).T
        y = states[-1]
        visible = states[:, zone]
        lower, upper, span = states.min(axis=1), visible.max(axis=1), np.ptp(visible, axis=1)
        # In each constant-control segment w=T' obeys w'=Aw. The checked
        # contraction premise bounds ||w(t)||inf by its norm at the left
        # endpoint of each sampling interval. The nearest endpoint is at most
        # gap/2 away; spread has Lipschitz bound 2||w||inf.
        def envelope(points):
            yy = sol.sol(points).T
            vv = yy[:, zone]
            lo, hi, sp = yy.min(axis=1), vv.max(axis=1), np.ptp(vv, axis=1)
            derivatives = ((g@yy.T).T + ha*(p['air_temp']-yy) + hb*(p['body_temp']-yy)
                           + flow*((adv@yy.T).T+net['hot']))/cap
            norms = np.max(np.abs(derivatives), axis=1)
            radii = norms[:-1]*np.diff(points)/2
            return (np.minimum(lo[:-1], lo[1:])-radii-allowance,
                    np.maximum(hi[:-1], hi[1:])+radii+allowance,
                    np.maximum(sp[:-1], sp[1:])+(2*radii if zone.sum() > 1 else 0)+2*allowance,
                    norms)
        def unresolved(bounds):
            lo, hi, sp, _ = bounds
            return (lo < p['floor']) | (hi > p['ceiling']) | (sp > p['span'])
        sampled = lower.min() >= p['floor']-tolerance_c and upper.max() <= p['ceiling']+tolerance_c and span.max() <= p['span']+tolerance_c
        one_second = envelope(times)
        one_second_passed = premise and not unresolved(one_second).any()
        # Include actual RK45 step endpoints, then bisect only intervals whose
        # bounds remain inconclusive. The policy and physical limits stay fixed.
        envelope_times = np.unique(np.r_[times, sol.t])
        rounds = 0
        while True:
            bounds = envelope(envelope_times)
            bad = unresolved(bounds)
            if not premise or not sampled or not bad.any() or rounds == 8:
                break
            midpoints = (envelope_times[:-1][bad]+envelope_times[1:][bad])/2
            envelope_times = np.unique(np.r_[envelope_times, midpoints])
            rounds += 1
        lo_bounds, hi_bounds, span_bounds, rates = bounds
        gaps = np.diff(envelope_times)
        lower_bound, upper_bound, span_bound = float(lo_bounds.min()), float(hi_bounds.max()), float(span_bounds.max())
        continuous = premise and lower_bound >= p['floor'] and upper_bound <= p['ceiling'] and span_bound <= p['span']
        segments.append(dict(segment=index, start_s=start, stop_s=stop, flow_lpm=float(flow_lpm),
            samples=len(times), largest_sample_gap_s=float(np.diff(times).max()),
            envelope_samples=len(envelope_times), largest_envelope_gap_s=float(gaps.max()),
            smallest_envelope_gap_s=float(gaps.min()), envelope_refinement_rounds=rounds,
            one_second_continuous_passed=bool(one_second_passed),
            one_second_lower_bound_c=float(one_second[0].min()),
            one_second_upper_bound_c=float(one_second[1].max()),
            one_second_span_upper_bound_c=float(one_second[2].max()),
            min_temp=float(lower.min()), max_temp=float(upper.max()), max_span=float(span.max()),
            contraction_premise=bool(premise), min_off_diagonal_per_s=minimum_off, max_row_sum_per_s=row_sum,
            initial_derivative_norm_c_per_s=float(rates[0]),
            lower_temperature_bound_c=lower_bound, upper_temperature_bound_c=upper_bound,
            span_upper_bound_c=span_bound, sampled_passed=bool(sampled), continuous_passed=bool(continuous)))
    return dict(grid=list(grid), min_temp=min(s['min_temp'] for s in segments),
        max_temp=max(s['max_temp'] for s in segments), max_span=max(s['max_span'] for s in segments),
        lower_temperature_bound_c=min(s['lower_temperature_bound_c'] for s in segments),
        upper_temperature_bound_c=max(s['upper_temperature_bound_c'] for s in segments),
        span_upper_bound_c=max(s['span_upper_bound_c'] for s in segments),
        sampled_passed=all(s['sampled_passed'] for s in segments),
        continuous_passed=all(s['continuous_passed'] for s in segments), segments=segments,
        sample_s=sample_s, numerical_tolerance_c=tolerance_c, continuous_limit_tolerance_c=0., integration_allowance_c=allowance,
        scope='Conditional envelope for this thermal network; floating-point RK45 is not interval arithmetic or empirical validation')
