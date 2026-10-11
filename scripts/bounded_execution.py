"""Subprocess deadlines for expression tools; no shell or arbitrary client commands."""
import subprocess


def run_with_deadline(command, payload, *, cwd, timeout):
    """Kill and reap a timed-out worker; preserve failures rather than a fallback."""
    try:
        result = subprocess.run(command, input=payload, cwd=cwd, text=True,
                                capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f'Expression worker exceeded its {timeout:g}-second deadline; no result accepted') from exc
    if result.returncode:
        raise ValueError(f'Expression worker failed: {result.stderr[-4000:]}')
    if len(result.stdout) > 4 * 1024 * 1024:
        raise ValueError('Expression worker output exceeds the 4 MiB delivery limit')
    return result.stdout
