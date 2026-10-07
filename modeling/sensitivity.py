"""Local safeguards around SALib; no upstream algorithm is copied or changed."""
import numpy as np
from SALib.sample import sobol as sampling
from SALib.analyze import sobol as analysis


def sobol_sensitivity(model, names, bounds, *, n=2048, seed=2027, max_evaluations=100_000):
    """Vectorized deterministic scalar model under independent uniform inputs.

    model(X) must return one output per row, in the SAME order. Sampling and
    analysis are a pair; arbitrary pre-existing Monte Carlo samples cannot be used.
    n is a power of two; this wrapper omits second-order pairwise estimates.
    """
    names = list(names)
    if not names or any(not isinstance(s, str) or not s.strip() for s in names) or len(set(names)) != len(names):
        raise ValueError("Parameter names must be nonempty and unique")
    limits = np.asarray(bounds, dtype=float)
    if limits.shape != (len(names), 2) or not np.isfinite(limits).all() or np.any(limits[:, 0] >= limits[:, 1]):
        raise ValueError("Each parameter needs a finite increasing [lower, upper] bound")
    if type(n) is not int or n < 64 or n & (n - 1):
        raise ValueError("n must be a power of two >=64")
    if type(max_evaluations) is not int or max_evaluations < 1:
        raise ValueError("max_evaluations must be a positive integer")
    count = n * (len(names) + 2)
    if count > max_evaluations:
        raise ValueError(f"Requires {count} model evaluations; budget is {max_evaluations}")
    problem = {"num_vars": len(names), "names": names, "bounds": limits.tolist()}
    samples = sampling.sample(problem, n, calc_second_order=False, seed=seed)
    outputs = np.asarray(model(samples.copy()), dtype=float)
    if outputs.shape != (len(samples),) or not np.isfinite(outputs).all():
        raise ValueError("Model must return one finite scalar per sample in original order")
    if np.ptp(outputs) == 0:
        raise ValueError("Constant output has zero variance; Sobol indices are undefined")
    indices = analysis.analyze(problem, outputs, calc_second_order=False, seed=seed,
                               num_resamples=200, conf_level=.95, print_to_console=False)
    if not all(np.isfinite(indices[key]).all() for key in ["S1", "ST", "S1_conf", "ST_conf"]):
        raise ValueError("Non-finite sensitivity estimate; inspect model scaling and sample size")
    return {"seed": seed, "base_sample_size": n, "evaluations": len(samples),
            "assumption": "Independent continuous uniform inputs; deterministic scalar model",
            "method": "SALib Sobol sampling and analysis; no pairwise second-order estimates",
            "confidence": "95% bootstrap half-widths conditional on this model and input distributions",
            "parameters": [{"name": name, "bounds": limits[i].tolist(),
                            "S1": float(indices["S1"][i]), "ST": float(indices["ST"][i]),
                            "S1_conf": float(indices["S1_conf"][i]), "ST_conf": float(indices["ST_conf"][i])}
                           for i, name in enumerate(names)],
            "interpretation": "Do not clip negative estimates or infer causality. Confirm convergence at larger n."}
