"""Input and stability safeguards around pyMCDM's TOPSIS implementation."""
import numpy as np
from pymcdm.methods import TOPSIS
from pymcdm.normalizations import minmax_normalization
from scipy.stats import rankdata


def evaluate_alternatives(matrix, weights, directions, *, alternatives=None,
                          criteria=None, trials=1000, weight_sigma=.35, seed=2027):
    """directions: +1 benefit, -1 cost; weights encode justified preferences.

    Weight scenarios are multiplicative lognormal perturbations, normalized to
    sum one. They express assumed preference scenarios, not real-world win odds.
    """
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] < 1 or not np.isfinite(matrix).all():
        raise ValueError("Need >=2 alternatives and >=1 finite numeric criterion")
    rows, columns = matrix.shape
    weights = np.asarray(weights, dtype=float)
    directions = np.asarray(directions)
    if weights.shape != (columns,) or not np.isfinite(weights).all() or np.any(weights < 0) or not np.any(weights > 0):
        raise ValueError("Weights must be finite, nonnegative and not all zero")
    if directions.shape != (columns,) or not np.isin(directions, [-1, 1]).all():
        raise ValueError("Each direction must be +1 (benefit) or -1 (cost)")
    if type(trials) is not int or not 1 <= trials <= 10000:
        raise ValueError("trials must be an integer from 1 to 10000")
    if not np.isfinite(weight_sigma) or not 0 <= weight_sigma <= 2:
        raise ValueError("weight_sigma must be finite in [0,2]")
    alternatives = list(alternatives) if alternatives is not None else [f"A{i+1}" for i in range(rows)]
    criteria = list(criteria) if criteria is not None else [f"C{i+1}" for i in range(columns)]
    for labels, size in [(alternatives, rows), (criteria, columns)]:
        if len(labels) != size or any(not isinstance(x, str) or not x.strip() for x in labels) or len(set(labels)) != size:
            raise ValueError("Labels must be nonempty, unique and match matrix dimensions")
    # Zero-weight and constant criteria provide no TOPSIS discrimination.
    active = (weights > 0) & (np.ptp(matrix, axis=0) > 0)
    if not np.any(active):
        raise ValueError("No varying positively weighted criteria; no ranking is supported")
    dropped = [{"criterion": criteria[i], "reason": "zero weight" if weights[i] == 0 else "constant"}
               for i in range(columns) if not active[i]]
    w = weights[active] / np.max(weights[active])
    w /= w.sum()
    # We validate our stricter input contract above; do not run upstream
    # dominance warnings 1000 times. TOPSIS validly ranks dominant alternatives.
    solver = TOPSIS(normalization_function=minmax_normalization)
    x, types = matrix[:, active], directions[active]
    scores = np.asarray(solver(x, w, types, validation=False), dtype=float)
    if not np.isfinite(scores).all():
        raise ValueError("Non-finite scores; inspect numeric scale")
    rng = np.random.default_rng(seed)
    first_share = np.zeros(rows)
    rank_sum = np.zeros(rows)
    for _ in range(trials):
        scenario_weights = w * np.exp(rng.normal(0, weight_sigma, len(w)))
        scenario_weights /= scenario_weights.sum()
        scenario = np.asarray(solver(x, scenario_weights, types, validation=False), dtype=float)
        if not np.isfinite(scenario).all():
            raise ValueError("Non-finite scenario scores")
        winners = np.isclose(scenario, scenario.max(), rtol=0, atol=1e-10)
        first_share += winners / winners.sum()  # Tied winners split one share.
        rank_sum += rankdata(-scenario, method="average")
    return {"method": "pyMCDM TOPSIS with min-max normalization",
            "seed": seed, "trials": trials, "weight_sigma": weight_sigma,
            "active_criteria": [{"name": criteria[i], "direction": int(directions[i]),
                                 "normalized_weight": float(w[j])}
                                for j, i in enumerate(np.flatnonzero(active))],
            "dropped_criteria": dropped,
            "alternatives": [{"name": name, "score": float(scores[i]),
                              "base_rank": float(rankdata(-scores, method="average")[i]),
                              "first_place_scenario_share": float(first_share[i] / trials),
                              "mean_scenario_rank": float(rank_sum[i] / trials)}
                             for i, name in enumerate(alternatives)],
            "interpretation": "Scenario shares depend on assumed weight perturbations, not objective probabilities. Scores depend on criteria, normalization and the alternative set; check rank reversal."}
