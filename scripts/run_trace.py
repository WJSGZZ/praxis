"""Observed Python file use, with explicit limits; not an OS sandbox or I/O proof.

python-reviewed is a caller's source-review assertion. Audit events cannot observe
arbitrary native-library internal I/O. Child processes, network and user ctypes calls
force the conservative pipeline policy; a bound stdlib initialization is recorded separately. Historical receipts are never retrofitted.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time

SCHEMA = 2
LIMITATIONS = ['Python audit/open/exec/import observation only; not an OS sandbox.',
               'Native library internal file/network I/O is not observed; python-reviewed requires caller source review.',
               'Transient edits restored between observations are not guaranteed detectable.']


def file_state(path):
    logical = Path(os.path.abspath(os.fsdecode(path)))
    target = logical.resolve()
    try:
        sha = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    except OSError:
        sha = None
    kind='file' if target.is_file() else 'directory' if target.is_dir() else 'other' if target.exists() else 'missing'
    return {'logical_path': str(logical), 'resolved_path': str(target), 'sha256': sha, 'kind':kind}


def directory_state(path):
    return {'resolved_path':str(Path(path).resolve()),'names':sorted(os.listdir(path))}


# Locale and terminal dimensions are presentation inputs, not scientific configuration.
# New runners fix their values; old observations stay in the immutable trace.
PRESENTATION_ENV = frozenset({'LANG', 'LANGUAGE', 'COLUMNS', 'LINES'})


def presentation_environment(key):
    return key in PRESENTATION_ENV or key.startswith('LC_')


def fixed_presentation_environment(environment):
    result = dict(environment)
    for key in list(result):
        if key.startswith('LC_'):
            result[key] = 'C'
    result.update(LC_ALL='C', LANG='C', LANGUAGE='C', COLUMNS='80', LINES='24')
    return result


def bind_state(row, case):
    """Case-local paths are relocatable; external inputs keep absolute identity."""
    value = dict(row)
    root = Path(case).absolute()
    for field in ('logical_path', 'resolved_path', 'end_resolved_path'):
        if isinstance(value.get(field), str):
            path = Path(value[field])
            if path.is_absolute() and path.is_relative_to(root):
                value[field] = str(path.relative_to(root))
                value[field.replace('_path', '_scope')] = 'case'
    return value


def _path(value, scope, case, historical_root=None):
    path = Path(value)
    if scope == 'case':
        if case is None or path.is_absolute() or '..' in path.parts:
            raise ValueError('Invalid case-relative dependency path')
        return Path(case).absolute() / path
    if scope is not None or not path.is_absolute():
        raise ValueError('Invalid external dependency path')
    # Schema1 compatibility is read-only. The observed stage cwd defines the
    # original case, not a guessed prefix or the source's current location.
    if case is not None and historical_root is not None and path.is_relative_to(historical_root):
        return Path(case).absolute() / path.relative_to(historical_root)
    return path


def observed_path(row, field, case, historical_root=None):
    return _path(row[field], row.get(field.replace('_path', '_scope')), case, historical_root)


def changes(actual, *, case=None, run=None):
    """Check current case-local evidence, external identity and scientific inputs.

    Old absolute schema1 traces are resolved against their recorded cwd, without
    modifying their bytes. Case source snapshots are independently checked by
    the pipeline even when Python observation is complete.
    """
    problems = []
    value = os.environ.get('PYTHONPATH')
    current = hashlib.sha256(value.encode()).hexdigest() if value is not None else None
    if current != actual.get('parent_pythonpath_sha256'):
        problems.append('parent PYTHONPATH changed')
    traces = []
    roots = set()
    for stage in actual.get('stages', []):
        relative = Path(stage.get('trace_path', ''))
        if run is not None:
            if not relative.name or relative.is_absolute() or '..' in relative.parts:
                problems.append('invalid dependency trace path'); continue
            trace_path = Path(run) / relative
        else:
            trace_path = Path(stage['trace_path_absolute'])
        if not trace_path.is_file() or file_state(trace_path)['sha256'] != stage['sha256']:
            problems.append('dependency trace missing or changed: ' + str(trace_path)); continue
        try:
            trace = json.loads(trace_path.read_text(encoding='utf-8'))
            if trace.get('schema') not in (1, 2):
                raise ValueError('Unsupported dependency trace schema')
            root = trace.get('case_root') if trace.get('schema') == 2 else trace.get('cwd')
            if not isinstance(root, str) or not Path(root).is_absolute():
                raise ValueError('Missing recorded case root')
            roots.add(root)
            traces.append(trace)
        except (OSError, ValueError, TypeError):
            problems.append('invalid dependency trace: ' + str(trace_path))
    if len(roots) > 1:
        problems.append('conflicting recorded dependency case roots')
        return sorted(set(problems))
    historical_root = Path(next(iter(roots))) if roots else None
    records = list(actual.get('invariants', []))
    for trace in traces:
        listings = trace.get('directory_listings', {})
        rows = ([dict(logical_path=logical, **(expected or {}), missing=expected is None)
                 for logical, expected in listings.items()] if isinstance(listings, dict) else listings)
        for row in rows:
            try:
                logical = observed_path(row, 'logical_path', case, historical_root)
                expected = None if row.get('missing') else {
                    'resolved_path': str(observed_path(row, 'resolved_path', case, historical_root)),
                    'names': row['names']}
                now = directory_state(logical)
            except OSError:
                now = None
            except (ValueError, TypeError, KeyError):
                problems.append('invalid directory dependency'); continue
            if now != expected:
                problems.append('used directory listing changed: ' + str(logical))
        for key, expected in trace.get('environment_reads', {}).items():
            if key in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE') or presentation_environment(key):
                continue  # fixed runner inputs; full observed values remain recorded
            value = os.environ.get(key)
            current = hashlib.sha256(value.encode()).hexdigest() if value is not None else None
            if current != expected:
                problems.append('used environment variable changed: ' + key)
        for row in trace.get('files', []):
            if row.get('read') and row.get('role') != 'generated':
                records.append(dict(row, sha256=row['first_sha256']))
                if row.get('changed_during_stage'):
                    problems.append('dependency changed during execution: ' + row['logical_path'])
    for row in records:
        try:
            logical = observed_path(row, 'logical_path', case, historical_root)
            expected = {'logical_path': str(logical),
                        'resolved_path': str(observed_path(row, 'resolved_path', case, historical_root)),
                        'sha256': row['sha256'], 'kind': row['kind']}
            if file_state(logical) != expected:
                problems.append('actual dependency changed: ' + str(logical))
        except (OSError, ValueError, TypeError, KeyError):
            problems.append('invalid file dependency: ' + str(row.get('logical_path')))
    return sorted(set(problems))

class Observer:
    def __init__(self, output, stage, generated, case=None):
        self.output = output
        self.case = Path(case or os.getcwd()).absolute()
        self.case_prefix = str(self.case) + os.sep
        self.path_bindings = {}
        self.busy = False
        self.last_checkpoint=0.0
        self.generated = generated if isinstance(generated,dict) else {path:None for path in generated}
        self.files = {}
        self.data = {'schema':SCHEMA,'stage':stage,'argv':sys.argv[:], 'cwd':os.getcwd(),
                     'case_root':str(self.case), 'files':[], 'directory_listings':{}, 'native_events':[], 'runtime_initializations':[], 'uncovered':[], 'extensions':[], 'limitations':LIMITATIONS,
                     'completed':False,'finalized':False, 'environment_reads':{},
                     'environment_fingerprint':hashlib.sha256(json.dumps(dict(os.environ),sort_keys=True).encode()).hexdigest()}

    def portable_state(self, row):
        # A stage can observe thousands of import candidates. Bind each path
        # once, rather than reparsing every path during every full checkpoint.
        value = dict(row)
        for field in ('logical_path', 'resolved_path', 'end_resolved_path'):
            path = value.get(field)
            if not isinstance(path, str):
                continue
            if path not in self.path_bindings:
                if path == str(self.case):
                    self.path_bindings[path] = '.'
                elif path.startswith(self.case_prefix):
                    self.path_bindings[path] = path[len(self.case_prefix):]
                else:
                    self.path_bindings[path] = None
            relative = self.path_bindings[path]
            if relative is not None:
                value[field] = relative
                value[field.replace('_path', '_scope')] = 'case'
        return value

    def checkpoint(self,force=False):
        now=time.monotonic()
        if not force and self.data['files'] and now-self.last_checkpoint<.25:return
        self.data['files'] = list(self.files.values())
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output.with_suffix('.partial')
        payload = dict(self.data)
        payload['files'] = [self.portable_state(row) for row in self.data['files']]
        payload['extensions'] = [self.portable_state(row) for row in self.data['extensions']]
        payload['directory_listings'] = [self.portable_state(dict(logical_path=logical, **(expected or {}),
            missing=expected is None)) for logical, expected in self.data['directory_listings'].items()]
        temporary.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        os.replace(temporary,self.output)
        self.last_checkpoint=time.monotonic()

    def observe(self,path,read=True,write=False):
        if not isinstance(path,(str,bytes,os.PathLike)):
            if read: self.data['uncovered'].append('read via inherited/unidentified file descriptor')
            return
        logical=os.path.abspath(os.fsdecode(path))
        row=self.files.get(logical)
        if row is not None and row['read'] and not write:
            return  # final rehash detects persistent mid-stage changes; transient restores are a stated limit
        state = file_state(path)
        if row is None:
            generated=logical in self.generated or write and state['sha256'] is None
            row={**state,'first_sha256':state['sha256'],'end_sha256':None,
                 'read':False,'written':False,'role':'generated' if generated else 'input',
                 'producer_stage':self.generated.get(logical,self.data['stage']) if generated else None,
                 'changed_during_stage':False}
            self.files[logical]=row
        elif read and row['read'] and (state['sha256']!=row['first_sha256'] or state['resolved_path']!=row['resolved_path']):
            row['changed_during_stage']=True
        if write and row['first_sha256'] is None:
            row['role']='generated';row['producer_stage']=self.data['stage']
        row['read'] |= read;row['written'] |= write
        self.checkpoint()

    def hook(self,event,args):
        if self.busy:return
        self.busy=True
        try:
            if event=='open':
                path,mode,flags=args
                read = 'r' in mode or '+' in mode if isinstance(mode,str) else not flags & os.O_WRONLY
                write = bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
                self.observe(path,read,write)
            elif event in ('os.listdir','os.scandir'):
                caller=sys._getframe(1).f_code.co_filename
                if 'importlib' in caller:
                    return  # import candidate paths and executed sources are bound below
                path=args[0] if args and args[0] is not None else os.getcwd()
                if isinstance(path,(str,bytes,os.PathLike)):
                    logical=os.path.abspath(os.fsdecode(path))
                    if not Path(logical).is_relative_to(self.output.parent):
                        try:self.data['directory_listings'].setdefault(logical,directory_state(logical))
                        except OSError:self.data['directory_listings'].setdefault(logical,None)
                    self.checkpoint()
                else:self.data['uncovered'].append('directory listing via unidentified descriptor')
            elif event=='exec':
                filename=args[0].co_filename
                if filename and not filename.startswith('<'):self.observe(filename)
            elif event=='import' and len(args)>1 and args[1] is None:
                name=args[0].replace('.',os.sep)
                for root in sys.path:
                    if isinstance(root,str):
                        for suffix in (name+'.py',os.path.join(name,'__init__.py')):
                            self.observe(os.path.join(root or os.getcwd(),suffix))
            elif event=='import' and len(args)>1 and isinstance(args[1],str):
                self.observe(args[1])
                if args[1].endswith(('.so','.pyd','.dylib')):
                    self.data['extensions'].append(file_state(args[1]))
            elif event=='ctypes.dlopen':
                frames=[];frame=sys._getframe(1)
                while frame is not None and len(frames)<20:
                    filename=frame.f_code.co_filename
                    record={'file':filename,'function':frame.f_code.co_name,'line':frame.f_lineno}
                    if filename and not filename.startswith('<'):
                        try:record['source_line']=Path(filename).read_text(encoding='utf-8').splitlines()[frame.f_lineno-1].strip()
                        except (OSError,UnicodeError,IndexError):pass
                    frames.append(record);frame=frame.f_back
                observation={'event':event,'target':args[0] if args else None,'stack':frames}
                self.data['native_events'].append(observation)
                stdlib_ctypes=(Path(os.__file__).parent/'ctypes/__init__.py').resolve()
                matched=next((f for f in frames if f['function']=='<module>' and
                              f.get('source_line')=='pythonapi = PyDLL(None)' and
                              not f['file'].startswith('<') and Path(f['file']).resolve()==stdlib_ctypes),None)
                if observation['target'] is None and matched is not None:
                    self.observe(stdlib_ctypes)
                    self.data['runtime_initializations'].append({**observation,
                        'source_line':matched['source_line'],'source':file_state(stdlib_ctypes),
                        'reason':'Bound stdlib ctypes top-level pythonapi initialization; no user-library load is inferred.'})
                else:self.data['uncovered'].append(event)
                self.checkpoint()
            elif event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','ctypes.dlopen','ctypes.dlsym') or event.startswith('socket.'):
                self.data['uncovered'].append(event);self.checkpoint()
        except Exception as exc:
            self.data['uncovered'].append('audit observation failure: '+type(exc).__name__)
        finally:self.busy=False

    def finish(self,completed):
        self.busy=True
        try:
            for row in self.files.values():
                now=file_state(row['logical_path']);row['end_sha256']=now['sha256'];row['end_resolved_path']=now['resolved_path']
                if row['read'] and row['role']!='generated' and (now['sha256']!=row['first_sha256'] or now['resolved_path']!=row['resolved_path']):row['changed_during_stage']=True
            self.data.update(completed=completed,finalized=True)
            self.checkpoint(force=True)
        finally:self.busy=False


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--trace',type=Path,required=True);parser.add_argument('--stage',required=True);parser.add_argument('--case-root',type=Path);parser.add_argument('--generated',default='[]');parser.add_argument('command',nargs=argparse.REMAINDER)
    a=parser.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
    observer=Observer(a.trace,a.stage,json.loads(a.generated),case=a.case_root)
    observer.data['target_argv']=command;observer.data['python']=sys.executable
    observer.busy=True;observer.checkpoint(force=True);observer.busy=False
    # The minimal trusted bootstrap imports stdlib before installing hooks. Bind
    # those actual module files too, separately from later exec/import events.
    observer.busy=True
    for module in list(sys.modules.values()):
        path=getattr(module,'__file__',None)
        if isinstance(path,str) and Path(path).is_file():
            observer.observe(path)
    observer.checkpoint(force=True)
    observer.busy=False
    sys.addaudithook(observer.hook)
    original_stat=os.stat
    def observed_stat(path,*args,**kwargs):
        if not observer.busy and isinstance(path,(str,bytes,os.PathLike)):
            observer.busy=True
            try:observer.observe(path)
            finally:observer.busy=False
        return original_stat(path,*args,**kwargs)
    os.stat=observed_stat
    environment_class=type(os.environ)
    original_getitem=environment_class.__getitem__
    def observed_getitem(mapping,key):
        try:value=original_getitem(mapping,key)
        except KeyError:
            value=None
            if mapping is os.environ and not observer.busy:
                observer.data['environment_reads'].setdefault(str(key),None)
            raise
        if mapping is os.environ and not observer.busy:
            observer.data['environment_reads'].setdefault(str(key),hashlib.sha256(value.encode()).hexdigest())
        return value
    environment_class.__getitem__=observed_getitem
    sys.argv=command
    # Match direct-script import resolution without relying on sys.modules inventory.
    sys.path.insert(0,str(Path(command[0]).parent))
    ok=False
    try:
        runpy.run_path(command[0],run_name='__main__');ok=True
    except SystemExit as exc:
        ok=exc.code is None or exc.code==0
        raise
    finally:observer.finish(ok)


if __name__=='__main__':main()
