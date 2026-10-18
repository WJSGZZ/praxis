"""Semantic pointers and independent answers; malformed inputs fail closed."""
import json
import pytest
from scripts import paper_facts as pf


def case(tmp_path):
    c=tmp_path/'cases/t';o=c/'runs/run1/output';o.mkdir(parents=True)
    (o/'results.json').write_text(json.dumps({'a/b':{'~x':20651159.02346611},'rows':[{'policy':'P','x':4},{'policy':'Q','x':-1}]}))
    (o.parent/'receipt.json').write_text(json.dumps({'automatic_checks_passed':True,'outputs':{'output/results.json':pf.digest(o/'results.json')}}))
    return c,{'schema':1,'sources':{'run':{'kind':'run_result','file':'output/results.json'}},'facts':{'gain':{'source':'run','pointer':'/a~1b/~0x','unit':'million KES','format':'.2f','scale':1e-6}}}


def test_exact_bytes_and_lineage(tmp_path):
    c,m=case(tmp_path);s=tmp_path/'src';s.mkdir();(s/'paper.tex').write_bytes(b'First \\fact{gain}.\nAgain \\fact{gain}.\n')
    r=pf.expand(s,tmp_path/'new',m,case=c,run_id='run1',workspace=tmp_path,historical=True)
    assert (tmp_path/'new/paper.tex').read_bytes()==b'First 20.65.\nAgain 20.65.\n'
    assert len(r['occurrences'])==2 and r['mode']=='historical-reproduction'
    assert r['facts']['gain']['lineage'][0]['pointer']=='/a~1b/~0x'


@pytest.mark.parametrize('p',['','/','/missing','/a~2b','/rows/01','/rows/-1','/rows/true'])
def test_invalid_pointer(tmp_path,p):
    c,m=case(tmp_path);m['facts']['gain']['pointer']=p
    with pytest.raises(ValueError):pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)


def test_guard(tmp_path):
    c,m=case(tmp_path);m['facts']['gain']['guard']={'pointer':'/rows/0/policy','equals':'Q'}
    with pytest.raises(ValueError,match='guard'):pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)


def test_derived_answer(tmp_path):
    c,m=case(tmp_path);m['facts']={'delta':{'expression':{'op':'subtract','args':[{'source':'run','pointer':'/rows/0/x'},{'source':'run','pointer':'/rows/1/x'}]},'unit':'KES','format':'.0f','classification':'derived_presentation'}}
    r=pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)
    assert r['facts']['delta']['display']=='5'
    assert [x['pointer'] for x in r['facts']['delta']['lineage']]==['/rows/0/x','/rows/1/x']


def test_supplement(tmp_path):
    c,m=case(tmp_path);p=tmp_path/'independent.json';p.write_text('{"threshold":0.18554440126884794}')
    m['sources']['independent']={'kind':'supplementary_evidence','path':'independent.json','sha256':pf.digest(p),'scope':'independent old run'}
    m['facts']={'threshold':{'source':'independent','pointer':'/threshold','scale':100,'unit':'percent','format':'.1f'}}
    r=pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)
    assert r['facts']['threshold']['display']=='18.6' and r['sources']['independent']['scope']=='independent old run'
    p.write_text('{"threshold":0.2}')
    with pytest.raises(ValueError,match='hash'):pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)


@pytest.mark.parametrize('kind',['hash','escape','nonfinite','format','unit','bool','unknown_op','division_zero'])
def test_bad_contract(tmp_path,kind):
    c,m=case(tmp_path)
    if kind=='hash':(c/'runs/run1/output/results.json').write_text('{"x":1}')
    if kind=='escape':m['sources']['run']['file']='../../../../outside.json'
    if kind=='nonfinite':m['facts']['gain']['scale']=float('inf')
    if kind=='format':m['facts']['gain']['format']='1000000000f'
    if kind=='unit':m['facts']['gain']['unit']=''
    if kind=='bool':m['facts']['gain']['scale']=True
    if kind=='unknown_op':m['facts']['gain']={'expression':{'op':'eval','args':[]},'unit':'KES','format':'.2f'}
    if kind=='division_zero':m['facts']['gain']={'expression':{'op':'divide','args':[{'source':'run','pointer':'/rows/0/x'},0]},'unit':'KES','format':'.2f'}
    with pytest.raises(ValueError):pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)


@pytest.mark.parametrize('text',['\\fact{missing}','\\fact{gain','\\fact{gain} \\fact{unknown}'])
def test_macro_failure_no_partial_output(tmp_path,text):
    c,m=case(tmp_path);s=tmp_path/'src';s.mkdir();(s/'paper.tex').write_text(text)
    with pytest.raises(ValueError):pf.expand(s,tmp_path/'new',m,case=c,run_id='run1',workspace=tmp_path,historical=True)
    assert not (tmp_path/'new').exists()


def test_no_overwrite_or_symlink(tmp_path):
    c,m=case(tmp_path);s=tmp_path/'src';s.mkdir();(s/'paper.tex').write_text('\\fact{gain}');d=tmp_path/'existing';d.mkdir()
    with pytest.raises(ValueError):pf.expand(s,d,m,case=c,run_id='run1',workspace=tmp_path,historical=True)
    (s/'hidden.tex').symlink_to(s/'paper.tex')
    with pytest.raises(ValueError):pf.expand(s,tmp_path/'new',m,case=c,run_id='run1',workspace=tmp_path,historical=True)


def test_json_finite_unique(tmp_path):
    for content in ['{"a":1,"a":2}','{"a":NaN}','{"a":1e999}']:
        p=tmp_path/'bad.json';p.write_text(content)
        with pytest.raises(ValueError):pf.read_json(p)


def test_source_resources_only_no_execution_or_old_build(tmp_path):
    c,m=case(tmp_path);s=tmp_path/'src';s.mkdir();(s/'figures').mkdir()
    (s/'paper.tex').write_text('\\input{figures/x.tex}')
    (s/'figures/x.tex').write_text('\\fact{gain}')
    for name in ['paper.pdf','paper.log','paper.build.json','run.py']:(s/name).write_text('never execute or copy')
    (s/'data.json').write_text('{"ok":true}')
    r=pf.expand(s,tmp_path/'new',m,case=c,run_id='run1',workspace=tmp_path,historical=True)
    assert (tmp_path/'new/figures/x.tex').read_text()=='20.65'
    assert set(r['generated_files'])=={'paper.tex','figures/x.tex','data.json'}


def test_default_refuses_failed_latest_without_fallback(tmp_path,monkeypatch):
    c,m=case(tmp_path)
    from scripts import pipeline
    monkeypatch.setattr(pipeline,'status',lambda case:{'runs':[{'run':'run1','usable_automatic_evidence':True},{'run':'run2','usable_automatic_evidence':False}]})
    with pytest.raises(ValueError,match='Latest'):pf.resolve(c,m,workspace=tmp_path)


def test_missing_guard_and_nonregistered_source_are_errors(tmp_path):
    c,m=case(tmp_path);m['facts']['gain']['guard']={'pointer':'/rows/99/policy','equals':'P'}
    with pytest.raises(ValueError):pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)


def test_bounded_select_and_count_independent_answer(tmp_path):
    c,m=case(tmp_path)
    m['facts']={'positive':{'classification':'derived_presentation','unit':'count','format':'d','expression':{'op':'count_where','args':[{'source':'run','pointer':'/rows'}],'predicates':[{'pointer':'/x','comparison':'positive'}]}}}
    assert pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)['facts']['positive']['display']=='1'


def test_unsafe_source_text_and_fractional_integer(tmp_path):
    c,m=case(tmp_path);m['facts']['gain']['format']='d'
    with pytest.raises(ValueError,match='truncate'):pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)
    m['facts']['gain']={'source':'run','pointer':'/rows/0/policy','unit':'policy','format':'s'}
    assert pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)['facts']['gain']['display']=='P'


def test_output_boundary_and_sentence(tmp_path):
    c,m=case(tmp_path);s=tmp_path/'src';s.mkdir();(s/'paper.tex').write_text('Prior. Gain \\fact{gain} million. Next.')
    r=pf.expand(s,tmp_path/'new',m,case=c,run_id='run1',workspace=tmp_path,historical=True)
    assert r['occurrences'][0]['sentence']=='Gain \\fact{gain} million.'
    with pytest.raises(ValueError,match='workspace'):pf.expand(s,tmp_path.parent/'outside',m,case=c,run_id='run1',workspace=tmp_path,historical=True)


def test_result_source_symlink_is_refused_even_inside_workspace(tmp_path):
    c,m=case(tmp_path)
    target=c/'runs/run1/output/results.json'; target.rename(target.with_name('other.json'))
    target.symlink_to('other.json')
    with pytest.raises(ValueError,match='[Ss]ymlink'):
        pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)


def test_derived_literal_is_not_a_bound_scientific_result(tmp_path):
    c,m=case(tmp_path)
    m['facts']={'invented':{'expression':{'op':'add','args':[2,3]},'unit':'KES',
                          'format':'d','classification':'derived_presentation'}}
    with pytest.raises(ValueError,match='lineage'):
        pf.resolve(c,m,'run1',workspace=tmp_path,historical=True)


def test_current_resolution_honors_explicit_workspace_from_another_cwd(tmp_path,monkeypatch):
    from scripts import pipeline
    c,m=case(tmp_path)
    old=pipeline.PROJECT
    def report(selected):
        assert pipeline.PROJECT == tmp_path
        return {'runs':[{'run':str(c/'runs/run1'),'usable_automatic_evidence':True}]}
    monkeypatch.setattr(pipeline,'status',report)
    assert pf.resolve(c,m,workspace=tmp_path)['run_id']=='run1'
    assert pipeline.PROJECT==old
