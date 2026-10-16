import pytest

from modeling import lessons


def sample(**kw):
    base = dict(problem='cooling bath, minimise added water', structure='energy balance + monotone loss', recognized='loss grows with temperature',
                routes_tried=['simulation only', 'ODE with lower bound'], what_failed='simulation gave no optimality evidence',
                what_worked='coast then hold, proved by monotonicity', verified_by='independent ODE integration', principle='if loss is monotone in state, delay the control',
                tags=['ode', 'control'], checklist=['Check the control bound against an independent ODE solution.'])
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


def test_legacy_active_reuse_does_not_apply_new_append_limits(tmp_path):
    import json
    path = tmp_path / 'legacy.jsonl'
    legacy = sample(id='L0001', date='2020-01-01', evidence='observed once',
                    principle='Historical principle. ' * 30,
                    tags=[f'old-tag-{i}' for i in range(9)])
    legacy.pop('checklist')
    path.write_text(json.dumps(legacy) + '\n', encoding='utf-8')
    before = path.read_bytes()
    assert lessons.add_lesson(path, legacy) == legacy
    assert path.read_bytes() == before


def test_multilabel_historical_structures_are_searchable_without_rewriting(tmp_path):
    from scripts import mcp_server
    f = tmp_path / 'lessons.jsonl'
    first = lessons.add_lesson(f, sample(structure=['energy', 'control', 'energy']))
    second = lessons.add_lesson(f, sample(problem='another task', structure=['energy', 'lower-bound']))
    original = f.read_bytes()
    out = mcp_server.call('lesson_search', {'path': str(f), 'query': 'energy', 'limit': 5})
    assert {r['id'] for r in out['lessons']} == {first['id'], second['id']}
    assert out['patterns']['by_structure'] == {'energy': 2, 'control': 1, 'lower-bound': 1}
    assert out['patterns']['repeated_structures'] == {'energy': 2}
    assert f.read_bytes() == original


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
    # Legacy seeds remain readable; newly appended observations obey the compact contract.
    assert all('checklist' not in rec for rec in records)
    lessons.add_lesson(target, sample(problem='another'))


@pytest.mark.parametrize('query', ['', '   ', 'the of and', 'THE, OF; AND!', 'an the of and'])
def test_empty_and_function_word_queries_do_not_retrieve_seed_lessons(query):
    from pathlib import Path
    seed = Path(__file__).resolve().parents[1] / 'templates/lessons-seed.jsonl'
    original = seed.read_bytes()
    assert lessons.search_lessons(seed, query) == []
    assert seed.read_bytes() == original


def test_function_words_do_not_change_content_ranking_or_explicit_tags(tmp_path):
    from pathlib import Path
    import shutil
    target = tmp_path / 'lessons.jsonl'
    shutil.copy(Path(__file__).resolve().parents[1] / 'templates/lessons-seed.jsonl', target)
    original = target.read_bytes()
    for plain, padded, expected in (
        ('mesh refinement point source inlet constraint', 'THE mesh refinement OF point source AND inlet constraint!', 'S0001'),
        ('三维热网络中带入口点源的温度约束', 'the 三维热网络中带入口点源的温度约束 of and', 'S0001'),
        ('整数规划 二元变量 容差 MILP', 'the 整数规划 and 二元变量 of 容差 MILP', 'S0004'),
    ):
        found = lessons.search_lessons(target, plain)
        assert found[0]['id'] == expected
        assert lessons.search_lessons(target, padded) == found
    assert lessons.search_lessons(target, 'the of and', tags=['MILP'])[0]['id'] == 'S0004'
    assert lessons.search_lessons(target, '', tags=['MILP'])[0]['id'] == 'S0004'
    assert target.read_bytes() == original


def test_filter_matches_whole_words_and_keeps_domain_terms_and_tag_identity(tmp_path):
    target = tmp_path / 'lessons.jsonl'
    record = lessons.add_lesson(target, sample(problem='theory of bandwidth and software proofs',
                                             tags=['and', 'x']))
    for query in ('THEORY', 'bandwidth', 'software', 'proofs', 'x'):
        assert lessons.search_lessons(target, query)[0]['id'] == record['id']
    assert lessons.search_lessons(target, 'the of and') == []
    assert lessons.search_lessons(target, tags=['AND'])[0]['id'] == record['id']


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


@pytest.mark.parametrize('string_target', [False, True])
def test_active_superseding_lesson_retry_reuses_identity_without_append(tmp_path, string_target):
    from scripts import mcp_server
    f = tmp_path / 'lessons.jsonl'
    first = lessons.add_lesson(f, sample())
    target = first['id'] if string_target else [first['id']]
    request = sample(principle='The resource region must allow alternative assignments', supersedes=target)
    replacement = mcp_server.call('lesson_add', {'path': str(f), 'lesson': request})
    saved = f.read_bytes()
    assert mcp_server.call('lesson_add', {'path': str(f), 'lesson': request}) == replacement
    assert f.read_bytes() == saved
    assert [r['id'] for r in lessons.active(f)] == [replacement['id']]
    assert len(lessons.load(f)) == 2


def test_replacement_retry_matches_parent_set_but_never_revives_retired_record(tmp_path):
    f = tmp_path / 'lessons.jsonl'
    a = lessons.add_lesson(f, sample())
    b = lessons.add_lesson(f, sample(problem='another original observation'))
    request = sample(principle='A shared resource cut replaces both observations', supersedes=[a['id'], b['id']])
    replacement = lessons.add_lesson(f, request)
    saved = f.read_bytes()
    assert lessons.add_lesson(f, dict(request, supersedes=[b['id'], a['id']])) == replacement
    assert f.read_bytes() == saved
    for targets in ([a['id'], a['id']], ['missing'], [a['id']]):
        with pytest.raises(ValueError, match='supersedes'):
            lessons.add_lesson(f, dict(request, supersedes=targets))
        assert f.read_bytes() == saved
    lessons.add_lesson(f, {'event': 'retire', 'target': replacement['id'], 'reason': 'Independent counterexample'})
    retired = f.read_bytes()
    with pytest.raises(ValueError):
        lessons.add_lesson(f, request)
    assert f.read_bytes() == retired and not lessons.active(f)


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


@pytest.mark.parametrize('change,message', [
    ({'checklist': None}, 'checklist'),
    ({'checklist': []}, 'checklist'),
    ({'checklist': ['Check units.'] * 4}, 'checklist'),
    ({'checklist': ['Check ' + 'x' * 116]}, '120'),
    ({'principle': 'x' * 301}, 'principle'),
    ({'tags': [f'tag{i}' for i in range(9)]}, 'tags'),
    ({'tags': 'not a list'}, 'tags'),
    ({'hidden_extra': 'x' * 2000}, '1500'),
    ({'derived_from': 'missing'}, 'derived_from'),
])
def test_new_lesson_limits_are_atomic_including_extra_fields(tmp_path, change, message):
    path = tmp_path / 'lessons.jsonl'
    lessons.add_lesson(path, sample())
    before = path.read_bytes()
    with pytest.raises(ValueError, match=message):
        lessons.add_lesson(path, sample(problem='new observation', **change))
    assert path.read_bytes() == before


@pytest.mark.parametrize('instruction', ['在相同误差条件下核对候选结构。', 'Using the same observation history, compare feasible actions.'])
def test_checklist_accepts_conditional_actions_without_a_verb_whitelist(tmp_path, instruction):
    # Meaning and imperative style are author-reviewed; the machine checks shape.
    record = lessons.add_lesson(tmp_path / 'lessons.jsonl', sample(checklist=[instruction]))
    assert record['checklist'] == [instruction]


def test_total_record_length_counts_json_keys_values_and_metadata(tmp_path):
    import json
    path = tmp_path / 'lessons.jsonl'
    first = lessons.add_lesson(path, sample())
    count = lambda r: len(json.dumps(r, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
    payload = sample(problem='a different observation', derived_from=first['id'], date='2026-10-16')
    expected = dict(payload, evidence='observed once', source_kind='legacy_unspecified',
                    tags=sorted(payload['tags']), id='L0002')
    payload['extra'] = '中' * (1500 - count(expected) - len(',"extra":""'))
    new = lessons.add_lesson(path, payload)
    assert count(new) == 1500
    with pytest.raises(ValueError, match='1500'):
        lessons.add_lesson(path, dict(payload, problem='a different observation!', extra=payload['extra'] + '中'))


def test_legacy_long_records_stay_readable_but_cannot_be_newly_appended(tmp_path):
    import json
    path = tmp_path / 'lessons.jsonl'
    legacy = sample(problem='legacy observation', what_worked='historical ' * 2000)
    legacy.pop('checklist')
    legacy.update(id='L0001', evidence='observed once')
    path.write_text(json.dumps(legacy) + '\n')
    before = path.read_bytes()
    assert lessons.load(path) == [legacy]
    assert lessons.search_lessons(path, 'legacy')[0]['id'] == 'L0001'
    with pytest.raises(ValueError, match='checklist'):
        lessons.add_lesson(path, dict(legacy, problem='new'))
    assert path.read_bytes() == before


def test_search_uses_only_five_fields_and_normalizes_long_records(tmp_path):
    import json
    path = tmp_path / 'lessons.jsonl'
    long = sample(id='L0001', problem='generic historical traffic forecast water',
                  structure='archive ' * 2500, principle='Scope old rules carefully.',
                  what_worked='highway network opioid county optimization ' * 2500,
                  verified_by='only_evidence_field',
                  tags=[])
    long.pop('checklist')
    path.write_text(json.dumps(long) + '\n')
    for subject in ('traffic flow optimization highway network', 'forecast opioid counts county', 'water supply storage balance'):
        for index in range(3):
            lessons.add_lesson(path, sample(problem=f'{subject} example {index}', structure=subject,
                                           principle='Check this specific system.', tags=[]))
    for query in ('traffic flow optimization on a highway network', 'forecast opioid counts by county', 'water supply storage balance'):
        hits = lessons.search_lessons(path, query)
        assert hits and hits[0]['id'] != 'L0001'
        assert 'L0001' not in [r['id'] for r in hits[:3]]
    assert lessons.search_lessons(path, 'Scope old rules carefully')[0]['id'] == 'L0001'
    assert lessons.search_lessons(path, 'historical')
    assert lessons.search_lessons(path, 'only_evidence_field') == []


def test_compact_search_preserves_ids_order_and_legacy_checklist_gap(tmp_path):
    import json
    from scripts import mcp_server
    path = tmp_path / 'lessons.jsonl'
    legacy = sample(id='L0001', problem='legacy thermal control')
    legacy.pop('checklist')
    path.write_text(json.dumps(legacy) + '\n')
    lessons.add_lesson(path, sample(problem='new thermal control'))
    full = lessons.search_lessons(path, 'thermal control')
    compact = lessons.search_lessons(path, 'thermal control', compact=True)
    assert [r['id'] for r in compact] == [r['id'] for r in full]
    assert all(set(r) == {'id', 'checklist', 'principle'} for r in compact)
    assert next(r for r in compact if r['id'] == 'L0001')['checklist'] == []
    via_mcp = mcp_server.call('lesson_search', {'path': str(path), 'query': 'thermal control', 'compact': True})
    assert via_mcp['lessons'] == compact
