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
LEVEL = ('observed once', 'seen repeatedly', 'derived', 'checked on a held-out problem')


def add_lesson(path: Path, lesson: dict) -> dict:
    """Append a lesson. Every required field must say something; 'principle' must be stated as a rule that could transfer."""
    missing = [k for k in REQUIRED if not str(lesson.get(k, '')).strip() and lesson.get(k) != []]
    if missing:
        raise ValueError('Lesson is missing: ' + ', '.join(missing))
    level = lesson.get('evidence', 'observed once')
    if level not in LEVEL:
        raise ValueError(f'evidence must be one of {LEVEL}')
    record = {**lesson, 'evidence': level, 'date': lesson.get('date') or date.today().isoformat(), 'tags': sorted(set(lesson.get('tags', [])))}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load(path)
    record['id'] = f'L{len(existing) + 1:04d}'
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + '\n')
    return record


def load(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


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
    for rec in load(path):
        text = ' '.join(str(v) for k, v in rec.items() if k not in ('id', 'date')).lower()
        have = _tokens(text)
        rec_tags = {t.lower() for t in rec.get('tags', [])}
        tag_hits = len(want & rec_tags) + sum(1 for t in rec_tags if t in lowered)
        score = len(words & have) + 3 * tag_hits
        if score:
            ranked.append((score, LEVEL.index(rec['evidence']), rec))
    ranked.sort(key=lambda r: (-r[0], -r[1]))
    return [r[2] for r in ranked[:limit]]


def patterns(path: Path) -> dict:
    """Structures and principles that recur: counts by structure tag and the lessons seen more than once."""
    records = load(path)
    by_structure: dict[str, int] = {}
    for rec in records:
        by_structure[rec['structure']] = by_structure.get(rec['structure'], 0) + 1
    repeated = {k: v for k, v in by_structure.items() if v > 1}
    return dict(lessons=len(records), by_structure=by_structure, repeated_structures=repeated)
