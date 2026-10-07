import numpy as np
import pytest

from modeling import pde


def test_decaying_sine_matches_exact_solution_with_second_order_convergence():
    L, k, rc, t_end = 1.0, 2.0, 4.0, 0.3

    def exact(x):
        return np.exp(-k * np.pi ** 2 * t_end / (rc * L ** 2)) * np.sin(np.pi * x / L)

    def run(n):
        r = pde.solve_diffusion(L, n, k, rc, lambda x: np.sin(np.pi * x / L), t_end, 4 * n, left=('dirichlet', 0.), right=('dirichlet', 0.), theta=.5)
        return r['x'], r['u']

    study = pde.convergence_study(run, exact, (20, 40, 80, 160))
    assert all(1.8 < o < 2.3 for o in study['observed_orders']), study
    assert study['errors'][-1] < 2e-5


def test_backward_euler_is_first_order_in_time():
    L, k, rc, t_end = 1.0, 1.0, 1.0, 0.1
    exact = lambda x: np.exp(-np.pi ** 2 * t_end) * np.sin(np.pi * x)
    err = []
    for steps in (10, 20, 40):
        r = pde.solve_diffusion(L, 400, k, rc, lambda x: np.sin(np.pi * x), t_end, steps, left=('dirichlet', 0.), right=('dirichlet', 0.), theta=1.0)
        err.append(float(np.max(np.abs(r['u'] - exact(r['x'])))))
    assert 0.8 < np.log2(err[0] / err[1]) < 1.3 and 0.8 < np.log2(err[1] / err[2]) < 1.3


def test_energy_is_conserved_with_insulated_ends_and_accounted_with_flux_and_source():
    x0 = lambda x: 1 + np.exp(-((x - .3) / .1) ** 2)
    r = pde.solve_diffusion(1.0, 100, 1.0, 1.0, x0, .2, 200)
    assert abs(r['stored_change']) < 1e-12 and abs(r['energy_residual']) < 1e-12
    r = pde.solve_diffusion(1.0, 100, 1.0, 1.0, x0, .2, 200, left=('neumann', 3.0), right=('robin', 5.0, 0.0), source=lambda x: 2 * x)
    assert abs(r['energy_residual']) < 1e-10 and abs(r['stored_change']) > 0.1


def test_steady_state_with_source_and_robin_boundary_agree_with_closed_form():
    L, k, s = 1.0, 2.0, 10.0
    r = pde.solve_diffusion(L, 200, k, 1.0, lambda x: 0 * x, 5.0, 500, left=('dirichlet', 0.), right=('dirichlet', 0.), source=lambda x: s + 0 * x, theta=1.0)
    exact = s * r['x'] * (L - r['x']) / (2 * k)
    assert np.max(np.abs(r['u'] - exact)) < 1e-4
    # insulated left, convective right (h, u_inf): steady u(x) = u_inf + s (L^2 - x^2)/(2k) + s L / h
    h, uinf = 4.0, 3.0
    r = pde.solve_diffusion(L, 400, k, 1.0, lambda x: 0 * x + uinf, 20.0, 400, left=('neumann', 0.), right=('robin', h, uinf), source=lambda x: s + 0 * x, theta=1.0)
    exact = uinf + s * (L ** 2 - r['x'] ** 2) / (2 * k) + s * L / h
    assert np.max(np.abs(r['u'] - exact)) < 2e-3


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        pde.solve_diffusion(1, 10, 1, 1, lambda x: x, 1, 10, theta=.3)
    with pytest.raises(ValueError):
        pde.solve_diffusion(1, 10, 1, 1, lambda x: x, 1, 10, left=('weird', 1))


def test_grid_convergence_index_recovers_a_planted_order_and_limit():
    f0, C, p = 3.0, 0.8, 2.0
    h = [0.1, 0.2, 0.4]
    fine, med, coarse = (f0 + C * x ** p for x in h)
    r = pde.grid_convergence_index(fine, med, coarse, 2.0)
    assert abs(r['observed_order'] - 2) < 1e-9 and abs(r['extrapolated'] - f0) < 1e-9
    assert abs(r['gci_fine'] - 1.25 * abs((med - fine) / fine) / 3) < 1e-12
    with pytest.raises(ValueError):
        pde.grid_convergence_index(1.0, 1.2, 1.1, 2.0)       # oscillatory, not monotone
    with pytest.raises(ValueError):
        pde.grid_convergence_index(1.0, 1.3, 1.4, 2.0)       # successive changes grow on refinement: observed order negative
