"""Small cross-platform tests for worker byte caps, deadline and failure handling."""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.bounded_execution import MAX_STDERR_BYTES, MAX_STDOUT_BYTES, run_with_deadline

ROOT = Path(__file__).resolve().parents[1]


def python(code):
    return [sys.executable, '-c', code]


def test_normal_unicode_output_and_independent_result_are_preserved():
    expected = {'answer': 42, 'message': '中文 🌱'}
    actual = run_with_deadline(python('import json; print(json.dumps({"answer":42,"message":"中文 🌱"}, ensure_ascii=False))'),
                               '', cwd=ROOT, timeout=5)
    assert json.loads(actual) == expected


def test_stdout_is_capped_while_draining_and_worker_is_reaped():
    code = f'import sys; sys.stdout.write("x" * {MAX_STDOUT_BYTES + 1}); sys.stdout.flush()'
    started = time.monotonic()
    with pytest.raises(ValueError, match='stdout exceeds'):
        run_with_deadline(python(code), '', cwd=ROOT, timeout=5)
    assert time.monotonic() - started < 5


def test_stdout_at_byte_limit_is_accepted():
    code = f'import sys; sys.stdout.write("x" * {MAX_STDOUT_BYTES}); sys.stdout.flush()'
    assert len(run_with_deadline(python(code), '', cwd=ROOT, timeout=5).encode()) == MAX_STDOUT_BYTES


def test_stderr_has_a_separate_finite_cap():
    code = f'import sys; sys.stderr.write("e" * {MAX_STDERR_BYTES + 1}); sys.stderr.flush()'
    with pytest.raises(ValueError, match='stderr exceeds'):
        run_with_deadline(python(code), '', cwd=ROOT, timeout=5)


@pytest.mark.parametrize('stream,limit', [('stdout', MAX_STDOUT_BYTES), ('stderr', MAX_STDERR_BYTES)])
def test_output_overflow_without_a_stdin_writer_is_still_rejected(stream, limit):
    code = f'import sys; sys.{stream}.write("x" * {limit + 1}); sys.{stream}.flush()'
    with pytest.raises(ValueError, match=f'{stream} exceeds'):
        run_with_deadline(python(code), None, cwd=ROOT, timeout=5)


def test_overflow_completed_during_exit_poll_is_never_accepted(monkeypatch):
    import scripts.bounded_execution as execution
    import threading

    # Force actual pipe completion between the loop's overflow check and exit
    # check. This timing used to return truncated stdout as a successful result.
    gate = threading.Event()
    original_drain = execution._drain
    original_popen = execution.subprocess.Popen

    def delayed_drain(*args):
        assert gate.wait(3)
        return original_drain(*args)

    def timed_process(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        original_poll = process.poll

        def poll_after_capture():
            gate.set()
            deadline = time.monotonic() + 3
            while not (process.stdout.closed and process.stderr.closed):
                if time.monotonic() > deadline:
                    raise AssertionError('The controlled output readers did not finish')
                time.sleep(0.001)
            process.wait(timeout=3)
            return original_poll()

        process.poll = poll_after_capture
        return process

    monkeypatch.setattr(execution, '_drain', delayed_drain)
    monkeypatch.setattr(execution.subprocess, 'Popen', timed_process)
    code = f'import sys; sys.stdout.write("x" * {MAX_STDOUT_BYTES + 1})'
    with pytest.raises(ValueError, match='stdout exceeds'):
        run_with_deadline(python(code), '', cwd=ROOT, timeout=5)


def test_nonzero_exit_is_preserved_with_bounded_error_text():
    with pytest.raises(ValueError, match='Expression worker failed: expected failure'):
        run_with_deadline(python('import sys; sys.stderr.write("expected failure"); sys.exit(7)'),
                          '', cwd=ROOT, timeout=5)


def test_input_encoding_failure_is_not_hidden_by_a_child_result():
    with pytest.raises(ValueError, match='input could not be encoded or written'):
        run_with_deadline(python('import sys; sys.stdin.read(); print("incorrect result")'),
                          '\ud800', cwd=ROOT, timeout=5)


def test_worker_utf8_overrides_an_inherited_ascii_stream_setting(monkeypatch):
    monkeypatch.setenv('PYTHONIOENCODING', 'ascii')
    expected = '中文 🌱'
    actual = run_with_deadline(python('import sys; print(sys.stdin.read())'), expected, cwd=ROOT, timeout=5)
    assert actual == expected + '\n'


def test_wall_clock_cutoff_includes_a_blocked_stdin_writer_and_next_call_recovers():
    payload = 'x' * (1024 * 1024)
    started = time.monotonic()
    with pytest.raises(TimeoutError, match='deadline; no result accepted'):
        run_with_deadline(python('import time; time.sleep(5)'), payload, cwd=ROOT, timeout=0.1)
    assert time.monotonic() - started < 2
    assert run_with_deadline(python('print("recovered")'), '', cwd=ROOT, timeout=5) == 'recovered\n'


def test_timeout_does_not_accept_child_output():
    with pytest.raises(TimeoutError, match='deadline; no result accepted'):
        run_with_deadline(python('import time; print("late", flush=True); time.sleep(5)'),
                          '', cwd=ROOT, timeout=0.1)


def test_late_completion_after_delayed_parent_poll_is_refused(monkeypatch):
    import scripts.bounded_execution as execution
    original_popen = execution.subprocess.Popen

    def delayed_poll_process(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        original_poll = process.poll

        def delayed_poll():
            time.sleep(0.2)
            return original_poll()

        process.poll = delayed_poll
        return process

    monkeypatch.setattr(execution.subprocess, 'Popen', delayed_poll_process)
    with pytest.raises(TimeoutError, match='deadline; no result accepted'):
        run_with_deadline(python('import time; time.sleep(0.06); print("late result")'),
                          '', cwd=ROOT, timeout=0.03)
