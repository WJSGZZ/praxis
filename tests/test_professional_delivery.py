"""Preserve actual source files when an audit writes its derived report."""
from pathlib import Path
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("hardlink", [False, True])
def test_cli_output_cannot_overwrite_its_source_contract(tmp_path, hardlink):
    data = tmp_path / "input.csv"
    data.write_text("x\n1\n2\n")
    contract = tmp_path / "contract.json"
    contract.write_text('{"columns":{"x":{"kind":"numeric"}}}')
    output = contract
    if hardlink:
        output = tmp_path / "contract-alias.json"
        try:
            os.link(contract, output)
        except OSError as error:
            pytest.skip(f"Filesystem does not support this hardlink fixture: {error}")
    before = contract.read_bytes(), data.read_bytes()
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "scripts/audit_data.py"), str(data),
                             "--contract", str(contract), "--output", str(output)],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 2
    assert "source contract" in result.stderr
    assert before == (contract.read_bytes(), data.read_bytes())
