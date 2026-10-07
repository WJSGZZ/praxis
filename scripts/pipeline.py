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
from importlib.metadata import version

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
    return {str(p.relative_to(case)): digest(p) for p in paths}


def dependency_snapshot():
    paths = [BUNDLE / 'pyproject.toml', BUNDLE / 'uv.lock', Path(__file__).resolve()]
    paths += list((BUNDLE / 'modeling').rglob('*.py')) + list((BUNDLE / 'scripts').glob('*.py'))
    return {str(p.relative_to(BUNDLE)): digest(p) for p in paths if p.is_file()}



def environment_snapshot():
    packages = ['numpy', 'pandas', 'scipy', 'scikit-learn', 'networkx', 'SALib', 'pymcdm', 'pypdf']
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'executable': sys.executable, 'packages': {name: version(name) for name in packages}}


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
    show = commands.add_parser('status')
    show.add_argument('--case', type=Path, required=True)
    args = parser.parse_args()
    PROJECT = args.workspace.resolve()
    try:
        if args.action == 'init':
            result = init_case(args.case_root or PROJECT / 'cases',args.name,args.problem,args.data,args.phase,args.encoding)
        elif args.action == 'run':
            result = run_case(args.case,args.model,args.validator,args.timeout)
        else:
            result = status(args.case)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if result.get('status') == 'failed':
            raise SystemExit(1)
    except (ValueError, FileExistsError, FileNotFoundError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
