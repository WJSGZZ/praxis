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


def sobol_convergence(model, names, bounds, *, n=1024, seed=2027, max_evaluations=400_000):
    """Sobol indices at base sample sizes n and 2n, and the largest change in S1 and ST between them.

    Indices that move by more than their bootstrap half-width when n doubles have not converged; report them as such, or enlarge n."""
    a = sobol_sensitivity(model, names, bounds, n=n, seed=seed, max_evaluations=max_evaluations)
    b = sobol_sensitivity(model, names, bounds, n=2 * n, seed=seed, max_evaluations=max_evaluations)
    shifts = [dict(name=p['name'], S1_change=abs(p['S1'] - q['S1']), ST_change=abs(p['ST'] - q['ST']), S1_conf=q['S1_conf'], ST_conf=q['ST_conf'])
              for p, q in zip(a['parameters'], b['parameters'])]
    converged = all(s['S1_change'] <= max(s['S1_conf'], 0.02) and s['ST_change'] <= max(s['ST_conf'], 0.02) for s in shifts)
    return dict(n=n, coarse=a, fine=b, changes=shifts, converged=bool(converged),
                note='Converged means no index moved by more than its confidence half-width (or 0.02) when n doubled; it does not make the input ranges right.')
