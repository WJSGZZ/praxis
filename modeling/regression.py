"""Linear regression with the diagnostics a report needs, and an honest model comparison against a baseline."""
from __future__ import annotations

import warnings
from typing import Sequence

import numpy as np
import statsmodels.api as sm
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, TimeSeriesSplit
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera


def ols_report(X: Sequence[Sequence[float]], y: Sequence[float], *, names: Sequence[str] | None = None, add_constant: bool = True, alpha: float = 0.05) -> dict:
    """Ordinary least squares with confidence intervals and the usual checks; `flags` lists every problem found.

    Checks: normality of residuals (Jarque-Bera), heteroscedasticity (Breusch-Pagan), autocorrelation (Durbin-Watson, meaningful only
    when rows are ordered in time), multicollinearity (variance inflation factors), influential rows (Cook's distance above 0.5, or more than 10% of rows above 4/n) and the
    condition number. A clean report does not make the model right; a flagged one says which assumption to examine."""
    X = np.asarray(X, float)
    y = np.asarray(y, float).reshape(-1)
    if X.ndim == 1:
        X = X[:, None]
    n, k = X.shape
    if n <= k + 2:
        raise ValueError('Need more observations than parameters (n > k + 2)')
    if names is not None and len(names) != k:
        raise ValueError('names must contain exactly one label per input column')
    labels = list(names) if names is not None else [f'x{i + 1}' for i in range(k)]
    design = sm.add_constant(X, has_constant='add') if add_constant else X
    cols = (['const'] if add_constant else []) + labels
    fit = sm.OLS(y, design).fit()
    ci = fit.conf_int(alpha)
    resid = fit.resid
    jb_p = float(jarque_bera(resid)[1])
    has_intercept = bool(np.any((np.ptp(design, axis=0) == 0) & (design[0] != 0)))
    bp_applicable = design.shape[1] >= 2 and has_intercept
    bp_p = float(het_breuschpagan(resid, design)[1]) if bp_applicable else None
    bp_status = dict(status='computed') if bp_applicable else dict(
        status='not_applicable', reason='Breusch-Pagan requires at least two design columns including a nonzero constant; fitted model was not changed')
    dw = float(durbin_watson(resid))
    vif = [float(variance_inflation_factor(design, i)) for i in range(design.shape[1])] if design.shape[1] > 1 else []
    vif = {c: v for c, v in zip(cols, vif) if c != 'const'} if vif else {}
    cooks = fit.get_influence().cooks_distance[0]
    influential = [int(i) for i in np.flatnonzero(cooks > 4 / n)]
    flags = []
    if jb_p < alpha:
        flags.append(f'residuals are not normal (Jarque-Bera p={jb_p:.3g}): intervals and p-values are approximate')
    if bp_p is not None and bp_p < alpha:
        flags.append(f'heteroscedasticity (Breusch-Pagan p={bp_p:.3g}): use robust standard errors or transform')
    if dw < 1.5 or dw > 2.5:
        flags.append(f'residual autocorrelation (Durbin-Watson {dw:.2f}): errors are not independent if rows are ordered in time')
    big = [c for c, v in vif.items() if v > 10]
    if big:
        flags.append(f'multicollinearity (VIF > 10 for {big}): individual coefficients are unstable')
    if cooks.max() > 0.5 or len(influential) > 0.10 * n:
        flags.append(f'influential rows: max Cook distance {cooks.max():.2f}, {len(influential)} rows above 4/n')
    return dict(n=n, parameters=design.shape[1], r2=float(fit.rsquared), adj_r2=float(fit.rsquared_adj), rmse=float(np.sqrt(np.mean(resid ** 2))),
                coefficients=[dict(name=c, estimate=float(b), std_error=float(s), p_value=float(p), ci_low=float(lo), ci_high=float(hi))
                              for c, b, s, p, (lo, hi) in zip(cols, fit.params, fit.bse, fit.pvalues, ci)],
                diagnostics=dict(jarque_bera_p=jb_p, breusch_pagan_p=bp_p, breusch_pagan=bp_status, durbin_watson=dw, vif=vif, condition_number=float(np.linalg.cond(design)),
                                 influential_rows=influential[:20]),
                flags=flags)


def compare_models(X: Sequence[Sequence[float]], y: Sequence[float], *, scheme: str = 'kfold', folds: int = 5, seed: int = 2027) -> dict:
    """Out-of-sample RMSE of a baseline, OLS, ridge and gradient boosting, with the fold-to-fold standard error.

    scheme 'kfold' shuffles rows; 'time' uses expanding-window splits (rows must be in time order) and the baseline is the previous value
    of y. A model is said to beat the baseline only if its mean RMSE is lower by more than one standard error of the difference. Tuning
    uses the training folds only; a final hold-out is still needed before reporting performance."""
    X = np.asarray(X, float)
    y = np.asarray(y, float).reshape(-1)
    if X.ndim == 1:
        X = X[:, None]
    if scheme not in ('kfold', 'time'):
        raise ValueError("scheme must be 'kfold' or 'time'")
    splitter = KFold(folds, shuffle=True, random_state=seed) if scheme == 'kfold' else TimeSeriesSplit(folds)
    errors: dict[str, list[float]] = {'baseline': [], 'ols': [], 'ridge': [], 'boosting': []}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for train, test in splitter.split(X):
            base = np.full(len(test), y[train].mean()) if scheme == 'kfold' else np.r_[y[train][-1], y[test][:-1]]
            preds = {'baseline': base}
            lin = sm.OLS(y[train], sm.add_constant(X[train], has_constant='add')).fit()
            preds['ols'] = lin.predict(sm.add_constant(X[test], has_constant='add'))
            preds['ridge'] = RidgeCV(alphas=np.logspace(-3, 3, 13)).fit(X[train], y[train]).predict(X[test])
            preds['boosting'] = HistGradientBoostingRegressor(random_state=seed, max_iter=100).fit(X[train], y[train]).predict(X[test])
            for name, p in preds.items():
                errors[name].append(float(np.sqrt(np.mean((y[test] - p) ** 2))))
    base = np.array(errors['baseline'])
    table = {}
    for name, e in errors.items():
        e = np.array(e)
        diff = base - e
        se = float(diff.std(ddof=1) / np.sqrt(len(diff))) if name != 'baseline' and len(diff) > 1 else None
        table[name] = dict(rmse=float(e.mean()), rmse_se=float(e.std(ddof=1) / np.sqrt(len(e))),
                           beats_baseline=None if name == 'baseline' else bool(diff.mean() > (se or 0.0)),
                           improvement_over_baseline=None if name == 'baseline' else float(diff.mean()))
    return dict(scheme=scheme, folds=folds, models=table,
                note='Cross-validated on the data given; reserve a final hold-out untouched by tuning before reporting performance.')
