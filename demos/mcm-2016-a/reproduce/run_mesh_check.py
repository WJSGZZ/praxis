"""Select the least-water archived candidate passing independent mesh replay.

No optimization is performed. Every best/buffer_price candidate is replayed on
three meshes, with RK45 restarted at each switch and continuous envelopes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'code'))
import model
from policy_validation import replay_schedule

GRIDS = ((8, 4, 3), (12, 6, 4), (16, 8, 6))


def validate_candidates(extended):
    p = extended['parameters']
    control = extended['control']
    candidates = [('best', control['best'])] + [
        (f'buffer_price[{i}]', candidate) for i, candidate in enumerate(control['buffer_price'])]
    networks = {grid: model.network(p, grid) for grid in GRIDS}
    diagnostics = []
    for source, candidate in candidates:
        record = dict(source=source, segments=None, segment_s=None,
                      flow_lpm=None, water_l=None, archived_water_l=None,
                      buffer_c=candidate.get('buffer_c') if isinstance(candidate, dict) else None,
                      accepted=False, meshes=[])
        try:
            if not isinstance(candidate, dict) or candidate.get('flow_lpm') is None or candidate.get('water_l') is None:
                record['error'] = dict(type='no_candidate', message='Archived candidate has no flow or water result')
                diagnostics.append(record)
                continue
            flows = candidate['flow_lpm']
            duration = p['horizon']/len(flows)
            water = float(np.sum(flows)*duration/60)
            record.update(segments=len(flows), segment_s=duration,
                          flow_lpm=flows, water_l=water, archived_water_l=candidate['water_l'])
            meshes = [replay_schedule(p, networks[grid], flows, grid) for grid in GRIDS]
            accounting = bool(np.isfinite(water) and abs(water-candidate['water_l']) < 1e-7
                and candidate.get('segments', len(flows)) == len(flows)
                and abs(candidate.get('segment_s', duration)-duration) < 1e-9)
            record.update(meshes=meshes, water_accounting_passed=accounting,
                accepted=accounting and all(m['sampled_passed'] and m['continuous_passed'] for m in meshes))
        except Exception as exc:
            record.update(accepted=False, error=dict(type=type(exc).__name__, message=str(exc)), meshes=[])
        diagnostics.append(record)
    passing = [candidate for candidate in diagnostics if candidate['accepted']]
    selected = min(passing, key=lambda candidate: candidate['water_l']) if passing else None
    raw = diagnostics[0]
    out = dict(schedule_replayed={key: raw[key] for key in ('segments', 'flow_lpm', 'water_l', 'meshes')},
        accepted_schedule=None, accepted_independent=None, candidate_diagnostics=diagnostics,
        scope='Lowest water among listed archived candidates passing all three mesh checks; not a global optimum or infeasibility theorem')
    if selected:
        meshes = selected['meshes']
        metrics = dict(min_temp=min(m['min_temp'] for m in meshes), max_temp=max(m['max_temp'] for m in meshes),
                       max_span=max(m['max_span'] for m in meshes))
        out['accepted_schedule'] = {key: selected[key] for key in ('source', 'segments', 'segment_s', 'flow_lpm', 'water_l', 'buffer_c')}
        out['accepted_schedule'].update(metrics, feasible=True)
        out['accepted_independent'] = dict(**metrics, meshes=meshes, passed=True,
            lower_temperature_bound_c=min(m['lower_temperature_bound_c'] for m in meshes),
            upper_temperature_bound_c=max(m['upper_temperature_bound_c'] for m in meshes),
            span_upper_bound_c=max(m['span_upper_bound_c'] for m in meshes),
            method='Independently assembled heat-flow RHS and RK45; per-interval contractive envelopes within each constant-control segment',
            numerical_tolerance_c=.002, continuous_limit_tolerance_c=0., integration_allowance_c=2e-6,
            scope='Same network coefficients; no empirical physical validation or interval-arithmetic proof')
    out['checks'] = [dict(name='accepted_candidate_exists', passed=bool(selected),
                         evidence='Every archived best/buffer_price candidate replayed; none accepted means only this candidate set failed'),
        dict(name='accepted_candidate_passes_three_meshes_and_continuous_envelopes', passed=bool(selected),
             evidence='All selected candidate mesh and segment records must pass; rejected candidate diagnostics are retained')]
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--extended', type=Path, default=HERE/'reproduced/extended.json')
    parser.add_argument('--output', type=Path, default=HERE/'reproduced/mesh_check.json')
    args = parser.parse_args()
    try:
        content = args.extended.read_bytes()
        out = validate_candidates(json.loads(content))
        out['input_sha256'] = hashlib.sha256(content).hexdigest()
        out['source_sha256'] = {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                               for name in ('run_mesh_check.py', 'code/model.py', 'code/policy_validation.py')}
    except Exception as exc:
        out = dict(accepted_schedule=None, accepted_independent=None, candidate_diagnostics=[],
                   checks=[dict(name='validator_execution', passed=False,
                                evidence=f'{type(exc).__name__}: {exc}')])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1)+'\n')
    passed = all(check['passed'] for check in out['checks'])
    print(json.dumps(dict(passed=passed, accepted_schedule=out['accepted_schedule'], output=str(args.output))))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
