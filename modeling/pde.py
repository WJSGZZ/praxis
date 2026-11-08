"""One-dimensional diffusion (heat) equation by finite volumes, with conservation and convergence checks.

rho_c u_t = (k u_x)_x + s(x) on [0, L] (s in W/m^3). Boundary conditions per side: ('dirichlet', value), ('neumann', flux) with flux = -k u_x
into the domain positive, or ('robin', h, u_inf): -k u_x = h (u_inf - u) on the boundary. Time stepping is theta-implicit
(theta = 1 backward Euler, 0.5 Crank-Nicolson). A solver that runs is not yet right: check the observed order of convergence
against a known solution before trusting a result."""
from __future__ import annotations

from fractions import Fraction
import math
from typing import Callable

import numpy as np
from scipy.linalg import solve_banded


def _boundary(bc, k, dx, u_cell):
    """Return (a, b) so that the boundary flux INTO the first/last cell is a + b * u_cell."""
    if not isinstance(bc, (list, tuple)) or not bc:
        raise ValueError('A boundary must be a nonempty boundary specification')
    kind = bc[0]
    expected = 3 if kind == 'robin' else 2
    if len(bc) != expected or not np.isfinite(bc[1:]).all() or kind == 'robin' and bc[1] <= 0:
        raise ValueError('Boundary values must be finite; Robin film coefficient must be positive')
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
    if (not np.isfinite([length, k, rho_c, t_end, theta]).all()
            or any(isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) for value in (cells, steps))
            or min(length, cells, k, rho_c, t_end, steps) <= 0 or not 0.5 <= theta <= 1):
        raise ValueError('Positive sizes are required and theta must lie in [0.5, 1]')
    dx, dt = length / cells, t_end / steps
    x = (np.arange(cells) + .5) * dx
    u = np.asarray(initial(x), float).copy()
    s = np.zeros(cells) if source is None else np.asarray(source(x), float)
    if u.shape != x.shape or s.shape != x.shape or not np.isfinite(u).all() or not np.isfinite(s).all():
        raise ValueError('initial and source must return one finite value per cell; broadcasting is not allowed')
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


def values_at(result: dict, points, *, left: float | None = None, right: float | None = None) -> list[float]:
    """Linear interpolation of a cell-centred solution at points. The cell centres exclude the ends, so give the boundary values (left, right)
    for Dirichlet ends; without them, points outside the first and last centre are rejected."""
    x, u = np.asarray(result['x'], float), np.asarray(result['u'], float)
    if x.ndim != 1 or not len(x) or u.shape != x.shape or not np.isfinite(x).all() or not np.isfinite(u).all() or (np.diff(x) <= 0).any():
        raise ValueError('Interpolation needs matching finite values at strictly increasing cell centres')
    if any(value is not None and not np.isfinite(value) for value in (left, right)):
        raise ValueError('Boundary interpolation values must be finite')
    length = float(x[-1] + x[0])
    xs, us = list(x), list(u)
    if left is not None:
        xs, us = [0.0] + xs, [left] + us
    if right is not None:
        xs, us = xs + [length], us + [right]
    pts = np.asarray(points, float)
    if not np.isfinite(pts).all():
        raise ValueError('Interpolation points must be finite')
    if (pts < xs[0] - 1e-12).any() or (pts > xs[-1] + 1e-12).any():
        raise ValueError('A point lies outside the interpolation range; pass the boundary values left/right')
    return np.interp(pts, xs, us).tolist()


def convergence_study(solver: Callable[[int], np.ndarray], exact: np.ndarray | Callable[[np.ndarray], np.ndarray], cell_counts=(20, 40, 80, 160)) -> dict:
    """Max-norm errors of solver(cells) against an exact function of x, and the observed orders between successive refinements.

    solver(cells) returns (x, u). An observed order near the scheme's design order is evidence that the code solves the stated
    equation; an order near zero means the error is not coming from the mesh. Refine space and time separately (a fine time step while
    refining the mesh, then a fine mesh while refining the step) or tie dt to dx for a second-order scheme; point values read off by
    interpolation add their own error, so use a mesh point or a higher-order interpolant when the order looks wrong."""
    cell_counts = tuple(cell_counts)
    if (not cell_counts or any(type(n) is bool or not isinstance(n, (int, np.integer))
                               or n <= 0 for n in cell_counts)
            or any(a >= b for a, b in zip(cell_counts, cell_counts[1:]))):
        raise ValueError('Use strictly increasing positive integer cell counts')

    errors = []
    for n in cell_counts:
        x, u = solver(n)
        x = np.asarray(x, dtype=float)
        if x.ndim != 1 or not x.size or not np.isfinite(x).all():
            raise ValueError('Expected a finite one-dimensional grid')
        u = np.asarray(u, dtype=float)
        ref = np.asarray(exact(x) if callable(exact) else exact, dtype=float)
        shapes = {(x.size,), (x.size, 1), (1, x.size)}
        if u.shape not in shapes or (ref.ndim and ref.shape not in shapes):
            raise ValueError('Each value must correspond to one grid point')
        error = float(np.max(np.abs(u.reshape(-1) - ref.reshape(-1))))
        if not math.isfinite(error):
            raise ValueError('Nonfinite max-norm error')
        errors.append(error)
    orders = [(math.log(a) - math.log(b)) / math.log(n2 / n1) if min(a, b) > 0 else None
              for a, b, n1, n2 in zip(errors, errors[1:], cell_counts, cell_counts[1:])]
    return dict(cells=list(cell_counts), errors=errors, observed_orders=orders,
                note='An order is undefined when either measured error is zero.')


def grid_convergence_index(f_fine: float, f_medium: float, f_coarse: float, refinement_ratio: float, *,
                           safety_factor: float = 1.25, reference_scale: float | None = None) -> dict:
    """Richardson estimate from three same-quantity grids of fixed refinement ratio.

    gci_fine is a fraction, normalized by the magnitude of the fine value or an
    explicitly supplied positive scale in the same units. gci_fine_abs has the
    units of the input quantity. Both assume a leading power-law error.
    """
    r = float(refinement_ratio)
    values = [f_fine, f_medium, f_coarse, r, safety_factor]
    if not np.isfinite(values).all() or r <= 1 or safety_factor <= 0:
        raise ValueError('Finite values, refinement ratio > 1 and positive safety factor required')
    if reference_scale is not None and (not math.isfinite(reference_scale) or reference_scale <= 0):
        raise ValueError('reference_scale must be positive, finite and in the units of the grid values')

    # Three scalars suffice. Rational arithmetic on their represented values
    # avoids overflow in products of differences and cancellation in r**p - 1.
    fine, middle, coarse = (Fraction(float(v)) for v in values[:3])
    d21, d32 = middle - fine, coarse - middle
    if not d21 or not d32 or (d21 > 0) != (d32 > 0):
        raise ValueError('Need monotone, non-zero differences between the three solutions')
    excess = d32 / d21 - 1
    if excess <= 0:
        raise ValueError('The solutions are not converging (observed order <= 0)')
    ratio = excess + 1
    log_ratio = (math.log1p(float(excess)) if excess < 1 else
                 math.log(ratio.numerator) - math.log(ratio.denominator))
    order = log_ratio / math.log(r)
    correction = -d21 / excess
    absolute = Fraction(float(safety_factor)) * abs(correction)
    scale = abs(fine) if reference_scale is None else Fraction(float(reference_scale))
    try:
        limit = float(fine + correction)
        band = float(absolute)
        relative = float(absolute / scale) if scale else None
    except OverflowError as exc:
        raise ValueError('Grid estimate exceeds the representable output range') from exc
    return dict(observed_order=order, extrapolated=limit, gci_fine=relative, gci_fine_abs=band,
                normalization_scale=float(scale), relative_status='defined' if scale else 'zero_reference',
                note='gci_fine is a fraction; gci_fine_abs is in input units. Three grids fit a leading '
                     'error term; they do not establish the asymptotic regime or a rigorous error bound.')
