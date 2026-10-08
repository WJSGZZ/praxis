from pathlib import Path

from scripts import release_check


def test_repeated_release_checks_preserve_existing_demo_output(tmp_path, monkeypatch):
    source = tmp_path / "demo" / "reproduce"
    source.mkdir(parents=True)
    (source / "reference.txt").write_text("archived reference")
    existing = source / "reproduced"
    existing.mkdir()
    (existing / "user.txt").write_text("prior user run")
    (source / "run_demo.py").write_text("# fixture")
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
        assert release_check.run_demo("demo/reproduce/run_demo.py")
    assert (existing / "user.txt").read_text() == "prior user run"
    assert all(not path.exists() for path in observed)
