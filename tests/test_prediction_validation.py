"""Independent arithmetic and structural counterexamples for supervised CV."""
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from modeling.prediction_validation import cross_validate_predictor


REGRESSION = dict(X=[[-1], [1], [-1], [1]], y=[-1, 1, -1, 1],
                  task='regression', split='group', groups=['a', 'a', 'b', 'b'], n_splits=2)


def test_ridge_and_dummy_have_independent_exact_answers():
    result = cross_validate_predictor(**REGRESSION)
    # Each train group has centered x/y=(-1,+1), sd(x)=1. Ridge slope:
    # sum(x*y)/(sum(x*x)+alpha)=2/(2+1). Intercept=0; errors=1/3.
    assert result['oof_predictions'] == pytest.approx([-2/3, 2/3, -2/3, 2/3], abs=1e-12)
    assert result['metrics']['model'] == pytest.approx(dict(rmse=1/3, mae=1/3))
    assert result['oof_baseline_predictions'] == [0, 0, 0, 0]
    assert result['metrics']['baseline'] == dict(rmse=1., mae=1.)
    validation_rows = []
    for fold in result['folds']:
        assert not set(fold['train_indices']) & set(fold['validation_indices'])
        assert not set(fold['train_groups']) & set(fold['validation_groups'])
        validation_rows.extend(fold['validation_indices'])
    assert sorted(validation_rows) == list(range(4))
    assert result['sample_design']['status'] == 'caller_declared_not_verified'


def test_missing_validation_value_is_imputed_from_train_only():
    result = cross_validate_predictor(X=[[0], [2], [None], [100]], y=[0, 2, 1, 100],
                                      task='regression', split='group', groups=['a', 'a', 'b', 'b'], n_splits=2)
    fold = next(f for f in result['folds'] if f['train_indices'] == [0, 1])
    assert fold['preprocessing']['median'] == [1]
    # The missing validation feature gets training median 1, not global median 2.
    # Training ridge line is y=1+(2/3)*(x-1); hence y(None)=1, y(100)=67.
    assert result['oof_predictions'][2:4] == pytest.approx([1, 67])


def test_balanced_constant_feature_classification_has_exact_baseline():
    result = cross_validate_predictor(X=[[7]] * 8, y=[0, 1] * 4, task='binary_classification',
                                      split='group', groups=['a', 'a', 'b', 'b', 'c', 'c', 'd', 'd'], n_splits=2)
    assert result['oof_predictions'] == pytest.approx([.5] * 8, abs=1e-12)
    assert result['metrics']['model'] == dict(brier=.25, accuracy=.5)
    assert result['metrics']['baseline'] == dict(brier=.25, accuracy=.5)
    assert result['positive_class'] == 1
    assert result['threshold_tie_class'] == 0


def test_json_integer_spellings_share_the_promised_group_identity():
    from scripts.mcp_server import call
    result = call('cross_validate_predictor', {**REGRESSION, 'groups': [1, 1.0, 2, 2.0],
                                               'n_splits': 2.0, 'seed': 12.0})
    assert result['metrics']['model']['rmse'] == pytest.approx(1/3)
    assert result['n_splits'] == 2 and result['seed'] == 12
    assert sorted(set(g for fold in result['folds'] for g in fold['validation_groups'])) == [1, 2]


def test_iid_is_explicit_and_metrics_use_actual_oof_denominators():
    result = cross_validate_predictor(X=[[x] for x in range(7)], y=[2*x+1 for x in range(7)],
                                      task='regression', split='iid', n_splits=3, seed=12)
    errors = [actual-prediction for actual, prediction in zip(range(1, 15, 2), result['oof_predictions'])]
    assert result['metrics']['model']['rmse'] == pytest.approx(math.sqrt(sum(e*e for e in errors)/7))
    assert result['metrics']['model']['mae'] == pytest.approx(sum(abs(e) for e in errors)/7)
    assert result['sample_design']['assumption'] == 'Rows are independent and exchangeable'
    assert sorted(i for fold in result['folds'] for i in fold['validation_indices']) == list(range(7))


@pytest.mark.parametrize('changes,match', [
    ({'X': [[1], [2, 3], [4], [5]]}, 'rectangular|columns'),
    ({'y': [1, 2]}, 'one target'),
    ({'y': [1, 2, float('nan'), 4]}, 'finite'),
    ({'y': [1, 2, True, 4]}, 'boolean'),
    ({'X': [[1], [2], [float('inf')], [4]]}, 'finite'),
    ({'X': [[1], [2], [float('nan')], [4]]}, 'finite'),
    ({'X': [[1], [2], ['3'], [4]]}, 'finite'),
    ({'X': [[None]] * 4}, 'observed'),
    ({'groups': None}, 'requires'),
    ({'groups': ['a'] * 4}, 'distinct'),
    ({'groups': ['a', 'a', 'b']}, 'one group'),
    ({'groups': [1, 1, '2', '2']}, 'consistent type'),
    ({'groups': ['a', 'a', '', 'b']}, 'Group IDs'),
    ({'n_splits': 11}, 'n_splits'),
    ({'n_splits': True}, 'n_splits'),
    ({'seed': True}, 'seed'),
    ({'ridge_alpha': 0}, 'positive'),
    ({'logistic_c': float('inf')}, 'finite'),
    ({'split': 'time'}, 'time-series'),
    ({'split': 'iid'}, 'cannot be ignored'),
])
def test_rejects_invalid_shape_numerical_design_and_budget(changes, match):
    with pytest.raises(ValueError, match=match):
        cross_validate_predictor(**{**REGRESSION, **changes})


def test_class_coverage_cannot_be_repaired_by_hiding_failed_folds():
    with pytest.raises(ValueError, match='both classes'):
        cross_validate_predictor(X=[[0], [1], [2], [3]], y=[0, 0, 1, 1], task='binary_classification',
                                 split='group', groups=['a', 'a', 'b', 'b'], n_splits=2)
    with pytest.raises(ValueError, match='each class'):
        cross_validate_predictor(X=[[0], [1], [2], [3]], y=[0, 0, 0, 1], task='binary_classification',
                                 split='iid', n_splits=2)
    with pytest.raises(ValueError, match='both labels'):
        cross_validate_predictor(X=[[0], [1], [2], [3]], y=[0, 0, 0, 0], task='binary_classification',
                                 split='iid', n_splits=2)


def test_imputer_cannot_learn_a_feature_missing_in_an_entire_training_fold():
    with pytest.raises(ValueError, match='training feature'):
        cross_validate_predictor(**{**REGRESSION, 'X': [[None], [None], [0], [1]]})


def test_single_class_validation_fold_remains_defined_and_disclosed():
    result = cross_validate_predictor(X=[[0]] * 8, y=[0, 0, 0, 0, 1, 1, 1, 1],
                                      task='binary_classification', split='group',
                                      groups=['a', 'a', 'b', 'b', 'c', 'c', 'd', 'd'], n_splits=3)
    assert any(not fold['validation_has_both_classes'] for fold in result['folds'])
    for fold in result['folds']:
        assert all(fold['training_class_counts'])
        assert math.isfinite(fold['model_metrics']['brier'])
        assert math.isfinite(fold['model_metrics']['accuracy'])


def test_input_work_budget_before_fitting():
    with pytest.raises(ValueError, match='rows'):
        cross_validate_predictor(X=[[0]] * 5001, y=[0] * 5001, task='regression', split='iid', n_splits=2)
    with pytest.raises(ValueError, match='cell budget'):
        cross_validate_predictor(X=[[0] * 100] * 1001, y=[0] * 1001, task='regression', split='iid', n_splits=2)


def test_actual_mcp_schema_error_and_subsequent_recovery():
    root = Path(__file__).resolve().parents[1]
    bad = {**REGRESSION, 'groups': ['only'] * 4}
    frames = [dict(jsonrpc='2.0', id=1, method='initialize', params={'protocolVersion': '2025-06-18'}),
              dict(jsonrpc='2.0', id=2, method='tools/list'),
              dict(jsonrpc='2.0', id=3, method='tools/call', params=dict(name='cross_validate_predictor', arguments=bad)),
              dict(jsonrpc='2.0', id=4, method='tools/call', params=dict(name='cross_validate_predictor', arguments=REGRESSION))]
    process = subprocess.run([sys.executable, '-m', 'scripts.mcp_server'], cwd=root,
                             input=''.join(json.dumps(frame)+'\n' for frame in frames), capture_output=True,
                             text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    replies = [json.loads(line) for line in process.stdout.splitlines()]
    listed = next(t for t in replies[1]['result']['tools'] if t['name'] == 'cross_validate_predictor')
    assert set(listed['inputSchema']['required']) == {'X', 'y', 'task', 'split'}
    assert replies[2]['result']['isError'] is True
    assert 'distinct groups' in replies[2]['result']['content'][0]['text']
    assert replies[3]['result']['isError'] is False
    payload = json.loads(replies[3]['result']['content'][0]['text'])
    assert payload['metrics']['model']['rmse'] == pytest.approx(1/3)
    assert payload['metrics']['baseline']['rmse'] == 1
