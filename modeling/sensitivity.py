"""Local safeguards around SALib; no upstream algorithm is copied or changed."""
import numpy as np
from SALib.sample import sobol as sampling
from SALib.analyze import sobol as analysis


def _problem(names, bounds, distributions):
    names = list(names)
    if not names or any(not isinstance(s, str) or not s.strip() for s in names) or len(set(names)) != len(names):
        raise ValueError('Parameter names must be nonempty and unique')
    dists = ['unif'] * len(names) if distributions is None else list(distributions)
    if len(dists) != len(names) or len(bounds) != len(names):
        raise ValueError('bounds and distributions must contain one specification per parameter')
    limits = []
    for dist, row in zip(dists, bounds):
        values = np.asarray(row, float)
        if values.ndim != 1 or not np.isfinite(values).all():
            raise ValueError('Distribution parameters must be finite vectors')
        count = {'unif': (2,), 'logunif': (2,), 'norm': (2,), 'lognorm': (2,),
                 'triang': (3,), 'truncnorm': (4,), 'weibull': (2, 3)}
        if not isinstance(dist, str) or dist not in count or len(values) not in count[dist]:
            raise ValueError('Use SALib unif/logunif/norm/lognorm/triang/truncnorm/weibull with the required parameter count; triang requires [lower, upper, peak_fraction]')
        if dist in ('unif', 'logunif', 'triang', 'truncnorm') and values[0] >= values[1]:
            raise ValueError('Distribution lower bound must be smaller than upper bound')
        if dist == 'logunif' and values[0] <= 0:
            raise ValueError('Log-uniform bounds must be positive')
        if dist in ('norm', 'lognorm') and values[1] <= 0 or dist == 'truncnorm' and values[3] <= 0:
            raise ValueError('Distribution standard deviation must be positive')
        if dist == 'triang' and (values[1] < 0 or not 0 <= values[2] < 1):
            raise ValueError('SALib triang requires upper >= 0 and 0 <= peak_fraction < 1')
        if dist == 'weibull' and np.any(values[:2] <= 0):
            raise ValueError('Weibull shape and scale must be positive')
        limits.append(values.tolist())
    problem = dict(num_vars=len(names), names=names, bounds=limits)
    if distributions is not None:
        problem['dists'] = dists
    return problem, dists


def sobol_sensitivity(model, names, bounds, *, n=2048, seed=2027, max_evaluations=100_000,
                      second_order=False, distributions=None):
    """Vectorized deterministic scalar model under independent continuous inputs.

    SALib distributions: unif [lower,upper], logunif [positive lower,upper], norm
    and lognorm [mean,sd] (lognorm in natural-log space), triang [lower,upper,
    peak_fraction], truncnorm [lower,upper,mean,sd], weibull [shape,scale,location?].
    model(X) must return one output per row in the SAME order. Sampling and
    analysis are paired; arbitrary pre-existing Monte Carlo samples cannot be used.
    n is a power of two. Second-order sampling costs n*(2*d+2), otherwise n*(d+2).
    """
    problem, dists = _problem(names, bounds, distributions)
    names, limits = problem['names'], problem['bounds']
    if type(second_order) is not bool:
        raise ValueError('second_order must be a boolean')
    if type(n) is not int or n < 64 or n & (n - 1):
        raise ValueError('n must be a power of two >=64')
    if type(max_evaluations) is not int or max_evaluations < 1:
        raise ValueError('max_evaluations must be a positive integer')
    count = n * ((2 if second_order else 1) * len(names) + 2)
    if count > max_evaluations:
        raise ValueError(f'Requires {count} model evaluations; budget is {max_evaluations}')
    samples = sampling.sample(problem, n, calc_second_order=second_order, seed=seed)
    if not np.isfinite(samples).all():
        raise ValueError('Marginal inverse CDF produced nonfinite samples; inspect distribution parameters')
    outputs = np.asarray(model(samples.copy()), dtype=float)
    if outputs.shape != (len(samples),) or not np.isfinite(outputs).all():
        raise ValueError('Model must return one finite scalar per sample in original order')
    if np.ptp(outputs) == 0:
        raise ValueError('Constant output has zero variance; Sobol indices are undefined')
    indices = analysis.analyze(problem, outputs, calc_second_order=second_order, seed=seed,
                               num_resamples=200, conf_level=.95, print_to_console=False)
    if not all(np.isfinite(indices[key]).all() for key in ['S1', 'ST', 'S1_conf', 'ST_conf']):
        raise ValueError('Non-finite sensitivity estimate; inspect model scaling and sample size')
    out = {'seed': seed, 'base_sample_size': n, 'evaluations': len(samples), 'second_order': second_order,
           'assumption': 'Independent continuous uniform inputs; deterministic scalar model' if all(d == 'unif' for d in dists) else 'Independent continuous inputs with the declared SALib marginal distributions; deterministic scalar model',
           'method': 'SALib Sobol sampling and analysis; pairwise second-order estimates' if second_order else 'SALib Sobol sampling and analysis; no pairwise second-order estimates',
           'confidence': '95% bootstrap half-widths conditional on this model and input distributions',
           'parameters': [{'name': name, 'bounds': limits[i], 'distribution': dists[i],
                           'S1': float(indices['S1'][i]), 'ST': float(indices['ST'][i]),
                           'S1_conf': float(indices['S1_conf'][i]), 'ST_conf': float(indices['ST_conf'][i])}
                          for i, name in enumerate(names)],
           'interpretation': 'Do not clip negative estimates or infer causality. Confirm convergence at larger n.'}
    if second_order:
        pairs = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                value, confidence = indices['S2'][i, j], indices['S2_conf'][i, j]
                if not np.isfinite([value, confidence]).all():
                    raise ValueError('Non-finite second-order estimate; inspect sample size and model scaling')
                pairs.append(dict(names=[names[i], names[j]], S2=float(value), S2_conf=float(confidence)))
        out['pairs'] = pairs
    return out


def sobol_convergence(model, names, bounds, *, n=1024, seed=2027, max_evaluations=400_000,
                      second_order=False, distributions=None):
    """Compare n and 2n estimates, including S2 when requested, within a combined evaluation budget."""
    problem, _ = _problem(names, bounds, distributions)
    names = problem['names']
    if type(second_order) is not bool:
        raise ValueError('second_order must be a boolean')
    if type(n) is not int or n < 64 or n & (n - 1):
        raise ValueError('n must be a power of two >=64')
    if type(max_evaluations) is not int or max_evaluations < 1:
        raise ValueError('max_evaluations must be a positive integer')
    total = 3 * n * ((2 if second_order else 1) * len(names) + 2)
    if total > max_evaluations:
        raise ValueError(f'Requires {total} total model evaluations; budget is {max_evaluations}')
    kwargs = dict(seed=seed, second_order=second_order, distributions=distributions)
    a = sobol_sensitivity(model, names, bounds, n=n, max_evaluations=max_evaluations, **kwargs)
    b = sobol_sensitivity(model, names, bounds, n=2*n, max_evaluations=max_evaluations-a['evaluations'], **kwargs)
    shifts = [dict(name=p['name'], S1_change=abs(p['S1']-q['S1']), ST_change=abs(p['ST']-q['ST']), S1_conf=q['S1_conf'], ST_conf=q['ST_conf'])
              for p, q in zip(a['parameters'], b['parameters'])]
    converged = all(s['S1_change'] <= max(s['S1_conf'], .02) and s['ST_change'] <= max(s['ST_conf'], .02) for s in shifts)
    out = dict(n=n, coarse=a, fine=b, changes=shifts, converged=bool(converged),
               total_evaluations=a['evaluations']+b['evaluations'],
               note='Converged means no reported index moved by more than its fine confidence half-width (or 0.02) when n doubled; this is a diagnostic, not a guarantee or validation of input distributions.')
    if second_order:
        pair_changes = [dict(names=p['names'], S2_change=abs(p['S2']-q['S2']), S2_conf=q['S2_conf']) for p, q in zip(a['pairs'], b['pairs'])]
        out['pair_changes'] = pair_changes
        out['converged'] = bool(converged and all(s['S2_change'] <= max(s['S2_conf'], .02) for s in pair_changes))
    return out
