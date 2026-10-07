import math

import numpy as np
import pytest
from scipy.special import erfc

from modeling import layered

SUIT = [dict(thickness=0.006, k=0.082, rho_c=300 * 1377), dict(thickness=0.0036, k=0.37, rho_c=862 * 2100),
        dict(thickness=0.005, k=0.028, rho_c=1.18 * 1005), dict(thickness=0.0055, k=0.045, rho_c=74.2 * 1726)]   # four layers, textbook-order properties
TIMES = [60.0, 300.0, 1200.0, 3600.0]


def test_two_solvers_agree_on_a_four_layer_composite_and_the_fv_order_is_two():
    kw = dict(t_initial=37.0, left=['robin', 100.0, 75.0], right=['robin', 8.0, 37.0])
    exact = layered.laplace_layered(SUIT, times=TIMES, **kw)
    errors = []
    for cells in (8, 16, 32):
        fv = layered.solve_layered(SUIT, t_end=3600, times=TIMES, cells_per_layer=cells, **kw)
        errors.append(max(abs(np.array(fv['surface_right']) - np.array(exact['surface_right']))))
    assert errors[-1] < 5e-3
    orders = [math.log(errors[i] / errors[i + 1]) / math.log(2) for i in range(2)]
    assert all(1.5 < o < 2.6 for o in orders), (errors, orders)
    fv = layered.solve_layered(SUIT, t_end=3600, times=TIMES, cells_per_layer=32, **kw)
    for a, b in zip(fv['interfaces'], exact['interfaces']):
        assert np.max(np.abs(np.array(a) - np.array(b))) < 5e-3


def test_semi_infinite_limit_matches_the_erfc_solution_at_an_interface():
    alpha = 1e-6
    layers = [dict(thickness=0.01, k=1.0, rho_c=1.0 / alpha), dict(thickness=0.3, k=1.0, rho_c=1.0 / alpha)]
    kw = dict(t_initial=20.0, left=['dirichlet', 100.0], right=['dirichlet', 20.0])
    t = 40.0
    truth = 20 + 80 * erfc(0.01 / (2 * math.sqrt(alpha * t)))
    lap = layered.laplace_layered(layers, times=[t], **kw)['interfaces'][0][0]
    assert abs(lap - truth) < 1e-6
    # a step change of the surface temperature at t = 0 is singular: the finite-volume error is first order here, and must shrink with the mesh
    errors = [abs(layered.solve_layered(layers, t_end=t, times=[t], cells_per_layer=[n, 2 * n], **kw)['interfaces'][0][0] - truth) for n in (30, 60, 120)]
    assert errors[0] > errors[1] > errors[2] and errors[0] / errors[2] > 3 and errors[2] < 0.15


def test_steady_state_equals_the_series_resistance_solution():
    kw = dict(t_initial=37.0, left=['robin', 100.0, 75.0], right=['robin', 8.0, 37.0])
    resistance = 1 / 100.0 + sum(l['thickness'] / l['k'] for l in SUIT) + 1 / 8.0
    flux = (75.0 - 37.0) / resistance
    right_surface = 37.0 + flux / 8.0
    long = layered.solve_layered(SUIT, t_end=2e5, times=[2e5], cells_per_layer=10, **kw)
    assert abs(long['surface_right'][-1] - right_surface) < 1e-3
    assert abs(layered.laplace_layered(SUIT, times=[2e4], **kw)['surface_right'][0] - right_surface) < 1e-3


def test_mixed_boundary_types_and_invalid_input():
    layers = [dict(thickness=0.02, k=1.0, rho_c=2e6), dict(thickness=0.02, k=0.5, rho_c=1e6)]
    for left, right in ((['dirichlet', 50.0], ['robin', 10.0, 20.0]), (['robin', 20.0, 50.0], ['dirichlet', 20.0])):
        kw = dict(t_initial=20.0, left=left, right=right)
        lap = layered.laplace_layered(layers, times=[600.0], **kw)
        fv = layered.solve_layered(layers, t_end=600, times=[600.0], cells_per_layer=60, **kw)
        assert abs(lap['surface_right'][0] - fv['surface_right'][-1]) < 5e-3 and abs(lap['interfaces'][0][0] - fv['interfaces'][0][-1]) < 5e-3
    with pytest.raises(ValueError):
        layered.solve_layered([], t_end=1, t_initial=0, left=['dirichlet', 1], right=['dirichlet', 1])
    with pytest.raises(ValueError):
        layered.solve_layered(layers, t_end=1, t_initial=0, left=['robin', -1, 0], right=['dirichlet', 1])
