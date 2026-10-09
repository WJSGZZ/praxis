"""Reproduce the Merge After Toll research audit against an explicit code version.

Run with the repository's locked environment and --results/--code-dir/--output.
The audit can see author code and shares its model family: it is neither an
Agent blind test nor empirical traffic/safety validation. Candidate modules are
executed when imported; use a trusted local code directory. No official problem
text is distributed here. Dependencies are already in the Praxis lock.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
import sympy as sp


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def independent_capacity(counts, shares, means, lane_cap):
    """Maximize lambda directly, independently of reduced-cut enumeration."""
    groups, types = counts.shape
    dims = groups * types + 1
    objective = np.zeros(dims)
    objective[-1] = -1
    eq = np.zeros((types, dims))
    for t in range(types):
        eq[t, t:groups * types:types] = 1
        eq[t, -1] = -shares[t]
    ub = np.zeros((groups, dims))
    for g in range(groups):
        ub[g, g * types:(g + 1) * types] = 1
    bounds = [(0, float(x)) for x in (counts * 3600 / means).ravel()] + [(0, None)]
    fit = linprog(objective, A_eq=eq, b_eq=np.zeros(types),
                  A_ub=ub, b_ub=np.full(groups, lane_cap), bounds=bounds, method='highs')
    if not fit.success:
        raise RuntimeError(f'Independent capacity LP failed: {fit.message}')
    return float(fit.x[-1])


def free_travel(design, cfg):
    travel = np.repeat(design['length_m'] / cfg['departure_speed_m_s'], 3)
    if cfg.get('recovery_length_m', 0) > 0:
        travel[:2] += cfg['departure_speed_m_s'] / (2 * cfg['cash_acceleration_m_s2'])
    return travel


def queue_inputs(model, counts, shares, cfg, *, slots=None, design=None):
    # Compare event engines with the same effective routing policy. For balanced
    # finite storage, occupancy is an input to routing as well as to the queue.
    route = (model.operating_routing(counts, shares, cfg, cfg['heavy_vph'],
                                    slots=slots, design=design)
             if cfg.get('routing_strategy') == 'balanced'
             else model.routing(counts, shares, cfg))
    flows = np.array(route['type_lane_flow_vph'])
    types, groups, weights = [], [], []
    for g in range(len(counts)):
        # Matches the finite-model caller; old simulate uses a different global
        # order but should preserve each payment type's routing intervals.
        for t in [2, 1, 0]:
            for _ in range(counts[g, t]):
                types.append(t)
                groups.append(g)
                weights.append(flows[g, t] / counts[g, t])
    return types, groups, weights


def audit(result, model, finite):
    cfg = result['config']
    checks = []

    def add(name, passed, evidence):
        checks.append(dict(name=name, passed=bool(passed), evidence=evidence))

    u = sp.symbols('u', real=True)
    f = 10 * u**3 - 15 * u**4 + 6 * u**5
    first, second = sp.diff(f, u), sp.diff(f, u, 2)
    p1 = [sp.Integer(0), sp.Integer(1)] + [x for x in sp.solve(second, u) if 0 <= x <= 1]
    p2 = [sp.Integer(0), sp.Integer(1)] + [x for x in sp.solve(sp.diff(second, u), u) if 0 <= x <= 1]
    max_first = max(abs(first.subs(u, x)) for x in p1)
    max_second = max(abs(second.subs(u, x)) for x in p2)
    add('quintic analytic extrema', max_first == sp.Rational(15, 8) and
        sp.simplify(max_second - 10 * sp.sqrt(3) / 3) == 0,
        dict(first=str(max_first), second=str(max_second)))

    rng = np.random.default_rng(8863)
    lp_cases = []
    for i in range(256):
        counts = rng.integers(0, 5, size=(3, 3))
        shares = rng.dirichlet(np.ones(3))
        if i % 7 == 0:
            shares = np.array([0., .3, .7])
        means, lane_cap = rng.uniform(.5, 20, 3), float(rng.uniform(300, 4000))
        candidate, _ = model.capacity(counts, shares, means, lane_cap)
        reference = independent_capacity(counts, shares, means, lane_cap)
        lp_cases.append(dict(counts=counts.tolist(), shares=shares.tolist(),
                             service_s=means.tolist(), lane_cap=lane_cap,
                             candidate=candidate, independent_lp=reference))
    gap = max(abs(x['candidate'] - x['independent_lp']) for x in lp_cases)
    add('256 cut versus independent optimizing LP cases', gap < 1e-7, dict(seed=8863, max_abs_gap=gap))

    # A common taper transit T permits moving metering from exit to entrance:
    # d_k=max(r_k+T,d_{k-1}+h) iff e_k=max(r_k,e_{k-1}+h), d=e+T.
    # At fixed longitudinal speed v, adjacent entries h apart have longitudinal
    # spacing >=v*h whenever both vehicles are in this same group's taper.
    release_rng = np.random.default_rng(8864)
    equivalence_gaps, entry_gaps = [], []
    speed = cfg['departure_speed_m_s']
    for _ in range(128):
        release = np.sort(release_rng.uniform(0, 100, 100))
        transit = float(release_rng.uniform(5, 50))
        h = float(release_rng.uniform(cfg['av_pair_headway_s'], cfg['human_headway_s']))
        prev_d = prev_e = -math.inf
        for r in release:
            d = max(r + transit, prev_d + h)
            e = max(r, prev_e + h)
            equivalence_gaps.append(abs(d - e - transit))
            if math.isfinite(prev_e):
                entry_gaps.append(speed * (e - prev_e))
                assert e - prev_e >= h - 1e-10
            prev_d, prev_e = d, e
    add('random common-transit entrance versus exit metering', max(equivalence_gaps) < 1e-9,
        dict(seed=8864, release_cases=128, vehicles_per_case=100, max_time_gap=max(equivalence_gaps)))
    add('same-group kinematic taper gap surrogate', min(entry_gaps) >= 7 - 1e-9 and
        speed * cfg['av_pair_headway_s'] >= 7,
        dict(min_sampled_longitudinal_gap_m=min(entry_gaps), worst_declared_gap_m=speed * cfg['av_pair_headway_s'],
             assumed_vehicle_length_m=5, assumed_net_gap_m=2,
             assumptions='Common taper, constant longitudinal speed, ordered entries; not braking, cross-group, heavy-vehicle or field safety validation'))

    # Observe actual candidate event times without modifying its source. Tokens
    # must still cover recovery, entrance waiting and taper travel until exit.
    design = result['expansion']
    shares = cfg['payment_scenarios']['nominal']
    types, groups, weights = queue_inputs(model, np.array(design['counts']), shares, cfg,
                                         slots=4, design=design)
    travel = free_travel(design, cfg)
    stream = model.arrival_stream(cfg['heavy_vph'], shares, cfg, cfg['seeds'][0])
    ready_order, admissions, actual_exits = [], {}, {}
    original_push, original_pop = finite.heapq.heappush, finite.heapq.heappop

    def traced_push(heap, event):
        at, _, kind, data = event
        if kind == 'ready':
            lane, job = data
            admissions[tuple(job)] = at - travel[job[1]]
        return original_push(heap, event)

    def traced_pop(heap):
        event = original_pop(heap)
        at, _, kind, data = event
        if kind == 'ready':
            ready_order.append((at, data[0], tuple(data[1])))
        elif kind == 'exit':
            actual_exits[tuple(data[1])] = at
        return event

    finite.heapq.heappush, finite.heapq.heappop = traced_push, traced_pop
    try:
        finite.run(stream, types, groups, weights, travel, model.headway(0, cfg), cfg['horizon_s'], 4)
    finally:
        finite.heapq.heappush, finite.heapq.heappop = original_push, original_pop
    transit = design['taper_length_m'] / speed
    prev_entries = np.full(cfg['lanes'], -math.inf)
    trace_gaps, token_order_valid = [], True
    for ready, lane, job in ready_order:
        release = ready - transit
        entry = max(release, prev_entries[lane] + model.headway(0, cfg))
        departure = actual_exits[job]
        trace_gaps.append(abs(departure - entry - transit))
        token_order_valid = token_order_valid and admissions[job] <= release + 1e-9 and release <= entry + 1e-9 and entry <= departure + 1e-9
        if math.isfinite(prev_entries[lane]):
            token_order_valid = token_order_valid and speed * (entry - prev_entries[lane]) >= 7 - 1e-9
        prev_entries[lane] = entry
    add('finite-event metering equivalence retains occupancy waiting', len(actual_exits) == len(stream) and
        max(trace_gaps, default=0) < 1e-9 and token_order_valid,
        dict(vehicles=len(stream), slots=4, max_departure_difference_s=max(trace_gaps, default=0),
             scope='Same exits and token intervals; entrance waiting remains occupied. Recovery storage and collision safety are not modeled.'))

    three = finite.run([(0., 0, 1., 0.)] * 3, [0], [0], [1.], [2.] * 3, 1., 5., 1)
    add('K1 one booth three jobs', three['completed'] == 2 and three['residual'] == 1 and
        three['clearance_s'] == 2 and three['mean_delay_s'] == 2 and
        three['total_booth_blocked_s'] == 2 and three['peak_occupancy_by_group'] == [1],
        dict(expected_exits_s=[3, 5, 7], actual=three))
    two = finite.run([(0., 0, 1., 0.), (0., 0, 1., .99)], [0, 0], [0, 0], [1., 1.], [2.] * 3, 1., 4., 1)
    add('K1 two parallel booths', two['completed'] == 1 and two['residual'] == 1 and
        two['mean_delay_s'] == 1 and two['total_booth_blocked_s'] == 2 and two['clearance_s'] == 1,
        dict(expected_exits_s=[3, 5], actual=two))
    pipe = finite.run([(0., 0, 1., 0.)] * 3, [0], [0], [1.], [2.] * 3, 1., 5., 3)
    add('K3 pipeline retains booth waiting', pipe['completed'] == 3 and pipe['mean_delay_s'] == 1 and
        pipe['total_booth_blocked_s'] == 0, pipe)

    profiles = [result['baseline'], result['expansion']]
    limits, bounded = [], []
    for design, (scenario, shares), seed in itertools.product(profiles, cfg['payment_scenarios'].items(), cfg['seeds']):
        counts = np.array(design['counts'])
        travel = free_travel(design, cfg)
        types, groups, weights = queue_inputs(model, counts, shares, cfg)
        stream = model.arrival_stream(cfg['heavy_vph'], shares, cfg, seed)
        old = model.simulate(design, shares, cfg, cfg['heavy_vph'], seed, stream=stream)
        large = finite.run(stream, types, groups, weights, travel, model.headway(0, cfg), cfg['horizon_s'], len(stream) + 1)
        fields = ['arrivals', 'completed', 'residual', 'observed_output_vph', 'mean_delay_s', 'p95_delay_s', 'clearance_s']
        limits.append(dict(counts=counts.tolist(), scenario=scenario, seed=seed,
                           max_gap=max(abs(old[k] - large[k]) for k in fields),
                           blocked_s=large['total_booth_blocked_s']))
        small_types, small_groups, small_weights = queue_inputs(
            model, counts, shares, cfg, slots=4, design=design)
        small = finite.run(stream, small_types, small_groups, small_weights,
                           travel, model.headway(0, cfg), cfg['horizon_s'], 4)
        bounded.append(small)
    add('same stream large K limit', all(x['max_gap'] < 1e-9 and x['blocked_s'] == 0 for x in limits),
        dict(cases=len(limits), max_abs_gap=max(x['max_gap'] for x in limits)))
    add('finite K4 drainage conservation occupancy', all(x['arrivals'] == x['completed'] + x['residual'] and
        max(x['peak_occupancy_by_group']) <= 4 and x['mean_delay_s'] >= -1e-9 and x['total_booth_blocked_s'] >= 0
        for x in bounded), dict(cases=len(bounded)))

    for label, design in [('baseline', result['baseline']), ('expanded', result['expansion'])]:
        taper = design['taper_length_m']
        d, speed = design['max_displacement_m'], cfg['departure_speed_m_s']
        count = sum(map(sum, design['counts']))
        slope, accel = 15 / 8 * d / taper, speed**2 * (10 * math.sqrt(3) / 3) * d / taper**2
        area = design['recovery_length_m'] * count * cfg['booth_pitch_m'] + taper * (count * cfg['booth_pitch_m'] + cfg['lanes'] * cfg['lane_width_m']) / 2
        add(f'{label} taper versus total geometry', abs(design['length_m'] - taper - design['recovery_length_m']) < 1e-9 and
            slope <= cfg['max_path_slope'] + 1e-12 and accel <= cfg['lateral_accel_m_s2'] + 1e-12 and
            abs(area - design['area_m2']) < 1e-7, dict(slope=slope, lateral_accel=accel, area=area))

    # Analytic certificate is specific to the archive's support pattern. A new
    # layout must supply a new proof; never silently reuse the old certificate.
    expanded = result['expansion']
    n = np.array(expanded['counts'])
    support = np.array([[0, 0, 1], [1, 1, 1], [1, 0, 0]], dtype=bool)
    supported = n.shape == (3, 3) and np.array_equal(n > 0, support)
    add('analytic occupancy certificate layout support', supported, dict(counts=n.tolist()))
    slot_cases = []
    if supported:
        tau = free_travel(expanded, cfg)
        for scenario, shares in cfg['payment_scenarios'].items():
            cash, exact, etc = cfg['heavy_vph'] * np.array(shares)
            # Noncash must cross groups0+1; stopped vehicles must cross groups1+2.
            noncash = (exact * tau[1] + etc * tau[2]) / 7200
            stopped = (cash * tau[0] + exact * tau[1]) / 7200
            lower = max(noncash, stopped)
            if noncash >= stopped:
                e0 = lower * 3600 / tau[2]
                flow = np.array([[0., 0., e0], [0., exact, etc - e0], [cash, 0., 0.]])
            else:
                c1 = (cash - exact) / 2
                flow = np.array([[0., 0., etc], [c1, exact, 0.], [cash - c1, 0., 0.]])
            witness = bool(np.all(flow >= -1e-8) and
                           np.all(flow <= n * 3600 / np.array(cfg['mean_service_s']) + 1e-8) and
                           np.all(flow.sum(axis=1) <= 3600 / model.headway(0, cfg) + 1e-8) and
                           np.allclose(flow.sum(axis=0), cfg['heavy_vph'] * np.array(shares), rtol=0, atol=1e-8) and
                           np.max(flow @ tau / 3600) <= lower + 1e-8)
            candidate = model.minimum_slots(expanded, shares, cfg, cfg['heavy_vph'])
            value = candidate['continuous_lower_bound']
            archive = result['occupancy_bounds']['expanded'][scenario]['continuous_lower_bound']
            passed = witness and value is not None and archive is not None and abs(value - lower) < 1e-8 and abs(archive - lower) < 1e-8
            add(f'{scenario} analytic occupancy lower bound and feasible witness', passed,
                dict(analytic_lower=lower, integer_necessary=math.ceil(lower - 1e-10),
                     candidate=value, archived=archive, witness=flow.tolist(), witness_feasible=witness,
                     scope='Necessary steady-flow occupancy, not sufficient buffer or finite-window output bound'))
            slot_cases.append(dict(scenario=scenario, noncash_group_bound=noncash, stopped_group_bound=stopped))
    # Optional historical coverage is explicit. Old results without this new
    # field are incomplete for the land audit, never silently reported passed.
    if 'land_cost_scenarios' not in result:
        checks.append(dict(name='land cost coverage', passed=None, status='not_covered',
                           evidence='Result predates land-cost scenarios; no land audit claim.'))
    else:
        prices = cfg.get('land_price_scenarios_usd_m2', [])
        policies = dict(baseline=result['baseline'], nominal=result['search']['nominal'],
                        robust=result['search']['robust'], expanded=result['expansion'])
        independent_areas, capital, observed = {}, {}, {}
        for label, design in policies.items():
            counts = np.asarray(design['counts'])
            booth_count = int(counts.sum())
            groups = len(counts)
            recovery = cfg['recovery_length_m']
            taper = design['taper_length_m']
            booth_width = booth_count * cfg['booth_pitch_m']
            exit_width = groups * cfg['lane_width_m']
            area = recovery * booth_width + taper * (booth_width + exit_width) / 2
            equipment = float(counts.sum(axis=0) @ np.asarray(cfg['equipment_cost_usd']))
            construction = area * cfg['road_cost_usd_m2']
            independent_areas[label], capital[label] = area, construction + equipment
            rows = result['land_cost_scenarios'].get(label, [])
            actual = {row['land_price_usd_m2']: row['total_capital_usd'] for row in rows}
            observed[label] = actual
            passed = (bool(prices) and len(rows) == len(prices) and set(actual) == set(prices) and
                      abs(area - design['area_m2']) < 1e-7 and
                      abs(capital[label] - design['capital_usd']) < 1e-6 and
                      all(abs(actual[price] - (construction + equipment + price * area)) < 1e-6 for price in prices))
            add(f'{label} independent area equipment land total', passed,
                dict(area_m2=area, equipment_usd=equipment, construction_usd=construction,
                     expected_totals=[dict(land_price_usd_m2=price, total_capital_usd=construction + equipment + price * area) for price in prices],
                     scope='Illustrative cost scenarios, not measured prices, ROI or an investment recommendation'))
        area_difference = independent_areas['expanded'] - independent_areas['robust']
        pairs, premium_valid = [], True
        for lo, hi in zip(sorted(set(prices)), sorted(set(prices))[1:]):
            if any(p not in observed[label] for p in [lo, hi] for label in ['expanded', 'robust']):
                premium_valid = False
                continue
            lower = observed['expanded'][lo] - observed['robust'][lo]
            upper = observed['expanded'][hi] - observed['robust'][hi]
            slope = (upper - lower) / (hi - lo)
            premium_valid = premium_valid and abs(slope - area_difference) < 1e-7
            pairs.append(dict(price_interval=[lo, hi], observed_premium_slope_m2=slope))
        add('expansion versus robust land premium slope', premium_valid and bool(pairs),
            dict(independent_area_difference_m2=area_difference, slope_checks=pairs,
                 scope='Slope of illustrative upfront cost difference only; no revenue, return or payback model'))
    return dict(checks=checks, lp_cases=lp_cases, large_K_cases=limits, slot_constraints=slot_cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--code-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.results.read_text())
    model = load_module(args.code_dir / 'model.py', 'merge_audit_candidate_model')
    finite = load_module(args.code_dir / 'finite_queue.py', 'merge_audit_candidate_finite')
    report = audit(result, model, finite)
    report['scope'] = 'Author-external role with visible code, shared model family; not blind or field safety validation'
    report['inputs_sha256'] = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in
                               [('results', args.results), ('model.py', args.code_dir / 'model.py'), ('finite_queue.py', args.code_dir / 'finite_queue.py')]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    checks = report['checks']
    not_covered = sum(x.get('status') == 'not_covered' for x in checks)
    print(json.dumps(dict(passed=sum(x['passed'] is True for x in checks), checks=len(checks), not_covered=not_covered)))
    # Exit 2 distinguishes incomplete historic coverage from a failed check (1).
    raise SystemExit(1 if any(x['passed'] is False for x in checks) else 2 if not_covered else 0)


if __name__ == '__main__':
    main()
