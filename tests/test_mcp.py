import json
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
