import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from scripts.build_plugin import BUNDLE, build_plugin


def test_export_is_self_contained_and_excludes_runtime_data(tmp_path):
    output = tmp_path / 'plugin'
    build_plugin(output)
    receipt = json.loads((output / 'build-receipt.json').read_text())
    assert json.loads((output / 'plugin.json').read_text())['name'] == 'praxis'
    for name, digest in receipt['files_sha256'].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    assert not any(part in {'.git', '.venv', '.session', 'cases', 'outputs', '__pycache__'}
                   for path in output.rglob('*') for part in path.relative_to(output).parts)
    # README showcase links must also work in an exported, self-contained bundle.
    demo = output / 'skills/praxis/demos/cumcm-1998-a'
    assert (demo / 'deliverables/paper.pdf').read_bytes() == (
        BUNDLE / 'demos/cumcm-1998-a/deliverables/paper.pdf').read_bytes()
    assert (demo / 'assets/risk-return.png').is_file()
    assert (demo / 'assets/risk-return-zh.png').is_file()
    assert (demo / 'reproduce/run_demo.py').is_file()
    assert not (demo / 'reproduce/reproduced').exists()
    bath = output / 'skills/praxis/demos/mcm-2016-a'
    assert (bath / 'deliverables/7391856.pdf').read_bytes() == (BUNDLE / 'demos/mcm-2016-a/deliverables/7391856.pdf').read_bytes()
    assert (bath / 'assets/overview-zh.png').is_file()
    assert (bath / 'reproduce/reference/trajectory.npz').is_file()
    assert not (bath / 'reproduce/reproduced').exists()
    problem = tmp_path / 'synthetic.md'
    problem.write_text('Synthetic packaging check only.')
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    result = subprocess.run([sys.executable, str(output / 'skills/praxis/scripts/pipeline.py'),
                             '--workspace', str(workspace), 'init', '--name', 'export-check',
                             '--problem', str(problem)], cwd=workspace, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert list(workspace.rglob('planning/tasks.md'))
    assert not list((output / 'skills/praxis').glob('cases/*'))


def test_export_preserves_existing_target(tmp_path):
    output = tmp_path / 'plugin'
    output.mkdir()
    (output / 'keep.txt').write_text('existing user content')
    with pytest.raises(FileExistsError):
        build_plugin(output)
    assert (output / 'keep.txt').read_text() == 'existing user content'


def test_export_rejects_links_to_external_content(tmp_path):
    source = tmp_path / 'source'
    # A public source clone without environments or user artifacts.
    from scripts.build_plugin import public_files
    for path in public_files(BUNDLE):
        target = source / path.relative_to(BUNDLE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    external = tmp_path / 'external.md'
    external.write_text('Must not be published')
    (source / 'references/external.md').symlink_to(external)
    with pytest.raises(ValueError, match='Symlink'):
        build_plugin(tmp_path / 'plugin', source)
    assert not (tmp_path / 'plugin').exists()


FOCUSED = ('praxis-model', 'praxis-compute', 'praxis-verify', 'praxis-explore', 'praxis-dialogue', 'praxis-report')


def _links(text):
    import re
    return [m for m in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', text) if '://' not in m]


def test_focused_skills_are_valid_and_links_resolve_in_repo_and_export(tmp_path):
    output = tmp_path / 'plugin'
    build_plugin(output)
    for name in FOCUSED:
        for root in (BUNDLE / 'skills' / name, output / 'skills' / name):
            text = (root / 'SKILL.md').read_text()
            header = text.split('---')[1]
            assert f'name: {name}\n' in header
            description = [l for l in header.splitlines() if l.startswith('description:')][0]
            assert 0 < len(description) < 1100
            for link in _links(text):
                assert (root / link).resolve().is_file(), (root, link)


def test_all_packaged_markdown_links_resolve_after_relocation(tmp_path):
    """Core, focused, references and showcases must form one usable package."""
    output = tmp_path / 'plugin'
    build_plugin(output)
    for path in output.rglob('*.md'):
        for link in _links(path.read_text()):
            assert (path.parent / link).resolve().exists(), (path.relative_to(output), link)
    core = output / 'skills/praxis/SKILL.md'
    assert '](../praxis-model/SKILL.md)' in core.read_text()
    convergence = output / 'skills/praxis/references/convergence.md'
    assert '](../../praxis-dialogue/SKILL.md)' in convergence.read_text()


def test_link_relocation_preserves_anchors_titles_and_external_urls():
    from scripts.build_plugin import relocate_links, public_files
    text = ('[model](skills/praxis-model/SKILL.md#route "Choose a route") '
            '[web](https://example.com/skills/praxis-model/SKILL.md) [here](#route)')
    actual = relocate_links(text, BUNDLE / 'SKILL.md', BUNDLE, public_files(BUNDLE))
    assert actual == ('[model](../praxis-model/SKILL.md#route "Choose a route") '
                      '[web](https://example.com/skills/praxis-model/SKILL.md) [here](#route)')


def test_export_declares_a_working_mcp_server(tmp_path):
    output = tmp_path / 'plugin'
    build_plugin(output)
    config = json.loads((output / 'mcp.json').read_text())
    assert config['$schema'].endswith('/mcp.schema.json')
    server = config['mcpServers']['praxis-tools']
    assert server['type'] == 'stdio' and server['cwd'] == '${PLUGIN_ROOT}/skills/praxis'
    # Third-party server: exact version, papers stored in plugin data rather than the home directory.
    arxiv = config['mcpServers']['arxiv']
    assert arxiv['args'][0] == 'arxiv-mcp-server==0.8.1' and arxiv['args'][-1].startswith('${PLUGIN_DATA}')
    # Same module the manifest launches, started from the exported copy.
    request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}) + '\n'
    result = subprocess.run([sys.executable, '-m', 'scripts.mcp_server'], cwd=output / 'skills/praxis',
                            input=request, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    names = {t['name'] for t in json.loads(result.stdout)['result']['tools']}
    assert {'solve_lp', 'ahp_weights', 'check_references'} <= names


def test_exported_mcp_handshake_computation_and_error_recovery(tmp_path):
    output = tmp_path / 'plugin'
    build_plugin(output)
    messages = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
         'params': {'protocolVersion': '2025-06-18', 'capabilities': {},
                    'clientInfo': {'name': 'plugin-check', 'version': '1'}}},
        {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
         'params': {'name': 'solve_lp', 'arguments': {'c': [3, 2], 'A_ub': [[1, 1], [1, 0], [0, 1]],
                    'b_ub': [4, 2, 3], 'maximize': True}}},
        {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
         'params': {'name': 'solve_lp', 'arguments': {}}},
        {'jsonrpc': '2.0', 'id': 4, 'method': 'ping'},
    ]
    result = subprocess.run([sys.executable, '-m', 'scripts.mcp_server'],
                            cwd=output / 'skills/praxis', input='\n'.join(map(json.dumps, messages)) + '\n',
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    assert [reply['id'] for reply in replies] == [1, 2, 3, 4]
    assert replies[0]['result']['serverInfo']['name'] == 'praxis-tools'
    assert not replies[1]['result']['isError']
    answer = json.loads(replies[1]['result']['content'][0]['text'])
    # Independent bound: 3x+2y = 2(x+y)+x <= 2*4+2 = 10; attained at (2,2).
    assert answer['objective'] == pytest.approx(10)
    assert answer['x'] == pytest.approx([2, 2])
    assert replies[2]['result']['isError']
    assert replies[3]['result'] == {}


def test_plugin_manifest_version_matches_pyproject():
    import json
    import tomllib
    root = Path(__file__).resolve().parents[1]
    assert json.loads((root / 'packaging/plugin.json').read_text())['version'] == tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']


def test_exported_plugin_carries_the_seed_lessons(tmp_path):
    out = tmp_path / 'plugin'
    build_plugin(out)
    assert (out / 'skills/praxis/templates/lessons-seed.jsonl').is_file()
