"""Exercise the actual temporal tool contract and recoverable stdio errors."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.mcp_server import EXAMPLES, TOOLS, call


def test_registered_example_uses_declared_availability_and_default_strictness():
    example = EXAMPLES['asof_join']
    result = call('asof_join', example)
    assert result['mappings'][0]['matched_version_index'] == 0
    assert result['allow_exact_matches'] is False
    assert result['schema_version'] == 1
    query = dict(example['queries'][0], cutoff='2026-01-02T07:50:00Z')
    strict = call('asof_join', dict(example, queries=[query]))
    assert strict['counts']['not_available'] == 1
    equal = call('asof_join', dict(example, queries=[query], allow_exact_matches=True))
    assert equal['mappings'][0]['matched_version_index'] == 0
    schema = TOOLS['asof_join']['schema']
    assert schema['properties']['allow_exact_matches']['default'] is False
    assert schema['properties']['queries']['maxItems'] == 20000


@pytest.mark.parametrize('extra', [{'direction': 'nearest'}, {'allow_exact_matches': 1},
                                   {'on': []}, {'decision_time': ''}])
def test_invalid_temporal_arguments_do_not_reach_mapping(extra):
    with pytest.raises(ValueError):
        call('asof_join', dict(EXAMPLES['asof_join'], **extra))


def test_actual_stdio_keeps_unknown_release_and_recovers_after_bad_timestamp():
    example = EXAMPLES['asof_join']
    missing = dict(example, versions=[dict(example['versions'][0], released=None)])
    bad = dict(example, queries=[dict(example['queries'][0], cutoff='2026-01-02')])
    messages = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
         'params': {'protocolVersion': '2025-06-18'}},
        {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
    ]
    for number, args in enumerate([missing, bad, example], start=3):
        messages.append({'jsonrpc': '2.0', 'id': number, 'method': 'tools/call',
                         'params': {'name': 'asof_join', 'arguments': args}})
    process = subprocess.run([sys.executable, '-m', 'scripts.mcp_server'],
                             cwd=Path(__file__).resolve().parents[1], text=True,
                             input='\n'.join(json.dumps(m) for m in messages) + '\n',
                             capture_output=True, timeout=30)
    assert process.returncode == 0, process.stderr
    replies = [json.loads(line) for line in process.stdout.splitlines()]
    assert len(replies[1]['result']['tools']) == len(TOOLS)
    unknown = json.loads(replies[2]['result']['content'][0]['text'])
    assert unknown['counts']['unknown_availability'] == 1
    assert unknown['mappings'][0]['matched_version_index'] is None
    assert replies[3]['result']['isError'] is True
    recovered = json.loads(replies[4]['result']['content'][0]['text'])
    assert recovered['mappings'][0]['matched_version_index'] == 0
