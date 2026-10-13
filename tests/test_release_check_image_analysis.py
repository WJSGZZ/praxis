"""Release quick-check coverage for the synthetic image demo."""
from pathlib import Path

from scripts import release_check


def test_image_demo_is_in_quick_checks_and_runs_demo_then_figure(monkeypatch):
    script = "examples/image_analysis_demo.py"
    assert script in release_check.QUICK
    commands = []

    def fake_run(command):
        commands.append(command)
        return True

    monkeypatch.setattr(release_check, "run", fake_run)
    assert release_check.run_demo(script)
    assert len(commands) == 2
    assert commands[0][4] == str(release_check.ROOT / script)
    assert commands[1][4] == "demos/image-analysis/build_figure.py"
    assert Path(commands[0][-1]).parent == Path(commands[1][commands[1].index("--run") + 1]).parent
    assert commands[0][-1] == commands[1][commands[1].index("--run") + 1]
