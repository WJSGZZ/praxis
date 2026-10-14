"""Actual bare CLI/export checks and safe, deliberately broken disk resources."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts import runtime_info
from scripts.build_plugin import build_plugin

SRC = Path(__file__).resolve().parents[1]


def minimal_export(tmp_path):
    root = tmp_path / 'export'
    core = root / 'skills/praxis'
    for name in runtime_info.KEY_RESOURCES:
        p = core / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('Local diagnostic fixture\n', encoding='utf-8')
    (core / 'pyproject.toml').write_text('[project]\nname="praxis"\nversion="0.8.0"\nrequires-python=">=3.12,<3.13"\ndependencies=[]\n')
    (core / 'scripts/build_plugin.py').write_text("FOCUSED=('praxis-model',)\n")
    p = root / 'skills/praxis-model/SKILL.md'
    p.parent.mkdir(parents=True)
    p.write_text('Declared local skill fixture\n')
    (root / 'README.md').write_text('Package root guidance\n')
    (root / 'LICENSE').write_text('Local fixture license\n')
    receipt = dict(format='praxis-plugin-export-v1', name='praxis', version='0.8.0', host='portable',
                   files_sha256={p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in root.rglob('*') if p.is_file()})
    (root / 'build-receipt.json').write_text(json.dumps(receipt))
    return root, core, receipt


def test_actual_bare_python_cli_is_useful_without_numpy_or_site_packages():
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    p = subprocess.run([sys.executable, '-S', '-B', '-m', 'scripts.runtime_info'], cwd=SRC,
                       env=env, text=True, capture_output=True, timeout=15)
    assert p.returncode == 0, p.stderr
    value = json.loads(p.stdout)
    assert value['schema_version'] == 1 and value['status'] == 'attention'
    assert value['process']['executable'] == os.path.abspath(sys.executable)
    assert value['process']['site_startup'] == 'disabled_by_-S'
    assert value['dependencies']['missing'] == value['dependencies']['declared'] > 0
    assert value['tools']['status'] == 'not_loaded' and value['tools']['count'] is None
    assert value['core_path'] == str(SRC)
    assert value['export_receipt']['status'] == 'not_applicable'
    assert len(p.stdout) < 20000


def test_source_and_actual_export_use_actual_manifest_contract(tmp_path, monkeypatch):
    source = runtime_info.inspect_runtime(tool_names=('actual_one', 'actual_two'))
    assert source['tools']['count'] == 2 and source['tools']['status'] == 'provided_by_caller'
    assert source['export_receipt']['status'] == 'not_applicable'
    assert source['resources']['missing'] == source['resources']['unsafe'] == 0
    root = tmp_path / 'actual-export'
    build_plugin(root, source=SRC)
    core = root / 'skills/praxis'
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', core)
    receipt = json.loads((root / 'build-receipt.json').read_text())
    assert 'README.md' in receipt['files_sha256'] and 'LICENSE' in receipt['files_sha256']
    (core / '.venv').mkdir()
    (core / '.venv/ignored-generated-file').write_text('Not a shipped resource')
    good = runtime_info.inspect_runtime()
    assert good['export_receipt']['status'] == 'matched'
    assert good['export_receipt']['matched'] == len(receipt['files_sha256'])
    assert good['resources']['focused_skills_present'] > 0
    assert len(json.dumps(good, allow_nan=False)) < 20000
    receipt_bytes = (root / 'build-receipt.json').read_bytes()
    (root / 'build-receipt.json').unlink()
    unknown = runtime_info.inspect_runtime()
    assert unknown['core_layout'] == 'export' and unknown['status'] == 'attention'
    assert unknown['export_receipt']['status'] == 'not_present'
    assert unknown['export_receipt']['integrity'] == 'unknown'
    assert unknown['resources']['missing'] == unknown['resources']['unsafe'] == 0
    (root / 'build-receipt.json').write_bytes(receipt_bytes)
    (root / 'README.md').write_text('Changed root guidance')
    changed = runtime_info.inspect_runtime()
    assert changed['status'] == 'attention' and changed['export_receipt']['changed'] == 1
    (core / 'templates/mcm-style.tex').unlink()
    missing = runtime_info.inspect_runtime()
    assert missing['resources']['missing'] == 1 and missing['export_receipt']['missing'] == 1


def test_added_nested_source_tree_cannot_hide_changed_export_receipt(tmp_path, monkeypatch):
    import shutil
    from scripts.build_plugin import FOCUSED
    root = tmp_path/'actual-export'
    build_plugin(root, source=SRC)
    core = root/'skills/praxis'
    for name in FOCUSED:
        nested = core/'skills'/name/'SKILL.md'
        nested.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/'skills'/name/'SKILL.md', nested)
    (root/'README.md').write_text('Changed exported guidance')
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', core)
    value = runtime_info.inspect_runtime()
    assert value['status'] == 'attention'
    assert value['export_receipt']['status'] == 'attention'
    assert value['export_receipt']['changed'] == 1


@pytest.mark.parametrize('name', ['../outside.txt', '/outside.txt', 'C:/outside.txt',
                                  'skills/praxis/.venv/private.txt', 'build-receipt.json'])
def test_receipt_cannot_expand_scope_to_unsafe_paths(tmp_path, monkeypatch, name):
    root, core, receipt = minimal_export(tmp_path)
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', core)
    receipt['files_sha256'][name] = '0' * 64
    (root / 'build-receipt.json').write_text(json.dumps(receipt))
    value = runtime_info.inspect_runtime()
    assert value['export_receipt']['unsafe'] == 1 and value['status'] == 'attention'
    assert value['export_receipt']['matched'] == len(receipt['files_sha256']) - 1


def test_actual_source_clone_inside_skills_is_not_an_export(tmp_path):
    core = tmp_path / 'skills/praxis'
    shutil.copytree(SRC, core, ignore=shutil.ignore_patterns('.git', '.venv', '.session', '__pycache__', '*.pyc'))
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    process = subprocess.run([sys.executable, '-S', '-B', '-m', 'scripts.runtime_info'],
                             cwd=core, env=env, text=True, capture_output=True, timeout=15)
    assert process.returncode == 0, process.stderr
    value = json.loads(process.stdout)
    assert value['core_path'] == str(core) and value['core_layout'] == 'source'
    assert value['resources']['missing'] == value['resources']['unsafe'] == 0
    assert value['resources']['focused_skills_present'] == 23
    assert value['export_receipt']['status'] == 'not_applicable'
    assert value['dependencies']['missing'] == value['dependencies']['declared']


@pytest.mark.parametrize('directory', ['cases', 'planning', 'lessons', '.local', 'outputs', '.session'])
def test_receipt_does_not_read_user_case_or_runtime_files(tmp_path, monkeypatch, directory):
    root, core, receipt = minimal_export(tmp_path)
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', core)
    private = core / directory / 'private.txt'
    private.parent.mkdir()
    private.write_text('User content must not be inspected')
    receipt['files_sha256'][private.relative_to(root).as_posix()] = '0' * 64
    (root / 'build-receipt.json').write_text(json.dumps(receipt))
    original = Path.open
    def guarded(path, *args, **kwargs):
        assert path != private, 'Private user file was opened'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    value = runtime_info.inspect_runtime()
    assert value['export_receipt']['unsafe'] == 1
    assert value['export_receipt']['matched'] == len(receipt['files_sha256']) - 1


def test_receipt_symlink_escape_is_not_opened(tmp_path, monkeypatch):
    root, core, receipt = minimal_export(tmp_path)
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', core)
    outside = tmp_path / 'outside.txt'
    outside.write_text('Must never be read')
    link = root / 'escape.txt'
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip('This host does not allow symlink creation')
    receipt['files_sha256']['escape.txt'] = '0' * 64
    (root / 'build-receipt.json').write_text(json.dumps(receipt))
    original = Path.open
    def guarded(path, *args, **kwargs):
        assert path not in (link, outside), 'Untrusted target was opened'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    value = runtime_info.inspect_runtime()
    assert value['export_receipt']['unsafe'] == 1


def test_symlinked_receipt_is_attention_without_reading_target(tmp_path, monkeypatch):
    root, core, _ = minimal_export(tmp_path)
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', core)
    outside = tmp_path / 'private-receipt.json'
    outside.write_text('Private metadata must never be read')
    receipt = root / 'build-receipt.json'
    receipt.unlink()
    try:
        receipt.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip('This host does not allow symlink creation')
    original = Path.open
    def guarded(path, *args, **kwargs):
        assert path not in (receipt, outside), 'Untrusted receipt was opened'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    value = runtime_info.inspect_runtime()
    assert value['core_layout'] == 'export'
    assert value['export_receipt']['status'] == value['status'] == 'attention'


def test_missing_distribution_version_metadata_is_reported(tmp_path, monkeypatch):
    _, core, _ = minimal_export(tmp_path)
    (core / 'pyproject.toml').write_text('[project]\nname="praxis"\nversion="0.8.0"\ndependencies=["broken-dist>=1"]\n')
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', core)
    monkeypatch.setattr(runtime_info.metadata, 'version', lambda name: None)
    value = runtime_info.inspect_runtime()
    assert value['dependencies']['missing'] == 1 and value['status'] == 'attention'
    assert value['dependencies']['packages'][0]['status'] == 'metadata_unreadable'


def test_source_skill_root_symlink_is_not_followed(tmp_path, monkeypatch):
    root, core, receipt = minimal_export(tmp_path)
    source = tmp_path / 'source'
    source.mkdir()
    for child in core.iterdir():
        if child.is_dir():
            shutil.copytree(child, source / child.name)
        else:
            (source / child.name).write_bytes(child.read_bytes())
    try:
        (source / 'skills').symlink_to(root / 'skills', target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('This host does not allow symlink creation')
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', source)
    value = runtime_info.inspect_runtime()
    assert value['resources']['unsafe'] == 1 and value['status'] == 'attention'


@pytest.mark.parametrize('raw', ['{"format":"a","format":"b"}',
                                 '{"format": NaN}', '{"extra": 1e999}', '[]'])
def test_invalid_receipt_is_attention_not_an_exception(tmp_path, monkeypatch, raw):
    root, core, receipt = minimal_export(tmp_path)
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', core)
    (root / 'build-receipt.json').write_text(raw)
    value = runtime_info.inspect_runtime()
    assert value['status'] == value['export_receipt']['status'] == 'attention'
    json.dumps(value, allow_nan=False)


def test_compiler_is_only_located_and_many_gaps_stay_bounded(tmp_path, monkeypatch):
    root, core, receipt = minimal_export(tmp_path)
    monkeypatch.setattr(runtime_info, 'CORE_ROOT', core)
    monkeypatch.setattr(runtime_info.shutil, 'which', lambda name: '/local/fake/tectonic')
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: pytest.fail('Diagnostic attempted execution'))
    for i in range(100):
        receipt['files_sha256'][f'missing/{i}.txt'] = '0' * 64
    (root / 'build-receipt.json').write_text(json.dumps(receipt))
    value = runtime_info.inspect_runtime()
    assert value['export_receipt']['missing'] == 100
    assert len(value['export_receipt']['samples']) == runtime_info.MAX_SAMPLES
    assert value['compiler']['status'] == 'found_not_verified' and value['compiler']['executed'] is False
    assert len(json.dumps(value, allow_nan=False)) < 20000


def test_tools_are_not_guessed_and_invalid_supplied_names_are_rejected():
    assert runtime_info.inspect_runtime()['tools']['count'] is None
    for names in ('solve_lp', ['x', 'x'], [True], ['x'] * 513):
        with pytest.raises(ValueError):
            runtime_info.inspect_runtime(tool_names=names)
