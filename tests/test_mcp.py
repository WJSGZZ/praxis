import json
import pytest
import subprocess
import sys
from pathlib import Path

from scripts.mcp_server import TOOLS, call

ROOT = Path(__file__).resolve().parents[1]


def rpc(*messages):
    process = subprocess.run([sys.executable, '-m', 'scripts.mcp_server'], cwd=ROOT, text=True, capture_output=True,
                             input='\n'.join(json.dumps(m) for m in messages) + '\n', timeout=60)
    assert process.returncode == 0, process.stderr
    return [json.loads(line) for line in process.stdout.splitlines()]


def test_stdio_handshake_listing_and_call():
    replies = rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
                  {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                  {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                  {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'solve_lp', 'arguments': {
                      'c': [3, 2], 'A_ub': [[1, 1], [1, 3]], 'b_ub': [4, 6], 'bounds': [[0, 3], [0, None]], 'maximize': True}}},
                  {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'queue_mmc', 'arguments': {
                      'arrival_rate': 2, 'service_rate': 1, 'servers': 2}}},
                  {'jsonrpc': '2.0', 'id': 5, 'method': 'nope'})
    assert [r['id'] for r in replies] == [1, 2, 3, 4, 5]  # the notification gets no reply
    assert replies[0]['result']['serverInfo']['name'] == 'praxis-tools'
    listed = {t['name'] for t in replies[1]['result']['tools']}
    assert listed == set(TOOLS) and 'solve_lp' in listed
    solved = json.loads(replies[2]['result']['content'][0]['text'])
    assert abs(solved['objective'] - 11) < 1e-9 and solved['certified']
    assert replies[3]['result']['isError'] is True  # unstable queue is a tool error, not a crash
    assert replies[4]['error']['code'] == -32601


def test_sobol_expression_is_restricted_and_correct():
    result = call('sobol_sensitivity', dict(expression='2*a + b', names=['a', 'b', 'c'], bounds=[[0, 1]] * 3, n=1024))
    s1 = {item['name']: item['S1'] for item in result['parameters']}
    assert abs(s1['a'] - .8) < .05 and abs(s1['b'] - .2) < .05 and abs(s1['c']) < .05
    for bad in ('__import__("os").system("true")', 'a.__class__', 'open("x")', '[a]'):
        try:
            call('sobol_sensitivity', dict(expression=bad, names=['a'], bounds=[[0, 1]], n=64))
        except ValueError:
            continue
        raise AssertionError(f'accepted {bad}')


def test_structure_and_exploration_tools_through_the_server():
    from scripts import mcp_server as server
    probe = server.call('probe_structure', dict(property='convexity', expression='x**2+y**2', names=['x', 'y'], bounds=[[-1, 1], [-1, 1]]))
    assert probe['convex'] and not probe['proved']
    bad = server.call('probe_structure', dict(property='monotone', expression='x**2', names=['x'], bounds=[[-1, 1]], variable='x'))
    assert bad['kind'] == 'not monotone'
    invariant = server.call('probe_structure', dict(property='invariant', expression='x**2+y**2', rhs=['y', '-x'], names=['x', 'y'], bounds=[[-2, 2], [-2, 2]]))
    assert invariant['conserved']
    assert server.call('dimensional_analysis', dict(matrix=[[0, 0, 0, 1], [0, 1, 1, 0], [1, 0, -2, 0]], names=['T', 'L', 'g', 'm']))['n_groups'] == 1
    assert server.call('check_total_unimodularity', dict(matrix=[[1, 1, 0], [0, 1, 1], [1, 0, 1]]))['totally_unimodular'] is False
    found = server.call('find_counterexample', dict(claim='isprime(n*n+n+41)', names=['n'], domain=[['int', 0, 100]]))
    assert found['counterexample'] == [40]
    with pytest.raises(ValueError):
        server.call('find_counterexample', dict(claim='__import__("os").system("true")', names=['n'], domain=[['int', 0, 3]]))
    conj = server.call('test_conjecture', dict(lhs='x**2', rhs='x', relation='<=', names=['x'], bounds=[[0, 3]]))
    assert not conj['holds']
    seq = server.call('guess_sequence', dict(sequence=[0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]))
    assert seq['recurrence']['coefficients'] == ['1', '1']
    rel = server.call('find_relation', dict(value='zeta(2)', constants={'pi2': 'pi**2'}))
    assert rel['found']
    graph = server.call('route_graph', dict(question='q', operations=[dict(op='add_path', key='A', title='a')]))
    assert graph['graph']['paths']['A']['status'] == 'open' and 'a' in graph['trace']


def test_lesson_tools_round_trip(tmp_path):
    from scripts import mcp_server as server
    path = str(tmp_path / 'lessons.jsonl')
    lesson = dict(problem='p', structure='s', recognized='r', routes_tried=['a'], what_failed='f', what_worked='w', verified_by='v', principle='rule', tags=['t'])
    assert server.call('lesson_add', dict(path=path, lesson=lesson))['id'] == 'L0001'
    found = server.call('lesson_search', dict(path=path, query='rule'))
    assert found['lessons'][0]['id'] == 'L0001' and found['patterns']['lessons'] == 1


def test_model_tools_through_the_server():
    from scripts import mcp_server as server
    heat = server.call('solve_diffusion', dict(length=1, k=1, rho_c=1, initial='sin(3.141592653589793*x)', t_end=.1, cells=100, steps=100, left=['dirichlet', 0], right=['dirichlet', 0]))
    exact = float(__import__('math').exp(-__import__('math').pi ** 2 * .1) * __import__('math').sin(__import__('math').pi * heat['x'][50]))
    assert abs(heat['u'][50] - exact) < 1e-3
    assert abs(server.call('matrix_game', dict(payoff=[[3, 2], [1, 4]]))['value'] - 2.5) < 1e-9
    assert abs(server.call('newsvendor', dict(price=10, cost=6, salvage=2, mean=100, sd=20))['order_quantity'] - 100) < 1e-9
    assert server.call('markov_stationary', dict(matrix=[[.7, .3], [.1, .9]]))['stationary'][0] == pytest.approx(.25)
    assert abs(server.call('eoq', dict(demand=1200, order_cost=50, holding_cost=2))['order_quantity'] - 244.9489742783178) < 1e-6
    eq = server.call('equilibria', dict(rhs=['x*(1-x)'], names=['x'], bounds=[[-.5, 2]]))
    assert sorted(e['kind'] for e in eq['equilibria']) == ['stable node', 'unstable node']
    assert server.call('pareto_front', dict(points=[[1, 5], [2, 4], [3, 3], [2, 2]], senses=[1, 1]))['indices'] == [0, 1, 2]
    kf = server.call('kalman_filter', dict(F=[[1]], H=[[1]], Q=[[.1]], R=[[1]], x0=[0], P0=[[1]], observations=[[1.0], [1.2], [0.9]]))
    assert len(kf['filtered_mean']) == 3
    cv = server.call('cvar_portfolio', dict(returns=[[.01, .05], [.02, -.04], [.01, .09], [.015, .0]], target=.02, alpha=.75))
    assert abs(sum(cv['weights']) - 1) < 1e-9


def test_missing_and_unknown_fields_are_reported_with_the_schema():
    from scripts import mcp_server as server
    with pytest.raises(ValueError, match=r"missing field\(s\) \['names'\].*required"):
        server.call('probe_structure', dict(property='convexity', expression='x', bounds=[[0, 1]]))
    with pytest.raises(ValueError, match=r"unknown field\(s\) \['kind'\]"):
        server.call('probe_structure', dict(kind='convexity', property='convexity', expression='x', names=['x'], bounds=[[0, 1]]))
    listing = subprocess.run([sys.executable, '-m', 'scripts.mcp_server', '--list'], capture_output=True, text=True, check=True).stdout
    assert 'probe_structure(property*, expression*, names*, bounds*' in listing
    described = json.loads(subprocess.run([sys.executable, '-m', 'scripts.mcp_server', '--describe', 'find_counterexample'], capture_output=True, text=True, check=True).stdout)
    assert 'domain' in described['input']['properties']


def test_recurrence_tools_and_route_modes_through_the_server():
    from scripts import mcp_server as server
    seq = [1, 3, 11, 41, 153, 571, 2131, 7953, 29681, 110771, 413403, 1542841, 5757961, 21489003]
    held = server.call('guess_sequence', dict(sequence=seq, holdout=3))
    assert held['recurrence']['holdout_ok'] and held['recurrence']['coefficients'] == ['4', '-1']
    proof = server.call('check_recurrence', dict(sequence=seq, coefficients=[4, -1], order_bound=8))
    assert proof['proof_by_finite_check']
    small = server.call('find_counterexample', dict(claim='n*n+n+41 > 0', names=['n'], domain=[['int', 0, 900]], exhaustive_limit=1000))
    assert small['proved_for_domain']
    g = server.call('route_graph', dict(question='q', mode='standard', operations=[dict(op='add_path', key='a', title='A'), dict(op='add_path', key='b', title='B'),
                                                                                 dict(op='attack', key='b', claim='c', method='m', outcome='survived'), dict(op='choose', key='b', why='w')]))
    assert g['graph']['paths']['b']['status'] == 'chosen' and g['graph']['mode'] == 'standard'
    kept = server.call('route_graph', dict(graph=g['graph'], operations=[dict(op='keep_result', key='r', statement='x', status='proved_finite_check')]))
    assert kept['graph']['partial_results']['r']['status'] == 'proved_finite_check'
