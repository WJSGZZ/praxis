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
from modeling.contracts import diagnostic


def ols_report(X: Sequence[Sequence[float]], y: Sequence[float], *, names: Sequence[str] | None = None, add_constant: bool = True,
               alpha: float = 0.05, covariance: str = 'nonrobust', groups: Sequence[str | int] | None = None) -> dict:
    """Ordinary least squares with confidence intervals and the usual checks; `flags` lists every problem found.

    Checks: normality of residuals (Jarque-Bera), heteroscedasticity (Breusch-Pagan), autocorrelation (Durbin-Watson, meaningful only
    when rows are ordered in time), multicollinearity (variance inflation factors), influential rows (Cook's distance above 0.5, or more than 10% of rows above 4/n) and the
    condition number. Undefined/unbounded diagnostics are null with explicit statuses and reasons; a rank-deficient fit
    retains one coefficient solution but no individual inference. With covariance='cluster', groups declares one cluster per row;
    Statsmodels supplies one-way CRV1 covariance, its finite-sample correction, and t intervals with G-1 degrees of freedom.
    Clusters must be independent of each other; dependence within a cluster is allowed. Few clusters can give unreliable inference.
    A clean report does not make the model right, and clustering does not remove confounding or repair the conditional mean model."""
    X = np.asarray(X, float)
    y = np.asarray(y, float).reshape(-1)
    if X.ndim == 1:
        X = X[:, None]
    if X.ndim != 2 or not X.size or len(y) != len(X) or not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError('X and y must be matching nonempty finite data')
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError('alpha must be between zero and one')
    n, k = X.shape
    if covariance not in ('nonrobust', 'cluster'):
        raise ValueError("covariance must be 'nonrobust' or 'cluster'")
    cluster_codes, cluster_counts = None, None
    if covariance == 'nonrobust' and groups is not None:
        raise ValueError("groups requires covariance='cluster'; group dependence must not be silently ignored")
    if covariance == 'cluster':
        if groups is None or isinstance(groups, (str, bytes)):
            raise ValueError('groups must contain one nonempty string or integer cluster identifier per observation')
        group_array = np.asarray(groups, dtype=object)
        if group_array.ndim != 1 or len(group_array) != n:
            raise ValueError('groups must contain one cluster identifier per observation')
        identities = {}
        cluster_codes = []
        for value in group_array:
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, (str, int, np.integer)) or isinstance(value, str) and not value.strip():
                raise ValueError('cluster identifiers must be nonempty strings or integers, not missing values or booleans')
            key = ('string', value) if isinstance(value, str) else ('integer', int(value))
            if key not in identities:
                identities[key] = len(identities)
            cluster_codes.append(identities[key])
        cluster_codes = np.asarray(cluster_codes, dtype=int)
        cluster_counts = np.bincount(cluster_codes)
    if n <= k + 2:
        raise ValueError('Need more observations than parameters (n > k + 2)')
    if names is not None and len(names) != k:
        raise ValueError('names must contain exactly one label per input column')
    labels = list(names) if names is not None else [f'x{i + 1}' for i in range(k)]
    design = sm.add_constant(X, has_constant='add') if add_constant else X
    cols = (['const'] if add_constant else []) + labels
    fit = sm.OLS(y, design).fit()
    if not np.isfinite(fit.params).all() or not np.isfinite(fit.resid).all():
        raise ValueError('OLS did not produce finite coefficients and residuals')
    rank = int(np.linalg.matrix_rank(design))
    identified = rank == design.shape[1]
    inference_fit = fit
    inference_status, inference_reason = None, None
    covariance_report = None
    cluster_roundoff = None
    if covariance == 'cluster':
        cluster_count = len(cluster_counts)
        if not identified:
            inference_status = 'not_reported_rank_deficient'
            inference_reason = 'Rank-deficient design; individual cluster inference requires checking estimable coefficients or contrasts'
        elif cluster_count < 2:
            inference_status = 'undefined'
            inference_reason = 'Cluster covariance and G-1 t inference require at least two independent clusters'
        else:
            inference_fit = fit.get_robustcov_results(cov_type='cluster', groups=cluster_codes,
                                                    use_correction=True, df_correction=True, use_t=True)
        matrix = None if inference_status else np.asarray(inference_fit.cov_params())
        matrix_ok = matrix is not None and np.isfinite(matrix).all()
        if not inference_status and not matrix_ok:
            inference_status = 'undefined'
            inference_reason = 'Cluster covariance is nonfinite for this design and residuals'
        covariance_report = dict(type='cluster', estimator='CRV1', status=inference_status or 'computed',
                                 clusters=cluster_count, cluster_size_min=int(cluster_counts.min()), cluster_size_max=int(cluster_counts.max()),
                                 finite_sample_correction=None if inference_status else float(cluster_count / (cluster_count - 1) * (n - 1) / (n - design.shape[1])),
                                 reference_distribution='student_t', df_inference=cluster_count - 1 if cluster_count >= 2 else None,
                                 matrix=matrix.tolist() if matrix_ok and not inference_status else None,
                                 conditions=['Clusters are independent across groups; arbitrary within-cluster dependence is allowed.',
                                             'A sufficiently large number of clusters and a correctly specified conditional mean are required for the usual asymptotic justification.'],
                                 note='One-way cluster covariance, with no automatic choice of cluster unit. It does not repair confounding, selection or misspecified effects.')
        if inference_reason:
            covariance_report['reason'] = inference_reason
        if matrix_ok and not inference_status:
            covariance_report['rank'] = int(np.linalg.matrix_rank(matrix))
            covariance_report['joint_inference_status'] = 'not_checked' if covariance_report['rank'] == design.shape[1] else 'singular_covariance'
            # A group-score cancellation can leave tiny positive variances from
            # coefficient roundoff (e.g. every cluster mean is exactly equal).
            # Scale each coefficient in its own units, using the existing OLS
            # pseudoinverse; preserve the raw covariance rather than zeroing it.
            with np.errstate(over='ignore', invalid='ignore'):
                cluster_roundoff = n * np.finfo(float).eps * (np.abs(fit.model.pinv_wexog) @ np.abs(y))
            covariance_report['coefficient_roundoff_threshold'] = [float(value) if np.isfinite(value) else None for value in cluster_roundoff]
            covariance_report['roundoff_note'] = 'n * machine epsilon * abs(OLS pseudoinverse) @ abs(y), in coefficient units. A numerical diagnostic heuristic, not a certified error bound or statistical uncertainty.'
            if np.all(~np.isfinite(inference_fit.bse) | (inference_fit.bse <= cluster_roundoff)):
                covariance_report['joint_inference_status'] = 'numerically_degenerate'
    ci = inference_fit.conf_int(alpha) if not inference_status else np.full((design.shape[1], 2), np.nan)
    resid = fit.resid
    noise = bool(np.ptp(resid) > 0)
    status = {}

    def scalar(key, value, reason, override=None):
        result, status[key] = diagnostic(value, reason=reason, status=override)
        return result

    jb_p = scalar('jarque_bera_p', jarque_bera(resid)[1] if noise else 0,
                  'Residual distribution has no variation', None if noise else 'undefined')
    has_intercept = bool(np.any((np.ptp(design, axis=0) == 0) & (design[0] != 0)))
    bp_applicable = design.shape[1] >= 2 and has_intercept
    bp_p = scalar('breusch_pagan_p', het_breuschpagan(resid, design)[1] if bp_applicable and noise else 0,
                  'Breusch-Pagan requires residual variation and at least two design columns including a nonzero constant; fitted model was not changed',
                  None if bp_applicable and noise else ('undefined' if bp_applicable else 'not_applicable'))
    dw = scalar('durbin_watson', durbin_watson(resid) if np.any(resid) else 0,
                'Zero residual sum of squares makes Durbin-Watson undefined', None if np.any(resid) else 'undefined')
    vif, vif_status = {}, {}
    for i, c in enumerate(cols):
        if c == 'const':
            continue
        if np.ptp(design[:, i]) == 0:
            vif[c], vif_status[c] = diagnostic(0, status='undefined', reason='A constant predictor has no variance for VIF')
        elif np.linalg.matrix_rank(np.delete(design, i, axis=1)) == rank:
            vif[c], vif_status[c] = diagnostic(0, status='unbounded', reason='Predictor is linearly dependent on the remaining design columns at numerical rank tolerance')
        elif design.shape[1] == 1:
            vif[c], vif_status[c] = diagnostic(0, status='not_applicable', reason='No other design column for the auxiliary VIF regression')
        else:
            vif[c], vif_status[c] = diagnostic(variance_inflation_factor(design, i), reason='Auxiliary regression gives an undefined or unbounded variance inflation factor')
    with np.errstate(divide='ignore', invalid='ignore'):
        cooks = fit.get_influence().cooks_distance[0]
    finite_cooks = cooks[np.isfinite(cooks)]
    influential = [int(i) for i in np.flatnonzero(np.isfinite(cooks) & (cooks > 4 / n))]
    status['cooks_distance'] = dict(status='computed') if len(finite_cooks) == n else dict(status='partly_undefined' if len(finite_cooks) else 'undefined', reason='Zero residual variance or unit leverage makes some Cook distances undefined', undefined_rows=np.flatnonzero(~np.isfinite(cooks)).tolist())
    flags = []
    if covariance_report is not None:
        if covariance_report['clusters'] < 30:
            flags.append(f"few clusters ({covariance_report['clusters']}): t intervals and p-values can be unreliable; 30 is a warning heuristic, not a validity threshold")
        if covariance_report['status'] != 'computed':
            flags.append(covariance_report['reason'])
        elif covariance_report['joint_inference_status'] == 'singular_covariance':
            flags.append('cluster covariance is singular: joint coefficient inference is not established')
        elif covariance_report['joint_inference_status'] == 'numerically_degenerate':
            flags.append('cluster standard errors are at numerical roundoff scale: coefficient t inference is not reported')
    if not identified:
        flags.append(f'rank-deficient design ({rank}/{design.shape[1]}): not all individual coefficients are uniquely identified')
    if jb_p is not None and jb_p < alpha:
        flags.append(f'residuals are not normal (Jarque-Bera p={jb_p:.3g}): intervals and p-values are approximate')
    if bp_p is not None and bp_p < alpha:
        flags.append(f'heteroscedasticity (Breusch-Pagan p={bp_p:.3g}): use robust standard errors or transform')
    if dw is not None and (dw < 1.5 or dw > 2.5):
        flags.append(f'residual autocorrelation (Durbin-Watson {dw:.2f}): errors are not independent if rows are ordered in time')
    big = [c for c, v in vif.items() if (v is not None and v > 10) or vif_status[c]['status'] == 'unbounded']
    if big:
        flags.append(f'multicollinearity (VIF > 10 or unbounded for {big}): individual coefficients are unstable')
    if len(finite_cooks) and (finite_cooks.max() > 0.5 or len(influential) > 0.10 * n):
        flags.append(f'influential rows: max Cook distance {finite_cooks.max():.2f}, {len(influential)} rows above 4/n')
    coefficients = []
    for index, (c, b, se, pv, (lo, hi)) in enumerate(zip(cols, fit.params, inference_fit.bse, inference_fit.pvalues, ci)):
        item = dict(name=c, estimate=float(b), inference=dict(status='computed' if identified else 'not_reported_rank_deficient'))
        if not identified:
            item['inference']['reason'] = 'Rank-deficient design; one least-squares solution is retained. Individual inference is not reported without checking estimable coefficients or contrasts'
        elif inference_status:
            item['inference'] = dict(status=inference_status, reason=inference_reason)
        coefficient_status = 'not_reported_rank_deficient' if not identified else inference_status
        coefficient_reason = inference_reason or 'Individual coefficient inference is undefined or not checked for estimability in this rank-deficient design'
        if covariance == 'cluster' and identified and not inference_status and (not np.isfinite(se) or not np.isfinite(cluster_roundoff[index]) or se <= cluster_roundoff[index]):
            coefficient_status = 'undefined'
            coefficient_reason = 'Cluster standard error is nonfinite, zero or at the numerical roundoff scale of the coefficient calculation; t inference is not reported'
            item['inference'] = dict(status=coefficient_status, reason=coefficient_reason)
        for key, value in [('std_error', se), ('p_value', pv), ('ci_low', lo), ('ci_high', hi)]:
            item[key], info = diagnostic(value, status=coefficient_status, reason=coefficient_reason)
            if identified and info['status'] != 'computed':
                item['inference'] = info
        coefficients.append(item)
    out = dict(n=n, parameters=design.shape[1], design_rank=rank,
                r2=scalar('r2', fit.rsquared, 'Zero total variation makes R squared undefined'),
                adj_r2=scalar('adj_r2', fit.rsquared_adj, 'Adjusted R squared is undefined for this response or degrees of freedom'),
                rmse=float(np.sqrt(np.mean(resid ** 2))), coefficients=coefficients,
                diagnostics=dict(jarque_bera_p=jb_p, breusch_pagan_p=bp_p, breusch_pagan=status['breusch_pagan_p'], durbin_watson=dw,
                                 vif=vif, vif_status=vif_status, condition_number=scalar('condition_number', np.linalg.cond(design), 'Singular design has an unbounded condition number'),
                                 status=status, influential_rows=influential[:20]), flags=flags)
    if covariance_report is not None:
        out['covariance'] = covariance_report
    return out



def compare_models(X: Sequence[Sequence[float]], y: Sequence[float], *, scheme: str = 'kfold', folds: int = 5, seed: int = 2027) -> dict:
    """Out-of-sample RMSE of a baseline, OLS, ridge and gradient boosting, with the fold-to-fold standard error.

    scheme 'kfold' shuffles rows; 'time' uses expanding-window splits (rows must be in time order). Each time test block is forecast
    from one fixed training origin; the last training value is held constant for the entire baseline block, without using test y.
    A model is said to beat the baseline only if its mean RMSE is lower by more than one standard error of the difference. Tuning
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
            base = np.full(len(test), y[train].mean() if scheme == 'kfold' else y[train][-1])
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
    out = dict(scheme=scheme, folds=folds, models=table,
                note='Cross-validated on the data given; reserve a final hold-out untouched by tuning before reporting performance.')
    if scheme == 'time':
        out['evaluation_design'] = 'fixed_origin_test_blocks'
        out['note'] += ' Each time fold forecasts its entire test block from the same training origin; the last-value baseline uses only the final training response. Fold RMSE combines several horizons and is not one-step rolling evaluation.'
    return out
