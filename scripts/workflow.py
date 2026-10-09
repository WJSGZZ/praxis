"""Explicit, resumable coordination over pipeline evidence, not scientific certification."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

BUNDLE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUNDLE))
from scripts import pipeline
from modeling import lessons
from pypdf import PdfReader

BEGIN = '<!-- PRAXIS WORKFLOW STATE BEGIN -->'
END = '<!-- PRAXIS WORKFLOW STATE END -->'
NOTE = 'Declared evidence and delivery connections; not mathematical, human or award certification.'


def now():
    return datetime.now(timezone.utc)


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def positive_int(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(f'{name} must be a finite positive integer, not bool')
    return value


def safe_path(value, root):
    """Reject traversal and symlink components, including links remaining within root."""
    root = Path(root).resolve()
    path = Path(value)
    if '..' in path.parts:
        raise ValueError('Path traversal is forbidden')
    path = path if path.is_absolute() else root / path
    if not path.is_relative_to(root):
        raise ValueError('Path must remain inside the selected workspace/case')
    cursor = root
    for part in path.relative_to(root).parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError('Symlink paths are forbidden')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Path must remain inside the selected workspace/case')
    return path


def case_path(value):
    case = safe_path(value, pipeline.PROJECT)
    if not (case / 'case.json').is_file():
        raise ValueError('Use an existing pipeline case')
    # Pipeline snapshots and output receipts must never follow links introduced elsewhere.
    if any(p.is_symlink() for p in case.rglob('*')):
        raise ValueError('Symlinks are forbidden inside a workflow case')
    pipeline.read_json(case / 'case.json')
    return case


def instant(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError('timestamp needs timezone')
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        raise ValueError('Invalid workflow timestamp') from exc


def validate_state(state):
    if not isinstance(state, dict) or type(state.get('schema')) is not int or state.get('schema') != 1:
        raise ValueError('Invalid workflow state schema')
    for key in ['budget_seconds', 'max_attempts', 'per_run_timeout']:
        positive_int(state.get(key), key)
    if state['per_run_timeout'] > 3600:
        raise ValueError('per_run_timeout cannot exceed pipeline limit 3600')
    if type(state.get('attempts')) is not int or not 0 <= state['attempts'] <= state['max_attempts']:
        raise ValueError('Invalid workflow attempt count')
    start, deadline = instant(state.get('started_utc')), instant(state.get('deadline_utc'))
    if (deadline - start).total_seconds() != state['budget_seconds']:
        raise ValueError('Workflow deadline does not match budget')
    if not isinstance(state.get('goal'), str) or not state['goal'].strip():
        raise ValueError('Workflow goal is required')
    if not isinstance(state.get('attempt_history'), list) or not isinstance(state.get('lesson_retrieval'), dict):
        raise ValueError('Invalid workflow history/retrieval')
    if len(state['attempt_history']) != state['attempts']:
        raise ValueError('Workflow attempt history does not match counter')
    for key in ['initial_source', 'initial_dependencies']:
        if not isinstance(state.get(key), dict):
            raise ValueError('Missing initial source/dependency identity')
    return state


def read_state(case):
    path = safe_path('planning/progress.md', case)
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('Workflow state missing, duplicate or damaged')
    before, tail = text.split(BEGIN, 1)
    body, after = tail.split(END, 1)
    body = body.strip()
    if not body.startswith('```json\n') or not body.endswith('\n```'):
        raise ValueError('Workflow state must be one marked JSON block')
    state = json.loads(body[8:-4], parse_constant=pipeline.reject_nonfinite,
                       parse_float=pipeline.finite_json_float)
    return validate_state(state), before, after


def write_state(case, state, *, initial=False):
    path = safe_path('planning/progress.md', case)
    if initial:
        text = path.read_text(encoding='utf-8') if path.exists() else ''
        if BEGIN in text or END in text:
            raise ValueError('Refuse to overwrite an existing or damaged workflow block')
        before, after = text + ('\n' if text and not text.endswith('\n') else ''), '\n'
    else:
        _, before, after = read_state(case)
    validate_state(state)
    block = BEGIN + '\n```json\n' + json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False).replace('<', '\\u003c') + '\n```\n' + END
    temporary = path.with_name('.progress-' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(before + block + after, encoding='utf-8')
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def init(case, goal, query='', lessons_path=None, budget_seconds=3600, max_attempts=3, per_run_timeout=120):
    case = case_path(case)
    for key, value in [('budget_seconds', budget_seconds), ('max_attempts', max_attempts), ('per_run_timeout', per_run_timeout)]:
        positive_int(value, key)
    if per_run_timeout > 3600:
        raise ValueError('per_run_timeout cannot exceed pipeline limit 3600')
    if not isinstance(goal, str) or not goal.strip() or not isinstance(query, str):
        raise ValueError('Provide a nonempty goal and a string query')
    progress = safe_path('planning/progress.md', case)
    if progress.exists() and (BEGIN in progress.read_text() or END in progress.read_text()):
        raise ValueError('Refuse to overwrite an existing or damaged workflow block')
    start = now()
    source = pipeline.source_snapshot(case)
    knowledge = safe_path(lessons_path or 'planning/lessons.jsonl', pipeline.PROJECT)
    # Strict finite JSON validation before the existing lesson search consumes the file.
    if knowledge.exists():
        for line in knowledge.read_text(encoding='utf-8').splitlines():
            if line.strip():
                json.loads(line, parse_constant=pipeline.reject_nonfinite, parse_float=pipeline.finite_json_float)
    retrieved = lessons.search_lessons(knowledge, query, limit=3)
    state = {'schema': 1, 'goal': goal, 'started_utc': start.isoformat(),
             'deadline_utc': (start + timedelta(seconds=budget_seconds)).isoformat(),
             'budget_seconds': budget_seconds, 'max_attempts': max_attempts,
             'per_run_timeout': per_run_timeout, 'attempts': 0, 'attempt_history': [],
             'initial_source': source, 'initial_source_sha256': canonical_hash(source),
             'initial_dependencies': pipeline.dependency_snapshot(),
             'lesson_retrieval': {'path': str(knowledge), 'query': query, 'retrieved_utc': start.isoformat(),
                                  'index_sha256': pipeline.digest(knowledge) if knowledge.is_file() else None,
                                  'hits': [{'id': hit['id'], 'sha256': canonical_hash(hit)} for hit in retrieved]},
             'accepted': None, 'report': None, 'metering': {'model': 'unknown', 'tokens': 'not measured'}, 'note': NOTE}
    write_state(case, state, initial=True)
    return {'case': str(case), 'state': state, 'note': NOTE}


def latest_evidence(case):
    status = pipeline.status(case)
    return status, status['runs'][-1] if status['runs'] else None


def unreceipted_attempt(state, latest):
    """Do not conceal a launch error/interrupted controller behind an older success."""
    history = state['attempt_history']
    if not history or history[-1].get('status') not in ['error', 'started']:
        return False
    if not latest:
        return True
    receipt = pipeline.read_json(Path(latest['run']) / 'receipt.json')
    if not receipt.get('started_utc'):
        return True
    return instant(receipt['started_utc']) < instant(history[-1]['started_utc'])


def linked(case):
    try:
        evidence = pipeline.evidence_index(case)
    except (ValueError, FileNotFoundError, KeyError, TypeError):
        return False
    return evidence['status'] == 'evidence-linked'


def review_identity(case, path, latest):
    path = safe_path(path, case)
    review = pipeline.read_json(path)
    receipt = Path(latest['run']) / 'receipt.json'
    if (not isinstance(review, dict) or review.get('verdict') != 'pass'
            or any(not isinstance(review.get(k), str) or not review[k].strip() for k in ['actor', 'scope'])
            or review.get('run_id') != receipt.parent.name or review.get('receipt_sha256') != pipeline.digest(receipt)):
        raise ValueError('Review must pass with actor, scope and exact current run/receipt identity')
    quality = review.get('quality_decision')
    if (not isinstance(quality, dict) or quality.get('decision') not in ['continue', 'stop']
            or not isinstance(quality.get('reason'), str) or not quality['reason'].strip()
            or (quality['decision'] == 'continue' and (not isinstance(quality.get('next_action'), str) or not quality['next_action'].strip()))):
        raise ValueError('Review needs quality_decision continue/stop, reason and next_action for continue')
    return {'run_id': receipt.parent.name, 'receipt_sha256': pipeline.digest(receipt),
            'quality_decision': quality, 'review_path': str(path.relative_to(case)), 'review_sha256': pipeline.digest(path)}


def accepted_valid(case, state, latest):
    accepted = state.get('accepted')
    if not isinstance(accepted, dict) or not latest or not latest['usable_automatic_evidence']:
        return False
    try:
        return accepted == review_identity(case, accepted['review_path'], latest)
    except (ValueError, OSError, KeyError, TypeError):
        return False


def pdf_review(case, path):
    sidecar = safe_path(str(path.relative_to(case)) + '.page-review.json', case)
    review = pipeline.read_json(sidecar)
    count = len(PdfReader(path).pages)
    if (not isinstance(review, dict) or not isinstance(review.get('actor'), str) or not review['actor'].strip()
            or review.get('pdf_sha256') != pipeline.digest(path) or not isinstance(review.get('pages'), list)
            or any(type(n) is not int for n in review['pages']) or review['pages'] != list(range(1, count + 1))):
        raise ValueError('PDF needs explicit actor/hash/all actual pages in <report>.page-review.json')
    return {'page_review_path': str(sidecar.relative_to(case)), 'page_review_sha256': pipeline.digest(sidecar), 'pages': count}


def report_identity(case, path, accepted):
    path = safe_path(path, case)
    if not path.is_file() or path.suffix.lower() not in ['.md', '.pdf']:
        raise ValueError('Use an existing case Markdown or PDF report')
    result = {'report_path': str(path.relative_to(case)), 'report_sha256': pipeline.digest(path),
              'run_id': accepted['run_id'], 'receipt_sha256': accepted['receipt_sha256']}
    if path.suffix.lower() == '.pdf':
        result.update(pdf_review(case, path))
    return result


def next(case):
    case = case_path(case)
    state, _, _ = read_state(case)
    remaining = (instant(state['deadline_utc']) - now()).total_seconds()
    result = {'case': str(case), 'remaining_seconds': max(0, remaining), 'attempts': state['attempts'], 'note': NOTE}
    if remaining <= 0:
        return {**result, 'action': 'closeout', 'reason': 'budget expired; computation cannot start'}
    try:
        pipeline.code_path(case, 'code/model.py')
        pipeline.code_path(case, 'code/validate.py')
    except ValueError:
        return {**result, 'action': 'prepare'}
    status, latest = latest_evidence(case)
    result['expected_source_sha256'] = canonical_hash(pipeline.source_snapshot(case))
    if unreceipted_attempt(state, latest):
        return {**result, 'action': 'closeout' if state['attempts'] >= state['max_attempts'] else 'repair',
                'reason': 'latest workflow attempt failed or was interrupted before a current receipt',
                'previous_accepted': state.get('accepted')}
    if not latest:
        if state['attempts'] >= state['max_attempts']:
            return {**result, 'action': 'closeout', 'reason': 'maximum attempts reached'}
        return {**result, 'action': 'run' if not status['raw_input_changes'] else 'repair'}
    result['latest_run_id'] = Path(latest['run']).name
    if not latest['usable_automatic_evidence']:
        return {**result, 'action': 'closeout' if state['attempts'] >= state['max_attempts'] else 'repair', 'reason': 'latest run failed or stale; attempts exhausted' if state['attempts'] >= state['max_attempts'] else 'latest run failed or stale', 'previous_accepted': state.get('accepted')}
    if not linked(case):
        return {**result, 'action': 'coverage'}
    if not accepted_valid(case, state, latest):
        return {**result, 'action': 'review'}
    quality = state['accepted']['quality_decision']
    if quality['decision'] == 'continue':
        return {**result, 'action': 'improve', 'next_action': quality['next_action'], 'reason': quality['reason']}
    try:
        stored = state.get('report')
        valid_report = isinstance(stored, dict) and stored == report_identity(case, stored['report_path'], state['accepted'])
    except (OSError, ValueError, KeyError, TypeError):
        valid_report = False
    return {**result, 'action': 'delivered' if valid_report else 'report'}


def run(case, reviewed_source_sha256):
    case = case_path(case)
    state, _, _ = read_state(case)
    expected = canonical_hash(pipeline.source_snapshot(case))
    if reviewed_source_sha256 != expected:
        raise ValueError('reviewed_source_sha256 must match the current canonical source snapshot')
    remaining = (instant(state['deadline_utc']) - now()).total_seconds()
    if remaining < 2 * state['per_run_timeout']:
        raise ValueError('Insufficient remaining budget: reserve both pipeline stage timeouts')
    if state['attempts'] >= state['max_attempts']:
        raise ValueError('Maximum attempts reached')
    pipeline.code_path(case, 'code/model.py')
    pipeline.code_path(case, 'code/validate.py')
    config = pipeline.read_json(case / 'case.json')
    if not config.get('intake_complete') or pipeline.input_changes(case, config):
        raise ValueError('Intake incomplete or raw inputs changed')
    attempt = {'started_utc': now().isoformat(), 'reviewed_source_sha256': expected, 'status': 'started'}
    state['attempts'] += 1
    state['attempt_history'].append(attempt)
    write_state(case, state)
    started = time.monotonic()
    try:
        receipt = pipeline.run_case(case, timeout=state['per_run_timeout'])
        attempt.update({'status': receipt['status'], 'run_id': Path(receipt['run']).name,
                        'receipt_sha256': pipeline.digest(Path(receipt['run']) / 'receipt.json')})
        return receipt
    except Exception as exc:
        attempt.update({'status': 'error', 'error': f'{type(exc).__name__}: {exc}'})
        raise
    finally:
        attempt.update({'ended_utc': now().isoformat(), 'wall_seconds': time.monotonic() - started})
        write_state(case, state)


def accept(case, review_path):
    case = case_path(case)
    state, _, _ = read_state(case)
    _, latest = latest_evidence(case)
    if unreceipted_attempt(state, latest) or not latest or not latest['usable_automatic_evidence'] or not linked(case):
        raise ValueError('Accept requires current latest valid evidence-linked run')
    accepted = review_identity(case, review_path, latest)
    state['accepted'] = accepted
    state['report'] = None
    write_state(case, state)
    return {'accepted': accepted, 'note': NOTE}


def report(case, report_path):
    case = case_path(case)
    state, _, _ = read_state(case)
    _, latest = latest_evidence(case)
    if unreceipted_attempt(state, latest) or not accepted_valid(case, state, latest) or not linked(case):
        raise ValueError('Report requires a current accepted review and evidence-linked run')
    identity = report_identity(case, report_path, state['accepted'])
    state['report'] = identity
    write_state(case, state)
    return {'report': identity, 'note': NOTE}


def main():
    class JSONParser(argparse.ArgumentParser):
        def error(self, message):
            print(json.dumps({'error': message}), file=sys.stderr)
            raise SystemExit(2)
    parser = JSONParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('init'); p.add_argument('--case', required=True); p.add_argument('--goal', required=True)
    p.add_argument('--query', default=''); p.add_argument('--lessons-path'); p.add_argument('--budget-seconds', type=int, required=True)
    p.add_argument('--max-attempts', type=int, default=3); p.add_argument('--per-run-timeout', type=int, default=120)
    for name in ['next', 'run', 'accept', 'report']:
        p = sub.add_parser(name); p.add_argument('--case', required=True)
        if name == 'run': p.add_argument('--reviewed-source-sha256', required=True)
        if name == 'accept': p.add_argument('--review-path', required=True)
        if name == 'report': p.add_argument('--report-path', required=True)
    args = parser.parse_args(); pipeline.PROJECT = args.workspace.resolve()
    try:
        values = vars(args); command = values.pop('command'); values.pop('workspace')
        result = globals()[command](**values)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        if command == 'run' and result.get('status') == 'failed':
            raise SystemExit(1)
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as exc:
        print(json.dumps({'error': f'{type(exc).__name__}: {exc}'}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
