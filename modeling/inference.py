"""Statistical inference and simulation tools: tests with effect sizes and assumption flags, bootstrap, Monte Carlo with a convergence
account, ODE solving with a tolerance check, ARIMA forecasts, PCA and clustering.

Each result carries the assumptions it relies on; a p-value alone is never the output."""
from __future__ import annotations

import warnings
from numbers import Real
from typing import Callable, Sequence

import numpy as np
from scipy import stats
from modeling.contracts import diagnostic, finite_real


def adjust_pvalues(pvalues: Sequence[float], *, hypothesis_ids: Sequence[str], family_id: str,
                   method: str = 'holm', alpha: float = 0.05, effects: Sequence[float | None] | None = None,
                   effect_definition: str | None = None) -> dict:
    """Adjust a complete hypothesis family using Statsmodels, preserving input order.

    Holm/Bonferroni control FWER; BH/BY control FDR under the returned conditions.
    Effect estimates, when supplied, are caller measurements and are not recomputed
    or validated scientifically by a p-value correction. No observations are read.
    """
    from importlib.metadata import version
    from statsmodels.stats.multitest import multipletests

    def finite_number(value, name):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
            raise ValueError(f'{name} must contain finite real numbers, not booleans')
        try:
            result = float(value)
        except (ValueError, TypeError, OverflowError) as error:
            raise ValueError(f'{name} must contain finite real numbers') from error
        if not np.isfinite(result):
            raise ValueError(f'{name} must contain finite real numbers')
        return result

    if not isinstance(method, str) or method not in ('holm', 'bonferroni', 'bh', 'by'):
        raise ValueError('method must be holm, bonferroni, bh or by')
    level = finite_number(alpha, 'alpha')
    if not 0 < level < 1:
        raise ValueError('alpha must be strictly between zero and one')
    raw = np.asarray(pvalues, dtype=object)
    if raw.ndim != 1 or not len(raw):
        raise ValueError('pvalues must be a nonempty one-dimensional sequence')
    p = np.array([finite_number(value, 'pvalues') for value in raw])
    if ((p < 0) | (p > 1)).any():
        raise ValueError('pvalues must be probabilities in [0, 1]')
    if not isinstance(family_id, str) or not family_id.strip():
        raise ValueError('family_id must be a nonempty string')
    if hypothesis_ids is None or isinstance(hypothesis_ids, (str, bytes)):
        raise ValueError('hypothesis_ids must be one unique nonempty string per p-value')
    try:
        ids = list(hypothesis_ids)
    except TypeError as error:
        raise ValueError('hypothesis_ids must be one unique nonempty string per p-value') from error
    if len(ids) != len(p) or any(not isinstance(item, str) or not item.strip() for item in ids) or len(set(ids)) != len(ids):
        raise ValueError('hypothesis_ids must be one unique nonempty string per p-value')
    estimates = [None] * len(p)
    if effects is not None:
        values = np.asarray(effects, dtype=object)
        if values.ndim != 1 or len(values) != len(p):
            raise ValueError('effects must contain exactly one estimate or null per hypothesis')
        if not isinstance(effect_definition, str) or not effect_definition.strip():
            raise ValueError('effect_definition must describe the supplied effects and their units')
        estimates = [None if value is None else finite_number(value, 'effects') for value in values]
    elif effect_definition is not None:
        raise ValueError('effect_definition requires effects')
    backend_method = {'holm': 'holm', 'bonferroni': 'bonferroni', 'bh': 'fdr_bh', 'by': 'fdr_by'}[method]
    reject, adjusted, _, _ = multipletests(p, alpha=level, method=backend_method, is_sorted=False)
    conditions = {
        'holm': 'Strong family-wise error rate control under arbitrary dependence, provided each null p-value is valid.',
        'bonferroni': 'Family-wise error rate control under arbitrary dependence, provided each null p-value is valid.',
        'bh': 'False discovery rate control for valid null p-values under independence of the p-values, or suitable positive dependence (PRDS) on the subset of true null hypotheses.',
        'by': 'False discovery rate control under arbitrary dependence, provided each null p-value is valid.'
    }
    return dict(family_id=family_id, family_size=len(p), method=method, alpha=level,
                error_control='FWER' if method in ('holm', 'bonferroni') else 'FDR',
                error_control_definition='Probability of at least one false rejection in the family' if method in ('holm', 'bonferroni') else 'Expected fraction of false rejections among rejected hypotheses (zero when none are rejected)',
                hypotheses=[dict(hypothesis_id=identifier, p_value=float(original), adjusted_p_value=float(adjustment),
                                 reject=bool(rejected), effect_estimate=estimate,
                                 effect_status='caller_supplied' if estimate is not None else 'not_supplied')
                            for identifier, original, adjustment, rejected, estimate in zip(ids, p, adjusted, reject, estimates)],
                effect_definition=effect_definition,
                conditions=[conditions[method], 'Supply the complete prespecified family, including nonsignificant tests; this tool cannot check omitted tests or the sampling design.'],
                backend=dict(name='statsmodels.stats.multitest.multipletests', version=version('statsmodels'), method=backend_method),
                note='Adjustment does not repair invalid p-values, data selection, confounding or a wrong statistical model. Adjusted p-values are not probabilities that hypotheses are false; effect estimates remain caller supplied.')


def hypothesis_test(kind: str, a: Sequence[float], b: Sequence[float] | None = None, *, table=None, alpha: float = 0.05, groups: Sequence[Sequence[float]] | None = None) -> dict:
    """kind: welch_t, paired_t, mann_whitney, ks_2samp, anova, kruskal, chi2_independence (table), shapiro (a), correlation (a, b).

    Returns statistic, p-value, an effect size, a confidence interval where one is standard, and flags for violated assumptions."""
    alpha = finite_real(alpha, 'alpha')
    if not 0 < alpha < 1:
        raise ValueError('alpha must lie strictly between zero and one')

    def sample(value, name, minimum=2):
        result = np.asarray(value, float)
        if result.ndim != 1 or len(result) < minimum or not np.isfinite(result).all():
            raise ValueError(f'{name} must be a finite one-dimensional sample with at least {minimum} observations')
        return result

    flags = []
    out: dict = dict(kind=kind, alpha=alpha)
    if kind in ('welch_t', 'paired_t', 'mann_whitney', 'ks_2samp', 'correlation'):
        minimum = 1 if kind in ('mann_whitney', 'ks_2samp') else 2
        a, b = sample(a, 'a', minimum), sample(b, 'b', minimum)
        if kind in ('paired_t', 'correlation') and a.shape != b.shape:
            raise ValueError('Paired samples and correlation require matching sample lengths; broadcasting is not allowed')
    if kind == 'welch_t':
        r = stats.ttest_ind(a, b, equal_var=False)
        sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        diff = a.mean() - b.mean()
        ci = r.confidence_interval(1 - alpha)
        out.update(statistic=float(r.statistic), p=float(r.pvalue), difference=float(diff), ci=[float(ci.low), float(ci.high)], effect_size_cohen_d=float(diff / sp))
        for name, x in (('a', a), ('b', b)):
            if 3 <= len(x) < 30 and stats.shapiro(x).pvalue < alpha:
                flags.append(f'sample {name} departs from normality (Shapiro p<{alpha}); this is a diagnostic, not a rule for choosing another test. Assess outliers, sample size and independence for the mean-difference target; a rank test is not a general substitute for comparing means')
    elif kind == 'paired_t':
        r = stats.ttest_rel(a, b)
        d = a - b
        ci = r.confidence_interval(1 - alpha)
        out.update(statistic=float(r.statistic), p=float(r.pvalue), mean_difference=float(d.mean()), ci=[float(ci.low), float(ci.high)], effect_size_dz=float(d.mean() / d.std(ddof=1)))
        if 3 <= len(d) < 30 and stats.shapiro(d).pvalue < alpha:
            flags.append('paired differences depart from normality; assess pair alignment, independence across pairs, outliers and the mean-difference target. Do not switch tests from this diagnostic p-value alone; signed-rank inference has a different target and additional symmetry assumptions')
    elif kind == 'mann_whitney':
        r = stats.mannwhitneyu(a, b, alternative='two-sided')
        out.update(statistic=float(r.statistic), p=float(r.pvalue), effect_size_prob_superiority=float(r.statistic / (len(a) * len(b))))
    elif kind == 'ks_2samp':
        r = stats.ks_2samp(a, b)
        out.update(statistic=float(r.statistic), p=float(r.pvalue))
    elif kind in ('anova', 'kruskal'):
        if groups is None or len(groups) < 2:
            raise ValueError('At least two finite group samples are required')
        gs = [sample(g, f'groups[{i}]') for i, g in enumerate(groups)]
        r = stats.f_oneway(*gs) if kind == 'anova' else stats.kruskal(*gs)
        out.update(statistic=float(r.statistic), p=float(r.pvalue), group_means=[float(g.mean()) for g in gs])
        if kind == 'anova':
            n = sum(len(g) for g in gs)
            ssb = sum(len(g) * (g.mean() - np.concatenate(gs).mean()) ** 2 for g in gs)
            sst = ((np.concatenate(gs) - np.concatenate(gs).mean()) ** 2).sum()
            out['effect_size_eta_squared'] = float(ssb / sst)
            if stats.levene(*gs).pvalue < alpha:
                flags.append('variances differ (Levene); for a group-mean target, assess a heteroscedasticity-valid analysis such as Welch together with the sampling design. This diagnostic p-value alone does not select a method, and Kruskal is not a general substitute for comparing means')
            out['n'] = n
    elif kind == 'chi2_independence':
        t = np.asarray(table, float)
        if (t.ndim != 2 or min(t.shape) < 2 or not np.isfinite(t).all()
                or (t < 0).any() or (t.sum(axis=0) <= 0).any() or (t.sum(axis=1) <= 0).any()):
            raise ValueError('table must be a finite nonnegative 2-D table with at least two positive rows and columns')
        chi2, p, dof, expected = stats.chi2_contingency(t)
        out.update(statistic=float(chi2), p=float(p), dof=int(dof), effect_size_cramers_v=float(np.sqrt(stats.chi2_contingency(t, correction=False)[0] / (t.sum() * (min(t.shape) - 1)))))
        if (expected < 5).any():
            flags.append('some expected counts are below 5; the chi-square approximation is poor (consider Fisher exact for 2x2)')
    elif kind == 'shapiro':
        a = sample(a, 'a', 3)
        r = stats.shapiro(a)
        out.update(statistic=float(r.statistic), p=float(r.pvalue))
    elif kind == 'correlation':
        pr, ps = stats.pearsonr(a, b), stats.spearmanr(a, b)
        ci = pr.confidence_interval(1 - alpha)
        out.update(pearson=float(pr.statistic), pearson_p=float(pr.pvalue), pearson_ci=[float(ci.low), float(ci.high)], spearman=float(ps.statistic), spearman_p=float(ps.pvalue))
        if abs(pr.statistic - ps.statistic) > .2:
            flags.append('Pearson and Spearman differ by more than 0.2: nonlinearity or outliers')
    else:
        raise ValueError('kind must be welch_t, paired_t, mann_whitney, ks_2samp, anova, kruskal, chi2_independence, shapiro or correlation')
    design_targets = {
        'welch_t': ('Difference in population means (a minus b)',
                    ['Observations are independent within and across the two samples.',
                     'Mean inference needs a suitable sampling design and adequate control of tails and outliers; Welch allows unequal variances.']),
        'paired_t': ('Mean of aligned within-pair differences (a minus b)',
                     ['a and b are aligned observations of the same pairs; differences are independent across pairs.',
                      'The paired mean interval needs a suitable model for the differences, including normality for exact small-sample t inference.']),
        'anova': ('Differences among population group means; eta squared describes the observed between-group variation',
                  ['Observations are independent within and across groups.',
                   'Classical one-way ANOVA assumes normal errors and equal group variances for exact finite-sample inference.'])
    }
    if kind in design_targets:
        out['estimand'], requirements = design_targets[kind]
        out['sample_design'] = dict(status='not_checked', requirements=requirements,
                                    note='Diagnostic p-values neither verify these design requirements nor select another estimand or test automatically.')
    # A numerical infinity or an undefined test cannot become JSON NaN or a
    # positive scientific finding. Keep descriptive differences, but withhold
    # t inference when its estimated standard error is zero.
    diagnostics = {}
    degenerate_t = ((kind == 'welch_t' and a.var(ddof=1) == 0 and b.var(ddof=1) == 0)
                    or (kind == 'paired_t' and (a - b).std(ddof=1) == 0))
    if degenerate_t:
        reason = 'Estimated standard error is zero; ordinary t inference is undefined for these samples'
        for key in ('statistic', 'p', 'ci', 'effect_size_cohen_d', 'effect_size_dz'):
            if key in out:
                out[key] = None
                diagnostics[key] = dict(status='undefined', reason=reason)
        flags.append(reason)
    if kind == 'correlation' and (np.ptp(a) == 0 or np.ptp(b) == 0):
        reason = 'Correlation is undefined when either aligned sample is constant'
        for key in ('pearson', 'pearson_p', 'pearson_ci', 'spearman', 'spearman_p'):
            out[key] = None
            diagnostics[key] = dict(status='undefined', reason=reason)
        flags.append(reason)

    def finite_diagnostics(value, path):
        if isinstance(value, list):
            return [finite_diagnostics(item, f'{path}[{i}]') for i, item in enumerate(value)]
        if isinstance(value, float) and not np.isfinite(value):
            result, diagnostics[path] = diagnostic(value, reason='This statistic is undefined or exceeds finite numerical range for the supplied samples')
            return result
        return value

    out = {key: finite_diagnostics(value, key) for key, value in out.items()}
    p_value = out.get('p', out.get('pearson_p'))
    out['significant'] = None if p_value is None else bool(p_value < alpha)
    if diagnostics:
        out['diagnostics'] = diagnostics
    out['flags'] = flags
    out['note'] = 'Significance is not importance: read the effect size and interval. Several tests on one data set need a multiplicity correction.'
    return out


def bootstrap_ci(data: Sequence[float], statistic: str = 'mean', *, n_resamples: int = 5000, confidence: float = 0.95, seed: int = 2027, method: str = 'BCa') -> dict:
    """Bootstrap confidence interval for mean, median, std or a quantile such as q0.9. Independent observations are assumed."""
    x = np.asarray(data, float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError('data must be a finite one-dimensional sample with at least two observations')
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, (int, np.integer)) or n_resamples < 2:
        raise ValueError('n_resamples must be an integer of at least two')
    if not np.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError('confidence must lie strictly between zero and one')
    if not isinstance(method, str) or method.lower() not in ('bca', 'basic', 'percentile'):
        raise ValueError('method must be BCa, basic or percentile')
    if not isinstance(statistic, str):
        raise ValueError('statistic must be a supported statistic name')
    fn: Callable
    if statistic in ('mean', 'median', 'std'):
        fn = {'mean': np.mean, 'median': np.median, 'std': lambda v, axis=-1: np.std(v, ddof=1, axis=axis)}[statistic]
    elif statistic.startswith('q'):
        q = float(statistic[1:])
        if not np.isfinite(q) or not 0 <= q <= 1:
            raise ValueError('quantile level must lie in [0,1]')
        fn = lambda v, axis=-1: np.quantile(v, q, axis=axis)
    else:
        raise ValueError("statistic: mean, median, std, or q<level> such as q0.9")
    res = stats.bootstrap((x,), fn, n_resamples=n_resamples, confidence_level=confidence, method=method, random_state=np.random.default_rng(seed))
    interval = np.array([res.confidence_interval.low, res.confidence_interval.high], float)
    se, se_status = diagnostic(res.standard_error, reason='Bootstrap standard error is undefined for this resampling distribution')
    interval_status = dict(status='computed') if np.isfinite(interval).all() else dict(status='undefined', reason='The requested bootstrap interval is undefined for this resampling distribution; BCa can degenerate even when the estimate is finite')
    return dict(statistic=statistic, estimate=finite_real(fn(x), 'statistic estimate'), ci=interval.tolist() if np.isfinite(interval).all() else None,
                standard_error=se, diagnostics=dict(ci=interval_status, standard_error=se_status),
                n=len(x), method=method, note='For time series or clustered data resample blocks instead; with very small n the interval is itself unreliable.')


def monte_carlo(model: Callable, distributions: dict, *, n: int = 20000, seed: int = 2027,
                threshold: float | None = None, covariance=None, correlation=None,
                sampling: str = 'random', bootstrap_resamples: int = 200,
                confidence: float = .95) -> dict:
    """Propagate declared marginals with independent, normal-covariance or Gaussian-copula inputs.

    Matrix order is distributions insertion order. Covariance requires normal marginals
    and diagonal agreement with their declared variances. Copula correlation is LATENT
    Gaussian correlation, not generally the output marginals' Pearson correlation.
    LHS stratifies independent latent uniforms before the Gaussian transform; dependent
    transformed marginals are not claimed to retain marginal Latin stratification.
    Ordinary row-bootstrap intervals and iid MC errors are unavailable for LHS.
    """
    from scipy.stats import qmc
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or not 2 <= n <= 1_000_000:
        raise ValueError('n must be an integer from two to 1000000')
    if sampling not in ('random', 'lhs'):
        raise ValueError("sampling must be 'random' or 'lhs'")
    if type(bootstrap_resamples) is not int or not 100 <= bootstrap_resamples <= 2000 or n * bootstrap_resamples > 200_000_000:
        raise ValueError('bootstrap_resamples must be 100..2000 with at most 200 million resampled values')
    if isinstance(confidence, bool) or not np.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError('confidence must be strictly between zero and one')
    if threshold is not None and (isinstance(threshold, bool) or not np.isfinite(threshold)):
        raise ValueError('threshold must be finite')
    if not isinstance(distributions, dict) or len(distributions) > 32 or any(not isinstance(k, str) or not k.strip() for k in distributions):
        raise ValueError('distributions must be a dictionary with at most 32 nonempty input names')
    names = list(distributions); d = len(names)
    if n * d > 2_000_000:
        raise ValueError('At most two million input sample values are supported')
    marginals, point_masses = [], {}
    for name, spec in distributions.items():
        if not isinstance(spec, dict) or not isinstance(spec.get('params', {}), dict):
            raise ValueError('Each distribution requires dist and a params dictionary')
        family = getattr(stats, spec.get('dist', ''), None)
        if not isinstance(family, (stats.rv_continuous, stats.rv_discrete)):
            raise ValueError('Only scipy.stats continuous or discrete probability families are supported')
        try:
            marginal = family(**spec.get('params', {}))
            if not np.isfinite(marginal.ppf([.25, .5, .75])).all():
                # SciPy rvs accepts a valid zero-scale location family even
                # though its ppf is undefined. Preserve that point-mass input.
                probe = marginal.rvs(size=2, random_state=np.random.default_rng(0))
                if spec.get('params', {}).get('scale') != 0 or not np.isfinite(probe).all() or probe[0] != probe[1]:
                    raise ValueError('Invalid distribution parameters')
                point_masses[name] = float(probe[0])
        except (ValueError, TypeError) as exc:
            raise ValueError(f'Invalid marginal {name}: {exc}') from exc
        marginals.append(marginal)
    if covariance is not None and correlation is not None:
        raise ValueError('Supply covariance or latent correlation, not both')
    matrix = covariance if covariance is not None else correlation
    factor = None
    if matrix is not None:
        M = np.asarray(matrix, float)
        if not d or M.shape != (d, d) or not np.isfinite(M).all() or not np.allclose(M, M.T, rtol=0, atol=1e-12):
            raise ValueError('Dependence matrix must be finite, symmetric, and match input order')
        if covariance is not None:
            if any(v.dist.name != 'norm' for v in marginals):
                raise ValueError('Covariance input requires normal marginals; use latent correlation for a copula')
            scales = np.array([v.std() for v in marginals])
            if not np.isfinite(scales).all() or np.any(scales <= 0) or not np.allclose(np.diag(M), scales ** 2, rtol=1e-10, atol=0):
                raise ValueError('Covariance diagonal must match positive declared normal variances')
            M = M / np.outer(scales, scales)
        if not np.allclose(np.diag(M), 1, rtol=0, atol=1e-12):
            raise ValueError('Latent correlation diagonal must be one')
        eigenvalues, eigenvectors = np.linalg.eigh(M)
        if eigenvalues.min() < -1e-12:
            raise ValueError('Dependence matrix must be positive semidefinite')
        factor = eigenvectors @ np.diag(np.sqrt(np.maximum(eigenvalues, 0)))
    rng = np.random.default_rng(seed)
    if sampling == 'random' and factor is None:
        sample = {k: marginal.rvs(size=n, random_state=rng) for k, marginal in zip(names, marginals)}
    elif d:
        u = qmc.LatinHypercube(d, seed=seed).random(n) if sampling == 'lhs' else rng.random((n, d))
        if factor is not None:
            latent = stats.norm.ppf(np.clip(u, np.finfo(float).eps, 1 - np.finfo(float).eps)) @ factor.T
            u = stats.norm.cdf(latent)
        u = np.clip(u, np.finfo(float).eps, 1 - np.finfo(float).eps)
        sample = {k: np.full(n, point_masses[k]) if k in point_masses else marginal.ppf(u[:, i])
                  for i, (k, marginal) in enumerate(zip(names, marginals))}
    else:
        sample = {}
    if any(not np.isfinite(v).all() for v in sample.values()):
        raise ValueError('Input sampling produced nonfinite values')
    y = np.asarray(model(sample), float)
    if y.shape != (n,) or not np.isfinite(y).all():
        raise ValueError('model must return exactly n finite scalar outcomes')
    mean, sd = float(y.mean()), float(y.std(ddof=1)); h = n // 2
    if not np.isfinite([mean, sd]).all():
        raise ValueError('Output summary exceeds finite numerical range')
    qs = (.025, .05, .5, .95, .975)
    out = dict(n=int(n), mean=mean, sd=sd, mc_standard_error=sd / np.sqrt(n) if sampling == 'random' else None,
               quantiles={q: float(np.quantile(y, q)) for q in qs},
               half_sample_means=[float(y[:h].mean()), float(y[h:].mean())],
               settled=bool(abs(y[:h].mean() - y[h:].mean()) <= 3 * np.sqrt(2) * sd / np.sqrt(h)) if sampling == 'random' else None,
               sampling=sampling, input_order=names,
               dependence='normal_covariance' if covariance is not None else 'gaussian_copula_latent_correlation' if correlation is not None else 'independent')
    intervals = None
    if sampling == 'random':
        # One resample at a time bounds memory independently of the replicate count.
        brng = np.random.default_rng(np.random.SeedSequence(seed).spawn(1)[0])
        boot = np.array([np.quantile(y[brng.integers(0, n, n)], qs) for _ in range(bootstrap_resamples)])
        tails = ((1-confidence)/2, (1+confidence)/2)
        intervals = {q: np.quantile(boot[:, i], tails).tolist() for i, q in enumerate(qs)}
    out['quantile_bootstrap'] = dict(intervals=intervals, confidence=confidence, resamples=bootstrap_resamples if intervals is not None else 0,
        method='ordinary iid row percentile bootstrap' if intervals is not None else None,
        reason=None if intervals is not None else 'LHS rows are dependent; iid row bootstrap does not estimate this sampling design error. Independent LHS design replicates are needed.')
    if threshold is not None:
        k = int((y > threshold).sum())
        ci = stats.binomtest(k, n).proportion_ci(confidence_level=confidence, method='wilson') if sampling == 'random' else None
        out['exceedance'] = dict(threshold=threshold, probability=k / n, ci=[float(ci.low), float(ci.high)] if ci else None,
            reason=None if ci else 'Wilson iid-binomial sampling interval is not valid for a single LHS design')
    out['note'] = ('Input laws and dependence are caller assumptions. Bootstrap intervals quantify finite iid sampling only, not input-law or structural uncertainty. '
                   'Copula uniforms are clipped at machine epsilon for finite numerical transforms. LHS has no iid MC SE, settled test or bootstrap/Wilson coverage claim.')
    return out


def solve_ode(rhs: Callable, y0: Sequence[float], t_span: Sequence[float], t_eval: Sequence[float] | None = None, *, method: str = 'LSODA', rtol: float = 1e-8, atol: float = 1e-10,
              events: Callable | None = None) -> dict:
    """Integrate twice, comparing dense interpolants only at common physical times.

    The comparison is a sensitivity indicator, not a certified error bound: it
    includes both integration and dense-interpolation error. Terminal events may
    end the two runs at slightly different times; neither run is extrapolated.
    Returned t/y remain the ordinary-tolerance run's requested/adaptive samples.
    """
    from scipy.integrate import solve_ivp
    kw = dict(method=method, t_eval=None if t_eval is None else np.asarray(t_eval, float), events=events, dense_output=True)
    a = solve_ivp(rhs, tuple(t_span), np.asarray(y0, float), rtol=rtol, atol=atol, **kw)
    b = solve_ivp(rhs, tuple(t_span), np.asarray(y0, float), rtol=rtol / 100, atol=atol / 100, **kw)
    if not (a.success and b.success):
        raise RuntimeError(a.message if not a.success else b.message)
    lo = max(a.sol.t_min, b.sol.t_min)
    hi = min(a.sol.t_max, b.sol.t_max)
    # Include internal solver knots even when t_eval omits the terminal event.
    # Sorted times also work for backward integration; evaluate, never extrapolate.
    times = np.unique(np.concatenate((a.sol.ts, b.sol.ts, a.t, b.t, [lo, hi])))
    times = times[(times >= lo) & (times <= hi)]
    if not times.size:
        raise RuntimeError('The two ODE solutions have no common effective time interval')
    difference = np.abs(a.sol(times) - b.sol(times))
    if not np.isfinite(difference).all():
        raise RuntimeError('Non-finite ODE tolerance comparison')
    err = float(np.max(difference))
    out = dict(t=np.asarray(a.t).tolist(), y=np.asarray(a.y).tolist(), method=method, steps=int(np.asarray(a.t).size), tolerance_check_max_difference=err,
               tolerance_check=dict(times=times.tolist(), common_interval=[float(lo), float(hi)],
                                    ordinary_interval=[float(a.sol.t_min), float(a.sol.t_max)],
                                    tighter_interval=[float(b.sol.t_min), float(b.sol.t_max)],
                                    comparison='dense interpolants at the union of solver knots and requested samples in the common interval',
                                    note='Includes interpolation error; a tolerance sensitivity indicator, not a certified error bound. No extrapolation.'),
               stiff_warning=bool(method in ('RK45', 'RK23', 'DOP853') and a.nfev > 50 * max(np.asarray(a.t).size, 1)))
    if events is not None:
        out['events'] = [dict(t=te.tolist(), y=ye.tolist()) for te, ye in zip(a.t_events, a.y_events)]
        out['tighter_events'] = [dict(t=te.tolist(), y=ye.tolist()) for te, ye in zip(b.t_events, b.y_events)]
    return out


def arima_forecast(series: Sequence[float], horizon: int, *, max_p: int = 3, max_d: int = 2,
                   max_q: int = 3, seasonal_period: int | None = None, exog=None,
                   future_exog=None, backtest=False) -> dict:
    """Training-only ADF/AICc ARIMA selection, optional future-known exogenous regressors.

    Backtesting reselects the model at every origin through rolling_origin; actual
    held-out exog are allowed only with explicit exog_known_at_origin=True. That
    declaration is an information assumption, not evidence of historical availability.
    """
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    y = np.asarray(series, float)
    if y.ndim != 1 or len(y) < 12 or not np.isfinite(y).all():
        raise ValueError('ARIMA needs at least12 finite one-dimensional observations')
    if isinstance(horizon, bool) or not isinstance(horizon, (int, np.integer)) or not 1 <= horizon <= 1000:
        raise ValueError('horizon must be an integer from1 to1000')
    for key, v in [('max_p', max_p), ('max_d', max_d), ('max_q', max_q)]:
        if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or not 0 <= v <= 10:
            raise ValueError(f'{key} must be an integer from0 to10')
    if 2 * (max_p+1) * (max_q+1) > 128:
        raise ValueError('ARIMA search grid may contain at most128 trend/order candidates')
    if seasonal_period is not None and (isinstance(seasonal_period, bool) or not isinstance(seasonal_period, (int, np.integer)) or seasonal_period < 2 or seasonal_period * 2 > len(y)):
        raise ValueError('seasonal_period needs at least two full seasons and an integer period>=2')
    X = F = None
    if exog is not None:
        X = np.asarray(exog, float)
        if X.ndim == 1: X = X[:, None]
        if X.ndim != 2 or X.shape[0] != len(y) or not X.shape[1] or X.shape[1] > 16 or not np.isfinite(X).all():
            raise ValueError('exog must be a finite training-row matrix with1..16 columns')
        if np.linalg.matrix_rank(np.column_stack([np.ones(len(y)), X])) != X.shape[1]+1:
            raise ValueError('exog must have full column rank and no constant/duplicate column')
        if future_exog is None:
            raise ValueError('future_exog is required for every forecast horizon and exog column')
        F = np.asarray(future_exog, float)
        if F.ndim == 1 and X.shape[1] == 1: F = F[:, None]
        if F.shape != (horizon, X.shape[1]) or not np.isfinite(F).all():
            raise ValueError('future_exog must match horizon and exog columns and be finite')
    elif future_exog is not None:
        raise ValueError('future_exog requires training exog')
    if type(backtest) is not bool and not isinstance(backtest, dict):
        raise ValueError('backtest must be a boolean or options dictionary')
    options = dict(backtest) if isinstance(backtest, dict) else {}
    if set(options) - {'min_train', 'exog_known_at_origin'}:
        raise ValueError('backtest options are min_train and exog_known_at_origin')
    do_backtest = isinstance(backtest, dict) or backtest
    if do_backtest and X is not None and options.get('exog_known_at_origin') is not True:
        raise ValueError('Exogenous backtest requires explicit exog_known_at_origin=True')
    fits = []
    unit_root_tests = []
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        z = y if X is None else y - np.column_stack([np.ones(len(y)), X]) @ np.linalg.lstsq(np.column_stack([np.ones(len(y)), X]), y, rcond=None)[0]
        d = 0
        # Difference only when ADF rejects a unit root neither around a constant nor around a
        # linear trend; otherwise a trend-stationary series would be differenced and forecast flat.
        while d < max_d and len(z) >= 8 and np.ptp(z) > np.finfo(float).eps * max(1, np.abs(z).max()):
            try: p_c, p_ct = float(adfuller(z, regression='c')[1]), float(adfuller(z, regression='ct')[1])
            except ValueError: break
            unit_root = p_c > .05 and p_ct > .05
            unit_root_tests.append(dict(d=d, adf_p_constant=p_c, adf_p_trend=p_ct, differenced=bool(unit_root)))
            if not unit_root: break
            z, d = np.diff(z), d+1
        # d=0: constant or constant+trend; d=1: none or drift (statsmodels trend='t' in levels).
        trends = ('c', 'ct') if d == 0 else ('n', 't') if d == 1 else ('n',)
        timed_rank_ok = X is None or np.linalg.matrix_rank(np.column_stack([np.ones(len(y)), np.arange(len(y)), X])) == X.shape[1]+2
        for p in range(max_p+1):
            for q in range(max_q+1):
                for trend in trends:
                    if 't' in trend and not timed_rank_ok:
                        continue
                    try:
                        seasonal = (1, 0, 0, seasonal_period) if seasonal_period else (0, 0, 0, 0)
                        fit = ARIMA(y, exog=X, order=(p, d, q), seasonal_order=seasonal, trend=trend).fit()
                        k = len(fit.params); denom = len(y)-d-k-1
                        if denom <= 0 or not np.isfinite(fit.aic) or not np.isfinite(fit.params).all(): continue
                        aicc = fit.aic + 2*k*(k+1)/denom
                        fits.append((aicc, (p, d, q), trend, fit, bool(fit.mle_retvals.get('converged', False))))
                    except (ValueError, np.linalg.LinAlgError, RuntimeError):
                        continue
        if not fits: raise RuntimeError('No finite ARIMA model could be fitted')
        fits.sort(key=lambda item: item[0])
        converged_fits = [item for item in fits if item[4]]
        aicc, order, trend, fit, _ = (converged_fits or fits)[0]
        selection = dict(rule='lowest AICc among optimizer-converged candidates', candidates_fitted=len(fits),
                         converged_candidates=len(converged_fits), fallback_from_nonconverged=None)
        if converged_fits and fits[0] is not converged_fits[0]:
            selection['fallback_from_nonconverged'] = dict(order=list(fits[0][1]), trend=fits[0][2], aicc=float(fits[0][0]))
        if not converged_fits:
            selection['reason'] = f'None of {len(fits)} finite candidates reported optimizer convergence; lowest-AICc nonconverged fit returned'
        fc = fit.get_forecast(horizon, exog=F); ci = np.asarray(fc.conf_int(alpha=.05)); prediction = np.asarray(fc.predicted_mean)
        if prediction.shape != (horizon,) or ci.shape != (horizon, 2) or not np.isfinite(prediction).all() or not np.isfinite(ci).all():
            raise ValueError('ARIMA forecast or interval is nonfinite or incorrectly shaped')
        resid = np.asarray(fit.resid, float)
        lb = acorr_ljungbox(resid[max(order[1], 1):], lags=[min(10, len(y)//5)], return_df=True)
    lb_value = float(lb['lb_pvalue'].iloc[0]); lb_valid = np.isfinite(lb_value)
    # statsmodels names a time trend and exog both 'x<i>'; name trend terms explicitly instead.
    trend_names = {'c': ['const'], 'ct': ['const', 'trend'], 't': ['drift'], 'n': []}[trend]
    names = trend_names + [str(k) for k in fit.param_names[len(trend_names):]]
    if X is not None:
        names[len(trend_names):len(trend_names)+X.shape[1]] = [f'x{i+1}' for i in range(X.shape[1])]
    out = dict(order=list(order), trend=trend, aicc=float(aicc), forecast=prediction.tolist(), lower=ci[:,0].tolist(), upper=ci[:,1].tolist(),
               residuals=resid.tolist(), ljung_box_p=lb_value if lb_valid else None,
               residuals_white=bool(lb_value>.05) if lb_valid else None,
               parameters={k:float(v) for k,v in zip(names, fit.params)},
               converged=bool(fit.mle_retvals.get('converged', False)),
               selection=selection, unit_root_tests=unit_root_tests,
               exog_columns=0 if X is None else X.shape[1],
               differencing_basis='training response' if X is None else 'training OLS residual after intercept and exog',
               note='Intervals condition on selected order, Gaussian errors and supplied future exog. Selection/parameter/future-regressor uncertainty is not fully included; optimizer convergence is reported separately.')
    if not lb_valid: out['ljung_box_reason'] = 'Residual test is undefined for these fitted residuals'
    if do_backtest:
        from modeling.forecast import rolling_origin
        minimum = options.get('min_train', max(12, len(y)//2, len(y)-horizon-9))
        if isinstance(minimum, bool) or not isinstance(minimum, (int, np.integer)) or minimum < 12:
            raise ValueError('ARIMA backtest min_train must be an integer>=12')
        origins = len(y)-horizon-minimum+1
        if origins > 50: raise ValueError('At most50 rolling origins; declare a later min_train or a smaller series')
        def candidate(train, h, origin):
            candidate_result = arima_forecast(train, h, max_p=max_p, max_d=max_d, max_q=max_q,
                                  seasonal_period=seasonal_period, exog=None if X is None else X[:origin],
                                  future_exog=None if X is None else X[origin:origin+h])
            if not candidate_result['converged']:
                raise RuntimeError('No ARIMA candidate converged at this origin: ' + candidate_result['selection']['reason'])
            return candidate_result['forecast']
        report = rolling_origin(y, horizon, min_train=minimum, season=seasonal_period, candidates={'arima': candidate})
        report['min_train'] = int(minimum); report['horizon'] = int(horizon)
        report['information_assumption'] = 'No exog' if X is None else 'Caller explicitly declares each held-out exog row known at its forecast origin; no availability audit supplied'
        report['selection'] = 'ADF/order/trend/parameters reselected using each training prefix only'
        out['backtest'] = report
    return out


def pca_report(X: Sequence[Sequence[float]], names: Sequence[str] | None = None, *, standardise: bool = True) -> dict:
    """Principal components: explained variance, cumulative share and loadings; standardise unless all columns share one unit."""
    from sklearn.decomposition import PCA
    A = np.asarray(X, float)
    if A.ndim != 2 or A.shape[0] < 2 or not A.shape[1] or not np.isfinite(A).all():
        raise ValueError('X must be a finite matrix with at least two observations and one feature')
    if not np.any(np.ptp(A, axis=0) > 0):
        raise ValueError('PCA variance ratios are undefined when every feature is constant')
    scale = A.std(0, ddof=1)
    Z = (A - A.mean(0)) / np.where(scale > 0, scale, 1) if standardise else A - A.mean(0)
    pca = PCA().fit(Z)
    names = list(names) if names is not None else [f'x{i}' for i in range(A.shape[1])]
    if len(names) != A.shape[1] or any(not isinstance(name, str) or not name.strip() for name in names) or len(set(names)) != len(names):
        raise ValueError('names must contain one unique nonempty label per feature')
    return dict(explained_ratio=pca.explained_variance_ratio_.tolist(), cumulative=np.cumsum(pca.explained_variance_ratio_).tolist(),
                loadings=[dict(zip(names, row)) for row in pca.components_.tolist()], scores=pca.transform(Z).tolist(), standardised=standardise,
                constant_features=np.flatnonzero(scale == 0).tolist(),
                note='Components are directions of variance, not of importance for any outcome; sign is arbitrary. Constant features are centered to zero and have no variance contribution.')


def cluster_report(X: Sequence[Sequence[float]], k_range: Sequence[int] = (2, 3, 4, 5, 6), *, seed: int = 2027, standardise: bool = True) -> dict:
    """K-means for several k with silhouette and inertia, plus stability of the best k (adjusted Rand index between reruns on 80% subsamples)."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    A = np.asarray(X, float)
    if A.ndim != 2 or len(A) < 3 or not A.shape[1] or not np.isfinite(A).all():
        raise ValueError('X must be a finite matrix with at least three observations and one feature')
    scale = A.std(0, ddof=1)
    Z = (A - A.mean(0)) / np.where(scale > 0, scale, 1) if standardise else A
    counts = list(k_range)
    if not counts or any(isinstance(k, bool) or not isinstance(k, (int, np.integer)) or k < 2 for k in counts):
        raise ValueError('k_range must contain integers of at least two')
    unique_count = len(np.unique(Z, axis=0))
    rows = []
    skipped = []
    for k in dict.fromkeys(counts):
        if k >= len(Z) or k > unique_count:
            skipped.append(dict(k=int(k), reason='Needs k < observation count and k <= distinct observation count'))
            continue
        km = KMeans(k, n_init=10, random_state=seed).fit(Z)
        rows.append(dict(k=int(k), silhouette=float(silhouette_score(Z, km.labels_)), inertia=float(km.inertia_)))
    if not rows:
        raise ValueError('No admissible k can be assessed by silhouette on these observations')
    best = max(rows, key=lambda r: r['silhouette'])
    rng = np.random.default_rng(seed)
    base = KMeans(best['k'], n_init=10, random_state=seed).fit(Z)
    ari = []
    skipped_subsamples = 0
    for _ in range(20):
        idx = rng.choice(len(Z), int(.8 * len(Z)), replace=False)
        if len(idx) < best['k'] or len(np.unique(Z[idx], axis=0)) < best['k']:
            skipped_subsamples += 1
            continue
        sub = KMeans(best['k'], n_init=10, random_state=int(rng.integers(1 << 30))).fit(Z[idx])
        ari.append(adjusted_rand_score(base.labels_[idx], sub.labels_))
    return dict(by_k=rows, skipped_k=skipped, best_k=best['k'], labels=base.labels_.tolist(), centres=base.cluster_centers_.tolist(),
                stability_ari_mean=float(np.mean(ari)) if ari else None,
                stability=dict(status='computed' if ari else 'undefined', successful_subsamples=len(ari), skipped_subsamples=skipped_subsamples,
                               reason=None if ari else 'No subsample had enough distinct observations for the selected k'),
                constant_features=np.flatnonzero(scale == 0).tolist(),
                note='Silhouette below about 0.25 means little cluster structure; a stability ARI below 0.7 means the grouping depends on the sample.')
