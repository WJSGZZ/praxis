"""One-dimensional diffusion (heat) equation by finite volumes, with conservation and convergence checks.

rho_c u_t = (k u_x)_x + s(x) on [0, L] (s in W/m^3). Boundary conditions per side: ('dirichlet', value), ('neumann', flux) with flux = -k u_x
into the domain positive, or ('robin', h, u_inf): -k u_x = h (u_inf - u) on the boundary. Time stepping is theta-implicit
(theta = 1 backward Euler, 0.5 Crank-Nicolson). A solver that runs is not yet right: check the observed order of convergence
against a known solution before trusting a result."""
from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.linalg import solve_banded


def _boundary(bc, k, dx, u_cell):
    """Return (a, b) so that the boundary flux INTO the first/last cell is a + b * u_cell."""
    kind = bc[0]
    if kind == 'dirichlet':
        g = 2 * k / dx          # half-cell conduction to the face value
        return g * bc[1], -g
    if kind == 'neumann':
        return float(bc[1]), 0.0
    if kind == 'robin':
        h, uinf = bc[1], bc[2]
        g = 1 / (1 / h + dx / (2 * k))   # film in series with half-cell conduction
        return g * uinf, -g
    raise ValueError("boundary kind must be 'dirichlet', 'neumann' or 'robin'")


def solve_diffusion(length: float, cells: int, k: float, rho_c: float, initial: Callable[[np.ndarray], np.ndarray], t_end: float, steps: int, *,
                    left=('neumann', 0.0), right=('neumann', 0.0), source: Callable[[np.ndarray], np.ndarray] | None = None, theta: float = 0.5) -> dict:
    """Cell-centred finite-volume solution. Returns x, u(t_end), and an energy account (stored change vs boundary flux plus sources)."""
    if min(length, cells, k, rho_c, t_end, steps) <= 0 or not 0.5 <= theta <= 1:
        raise ValueError('Positive sizes are required and theta must lie in [0.5, 1]')
    dx, dt = length / cells, t_end / steps
    x = (np.arange(cells) + .5) * dx
    u = np.asarray(initial(x), float).copy()
    s = np.zeros(cells) if source is None else np.asarray(source(x), float)
    c = k / dx ** 2
    # d u / dt = (c * (u[i-1] - 2 u[i] + u[i+1]) + boundary + s) / rho_c, assembled as banded A u + f
    lo, hi = np.full(cells, c), np.full(cells, c)
    diag = np.full(cells, -2 * c)
    fl, bl = _boundary(left, k, dx, None)
    fr, br = _boundary(right, k, dx, None)
    diag[0] += c + bl / dx
    diag[-1] += c + br / dx
    f = s.copy()
    f[0] += fl / dx
    f[-1] += fr / dx
    f = f / rho_c
    lo, hi, diag = lo / rho_c, hi / rho_c, diag / rho_c
    ab = np.zeros((3, cells))
    ab[0, 1:], ab[1], ab[2, :-1] = hi[:-1], diag, lo[1:]

    def apply(v):
        out = diag * v
        out[1:] += lo[1:] * v[:-1]
        out[:-1] += hi[:-1] * v[1:]
        return out

    lhs = -theta * dt * ab
    lhs[1] += 1.0
    stored0 = float(rho_c * dx * u.sum())
    boundary_energy = source_energy = 0.0
    for _ in range(steps):
        rhs = u + (1 - theta) * dt * (apply(u) + f)
        rhs += theta * dt * f
        new = solve_banded((1, 1), lhs, rhs)
        # energy bookkeeping with the same weights as the scheme
        uu = (1 - theta) * u + theta * new
        boundary_energy += dt * ((fl + bl * uu[0]) + (fr + br * uu[-1]))
        source_energy += dt * float((s * dx).sum())
        u = new
    stored = float(rho_c * dx * u.sum())
    return dict(x=x, u=u, dx=dx, dt=dt, stored_change=stored - stored0, boundary_energy=boundary_energy, source_energy=source_energy,
                energy_residual=stored - stored0 - boundary_energy - source_energy)


def convergence_study(solver: Callable[[int], np.ndarray], exact: np.ndarray | Callable[[np.ndarray], np.ndarray], cell_counts=(20, 40, 80, 160)) -> dict:
    """Max-norm errors of solver(cells) against an exact function of x, and the observed orders between successive refinements.

    solver(cells) returns (x, u). An observed order near the scheme's design order is evidence that the code solves the stated
    equation; an order near zero means the error is not coming from the mesh."""
    errors = []
    for n in cell_counts:
        x, u = solver(n)
        errors.append(float(np.max(np.abs(u - (exact(x) if callable(exact) else exact)))))
    orders = [float(np.log(errors[i] / errors[i + 1]) / np.log(cell_counts[i + 1] / cell_counts[i])) for i in range(len(errors) - 1)]
    return dict(cells=list(cell_counts), errors=errors, observed_orders=orders)


def grid_convergence_index(f_fine: float, f_medium: float, f_coarse: float, refinement_ratio: float, *, safety_factor: float = 1.25) -> dict:
    """Observed order, Richardson-extrapolated value and grid convergence index from three systematically refined solutions (Roache).

    Needs monotone convergence: (f_coarse - f_medium) and (f_medium - f_fine) of the same sign. The GCI is an error band on the fine-grid
    value, not a bound; a safety factor of 1.25 is conventional for three grids."""
    r = float(refinement_ratio)
    d21, d32 = f_medium - f_fine, f_coarse - f_medium
    if r <= 1 or d21 == 0 or d32 == 0 or d21 * d32 < 0:
        raise ValueError('Need refinement_ratio > 1 and monotone, non-zero differences between the three solutions')
    p = float(np.log(d32 / d21) / np.log(r))
    if p <= 0:
        raise ValueError('The solutions are not converging (observed order <= 0)')
    extrapolated = f_fine + (f_fine - f_medium) / (r ** p - 1)
    rel = abs((f_medium - f_fine) / f_fine) if f_fine != 0 else abs(f_medium - f_fine)
    return dict(observed_order=p, extrapolated=float(extrapolated), gci_fine=float(safety_factor * rel / (r ** p - 1)),
                note='Error band on the fine-grid value assuming the asymptotic range; check that the three grids are in it.')
