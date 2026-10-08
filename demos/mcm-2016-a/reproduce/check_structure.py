"""Replay archived policies under explicit, uncalibrated structural alternatives.

No policy search is repeated. Geometry/conductances are shared with model.py;
the heat-flow RHS and integrated energy accounting are assembled here.
Finite body capacity is an effective contact reservoir, not a physiological model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import csr_matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'code'))
import model


def replay(p, net, flows, route='surface', body_capacity=None, sample_s=1.):
    nx, ny, nz = net['grid']
    idx = lambda i, j, k: (i*ny+j)*nz+k
    path = [idx(i, ny//2, nz-1) for i in range(nx)]
    if route == 'deep':
        # Same inlet/outlet; descend at one end, traverse the bottom, rise at
        # the other. Consecutive cells share a face; every edge carries q.
        path = ([idx(0, ny//2, k) for k in range(nz-1, -1, -1)]
                + [idx(i, ny//2, 0) for i in range(1, nx)]
                + [idx(nx-1, ny//2, k) for k in range(1, nz)])
    elif route != 'surface':
        raise ValueError('Unknown route')
    cap, ha, hb = (np.asarray(net[k]) for k in ('cap', 'ha', 'hb'))
    g = csr_matrix(net['G'])
    n = len(cap)
    state = np.r_[np.full(n, p['initial']), p['body_temp'], 0.]
    all_t, all_y, residuals = [], [], []
    seconds = p['horizon']/len(flows)
    for segment, flow in enumerate(flows):
        start, end = segment*seconds, (segment+1)*seconds
        mass_heat = p['rho']*p['cp']*float(flow)/60000.
        def rhs(t, y):
            water, body = y[:n], y[n]
            to_body = hb*(water-body)
            environmental = ha*(p['air_temp']-water)
            rate = g@water + environmental-to_body
            upstream = p['inlet_temp']
            for cell in path:
                rate[cell] += mass_heat*(upstream-water[cell])
                upstream = water[cell]
            body_rate = to_body.sum()/body_capacity if body_capacity is not None else 0.
            external = environmental.sum()+mass_heat*(p['inlet_temp']-water[path[-1]])
            if body_capacity is None:
                external -= to_body.sum()
            residuals.append(abs(rate.sum()+(body_capacity or 0.)*body_rate-external))
            return np.r_[rate/cap, body_rate, external]
        points = np.linspace(start, end, int(np.ceil(seconds/sample_s))+1)
        solution = solve_ivp(rhs, (start, end), state, t_eval=points,
                             rtol=2e-9, atol=2e-10, max_step=sample_s)
        if not solution.success:
            raise RuntimeError(solution.message)
        state = solution.y[:, -1]
        all_t.extend(points if segment == 0 else points[1:])
        all_y.extend(solution.y.T if segment == 0 else solution.y.T[1:])
    y = np.asarray(all_y)
    water = y[:, :n]
    visible = water[:, net['region']]
    minimum, maximum = float(water.min()), float(visible.max())
    spread = float(np.ptp(visible, axis=1).max())
    stored = ((water[-1]-p['initial'])@cap
              + (body_capacity or 0.)*(state[n]-p['body_temp']))
    return dict(route=route, body_capacity_j_per_k=body_capacity,
                water_l=float(np.sum(flows)*seconds/60.),
                min_temp=minimum, max_temp=maximum, max_span=spread,
                sampled_passed=minimum >= p['floor'] and maximum <= p['ceiling'] and spread <= p['span'],
                final_body_temp_c=float(state[n]),
                instantaneous_balance_residual_w=max(residuals),
                integrated_balance_residual_j=float(abs(stored-state[-1])),
                sample_s=sample_s, path=path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    ref = HERE/'reference'
    base = json.loads((ref/'results.json').read_text())
    mesh = json.loads((ref/'mesh_check.json').read_text())
    p = base['parameters']
    net = model.network(p)
    policies = {'constant': [base['policy']['flow_lpm']],
                'scheduled': mesh['accepted_schedule']['flow_lpm']}
    rows = []
    for label, flows in policies.items():
        for route, capacity in [('surface', None), ('surface', 73000*3.47),
                                ('deep', None), ('deep', 73000*3.47)]:
            result = replay(p, net, flows, route, capacity)
            # A second time resolution checks the new alternatives only; it
            # does not rerun optimization or substitute for mesh validation.
            finer = replay(p, net, flows, route, capacity, sample_s=.5)
            delta = max(abs(result[k]-finer[k]) for k in ('min_temp', 'max_temp', 'max_span', 'final_body_temp_c'))
            assert delta < 2e-4, delta
            assert result['instantaneous_balance_residual_w'] < 1e-6
            assert result['integrated_balance_residual_j'] < .1
            result.update(policy=label, step_check_delta_c=delta)
            rows.append(result)
    for label in policies:
        actual = next(x for x in rows if x['policy']==label and x['route']=='surface' and x['body_capacity_j_per_k'] is None)
        expected = base['policy'] if label == 'constant' else mesh['accepted_independent']['meshes'][0]
        assert max(abs(actual[k]-expected[k]) for k in ('min_temp', 'max_temp', 'max_span')) < 2e-4
    inputs = [ref/'results.json', ref/'mesh_check.json', HERE/'code/model.py', Path(__file__)]
    receipt = dict(grid=net['grid'], body_capacity_scenario='73 kg times 3470 J/(kg K), initial effective contact node 34 C; no thermoregulation or empirical calibration',
                   scope='Fixed archived-policy replay on one spatial mesh; time-resolution and energy checks only. Sampled acceptance is not continuous or empirical certification; no re-optimization, no claim that the old energy lower bound applies to the finite-body alternatives.',
                   input_sha256={str(f.relative_to(HERE)): hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}, rows=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
