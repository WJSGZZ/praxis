"""Consumer regression for the finite-initial-state SIR result contract."""
import pytest

from evals import planted


def test_public_sir_solver_consumes_the_fitted_finite_initial_state(monkeypatch):
    # A subcritical R0 with 10% initially infected still has a positive final
    # attack fraction. Recomputing the infinitesimal-seed limit returns zero.
    expected = planted._sir_attack_oracle(.5, susceptible=.9)
    assert expected > .1
    observations = [100., 90., 80., 70.]

    def fitted(infected, population):
        assert infected == observations and population == 1000.
        return {"beta": .5, "gamma": 1., "final_size": expected}

    monkeypatch.setattr(planted.epidemic, "fit_sir", fitted)
    task = planted.Task("sir", 0, "Finite initial infection", {
        "infected": observations, "population": 1000.}, ["r0", "final_size"])
    answer = planted.solve_with_tools(task)
    assert answer["r0"] == .5
    assert answer["final_size"] == pytest.approx(expected)
