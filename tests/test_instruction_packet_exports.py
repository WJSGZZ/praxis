"""Consume real host exports without widening instruction-source access."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.build_plugin import BUNDLE, HOSTS, build_plugin
from scripts.instruction_packet import ROLES, build_packet, read_source


@pytest.fixture(scope='module', params=HOSTS)
def exported(request, tmp_path_factory):
    destination = tmp_path_factory.mktemp('packet-export') / request.param
    build_plugin(destination, host=request.param)
    return destination


@pytest.mark.parametrize("stage", ("contest", "research", *ROLES))
def test_real_export_packets(exported, stage):
    bundle = exported / 'skills/praxis'
    integrity = (bundle / 'references/integrity.md').read_text()
    text, manifest = build_packet(bundle, stage=stage)
    assert integrity in text
    assert '不得通过删除文件、回滚、换 Agent' in text
    assert manifest['core_characters'] <= 9390
    assert len(text) == (manifest['core_characters'] + manifest['required_detail_characters']
                         + manifest['conditional_detail_characters'])
    expected = ROLES if stage in ('contest', 'research') else (stage,)
    for role in expected:
        skill = exported / f'skills/praxis-{role}/SKILL.md'
        assert skill.read_text() in text
        assert f'name: praxis-{role}\n' in text
        record = next(row for row in manifest['sources']
                      if row['path'] == f'skills/praxis-{role}/SKILL.md')
        assert Path(record['resolved_path']) == skill.resolve()


@pytest.mark.parametrize("stage", ("contest", "research", *ROLES))
def test_real_export_cli_from_unrelated_cwd(exported, tmp_path, stage):
    bundle = exported / "skills/praxis"
    arguments = [] if stage == 'contest' else ['--stage', stage]
    manifest_path = tmp_path / 'manifest.json'
    result = subprocess.run(
        [sys.executable, str(bundle / 'scripts/instruction_packet.py'), *arguments,
         '--manifest', str(manifest_path)],
        cwd=tmp_path, capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    manifest = json.loads(manifest_path.read_text())
    assert len(result.stdout) == manifest['emitted_characters']
    assert manifest['core_characters'] <= 9390
    assert manifest['required_detail_characters'] > 0 if stage == 'research' else manifest['required_detail_characters'] == 0
    assert (bundle / 'references/integrity.md').read_text() in result.stdout
    if stage != 'research':
        assert len(result.stdout) <= 9390
    else:
        assert (bundle / 'references/research-mode.md').read_text() in result.stdout
    for role in ROLES if stage in ('contest', 'research') else (stage,):
        assert f'name: praxis-{role}\n' in result.stdout


def test_source_and_overlay_precedence_remain_local(tmp_path):
    original, _ = read_source(BUNDLE, None, 'skills/praxis-model/SKILL.md')
    assert original == (BUNDLE / 'skills/praxis-model/SKILL.md').read_text()
    overlay = tmp_path / 'overlay'
    target = overlay / 'skills/praxis-model/SKILL.md'
    target.parent.mkdir(parents=True)
    target.write_text('overlay model', encoding='utf-8')
    selected, record = read_source(BUNDLE, overlay, 'skills/praxis-model/SKILL.md')
    assert selected == 'overlay model'
    assert Path(record['resolved_path']) == target
    assert read_source(BUNDLE, overlay, 'references/integrity.md')[0] == (
        BUNDLE / 'references/integrity.md').read_text()
    target.unlink()
    target.symlink_to(BUNDLE / 'skills/praxis-model/SKILL.md')
    with pytest.raises(ValueError, match='Outside'):
        read_source(BUNDLE, overlay, 'skills/praxis-model/SKILL.md')


@pytest.fixture
def boundary_export(tmp_path):
    # An isolated official export: mutations must never alter the shared host
    # exports or the working bundle.
    output = tmp_path / 'official'
    build_plugin(output)
    return output


@pytest.mark.parametrize('target', ['outside', 'other-role', 'unrelated-neighbor'])
def test_role_symlinks_cannot_escape_or_select_neighbor(boundary_export, tmp_path, target):
    output = boundary_export
    role = output / 'skills/praxis-model'
    original = role / 'SKILL.md'
    if target == 'outside':
        destination = tmp_path / 'outside.md'
        destination.write_text(original.read_text(), encoding='utf-8')
    elif target == 'other-role':
        destination = output / 'skills/praxis-compute/SKILL.md'
    else:
        destination = output / 'skills/unrelated/SKILL.md'
        destination.parent.mkdir()
        destination.write_text(original.read_text(), encoding='utf-8')
    original.unlink()
    original.symlink_to(destination)
    with pytest.raises(ValueError):
        read_source(output / 'skills/praxis', None, 'skills/praxis-model/SKILL.md')


def test_role_directory_symlink_is_rejected(boundary_export, tmp_path):
    role = boundary_export / 'skills/praxis-model'
    elsewhere = tmp_path / 'copy-model'
    shutil.move(role, elsewhere)
    role.symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError):
        read_source(boundary_export / 'skills/praxis', None, 'skills/praxis-model/SKILL.md')


def test_unmanaged_neighbors_and_noncanonical_paths_are_rejected(boundary_export):
    bundle = boundary_export / 'skills/praxis'
    for relative in ('../praxis-model/SKILL.md', 'skills/praxis-model/../praxis-model/SKILL.md',
                     'skills/praxis-review/SKILL.md', 'skills/unrelated/SKILL.md'):
        with pytest.raises((ValueError, OSError)):
            read_source(bundle, None, relative)
    receipt = boundary_export / 'build-receipt.json'
    data = json.loads(receipt.read_text())
    data['files_sha256'].pop('skills/praxis-model/SKILL.md')
    receipt.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError):
        read_source(bundle, None, 'skills/praxis-model/SKILL.md')


def test_changed_neighbor_not_authenticated_by_export_receipt(boundary_export):
    role = boundary_export / 'skills/praxis-model/SKILL.md'
    role.write_text('name: unrelated\n', encoding='utf-8')
    with pytest.raises(ValueError):
        read_source(boundary_export / 'skills/praxis', None, 'skills/praxis-model/SKILL.md')


def test_source_cannot_fall_back_to_arbitrary_siblings(tmp_path):
    bundle = tmp_path / 'source'
    bundle.mkdir()
    neighbor = tmp_path / 'praxis-model/SKILL.md'
    neighbor.parent.mkdir()
    neighbor.write_text('unrelated neighbor', encoding='utf-8')
    with pytest.raises((ValueError, OSError)):
        read_source(bundle, None, 'skills/praxis-model/SKILL.md')


def test_source_research_and_report_do_not_load_competition_cores():
    for stage in ('report', 'research'):
        text, manifest = build_packet(BUNDLE, stage=stage)
        paths = {row['path'] for row in manifest['sources']}
        assert 'references/contest-paper-checklist.md' not in paths
        assert 'references/contest-delivery.md' not in paths
        assert '--contest mcm' not in text
        assert manifest['core_characters'] <= 9390
    original = (BUNDLE / 'references/research-mode.md').read_text()
    assert original in text
    assert [row['id'] for row in manifest['required_details']] == ['research']
    assert manifest['required_detail_characters'] > len(original)
    assert len(text) == manifest['core_characters'] + manifest['required_detail_characters']
    assert not manifest['details']
    again, duplicate = build_packet(BUNDLE, stage='research', details=['research', 'research'])
    assert again == text
    assert duplicate['required_detail_characters'] == manifest['required_detail_characters']
    contest, manifest = build_packet(BUNDLE)
    paths = {row['path'] for row in manifest['sources']}
    assert {'references/contest-paper-checklist.md', 'references/contest-delivery.md'} <= paths


def test_offline_index_is_deterministic_source_and_stdout_only(tmp_path):
    from scripts.instruction_packet import DETAILS, render_index
    index = render_index()
    assert index == render_index() == (BUNDLE / 'references/instruction-index.md').read_text()
    for key in DETAILS:
        assert f'| `{key}` |' in index
    assert '额外必读 detail `research`' in index
    result = subprocess.run([sys.executable, str(BUNDLE / 'scripts/instruction_packet.py'),
                             '--print-index'], cwd=tmp_path, capture_output=True,
                            text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    assert result.stdout == index
    assert not result.stderr
    assert list(tmp_path.iterdir()) == []


def test_official_export_index_links_resolve(exported):
    import re
    index = exported / 'skills/praxis/references/instruction-index.md'
    text = index.read_text()
    for destination in re.findall(r'\]\(([^)]+)\)', text):
        path = destination.split('#')[0]
        assert (index.parent / path).resolve().is_file(), destination
    for role in ROLES:
        assert f'](../../praxis-{role}/SKILL.md)' in text
