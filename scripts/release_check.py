"""Run before tagging a release: the quick demo reruns, then the test suite, with a pass/fail line for each.

    uv run --locked python -m scripts.release_check          # quick demos (about three minutes) and tests
    uv run --locked python -m scripts.release_check --long   # also the long MCM re-optimisation runs (about 40 minutes)

A demo run must exit cleanly and leave the tracked records unchanged: the check fails if git shows a change under demos/."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUICK = ['demos/domino-research/reproduce/explore.py', 'demos/cumcm-1998-a/reproduce/run_demo.py', 'demos/cumcm-1998-a/reproduce/check_capital_threshold.py',
         'demos/cumcm-1998-a/reproduce/check_recommendation.py', 'demos/cumcm-1998-a/reproduce/check_robustness.py', 'demos/cumcm-1998-a/reproduce/check_alternatives.py',
         'demos/mcm-2016-a/reproduce/run_demo.py']
LONG = ['demos/mcm-2016-a/reproduce/run_extended.py', 'demos/mcm-2016-a/reproduce/run_mesh_check.py']


def run(command):
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode == 0


def changed_demo_files():
    out = subprocess.run(['git', 'status', '--short', 'demos'], cwd=ROOT, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--long', action='store_true')
    args = parser.parse_args()
    failures = []
    for script in QUICK + (LONG if args.long else []):
        ok = run(['uv', 'run', '--locked', 'python', script])
        print(('PASS ' if ok else 'FAIL ') + script, flush=True)
        if not ok:
            failures.append(script)
    drift = changed_demo_files()
    print(('PASS ' if not drift else 'FAIL ') + 'demo records unchanged' + ('' if not drift else f': {drift}'), flush=True)
    ok = run(['uv', 'run', '--locked', 'python', '-m', 'pytest', '-q'])
    print(('PASS ' if ok else 'FAIL ') + 'test suite', flush=True)
    return 0 if not failures and not drift and ok else 1


if __name__ == '__main__':
    sys.exit(main())
