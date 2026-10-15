import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals import aggregate as ag


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run([sys.executable, '-m', 'evals.aggregate', *map(str, args)],
                          cwd=ROOT, capture_output=True, text=True, timeout=10)


def test_help_exits_successfully_without_opening_a_file():
    result = run_cli('--help')
    assert result.returncode == 0, result.stderr
    assert 'usage:' in result.stdout and '--contest' in result.stdout and '--view' in result.stdout
    assert result.stderr == ''


@pytest.mark.parametrize('contest', [None, 'general', 'mcm', 'cumcm'])
@pytest.mark.parametrize('view', [None, 'user', 'internal'])
def test_existing_equals_options_and_default_views_preserve_outputs(tmp_path, contest, view):
    first, second = tmp_path / 'first review.json', tmp_path / 'second.json'
    for path, score in ((first, 2), (second, 3)):
        path.write_text(json.dumps([{'paper': 'P', 'scores': dict.fromkeys(ag.WEIGHTS, score)}]))
    args = ([f'--contest={contest}'] if contest else []) + [str(first)]
    if view:
        args.append(f'--view={view}')  # The old CLI allowed --view between file names.
    args.append(str(second))
    result = run_cli(*args)
    assert result.returncode == 0, result.stderr
    report = ag.aggregate([first, second], contest)
    selected = view or ('user' if contest and contest != 'general' else 'internal')
    expected = ag.user_view(report, contest) if selected == 'user' else report
    assert json.loads(result.stdout) == expected
    assert result.stderr == ''


def test_standard_separate_options_can_follow_files(tmp_path):
    path = tmp_path / 'review.json'
    path.write_text(json.dumps([{'paper': 'P', 'scores': dict.fromkeys(ag.WEIGHTS, 2)}]))
    result = run_cli(path, '--contest', 'mcm', '--view', 'internal')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ag.aggregate([path], 'mcm')


@pytest.mark.parametrize('args, message', [
    ([], 'required'),
    (['--unknown-flag'], 'unrecognized arguments'),
    (['--view=other'], 'invalid choice'),
    (['--contest=graduate'], 'invalid choice'),
    (['--view'], 'expected one argument'),
    (['--contest'], 'expected one argument'),
])
def test_bad_arguments_have_cli_errors_without_file_tracebacks(tmp_path, args, message):
    path = tmp_path / 'review.json'
    path.write_text('[]')
    supplied_file = args and ('=' in args[0] or args == ['--unknown-flag'])
    result = run_cli(*(args + ([str(path)] if supplied_file else [])))
    assert result.returncode == 2
    assert message in result.stderr and 'Traceback' not in result.stderr
    assert result.stdout == ''


def test_missing_input_path_is_distinct_from_an_unknown_option(tmp_path):
    path = tmp_path / 'missing.json'
    result = run_cli(path)
    assert result.returncode != 0
    assert str(path) in result.stderr and 'unrecognized arguments' not in result.stderr


def test_double_dash_allows_a_file_named_like_an_option(tmp_path):
    path = tmp_path / '--review.json'
    path.write_text('[]')
    result = run_cli('--', path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {}
