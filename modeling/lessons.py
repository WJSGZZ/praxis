"""A failure-and-strategy memory kept in the user's own project (JSON lines), so the next problem starts from what was learned.

A lesson stores how a problem was recognised, which routes were tried and why they failed, what worked, how it was verified and the
principle that may carry over. It stores no answers and no private data beyond what the user puts in; the file never leaves the
project unless the user moves it."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

OPTIONAL = ('failure_pattern', 'detected_by', 'signal')      # the faulty way of working, how it was found, and what to watch for next time
REQUIRED = ('problem', 'structure', 'recognized', 'routes_tried', 'what_failed', 'what_worked', 'verified_by', 'principle')
LEVEL = ('candidate', 'observed once', 'seen repeatedly', 'derived', 'checked on a held-out problem')
SOURCES = ('legacy_unspecified', 'external_proposal', 'task_observation', 'mathematical_derivation')


def _entries(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def _signature(record: dict) -> str:
    payload = {k: v for k, v in record.items() if k not in ('id', 'date', 'status', 'supersedes')}
    payload.setdefault('source_kind', 'legacy_unspecified')
    payload['tags'] = sorted(set(payload.get('tags', [])))
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)


def active(path: Path) -> list[dict]:
    """Current view only. Raw lesson identities remain available through load()."""
    entries = _entries(path)
    records = [r for r in entries if 'event' not in r]
    by_id = {}
    for rec in records:
        identity = rec.get('id')
        if not isinstance(identity, str) or not identity or identity in by_id:
            raise ValueError('Lesson IDs must be unique nonempty strings')
        if rec.get('status', 'active') not in ('active', 'retired'):
            raise ValueError('Unknown lesson status')
        if rec.get('evidence', 'observed once') not in LEVEL:
            raise ValueError('Unknown lesson evidence')
        if rec.get('source_kind', 'legacy_unspecified') not in SOURCES:
            raise ValueError('Unknown lesson source_kind')
        if rec.get('source_kind') == 'external_proposal' and rec.get('evidence') != 'candidate':
            raise ValueError('An external proposal must remain candidate evidence')
        by_id[identity] = rec
    replaced = set(); edges = {}
    for rec in records:
        targets = rec.get('supersedes', [])
        if isinstance(targets, str): targets = [targets]
        if not isinstance(targets, list) or any(not isinstance(t, str) for t in targets):
            raise ValueError('supersedes must contain lesson IDs')
        if len(set(targets)) != len(targets): raise ValueError('Duplicate supersedes target')
        if any(t not in by_id or t == rec['id'] for t in targets):
            raise ValueError('supersedes target is missing or self-referential')
        edges[rec['id']] = targets; replaced.update(targets)
    visiting = set(); visited = set()
    def visit(identity):
        if identity in visiting: raise ValueError('Cyclic lesson replacement')
        if identity in visited: return
        visiting.add(identity)
        for target in edges[identity]: visit(target)
        visiting.remove(identity); visited.add(identity)
    for identity in edges: visit(identity)
    retired = {r['id'] for r in records if r.get('status') == 'retired'}
    for event in entries:
        if 'event' not in event: continue
        if event['event'] != 'retire' or event.get('target') not in by_id or not str(event.get('reason', '')).strip():
            raise ValueError('Invalid lesson lifecycle event')
        retired.add(event['target'])
    # Legacy duplicate rows are aliases, so retiring their canonical identity
    # cannot resurrect an identical later row. Explicit replacements are new identities.
    canonical = {}; aliases = {}; representatives = []
    for rec in records:
        signature = _signature(rec)
        if rec.get('supersedes') or signature not in canonical:
            canonical[signature] = rec['id']; representatives.append(rec)
        aliases[rec['id']] = canonical[signature]
    excluded = {aliases[identity] for identity in replaced | retired}
    return [rec for rec in representatives if rec['id'] not in excluded]


def add_lesson(path: Path, lesson: dict) -> dict:
    """Append a lesson. Every required field must say something; 'principle' must be stated as a rule that could transfer."""
    path = Path(path)
    current = active(path)  # Validate the entire lifecycle before any append.
    if 'event' in lesson:
        if lesson['event'] != 'retire' or lesson.get('target') not in {r['id'] for r in current} or not str(lesson.get('reason', '')).strip():
            raise ValueError('retire requires a currently active target and a reason')
        record = {'event': 'retire', 'target': lesson['target'], 'reason': lesson['reason'], 'date': lesson.get('date') or date.today().isoformat()}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as handle: handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
        return record
    missing = [k for k in REQUIRED if not str(lesson.get(k, '')).strip() and lesson.get(k) != []]
    if missing:
        raise ValueError('Lesson is missing: ' + ', '.join(missing))
    level = lesson.get('evidence', 'observed once')
    if level not in LEVEL:
        raise ValueError(f'evidence must be one of {LEVEL}')
    source = lesson.get('source_kind', 'legacy_unspecified')
    if source not in SOURCES: raise ValueError('Unknown lesson source_kind')
    if source == 'external_proposal' and level != 'candidate':
        raise ValueError('An external proposal must remain candidate evidence')
    if lesson.get('status', 'active') != 'active': raise ValueError('Use a retire event for retirement')
    record = {**lesson, 'evidence': level, 'source_kind': source, 'date': lesson.get('date') or date.today().isoformat(), 'tags': sorted(set(lesson.get('tags', [])))}
    targets = record.get('supersedes', [])
    if isinstance(targets, str): targets = [targets]
    if not isinstance(targets, list) or any(not isinstance(t, str) for t in targets) or len(set(targets)) != len(targets) or not set(targets) <= {r['id'] for r in current}:
        raise ValueError('supersedes requires distinct currently active lesson IDs')
    if targets: record['supersedes'] = targets
    for rec in current:
        if not targets and _signature(rec) == _signature(record): return rec
    existing = load(path)
    if not targets and any(_signature(rec) == _signature(record) for rec in existing):
        raise ValueError('An identical inactive lesson cannot be revived; provide revised evidence or content')
    used = {r['id'] for r in existing}; number = len(existing) + 1
    while f'L{number:04d}' in used: number += 1
    record['id'] = f'L{number:04d}'
    encoded = json.dumps(record, ensure_ascii=False, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as handle:
        handle.write(encoded + '\n')
    return record


def load(path: Path) -> list[dict]:
    """Historical lesson rows, including superseded/retired ones; no rewriting."""
    return [r for r in _entries(path) if 'event' not in r]


def _tokens(text: str) -> set[str]:
    """Latin words (two letters or more) plus Chinese character bigrams, so a query without spaces still finds lessons."""
    text = text.lower()
    words = {w for w in re.findall(r'[a-z0-9_]+', text) if len(w) > 1}
    for run in re.findall(r'[\u4e00-\u9fff]+', text):
        words |= {run[i:i + 2] for i in range(len(run) - 1)} if len(run) > 1 else {run}
    return words


def search_lessons(path: Path, query: str = '', *, tags: list[str] | None = None, limit: int = 5) -> list[dict]:
    """Lessons ranked by token overlap with the query (any field, English words or Chinese bigrams) and by tags found in the query or given.
    Returns the best few, strongest evidence first on ties."""
    words = _tokens(query.replace(',', ' '))
    want = {t.lower() for t in (tags or [])}
    lowered = query.lower()
    ranked = []
    if type(limit) is not int or limit < 0: raise ValueError('limit must be a nonnegative integer')
    for rec in active(path):
        text = ' '.join(str(v) for k, v in rec.items() if k not in ('id', 'date')).lower()
        have = _tokens(text)
        rec_tags = {t.lower() for t in rec.get('tags', [])}
        tag_hits = len(want & rec_tags) + sum(1 for t in rec_tags if t in lowered)
        score = len(words & have) + 3 * tag_hits
        if score:
            ranked.append((score, LEVEL.index(rec.get('evidence', 'observed once')), rec))
    ranked.sort(key=lambda r: (-r[0], -r[1]))
    return [r[2] for r in ranked[:limit]]


def patterns(path: Path) -> dict:
    """Structures and principles that recur: counts by structure tag and the lessons seen more than once."""
    records = active(path)
    by_structure: dict[str, int] = {}
    for rec in records:
        by_structure[rec['structure']] = by_structure.get(rec['structure'], 0) + 1
    repeated = {k: v for k, v in by_structure.items() if v > 1}
    return dict(lessons=len(records), by_structure=by_structure, repeated_structures=repeated)
