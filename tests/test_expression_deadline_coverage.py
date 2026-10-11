"""Discover current expression consumers independently of the deadline roster."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from scripts import mcp_server as server

ROOT = Path(__file__).resolve().parents[1]
MC = dict(expression='x**2', distributions={'x': dict(dist='uniform', params=dict(loc=3, scale=0))}, n=64)


def expression_consumers():
    """Trace this module's compiler wrappers plus its external relation evaluator.

    This is a bounded source check for the current registry, not a general Python
    call-graph analyzer. New external expression evaluators need a reviewed root.
    No tool names or membership in EXPRESSION_TOOLS decide the expected set.
    """
    tree = ast.parse((ROOT/'scripts/mcp_server.py').read_text())

    def calls(node):
        names = set()
        for item in ast.walk(node):
            if isinstance(item, ast.Call):
                if isinstance(item.func, ast.Name):
                    names.add(item.func.id)
                elif isinstance(item.func, ast.Attribute) and isinstance(item.func.value, ast.Name):
                    names.add(item.func.value.id + '.' + item.func.attr)
        return names

    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    reaches = {'_compile', '_predicate', 'experiment.find_relation'}
    while True:
        extra = {name for name, node in functions.items() if calls(node) & reaches}
        if extra <= reaches:
            break
        reaches |= extra
    registry = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'TOOLS' for t in n.targets))
    expected = set()
    for node in ast.walk(registry):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_tool':
            function = node.args[4]
            invoked = {function.id} if isinstance(function, ast.Name) else calls(function)
            if invoked & reaches:
                expected.add(node.args[0].value)
    return expected


CONSUMERS = sorted(expression_consumers())


def test_all_current_expression_consumers_have_a_deadline():
    expected = expression_consumers()
    assert 'monte_carlo' in expected  # the original omission must be discoverable
    assert expected == server.EXPRESSION_TOOLS


@pytest.mark.parametrize('name', CONSUMERS)
@pytest.mark.parametrize('entry', ['mcp', 'cli'])
def test_every_expression_entry_rejects_late_results_and_recovers(monkeypatch, name, entry):
    # A missed route safely waits 30ms and returns a recognizable late result.
    # The child starts unmodified source; 1ms is a test-only shortened deadline,
    # not a claim that a real production expression exceeded 30 seconds.
    def controlled_call(tool, arguments):
        time.sleep(.03)
        return {'late_result': True}

    monkeypatch.setattr(server, 'call', controlled_call)
    monkeypatch.setattr(server, 'EXPRESSION_TIMEOUT_SECONDS', .001)
    if entry == 'mcp':
        reply = server.handle(dict(id=1, method='tools/call', params=dict(name=name, arguments={})))
        assert reply['result']['isError'] is True
        assert 'TimeoutError' in reply['result']['content'][0]['text']
        assert 'late_result' not in reply['result']['content'][0]['text']
    else:
        monkeypatch.setattr(sys, 'argv', ['mcp_server', '--call', name, '{}'])
        with pytest.raises(TimeoutError, match='no result accepted'):
            server.main()
    assert server.handle(dict(id=2, method='ping'))['result'] == {}


def check_constant_answer(result):
    # Degenerate uniform inputs are exactly x=3, so every outcome is 9.
    assert result['n'] == 64 and result['mean'] == 9
    assert result['mc_standard_error'] == result['sd'] == 0
    assert result['half_sample_means'] == [9, 9] and result['settled']
    assert all(value == 9 for value in result['quantiles'].values())


def test_actual_cli_monte_carlo_retains_independent_answer():
    run = subprocess.run([sys.executable, '-m', 'scripts.mcp_server', '--call', 'monte_carlo', json.dumps(MC)],
                         cwd=ROOT, capture_output=True, text=True, timeout=15)
    assert run.returncode == 0, run.stderr
    check_constant_answer(json.loads(run.stdout))


def test_actual_stdio_monte_carlo_answer_bad_expression_and_recovery():
    requests = [dict(jsonrpc='2.0', id=1, method='initialize', params=dict(protocolVersion='2025-06-18')),
                dict(jsonrpc='2.0', method='notifications/initialized'),
                dict(jsonrpc='2.0', id=2, method='tools/call', params=dict(name='monte_carlo', arguments=MC)),
                dict(jsonrpc='2.0', id=3, method='tools/call', params=dict(name='monte_carlo', arguments={**MC, 'expression': '2**(201+1)'})),
                dict(jsonrpc='2.0', id=4, method='ping')]
    run = subprocess.run([sys.executable, '-m', 'scripts.mcp_server'], cwd=ROOT,
                         input='\n'.join(json.dumps(r) for r in requests)+'\n',
                         capture_output=True, text=True, timeout=15)
    assert run.returncode == 0, run.stderr
    replies = [json.loads(line) for line in run.stdout.splitlines()]
    assert [r['id'] for r in replies] == [1, 2, 3, 4]
    assert not replies[1]['result']['isError']
    check_constant_answer(json.loads(replies[1]['result']['content'][0]['text']))
    assert replies[2]['result']['isError'] and 'ValueError' in replies[2]['result']['content'][0]['text']
    assert replies[3]['result'] == {}
