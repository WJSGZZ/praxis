"""Bounded supervised CV using fold-local scikit-learn pipelines and baselines.

This checks predictions and split mechanics, not the caller's scientific design.
Only finite numerical features (or explicit None) and finite targets are accepted.
"""
from __future__ import annotations

from importlib.metadata import version
from numbers import Integral, Real
import warnings

import numpy as np

MAX_ROWS = 5000
MAX_FEATURES = 100
MAX_CELLS = 100_000
MAX_FOLDS = 10


def _number(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f'{name} must be a finite real number, not boolean')
    try:
        result = float(value)
    except (OverflowError, TypeError, ValueError) as error:
        raise ValueError(f'{name} must be a finite real number') from error
    if not np.isfinite(result):
        raise ValueError(f'{name} must be a finite real number')
    return result


def _integer(value, name, lower, upper):
    # JSON Schema integers include 2.0. Normalize that spelling, preserving the
    # rejection of booleans, fractional numbers and nonfinite values.
    try:
        number = float(value) if isinstance(value, Real) and not isinstance(value, (bool, np.bool_)) else np.nan
    except (OverflowError, ValueError, TypeError):
        number = np.nan
    if not np.isfinite(number) or not number.is_integer() or not lower <= number <= upper:
        raise ValueError(f'{name} must be an integer between {lower} and {upper}')
    return int(number)


def _finite(values, name):
    if not np.isfinite(np.asarray(values, dtype=float)).all():
        raise ValueError(f'{name} exceeds finite numerical range')


def cross_validate_predictor(X, y, *, task, split, n_splits=5, groups=None,
                             seed=2027, ridge_alpha=1.0, logistic_c=1.0):
    """Compare Ridge or binary LogisticRegression with a training-only Dummy.

    iid explicitly assumes independent exchangeable rows; group assesses held-out
    groups, assuming exchangeable independent groups. Neither is a future-time
    split. None features are median-imputed inside each training-fold pipeline.
    Returns per-fold indices/metrics and row-weighted OOF scores, without tuning,
    an all-data refit, confidence intervals, deployment calibration or causality.
    """
    from sklearn.dummy import DummyClassifier, DummyRegressor
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import accuracy_score, brier_score_loss, mean_absolute_error, root_mean_squared_error
    from sklearn.model_selection import GroupKFold, KFold, StratifiedGroupKFold, StratifiedKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    if not isinstance(task, str) or task not in ('regression', 'binary_classification'):
        raise ValueError('task must be regression or binary_classification')
    if not isinstance(split, str) or split not in ('iid', 'group'):
        raise ValueError('split must be iid or group; use the time-series workflow for time-dependent prediction')
    seed = _integer(seed, 'seed', 0, 2**32 - 1)
    n_splits = _integer(n_splits, 'n_splits', 2, MAX_FOLDS)
    ridge_alpha = _number(ridge_alpha, 'ridge_alpha')
    logistic_c = _number(logistic_c, 'logistic_c')
    if ridge_alpha <= 0 or logistic_c <= 0:
        raise ValueError('ridge_alpha and logistic_c must be strictly positive')
    try:
        raw = np.asarray(X, dtype=object)
        target = np.asarray(y, dtype=object)
    except (ValueError, TypeError) as error:
        raise ValueError('X must be a rectangular matrix and y a one-dimensional target') from error
    if raw.ndim != 2 or not 4 <= len(raw) <= MAX_ROWS or not 1 <= raw.shape[1] <= MAX_FEATURES:
        raise ValueError(f'X must have 4..{MAX_ROWS} rows and 1..{MAX_FEATURES} columns')
    if raw.size > MAX_CELLS:
        raise ValueError(f'X exceeds the {MAX_CELLS} cell budget')
    if target.ndim != 1 or len(target) != len(raw):
        raise ValueError('y must contain exactly one target per X row')
    if n_splits > len(raw):
        raise ValueError('n_splits exceeds the sample count')
    data = np.array([[np.nan if item is None else _number(item, 'X') for item in row] for row in raw])
    target = np.array([_number(item, 'y') for item in target])
    if np.isnan(data).all(axis=0).any():
        raise ValueError('Every feature needs at least one observed value')
    classification = task == 'binary_classification'
    if classification and set(target.tolist()) != {0.0, 1.0}:
        raise ValueError('binary_classification requires both labels 0 and 1; label 1 is the positive class')

    labels = None
    if split == 'iid':
        if groups is not None:
            raise ValueError('groups cannot be ignored by iid splitting; choose split=group')
        if classification:
            if np.bincount(target.astype(int), minlength=2).min() < n_splits:
                raise ValueError('iid classification requires at least n_splits observations of each class')
            splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        else:
            splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
        partitions = list(splitter.split(data, target))
    else:
        if groups is None or isinstance(groups, (str, bytes)):
            raise ValueError('group splitting requires exactly one group ID per row')
        labels = np.asarray(groups, dtype=object)
        if labels.ndim != 1 or len(labels) != len(data):
            raise ValueError('groups must contain exactly one group ID per row')
        kinds = set()
        normalized = []
        for item in labels:
            if isinstance(item, str) and item.strip():
                try:
                    item.encode('utf-8')
                except UnicodeEncodeError as error:
                    raise ValueError('Group IDs must be valid Unicode strings') from error
                kinds.add('str')
                normalized.append(item)
            elif isinstance(item, Integral) and not isinstance(item, (bool, np.bool_)):
                kinds.add('int')
                normalized.append(int(item))
            elif (isinstance(item, Real) and not isinstance(item, (bool, np.bool_))
                  and np.isfinite(item) and float(item).is_integer()):
                kinds.add('int')
                normalized.append(int(item))
            else:
                raise ValueError('Group IDs must be nonempty strings or integers, without missing IDs')
        if len(kinds) != 1:
            raise ValueError('Group IDs must use one consistent type; normalize mixed IDs upstream')
        labels = np.asarray(normalized, dtype=object)
        identities = {item: index for index, item in enumerate(dict.fromkeys(labels.tolist()))}
        if len(identities) < n_splits:
            raise ValueError('group splitting needs at least n_splits distinct groups')
        encoded = np.array([identities[item] for item in labels])
        splitter = (StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed) if classification
                    else GroupKFold(n_splits=n_splits, shuffle=True, random_state=seed))
        partitions = list(splitter.split(data, target, groups=encoded))

    coverage = np.zeros(len(data), dtype=int)
    for fold, (train, validation) in enumerate(partitions):
        if not len(train) or not len(validation) or np.intersect1d(train, validation).size:
            raise ValueError(f'Fold {fold} has an empty or overlapping train/validation partition')
        coverage[validation] += 1
        if np.isnan(data[train]).all(axis=0).any():
            raise ValueError(f'Fold {fold} has a training feature with no observed values; imputation cannot learn it')
        if classification and len(np.unique(target[train])) != 2:
            raise ValueError(f'Fold {fold} training data must contain both classes')
        if labels is not None and set(labels[train]) & set(labels[validation]):
            raise ValueError(f'Fold {fold} crosses group identities')
    if not (coverage == 1).all():
        raise ValueError('Validation partitions must cover every row exactly once')

    def metrics(observed, prediction, predicted_class=None):
        if classification:
            result = dict(brier=float(brier_score_loss(observed, prediction, pos_label=1)),
                          accuracy=float(accuracy_score(observed, predicted_class)))
        else:
            result = dict(rmse=float(root_mean_squared_error(observed, prediction)),
                          mae=float(mean_absolute_error(observed, prediction)))
        _finite(list(result.values()), 'Metrics')
        return result

    oof = np.empty(len(data))
    baseline_oof = np.empty(len(data))
    classes_oof = np.empty(len(data), dtype=int) if classification else None
    baseline_classes = np.empty(len(data), dtype=int) if classification else None
    folds = []
    for fold, (train, validation) in enumerate(partitions):
        estimator = (LogisticRegression(C=logistic_c, solver='lbfgs', max_iter=500, random_state=seed) if classification
                     else Ridge(alpha=ridge_alpha, solver='svd'))
        pipeline = Pipeline([('impute', SimpleImputer(strategy='median')),
                             ('scale', StandardScaler()), ('predictor', estimator)])
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', ConvergenceWarning)
                pipeline.fit(data[train], target[train])
            median = pipeline.named_steps['impute'].statistics_
            mean = pipeline.named_steps['scale'].mean_
            scale = pipeline.named_steps['scale'].scale_
            _finite(np.r_[median, mean, scale], 'Training preprocessing')
            dummy = DummyClassifier(strategy='prior') if classification else DummyRegressor(strategy='mean')
            dummy.fit(np.zeros((len(train), 1)), target[train])
            if classification:
                prediction = pipeline.predict_proba(data[validation])[:, 1]
                base = dummy.predict_proba(np.zeros((len(validation), 1)))[:, 1]
                predicted_class = pipeline.predict(data[validation]).astype(int)
                base_class = dummy.predict(np.zeros((len(validation), 1))).astype(int)
                classes_oof[validation], baseline_classes[validation] = predicted_class, base_class
            else:
                prediction = pipeline.predict(data[validation])
                base = dummy.predict(np.zeros((len(validation), 1)))
                predicted_class = base_class = None
            _finite(prediction, 'Predictions')
            _finite(base, 'Baseline predictions')
        except (ConvergenceWarning, FloatingPointError, OverflowError) as error:
            raise ValueError(f'Fold {fold} failed numerical convergence or finite-range checks: {error}') from error
        oof[validation], baseline_oof[validation] = prediction, base
        record = dict(fold=fold, train_indices=train.tolist(), validation_indices=validation.tolist(),
                      n_train=len(train), n_validation=len(validation),
                      model_metrics=metrics(target[validation], prediction, predicted_class),
                      baseline_metrics=metrics(target[validation], base, base_class),
                      preprocessing=dict(fitted_on='training_rows_only', median=median.tolist(),
                                         mean=mean.tolist(), scale=scale.tolist()))
        if labels is not None:
            record['train_groups'] = list(dict.fromkeys(labels[train].tolist()))
            record['validation_groups'] = list(dict.fromkeys(labels[validation].tolist()))
        if classification:
            record['training_class_counts'] = np.bincount(target[train].astype(int), minlength=2).tolist()
            record['validation_class_counts'] = np.bincount(target[validation].astype(int), minlength=2).tolist()
            record['validation_has_both_classes'] = len(np.unique(target[validation])) == 2
        folds.append(record)

    result = dict(schema_version='1.0', task=task, split=split, n_rows=len(data), n_features=data.shape[1],
                  n_splits=n_splits, seed=seed, folds=folds,
                  oof_predictions=oof.tolist(), oof_baseline_predictions=baseline_oof.tolist(),
                  metrics=dict(model=metrics(target, oof, classes_oof), baseline=metrics(target, baseline_oof, baseline_classes)),
                  aggregation='row_weighted_pooled_oof; pooled RMSE is not the arithmetic mean of fold RMSEs',
                  estimator='LogisticRegression' if classification else 'Ridge',
                  estimator_parameters=dict(C=logistic_c, solver='lbfgs', max_iter=500) if classification else dict(alpha=ridge_alpha, solver='svd'),
                  baseline='training_class_prior' if classification else 'training_target_mean',
                  sample_design=dict(status='caller_declared_not_verified',
                                     assumption='Rows are independent and exchangeable' if split == 'iid' else 'Groups are independent and exchangeable; validation concerns unseen groups'),
                  backend=dict(name='scikit-learn', version=version('scikit-learn')),
                  limits=['Numeric features only; null means missing and is median-imputed per training fold.',
                          'No time-dependent split, hyperparameter search, final refit or external deployment calibration.',
                          'Observed OOF scores are descriptive under this split; no confidence interval or causal effect is inferred.',
                          'Group disjointness does not verify group independence; feature availability and upstream target leakage are not detectable from numeric arrays.',
                          'Input size, folds and optimizer iterations are bounded; this is not a wall-clock, memory or process sandbox.'])
    if classification:
        result.update(positive_class=1, decision_threshold=0.5, threshold_tie_class=0,
                      oof_classes=classes_oof.tolist(), oof_baseline_classes=baseline_classes.tolist())
    return result
