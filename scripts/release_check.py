"""Run before tagging a release: the quick demo reruns, then the test suite, with a pass/fail line for each.

    uv run --locked python -m scripts.release_check          # quick demos (about three minutes) and tests
    uv run --locked python -m scripts.release_check --long   # also the long MCM re-optimisation runs (about 40 minutes)

A demo run must exit cleanly and leave the tracked records unchanged: the check fails if git shows a change under demos/."""
import argparse
from datetime import datetime, timezone
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
QUICK = ['demos/domino-research/reproduce/explore.py', 'demos/cumcm-1998-a/reproduce/run_demo.py', 'demos/cumcm-1998-a/reproduce/check_capital_threshold.py',
         'demos/cumcm-1998-a/reproduce/check_recommendation.py', 'demos/cumcm-1998-a/reproduce/check_robustness.py', 'demos/cumcm-1998-a/reproduce/check_alternatives.py',
         'demos/cumcm-1998-a/reproduce/check_return_target.py', 'demos/cumcm-1998-a/reproduce/check_target_certificates.py',
         'demos/mcm-2016-a/reproduce/run_demo.py', 'examples/data_analysis_demo.py', 'examples/spatial_analysis_demo.py', 'examples/image_analysis_demo.py', 'demos/data-vintages/run.py']
LONG = ['demos/mcm-2016-a/reproduce/run_extended.py', 'demos/mcm-2016-a/reproduce/run_mesh_check.py']


def run(command):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        print(result.stdout, end='')
        print(result.stderr, end='', file=sys.stderr)
    return result.returncode == 0


def run_demo(script):
    source = ROOT / script
    if script == 'examples/image_analysis_demo.py':
        with tempfile.TemporaryDirectory(prefix='praxis-release-image-') as temporary:
            run_dir = Path(temporary) / 'generated-mask'
            if not run(['uv', 'run', '--locked', 'python', str(source), '--output', str(run_dir)]):
                return False
            return run(['uv', 'run', '--locked', 'python', 'demos/image-analysis/build_figure.py',
                        '--run', str(run_dir), '--output', str(Path(temporary) / 'generated-figure')])
    if script in {'examples/data_analysis_demo.py', 'examples/spatial_analysis_demo.py', 'demos/data-vintages/run.py'}:
        with tempfile.TemporaryDirectory(prefix='praxis-release-data-') as temporary:
            return run(['uv', 'run', '--locked', 'python', str(source), '--output',
                        str(Path(temporary) / 'generated-demo')])
    if source.name not in {'run_demo.py', 'check_return_target.py', 'check_target_certificates.py'}:
        return run(['uv', 'run', '--locked', 'python', script])
    # The submitted reproduction scripts deliberately refuse to overwrite output.
    # Exercise the unchanged package in isolation so repeat checks preserve both
    # the archived reference records and any user's previous reproduction.
    with tempfile.TemporaryDirectory(prefix='praxis-release-') as temporary:
        work = Path(temporary) / 'reproduce'
        shutil.copytree(source.parent, work,
                        ignore=shutil.ignore_patterns('reproduced', '__pycache__'))
        return run(['uv', 'run', '--locked', 'python', str(work / source.name)])


def changed_demo_files():
    out = subprocess.run(['git', 'status', '--short', 'demos'], cwd=ROOT, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def check_main_cases(manifest, *, workspace, output):
    """Write an impact report only; never execute/rebuild a scientific case.

    Differences and stale/unknown results require explanation, rather than
    failing a code test. Reading/assessment errors fail this optional gate.
    """
    from scripts import case_refresh
    try:
        report = case_refresh.refresh(manifest, workspace=workspace, dry_run=True,
                                      output=output, rebuild=False)
    except Exception as exc:
        print(f'FAIL main cases report: {type(exc).__name__}: {exc}', flush=True)
        return False
    for row in report['cases']:
        delta = row.get('numeric_delta')
        changes = len(delta['changes']) if delta is not None else None
        count = str(changes) if changes is not None else 'unknown (not computed)'
        detail = 'explanation required' if changes or row.get('conclusion_changes') else 'review report'
        print(f"CASE {row['id']}: {', '.join(row['categories'])}; "
              f'numeric changes={count}; {detail}', flush=True)
    ok = report['status'] != 'failed'
    print(('PASS ' if ok else 'FAIL ') + 'main cases dry-run report: '
          + str(Path(workspace).resolve() / output / 'report.json'), flush=True)
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--long', action='store_true')
    parser.add_argument('--main-cases', type=Path, help='Optional manifest in the private modeling workspace')
    parser.add_argument('--workspace', type=Path, help='Workspace containing the main cases; default: current directory')
    parser.add_argument('--case-report', type=Path, help='New report directory inside that workspace')
    args = parser.parse_args()
    if args.main_cases is None and (args.workspace is not None or args.case_report is not None):
        parser.error('--workspace and --case-report require --main-cases')
    failures = []
    for script in QUICK + (LONG if args.long else []):
        ok = run_demo(script)
        print(('PASS ' if ok else 'FAIL ') + script, flush=True)
        if not ok:
            failures.append(script)
    drift = changed_demo_files()
    print(('PASS ' if not drift else 'FAIL ') + 'demo records unchanged' + ('' if not drift else f': {drift}'), flush=True)
    if args.main_cases is not None:
        workspace = args.workspace or Path.cwd()
        destination = args.case_report or (Path('outputs/release-main-cases') /
            (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]))
        if not check_main_cases(args.main_cases, workspace=workspace, output=destination):
            failures.append('main cases dry-run report')
    ok = run(['uv', 'run', '--locked', 'python', '-m', 'pytest', '-q'])
    print(('PASS ' if ok else 'FAIL ') + 'test suite', flush=True)
    return 0 if not failures and not drift and ok else 1


if __name__ == '__main__':
    sys.exit(main())
