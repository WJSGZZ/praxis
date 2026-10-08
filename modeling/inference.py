"""Statistical inference and simulation tools: tests with effect sizes and assumption flags, bootstrap, Monte Carlo with a convergence
account, ODE solving with a tolerance check, ARIMA forecasts, PCA and clustering.

Each result carries the assumptions it relies on; a p-value alone is never the output."""
from __future__ import annotations

import warnings
from typing import Callable, Sequence

import numpy as np
from scipy import stats


def hypothesis_test(kind: str, a: Sequence[float], b: Sequence[float] | None = None, *, table=None, alpha: float = 0.05, groups: Sequence[Sequence[float]] | None = None) -> dict:
    """kind: welch_t, paired_t, mann_whitney, ks_2samp, anova, kruskal, chi2_independence (table), shapiro (a), correlation (a, b).

    Returns statistic, p-value, an effect size, a confidence interval where one is standard, and flags for violated assumptions."""
    flags = []
    out: dict = dict(kind=kind, alpha=alpha)
    if kind in ('welch_t', 'paired_t', 'mann_whitney', 'ks_2samp', 'correlation'):
        a, b = np.asarray(a, float), np.asarray(b, float)
    if kind == 'welch_t':
        r = stats.ttest_ind(a, b, equal_var=False)
        sp = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        diff = a.mean() - b.mean()
        ci = r.confidence_interval(1 - alpha)
        out.update(statistic=float(r.statistic), p=float(r.pvalue), difference=float(diff), ci=[float(ci.low), float(ci.high)], effect_size_cohen_d=float(diff / sp))
        for name, x in (('a', a), ('b', b)):
            if len(x) < 30 and stats.shapiro(x).pvalue < alpha:
                flags.append(f'sample {name} departs from normality (Shapiro p<{alpha}); consider mann_whitney')
    elif kind == 'paired_t':
        r = stats.ttest_rel(a, b)
        d = a - b
        ci = r.confidence_interval(1 - alpha)
        out.update(statistic=float(r.statistic), p=float(r.pvalue), mean_difference=float(d.mean()), ci=[float(ci.low), float(ci.high)], effect_size_dz=float(d.mean() / d.std(ddof=1)))
        if len(d) < 30 and stats.shapiro(d).pvalue < alpha:
            flags.append('differences depart from normality; consider a Wilcoxon signed-rank test')
    elif kind == 'mann_whitney':
        r = stats.mannwhitneyu(a, b, alternative='two-sided')
        out.update(statistic=float(r.statistic), p=float(r.pvalue), effect_size_prob_superiority=float(r.statistic / (len(a) * len(b))))
    elif kind == 'ks_2samp':
        r = stats.ks_2samp(a, b)
        out.update(statistic=float(r.statistic), p=float(r.pvalue))
    elif kind in ('anova', 'kruskal'):
        gs = [np.asarray(g, float) for g in groups]
        r = stats.f_oneway(*gs) if kind == 'anova' else stats.kruskal(*gs)
        out.update(statistic=float(r.statistic), p=float(r.pvalue), group_means=[float(g.mean()) for g in gs])
        if kind == 'anova':
            n = sum(len(g) for g in gs)
            ssb = sum(len(g) * (g.mean() - np.concatenate(gs).mean()) ** 2 for g in gs)
            sst = ((np.concatenate(gs) - np.concatenate(gs).mean()) ** 2).sum()
            out['effect_size_eta_squared'] = float(ssb / sst)
            if stats.levene(*gs).pvalue < alpha:
                flags.append('variances differ (Levene); use kruskal or a Welch-type test')
            out['n'] = n
    elif kind == 'chi2_independence':
        t = np.asarray(table, float)
        chi2, p, dof, expected = stats.chi2_contingency(t)
        out.update(statistic=float(chi2), p=float(p), dof=int(dof), effect_size_cramers_v=float(np.sqrt(stats.chi2_contingency(t, correction=False)[0] / (t.sum() * (min(t.shape) - 1)))))
        if (expected < 5).any():
            flags.append('some expected counts are below 5; the chi-square approximation is poor (consider Fisher exact for 2x2)')
    elif kind == 'shapiro':
        r = stats.shapiro(np.asarray(a, float))
        out.update(statistic=float(r.statistic), p=float(r.pvalue))
    elif kind == 'correlation':
        pr, ps = stats.pearsonr(a, b), stats.spearmanr(a, b)
        ci = pr.confidence_interval(1 - alpha)
        out.update(pearson=float(pr.statistic), pearson_p=float(pr.pvalue), pearson_ci=[float(ci.low), float(ci.high)], spearman=float(ps.statistic), spearman_p=float(ps.pvalue))
        if abs(pr.statistic - ps.statistic) > .2:
            flags.append('Pearson and Spearman differ by more than 0.2: nonlinearity or outliers')
    else:
        raise ValueError('kind must be welch_t, paired_t, mann_whitney, ks_2samp, anova, kruskal, chi2_independence, shapiro or correlation')
    out['significant'] = bool(out.get('p', out.get('pearson_p', 1.0)) < alpha)
    out['flags'] = flags
    out['note'] = 'Significance is not importance: read the effect size and interval. Several tests on one data set need a multiplicity correction.'
    return out


def bootstrap_ci(data: Sequence[float], statistic: str = 'mean', *, n_resamples: int = 5000, confidence: float = 0.95, seed: int = 2027, method: str = 'BCa') -> dict:
    """Bootstrap confidence interval for mean, median, std or a quantile such as q0.9. Independent observations are assumed."""
    x = np.asarray(data, float)
    fn: Callable
    if statistic in ('mean', 'median', 'std'):
        fn = {'mean': np.mean, 'median': np.median, 'std': lambda v, axis=-1: np.std(v, ddof=1, axis=axis)}[statistic]
    elif statistic.startswith('q'):
        q = float(statistic[1:])
        fn = lambda v, axis=-1: np.quantile(v, q, axis=axis)
    else:
        raise ValueError("statistic: mean, median, std, or q<level> such as q0.9")
    res = stats.bootstrap((x,), fn, n_resamples=n_resamples, confidence_level=confidence, method=method, random_state=np.random.default_rng(seed))
    return dict(statistic=statistic, estimate=float(fn(x)), ci=[float(res.confidence_interval.low), float(res.confidence_interval.high)], standard_error=float(res.standard_error),
                n=len(x), method=method, note='For time series or clustered data resample blocks instead; with very small n the interval is itself unreliable.')


def monte_carlo(model: Callable, distributions: dict, *, n: int = 20000, seed: int = 2027, threshold: float | None = None) -> dict:
    """Propagate input distributions through model(dict of arrays) -> array. distributions: {name: {'dist': 'norm'|'uniform'|'lognorm'|'triang'|..., 'params': {...}}}
    (scipy.stats names and keywords: norm loc/scale, uniform loc/scale, expon scale, triang c/loc/scale, ...).

    Reports the mean with its Monte Carlo standard error, quantiles, optional exceedance probability with an interval, and
    whether the estimate has settled (second half of the sample against the first)."""
    rng = np.random.default_rng(seed)
    sample = {k: getattr(stats, d['dist'])(**d.get('params', {})).rvs(size=n, random_state=rng) for k, d in distributions.items()}
    y = np.asarray(model(sample), float)
    mean, se = y.mean(), y.std(ddof=1) / np.sqrt(n)
    h = n // 2
    out = dict(n=n, mean=float(mean), mc_standard_error=float(se), sd=float(y.std(ddof=1)), quantiles={q: float(np.quantile(y, q)) for q in (.025, .05, .5, .95, .975)},
               half_sample_means=[float(y[:h].mean()), float(y[h:].mean())],
               settled=bool(abs(y[:h].mean() - y[h:].mean()) <= 3 * np.sqrt(2) * y.std(ddof=1) / np.sqrt(h)))
    if threshold is not None:
        k = int((y > threshold).sum())
        ci = stats.binomtest(k, n).proportion_ci(method='wilson')
        out['exceedance'] = dict(threshold=threshold, probability=k / n, ci=[float(ci.low), float(ci.high)])
    out['note'] = 'Monte Carlo error falls as 1/sqrt(n); the result is only as good as the input distributions, whose sources must be stated.'
    return out


def solve_ode(rhs: Callable, y0: Sequence[float], t_span: Sequence[float], t_eval: Sequence[float] | None = None, *, method: str = 'LSODA', rtol: float = 1e-8, atol: float = 1e-10,
              events: Callable | None = None) -> dict:
    """Integrate dy/dt = rhs(t, y) and repeat at 100 times tighter tolerance; the largest difference is the numerical error indicator."""
    from scipy.integrate import solve_ivp
    kw = dict(method=method, t_eval=None if t_eval is None else np.asarray(t_eval, float), events=events, dense_output=False)
    a = solve_ivp(rhs, tuple(t_span), np.asarray(y0, float), rtol=rtol, atol=atol, **kw)
    b = solve_ivp(rhs, tuple(t_span), np.asarray(y0, float), rtol=rtol / 100, atol=atol / 100, **kw)
    if not (a.success and b.success):
        raise RuntimeError(a.message if not a.success else b.message)
    n = min(a.y.shape[1], b.y.shape[1])
    err = float(np.max(np.abs(a.y[:, :n] - b.y[:, :n]))) if n else float('nan')
    out = dict(t=a.t.tolist(), y=a.y.tolist(), method=method, steps=int(a.t.size), tolerance_check_max_difference=err,
               stiff_warning=bool(method in ('RK45', 'RK23', 'DOP853') and a.nfev > 50 * max(a.t.size, 1)))
    if events is not None:
        out['events'] = [dict(t=te.tolist(), y=ye.tolist()) for te, ye in zip(a.t_events, a.y_events)]
    return out


def arima_forecast(series: Sequence[float], horizon: int, *, max_p: int = 3, max_d: int = 2, max_q: int = 3, seasonal_period: int | None = None) -> dict:
    """ARIMA: differencing order from ADF unit-root tests, p and q by AICc over a small grid; returns the forecast with 95% intervals and a residual autocorrelation test (Ljung-Box).

    Compare with `backtest_baselines` first: a model that does not beat naive and drift out of sample is not worth its complexity."""
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.tsa.arima.model import ARIMA
    y = np.asarray(series, float)
    best = None
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        # AICc is not comparable across differencing orders, so d comes from unit-root tests (ADF), and only p and q are chosen by AICc
        from statsmodels.tsa.stattools import adfuller
        z, d = y, 0
        while d < max_d and adfuller(z)[1] > .05:
            z, d = np.diff(z), d + 1
        for d in (d,):
            for p in range(max_p + 1):
                for q in range(max_q + 1):
                    try:
                        seasonal = (1, 0, 0, seasonal_period) if seasonal_period else (0, 0, 0, 0)
                        fit = ARIMA(y, order=(p, d, q), seasonal_order=seasonal, trend='t' if d == 0 else 'n').fit()
                    except Exception:
                        continue
                    k = len(fit.params)
                    aicc = fit.aic + 2 * k * (k + 1) / max(len(y) - k - 1, 1)
                    if best is None or aicc < best[0]:
                        best = (aicc, (p, d, q), fit)
        if best is None:
            raise RuntimeError('No ARIMA model could be fitted')
        aicc, order, fit = best
        fc = fit.get_forecast(horizon)
        ci = fc.conf_int(alpha=.05)
        lb = acorr_ljungbox(fit.resid[max(order[1], 1):], lags=[min(10, len(y) // 5)], return_df=True)
    return dict(order=list(order), aicc=float(aicc), forecast=np.asarray(fc.predicted_mean).tolist(), lower=np.asarray(ci)[:, 0].tolist(), upper=np.asarray(ci)[:, 1].tolist(),
                ljung_box_p=float(lb['lb_pvalue'].iloc[0]), residuals_white=bool(lb['lb_pvalue'].iloc[0] > .05), parameters={str(k): float(v) for k, v in zip(fit.param_names, fit.params)},
                note='Intervals assume the order is right and errors are Gaussian; they are too narrow when the order was chosen from the same data.')


def pca_report(X: Sequence[Sequence[float]], names: Sequence[str] | None = None, *, standardise: bool = True) -> dict:
    """Principal components: explained variance, cumulative share and loadings; standardise unless all columns share one unit."""
    from sklearn.decomposition import PCA
    A = np.asarray(X, float)
    Z = (A - A.mean(0)) / A.std(0, ddof=1) if standardise else A - A.mean(0)
    pca = PCA().fit(Z)
    names = list(names) if names else [f'x{i}' for i in range(A.shape[1])]
    return dict(explained_ratio=pca.explained_variance_ratio_.tolist(), cumulative=np.cumsum(pca.explained_variance_ratio_).tolist(),
                loadings=[dict(zip(names, row)) for row in pca.components_.tolist()], scores=pca.transform(Z).tolist(), standardised=standardise,
                note='Components are directions of variance, not of importance for any outcome; sign is arbitrary.')


def cluster_report(X: Sequence[Sequence[float]], k_range: Sequence[int] = (2, 3, 4, 5, 6), *, seed: int = 2027, standardise: bool = True) -> dict:
    """K-means for several k with silhouette and inertia, plus stability of the best k (adjusted Rand index between reruns on 80% subsamples)."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    A = np.asarray(X, float)
    Z = (A - A.mean(0)) / A.std(0, ddof=1) if standardise else A
    rows = []
    for k in k_range:
        if k >= len(Z):
            continue
        km = KMeans(k, n_init=10, random_state=seed).fit(Z)
        rows.append(dict(k=int(k), silhouette=float(silhouette_score(Z, km.labels_)), inertia=float(km.inertia_)))
    best = max(rows, key=lambda r: r['silhouette'])
    rng = np.random.default_rng(seed)
    base = KMeans(best['k'], n_init=10, random_state=seed).fit(Z)
    ari = []
    for _ in range(20):
        idx = rng.choice(len(Z), int(.8 * len(Z)), replace=False)
        sub = KMeans(best['k'], n_init=10, random_state=int(rng.integers(1 << 30))).fit(Z[idx])
        ari.append(adjusted_rand_score(base.labels_[idx], sub.labels_))
    return dict(by_k=rows, best_k=best['k'], labels=base.labels_.tolist(), centres=base.cluster_centers_.tolist(), stability_ari_mean=float(np.mean(ari)),
                note='Silhouette below about 0.25 means little cluster structure; a stability ARI below 0.7 means the grouping depends on the sample.')
