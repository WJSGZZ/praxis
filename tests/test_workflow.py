"""Adversarial boundaries and one independent, known integer knapsack pipeline."""
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pypdf import PdfWriter
from scripts import workflow as w


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setattr(w.pipeline, 'PROJECT', tmp_path)
    problem = tmp_path / 'problem.md'
    problem.write_text('Synthetic knapsack: capacity5; weights3,4,2; values5,6,4. Exact optimum9.')
    c = Path(w.pipeline.init_case(tmp_path / 'cases', 'integer-check', problem)['case'])
    (c / 'planning/progress.md').write_text('Existing progress, preserved.\n')
    (c / 'code/model.py').write_text('''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
w=[3,4,2];v=[5,6,4]
feasible=[(sum(v[i] for i in range(3) if m>>i&1),m) for m in range(8) if sum(w[i] for i in range(3) if m>>i&1)<=5]
value,mask=max(feasible)
(a.output/'results.json').write_text(json.dumps({'optimum':value,'mask':mask}))
''')
    (c / 'code/validate.py').write_text('''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--results',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
r=json.loads(a.results.read_text())
# Independent manual exhaustion: feasible pair(3,2) yields9; other pair weights6/7 exceed5;
# every singleton yields <=6 and all three weigh9. Thus exact optimum9, mask5.
ok=r['optimum']==9 and r['mask']==5
a.output.write_text(json.dumps([{'name':'manual subset bound','passed':ok,'evidence':'only feasible pair weights3+2=5 yields5+4=9; singletons<=6'}]))
raise SystemExit(0 if ok else 1)
''')
    w.pipeline.save(c / 'planning/requirements.json', {'requirements': [dict(id='Q1', question='maximum value', unit='value units', result_pointer='/optimum', checks=['manual subset bound'])]})
    return c


def initialise(case, **kw):
    return w.init(case, 'Solve the known integer case', query='integer bound', budget_seconds=120, max_attempts=3, per_run_timeout=5, **kw)


def execute(case):
    return w.run(case, w.next(case)['expected_source_sha256'])


def review(case, receipt, *, decision='stop'):
    p = case / 'planning/review.json'
    w.pipeline.save(p, {'verdict':'pass', 'actor':'AI test reviewer', 'scope':'manual optimum and constraints',
                        'run_id':Path(receipt['run']).name, 'receipt_sha256':w.pipeline.digest(Path(receipt['run'])/'receipt.json'),
                        'quality_decision': {'decision':decision, 'reason':'known exact answer established' if decision=='stop' else 'test sensitivity still needed', 'next_action':'check altered capacity'} })
    return p


def accepted(case, *, decision='stop'):
    initialise(case)
    receipt=execute(case)
    assert receipt['status']=='automatic-checks-passed'
    w.accept(case, review(case, receipt, decision=decision))
    return receipt


def test_known_knapsack_actual_pipeline_and_live_delivery(case):
    before=w.pipeline.source_snapshot(case)
    initialise(case)
    assert w.pipeline.source_snapshot(case)==before
    assert w.next(case)['action']=='run'
    receipt=execute(case)
    assert w.pipeline.read_json(Path(receipt['run'])/'output/results.json')=={'optimum':9,'mask':5}
    assert w.next(case)['action']=='review'
    w.accept(case,review(case,receipt))
    assert w.next(case)['action']=='report'
    report=case/'answer.md';report.write_text('Exact value9; choose weights3 and2.')
    w.report(case,report)
    assert w.next(case)['action']=='delivered'
    progress=(case/'planning/progress.md').read_text()
    assert progress.startswith('Existing progress, preserved.\n')
    assert progress.count(w.BEGIN)==progress.count(w.END)==1
    source=Path(receipt['run'])/'source-snapshot/planning/progress.md'
    assert not source.exists()
    report.write_text('Changed claim')
    assert w.next(case)['action']=='report'
    (case/'planning/review.json').write_text('{}')
    assert w.next(case)['action']=='review'


def test_cross_process_next_and_cli_bad_input_are_read_only(case):
    initialise(case)
    before=(case/'planning/progress.md').read_bytes()
    args=[sys.executable,str(w.BUNDLE/'scripts/workflow.py'),'--workspace',str(w.pipeline.PROJECT)]
    result=subprocess.run(args+['next','--case',str(case)],capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)['action']=='run'
    failure=subprocess.run(args+['run','--case',str(case),'--reviewed-source-sha256','bad'],capture_output=True,text=True)
    assert failure.returncode and 'error' in json.loads(failure.stderr)
    syntax=subprocess.run(args+['init','--case',str(case),'--goal','x','--budget-seconds','NaN'],capture_output=True,text=True)
    assert syntax.returncode and 'error' in json.loads(syntax.stderr)
    assert (case/'planning/progress.md').read_bytes()==before


@pytest.mark.parametrize('name,value', [('budget_seconds',True),('budget_seconds',float('nan')),('budget_seconds',float('inf')),('budget_seconds',0),('max_attempts',False),('max_attempts',-1),('per_run_timeout',1.5),('per_run_timeout',3601)])
def test_invalid_budget_never_creates_block(case,name,value):
    before=(case/'planning/progress.md').read_bytes()
    args=dict(budget_seconds=120,max_attempts=3,per_run_timeout=5);args[name]=value
    with pytest.raises(ValueError):w.init(case,'goal',**args)
    assert (case/'planning/progress.md').read_bytes()==before


def test_lessons_are_retrieved_before_run_with_finite_identity(case):
    history=w.pipeline.PROJECT/'cases/history/planning/lessons.jsonl';history.parent.mkdir(parents=True)
    seed=w.BUNDLE/'templates/lessons-seed.jsonl';history.write_bytes(seed.read_bytes())
    result=w.init(case,'goal',query='integer tolerance',lessons_path=history,budget_seconds=120,max_attempts=3,per_run_timeout=5)
    retrieval=result['state']['lesson_retrieval']
    assert 1<=len(retrieval['hits'])<=3 and retrieval['index_sha256']==w.pipeline.digest(history)
    assert all(len(x['sha256'])==64 for x in retrieval['hits'])
    assert not list((case/'runs').iterdir())
    before=(case/'planning/progress.md').read_bytes()
    with pytest.raises(ValueError):initialise(case)
    assert (case/'planning/progress.md').read_bytes()==before


def test_no_lesson_hits_are_preserved(case):
    state=initialise(case)['state']
    assert state['lesson_retrieval']['hits']==[]
    assert state['lesson_retrieval']['index_sha256'] is None
    assert state['metering']=={'model':'unknown','tokens':'not measured'}


@pytest.mark.parametrize('bad', ['NaN','1e999'])
def test_strict_json_and_damaged_blocks(case,bad):
    initialise(case)
    path=case/'planning/progress.md'
    text=path.read_text();path.write_text(text.replace('"budget_seconds": 120','"budget_seconds": '+bad))
    corrupted=path.read_bytes()
    with pytest.raises(ValueError):w.next(case)
    assert path.read_bytes()==corrupted
    path.write_text(text+'\n'+w.BEGIN+'\n{}\n'+w.END)
    with pytest.raises(ValueError):w.next(case)
    with pytest.raises(ValueError):initialise(case)


def test_traversal_symlinks_and_outside_review_never_mutate_acceptance(case):
    receipt=accepted(case)
    before=(case/'planning/progress.md').read_bytes()
    for p in [case/'../integer-check/planning/review.json',w.pipeline.PROJECT/'outside.json']:
        with pytest.raises(ValueError):w.accept(case,p)
    target=case/'planning/review.json';link=case/'planning/link.json';link.symlink_to(target)
    with pytest.raises(ValueError):w.accept(case,link)
    assert (case/'planning/progress.md').read_bytes()==before
    link.unlink()
    assert w.next(case)['action']=='report'


def test_latest_failure_does_not_hide_behind_previous_accepted(case):
    accepted(case)
    previous=w.read_state(case)[0]['accepted']
    (case/'code/model.py').write_text('raise SystemExit(7)\n')
    assert w.next(case)['action']=='repair'
    receipt=execute(case)
    assert receipt['status']=='failed'
    assert (Path(receipt['run'])/'receipt.json').is_file()
    state=w.read_state(case)[0]
    assert state['accepted']==previous and state['attempts']==2
    assert state['attempt_history'][-1]['wall_seconds']>0
    action=w.next(case)
    assert action['action']=='repair' and action['previous_accepted']==previous
    with pytest.raises(ValueError):w.accept(case,case/'planning/review.json')


def test_timeout_retains_receipt_and_elapsed(case):
    (case/'code/model.py').write_text('import time;time.sleep(3)\n')
    w.init(case,'goal',budget_seconds=20,max_attempts=1,per_run_timeout=1)
    receipt=execute(case)
    assert receipt['status']=='failed' and 'TimeoutExpired' in receipt['error']
    state=w.read_state(case)[0]
    assert state['attempt_history'][0]['wall_seconds']>=1
    assert (Path(receipt['run'])/'model.stderr.log').exists()
    assert w.next(case)['action']=='closeout'
    before=(case/'planning/progress.md').read_bytes()
    with pytest.raises(ValueError,match='Maximum'):execute(case)
    assert (case/'planning/progress.md').read_bytes()==before


def test_coverage_and_source_confirmation_are_current(case):
    manifest=case/'planning/requirements.json'
    definition=w.pipeline.read_json(manifest);definition['requirements'][0]['checks']=['not recorded'];w.pipeline.save(manifest,definition)
    initialise(case);receipt=execute(case)
    assert w.next(case)['action']=='coverage'
    before=(case/'planning/progress.md').read_bytes()
    with pytest.raises(ValueError):w.accept(case,review(case,receipt))
    assert (case/'planning/progress.md').read_bytes()==before
    oldhash=w.next(case)['expected_source_sha256']
    definition['requirements'][0]['checks']=['manual subset bound'];w.pipeline.save(manifest,definition)
    assert w.next(case)['action']=='repair'
    with pytest.raises(ValueError,match='snapshot'):w.run(case,oldhash)
    assert w.next(case)['expected_source_sha256']!=oldhash


def test_deadline_priority_and_both_timeout_reservation(case,monkeypatch):
    start=w.now();monkeypatch.setattr(w,'now',lambda:start)
    w.init(case,'goal',budget_seconds=20,max_attempts=2,per_run_timeout=5)
    before=(case/'planning/progress.md').read_bytes()
    monkeypatch.setattr(w,'now',lambda:start+timedelta(seconds=10.001))
    with pytest.raises(ValueError,match='remaining'):execute(case)
    assert (case/'planning/progress.md').read_bytes()==before
    monkeypatch.setattr(w,'now',lambda:start+timedelta(seconds=10))
    assert execute(case)['status']=='automatic-checks-passed'
    monkeypatch.setattr(w,'now',lambda:start+timedelta(seconds=20))
    assert w.next(case)['action']=='closeout'
    with pytest.raises(ValueError):w.run(case,w.canonical_hash(w.pipeline.source_snapshot(case)))


def test_quality_continue_overrides_report_and_requires_actual_action(case):
    receipt=accepted(case,decision='continue')
    report=case/'answer.md';report.write_text('Exact known optimum9.')
    w.report(case,report)
    action=w.next(case)
    assert action['action']=='improve' and action['next_action']=='check altered capacity'
    path=case/'planning/review.json';data=w.pipeline.read_json(path);data['quality_decision']['next_action']='';w.pipeline.save(path,data)
    before=(case/'planning/progress.md').read_bytes()
    with pytest.raises(ValueError,match='quality_decision'):w.accept(case,path)
    assert (case/'planning/progress.md').read_bytes()==before
    assert w.next(case)['action']=='review'


def test_bad_review_receipt_nonfinite_and_stop_reason_rejected(case):
    initialise(case);receipt=execute(case);path=review(case,receipt)
    valid=path.read_text();before=(case/'planning/progress.md').read_bytes()
    for mutate in [lambda d:d.update(receipt_sha256='0'*64),lambda d:d.update(actor=''),lambda d:d['quality_decision'].update(reason=''),lambda d:d.update(run_id='old')]:
        data=json.loads(valid);mutate(data);w.pipeline.save(path,data)
        with pytest.raises(ValueError):w.accept(case,path)
    path.write_text(valid.replace('"verdict": "pass"','"verdict": "pass", "unknown": NaN'))
    with pytest.raises(ValueError):w.accept(case,path)
    assert (case/'planning/progress.md').read_bytes()==before


def test_pdf_requires_hash_actor_and_every_actual_page(case):
    accepted(case)
    pdf=case/'paper.pdf';writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.add_blank_page(width=100,height=100)
    with pdf.open('wb') as out:writer.write(out)
    before=(case/'planning/progress.md').read_bytes()
    with pytest.raises(FileNotFoundError):w.report(case,pdf)
    side=case/'paper.pdf.page-review.json'
    data={'actor':'explicit test record','pdf_sha256':w.pipeline.digest(pdf),'pages':[1]};w.pipeline.save(side,data)
    with pytest.raises(ValueError):w.report(case,pdf)
    assert (case/'planning/progress.md').read_bytes()==before
    data['pages']=[1,2];w.pipeline.save(side,data);w.report(case,pdf)
    assert w.next(case)['action']=='delivered'
    data['actor']='changed';w.pipeline.save(side,data)
    assert w.next(case)['action']=='report'


def test_prepare_without_model_and_no_raw_mutation(case):
    (case/'code/model.py').unlink();initialise(case)
    raw=case/'raw/problem/problem.md';before=raw.read_bytes()
    assert w.next(case)['action']=='prepare'
    assert raw.read_bytes()==before


def test_receipt_identity_is_rechecked_without_writing_progress(case):
    receipt=accepted(case)
    path=Path(receipt['run'])/'receipt.json'
    path.write_text(path.read_text()+'\n')
    before=(case/'planning/progress.md').read_bytes()
    assert w.next(case)['action']=='review'
    assert (case/'planning/progress.md').read_bytes()==before


def test_marker_inside_goal_does_not_create_a_second_block(case):
    w.init(case,'Literal '+w.BEGIN,budget_seconds=120,max_attempts=2,per_run_timeout=5)
    assert w.read_state(case)[0]['goal']=='Literal '+w.BEGIN
    assert (case/'planning/progress.md').read_text().count(w.BEGIN)==1
    assert w.next(case)['action']=='run'


def test_launch_oserror_keeps_previous_acceptance_but_not_current_delivery(case,monkeypatch):
    accepted(case)
    report=case/'answer.md';report.write_text('Known exact result9.');w.report(case,report)
    prior=w.read_state(case)[0]['accepted']
    def fail(*args,**kwargs):
        raise OSError('synthetic launch failure before receipt')
    monkeypatch.setattr(w.pipeline,'run_case',fail)
    with pytest.raises(OSError):execute(case)
    state=w.read_state(case)[0]
    assert state['accepted']==prior and state['attempts']==2
    assert state['attempt_history'][-1]['status']=='error'
    assert state['attempt_history'][-1]['wall_seconds']>=0
    assert w.next(case)['action']=='repair'
    with pytest.raises(ValueError):w.report(case,report)
    with pytest.raises(ValueError):w.accept(case,case/'planning/review.json')
    assert w.read_state(case)[0]['accepted']==prior
    with pytest.raises(OSError):execute(case)
    assert w.next(case)['action']=='closeout'
    assert w.read_state(case)[0]['accepted']==prior


def test_cli_failed_pipeline_receipt_is_json_and_nonzero(case):
    (case/'code/model.py').write_text('raise SystemExit(4)\n');initialise(case)
    result=subprocess.run([sys.executable,str(w.BUNDLE/'scripts/workflow.py'),'--workspace',str(w.pipeline.PROJECT),'run','--case',str(case),'--reviewed-source-sha256',w.canonical_hash(w.pipeline.source_snapshot(case))],capture_output=True,text=True)
    receipt=json.loads(result.stdout)
    assert result.returncode==1 and receipt['status']=='failed'
    assert (Path(receipt['run'])/'receipt.json').exists()
    assert w.read_state(case)[0]['attempts']==1
