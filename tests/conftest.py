"""Keep generated test artifacts in this checkout's ignored session directory."""
from pathlib import Path


def pytest_configure(config):
    (Path(__file__).resolve().parents[1] / '.session').mkdir(exist_ok=True)
