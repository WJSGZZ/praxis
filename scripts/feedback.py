"""Optional local run feedback. Never execute attachments, upload, or infer chat history."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import sys
import uuid
import zipfile

SCHEMA = 'praxis-feedback/1'
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 200 * 1024 * 1024
MAX_MEMBERS = 2048
TEXT_SUFFIXES = {'.json', '.jsonl', '.md', '.txt', '.log', '.py', '.csv', '.tsv', '.tex', '.toml', '.yaml', '.yml'}
SOURCES = {'unknown', 'user-provided', 'host-reported', 'runtime-metadata', 'ui-setting', 'artifact', 'assistant-recorded'}
STATUSES = {'running', 'completed', 'failed', 'timeout', 'interrupted', 'budget-exhausted', 'user-stopped', 'unknown'}
MODES = {'autonomous', 'collaboration', 'contest', 'unknown'}
EVENT_TYPES = {'stage', 'tool', 'review', 'revision', 'candidate', 'acceptance', 'intervention', 'stop', 'resume', 'message', 'failure'}
INTERVENTIONS = {'necessary-input', 'authorization', 'research-participation', 'preference-change', 'omission-correction', 'continue-reminder', 'environment-assistance', 'unknown'}
BLOCKED_PARTS = {'.git', '.venv', 'node_modules', '__pycache__'}
SOURCED_FIELDS = {
    'identity': ('plugin_version', 'plugin_source_sha256', 'provider', 'requested_model', 'reported_model', 'settings', 'host_version', 'permissions', 'routing'),
    'exposure': ('problem_source', 'contest', 'year', 'problem_id', 'prior_work', 'reference_access', 'inputs_provided', 'pretraining_exposure'),
    'cost': ('tokens', 'fees', 'calls'),
    'user_observation': ('expectation', 'actual_issue', 'location'),
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def loads(data):
    def reject(value):
        raise ValueError('Non-finite JSON value: ' + value)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            reject(value)
        return parsed
    return json.loads(data, parse_constant=reject, parse_float=finite_float, object_pairs_hook=unique)


def safe_name(name):
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
        raise ValueError('Invalid relative path')
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {'', '.', '..'} for part in name.split('/')) or ':' in name:
        raise ValueError('Unsafe relative path: ' + name)
    return name


def safe_file(root, name):
    name = safe_name(name)
    root = Path(root).absolute()
    if root.is_symlink():
        raise ValueError('Symbolic link root rejected')
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Symbolic link rejected: ' + name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path outside root: ' + name)
    if path.exists() and not path.is_file():
        raise ValueError('Expected regular file: ' + name)
    if path.exists() and path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('File too large: ' + name)
    return path


def known(value='unknown', source='unknown'):
    return {'value': value, 'source': source}


def validate_time(value, field, *, allow_unknown=False):
    if allow_unknown and value == 'unknown':
        return
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('Timezone required')
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('ISO timestamp with timezone required: ' + field) from exc
    return parsed


def validate_known(value, field):
    if not isinstance(value, dict) or set(value) != {'value', 'source'} or value['source'] not in SOURCES:
        raise ValueError('Value and actual source required: ' + field)
    if value['source'] == 'unknown' and value['value'] != 'unknown':
        raise ValueError('Unknown source must retain unknown value: ' + field)


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get('schema') != SCHEMA:
        raise ValueError('Unsupported feedback schema')
    if manifest.get('status') not in STATUSES or manifest.get('mode') not in MODES:
        raise ValueError('Invalid status or work mode')
    for field in ('run_id', 'created_utc', 'started_utc', 'ended_utc', 'goal'):
        if not isinstance(manifest.get(field), str):
            raise ValueError('Missing field: ' + field)
    validate_time(manifest['created_utc'], 'created_utc')
    started = validate_time(manifest['started_utc'], 'started_utc', allow_unknown=True)
    ended = validate_time(manifest['ended_utc'], 'ended_utc', allow_unknown=True)
    if started is not None and ended is not None and ended < started:
        raise ValueError('ended_utc must not precede started_utc')
    for field, required_names in SOURCED_FIELDS.items():
        if not isinstance(manifest.get(field), dict):
            raise ValueError('Missing field: ' + field)
        for name in required_names:
            if name not in manifest[field]:
                raise ValueError('Missing sourced field: ' + field + '.' + name)
        for name, value in manifest[field].items():
            validate_known(value, field + '.' + name)
    if not isinstance(manifest.get('environment'), dict):
        raise ValueError('Missing environment')
    for field in ('events', 'files', 'missing', 'excluded', 'redactions'):
        if not isinstance(manifest.get(field), list):
            raise ValueError('Expected list: ' + field)
    if any(not isinstance(item, str) for item in manifest['missing']):
        raise ValueError('Missing records must be readable strings')
    for event in manifest['events']:
        validate_event(event)
    names = set()
    for item in manifest['files']:
        if not isinstance(item, dict):
            raise ValueError('Invalid file entry')
        name = safe_name(item.get('path'))
        safe_name(item.get('original_path'))
        if name in names or name in {'manifest.json', 'summary.md'}:
            raise ValueError('Duplicate/reserved declared file: ' + name)
        names.add(name)
        for field in ('sha256', 'original_sha256'):
            if not isinstance(item.get(field), str) or not re.fullmatch('[0-9a-f]{64}', item[field]):
                raise ValueError('Invalid hash: ' + name)
        if type(item.get('bytes')) is not int or not 0 <= item['bytes'] <= MAX_FILE_BYTES:
            raise ValueError('Invalid file size: ' + name)
    if sum(item['bytes'] for item in manifest['files']) > MAX_TOTAL_BYTES:
        raise ValueError('Declared files exceed size limit')
    if len(names) + 2 > MAX_MEMBERS:
        raise ValueError('Too many declared files')
    return manifest


def validate_event(event):
    if not isinstance(event, dict) or event.get('type') not in EVENT_TYPES:
        raise ValueError('Invalid event type')
    for field in ('at_utc', 'phase', 'actor', 'description', 'source'):
        if not isinstance(event.get(field), str) or not event[field]:
            raise ValueError('Event field required: ' + field)
    if event['source'] not in SOURCES:
        raise ValueError('Invalid event source')
    validate_time(event['at_utc'], 'event.at_utc')
    validate_known(event.get('model'), 'event.model')
    if not isinstance(event.get('artifacts'), list):
        raise ValueError('Event artifacts must be a list')
    for name in event['artifacts']:
        safe_name(name)
    if event['type'] == 'intervention' and event.get('intervention_kind') not in INTERVENTIONS:
        raise ValueError('Intervention kind required')
    if event['type'] in {'review', 'candidate', 'acceptance', 'revision'} and (not isinstance(event.get('candidate_id'), str) or not event['candidate_id'].strip()):
        raise ValueError('Candidate identity required')


def descriptor(case):
    return safe_file(case, 'feedback/manifest.json')


def init(case, *, mode='unknown', goal='unknown', metadata=None):
    case = Path(case).resolve()
    if not case.is_dir():
        raise ValueError('Case directory does not exist')
    path = descriptor(case)
    if path.exists():
        raise FileExistsError(path)
    now = stamp()
    manifest = {
        'schema': SCHEMA, 'run_id': uuid.uuid4().hex, 'created_utc': now,
        'started_utc': now, 'ended_utc': 'unknown', 'status': 'running', 'mode': mode,
        'goal': goal,
        **{group: {name: known() for name in names} for group, names in SOURCED_FIELDS.items()},
        'environment': {'python': platform.python_version(), 'os': platform.system(), 'os_release': platform.release(), 'architecture': platform.machine(), 'source': 'runtime-metadata'},
        'events': [], 'files': [], 'missing': ['Full conversation and model/tool calls are not automatically captured.', 'Final PDF/page review not recorded.'],
        'excluded': [], 'redactions': [], 'coverage': 'partial; explicit records only',
    }
    if metadata:
        allowed = {'identity', 'exposure', 'cost', 'user_observation', 'started_utc', 'ended_utc', 'status', 'missing'}
        if set(metadata) - allowed:
            raise ValueError('Unsupported metadata fields')
        for key, value in metadata.items():
            if key in {'identity', 'exposure', 'cost', 'user_observation'}:
                manifest[key].update(value)
            else:
                manifest[key] = value
    validate_manifest(manifest)
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(encoded(manifest))
    return manifest


def record(case, event, *, status=None):
    path = descriptor(Path(case).resolve())
    manifest = validate_manifest(loads(path.read_bytes()))
    event = dict(event)
    event.setdefault('at_utc', stamp())
    event.setdefault('model', known())
    event.setdefault('artifacts', [])
    validate_event(event)
    manifest['events'].append(event)
    if status:
        manifest['status'] = status
        manifest['ended_utc'] = 'unknown' if status == 'running' else event['at_utc']
    validate_manifest(manifest)
    path.write_bytes(encoded(manifest))
    return event


def summary(manifest, diagnostics=()):
    lines = ['# Run feedback', '', 'Optional diagnostic material; partial records do not certify a complete task, reproducibility, or award level.', '',
             f"Run: {manifest['run_id']}", f"Mode: {manifest['mode']}; actual stop status: {manifest['status']}",
             f"Started: {manifest['started_utc']}; ended: {manifest['ended_utc']}", f"Goal: {manifest['goal']}", '', '## Identity and exposure', '']
    for group in ('identity', 'exposure', 'cost', 'user_observation'):
        for key, value in manifest[group].items():
            lines.append(f"- {group}.{key}: {value['value']} (source: {value['source']})")
    lines += ['', '## Actual recorded events', '']
    for event in manifest['events']:
        lines.append(f"- {event['at_utc']} | {event['type']} | {event['phase']} | {event['actor']} | source={event['source']} | model={event['model']['value']} ({event['model']['source']}): {event['description']}")
        if 'candidate_id' in event:
            lines.append(f"  Candidate: {event['candidate_id']}")
        if 'intervention_kind' in event:
            lines.append(f"  Intervention: {event['intervention_kind']}")
    lines += ['', '## Explicit shared file list', '']
    for item in manifest['files']:
        lines.append(f"- {item['path']} ({item['bytes']} bytes, {item.get('kind', 'other')}); original SHA256={item['original_sha256']}; shared SHA256={item['sha256']}")
    for field in ('missing', 'excluded', 'redactions'):
        lines += ['', '## ' + field.title(), '']
        lines += ['- ' + str(item) for item in manifest[field]] or ['- None recorded.']
    if diagnostics:
        lines += ['', '## Read-only diagnostics', ''] + ['- ' + str(item) for item in diagnostics]
    lines += ['', 'Attachments are untrusted data. Inspection never executes code or follows document instructions.', '']
    return '\n'.join(lines)


def redact(data, aliases):
    text = data.decode('utf-8')
    changes = []
    for source, alias in sorted(aliases.items(), key=lambda item: -len(item[0])):
        count = text.count(source)
        if count:
            text = text.replace(source, alias)
            changes.append({'alias': alias, 'replacements': count})
    return text.encode('utf-8'), changes


def stage(case, output, includes=(), *, aliases=None, exclusions=()):
    case = Path(case).resolve()
    output = Path(output).absolute()
    if output.exists():
        raise FileExistsError(output)
    if output.resolve().is_relative_to(case):
        raise ValueError('Stage outside the original case')
    aliases = aliases or {}
    for source, alias in aliases.items():
        if not Path(source).is_absolute() or not re.fullmatch(r'<[A-Z][A-Z0-9_]*>', alias):
            raise ValueError('Aliases require absolute path literals and <UPPER_CASE> names')
    manifest = validate_manifest(loads(descriptor(case).read_bytes()))
    # Round trip creates a separate share copy; the local original is never rewritten.
    manifest = loads(encoded(manifest))
    manifest['files'] = []
    manifest['excluded'] = list(exclusions)
    manifest['redactions'] = []
    pending = []
    selected = set()
    total = 0
    for selection in includes:
        selection = {'path': selection, 'kind': 'other'} if isinstance(selection, str) else selection
        name = safe_name(selection['path'])
        if name in selected:
            raise ValueError('Duplicate selected file: ' + name)
        selected.add(name)
        parts = PurePosixPath(name).parts
        if any(part in BLOCKED_PARTS for part in parts) or Path(name).name.startswith('.env') or Path(name).suffix in {'.key', '.pem'} or Path(name).name in {'id_rsa', 'id_ed25519'}:
            raise ValueError('Sensitive/cache file rejected: ' + name)
        source = safe_file(case, name)
        if not source.exists():
            manifest['missing'].append('Selected file missing: ' + name)
            continue
        raw = source.read_bytes()
        shared = raw
        changes = []
        if source.suffix.lower() in TEXT_SUFFIXES:
            try:
                shared, changes = redact(raw, aliases)
            except UnicodeDecodeError:
                if aliases:
                    raise ValueError('Cannot redact selected non-UTF8 text: ' + name)
        total += len(shared)
        if len(shared) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError('Shared size limit exceeded')
        target = 'files/' + name
        manifest['files'].append({'path': target, 'original_path': name, 'kind': selection.get('kind', 'other'), 'bytes': len(shared), 'original_sha256': digest(raw), 'sha256': digest(shared)})
        manifest['redactions'].extend({'path': target, **change} for change in changes)
        pending.append((target, shared))
    # Path aliases apply to metadata and event descriptions too, including embedded JSON paths.
    data, changes = redact(encoded(manifest), aliases)
    manifest = loads(data)
    manifest['redactions'].extend({'path': 'manifest.json', **change} for change in changes)
    validate_manifest(manifest)
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in pending:
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (output / 'summary.md').write_text(summary(manifest), encoding='utf-8')
        manifest['summary_sha256'] = digest((output / 'summary.md').read_bytes())
        (output / 'manifest.json').write_bytes(encoded(manifest))
        report = inspect(output)
    except Exception:
        shutil.rmtree(output)
        raise
    return {'stage': str(output), 'manifest_sha256': digest((output / 'manifest.json').read_bytes()), 'inspection': report}


class Reader:
    """Only declared bytes are read. ZIP files are never extracted."""
    def __init__(self, source):
        self.source = Path(source)
        self.archive = None
        self.local_descriptor = False
        if self.source.is_dir():
            self.root = self.source
            self.manifest_name = 'manifest.json'
            if not (self.root / self.manifest_name).exists():
                self.manifest_name = 'feedback/manifest.json'
                self.local_descriptor = True
        else:
            self.archive = zipfile.ZipFile(self.source)
            self.members = {}
            total = 0
            for item in self.archive.infolist():
                name = safe_name(item.filename)
                if name in self.members:
                    raise ValueError('Duplicate ZIP member: ' + name)
                mode = item.external_attr >> 16
                if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in {0, stat.S_IFREG}):
                    raise ValueError('Non-regular ZIP member: ' + name)
                if item.file_size > MAX_FILE_BYTES or item.file_size > max(item.compress_size, 1) * 200:
                    raise ValueError('Abnormal ZIP expansion: ' + name)
                total += item.file_size
                if total > MAX_TOTAL_BYTES or len(self.members) >= MAX_MEMBERS:
                    raise ValueError('ZIP size/member limit exceeded')
                self.members[name] = item
            self.manifest_name = 'manifest.json'

    def read(self, name):
        name = safe_name(name)
        if self.archive:
            if name not in self.members:
                raise FileNotFoundError(name)
            data = self.archive.read(self.members[name])
        else:
            data = safe_file(self.root, name).read_bytes()
        if len(data) > MAX_FILE_BYTES:
            raise ValueError('File too large: ' + name)
        return data

    def close(self):
        if self.archive:
            self.archive.close()


def inspect(source):
    reader = Reader(source)
    try:
        try:
            manifest_data = reader.read(reader.manifest_name)
        except FileNotFoundError:
            if reader.archive:
                raise ValueError('Feedback ZIP manifest is missing')
            return {'schema': SCHEMA, 'status': 'unknown', 'mode': 'unknown',
                    'coverage': 'legacy directory; no feedback descriptor', 'verified_files': [],
                    'missing': ['Feedback descriptor missing; init can adapt this directory without moving its original files.',
                                'Process, identity, exposure, final PDF and actual stop status not established.'],
                    'complete_task_certified': False, 'reproducibility_certified': False}
        manifest = validate_manifest(loads(manifest_data))
        verified, missing = [], list(manifest['missing'])
        for item in manifest['files']:
            try:
                data = reader.read(item['path'])
            except FileNotFoundError:
                missing.append('Declared file missing: ' + item['path'])
                continue
            if len(data) != item['bytes'] or digest(data) != item['sha256']:
                raise ValueError('Hash/size mismatch: ' + item['path'])
            verified.append(item['path'])
        if 'summary_sha256' in manifest:
            try:
                data = reader.read('summary.md')
            except FileNotFoundError:
                missing.append('Declared summary missing: summary.md')
            else:
                if digest(data) != manifest['summary_sha256']:
                    raise ValueError('Hash mismatch: summary.md')
        else:
            missing.append('Share summary not recorded; local/legacy descriptor only.')
        if not any(item['path'].lower().endswith('.pdf') for item in manifest['files']):
            missing.append('No PDF selected; final page inspection is not established.')
        if not manifest['events']:
            missing.append('No process events recorded.')
        if manifest['ended_utc'] == 'unknown':
            missing.append('Actual end time unknown.')
        unknown = [group + '.' + key for group in ('identity', 'exposure', 'cost', 'user_observation') for key, item in manifest[group].items() if item['source'] == 'unknown']
        allowed = {'manifest.json', 'summary.md', *[item['path'] for item in manifest['files']]}
        ignored = sorted(set(reader.members) - allowed) if reader.archive else []
        return {'schema': SCHEMA, 'run_id': manifest['run_id'], 'status': manifest['status'], 'mode': manifest['mode'], 'coverage': 'partial; explicit records only',
                'goal': manifest['goal'], 'started_utc': manifest['started_utc'], 'ended_utc': manifest['ended_utc'],
                'identity': manifest['identity'], 'exposure': manifest['exposure'], 'cost': manifest['cost'], 'user_observation': manifest['user_observation'],
                'environment': manifest['environment'], 'events': manifest['events'],
                'manifest_sha256': digest(manifest_data), 'verified_files': verified, 'missing': missing, 'unknown_fields': unknown,
                'event_count': len(manifest['events']), 'interventions': [event for event in manifest['events'] if event['type'] == 'intervention'],
                'excluded': manifest['excluded'], 'redactions': manifest['redactions'], 'unread_members': ignored,
                'complete_task_certified': False, 'reproducibility_certified': False}
    finally:
        reader.close()


def pack(source, output, *, confirm_manifest_sha256):
    source = Path(source).resolve()
    output = Path(output).absolute()
    if output.exists():
        raise FileExistsError(output)
    if output.resolve().is_relative_to(source):
        raise ValueError('ZIP must be outside stage directory')
    report = inspect(source)
    if report['manifest_sha256'] != confirm_manifest_sha256:
        raise ValueError('Explicit confirmation must match the reviewed manifest SHA256')
    if any(value.startswith('Declared ') for value in report['missing']):
        raise ValueError('Cannot pack missing declared material')
    manifest = loads((source / 'manifest.json').read_bytes())
    names = ['manifest.json', 'summary.md'] + [item['path'] for item in manifest['files']]
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name in names:
                # Store bytes read through the same traversal/symlink boundary.
                archive.writestr(name, safe_file(source, name).read_bytes())
        archived = inspect(output)
        if archived != report:
            raise ValueError('Directory/ZIP inspection mismatch')
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {'zip': str(output), 'zip_sha256': digest(output.read_bytes()), 'inspection': archived}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('init'); p.add_argument('--case', type=Path, required=True); p.add_argument('--mode', choices=sorted(MODES), default='unknown'); p.add_argument('--goal', default='unknown'); p.add_argument('--metadata', type=Path)
    p = sub.add_parser('record'); p.add_argument('--case', type=Path, required=True); p.add_argument('--event', type=Path, required=True); p.add_argument('--status', choices=sorted(STATUSES))
    p = sub.add_parser('stage'); p.add_argument('--case', type=Path, required=True); p.add_argument('--output', type=Path, required=True); p.add_argument('--include', action='append', default=[]); p.add_argument('--alias', action='append', default=[]); p.add_argument('--exclude', action='append', default=[], help='A readable exclusion and reason; the file is never read')
    p = sub.add_parser('pack'); p.add_argument('--source', type=Path, required=True); p.add_argument('--output', type=Path, required=True); p.add_argument('--confirm-manifest-sha256', required=True)
    p = sub.add_parser('inspect'); p.add_argument('source', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            result = init(args.case, mode=args.mode, goal=args.goal, metadata=loads(args.metadata.read_bytes()) if args.metadata else None)
        elif args.command == 'record':
            result = record(args.case, loads(args.event.read_bytes()), status=args.status)
        elif args.command == 'stage':
            aliases = {}
            for item in args.alias:
                if '=' not in item:
                    raise ValueError('Alias must be PATH=<NAME>')
                key, value = item.rsplit('=', 1)
                if key in aliases:
                    raise ValueError('Duplicate alias')
                aliases[key] = value
            result = stage(args.case, args.output, args.include, aliases=aliases, exclusions=args.exclude)
        elif args.command == 'pack':
            result = pack(args.source, args.output, confirm_manifest_sha256=args.confirm_manifest_sha256)
        else:
            result = inspect(args.source)
        print(encoded(result).decode(), end='')
        return 0
    except (ValueError, OSError, zipfile.BadZipFile, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
