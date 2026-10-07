import pytest

from modeling import routes


def build():
    return routes.apply(None, [
        dict(op='add_structure', key='flow', text='资源沿网络流动，守恒', evidence='derived'),
        dict(op='add_assumption', key='a_linear', text='费用与流量成正比', evidence='assumed', if_false='改用凸费用网络流'),
        dict(op='add_path', key='P1', title='最小费用流', structure='flow', assumptions=['a_linear'], needs='弧容量与单位费用'),
        dict(op='add_path', key='P2', title='整数规划（逐变量）'),
        dict(op='add_path', key='P3', title='仿真加搜索'),
    ], question='怎样调运？')


def test_cannot_choose_without_alternatives_or_surviving_attack():
    g = build()['graph']
    with pytest.raises(ValueError, match='no attack'):
        routes.choose(g, 'P1', '因为快')
    routes.attack(g, 'P1', '线性费用假设', '拿一个已知凸费用小例子对照', 'survived', '差距小于 1e-9')
    routes.choose(g, 'P1', '有解析界且可验证')
    assert g['paths']['P1']['status'] == 'chosen'
    only = routes.apply(None, [dict(op='add_path', key='X', title='唯一路线'),
                               dict(op='attack', key='X', claim='c', method='m', outcome='survived')], question='q')['graph']
    with pytest.raises(ValueError, match='fewer than two'):
        routes.choose(only, 'X', '没有别的')


def test_assumption_without_fallback_blocks_choice():
    g = build()['graph']
    routes.add_assumption(g, 'a_data', '需求已知', evidence='unknown', if_false='')
    g['paths']['P1']['assumptions'].append('a_data')
    routes.attack(g, 'P1', 'c', 'm', 'survived')
    with pytest.raises(ValueError, match='fallback'):
        routes.choose(g, 'P1', 'x')


def test_killed_route_needs_reason_and_attack_can_kill():
    g = build()['graph']
    with pytest.raises(ValueError):
        routes.kill(g, 'P2', ' ')
    routes.attack(g, 'P2', '整数性', '松弛后与整数解对比', 'killed', '规模 1e6，求解超时')
    assert g['paths']['P2']['status'] == 'killed' and g['paths']['P2']['reason'] == '规模 1e6，求解超时'
    routes.attack(g, 'P1', 'c', 'm', 'killed', '负环')
    with pytest.raises(ValueError, match='killed this route'):
        routes.choose(g, 'P1', 'x')


def test_merge_keeps_parts_and_partial_results():
    g = build()['graph']
    routes.keep_result(g, 'bound', '网络流松弛给出费用下界', status='derived', source_path='P1', reusable_in=['P3'])
    routes.merge(g, ['P1', 'P3'], 'H1', '流模型加仿真', '流模型给出初值，仿真做稳健性检验')
    assert g['paths']['P1']['status'] == 'merged' and g['paths']['H1']['assumptions'] == ['a_linear']
    assert ['P1', 'H1', 'merges'] in g['edges']
    assert 'bound' in routes.trace_markdown(g)


def test_validate_reports_problems_and_trace_is_readable():
    result = build()
    g = result['graph']
    assert not any('killed' in i for i in result['issues'])
    g['paths']['P2']['status'] = 'killed'
    assert any('killed without a reason' in i for i in routes.validate(g))
    assert '最小费用流' in result['trace'] and '若不成立：改用凸费用网络流' in result['trace']


def test_apply_reports_the_failing_operation_and_does_not_mutate_input():
    first = build()['graph']
    snapshot = repr(first)
    with pytest.raises(ValueError, match='operation 2 .*already exists'):
        routes.apply(first, [dict(op='add_path', key='P4', title='x'), dict(op='add_path', key='P4', title='y')])
    assert repr(first) == snapshot
    with pytest.raises(ValueError, match='unknown op'):
        routes.apply(first, [dict(op='teleport')])


def test_draft_lesson_reads_the_record_and_requires_a_principle():
    from modeling import lessons
    g = build()['graph']
    routes.attack(g, 'P2', '整数性', '松弛', 'killed', '规模太大')
    routes.attack(g, 'P1', '线性费用', '凸费用小例子对照', 'survived')
    routes.choose(g, 'P1', '有解析界且可验证')
    draft = routes.draft_lesson(g, problem='调运', principle='约束矩阵若是网络矩阵，先试线性规划')
    assert 'P2: 规模太大' in draft['what_failed'] and draft['what_worked'].startswith('P1')
    assert '凸费用小例子对照' in draft['verified_by'] and len(draft['routes_tried']) == 3
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        assert lessons.add_lesson(pathlib.Path(d) / 'l.jsonl', draft)['id'] == 'L0001'
    with pytest.raises(ValueError, match='exactly one chosen'):
        routes.draft_lesson(build()['graph'], problem='x', principle='y')
