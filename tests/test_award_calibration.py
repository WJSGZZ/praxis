"""Independent answers and failure boundaries for developer award evaluation."""
import json
import math
import subprocess
import sys

import pytest

from evals.award_calibration import classification_metrics, evaluate, evaluate_external


def record(i, topic, award, **features):
    return dict(id=str(i), problem=topic, sha256=f'{i:064x}', award=award, features=features)


def sample():
    return [record(1,'a','O',x=4,fig=3), record(2,'a','M',x=2,fig=1),
            record(3,'b','O',x=5,fig=4), record(4,'b','H',x=1,fig=None),
            record(5,'c','O',x=6,fig=3), record(6,'c','M',x=3,fig=2)]


def test_hand_calculated_probabilities_confusion_and_losses():
    # Truth S,H,O; predictions S,M,F. Exactly one correct, all within one grade.
    truth=['S','H','O']
    p=[[.8,.1,.05,.03,.02], [.1,.2,.5,.1,.1], [.01,.02,.07,.6,.3]]
    m=classification_metrics(truth,p)
    assert m['exact_accuracy']==pytest.approx(1/3)
    assert m['adjacent_accuracy']==1
    assert m['macro_recall']==pytest.approx(1/3)  # only supported truth classes
    assert m['support']=={'S':1,'H':1,'M':0,'F':0,'O':1}
    assert m['confusion_matrix']==[[1,0,0,0,0],[0,0,1,0,0],[0]*5,[0]*5,[0,0,0,1,0]]
    expected=((.2**2+.1**2+.05**2+.03**2+.02**2)
              +(.1**2+.8**2+.5**2+.1**2+.1**2)
              +(.01**2+.02**2+.07**2+.6**2+.7**2))/3
    assert m['brier']==pytest.approx(expected)
    assert m['log_loss']==pytest.approx(-(math.log(.8)+math.log(.2)+math.log(.3))/3)
    assert classification_metrics(['O'],[[1,0,0,0,0]])['log_loss']==pytest.approx(-math.log(1e-15))


def test_lopo_training_metadata_and_missing_grades():
    result=evaluate(sample(),baseline_keys={'figures':'fig'},bootstrap_repetitions=20)
    assert len(result['predictions'])==6
    assert len(result['folds'])==3
    assert result['calibrated'] is False
    for fold in result['folds']:
        assert fold['test_problems']==[fold['held_out_problem']]
        assert fold['held_out_problem'] not in fold['train_problems']
    for p in result['predictions']:
        assert sum(p['probabilities'].values())==pytest.approx(1)
        assert p['probabilities']['S']==p['probabilities']['F']==0
        assert 'S' in p['training_missing_awards']


def test_heldout_extreme_cannot_change_median_or_scaler():
    rows=sample()
    a=evaluate(rows,bootstrap_repetitions=0)
    rows[0]['features']['x']=1e12
    b=evaluate(rows,bootstrap_repetitions=0)
    fa=next(f for f in a['folds'] if f['held_out_problem']=='a')
    fb=next(f for f in b['folds'] if f['held_out_problem']=='a')
    assert fa['preprocessing']==fb['preprocessing']
    assert fa['preprocessing']['median']['x']==4.0  # sorted training x = 1,3,5,6
    assert fa['preprocessing']['mean']['x']==3.75


def test_all_missing_zero_variance_and_single_class_prior():
    train=[record(1,'a','O',x=None,y=2),record(2,'b','M',x=None,y=2),record(3,'c','M',x=None,y=2)]
    test=[record(4,'d','H',x=100,y=999)]
    r=evaluate_external(train,test,bootstrap_repetitions=20)
    fold=r['folds'][0]
    assert fold['fallback_reason']=='no_effective_features'
    assert fold['preprocessing']['all_missing']==['x']
    assert fold['preprocessing']['kept_features']==[]
    assert r['predictions'][0]['probabilities']['M']==pytest.approx(2/3)
    assert r['predictions'][0]['probabilities']['O']==pytest.approx(1/3)
    assert r['confidence_intervals'] is None  # one test topic
    r=evaluate_external(train[:1],test,bootstrap_repetitions=0)
    assert r['folds'][0]['fallback_reason']=='training_single_class'
    assert r['predictions'][0]['probabilities']['O']==1


@pytest.mark.parametrize('change,match',[
    (lambda r:r[1].update(id=r[0]['id']),'duplicate id'),
    (lambda r:r[2].update(sha256=r[0]['sha256']),'duplicate sha256'),
    (lambda r:r[0].update(award='A'),'award'),
    (lambda r:r[0]['features'].update(x=float('nan')),'finite'),
    (lambda r:r[0]['features'].update(x=float('inf')),'finite'),
    (lambda r:r[0]['features'].update(x=True),'number'),
])
def test_rejects_invalid_input(change,match):
    rows=sample();change(rows)
    with pytest.raises(ValueError,match=match):evaluate(rows,bootstrap_repetitions=0)


def test_external_disjointness_and_test_labels_do_not_fit():
    train=sample()[:4]
    test=[record(7,'z','S',x=3,fig=None),record(8,'z','F',x=4,fig=3)]
    a=evaluate_external(train,test,bootstrap_repetitions=0)
    test[0]['award']='O';test[1]['award']='H'
    b=evaluate_external(train,test,bootstrap_repetitions=0)
    assert a['folds']==b['folds']
    assert [p['probabilities'] for p in a['predictions']]==[p['probabilities'] for p in b['predictions']]
    with pytest.raises(ValueError,match='problem overlap'):
        evaluate_external(train,[record(9,'a','O',x=3)],bootstrap_repetitions=0)
    bad=record(9,'z','O',x=3);bad['sha256']=train[0]['sha256']
    with pytest.raises(ValueError,match='sha256 overlap'):
        evaluate_external(train,[bad],bootstrap_repetitions=0)


def test_common_pair_denominator_retains_missing_and_ties():
    r=evaluate(sample(),baseline_keys={'figures':'fig','chars':'absent'},bootstrap_repetitions=20)
    rank=r['ranking']
    assert rank['pairs']==3
    assert rank['baselines']['figures']['pairs']==3
    assert rank['baselines']['figures']['abstentions']==1
    assert rank['baselines']['figures']['score']==pytest.approx(2/3)
    assert rank['baselines']['chars']['pairs']==3
    assert rank['baselines']['chars']['abstentions']==3
    assert rank['baselines']['chars']['score']==0
    assert rank['by_award_pair']['O_vs_M']['pairs']==2
    assert rank['by_award_pair']['O_vs_H']['pairs']==1
    assert r['confidence_intervals']['ranking']['model_minus_best_baseline'] is not None


def test_single_topic_lopo_has_no_training_data():
    with pytest.raises(ValueError,match='two problems'):
        evaluate(sample()[:2],bootstrap_repetitions=0)


def test_prespecified_model_keys_exclude_baseline_and_reject_unknown():
    r=evaluate(sample(),model_keys=['x'],baseline_keys={'figures':'fig'},bootstrap_repetitions=0)
    assert all(f['preprocessing']['feature_keys']==['x'] for f in r['folds'])
    assert r['ranking']['baselines']['figures']['pairs']==3
    assert r['model_keys']==['x']
    with pytest.raises(ValueError,match='unknown model'):
        evaluate(sample(),model_keys=['misspelled'],bootstrap_repetitions=0)
    with pytest.raises(ValueError,match='duplicate model'):
        evaluate(sample(),model_keys=['x','x'],bootstrap_repetitions=0)


def test_same_topic_same_hash_copy_is_rejected():
    rows=sample();rows[1]['sha256']=rows[0]['sha256']
    with pytest.raises(ValueError,match='duplicate sha256'):
        evaluate(rows,bootstrap_repetitions=0)


def test_missing_key_and_test_only_constant_column_do_not_enter_fit():
    rows=[record(1,'a','O',x=999,unique=1),record(2,'a','M',x=None,unique=5),
          record(3,'b','O',x=5),record(4,'b','M',x=1)]
    r=evaluate(rows,model_keys=['x','unique'],bootstrap_repetitions=0)
    fold=next(f for f in r['folds'] if f['held_out_problem']=='a')
    assert fold['preprocessing']['median']=={'x':3.,'unique':0.}
    assert fold['preprocessing']['all_missing']==['unique']
    assert fold['preprocessing']['kept_features']==['x']


def test_prior_model_and_quantity_ties_get_half_credit():
    rows=[record(1,'a','O',x=1),record(2,'a','M',x=1),
          record(3,'b','O',x=1),record(4,'b','M',x=1)]
    r=evaluate(rows,baseline_keys={'figures':'x'},bootstrap_repetitions=20)
    assert r['ranking']['model']['ties']==2
    assert r['ranking']['model']['score']==.5
    assert r['ranking']['baselines']['figures']['score']==.5
    assert r['ranking']['model_minus_best_baseline']==0
    assert r['confidence_intervals']['ranking']['model_minus_best_baseline']['lower']==0
    assert r['confidence_intervals']['ranking']['model_minus_best_baseline']['upper']==0


def test_cluster_bootstrap_repeats_entire_problem_and_is_reproducible():
    # Each topic has one error and one success. Every whole-topic bootstrap
    # therefore has accuracy exactly 1/2; row bootstrap need not have this.
    rows=[record(1,'a','O',x=1),record(2,'a','M',x=1),
          record(3,'b','O',x=1),record(4,'b','M',x=1)]
    a=evaluate(rows,bootstrap_repetitions=50)
    b=evaluate(rows,bootstrap_repetitions=50)
    assert a['confidence_intervals']==b['confidence_intervals']
    interval=a['confidence_intervals']['classification']['exact_accuracy']
    assert interval['lower']==interval['upper']==.5


def test_cli_executes_real_external_holdout_with_selected_columns(tmp_path):
    train=tmp_path/'train.json';test=tmp_path/'test.json';out=tmp_path/'new.json'
    train.write_text(json.dumps(sample()[:4]))
    test.write_text(json.dumps([record(9,'z','F',x=2,fig=999)]))
    p=subprocess.run([sys.executable,'-m','evals.award_calibration','--train-json',str(train),
                      '--test-json',str(test),'--model-keys','["x"]','--figures-key','fig',
                      '--output',str(out)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    result=json.loads(out.read_text())
    assert result['mode']=='external_holdout'
    assert result['model_keys']==['x']
    assert result['folds'][0]['preprocessing']['feature_keys']==['x']
    assert result['classification']['support']['F']==1
    assert result['predictions'][0]['probabilities']['F']==0


def test_cli_refuses_existing_output(tmp_path):
    src=tmp_path/'input.json';out=tmp_path/'out.json'
    src.write_text(json.dumps(sample()));out.write_text('keep')
    p=subprocess.run([sys.executable,'-m','evals.award_calibration','--input',str(src),'--output',str(out)],capture_output=True,text=True)
    assert p.returncode!=0
    assert out.read_text()=='keep'
    assert 'exists' in p.stderr.lower()


def test_shared_task_registry_prevents_denominator_only_winner():
    rows=sample()
    for r in rows:
        r['task_ids']=['one','two','three']
        r['summary_answered_task_ids']=['one']
        r['features']['summary.answered_share']=1/3
    rows[1]['task_ids'].append('four')
    rows[1]['features']['summary.answered_share']=1/4
    with pytest.raises(ValueError,match='shared task'):
        evaluate(rows,bootstrap_repetitions=0)
    rows[1]['task_ids']=list(reversed(rows[0]['task_ids']))
    rows[1]['features']['summary.answered_share']=1/3
    result=evaluate(rows,bootstrap_repetitions=0)
    assert result['measurement_validation']['task_registry']['a']=='validated'
    assert result['by_problem']['a']['classification']['n']==2
    assert result['by_problem']['a']['ranking']['pairs']==1
    rows[1]['features']['summary.answered_share']=.9
    with pytest.raises(ValueError,match='coverage feature'):
        evaluate(rows,bootstrap_repetitions=0)


@pytest.mark.parametrize('change',[
    lambda r:r[0].update(task_ids=['one','one']),
    lambda r:r[0].update(summary_answered_task_ids=['not-a-task']),
    lambda r:r[0].update(summary_answered_task_ids=['one','one']),
    lambda r:r[0].pop('summary_answered_task_ids'),
    lambda r:r[1].pop('task_ids'),
])
def test_task_registry_rejects_invalid_or_partial_rows(change):
    rows=sample()
    for r in rows:
        r.update(task_ids=['one','two'],summary_answered_task_ids=['one'])
    change(rows)
    with pytest.raises(ValueError):evaluate(rows,bootstrap_repetitions=0)


def test_legacy_measurements_not_falsely_certified():
    result=evaluate(sample(),bootstrap_repetitions=0)
    assert set(result['measurement_validation']['task_registry'].values())=={'not_supplied'}


def test_unprovided_summary_stays_unknown_without_discarding_common_tasks():
    rows=sample()
    for r in rows:
        r.update(task_ids=['one','two'],summary_answered_task_ids=['one'])
        r['features']['summary.answered_share']=.5
    rows[0].update(summary_answered_task_ids=None,
                   summary_coverage_unknown_reason='Summary sheet not provided in this local copy')
    rows[0]['features']['summary.answered_share']=None
    result=evaluate(rows,bootstrap_repetitions=0)
    assert result['measurement_validation']['task_registry']['a']=='validated'
    assert result['measurement_validation']['summary_coverage_unknown_ids']==['1']
    assert rows[0]['features']['summary.answered_share'] is None
    assert rows[0]['summary_answered_task_ids'] is None


@pytest.mark.parametrize('reason,value',[(None,None),('',None),('unknown',0)])
def test_unknown_summary_cannot_hide_a_zero_or_omit_reason(reason,value):
    rows=sample()
    for r in rows:
        r.update(task_ids=['one'],summary_answered_task_ids=[])
    rows[0].update(summary_answered_task_ids=None,summary_coverage_unknown_reason=reason)
    rows[0]['features']['summary.answered_share']=value
    with pytest.raises(ValueError):evaluate(rows,bootstrap_repetitions=0)
