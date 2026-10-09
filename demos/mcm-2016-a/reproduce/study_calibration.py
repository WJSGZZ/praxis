"""Synthetic finite measurement-compatible control study, not real-bath fitting.

Replays a separate calibration pulse, screens a declared parameter grid, then
optimizes and independently checks a post-calibration open-loop candidate.
The control starts again at 40 C; it is not continuation of the pulse trial.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'code'))
import model
from policy_validation import replay_schedule

PROBES = [89, 6]
PULSE = [0., 0., 1.2, 0., 0., 0.]
GRIDS = [(8, 4, 3), (12, 6, 4), (16, 8, 6)]


def compatible_offset(difference, reading_bound=.02, offset_bound=.02):
    """Minimax correction a; physical bias b=-a in y=T_model+b+e."""
    a = np.clip((difference.max(0) + difference.min(0)) / 2,
                -offset_bound, offset_bound)
    residual = float(np.max(np.abs(difference - a)))
    return a, residual, residual <= reading_bound


def study(seconds):
    started = time.monotonic()

    def budget():
        if time.monotonic() - started >= seconds:
            raise TimeoutError('Calibration study budget exhausted')

    def simulate(parameters, flows, step, net=None):
        budget()
        net = model.network(parameters) if net is None else net
        y = np.r_[np.full(len(net['cap']), parameters['initial']), 1.]
        values = [y[:-1].copy()]
        for flow in flows:
            budget()
            matrix = model.system(parameters, net,
                                  flow * parameters['flow_multiplier'] / 60000.)
            propagation = expm(matrix.toarray() * step)
            for _ in range(round(300 / step)):
                y = propagation @ y
                values.append(y[:-1].copy())
        return np.array(values), net

    def slack(parameters, flows, step, net=None):
        values, net = simulate(parameters, flows, step, net)
        view = values[:, net['region']]
        return np.r_[values.min(1) - 39., 41. - view.max(1),
                     1.5 - np.ptp(view, axis=1)]

    baseline = json.loads((HERE / 'reference/mesh_check.json').read_text())
    initial = np.array(baseline['accepted_schedule']['flow_lpm'])
    base = {**model.BASE, 'flow_multiplier': 1.}
    nominal, _ = simulate(base, PULSE, 30.)
    rows = []
    grid_values = dict(D=np.linspace(.00085, .00115, 7).tolist(),
                       h_surface=np.linspace(20., 30., 9).tolist(),
                       h_body=np.linspace(15., 35., 9).tolist(),
                       flow_multiplier=np.linspace(.95, 1.05, 5).tolist())
    for parameters_tuple in itertools.product(*grid_values.values()):
        parameters = dict(zip(grid_values, parameters_tuple))
        p = {**base, **parameters}
        values, _ = simulate(p, PULSE, 30.)
        correction, residual, compatible = compatible_offset(values[:, PROBES] - nominal[:, PROBES])
        if compatible:
            rows.append(dict(parameters=parameters,
                model_correction_c=correction.tolist(),
                physical_sensor_bias_c=(-correction).tolist(),
                measurement_max_residual_c=residual,
                baseline_sampled_slack_c=float(slack(p, initial, 5.).min())))
    if not rows:
        raise ValueError('No compatible models; cannot propose a control')
    plants = [({**base, **r['parameters']}, model.network({**base, **r['parameters']})) for r in rows]
    selected = set()
    for key in grid_values:
        selected.add(min(range(len(rows)), key=lambda i: rows[i]['parameters'][key]))
        selected.add(max(range(len(rows)), key=lambda i: rows[i]['parameters'][key]))
    selected.update(i for i, r in enumerate(rows) if r['baseline_sampled_slack_c'] < 0.)
    q = initial.copy()
    rounds = []
    for _ in range(3):
        indices = sorted(selected)

        def constraints(q):
            parts = []
            for i in indices:
                margin = slack(plants[i][0], q, 30., plants[i][1]) - .1
                margin[:len(margin) // 3] -= .03
                parts.append(margin)
            return np.concatenate(parts)

        answer = minimize(lambda q: 5 * sum(q), q, method='SLSQP',
            bounds=[(0., 2.)] * 6, constraints=[dict(type='ineq', fun=constraints)],
            callback=lambda _: budget(), options=dict(maxiter=60, ftol=1e-8))
        q = answer.x
        slacks = [float(slack(p, q, 5., net).min()) for p, net in plants]
        rounds.append(dict(selected_indices=indices, optimizer_success=bool(answer.success),
            message=str(answer.message), flow_lpm=q.tolist(), sampled_slacks_c=slacks))
        failures = [i for i, s in enumerate(slacks) if s < 0.]
        if not failures:
            break
        selected.update(sorted(failures, key=lambda i: slacks[i])[:6])
    replays = []
    for i, (p, _) in enumerate(plants):
        for grid in GRIDS:
            budget()
            actual = q * p['flow_multiplier']
            result = replay_schedule(p, model.network(p, grid), actual, grid,
                                     sample_s=1., tolerance_c=0.)
            replays.append(dict(model_index=i, grid=list(grid), water_l=float(5 * sum(actual)),
                **{key: result[key] for key in ('continuous_passed', 'sampled_passed',
                    'lower_temperature_bound_c', 'upper_temperature_bound_c', 'span_upper_bound_c')}))
    budget()
    accepted = all(r['continuous_passed'] for r in replays) and all(s >= 0 for s in slacks)
    paths = ['study_calibration.py', 'code/model.py', 'code/policy_validation.py',
             'reference/mesh_check.json']
    return dict(schema_version=1, status='completed', accepted=accepted,
        elapsed_s=time.monotonic() - started, time_budget_s=seconds,
        source_sha256={name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in paths},
        parameter_grid=grid_values, candidate_models=2835, compatible_models=len(rows),
        probes=PROBES, pulse_flow_lpm=PULSE, observation_sample_s=30.,
        reading_bound_c=.02, constant_offset_bound_c=.02, rows=rows, rounds=rounds,
        baseline_flow_lpm=initial.tolist(), baseline_sampled_failures=sum(r['baseline_sampled_slack_c'] < 0 for r in rows),
        commanded_water_l=float(5 * sum(q)), calibration_command_l=6.,
        independent=replays,
        scope='Synthetic nominal two-probe observations, finite parameter grid, known geometry and uniform initial 40 C. Target .1 C buffer plus .03 C floor reserve on selected models, not all-model buffer guarantee or global optimality. Conditional floating-point envelopes share the physical network, not interval certification or real-bath validation. Separate 6 L pulse trial; fill/reset costs unknown. Control is open loop and restarts at 40 C.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=180.)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; previous evidence must be preserved')
    if not np.isfinite(args.seconds) or args.seconds <= 0:
        parser.error('Time budget must be finite and positive')
    result = study(args.seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('accepted', 'compatible_models', 'commanded_water_l', 'elapsed_s')}))
    sys.exit(0 if result['accepted'] else 1)
