from pathlib import Path

import pytest

from scripts import release_check


@pytest.mark.parametrize('entry', ['run_demo.py', 'check_return_target.py', 'check_target_certificates.py'])
def test_repeated_release_checks_preserve_existing_demo_output(tmp_path, monkeypatch, entry):
    source = tmp_path / "demo" / "reproduce"
    source.mkdir(parents=True)
    (source / "reference.txt").write_text("archived reference")
    existing = source / "reproduced"
    existing.mkdir()
    (existing / "user.txt").write_text("prior user run")
    (source / entry).write_text("# fixture")
    observed = []

    def execute(command):
        copied = Path(command[-1]).parent
        assert copied != source
        assert not (copied / "reproduced").exists()
        assert (copied / "reference.txt").read_text() == "archived reference"
        (copied / "reproduced").mkdir()
        observed.append(copied)
        return True

    monkeypatch.setattr(release_check, "ROOT", tmp_path)
    monkeypatch.setattr(release_check, "run", execute)
    for _ in range(2):
        assert release_check.run_demo("demo/reproduce/" + entry)
    assert (existing / "user.txt").read_text() == "prior user run"
    assert all(not path.exists() for path in observed)


@pytest.mark.parametrize('entry', ['examples/data_analysis_demo.py', 'examples/spatial_analysis_demo.py'])
def test_example_release_checks_supply_fresh_output_without_touching_source(tmp_path, monkeypatch, entry):
    source = tmp_path / entry
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b'# synthetic example source')
    observed = []

    def execute(command):
        assert command[4] == str(source) and command[5] == '--output'
        output = Path(command[6])
        assert not output.exists() and not output.is_relative_to(tmp_path)
        output.mkdir()
        (output / 'report.json').write_text('{}')
        observed.append(output)
        return True

    monkeypatch.setattr(release_check, 'ROOT', tmp_path)
    monkeypatch.setattr(release_check, 'run', execute)
    for _ in range(2):
        assert release_check.run_demo(entry)
    assert source.read_bytes() == b'# synthetic example source'
    assert all(not path.exists() for path in observed)
