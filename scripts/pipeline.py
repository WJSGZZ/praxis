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
from scripts import run_trace
from scripts.audit_data import audit
from modeling.schema_contracts import check_model_contract, reasoned, unique_object_pairs
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


def finite_json_float(value):
    import math
    number = float(value)
    if not math.isfinite(number):
        reject_nonfinite(value)
    return number


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_nonfinite,
                      parse_float=finite_json_float, object_pairs_hook=unique_object_pairs)


def read_case_config(case):
    """Read the known intake format; an absent legacy marker still means v1.

    The original writer has always emitted integer schema 1. Older readers also
    accepted its absence, so retain that compatibility without rewriting files.
    Any explicitly supplied marker must be the supported integer, never bool.
    """
    config = read_json(case / 'case.json')
    schema = config.get('schema', 1) if isinstance(config, dict) else None
    if type(schema) is not int or schema not in (1, 2):
        raise ValueError('Unsupported case schema; expected integer 1 or 2 or a missing legacy marker')
    return config


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def under_project(path):
    path = Path(path)
    if not path.is_absolute():                                       # a relative path always means: relative to the workspace
        path = PROJECT / path
    path = path.resolve()
    if not path.is_relative_to(PROJECT):
        raise ValueError('Case paths must remain inside the selected workspace')
    return path


def init_case(case_root, name, problem, data=(), phase='preparation', encoding='utf-8', schema=2):
    if type(schema) is not int or schema not in (1, 2):
        raise ValueError('schema must be integer 1 or 2')
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
            from scripts.pdf_text import extract_pages
            text = '\n\n'.join(page['text'] for page in extract_pages(problem))
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
    config = {'schema': schema, 'name': name, 'phase': phase, 'created_utc': stamp(), 'inputs': inputs,
              'problem_visual_review_required': visual_review,
              'problem_text_extracted': bool(text.strip()), 'intake_complete': False,
              'human_verification': 'not recorded; automatic checks do not imply human approval'}
    if schema == 2:
        # Later edits to the extracted question must be declared (problem_text_corrections).
        config['problem_extracted_sha256'] = digest(case / 'planning/problem-extracted.txt')
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
    if read_case_config(case).get('schema', 1) == 2:
        for relative in ('planning/model-contract.json', 'planning/problem-extracted.txt'):
            if (case / relative).is_file():
                paths.append(case / relative)
    return {str(p.relative_to(case)): digest(p) for p in paths}


def dependency_snapshot():
    paths = [BUNDLE / 'pyproject.toml', BUNDLE / 'uv.lock', Path(__file__).resolve()]
    paths += list((BUNDLE / 'modeling').rglob('*.py')) + list((BUNDLE / 'scripts').glob('*.py'))
    return {str(p.relative_to(BUNDLE)): digest(p) for p in paths if p.is_file()}



def environment_snapshot():
    import tomllib
    declared = tomllib.loads((BUNDLE / 'pyproject.toml').read_text(encoding='utf-8'))['project']['dependencies']       # every declared dependency, so none is forgotten
    packages = [re.split(r'[<>=!~\[ ]', spec, maxsplit=1)[0] for spec in declared]
    versions = {}
    for name in packages:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = 'not installed'
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'executable': sys.executable, 'packages': versions}


def clean_bundle_commit():
    """Return the owning clean checkout's commit; installed copies keep snapshots."""
    try:
        root = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=BUNDLE,
                              capture_output=True, text=True, timeout=10, check=True)
        if Path(root.stdout.strip()).resolve() != BUNDLE.resolve():
            return None
        status = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=BUNDLE,
                                capture_output=True, text=True, timeout=10, check=True)
        if status.stdout.strip():
            return None
        head = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=BUNDLE,
                              capture_output=True, text=True, timeout=10, check=True)
        return head.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def model_contract_problems(case, warnings=None):
    """Return every schema-2 contract problem without executing anything; [] means it may run."""
    contract_path = case / 'planning/model-contract.json'
    if not contract_path.is_file():
        return ['schema 2 requires planning/model-contract.json before running']
    try:
        contract = read_json(contract_path)
    except (ValueError, UnicodeDecodeError) as exc:
        return [f'planning/model-contract.json is not valid finite JSON: {exc}']
    return check_model_contract(contract, warnings)


def run_case(case, model='code/model.py', validator='code/validate.py', timeout=120, dependency_mode=None):
    case = under_project(case)
    config = read_case_config(case)
    dependency_mode = config.get('dependency_mode', 'conservative') if dependency_mode is None else dependency_mode
    if dependency_mode not in ('conservative', 'python-reviewed'):
        raise ValueError('dependency_mode must be conservative or python-reviewed')
    if not config.get('intake_complete') or input_changes(case, config):
        raise ValueError('Intake incomplete or raw inputs changed; do not use stale materials')
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise ValueError('timeout must be integer seconds from 1 to 3600')
    model_path, validator_path = code_path(case, model), code_path(case, validator)
    schema = config.get('schema', 1)
    contract = None
    contract_warnings = []
    if schema == 2:
        contract_path = case / 'planning/model-contract.json'
        if not contract_path.is_file():
            raise ValueError('schema 2 requires planning/model-contract.json before running')
        contract = read_json(contract_path)
        problems = check_model_contract(contract, contract_warnings)
        if problems:
            raise ValueError('Model contract rejected before execution: ' + '; '.join(problems))
    code_hashes = source_snapshot(case)
    dependency_hashes = dependency_snapshot()
    attempt = case / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
    attempt.mkdir(parents=True, exist_ok=False)
    out = attempt / 'output'
    out.mkdir()
    receipt = {'schema': schema, 'started_utc': stamp(), 'phase': config['phase'],
               'inputs': config['inputs'], 'code': code_hashes, 'dependencies': dependency_hashes,
               'environment': environment_snapshot(), 'steps': [],
               'status': 'running', 'automatic_checks_passed': False,
               'human_verification': config['human_verification']}
    snapshots = [('source-snapshot', case, code_hashes)]
    commit = clean_bundle_commit() if schema == 2 else None
    if commit:
        receipt['bundle_git_commit'] = commit
    else:
        snapshots.append(('dependency-snapshot', BUNDLE, dependency_hashes))
    if contract is not None:
        parameters = contract['parameters']
        declared = sum(p['source_level'] == 'declared' for p in parameters)
        receipt['model_contract_warnings'] = (
            [f'{declared}/{len(parameters)} parameters are declared scenarios (>70%); verify empirical relevance']
            if parameters and declared / len(parameters) > 0.7 else []) + contract_warnings
    for prefix, root, snapshot in snapshots:
        for relative in snapshot:
            target = attempt / prefix / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
    env = run_trace.fixed_presentation_environment(os.environ)
    parent_pythonpath = env.get('PYTHONPATH')
    parent_pythonpath_sha256 = hashlib.sha256(parent_pythonpath.encode()).hexdigest() if parent_pythonpath is not None else None
    env['PYTHONPATH'] = str(BUNDLE) + os.pathsep + env.get('PYTHONPATH', '')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    commands = [('model', [sys.executable, str(model_path), '--output', str(out)]),
                ('validation', [sys.executable, str(validator_path), '--results', str(out / 'results.json'),
                                '--output', str(attempt / 'checks.json')])]
    invariants = [run_trace.file_state(p) for p in [Path(__file__), BUNDLE/'scripts/run_trace.py',
                  BUNDLE/'modeling/schema_contracts.py', BUNDLE/'pyproject.toml', BUNDLE/'uv.lock',
                  case/'case.json', model_path, validator_path] +
                  [case/relative for relative in code_hashes if relative.startswith('planning/')]]
    def observed_dependencies():
        stages=[];uncovered=[]
        for step in receipt['steps']:
            trace_path=attempt/(step['stage']+'.trace.json')
            try:
                trace=read_json(trace_path)
                stages.append({'stage':step['stage'],'trace_path':trace_path.name,
                               'trace_path_absolute':str(trace_path),'sha256':digest(trace_path)})
                uncovered.extend(trace.get('uncovered',[]))
                if not trace.get('finalized'):uncovered.append('incomplete stage trace: '+step['stage'])
            except (OSError,ValueError):uncovered.append('missing or invalid stage trace: '+step['stage'])
        precise=dependency_mode=='python-reviewed' and not uncovered and len(stages)==len(commands)
        return {'schema':2,'parent_pythonpath_sha256':parent_pythonpath_sha256,'requested_mode':dependency_mode,'mode':'python-reviewed' if precise else 'conservative',
                'coverage':{'uncovered':uncovered,'limitations':run_trace.LIMITATIONS,
                            'caller_review_required':True,'os_io_complete':False},
                'stages':stages,'invariants':[run_trace.bind_state(row, case) for row in invariants]}
    save(attempt / 'receipt.json', receipt)
    try:
        for stage, command in commands:
            generated={}
            for previous in receipt['steps']:
                try:
                    trace=read_json(attempt/(previous['stage']+'.trace.json'))
                    generated.update({str(run_trace.observed_path(row, 'logical_path', case)):row.get('producer_stage',previous['stage']) for row in trace['files'] if row.get('role')=='generated'})
                except (OSError,ValueError):pass
            executed=[sys.executable,str(BUNDLE/'scripts/run_trace.py'),'--trace',str(attempt/(stage+'.trace.json')),
                      '--stage',stage,'--case-root',str(case),'--generated',json.dumps(generated),'--']+command[1:]
            step = {'stage': stage, 'argv': command, 'executed_argv':executed, 'started_utc': stamp()}
            receipt['steps'].append(step)
            save(attempt / 'receipt.json', receipt)
            # Child processes write directly to these descriptors. Preserve
            # their actual bytes; a parent text wrapper cannot choose the
            # child's encoding or promise that arbitrary model output is UTF-8.
            with (attempt / (stage + '.stdout.log')).open('wb') as stdout, (attempt / (stage + '.stderr.log')).open('wb') as stderr:
                result = subprocess.run(executed, cwd=case, env=env, stdout=stdout, stderr=stderr, timeout=timeout)
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
        if contract is not None:
            methods = check_method_problems(checks)
            balances = [row['check_name'] for row in contract['conserved_quantities']]
            names = {check['name'] for check in checks if check['passed'] is True}
            methods += [f'Missing passed conservation check: {name}' for name in balances if name not in names]
            if methods:
                raise ValueError('; '.join(methods))
        receipt['actual_dependencies']=observed_dependencies()
        precise=receipt['actual_dependencies']['mode']=='python-reviewed'
        actual_changes=run_trace.changes(receipt['actual_dependencies'], case=case, run=attempt) if precise else []
        if read_case_config(case)['inputs'] != receipt['inputs'] or input_changes(case, config) or actual_changes or source_snapshot(case) != code_hashes or (not precise and dependency_snapshot() != dependency_hashes):
            raise ValueError('Inputs or reviewed code changed during execution: '+ '; '.join(actual_changes))
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
    receipt['actual_dependencies']=observed_dependencies()
    receipt['ended_utc'] = stamp()
    save(attempt / 'receipt.json', receipt)
    return {'run': str(attempt), **receipt}


def run_order(path, receipt):
    """Order attempts by recorded instants, never a random UUID within a second.

    Legacy receipts may omit timestamps: retain directory-time compatibility.
    Malformed timestamps fail closed rather than silently selecting old evidence.
    """
    def instant(value):
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'Invalid run timestamp in {path}: {value!r}') from exc
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)

    started = receipt.get('started_utc')
    ended = receipt.get('ended_utc')
    if started is None and ended is None:
        try:
            start = datetime.strptime(path.parent.name.split('-')[0], '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ValueError(f'Cannot order legacy run without timestamp: {path}') from exc
    else:
        start = instant(started if started is not None else ended)
    finish = instant(ended) if ended is not None else start
    # For exact ties, a failed/incomplete attempt must not be hidden by success.
    return start, finish, not receipt.get('automatic_checks_passed', False), str(path)


def status(case):
    case = under_project(case)
    config = read_case_config(case)
    changes = input_changes(case, config)
    runs = [(path, read_json(path)) for path in (case / 'runs').glob('*/receipt.json')]
    runs.sort(key=lambda item: run_order(*item))
    report = {'case': str(case), 'raw_input_changes': changes, 'runs': [],
              'paper_ready': False, 'human_verification': config['human_verification']}
    for path, receipt in runs:
        stale = list(changes)
        if receipt.get('schema') == 2 and config.get('schema') != 2:
            stale.append('case schema changed from the run receipt schema 2; schema-2 gates no longer apply')
        # Compare the run's immutable intake with the currently registered version.
        if not receipt.get('inputs'):
            stale.append('run input binding missing; validity unknown')
        elif receipt['inputs'] != config['inputs']:
            stale.append('registered input version changed')
        # A precise trace never replaces the case-relative reviewed source binding.
        # In particular, copied cases must check their own model, not the origin.
        for relative, checksum in receipt.get('code', {}).items():
            source = (case / relative).resolve()
            if not source.is_relative_to(case) or not source.is_file() or digest(source) != checksum:
                stale.append(relative)
        actual=receipt.get('actual_dependencies')
        if isinstance(actual,dict) and actual.get('schema') in (1, 2) and actual.get('mode')=='python-reviewed':
            stale.extend(run_trace.changes(actual, case=case, run=path.parent))
        else:
            if receipt.get('dependencies') != dependency_snapshot():
                stale.append('project dependency file set changed or binding missing')
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


CHECK_METHODS = {'analytic', 'enumeration', 'bound', 'conservation', 'hand_calc',
                 'naive_baseline', 'replay', 'external_value'}


BALANCE_METHODS = ('conservation', 'analytic', 'bound')


def check_method_problems(checks):
    return [f'check {check.get("name")!r}: method must be one of {sorted(CHECK_METHODS)}'
            for check in checks if not isinstance(check.get('method'), str)
            or check['method'] not in CHECK_METHODS]


def balance_method_problems(checks):
    """A `balance:` check must close a balance, not merely replay or spot-check it."""
    return [f'check {check["name"]!r}: balance checks must use method {", ".join(BALANCE_METHODS)}'
            for check in checks if isinstance(check, dict) and isinstance(check.get('name'), str)
            and check['name'].startswith('balance:') and check.get('method') not in BALANCE_METHODS]


def claim_problems(requirements, claims, lookup, results, schema=1):
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
        names = claim.get('checks', [])
        if not isinstance(names, list) or any(not isinstance(name, str) or not name.strip() for name in names):
            problems.append(f'claim {cid}: checks must be a list of nonempty strings')
            continue
        want = CLAIM_STRENGTH[claim['strength']]
        have = 0
        pointer = claim.get('result_pointer')
        if pointer:
            try:
                result_pointer(results, pointer)
                have = 1
            except ValueError:
                problems.append(f'claim {cid}: result_pointer {pointer!r} does not resolve')
        linked = [lookup[n] for n in names if n in lookup]
        missing = [n for n in names if n not in lookup]
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
        if schema == 2 and r.get('kind', 'answer') == 'forecast':
            baselines = [lookup[name] for name in r['checks'] if name in lookup
                         and lookup[name].get('method') == 'naive_baseline']
            if not baselines:
                problems.append(f'requirement {r["id"]}: forecast requires a naive_baseline check')
            for check in baselines:
                scores = (check.get('baseline_score'), check.get('model_score'))
                if any(type(score) not in (int, float) for score in scores) \
                        or type(check.get('lower_is_better')) is not bool \
                        or not isinstance(check.get('metric'), str) or not check['metric'].strip():
                    problems.append(f'check {check["name"]}: naive_baseline needs numeric scores, metric and lower_is_better')
                    continue
                baseline, model = scores
                worse = model > baseline if check['lower_is_better'] else model < baseline
                if worse and check.get('disclosed') is not True:
                    problems.append(f'requirement {r["id"]}: model is worse than naive baseline without disclosed: true')
    return problems


FORECAST_WORDS = re.compile(r'forecast|predict|projection|future|预测|未来|趋势', re.IGNORECASE)
REQUIREMENT_KINDS = ('answer', 'forecast', 'decision', 'proof')


def _collapse(text):
    return ' '.join(text.split())


def quote_variants(text):
    """Whitespace-collapsed text with a line-break hyphen ("reser- voir") kept, joined, or kept as "-"."""
    collapsed = _collapse(text)
    return [collapsed] + [re.sub(r'(?<=\w)- (?=\w)', joiner, collapsed) for joiner in ('', '-')]


def quote_found(quote, original):
    return any(q in o for q, o in zip(quote_variants(quote), quote_variants(original)))


def quote_long_enough(quote):
    """At least four non-CJK words, or at least fifteen letters/digits (each CJK character counts as one)."""
    words = re.findall(r'[^\W\u3400-\u9fff]+', quote)
    return len(words) >= 4 or len(re.findall(r'\w', quote)) >= 15


def problem_text_problems(case, definition, original):
    """Schema-2 cases record the extracted question hash at intake; later edits must be declared."""
    recorded = read_case_config(case).get('problem_extracted_sha256')
    path = case / 'planning/problem-extracted.txt'
    if recorded is None or (path.is_file() and digest(path) == recorded):
        return []
    corrections = definition.get('problem_text_corrections')
    if not isinstance(corrections, list) or not corrections:
        return ['planning/problem-extracted.txt differs from its intake hash; list each change in '
                'requirements.json problem_text_corrections [{before, after, reason}]']
    problems = []
    for index, row in enumerate(corrections):
        if (not isinstance(row, dict) or not isinstance(row.get('before'), str)
                or not isinstance(row.get('after'), str) or not row['after'].strip()
                or not reasoned(row.get('reason'))):
            problems.append(f'problem_text_corrections[{index}]: needs before text, nonempty after text and a reason')
        elif not quote_found(row['after'], original):
            problems.append(f'problem_text_corrections[{index}]: after text is not in problem-extracted.txt')
    return problems


def problem_item_problems(case, definition):
    """Validate schema-2 original-question quotations and requirement mappings."""
    problems = []
    items = definition.get('problem_items')
    if not isinstance(items, list) or not items:
        return ['Record nonempty problem_items with original problem quotations']
    problem_path = case / 'planning/problem-extracted.txt'
    original = problem_path.read_text(encoding='utf-8') if problem_path.is_file() else ''
    problems += problem_text_problems(case, definition, original)
    seen, covered, quotes, quote_owner = set(), set(), {}, {}
    for item in items:
        if not isinstance(item, dict):
            problems.append('Each problem_item must be an object')
            continue
        item_id = item.get('id')
        if not isinstance(item_id, str) or not item_id.strip() or item_id in seen:
            problems.append('Each problem_item needs a unique nonempty id')
            continue
        seen.add(item_id)
        quote, page = item.get('quote'), item.get('page')
        if not isinstance(quote, str) or not quote.strip() or not quote_found(quote, original):
            problems.append(f'problem_item {item_id}: quote not found verbatim in problem-extracted.txt')
        if isinstance(quote, str) and quote.strip():
            quotes[item_id] = quote
            if not quote_long_enough(quote):
                problems.append(f'problem_item {item_id}: quote too short; quote at least four words or '
                                'fifteen characters of the original sentence')
            identity = quote_variants(quote)[1].casefold()
            if identity in quote_owner:
                problems.append(f'problem_item {item_id}: same quote as {quote_owner[identity]}; '
                                'each item must quote its own original sentence')
            quote_owner.setdefault(identity, item_id)
        if type(page) is not int or page < 1:
            problems.append(f'problem_item {item_id}: page must be a positive integer')
        if any(isinstance(item.get(key), str) and item[key].strip()
               for key in ('not_addressed_reason', 'conditional_answer')):
            covered.add(item_id)
    for requirement in definition.get('requirements', []):
        requirement_id = requirement.get('id')
        refs = requirement.get('problem_item_ids')
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
            problems.append(f'requirement {requirement_id}: needs nonempty problem_item_ids')
            refs = []
        else:
            unknown = set(refs) - seen
            if unknown:
                problems.append(f'requirement {requirement_id}: unknown problem_item_ids {sorted(unknown)}')
            covered.update(refs)
        kind = requirement.get('kind')
        if 'kind' not in requirement:
            problems.append(f'requirement {requirement_id}: schema 2 requires kind '
                            f'({"|".join(REQUIREMENT_KINDS)})')
        elif kind not in REQUIREMENT_KINDS:
            problems.append(f'requirement {requirement_id}: unsupported kind')
        elif kind != 'forecast':
            worded = [ref for ref in refs if ref in quotes and FORECAST_WORDS.search(quotes[ref])]
            if worded and not reasoned(requirement.get('kind_justification')):
                problems.append(f'requirement {requirement_id}: linked problem items {worded} use forecast wording '
                                f'but kind is {kind}; use kind forecast or give kind_justification')
    for item_id in sorted(seen - covered):
        problems.append(f'problem_item {item_id}: no requirement mapping or explicit conditional/unaddressed reason')
    return problems


def evidence_index(case):
    """Link recorded requirements to the latest run, without certifying completeness."""
    case = under_project(case)
    manifest = case / 'planning/requirements.json'
    definition = read_json(manifest)
    schema = read_case_config(case).get('schema', 1)
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
        if schema == 2 and not any(c.get('independent') is True and isinstance(c.get('method'), str)
                                   and c['method'] in CHECK_METHODS - {'replay'}
                                   for c in entry['check_evidence']):
            errors.append('Requirement needs an independent check with a non-replay method')
        entry['linked'] = not errors
        entry['errors'] = errors
        entries.append(entry)
    claims = definition.get('claims', [])
    claim_issues = claim_problems(tasks, claims, lookup, results, schema) if claims or schema == 2 else []
    problem_issues = problem_item_problems(case, definition) if schema == 2 else []
    if schema == 2:
        problem_issues += check_method_problems(checks) + balance_method_problems(checks)
    complete = all(entry['linked'] for entry in entries) and not claim_issues and not problem_issues
    return {'status': 'evidence-linked' if complete else 'evidence-incomplete', 'claim_problems': claim_issues, 'claims_recorded': len(claims),
            'run': str(run), 'requirements_sha256': digest(manifest),
            'run_receipt_sha256': digest(run / 'receipt.json'),
            'covered': sum(entry['linked'] for entry in entries), 'recorded_requirements': len(entries),
            'entries': entries, 'paper_ready': False,
            **({'problem_item_problems': problem_issues} if schema == 2 else {}),
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
    init.add_argument('--schema', type=int, choices=[1, 2], default=2,
                      help='New cases use schema 2 gates; select 1 for legacy behavior')
    run = commands.add_parser('run')
    run.add_argument('--case', type=Path, required=True)
    run.add_argument('--model', default='code/model.py')
    run.add_argument('--validator', default='code/validate.py')
    run.add_argument('--timeout', type=int, default=120)
    run.add_argument('--full-output', action='store_true', help='print the whole receipt instead of a summary')
    refresh = commands.add_parser('refresh')
    refresh.add_argument('--cases', type=Path, required=True)
    refresh_mode=refresh.add_mutually_exclusive_group()
    refresh_mode.add_argument('--dry-run', action='store_true', help='Read-only comparison; default')
    refresh_mode.add_argument('--execute', action='store_true', help='Use an already authorized workflow attempt')
    refresh.add_argument('--rebuild', action='store_true')
    refresh.add_argument('--output', type=Path)
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
            result = init_case(args.case_root or PROJECT / 'cases',args.name,args.problem,args.data,args.phase,args.encoding,args.schema)
        elif args.action == 'run':
            result = run_case(args.case,args.model,args.validator,args.timeout)
        elif args.action == 'refresh':
            from scripts.case_refresh import refresh as refresh_cases
            destination=under_project(args.output) if args.output is not None else PROJECT/'outputs/refresh'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8])
            refreshed=refresh_cases(args.cases, workspace=PROJECT, dry_run=not args.execute,
                                    output=destination, rebuild=args.rebuild)
            result={'status':refreshed['status'],'report_path':str(destination/'report.json'),
                    'cases':[{key:row.get(key) for key in ('id','categories','recompute_required')} for row in refreshed['cases']]}
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
        # ASCII JSON is valid UTF-8 and preserves Unicode paths after decoding,
        # including on Windows consoles and pipes with a legacy code page.
        print(json.dumps(result,ensure_ascii=True,indent=2,allow_nan=False))
        if result.get('status') in ['failed', 'evidence-incomplete']:
            raise SystemExit(1)
    except (ValueError, FileExistsError, FileNotFoundError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
