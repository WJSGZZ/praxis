import pytest

from modeling import lessons


def sample(**kw):
    base = dict(problem='cooling bath, minimise added water', structure='energy balance + monotone loss', recognized='loss grows with temperature',
                routes_tried=['simulation only', 'ODE with lower bound'], what_failed='simulation gave no optimality evidence',
                what_worked='coast then hold, proved by monotonicity', verified_by='independent ODE integration', principle='if loss is monotone in state, delay the control',
                tags=['ode', 'control'])
    base.update(kw)
    return base


def test_add_search_and_patterns(tmp_path):
    f = tmp_path / 'planning' / 'lessons.jsonl'
    assert lessons.add_lesson(f, sample())['id'] == 'L0001'
    second = lessons.add_lesson(f, sample(problem='portfolio with fees', structure='piecewise cost + relaxation', tags=['milp'], evidence='derived',
                                                  recognized='fee jumps at a threshold', principle='relax the kink to get a bound', what_worked='MILP with relaxation bound', routes_tried=['greedy']))
    assert second['id'] == 'L0002'
    hits = lessons.search_lessons(f, 'monotone loss delay control')
    assert hits[0]['id'] == 'L0001'
    assert lessons.search_lessons(f, tags=['MILP'])[0]['id'] == 'L0002'
    assert lessons.search_lessons(f, 'zebra') == []
    lessons.add_lesson(f, sample(problem='another cooling task'))
    out = lessons.patterns(f)
    assert out['lessons'] == 3 and out['repeated_structures'] == {'energy balance + monotone loss': 2}


def test_incomplete_or_unknown_evidence_is_rejected(tmp_path):
    f = tmp_path / 'l.jsonl'
    with pytest.raises(ValueError, match='principle'):
        lessons.add_lesson(f, sample(principle='  '))
    with pytest.raises(ValueError, match='evidence'):
        lessons.add_lesson(f, sample(evidence='felt right'))
    assert not f.exists()


def test_seed_lessons_are_valid_and_found_by_a_new_problem(tmp_path):
    from pathlib import Path
    import shutil
    from modeling import lessons
    seed = Path(__file__).resolve().parents[1] / 'templates/lessons-seed.jsonl'
    target = tmp_path / 'lessons.jsonl'
    shutil.copy(seed, target)
    records = lessons.load(target)
    assert len(records) >= 5
    for rec in records:
        assert all(str(rec.get(k, '')).strip() for k in lessons.REQUIRED + lessons.OPTIONAL), rec['id']
    found = lessons.search_lessons(target, 'heat conduction mesh refinement point source inlet constraint')
    assert found and found[0]['id'] == 'S0001'
    lessons.add_lesson(target, dict(records[0], id=None, problem='another'))     # the seed file remains appendable


def test_route_graph_returns_related_lessons_for_a_new_record(tmp_path):
    import shutil
    from pathlib import Path
    from scripts import mcp_server
    seed = Path(__file__).resolve().parents[1] / 'templates/lessons-seed.jsonl'
    shutil.copy(seed, tmp_path / 'l.jsonl')
    out = mcp_server.call('route_graph', dict(question='rule multiplier misread in a strategy game', operations=[], lessons_path=str(tmp_path / 'l.jsonl')))
    assert out['related_lessons'] and out['related_lessons'][0]['id'] == 'S0002'


def test_chinese_queries_find_lessons(tmp_path):
    import shutil
    from pathlib import Path
    from modeling import lessons
    target = tmp_path / 'l.jsonl'
    shutil.copy(Path(__file__).resolve().parents[1] / 'templates/lessons-seed.jsonl', target)
    for query, expected in (('热传导 网格 加密 点源 约束', 'S0001'), ('三维热网络中带入口点源的温度约束', 'S0001'), ('规则倍数 读错', 'S0002'),
                            ('边界条件被数据否定', 'S0003'), ('整数规划的二元变量容差', 'S0004'), ('全部通过的检验没有变异测试', 'S0005')):
        found = lessons.search_lessons(target, query)
        assert found and found[0]['id'] == expected, (query, [r['id'] for r in found])
    assert all(r['evidence'] != 'checked on a held-out problem' for r in lessons.load(target))      # none was checked on another problem yet


def test_duplicate_replacement_chain_and_retirement_preserve_history(tmp_path):
    f = tmp_path / 'l.jsonl'
    first = lessons.add_lesson(f, sample())
    original = f.read_bytes()
    assert lessons.add_lesson(f, sample()) == first
    assert f.read_bytes() == original
    second = lessons.add_lesson(f, sample(principle='A monotone bound requires the same admissible controls', supersedes=first['id']))
    third = lessons.add_lesson(f, sample(principle='Check service and information before comparing control costs', supersedes=[second['id']]))
    assert [r['id'] for r in lessons.active(f)] == [third['id']]
    assert [r['id'] for r in lessons.load(f)] == [first['id'], second['id'], third['id']]
    lessons.add_lesson(f, {'event': 'retire', 'target': third['id'], 'reason': 'assumption contradicted by an independent example'})
    assert lessons.search_lessons(f, 'control') == []
    assert lessons.patterns(f)['lessons'] == 0
    assert f.read_bytes().startswith(original)
    assert len(lessons.load(f)) == 3
    retired_bytes=f.read_bytes()
    with pytest.raises(ValueError,match='inactive'):
        lessons.add_lesson(f,sample(principle=third['principle']))
    assert f.read_bytes()==retired_bytes


def test_invalid_replacements_and_retirement_are_atomic(tmp_path):
    f = tmp_path / 'l.jsonl'
    a = lessons.add_lesson(f, sample()); before=f.read_bytes()
    for payload in [sample(supersedes='missing'), sample(supersedes=[a['id'],a['id']]),
                    {'event':'retire','target':'missing','reason':'bad'}, {'event':'retire','target':a['id'],'reason':''},
                    sample(source_kind='external_proposal',evidence='checked on a held-out problem')]:
        with pytest.raises(ValueError): lessons.add_lesson(f,payload)
        assert f.read_bytes()==before


def test_legacy_duplicate_view_and_invalid_imported_cycles(tmp_path):
    import json
    f=tmp_path/'l.jsonl'
    a=dict(sample(),id='L0001',evidence='observed once'); b=dict(a,id='L0002')
    f.write_text(json.dumps(a)+'\n'+json.dumps(b)+'\n')
    assert len(lessons.load(f))==2 and len(lessons.active(f))==1
    lessons.add_lesson(f,{'event':'retire','target':'L0001','reason':'duplicates must not resurrect'})
    assert lessons.active(f)==[] and len(lessons.load(f))==2
    a['supersedes']='L0002';b['supersedes']='L0001'
    f.write_text(json.dumps(a)+'\n'+json.dumps(b)+'\n');before=f.read_bytes()
    with pytest.raises(ValueError,match='Cyclic'):lessons.search_lessons(f,'control')
    assert f.read_bytes()==before
    b['supersedes']='missing';f.write_text(json.dumps(b)+'\n')
    with pytest.raises(ValueError,match='missing'):lessons.active(f)


def test_external_candidate_does_not_become_observed_evidence(tmp_path):
    f=tmp_path/'l.jsonl'
    proposal=lessons.add_lesson(f,sample(source_kind='external_proposal',evidence='candidate'))
    checked=lessons.add_lesson(f,sample(source_kind='task_observation',evidence='observed once',
                                       verified_by='independent numerical counterexample',supersedes=proposal['id']))
    assert lessons.search_lessons(f,'control')[0]['id']==checked['id']
    assert lessons.load(f)[0]['evidence']=='candidate'
    assert checked['evidence']!='checked on a held-out problem'
