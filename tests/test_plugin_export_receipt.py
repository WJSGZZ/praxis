"""The exported receipt must cover every shipped file except itself."""
import hashlib
import json

import pytest

from scripts.build_plugin import build_plugin
from scripts.plugin_hosts import HOSTS


@pytest.mark.parametrize('host', HOSTS)
def test_export_receipt_binds_every_final_shipped_file(tmp_path, host):
    destination = tmp_path / host
    build_plugin(destination, host=host)
    receipt = json.loads((destination / 'build-receipt.json').read_text())
    shipped = {
        str(path.relative_to(destination))
        for path in destination.rglob('*')
        if path.is_file() and path != destination / 'build-receipt.json'
    }
    assert set(receipt['files_sha256']) == shipped
    for name, expected in receipt['files_sha256'].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == expected
