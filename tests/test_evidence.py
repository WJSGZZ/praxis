"""Task coverage must fail on missing, ambiguous or stale evidence."""
import json
import pytest
from test_pipeline import make_case, pipeline


def record(case, **changes):
    task={'id':'Q1','question':'Extrapolate y=1+2*x at x=4','unit':'dimensionless',
          'result_pointer':'/prediction','checks':['independent arithmetic']}
    task.update(changes)
    (case/'planning/requirements.json').write_text(json.dumps({'requirements':[task]}))


def test_links_known_answer_to_independent_check_and_run(tmp_path):
    case,_,_=make_case(tmp_path)
    record(case)
    receipt=pipeline.run_case(case)
    report=pipeline.evidence_index(case)
    assert report['status']=='evidence-linked'
    assert report['covered']==report['recorded_requirements']==1
    assert report['entries'][0]['value']==pytest.approx(9)
    assert '1+2*4=9' in report['entries'][0]['check_evidence'][0]['evidence']
    assert report['run']==receipt['run']
    assert not report['paper_ready']


@pytest.mark.parametrize('changes',[{'result_pointer':'/missing'}, {'checks':['absent check']}])
def test_missing_answer_or_check_cannot_count_as_covered(tmp_path,changes):
    case,_,_=make_case(tmp_path)
    record(case,**changes)
    pipeline.run_case(case)
    report=pipeline.evidence_index(case)
    assert report['status']=='evidence-incomplete'
    assert report['covered']==0
    assert report['entries'][0]['errors']


def test_changed_requirement_invalidates_previous_run(tmp_path):
    case,_,_=make_case(tmp_path)
    record(case)
    pipeline.run_case(case)
    record(case,unit='changed unit')
    with pytest.raises(ValueError,match='stale'):
        pipeline.evidence_index(case)


def test_latest_failure_does_not_fall_back_to_old_success(tmp_path):
    case,_,_=make_case(tmp_path)
    record(case)
    pipeline.run_case(case)
    (case/'code/model.py').write_text('raise RuntimeError("deliberate failure")')
    pipeline.run_case(case)
    with pytest.raises(ValueError,match='Latest run failed'):
        pipeline.evidence_index(case)


def test_duplicate_check_names_cannot_silently_select_one(tmp_path):
    case,_,_=make_case(tmp_path)
    record(case)
    validator=case/'code/validate.py'
    validator.write_text(validator.read_text().replace("json.dumps([{'name':", "json.dumps([{'name':").replace("raise SystemExit(0 if ok else 1)","checks=json.loads(a.output.read_text());a.output.write_text(json.dumps(checks+checks))\nraise SystemExit(0 if ok else 1)"))
    assert pipeline.run_case(case)['automatic_checks_passed']
    with pytest.raises(ValueError,match='unique'):
        pipeline.evidence_index(case)


def test_empty_manifest_never_means_complete(tmp_path):
    case,_,_=make_case(tmp_path)
    (case/'planning/requirements.json').write_text('{"requirements":[]}')
    with pytest.raises(ValueError,match='nonempty'):
        pipeline.evidence_index(case)


def test_json_pointer_arrays_escaped_keys_and_zero_are_valid():
    assert pipeline.result_pointer({'a/b':[{'~v':0}]},'/a~1b/0/~0v')==0
    assert pipeline.result_pointer({'ok':False},'/ok') is False
    for pointer in ['/a~2b','/a~1b/01','/a~1b/9','prediction']:
        with pytest.raises(ValueError):
            pipeline.result_pointer({'a/b':[7]},pointer)


def test_claims_cannot_outrun_their_evidence():
    requirements = [dict(id='Q1', question='q', unit='u', result_pointer='/a', checks=['c1']), dict(id='Q2', question='q', unit='u', result_pointer='/b', checks=['c2'])]
    lookup = {'c1': dict(name='c1', passed=True, evidence='e'), 'c2': dict(name='c2', passed=True, evidence='e', independent=True), 'c3': dict(name='c3', passed=False, evidence='e')}
    results = {'a': 1, 'b': 2}
    ok = [dict(id='K1', requirement='Q1', text='t', strength='checked', result_pointer='/a', checks=['c1']),
          dict(id='K2', requirement='Q2', text='t', strength='independent', result_pointer='/b', checks=['c2'])]
    assert pipeline.claim_problems(requirements, ok, lookup, results) == []
    over = [dict(ok[0], strength='independent'), ok[1]]
    assert any('supports only checked' in p for p in pipeline.claim_problems(requirements, over, lookup, results))
    failed = [dict(ok[0], checks=['c3']), ok[1]]
    problems = pipeline.claim_problems(requirements, failed, lookup, results)
    assert any('supports only computed' in p for p in problems) and any('requirement Q1 has no claim' in p for p in problems)
    uncovered = pipeline.claim_problems(requirements, [ok[1]], lookup, results)
    assert uncovered == ['requirement Q1 has no claim whose evidence supports it']
    assert any('unknown check' in p for p in pipeline.claim_problems(requirements, [dict(ok[0], checks=['nope'])], lookup, results))
    assert any('needs a unique id' in p for p in pipeline.claim_problems(requirements, [dict(ok[0], strength='proven')], lookup, results))
