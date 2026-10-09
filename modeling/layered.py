"""Heat conduction through layers in series (one dimension): a finite-volume solver and an independent Laplace-transform solution.

Layers run from the left surface to the right surface, each with thickness d [m], conductivity k [W/(m K)] and volumetric heat
capacity rho_c [J/(m^3 K)]; contact between layers is perfect. Boundary conditions: ('robin', h, T_env) with film coefficient h
[W/(m^2 K)] and ambient temperature T_env, or ('dirichlet', T). The initial temperature is uniform.

The two solvers share nothing but the physics, so agreement between them is evidence that the model is solved as stated; the
Laplace solution has no spatial discretisation at all. Neither says the physical model (1-D, constant properties, perfect contacts,
no air-layer convection or radiation) is right."""
from __future__ import annotations

from typing import Sequence

import mpmath as mp
import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import diags


def _check(layers):
    if not layers:
        raise ValueError('At least one layer is required')
    for layer in layers:
        if not np.isfinite([layer['thickness'], layer['k'], layer['rho_c']]).all() or min(layer['thickness'], layer['k'], layer['rho_c']) <= 0:
            raise ValueError('Thickness, conductivity and heat capacity must be positive')


def _bc(spec, name):
    if not spec or not np.isfinite(spec[1:]).all():
        raise ValueError(f'{name} boundary values must be finite')
    if spec[0] == 'robin' and len(spec) == 3 and spec[1] > 0:
        return 'robin', float(spec[1]), float(spec[2])
    if spec[0] == 'dirichlet' and len(spec) == 2:
        return 'dirichlet', None, float(spec[1])
    raise ValueError(f"{name} must be ['robin', h, T_env] with h > 0 or ['dirichlet', T]")


def solve_layered(layers: Sequence[dict], *, t_end: float, t_initial: float, left, right, times: Sequence[float] | None = None,
                  cells_per_layer: int | Sequence[int] = 20, rtol: float = 1e-8, atol: float = 1e-8) -> dict:
    """Method-of-lines finite volumes with a stiff adaptive integrator (Radau): the only discretisation error left is spatial.

    A step change of a surface temperature at t = 0 is singular, so near the start the error is first order in the cell size; smooth
    (Robin) boundaries give second order. Returns the times, the temperatures of the two outer surfaces and of every interface (interpolated with flux continuity), and the
    cell centres and cell temperatures at the final time."""
    _check(layers)
    lbc, rbc = _bc(left, 'left'), _bc(right, 'right')
    counts = [cells_per_layer] * len(layers) if isinstance(cells_per_layer, int) else list(cells_per_layer)
    if len(counts) != len(layers) or any(isinstance(c, bool) or not isinstance(c, (int, np.integer)) or c <= 0 for c in counts):
        raise ValueError('One positive integer cell count per layer is required')
    if not np.isfinite([t_end, t_initial, rtol, atol]).all() or t_end <= 0 or min(rtol, atol) <= 0:
        raise ValueError('Finite initial temperature, positive duration and tolerances required')
    dx, k, rc = [], [], []
    for layer, n in zip(layers, counts):
        dx += [layer['thickness'] / n] * n
        k += [layer['k']] * n
        rc += [layer['rho_c']] * n
    dx, k, rc = map(np.asarray, (dx, k, rc))
    n = len(dx)
    g = 1.0 / (dx[:-1] / (2 * k[:-1]) + dx[1:] / (2 * k[1:]))          # face conductance, W/(m^2 K)
    gl = 1.0 / (1.0 / lbc[1] + dx[0] / (2 * k[0])) if lbc[0] == 'robin' else 2 * k[0] / dx[0]
    gr = 1.0 / (1.0 / rbc[1] + dx[-1] / (2 * k[-1])) if rbc[0] == 'robin' else 2 * k[-1] / dx[-1]
    lower, upper = g / (rc[1:] * dx[1:]), g / (rc[:-1] * dx[:-1])
    main = np.zeros(n)
    main[:-1] -= g / (rc[:-1] * dx[:-1])
    main[1:] -= g / (rc[1:] * dx[1:])
    main[0] -= gl / (rc[0] * dx[0])
    main[-1] -= gr / (rc[-1] * dx[-1])
    A = diags([lower, main, upper], [-1, 0, 1], format='csc')
    forcing = np.zeros(n)
    forcing[0] = gl * lbc[2] / (rc[0] * dx[0])
    forcing[-1] += gr * rbc[2] / (rc[-1] * dx[-1])
    grid = np.linspace(0.0, t_end, 61) if times is None else np.asarray(times, float)
    if grid.ndim != 1 or not len(grid) or not np.isfinite(grid).all() or grid[0] < 0 or grid[-1] <= 0 or (np.diff(grid) <= 0).any() or not np.isclose(grid[-1], t_end):
        raise ValueError('times must increase within [0, t_end] and end at t_end')
    sol = solve_ivp(lambda t, T: A @ T + forcing, (0.0, float(grid[-1])), np.full(n, float(t_initial)), method='Radau', jac=A, t_eval=grid, rtol=rtol, atol=atol)
    if not sol.success:
        raise RuntimeError(sol.message)
    T = sol.y.T                                                           # (time, cell)
    edges = np.cumsum([0.0] + [layer['thickness'] for layer in layers])
    cell_edges = np.cumsum(np.r_[0.0, dx])
    interface_cells = np.cumsum(counts)[:-1]
    # interface temperature from flux continuity between neighbouring centres
    interfaces = [(k[i - 1] / dx[i - 1] * T[:, i - 1] + k[i] / dx[i] * T[:, i]) / (k[i - 1] / dx[i - 1] + k[i] / dx[i]) for i in interface_cells]
    if lbc[0] == 'robin':
        flux_in = lbc[1] * (lbc[2] - T[:, 0]) / (1 + lbc[1] * dx[0] / (2 * k[0]))
        surface_left = lbc[2] - flux_in / lbc[1]
    else:
        surface_left = np.full(len(T), lbc[2])
    if rbc[0] == 'robin':
        flux_out = rbc[1] * (T[:, -1] - rbc[2]) / (1 + rbc[1] * dx[-1] / (2 * k[-1]))
        surface_right = rbc[2] + flux_out / rbc[1]
    else:
        surface_right = np.full(len(T), rbc[2])
    return dict(times=sol.t.tolist(), surface_left=surface_left.tolist(), surface_right=surface_right.tolist(), interfaces=[i.tolist() for i in interfaces],
                interface_positions=[float(e) for e in edges[1:-1]], cell_centres=((cell_edges[:-1] + cell_edges[1:]) / 2).tolist(), final_cells=T[-1].tolist(),
                cells=int(n), integrator='Radau', note='Spatial discretisation is second order; check the observed order on 2-3 meshes.')


def laplace_layered(layers: Sequence[dict], *, times: Sequence[float], t_initial: float, left, right, dps: int = 25) -> dict:
    """Semi-analytic solution by transfer matrices in the Laplace domain, inverted numerically (Talbot) at the requested times.

    Returns the surface temperatures and the interface temperatures. There is no mesh and no time step: use it as the independent
    solution that a finite-volume or finite-difference result must match."""
    _check(layers)
    lbc, rbc = _bc(left, 'left'), _bc(right, 'right')
    mp.mp.dps = dps
    h1 = mp.mpf(lbc[1]) if lbc[0] == 'robin' else None
    h2 = mp.mpf(rbc[1]) if rbc[0] == 'robin' else None
    u1 = mp.mpf(lbc[2] - t_initial)
    u2 = mp.mpf(rbc[2] - t_initial)

    def layer_matrix(layer, s):
        alpha = mp.mpf(layer['k']) / mp.mpf(layer['rho_c'])
        lam = mp.sqrt(s / alpha)
        d, kk = mp.mpf(layer['thickness']), mp.mpf(layer['k'])
        ch, sh = mp.cosh(lam * d), mp.sinh(lam * d)
        return mp.matrix([[ch, -sh / (kk * lam)], [-kk * lam * sh, ch]])

    def fields(s):
        """Transform of the temperature rise at the left surface, at every interface and at the right surface."""
        mats = [layer_matrix(layer, s) for layer in layers]
        total = mp.eye(2)
        for m in mats:
            total = m * total
        a, b, c, d = total[0, 0], total[0, 1], total[1, 0], total[1, 1]
        # left condition: q0 = h1 (U1 - u0) with U1 = u1/s (Robin) or u0 = u1/s (Dirichlet); right: q_L = h2 (u_L - U2) or u_L = u2/s
        U1, U2 = u1 / s, u2 / s
        if h1 is not None and h2 is not None:
            u0 = (h2 * (b * h1 * U1 - U2) - d * h1 * U1) / (c - d * h1 - h2 * (a - b * h1))
            q0 = h1 * (U1 - u0)
        elif h1 is not None:                                   # Robin left, Dirichlet right: a u0 + b q0 = U2
            u0 = (U2 - b * h1 * U1) / (a - b * h1)
            q0 = h1 * (U1 - u0)
        elif h2 is not None:                                   # Dirichlet left, Robin right
            u0 = U1
            q0 = (h2 * (a * u0 - U2) - c * u0) / (d - h2 * b)
        else:
            u0 = U1
            q0 = (U2 - a * u0) / b
        state = mp.matrix([[u0], [q0]])
        values = [u0]
        for m in mats:
            state = m * state
            values.append(state[0])
        return values

    cache: dict = {}

    def cached(s):
        key = (str(s.real), str(s.imag))
        if key not in cache:
            cache[key] = fields(s)
        return cache[key]

    n_points = len(layers) + 1
    series = [[] for _ in range(n_points)]
    for t in times:
        t = mp.mpf(t)
        for j in range(n_points):
            f = (lambda s, j=j: cached(s)[j])
            series[j].append(float(mp.invertlaplace(f, t, method='talbot')) + t_initial)
    return dict(times=[float(t) for t in times], surface_left=series[0], surface_right=series[-1], interfaces=series[1:-1],
                note='Talbot inversion of the transfer-matrix solution; accurate for t > 0, no discretisation.')
