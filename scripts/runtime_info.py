"""Read-only process, dependency metadata and explicit plugin-resource diagnostics.

    python -m scripts.runtime_info

No model, compiler, network or installer is run. A disk receipt is neither a
publisher signature nor evidence that this process/chat reloaded those bytes.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import re
import shutil
import sys
import tomllib

CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))
from modeling.schema_contracts import unique_object_pairs

MAX_JSON_BYTES = 1024 * 1024
MAX_RECEIPT_FILES = 4096
MAX_HASH_BYTES = 512 * 1024 * 1024
MAX_SAMPLES = 8
PRIVATE_PATH_PARTS = frozenset({'.venv', '.local', '.session', 'outputs', 'cases', 'planning', 'lessons'})
KEY_RESOURCES = (
    'SKILL.md', 'pyproject.toml', 'uv.lock', 'packaging/plugin.json', 'packaging/mcp.json',
    'templates/mcm-paper.tex', 'templates/mcm-style.tex', 'templates/cumcm-paper.tex',
    'templates/cumcm-style.tex', 'templates/research-paper.tex', 'templates/research-style.tex',
    'templates/cumcm-fonts.json', 'templates/typesetting-runtime.json', 'scripts/build_plugin.py',
)


def _safe_file(root, name):
    if (not isinstance(name, str) or not name or len(name) > 4096 or '\\' in name
            or '\x00' in name or PurePosixPath(name).is_absolute()
            or PureWindowsPath(name).drive or '..' in PurePosixPath(name).parts):
        raise ValueError('Expected a safe package-relative POSIX path')
    path = root
    for part in PurePosixPath(name).parts:
        path /= part
        if path.is_symlink():
            raise ValueError('Symlink resource paths are not inspected')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Resource escapes the declared package root')
    return path


def _limited_bytes(path):
    if not path.is_file():
        raise ValueError('Diagnostic metadata must be a regular file')
    with path.open('rb') as stream:
        data = stream.read(MAX_JSON_BYTES + 1)
    if len(data) > MAX_JSON_BYTES:
        raise ValueError('Diagnostic metadata exceeds the 1 MiB limit')
    return data


def _reject_constant(value):
    raise ValueError('Non-finite JSON metadata')


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('Non-finite JSON metadata')
    return number


def _json(path):
    return json.loads(_limited_bytes(path), object_pairs_hook=unique_object_pairs,
                      parse_constant=_reject_constant, parse_float=_finite_float)


def _problem(items, path, status, reason):
    if len(items) < MAX_SAMPLES:
        items.append(dict(path=path[:240], status=status, reason=str(reason)[:240]))


def _project(core):
    try:
        path = _safe_file(core, 'pyproject.toml')
        project = tomllib.loads(_limited_bytes(path).decode('utf-8'))['project']
        deps = project.get('dependencies', [])
        if (not isinstance(project.get('name'), str) or len(project['name']) > 128
                or not isinstance(project.get('version'), str) or len(project['version']) > 128
                or not isinstance(deps, list) or len(deps) > 128
                or any(not isinstance(d, str) or len(d) > 512 for d in deps)
                or project.get('requires-python') is not None and (
                    not isinstance(project['requires-python'], str) or len(project['requires-python']) > 256)):
            raise ValueError('Invalid project metadata')
        return dict(status='read', name=project['name'], version=project['version'],
                    requires_python=project.get('requires-python'), dependencies=project.get('dependencies', []))
    except (OSError, ValueError, KeyError, TypeError) as error:
        return dict(status='unavailable', version=None, dependencies=[], reason=str(error)[:240])


def _dependencies(project):
    rows = []
    for requirement in project['dependencies']:
        match = re.match(r'^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)', requirement) if isinstance(requirement, str) else None
        if match is None:
            rows.append(dict(requirement=str(requirement)[:160], status='invalid_requirement', version=None))
            continue
        name = match.group(1)
        try:
            version = metadata.version(name)
            if not isinstance(version, str) or not version or len(version) > 256:
                raise ValueError('Distribution version metadata is absent or invalid')
            rows.append(dict(name=name, requirement=requirement, status='metadata_found', version=version))
        except metadata.PackageNotFoundError:
            rows.append(dict(name=name, requirement=requirement, status='metadata_missing', version=None))
        except (ValueError, OSError, UnicodeError) as error:
            rows.append(dict(name=name, requirement=requirement, status='metadata_unreadable',
                             version=None, reason=str(error)[:160]))
    return dict(declared=len(rows), metadata_found=sum(r['status'] == 'metadata_found' for r in rows),
                missing=sum(r['status'] != 'metadata_found' for r in rows), packages=rows,
                scope='Visible distribution metadata only; imports, ABI compatibility and locked-version satisfaction are not tested.')


def _layout(core):
    # A source checkout can legitimately live in ~/.agents/skills/praxis.
    # Its focused skills live inside the core; exports put them beside it.
    # A nested directory added to an export must not hide its actual receipt.
    # Check the enclosing explicit package identity before source-layout fallback.
    if core.name == 'praxis' and core.parent.name == 'skills':
        root = core.parent.parent.resolve()
        try:
            # An unsafe receipt still identifies an export to diagnose; do not
            # reclassify it as a receipt-free source and silently ignore it.
            if (root / 'build-receipt.json').is_symlink():
                return dict(kind='export', root=root)
            receipt = _safe_file(root, 'build-receipt.json')
            if receipt.exists():
                return dict(kind='export', root=root)
            manifest = _json(_safe_file(root, 'plugin.json'))
            if isinstance(manifest, dict) and manifest.get('name') == 'praxis':
                return dict(kind='export', root=root)
        except (OSError, ValueError, TypeError, RecursionError):
            pass
    return dict(kind='source', root=core)


def _resources(core, layout):
    resource_root = layout['root']
    samples, counts = [], dict(checked=0, present=0, missing=0, unsafe=0)
    for name in KEY_RESOURCES:
        counts['checked'] += 1
        try:
            exists = _safe_file(core, name).is_file()
            counts['present' if exists else 'missing'] += 1
            if not exists:
                _problem(samples, name, 'missing', 'Required shared resource is absent')
        except (OSError, ValueError) as error:
            counts['unsafe'] += 1
            _problem(samples, name, 'unsafe', error)
    # The exporter's explicit literal is the skill roster, not a tool registry.
    # Reading this bounded AST never executes the exporter or user instructions.
    skill_count = 0
    try:
        tree = ast.parse(_limited_bytes(_safe_file(core, 'scripts/build_plugin.py')))
        roster = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'FOCUSED' for t in n.targets))
        if (not isinstance(roster, tuple) or len(roster) > 256 or len(set(roster)) != len(roster)
                or any(not isinstance(s, str) or re.fullmatch(r'praxis-[a-z-]+', s) is None for s in roster)):
            raise ValueError('Invalid explicit focused-skill roster')
        for skill in roster:
            counts['checked'] += 1
            name = 'skills/' + skill + '/SKILL.md'
            try:
                exists = _safe_file(resource_root, name).is_file()
                counts['present' if exists else 'missing'] += 1
                skill_count += int(exists)
                if not exists:
                    _problem(samples, name, 'missing', 'Declared focused skill is absent')
            except (OSError, ValueError) as error:
                counts['unsafe'] += 1
                _problem(samples, name, 'unsafe', error)
    except (OSError, ValueError, TypeError, StopIteration, SyntaxError, RecursionError) as error:
        counts['unsafe'] += 1
        _problem(samples, 'scripts/build_plugin.py:FOCUSED', 'roster_unavailable', error)
    return dict(**counts, focused_skills_present=skill_count, samples=samples,
                scope='Explicit shared resources and exporter-declared skill paths; host discovery and document compilation are not checked.')


def _receipt(core, project, layout):
    if layout['kind'] != 'export':
        return dict(status='not_applicable', reason='Source-layout core has no required export receipt')
    root = layout['root']
    samples = []
    counts = dict(total=0, matched=0, changed=0, missing=0, unsafe=0, unreadable=0, not_checked=0)
    try:
        receipt_path = _safe_file(root, 'build-receipt.json')
        if not receipt_path.exists():
            return dict(status='not_present', integrity='unknown', reason='Export manifest found without a receipt; declared-file integrity is unverified')
        receipt = _json(receipt_path)
        entries = receipt.get('files_sha256') if isinstance(receipt, dict) else None
        if (receipt.get('format') != 'praxis-plugin-export-v1' or not isinstance(entries, dict)
                or not entries or len(entries) > MAX_RECEIPT_FILES
                or receipt.get('name') != project.get('name') or not isinstance(receipt.get('version'), str)):
            raise ValueError('Unsupported or inconsistent actual exporter receipt')
        version_match = receipt['version'] == project.get('version')
        counts['total'] = len(entries)
        used_bytes = 0
        for name, expected in entries.items():
            try:
                if (name == 'build-receipt.json' or PRIVATE_PATH_PARTS.intersection(PurePosixPath(name).parts)
                        or not isinstance(expected, str) or re.fullmatch(r'[0-9a-f]{64}', expected) is None):
                    raise ValueError('Invalid hash entry, self-hash or private/runtime directory entry')
                path = _safe_file(root, name)
                if not path.exists():
                    counts['missing'] += 1
                    _problem(samples, name, 'missing', 'Declared file is absent')
                    continue
                if not path.is_file():
                    raise ValueError('Declared resource is not a regular file')
                size = path.stat().st_size
                if used_bytes + size > MAX_HASH_BYTES:
                    counts['not_checked'] += 1
                    _problem(samples, name, 'not_checked', 'Diagnostic 512 MiB hash budget exceeded')
                    continue
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    while block := stream.read(1024 * 1024):
                        used_bytes += len(block)
                        if used_bytes > MAX_HASH_BYTES:
                            raise ValueError('Diagnostic hash budget exceeded while reading')
                        digest.update(block)
                status = 'matched' if digest.hexdigest() == expected else 'changed'
                counts[status] += 1
                if status == 'changed':
                    _problem(samples, name, status, 'Disk bytes differ from the declared receipt hash')
            except ValueError as error:
                counts['unsafe'] += 1
                _problem(samples, str(name), 'unsafe', error)
            except OSError as error:
                counts['unreadable'] += 1
                _problem(samples, str(name), 'unreadable', error)
        normal = version_match and counts['matched'] == counts['total']
        return dict(status='matched' if normal else 'attention', path=str(receipt_path),
                    version=receipt['version'], core_version_matches=version_match, **counts, samples=samples,
                    scope='Explicit declared package disk files only; private/runtime directories, receipt self and generated .venv are excluded. No external workspace scan. Matching does not authenticate the publisher or prove already-loaded code/chat reloading.')
    except (OSError, ValueError, TypeError, AttributeError, RecursionError) as error:
        return dict(status='attention', path=str(root / 'build-receipt.json'), **counts,
                    reason=str(error)[:240], samples=samples)


def inspect_runtime(*, tool_names=None):
    """Return bounded strict-JSON diagnostics for this process and this core."""
    core = CORE_ROOT.resolve()
    if tool_names is None:
        tools = dict(status='not_loaded', count=None, reason='No registry supplied; CLI does not import MCP or guess tool counts')
    else:
        if isinstance(tool_names, (str, bytes)):
            raise ValueError('tool_names must be a bounded collection of actual registered names')
        names = []
        for name in tool_names:
            if (len(names) >= 512 or not isinstance(name, str) or not name or len(name) > 128
                    or name in names):
                raise ValueError('Expected at most 512 unique nonempty registered tool names')
            names.append(name)
        tools = dict(status='provided_by_caller', count=len(names), scope='Actual names supplied by the calling registry, not a disk/host/chat reload claim')
    project = _project(core)
    layout = _layout(core)
    deps = _dependencies(project)
    resources = _resources(core, layout)
    receipt = _receipt(core, project, layout)
    executable = shutil.which('tectonic')
    compiler = dict(status='found_not_verified' if executable else 'not_found',
                    path=os.path.abspath(executable) if executable else None, executed=False,
                    scope='Optional PDF compiler location only; no version or document compilation test')
    attention = (project['status'] != 'read' or deps['missing'] > 0 or resources['missing'] > 0
                 or resources['unsafe'] > 0 or receipt['status'] in ('attention', 'not_present')
                 or sys.version_info[:2] != (3, 12))
    result = dict(schema_version=1, status='attention' if attention else 'normal',
                  process=dict(python_version=platform.python_version(), implementation=platform.python_implementation(),
                               executable=os.path.abspath(sys.executable), prefix=os.path.abspath(sys.prefix),
                               base_prefix=os.path.abspath(sys.base_prefix), platform=sys.platform,
                               system=platform.system(), release=platform.release(), machine=platform.machine(),
                               site_startup='disabled_by_-S' if sys.flags.no_site else 'enabled'),
                  core_path=str(core), core_layout=layout['kind'], project={k: v for k, v in project.items() if k != 'dependencies'},
                  dependencies=deps, tools=tools, resources=resources, export_receipt=receipt, compiler=compiler,
                  scope='Read-only process metadata and explicit disk-resource checks. No network, installation, model or compiler execution; no active-chat reload certification.')
    json.dumps(result, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pretty', action='store_true', help='Indent the diagnostic JSON')
    args = parser.parse_args()
    print(json.dumps(inspect_runtime(), ensure_ascii=True, allow_nan=False, indent=2 if args.pretty else None))


if __name__ == '__main__':
    main()
