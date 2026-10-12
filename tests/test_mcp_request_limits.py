"""Transport limits refuse one bad frame while preserving the next request."""
import io
import json

import pytest

from scripts import mcp_server as server


@pytest.mark.parametrize('binary', [False, True])
def test_exact_boundary_empty_lines_and_final_unterminated_frame(binary):
    data = 'abcd\n\nxyz'
    stream = io.BytesIO(data.encode()) if binary else io.StringIO(data)
    actual = list(server._request_lines(stream, 5))
    assert actual == ([b'abcd\n', b'\n', b'xyz'] if binary else ['abcd\n', '\n', 'xyz'])


@pytest.mark.parametrize('binary', [False, True])
def test_oversize_frame_is_drained_once_without_losing_next_frame(binary):
    data = 'x' * 100_000 + '\nnext\n'
    stream = io.BytesIO(data.encode()) if binary else io.StringIO(data)
    actual = list(server._request_lines(stream, 5))
    assert actual == [None, b'next\n' if binary else 'next\n']


def test_utf8_limit_is_in_bytes_for_text_and_binary_streams():
    data = '汉汉\nok\n'
    assert list(server._request_lines(io.StringIO(data), 5)) == [None, 'ok\n']
    assert list(server._request_lines(io.BytesIO(data.encode()), 5)) == [None, b'ok\n']


def test_stdio_rejects_oversize_and_invalid_utf8_then_pings(monkeypatch):
    data = b'x' * 300 + b'\n\xff\n' + b'{"jsonrpc":"2.0","id":7,"method":"ping"}\n'
    stream = io.TextIOWrapper(io.BytesIO(data), encoding='utf-8')
    out = io.StringIO()
    monkeypatch.setattr(server, 'MAX_MCP_REQUEST_BYTES', 128)
    monkeypatch.setattr(server.sys, 'stdin', stream)
    monkeypatch.setattr(server.sys, 'stdout', out)
    server.serve()
    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    assert [r.get('error', {}).get('code') for r in replies] == [-32600, -32700, None]
    assert replies[-1] == {'jsonrpc': '2.0', 'id': 7, 'result': {}}


def test_oversize_json_never_executes_a_tool(monkeypatch):
    packet = {'id': 1, 'method': 'tools/call', 'params': {'name': 'solve_lp', 'arguments': {'padding': 'x' * 300}}}
    stream = io.StringIO(json.dumps(packet) + '\n' + '{"id":2,"method":"ping"}\n')
    out = io.StringIO()
    monkeypatch.setattr(server, 'MAX_MCP_REQUEST_BYTES', 128)
    monkeypatch.setattr(server.sys, 'stdin', stream)
    monkeypatch.setattr(server.sys, 'stdout', out)
    def forbidden_call(*args, **kwargs):
        raise AssertionError('Oversized request was executed')
    monkeypatch.setattr(server, 'bounded_call', forbidden_call)
    server.serve()
    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    assert replies[0]['error']['code'] == -32600
    assert replies[1]['result'] == {}


@pytest.mark.parametrize('bad_frame', [
    '{"id":1,"id":2,"method":"ping"}',
    '{"id":1,"method":"tools/call","params":{"name":"solve_lp","arguments":{"c":[3,2],"c":[0,0]}}}',
    '[' * 2000 + '0' + ']' * 2000,
])
def test_ambiguous_or_excessively_nested_json_is_refused_then_next_request_runs(monkeypatch, bad_frame):
    out = io.StringIO()
    monkeypatch.setattr(server.sys, 'stdin', io.StringIO(bad_frame + '\n{"id":7,"method":"ping"}\n'))
    monkeypatch.setattr(server.sys, 'stdout', out)
    monkeypatch.setattr(server, 'bounded_call', lambda *_: pytest.fail('Bad JSON executed a tool'))
    server.serve()
    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    assert replies[0]['error']['code'] == -32700
    assert replies[1] == {'jsonrpc': '2.0', 'id': 7, 'result': {}}
