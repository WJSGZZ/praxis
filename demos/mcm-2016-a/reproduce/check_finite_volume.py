"""Verify FV diffusion and inlet transport against independent analytic cases.

These cases check numerical implementation, not bath mixing or flow physics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm_multiply
from scipy.special import gammainc

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'code'))
import model


def verification():
    started = time.monotonic()
    p = {**model.BASE, 'body_volume': 0., 'h_body': 0.,
         'h_surface': 0., 'h_wall': 0.}
    dims = np.array([p['L'], p['W'], p['H']])
    decay = p['D'] * np.pi**2 * sum(dims**-2)
    rows = []
    for grid in [(4, 2, 2), (8, 4, 4), (16, 8, 8), (24, 12, 12)]:
        net = model.network(p, grid)
        spacing = dims / np.array(grid)
        # Cell averages, not centre-point values of the continuum solution.
        mode = np.prod(np.cos(np.pi * net['xyz'] / dims)
                       * np.sinc(spacing / (2 * dims)), axis=1)
        initial = 40. + mode
        numeric = expm_multiply(csr_matrix(net['G'] / net['cap'][:, None]) * 5., initial)
        exact = 40. + mode * np.exp(-decay * 5.)
        discrete_decay = 4 * p['D'] * sum(
            np.sin(np.pi / (2 * np.array(grid)))**2 / spacing**2)
        # Independent Neumann cosine eigenvalue also checks every FV face.
        semidiscrete = 40. + mode * np.exp(-discrete_decay * 5.)
        rows.append(dict(grid=list(grid),
            rms_error_c=float(np.sqrt(np.mean((numeric - exact)**2))),
            max_error_c=float(np.max(np.abs(numeric - exact))),
            semidiscrete_max_error_c=float(np.max(np.abs(numeric - semidiscrete))),
            eigen_residual_c_per_s=float(np.max(np.abs(
                net['G'] @ mode / net['cap'] + discrete_decay * mode))),
            relative_energy_drift=float(abs((numeric - initial) @ net['cap'])
                                        / abs(initial @ net['cap']))))
    orders = [float(np.log(rows[i]['rms_error_c'] / rows[i+1]['rms_error_c'])
                    / np.log(rows[i+1]['grid'][0] / rows[i]['grid'][0]))
              for i in range(len(rows)-1)]
    # A coarse grid need not be in the asymptotic range; retain all orders.
    diffusion_ok = (1.8 < orders[-1] < 2.2
        and all(rows[i+1]['rms_error_c'] < rows[i]['rms_error_c'] for i in range(len(rows)-1))
        and all(r['semidiscrete_max_error_c'] < 1e-10
                and r['eigen_residual_c_per_s'] < 1e-11
                and r['relative_energy_drift'] < 1e-11 for r in rows))

    # D=0, no loss/body: the upwind inlet path is a series of equal-volume
    # stirred cells. Its exact step response is a Poisson-tail/Erlang CDF.
    adv_p = {**p, 'D': 0.}
    net = model.network(adv_p)
    nx, ny, nz = net['grid']
    path = [(i*ny + ny//2)*nz + nz-1 for i in range(nx)]
    q = 1. / 60000.  # 1 L/min in m3/s
    rate = q / net['vol'][path[0]]
    times = [30., 120., 300.]
    adv_rows = []
    for seconds in times:
        numeric = expm_multiply(model.system(adv_p, net, q) * seconds,
                                 np.r_[np.full(len(net['cap']), 40.), 1.])[:-1]
        exact = np.full(len(net['cap']), 40.)
        exact[path] += 10. * gammainc(np.arange(1, nx+1), rate*seconds)
        adv_rows.append(dict(time_s=seconds,
            max_error_c=float(np.max(np.abs(numeric-exact))),
            inlet_temp_c=float(numeric[path[0]]),
            outlet_temp_c=float(numeric[path[-1]])))
    advection_ok = all(r['max_error_c'] < 1e-10 for r in adv_rows)
    sources = ['check_finite_volume.py', 'code/model.py']
    return dict(status='completed', accepted=bool(diffusion_ok and advection_ok),
        diffusion_rows=rows, observed_orders=orders, advection_rows=adv_rows,
        elapsed_s=time.monotonic()-started,
        source_sha256={s: hashlib.sha256((HERE/s).read_bytes()).hexdigest() for s in sources},
        scope='Code verification: empty insulated constant-D Cartesian diffusion, and zero-D inlet-path step response. No verification of occupied-cell continuum convergence, inferred flow, turbulence or real baths.',
        method_sources=['https://pages.nist.gov/fipy/en/3.99/numerical/index.html',
                        'https://www.grc.nasa.gov/WWW/wind/valid/tutorial/verassess.html',
                        'https://www.grc.nasa.gov/WWW/wind/valid/tutorial/valassess.html'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; keep previous evidence')
    result = verification()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['accepted', 'observed_orders', 'advection_rows', 'elapsed_s']}, indent=2))
