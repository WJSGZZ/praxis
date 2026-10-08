"""Small, original counterexamples to common modeling claims.

Run from the Praxis root: python examples/method_contracts_demo.py
These calculations illustrate why checks are needed; they do not audit a solver
or establish predictive performance on a real problem. No external data is used.
"""

import json
import math

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator


def run() -> dict:
    results = {}

    # Correlation ignores an additive bias; prediction loss does not.
    truth = np.arange(1.0, 6.0)
    prediction = truth + 10
    correlation_squared = float(np.corrcoef(truth, prediction)[0, 1] ** 2)
    r2 = float(1 - np.sum((prediction - truth) ** 2) / np.sum((truth - truth.mean()) ** 2))
    assert math.isclose(correlation_squared, 1) and r2 == -49
    results["correlation_is_not_predictive_r2"] = {"correlation_squared": correlation_squared, "r2": r2}

    # A single lucky fold reverses the ranking of two candidates.
    losses = np.array([[0.0, 100.0], [20.0, 20.0]])
    assert int(np.argmin(losses.min(axis=1))) == 0
    assert int(np.argmin(losses.mean(axis=1))) == 1
    results["aggregate_folds"] = {"best_single_fold": "A", "best_mean_loss": "B"}

    # A fitted transformation must not use the held-out range.
    train = np.array([0.0, 1.0])
    joined = np.append(train, 100.0)
    scaled_train_only = (train[-1] - train.min()) / np.ptp(train)
    scaled_with_holdout = (train[-1] - joined.min()) / np.ptp(joined)
    assert scaled_train_only == 1 and scaled_with_holdout == 0.01
    results["holdout_changes_preprocessing"] = {"train_only": float(scaled_train_only), "joined": float(scaled_with_holdout)}

    # Centered smoothing at time 2 depends on the unavailable value at time 3.
    history = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    altered = history.copy()
    altered[3] = 400
    assert history[1:4].mean() != altered[1:4].mean()
    assert history[:3].mean() == altered[:3].mean()
    results["smoothing_information_boundary"] = {"centered_changed": True, "trailing_changed": False}

    # y=7+3x: prediction must preserve the fitted intercept.
    x = np.array([0.0, 1.0, 2.0])
    design = np.column_stack([np.ones(3), x])
    coefficients = np.linalg.lstsq(design, 7 + 3 * x, rcond=None)[0]
    assert np.allclose(design @ coefficients, 7 + 3 * x)
    assert np.allclose((7 + 3 * x) - x * coefficients[1], 7)
    results["intercept_contract"] = {"omitted_intercept_bias": 7}

    # On a->c, compare two routes with weights [2,2] and [5].
    # Costs prefer the former, capacities the latter.
    routes = [[2, 2], [5]]
    assert int(np.argmin([sum(p) for p in routes])) == 0
    assert int(np.argmax([min(p) for p in routes])) == 1
    results["path_objective"] = {"minimum_sum_route": "two-hop", "maximum_bottleneck_route": "direct"}

    # Relative +/-10% perturbations of x^3 cancel on a symmetric sample.
    x = np.array([-1.0, 1.0])
    response = (1.1 * x) ** 3 - (0.9 * x) ** 3
    assert abs(response.mean()) < 1e-12 and np.allclose(np.abs(response), 0.602)
    results["signed_sensitivity_cancellation"] = {"signed_mean": float(response.mean()), "mean_absolute": float(np.abs(response).mean())}

    # Each independent increment has variance 1. The second cumulative value
    # has variance 2, not the original second increment's variance 1.
    restore = np.tril(np.ones((2, 2)))
    covariance = restore @ np.eye(2) @ restore.T
    assert np.array_equal(covariance, [[1, 1], [1, 2]])
    mu, variance = 0.0, 1.0
    assert math.exp(mu + variance / 2) > math.exp(mu)
    results["restore_distribution"] = {"cumulative_covariance": covariance.tolist(), "lognormal_median": 1, "lognormal_mean": math.exp(0.5)}

    # Nondecreasing nodes need not produce a monotone ordinary cubic spline.
    x, y = np.arange(4.0), np.array([0.0, 1.0, 1.0, 1.0])
    grid = np.linspace(0, 3, 601)
    cubic, shape_preserving = CubicSpline(x, y)(grid), PchipInterpolator(x, y)(grid)
    assert cubic.max() > 1.01
    assert shape_preserving.min() >= 0 and shape_preserving.max() <= 1
    results["interpolation_shape"] = {"cubic_max": float(cubic.max()), "pchip_max": float(shape_preserving.max())}

    return {"scope": "synthetic counterexamples, not solver certification", "passed": len(results), "checks": results}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
