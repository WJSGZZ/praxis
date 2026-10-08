"""Workspace-aware automation: immutable intake, witnessed runs, stale evidence checks.

This does not select a model or run downloaded commands. Codex writes/reviews a
case's Python model and independent validator before explicitly calling `run`.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import platform
from importlib.metadata import PackageNotFoundError, version

BUNDLE = Path(__file__).resolve().parents[1]
PROJECT = Path.cwd().resolve()
sys.path.insert(0, str(BUNDLE))
from scripts.audit_data import audit
import pandas as pd
from pypdf import PdfReader


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def reject_nonfinite(value):
    raise ValueError(f'Non-finite JSON number: {value}')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_nonfinite)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def under_project(path):
    path = Path(path)
    if not path.is_absolute():                                       # a relative path always means: relative to the workspace
        path = PROJECT / path
    path = path.resolve()
    if not path.is_relative_to(PROJECT):
        raise ValueError('Case paths must remain inside the selected workspace')
    return path


def init_case(case_root, name, problem, data=(), phase='preparation', encoding='utf-8'):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) > 50:
        raise ValueError('Use a short lowercase hyphenated case name')
    if phase not in ['preparation', 'contest']:
        raise ValueError('phase must be preparation or contest')
    problem = problem.resolve()
    data = [p.resolve() for p in data]
    if not problem.is_file() or problem.suffix.lower() not in ['.pdf', '.txt', '.md']:
        raise ValueError('Provide a local PDF, TXT or Markdown problem')
    if any(not p.is_file() for p in data):
        raise ValueError('All data inputs must be local files')
    if len({p.name for p in data}) != len(data):
        raise ValueError('Duplicate data filenames; rename explicitly before intake')
    # Validate text extraction before creating a case; never run file instructions.
    if problem.suffix.lower() == '.pdf':
        with problem.open('rb') as stream:
            doc = PdfReader(stream)
            if doc.is_encrypted:
                raise ValueError('Encrypted problem PDF must be opened by its owner first')
            text = '\n\n'.join(page.extract_text() or '' for page in doc.pages)
        visual_review = True  # Text extraction can miss diagrams and equations.
    else:
        text = problem.read_text(encoding=encoding)
        visual_review = False
    case = under_project(case_root) / name
    case.mkdir(parents=True, exist_ok=False)  # Never merge or overwrite an old case.
    for directory in ['raw/problem', 'raw/data', 'planning', 'code', 'audits', 'runs']:
        (case / directory).mkdir(parents=True, exist_ok=True)
    inputs = []
    for source, directory, role in [(problem, 'raw/problem', 'problem')] + [(p, 'raw/data', 'data') for p in data]:
        target = case / directory / source.name
        shutil.copyfile(source, target)
        target.chmod(0o444)
        inputs.append({'role': role, 'original_path': str(source), 'path': str(target.relative_to(case)),
                       'sha256': digest(target), 'bytes': target.stat().st_size})
    (case / 'planning/problem-extracted.txt').write_text(text, encoding='utf-8')
    config = {'schema': 1, 'name': name, 'phase': phase, 'created_utc': stamp(), 'inputs': inputs,
              'problem_visual_review_required': visual_review,
              'problem_text_extracted': bool(text.strip()), 'intake_complete': False,
              'human_verification': 'not recorded; automatic checks do not imply human approval'}
    save(case / 'case.json', config)
    # Unsupported or large files remain intact with an explicit audit deferral.
    for entry in inputs:
        if entry['role'] != 'data':
            continue
        path = case / entry['path']
        report = {'input': entry['path'], 'sha256': entry['sha256'], 'sheets': {}, 'deferred': None}
        try:
            if entry['bytes'] > 50_000_000:
                report['deferred'] = 'File >50 MB: choose a streaming or targeted audit before modeling'
            elif path.suffix.lower() == '.csv':
                report['sheets']['csv'] = audit(path, encoding=encoding)
            elif path.suffix.lower() == '.xlsx':
                with pd.ExcelFile(path) as book:
                    sheets = list(book.sheet_names)
                for sheet in sheets:
                    report['sheets'][sheet] = audit(path, sheet=sheet)
            else:
                report['deferred'] = 'Format requires a task-specific read-only audit'
        except Exception as exc:
            report['deferred'] = f'{type(exc).__name__}: {exc}; input preserved, inspect before use'
        save(case / 'audits' / (path.name + '.json'), report)
    shutil.copyfile(BUNDLE / 'references/tasks-template.md', case / 'planning/tasks.md')
    config['intake_complete'] = True
    save(case / 'case.json', config)
    return {'case': str(case), 'intake_complete': True, 'inputs': len(inputs),
            'next': 'Read original problem, fill tasks and assumptions, write model.py and validate.py'}


def input_changes(case, config):
    changes = []
    for entry in config['inputs']:
        path = (case / entry['path']).resolve()
        if not path.is_relative_to(case) or not path.is_file() or digest(path) != entry['sha256']:
            changes.append(entry['path'])
    return changes


def code_path(case, name):
    path = (case / name).resolve()
    if not path.is_relative_to((case / 'code').resolve()) or path.suffix != '.py' or not path.is_file():
        raise ValueError('Run only explicitly reviewed .py files inside this case/code directory')
    return path



def source_snapshot(case):
    paths = [p for p in (case / 'code').rglob('*') if p.is_file()
             and '__pycache__' not in p.parts and p.suffix not in ['.pyc', '.pyo']]
    paths += [case / 'planning/tasks.md']
    if (case / 'planning/requirements.json').is_file():
        paths.append(case / 'planning/requirements.json')
    return {str(p.relative_to(case)): digest(p) for p in paths}


def dependency_snapshot():
    paths = [BUNDLE / 'pyproject.toml', BUNDLE / 'uv.lock', Path(__file__).resolve()]
    paths += list((BUNDLE / 'modeling').rglob('*.py')) + list((BUNDLE / 'scripts').glob('*.py'))
    return {str(p.relative_to(BUNDLE)): digest(p) for p in paths if p.is_file()}



def environment_snapshot():
    import tomllib
    declared = tomllib.loads((BUNDLE / 'pyproject.toml').read_text())['project']['dependencies']       # every declared dependency, so none is forgotten
    packages = [re.split(r'[<>=!~\[ ]', spec, maxsplit=1)[0] for spec in declared]
    versions = {}
    for name in packages:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = 'not installed'
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'executable': sys.executable, 'packages': versions}


def run_case(case, model='code/model.py', validator='code/validate.py', timeout=120):
    case = under_project(case)
    config = read_json(case / 'case.json')
    if not config.get('intake_complete') or input_changes(case, config):
        raise ValueError('Intake incomplete or raw inputs changed; do not use stale materials')
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise ValueError('timeout must be integer seconds from 1 to 3600')
    model_path, validator_path = code_path(case, model), code_path(case, validator)
    code_hashes = source_snapshot(case)
    dependency_hashes = dependency_snapshot()
    attempt = case / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
    attempt.mkdir(parents=True, exist_ok=False)
    out = attempt / 'output'
    out.mkdir()
    receipt = {'schema': 1, 'started_utc': stamp(), 'phase': config['phase'],
               'inputs': config['inputs'], 'code': code_hashes, 'dependencies': dependency_hashes,
               'environment': environment_snapshot(), 'steps': [],
               'status': 'running', 'automatic_checks_passed': False,
               'human_verification': config['human_verification']}
    for prefix, root, snapshot in [('source-snapshot', case, code_hashes),
                                  ('dependency-snapshot', BUNDLE, dependency_hashes)]:
        for relative in snapshot:
            target = attempt / prefix / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(BUNDLE) + os.pathsep + env.get('PYTHONPATH', '')
    commands = [('model', [sys.executable, str(model_path), '--output', str(out)]),
                ('validation', [sys.executable, str(validator_path), '--results', str(out / 'results.json'),
                                '--output', str(attempt / 'checks.json')])]
    save(attempt / 'receipt.json', receipt)
    try:
        for stage, command in commands:
            step = {'stage': stage, 'argv': command, 'started_utc': stamp()}
            receipt['steps'].append(step)
            save(attempt / 'receipt.json', receipt)
            with (attempt / (stage + '.stdout.log')).open('w') as stdout, (attempt / (stage + '.stderr.log')).open('w') as stderr:
                result = subprocess.run(command, cwd=case, env=env, stdout=stdout, stderr=stderr, timeout=timeout)
            step.update({'ended_utc': stamp(), 'exit_code': result.returncode})
            if result.returncode != 0:
                raise ValueError(f'{stage} exited {result.returncode}; inspect retained logs')
            if stage == 'model':
                # Ensure well-formed structured results, not just a successful exit.
                results = read_json(out / 'results.json')
                if not isinstance(results, dict) or not results:
                    raise ValueError('Model results must be a nonempty JSON object')
        checks = read_json(attempt / 'checks.json')
        if not isinstance(checks, list) or not checks:
            raise ValueError('Validator must produce a nonempty check list')
        if any(not isinstance(c, dict) or c.get('passed') is not True or not isinstance(c.get('name'), str)
               or not c['name'].strip() or not isinstance(c.get('evidence'), str) or not c['evidence'].strip()
               for c in checks):
            raise ValueError('Checks must individually pass with names and concrete evidence')
        if input_changes(case, config) or source_snapshot(case) != code_hashes or dependency_snapshot() != dependency_hashes:
            raise ValueError('Inputs or reviewed code changed during execution')
        receipt['outputs'] = {}
        for path in (list(out.rglob('*')) + [attempt / 'checks.json']
                     + list((attempt / 'source-snapshot').rglob('*'))
                     + list((attempt / 'dependency-snapshot').rglob('*'))):
            if path.is_symlink():
                raise ValueError('Outputs must not be symlinks')
            if path.is_file():
                receipt['outputs'][str(path.relative_to(attempt))] = digest(path)
        receipt.update({'status': 'automatic-checks-passed', 'automatic_checks_passed': True})
    except Exception as exc:
        receipt.update({'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})
    receipt['ended_utc'] = stamp()
    save(attempt / 'receipt.json', receipt)
    return {'run': str(attempt), **receipt}


def status(case):
    case = under_project(case)
    config = read_json(case / 'case.json')
    changes = input_changes(case, config)
    runs = sorted((case / 'runs').glob('*/receipt.json'))
    report = {'case': str(case), 'raw_input_changes': changes, 'runs': [],
              'paper_ready': False, 'human_verification': config['human_verification']}
    for path in runs:
        receipt = read_json(path)
        stale = list(changes)
        for relative, checksum in receipt.get('code', {}).items():
            source = (case / relative).resolve()
            if not source.is_relative_to(case) or not source.is_file() or digest(source) != checksum:
                stale.append(relative)
        current_sources = source_snapshot(case)
        if current_sources != receipt.get('code', {}):
            stale.append('case source/configuration file set changed')
        for relative, checksum in receipt.get('dependencies', {}).items():
            dependency = (BUNDLE / relative).resolve()
            if not dependency.is_relative_to(BUNDLE) or not dependency.is_file() or digest(dependency) != checksum:
                stale.append('project dependency: ' + relative)
        if receipt.get('environment') != environment_snapshot():
            stale.append('runtime environment changed')
        for relative, checksum in receipt.get('outputs', {}).items():
            output = (path.parent / relative).resolve()
            if not output.is_relative_to(path.parent) or not output.is_file() or digest(output) != checksum:
                stale.append(relative)
        report['runs'].append({'run': str(path.parent), 'status': receipt['status'],
                               'stale': sorted(set(stale)),
                               'usable_automatic_evidence': receipt.get('automatic_checks_passed', False) and not stale})
    report['note'] = 'Automatic evidence is not proof of model suitability, user verification or paper completeness'
    return report


def result_pointer(value, pointer):
    """Resolve a non-root RFC 6901 pointer; never evaluate expressions."""
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('result_pointer must start with / and name a result field')
    for escaped in pointer[1:].split('/'):
        if re.search(r'~(?![01])', escaped):
            raise ValueError('Invalid JSON pointer escape')
        token = escaped.replace('~1', '/').replace('~0', '~')
        try:
            if isinstance(value, dict):
                value = value[token]
            elif isinstance(value, list) and re.fullmatch(r'0|[1-9][0-9]*', token):
                value = value[int(token)]
            else:
                raise KeyError(token)
        except (KeyError, IndexError):
            raise ValueError(f'Result field does not exist: {pointer}') from None
    if value is None or value == '' or value == [] or value == {}:
        raise ValueError(f'Result field is empty: {pointer}')
    return value


CLAIM_STRENGTH = {'computed': 1, 'checked': 2, 'independent': 3}


def claim_problems(requirements, claims, lookup, results):
    """Compare each claim's declared strength with the evidence it links; list uncovered requirements and overclaims.

    computed: its result pointer resolves in results.json. checked: at least one linked check exists and passed.
    independent: at least one linked check passed and is marked `"independent": true` in checks.json (its author asserts a different method)."""
    problems = []
    ids = {r['id'] for r in requirements}
    covered = set()
    seen = set()
    for claim in claims:
        cid = claim.get('id') if isinstance(claim, dict) else None
        if not isinstance(cid, str) or not cid.strip() or cid in seen or claim.get('requirement') not in ids or claim.get('strength') not in CLAIM_STRENGTH \
                or not isinstance(claim.get('text'), str) or not claim['text'].strip():
            problems.append(f'claim {cid!r}: needs a unique id, text, a requirement id from the list and strength computed|checked|independent')
            continue
        seen.add(cid)
        want = CLAIM_STRENGTH[claim['strength']]
        have = 0
        pointer = claim.get('result_pointer')
        if pointer:
            try:
                result_pointer(results, pointer)
                have = 1
            except ValueError:
                problems.append(f'claim {cid}: result_pointer {pointer!r} does not resolve')
        linked = [lookup[n] for n in claim.get('checks', []) if n in lookup]
        missing = [n for n in claim.get('checks', []) if n not in lookup]
        if missing:
            problems.append(f'claim {cid}: unknown check(s) {missing}')
        if any(c['passed'] for c in linked):
            have = max(have, 2)
        if any(c['passed'] and c.get('independent') is True for c in linked):
            have = 3
        if have < want:
            name = {v: k for k, v in CLAIM_STRENGTH.items()}.get(have, 'no evidence')
            problems.append(f'claim {cid} is declared {claim["strength"]} but its evidence supports only {name}')
        else:
            covered.add(claim['requirement'])
    for r in requirements:
        if claims and r['id'] not in covered:
            problems.append(f'requirement {r["id"]} has no claim whose evidence supports it')
    return problems


def evidence_index(case):
    """Link recorded requirements to the latest run, without certifying completeness."""
    case = under_project(case)
    manifest = case / 'planning/requirements.json'
    definition = read_json(manifest)
    tasks = definition.get('requirements') if isinstance(definition, dict) else None
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('Record a nonempty requirements list before building evidence')
    ids = set()
    for task in tasks:
        if not isinstance(task, dict) or any(not isinstance(task.get(k), str) or not task[k].strip()
                for k in ['id', 'question', 'unit', 'result_pointer']):
            raise ValueError('Each requirement needs id, question, unit and result_pointer strings')
        names = task.get('checks')
        if not isinstance(names, list) or not names or any(not isinstance(n,str) or not n.strip() for n in names) or len(set(names)) != len(names):
            raise ValueError('Each requirement needs unique named independent checks')
        if task['id'] in ids:
            raise ValueError('Requirement ids must be unique')
        ids.add(task['id'])
    report = status(case)
    if not report['runs']:
        raise ValueError('Run the model and independent validator before building evidence')
    latest = report['runs'][-1]
    if not latest['usable_automatic_evidence']:
        raise ValueError('Latest run failed or is stale; resolve it rather than falling back silently')
    run = Path(latest['run'])
    results = read_json(run / 'output/results.json')
    checks = read_json(run / 'checks.json')
    names = [check['name'] for check in checks]
    if len(set(names)) != len(names):
        raise ValueError('Check names must be unique for unambiguous evidence links')
    lookup = {check['name']: check for check in checks}
    entries = []
    for task in tasks:
        entry = dict(task)
        errors = []
        try:
            entry['value'] = result_pointer(results, task['result_pointer'])
        except ValueError as exc:
            errors.append(str(exc))
        missing = [name for name in task['checks'] if name not in lookup]
        if missing:
            errors.append('Missing independent checks: ' + ', '.join(missing))
        entry['check_evidence'] = [lookup[name] for name in task['checks'] if name in lookup]
        entry['linked'] = not errors
        entry['errors'] = errors
        entries.append(entry)
    claims = definition.get('claims', [])
    claim_issues = claim_problems(tasks, claims, lookup, results) if claims else []
    complete = all(entry['linked'] for entry in entries) and not claim_issues
    return {'status': 'evidence-linked' if complete else 'evidence-incomplete', 'claim_problems': claim_issues, 'claims_recorded': len(claims),
            'run': str(run), 'requirements_sha256': digest(manifest),
            'run_receipt_sha256': digest(run / 'receipt.json'),
            'covered': sum(entry['linked'] for entry in entries), 'recorded_requirements': len(entries),
            'entries': entries, 'paper_ready': False,
            'note': 'Links cover recorded requirements only. Review task completeness, units, check independence and claim strength; links do not certify scientific validity.'}


def main():
    global PROJECT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd(),
                        help='Project receiving cases; defaults to current directory, never the skill install path')
    commands = parser.add_subparsers(dest='action', required=True)
    init = commands.add_parser('init')
    init.add_argument('--name', required=True)
    init.add_argument('--problem', type=Path, required=True)
    init.add_argument('--data', type=Path, action='append', default=[])
    init.add_argument('--phase', choices=['preparation','contest'], default='preparation')
    init.add_argument('--encoding', default='utf-8')
    init.add_argument('--case-root', type=Path, default=None)
    run = commands.add_parser('run')
    run.add_argument('--case', type=Path, required=True)
    run.add_argument('--model', default='code/model.py')
    run.add_argument('--validator', default='code/validate.py')
    run.add_argument('--timeout', type=int, default=120)
    run.add_argument('--full-output', action='store_true', help='print the whole receipt instead of a summary')
    show = commands.add_parser('status')
    show.add_argument('--case', type=Path, required=True)
    evidence = commands.add_parser('evidence')
    evidence.add_argument('--case', type=Path, required=True)
    contribution = commands.add_parser('contribution-add')
    contribution.add_argument('--case', type=Path, required=True)
    contribution.add_argument('--event', type=Path, required=True, help='Local JSON event; never a fabricated transcript')
    contribution_summary = commands.add_parser('contribution-summary')
    contribution_summary.add_argument('--case', type=Path, required=True)
    args = parser.parse_args()
    PROJECT = args.workspace.resolve()
    try:
        if args.action == 'init':
            result = init_case(args.case_root or PROJECT / 'cases',args.name,args.problem,args.data,args.phase,args.encoding)
        elif args.action == 'run':
            result = run_case(args.case,args.model,args.validator,args.timeout)
        elif args.action == 'evidence':
            result = evidence_index(args.case)
        elif args.action == 'contribution-add':
            from scripts.contributions import append_event
            result = append_event(under_project(args.case), read_json(args.event))
        elif args.action == 'contribution-summary':
            from scripts.contributions import summarize
            result = summarize(under_project(args.case))
        else:
            result = status(args.case)
        if args.action == 'run' and not args.full_output:
            # The full receipt (every dependency hash) is on disk in the run directory; print only what a person needs to see.
            keys = ('run', 'status', 'started_utc', 'ended_utc', 'checks_passed', 'checks_total')
            result = {**{k: result[k] for k in keys if k in result}, 'receipt': str(Path(result['run']) / 'receipt.json'), 'steps': [{k: s.get(k) for k in ('stage', 'exit_code')} for s in result.get('steps', [])], 'outputs': sorted(result.get('outputs', {}))}
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if result.get('status') in ['failed', 'evidence-incomplete']:
            raise SystemExit(1)
    except (ValueError, FileExistsError, FileNotFoundError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
