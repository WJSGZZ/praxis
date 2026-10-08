"""Local contribution events; summaries are not transcripts or proof of understanding.

Used by pipeline contribution-add/contribution-summary. No chat capture or remote I/O.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

FIELDS = {'source', 'proposer', 'matter', 'task', 'executor', 'kind', 'status',
          'impact', 'evidence', 'mode', 'origin', 'supersedes'}
REQUIRED = FIELDS - {'supersedes'}
KINDS = {'suggestion', 'challenge', 'decision', 'implementation', 'understanding',
         'independent-verification', 'review', 'continuation'}
MODES = {'autonomous', 'collaboration', 'contest'}


def validate(event):
    if not isinstance(event, dict) or set(event) - FIELDS or REQUIRED - set(event):
        raise ValueError('Contribution needs the documented fields only')
    for field in REQUIRED - {'source', 'evidence'}:
        if not isinstance(event[field], str) or not event[field].strip():
            raise ValueError(f'{field} needs nonempty text')
    if event['kind'] not in KINDS or event['mode'] not in MODES:
        raise ValueError('Unknown contribution kind or mode')
    if event['status'] not in {'proposed', 'accepted', 'rejected', 'checked', 'implemented', 'unresolved'}:
        raise ValueError('Unknown contribution status')
    if event['origin'] not in {'contemporaneous', 'retrospective'}:
        raise ValueError('origin must distinguish contemporaneous and retrospective records')
    source = event['source']
    if not isinstance(source, dict) or set(source) - {'message_ref', 'excerpt', 'source_time'}:
        raise ValueError('source needs a message_ref or original excerpt; time is optional')
    if not any(isinstance(source.get(k), str) and source[k].strip() for k in ('message_ref', 'excerpt')):
        raise ValueError('Missing source message or excerpt')
    if any(not isinstance(v, str) or not v.strip() for v in source.values()):
        raise ValueError('Source fields must be nonempty text')
    if not isinstance(event['evidence'], list) or any(not isinstance(p, str) or not p.strip() for p in event['evidence']):
        raise ValueError('evidence must be a list of workspace-relative file paths')
    if event['status'] in {'checked', 'implemented'} and not event['evidence']:
        raise ValueError('Checked or implemented events need evidence')
    if 'supersedes' in event and (not isinstance(event['supersedes'], str) or not event['supersedes'].strip()):
        raise ValueError('supersedes must name an existing event')


def append_event(root, event):
    """Append without rewriting history; corrections explicitly supersede old events."""
    validate(event)
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Contribution workspace must already exist')
    path = root / 'planning/contributions.jsonl'
    if not path.resolve().is_relative_to(root):
        raise ValueError('Contribution log must remain in the workspace')
    records = read_events(root)
    if event.get('supersedes') and event['supersedes'] not in {r['id'] for r in records}:
        raise ValueError('Unknown superseded event')
    hashes = {}
    for relative in event['evidence']:
        file = (root / relative).resolve()
        if Path(relative).is_absolute() or not file.is_relative_to(root) or not file.is_file():
            raise ValueError('Evidence must be an existing file inside the workspace')
        hashes[relative] = hashlib.sha256(file.read_bytes()).hexdigest()
    record = {**event, 'id': uuid.uuid4().hex, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
              'evidence_sha256': hashes}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
    return record


def read_events(root):
    root = Path(root).resolve()
    path = root / 'planning/contributions.jsonl'
    if not path.resolve().is_relative_to(root):
        raise ValueError('Contribution log must remain in the workspace')
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def summarize(root):
    records = read_events(root)
    replaced = {r['supersedes'] for r in records if r.get('supersedes')}
    current = [r for r in records if r['id'] not in replaced]
    return {'events': current, 'historical_events': len(records),
            'scope': 'Recorded contributions only; not a transcript, contribution percentage, or certification of human verification.'}
