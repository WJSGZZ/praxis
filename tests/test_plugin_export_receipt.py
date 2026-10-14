"""The exported receipt must cover every shipped file except itself."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_plugin import build_plugin
from scripts.plugin_hosts import HOSTS


@pytest.mark.parametrize('host', HOSTS)
def test_export_receipt_binds_every_final_shipped_file(tmp_path, host):
    destination = tmp_path / host
    build_plugin(destination, host=host)
    receipt = json.loads((destination / 'build-receipt.json').read_text(encoding='utf-8'))
    shipped = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob('*')
        if path.is_file() and path != destination / 'build-receipt.json'
    }
    assert set(receipt['files_sha256']) == shipped
    for name, expected in receipt['files_sha256'].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize('host', HOSTS)
def test_real_export_is_utf8_under_cp1252_default_and_matches_all_bytes(tmp_path, host, monkeypatch):
    """Exercise real text I/O, not a source scan or global UTF-8 mode."""
    normal = tmp_path/'normal'
    simulated = tmp_path/'cp1252-default'
    build_plugin(normal, host=host)
    actual_read, actual_write = Path.read_text, Path.write_text
    calls = []

    def locale_read(path, encoding=None, errors=None):
        calls.append(('read', str(path), encoding))
        return actual_read(path, encoding=encoding or 'cp1252', errors=errors)

    def locale_write(path, data, encoding=None, errors=None, newline=None):
        calls.append(('write', str(path), encoding))
        return actual_write(path, data, encoding=encoding or 'cp1252', errors=errors, newline=newline)

    with monkeypatch.context() as context:
        context.setattr(Path, 'read_text', locale_read)
        context.setattr(Path, 'write_text', locale_write)
        build_plugin(simulated, host=host)

    assert calls and all(encoding == 'utf-8' for _, _, encoding in calls)
    expected = json.loads((normal/'build-receipt.json').read_text(encoding='utf-8'))
    observed = json.loads((simulated/'build-receipt.json').read_text(encoding='utf-8'))
    assert observed == expected
    shipped = {path.relative_to(simulated).as_posix() for path in simulated.rglob('*')
               if path.is_file() and path != simulated/'build-receipt.json'}
    assert shipped == set(observed['files_sha256'])
    for name, digest in observed['files_sha256'].items():
        raw = (simulated/name).read_bytes()
        assert raw == (normal/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
    root_readme = (simulated/'README.md').read_bytes().decode('utf-8')
    skill = (simulated/'skills/praxis/SKILL.md').read_bytes().decode('utf-8')
    native = json.loads((simulated/'.codex-plugin/plugin.json').read_bytes().decode('utf-8'))
    assert '插件' in root_readme and '数学' in skill
    assert native['interface']['shortDescription'] == '数学建模，从问题到证据'
