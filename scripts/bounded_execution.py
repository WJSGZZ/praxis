"""Subprocess deadlines and bounded output capture for expression tools.

This is not a process-tree, CPU, memory, filesystem, or network sandbox.
"""
import codecs
import os
import subprocess
import threading
import time


MAX_STDOUT_BYTES = 4 * 1024 * 1024
MAX_STDERR_BYTES = 64 * 1024
_READ_CHUNK_BYTES = 16 * 1024


def _drain(pipe, limit, state, overflow):
    """Read to EOF while retaining at most limit bytes."""
    kept = bytearray()
    try:
        while True:
            chunk = pipe.read(_READ_CHUNK_BYTES)
            if not chunk:
                break
            remaining = limit - len(kept)
            if remaining > 0:
                kept.extend(chunk[:remaining])
            if len(chunk) > remaining:
                state['over_limit'] = True
                overflow.set()
        state['data'] = bytes(kept)
    except BaseException as error:
        state['error'] = error
        overflow.set()
    finally:
        state['done'].set()
        try:
            pipe.close()
        except OSError:
            pass


def _write_input(pipe, payload, encoding, state):
    try:
        encoder = codecs.getincrementalencoder(encoding)()
        for start in range(0, len(payload), _READ_CHUNK_BYTES):
            chunk = payload[start:start + _READ_CHUNK_BYTES]
            if os.linesep != '\n':
                chunk = chunk.replace('\n', os.linesep)
            encoded = encoder.encode(chunk)
            if encoded:
                pipe.write(encoded)
                pipe.flush()
        final = encoder.encode('', final=True)
        if final:
            pipe.write(final)
            pipe.flush()
    except BrokenPipeError:
        # Like communicate(), an early child exit may make remaining input moot.
        pass
    except BaseException as error:
        state['error'] = error
    finally:
        try:
            pipe.close()
        except OSError:
            pass
        state['done'].set()


def _stop_and_reap(process):
    if process.poll() is None:
        process.kill()
    process.wait()


def _join_bounded(threads):
    # A descendant can inherit a worker's output handles and keep a reader open
    # after the direct child exits. Do not let that defeat the caller's deadline.
    for thread in threads:
        thread.join(timeout=0.25)


def run_with_deadline(command, payload, *, cwd, timeout):
    """Run a fixed argv worker with a wall-clock deadline and bounded pipe capture.

    The child inherits the normal environment and permissions. Only the direct
    child is killed on timeout or output overflow; this is not a sandbox.
    """
    if payload is not None and not isinstance(payload, str):
        raise TypeError('text input payload must be a string or None')
    encoding = 'utf-8'
    environment = os.environ.copy()
    # These are Python expression workers with a UTF-8 text/JSON protocol,
    # independent of the parent's locale and inherited stream overrides.
    environment['PYTHONIOENCODING'] = 'utf-8'
    process = subprocess.Popen(command, cwd=cwd, text=False,
                               stdin=subprocess.PIPE if payload is not None else None, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, bufsize=0, env=environment)
    deadline = time.monotonic() + timeout
    overflow = threading.Event()
    stdout_state = {'data': b'', 'error': None, 'over_limit': False, 'done': threading.Event()}
    stderr_state = {'data': b'', 'error': None, 'over_limit': False, 'done': threading.Event()}
    input_state = {'error': None, 'done': threading.Event()}
    threads = [
        threading.Thread(target=_drain, args=(process.stdout, MAX_STDOUT_BYTES, stdout_state, overflow), daemon=True),
        threading.Thread(target=_drain, args=(process.stderr, MAX_STDERR_BYTES, stderr_state, overflow), daemon=True),
    ]
    writer = (threading.Thread(target=_write_input, args=(process.stdin, payload, encoding, input_state), daemon=True)
              if payload is not None else None)
    if writer is None:
        input_state['done'].set()
    try:
        for thread in threads:
            thread.start()
        if writer is not None:
            writer.start()
        while True:
            if overflow.is_set():
                _stop_and_reap(process)
                _join_bounded(threads + ([writer] if writer is not None else []))
                if stdout_state['error'] or stderr_state['error']:
                    error = stdout_state['error'] or stderr_state['error']
                    raise ValueError(f'Expression worker output could not be read: {error}') from error
                if stdout_state['over_limit']:
                    raise ValueError(f'Expression worker stdout exceeds the {MAX_STDOUT_BYTES}-byte capture limit')
                raise ValueError(f'Expression worker stderr exceeds the {MAX_STDERR_BYTES}-byte capture limit')

            if stdout_state['error'] or stderr_state['error']:
                _stop_and_reap(process)
                _join_bounded(threads + ([writer] if writer is not None else []))
                error = stdout_state['error'] or stderr_state['error']
                raise ValueError(f'Expression worker output could not be read: {error}') from error

            returncode = process.poll()
            if returncode is not None and stdout_state['done'].is_set() and stderr_state['done'].is_set():
                # Readers may finish between the first overflow check and poll.
                # Their completed state is now stable: never accept truncation.
                if overflow.is_set():
                    continue
                break

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _stop_and_reap(process)
                _join_bounded(threads + ([writer] if writer is not None else []))
                raise TimeoutError(f'Expression worker exceeded its {timeout:g}-second deadline; no result accepted')
            overflow.wait(min(0.01, remaining))

        if writer is not None:
            _join_bounded([writer])
        if not input_state['done'].is_set():
            raise TimeoutError(f'Expression worker input exceeded its {timeout:g}-second deadline; no result accepted')
        if time.monotonic() >= deadline:
            raise TimeoutError(f'Expression worker exceeded its {timeout:g}-second deadline; no result accepted')
        if input_state['error'] is not None:
            error = input_state['error']
            raise ValueError(f'Expression worker input could not be encoded or written: {error}') from error
        if returncode:
            stderr = stderr_state['data'].decode(encoding)
            raise ValueError(f'Expression worker failed: {stderr[-4000:]}')

        # The worker channel is UTF-8; retain text mode's universal newlines.
        stdout = stdout_state['data'].decode(encoding)
        if time.monotonic() >= deadline:
            raise TimeoutError(f'Expression worker exceeded its {timeout:g}-second deadline; no result accepted')
        return stdout.replace('\r\n', '\n').replace('\r', '\n')
    except BaseException:
        if process.poll() is None:
            _stop_and_reap(process)
        _join_bounded(threads + ([writer] if writer is not None else []))
        raise
