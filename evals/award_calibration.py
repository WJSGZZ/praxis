"""Developer-only grouped award-label replay; never a contest award probability oracle.

Run ``python -m evals.award_calibration --input records.json --output new.json``.
External holdout: replace --input with --train-json TRAIN --test-json TEST.
Inputs contain records with id/problem/sha256/award/features. Baseline keys are
explicit mappings (--figures-key, --chars-key, --pages-key), never inferred counts.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import warnings

import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

AWARDS = ('S', 'H', 'M', 'F', 'O')
LOG_CLIP = 1e-15
BOOTSTRAP_SEED = 20261031


def validate_records(records):
    """Reject ambiguous identities and nonfinite measurements before any fitting."""
    if not isinstance(records, list) or not records:
        raise ValueError('records must be a nonempty list')
    ids, hashes = set(), set()
    for r in records:
        if not isinstance(r, dict):
            raise ValueError('each record must be an object')
        for field in ('id', 'problem', 'sha256'):
            if not isinstance(r.get(field), str) or not r[field].strip():
                raise ValueError(f'{field} must be a nonempty string')
        if r['id'] in ids:
            raise ValueError(f'duplicate id: {r["id"]}')
        ids.add(r['id'])
        if not re.fullmatch(r'[0-9a-fA-F]{64}', r['sha256']):
            raise ValueError('sha256 must contain 64 hexadecimal characters')
        digest = r['sha256'].lower()
        if digest in hashes:
            raise ValueError(f'duplicate sha256: {digest}')
        hashes.add(digest)
        if r.get('award') not in AWARDS:
            raise ValueError(f'award must be one of {AWARDS}')
        if not isinstance(r.get('features'), dict):
            raise ValueError('features must be an object')
        for key, value in r['features'].items():
            if not isinstance(key, str) or not key:
                raise ValueError('feature names must be nonempty strings')
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError('feature values must be a number or null')
            try:
                finite = math.isfinite(value)
            except (OverflowError, TypeError):
                finite = False
            if not finite:
                raise ValueError('feature values must be finite')
    _task_registry(records)


def _task_registry(records):
    """Check a declared common task ontology, without judging answer semantics."""
    status = {}
    for problem in sorted({r['problem'] for r in records}):
        rows = [r for r in records if r['problem'] == problem]
        supplied = any('task_ids' in r or 'summary_answered_task_ids' in r for r in rows)
        if not supplied:
            status[problem] = 'not_supplied'
            continue
        shared = None
        for row in rows:
            tasks = row.get('task_ids')
            answers = row.get('summary_answered_task_ids')
            for value, name in [(tasks, 'task_ids')]:
                if (not isinstance(value, list) or
                    any(not isinstance(v, str) or not v.strip() for v in value) or
                    len(set(value)) != len(value)):
                    raise ValueError(f'{name} must contain unique task IDs for every shared task record')
            if not tasks:
                raise ValueError('shared task list must be nonempty')
            if shared is None:
                shared = set(tasks)
            elif shared != set(tasks):
                raise ValueError('same-problem papers must use the same shared task list')
            feature = row['features'].get('summary.answered_share')
            if answers is None:
                reason = row.get('summary_coverage_unknown_reason')
                if ('summary_answered_task_ids' not in row or feature is not None or
                    not isinstance(reason, str) or not reason.strip()):
                    raise ValueError('unknown summary coverage needs explicit nulls and a reason')
                continue
            if (not isinstance(answers, list) or
                any(not isinstance(v, str) or not v.strip() for v in answers) or
                len(set(answers)) != len(answers) or not set(answers).issubset(tasks)):
                raise ValueError('answered IDs must be unique members of the shared task list')
            if feature is not None and abs(feature - len(answers)/len(tasks)) > 1e-12:
                raise ValueError('coverage feature disagrees with declared shared task IDs')
        status[problem] = 'validated'
    return status


def classification_metrics(truth, probabilities):
    """Five-class confusion; absent truth classes excluded from macro recall.

    Brier is mean(sum((p-onehot)**2)), not divided by five. Log loss clips
    the true-class probability to [1e-15,1]; no re-normalization after clipping.
    Argmax ties resolve to the lowest class in S,H,M,F,O order.
    """
    if not truth or any(a not in AWARDS for a in truth):
        raise ValueError('truth must contain supported award labels')
    p = np.asarray(probabilities, dtype=float)
    if p.shape != (len(truth), 5) or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError('probabilities must be finite five-class distributions')
    if not np.allclose(p.sum(axis=1), 1, rtol=0, atol=1e-10):
        raise ValueError('probability rows must sum to one')
    y = np.array([AWARDS.index(a) for a in truth])
    predicted = p.argmax(axis=1)
    confusion = np.zeros((5, 5), dtype=int)
    np.add.at(confusion, (y, predicted), 1)
    support = confusion.sum(axis=1)
    recalls = {a: float(confusion[i, i]/support[i]) if support[i] else None for i, a in enumerate(AWARDS)}
    target = np.eye(5)[y]
    return dict(n=len(truth), confusion_matrix=confusion.tolist(),
                confusion_axes={'rows':'true', 'columns':'predicted', 'order':list(AWARDS)},
                support=dict(zip(AWARDS, support.tolist())), per_class_recall=recalls,
                macro_recall=float(np.mean([v for v in recalls.values() if v is not None])),
                exact_accuracy=float(np.mean(predicted == y)),
                adjacent_accuracy=float(np.mean(np.abs(predicted-y) <= 1)),
                brier=float(np.mean(np.sum((p-target)**2, axis=1))),
                log_loss=float(-np.mean(np.log(np.clip(p[np.arange(len(y)), y], LOG_CLIP, 1)))))


def _fit_predict(train, test, model_keys=None):
    # Column discovery, imputation, filtering, and scaling all use train only.
    keys = list(model_keys) if model_keys is not None else sorted({k for r in train for k in r['features']})
    def matrix(rows):
        return np.array([[r['features'].get(k) if r['features'].get(k) is not None else np.nan
                          for k in keys] for r in rows], dtype=float).reshape(len(rows), len(keys))
    x, z = matrix(train), matrix(test)
    medians, all_missing = [], []
    for j, key in enumerate(keys):
        finite = x[np.isfinite(x[:, j]), j]
        if len(finite):
            medians.append(float(np.median(finite)))
        else:
            medians.append(0.)
            all_missing.append(key)
    x = np.where(np.isfinite(x), x, medians)
    z = np.where(np.isfinite(z), z, medians)
    with np.errstate(over='raise', invalid='raise'):
        try:
            mean, std = x.mean(axis=0), x.std(axis=0)
        except FloatingPointError as e:
            raise ValueError('training preprocessing overflow; rescale finite feature inputs') from e
    keep = std > 0
    classes = [a for a in AWARDS if any(r['award'] == a for r in train)]
    missing = [a for a in AWARDS if a not in classes]
    metadata = dict(train_problems=sorted({r['problem'] for r in train}),
                    test_problems=sorted({r['problem'] for r in test}),
                    train_ids=[r['id'] for r in train], test_ids=[r['id'] for r in test],
                    training_support={a:sum(r['award']==a for r in train) for a in AWARDS},
                    supported_awards=classes, training_missing_awards=missing,
                    preprocessing=dict(feature_keys=keys, median=dict(zip(keys, medians)),
                                       mean=dict(zip(keys, mean.tolist())),
                                       scale=dict(zip(keys, std.tolist())),
                                       kept_features=[k for k,b in zip(keys,keep) if b],
                                       removed_zero_variance=[k for k,b in zip(keys,keep) if not b],
                                       all_missing=all_missing),
                    fallback_reason=None, convergence_warnings=[])
    p = np.zeros((len(test), 5))
    if len(classes) < 2 or not keep.any():
        metadata['fallback_reason'] = 'training_single_class' if len(classes) < 2 else 'no_effective_features'
        counts = np.array([sum(r['award']==a for r in train) for a in AWARDS])
        p[:] = counts/len(train)  # empirical unweighted training prior, explicitly a fallback
    else:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            try:
                xt = (x[:, keep]-mean[keep])/std[keep]
                zt = (z[:, keep]-mean[keep])/std[keep]
            except FloatingPointError as e:
                raise ValueError('feature standardization overflow') from e
        model = LogisticRegression(C=1, max_iter=2000, class_weight='balanced', random_state=BOOTSTRAP_SEED)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ConvergenceWarning)
            model.fit(xt, [r['award'] for r in train])
        metadata['convergence_warnings'] = [str(w.message) for w in caught]
        fitted = model.predict_proba(zt)
        for j, award in enumerate(model.classes_):
            p[:, AWARDS.index(award)] = fitted[:, j]
        metadata['iterations'] = model.n_iter_.tolist()
    predictions = []
    for r, dist in zip(test, p):
        predictions.append(dict(id=r['id'], problem=r['problem'], sha256=r['sha256'],
                                true_award=r['award'], predicted_award=AWARDS[int(dist.argmax())],
                                probabilities=dict(zip(AWARDS, dist.tolist())),
                                expected_ordinal=float(dist@np.arange(5)),
                                supported_awards=classes,
                                training_missing_awards=missing,
                                fallback_reason=metadata['fallback_reason']))
    return predictions, metadata


def _baseline_keys(baseline_keys):
    if baseline_keys is None:
        return {}
    if not isinstance(baseline_keys, dict) or set(baseline_keys)-{'figures','chars','pages'}:
        raise ValueError('baseline_keys may map figures/chars/pages only')
    if any(not isinstance(v,str) or not v for v in baseline_keys.values()):
        raise ValueError('baseline feature keys must be nonempty strings')
    return dict(baseline_keys)


def _model_keys(records, model_keys):
    if model_keys is None:
        return None
    if not isinstance(model_keys,list) or any(not isinstance(k,str) or not k for k in model_keys):
        raise ValueError('model_keys must be a list of feature names')
    if len(set(model_keys)) != len(model_keys):
        raise ValueError('duplicate model feature key')
    known={k for r in records for k in r['features']}
    if set(model_keys)-known:
        raise ValueError(f'unknown model feature keys: {sorted(set(model_keys)-known)}')
    return list(model_keys)


def _pairs(records, predictions, keys):
    pred = {p['id']:p for p in predictions}
    pairs = []
    for i, a in enumerate(records):
        for b in records[i+1:]:
            if a['problem'] != b['problem'] or a['award'] == b['award']:
                continue
            hi, lo = (a,b) if AWARDS.index(a['award'])>AWARDS.index(b['award']) else (b,a)
            delta = pred[hi['id']]['expected_ordinal']-pred[lo['id']]['expected_ordinal']
            # Deterministic tolerance handles floating roundoff only, not measurement noise.
            model = 0.5 if abs(delta)<=1e-12 else float(delta>0)
            baselines = {}
            for name, key in keys.items():
                av, bv = hi['features'].get(key), lo['features'].get(key)
                baselines[name] = None if av is None or bv is None else (0.5 if av==bv else float(av>bv))
            pairs.append(dict(problem=hi['problem'],higher_id=hi['id'],lower_id=lo['id'],
                              award_pair=f'{hi["award"]}_vs_{lo["award"]}',model=model,baselines=baselines))
    return pairs


def _pair_score(pairs, method):
    values = [p['model'] if method == 'model' else p['baselines'][method] for p in pairs]
    return dict(pairs=len(values), wins=sum(v==1 for v in values),
                ties=sum(v==.5 for v in values), losses=sum(v==0 for v in values),
                abstentions=sum(v is None for v in values),
                score=sum(v for v in values if v is not None)/len(values) if values else None,
                coverage=sum(v is not None for v in values)/len(values) if values else None)


def _ranking(pairs, keys):
    ranking = dict(pairs=len(pairs),model=_pair_score(pairs,'model'),
                   baselines={name:_pair_score(pairs,name) for name in keys},by_award_pair={})
    # Include empty O/M/H contrasts so an uncovered award pair is visible.
    types = sorted({p['award_pair'] for p in pairs}|{'O_vs_M','O_vs_H','M_vs_H'})
    for group in types:
        subset=[p for p in pairs if p['award_pair']==group]
        ranking['by_award_pair'][group]=dict(pairs=len(subset),model=_pair_score(subset,'model'),
                                            baselines={name:_pair_score(subset,name) for name in keys})
    return ranking


def _interval(values):
    finite=[v for v in values if v is not None]
    if not finite:
        return None
    return dict(lower=float(np.quantile(finite,.025)),upper=float(np.quantile(finite,.975)),
                valid_replicates=len(finite))


def _summarize(records, predictions, folds, keys, repetitions, mode):
    if isinstance(repetitions,bool) or not isinstance(repetitions,int) or repetitions<0:
        raise ValueError('bootstrap_repetitions must be a nonnegative integer')
    pred={p['id']:p for p in predictions}
    ordered=[pred[r['id']] for r in records]
    distributions=[[p['probabilities'][a] for a in AWARDS] for p in ordered]
    metrics=classification_metrics([r['award'] for r in records],distributions)
    pairs=_pairs(records,predictions,keys)
    ranking=_ranking(pairs,keys)
    best=max(keys, key=lambda k:ranking['baselines'][k]['score']) if keys and pairs else None
    ranking['best_baseline']=best
    ranking['model_minus_best_baseline']=(ranking['model']['score']-ranking['baselines'][best]['score']) if best else None
    topics=sorted({r['problem'] for r in records})
    intervals=None
    if len(topics)>1 and repetitions:
        rng=np.random.default_rng(BOOTSTRAP_SEED)
        metric_samples={k:[] for k in ['exact_accuracy','adjacent_accuracy','macro_recall','brier','log_loss']}
        score_samples={k:[] for k in ['model',*keys]}
        delta_samples=[]
        for _ in range(repetitions):
            draw=rng.choice(topics,len(topics),replace=True)
            indices=[i for topic in draw for i,r in enumerate(records) if r['problem']==topic]
            repeated_pairs=[p for topic in draw for p in pairs if p['problem']==topic]
            m=classification_metrics([records[i]['award'] for i in indices],[distributions[i] for i in indices])
            for key in metric_samples:
                metric_samples[key].append(m[key])
            for key in score_samples:
                score_samples[key].append(_pair_score(repeated_pairs,key)['score'])
            if best:
                a,b=score_samples['model'][-1],score_samples[best][-1]
                delta_samples.append(None if a is None or b is None else a-b)
        intervals=dict(classification={k:_interval(v) for k,v in metric_samples.items()},
                       ranking={k:_interval(v) for k,v in score_samples.items()})
        intervals['ranking']['model_minus_best_baseline']=_interval(delta_samples)
    by_problem = {}
    for problem in topics:
        indices = [i for i, row in enumerate(records) if row['problem'] == problem]
        by_problem[problem] = dict(
            classification=classification_metrics([records[i]['award'] for i in indices],
                                                  [distributions[i] for i in indices]),
            ranking=_ranking([p for p in pairs if p['problem'] == problem], keys))
    return dict(schema_version=1,mode=mode,award_order=list(AWARDS),calibrated=False,
                measurement_validation=dict(task_registry=_task_registry(records),
                    summary_coverage_unknown_ids=[r['id'] for r in records
                        if 'task_ids' in r and r.get('summary_answered_task_ids') is None],
                    scope='Declared task IDs and coverage arithmetic only; no semantic answer verification.'),
                interpretation='Validation-sample predictive distributions; not actual contest award probabilities or calibrated award thresholds.',
                fixed_model=dict(algorithm='sklearn.linear_model.LogisticRegression',C=1,max_iter=2000,
                                 class_weight='balanced',hyperparameter_selection='none',sklearn_version=sklearn.__version__),
                metrics_conventions=dict(macro_recall='mean over truth classes present in the evaluated sample',
                                         brier='mean sum of five squared class errors',log_loss_clip=LOG_CLIP,
                                         log_loss_clipping='clip true-class probability only; no renormalization',
                                         argmax_ties='lowest class in fixed award_order',
                                         ranking_tie_tolerance=1e-12,
                                         baseline_abstentions='zero credit, retained in shared pair denominator; coverage reported',
                                         best_baseline='maximum descriptive score among caller-prespecified quantities; fixed identity in paired bootstrap; no selection-adjusted superiority claim'),
                bootstrap=dict(unit='problem',repetitions=repetitions,seed=BOOTSTRAP_SEED,
                               method='percentile 95%; fixed out-of-fold predictions, no refitting',
                               limitation='Convenience-sample uncertainty conditional on fitted predictions; not population calibration.',
                               evaluated_topics=len(topics)),
                baseline_keys=keys,predictions=ordered,folds=folds,classification=metrics,ranking=ranking,
                pair_results=pairs,by_problem=by_problem,confidence_intervals=intervals)


def evaluate(records, *, baseline_keys=None, model_keys=None, bootstrap_repetitions=1000):
    """Leave each entire problem out, with fixed model and train-only transforms."""
    validate_records(records)
    keys=_baseline_keys(baseline_keys)
    selected=_model_keys(records,model_keys)
    topics=sorted({r['problem'] for r in records})
    if len(topics)<2:
        raise ValueError('leave-one-problem-out requires at least two problems')
    predictions,folds=[],[]
    for topic in topics:
        train=[r for r in records if r['problem']!=topic]
        test=[r for r in records if r['problem']==topic]
        p,metadata=_fit_predict(train,test,selected)
        metadata['held_out_problem']=topic
        predictions.extend(p);folds.append(metadata)
    result=_summarize(records,predictions,folds,keys,bootstrap_repetitions,'leave_one_problem_out')
    result['model_keys']=selected
    return result


def evaluate_external(train, test, *, baseline_keys=None, model_keys=None, bootstrap_repetitions=1000):
    """Explicit external holdout; test labels are accessed only for evaluation."""
    validate_records(train);validate_records(test)
    if {r['problem'] for r in train}&{r['problem'] for r in test}:
        raise ValueError('train/test problem overlap')
    if {r['sha256'].lower() for r in train}&{r['sha256'].lower() for r in test}:
        raise ValueError('train/test sha256 overlap')
    if {r['id'] for r in train}&{r['id'] for r in test}:
        raise ValueError('train/test id overlap')
    keys=_baseline_keys(baseline_keys)
    selected=_model_keys(train,model_keys)
    p,metadata=_fit_predict(train,test,selected)
    result=_summarize(test,p,[metadata],keys,bootstrap_repetitions,'external_holdout')
    result['model_keys']=selected
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--train-json',type=Path)
    parser.add_argument('--test-json',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--model-keys',help='JSON array or comma-separated prespecified feature names; omitted uses training columns')
    for name in ('figures','chars','pages'):
        parser.add_argument(f'--{name}-key')
    args=parser.parse_args(argv)
    if args.output.exists():
        parser.error('output already exists; refusing to overwrite')
    if args.input is not None:
        if args.train_json is not None or args.test_json is not None:
            parser.error('--input cannot be combined with external holdout inputs')
    elif args.train_json is None or args.test_json is None:
        parser.error('provide --input or both --train-json and --test-json')
    keys={n:getattr(args,f'{n}_key') for n in ('figures','chars','pages') if getattr(args,f'{n}_key')}
    def load(path):
        return json.loads(path.read_text(encoding='utf-8'))
    try:
        selected=None
        if args.model_keys is not None:
            selected=(json.loads(args.model_keys) if args.model_keys.lstrip().startswith('[')
                      else [k.strip() for k in args.model_keys.split(',')])
        result=(evaluate(load(args.input),baseline_keys=keys,model_keys=selected) if args.input is not None
                else evaluate_external(load(args.train_json),load(args.test_json),baseline_keys=keys,model_keys=selected))
        text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        with args.output.open('x',encoding='utf-8') as stream:
            stream.write(text)
    except (ValueError,OSError) as error:
        parser.error(str(error))


if __name__=='__main__':
    main()
