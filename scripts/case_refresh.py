"""Refresh explicit local case manifests without rewriting historical evidence.

Dry runs never predict uncomputed numbers. Execution uses the existing workflow
budget; neither this module nor a manifest can initialize/reset that budget.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import subprocess
import uuid

from scripts import pipeline


def _finite_tree(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Comparison requires finite JSON values')
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError('JSON object keys must be strings')
        for x in value.values():
            _finite_tree(x)
    elif isinstance(value, list):
        for x in value:
            _finite_tree(x)
    elif value is not None and not isinstance(value, (str, bool, int, float)):
        raise ValueError('Comparison requires JSON values')


def _pointer_part(value):
    return str(value).replace('~', '~0').replace('/', '~1')


def compare_results(old, new, tolerances=None):
    """Compare every JSON field, with explicit abs+relative numeric tolerances.

    A difference is tolerated iff abs(a-b) <= absolute + relative*max(abs(a),abs(b)).
    Decimal conversion preserves integers beyond floating point's exact range.
    Ignored exact RFC6901 paths remain visible; array reordering is a change.
    """
    _finite_tree(old); _finite_tree(new)
    tolerances = tolerances or {}
    if not isinstance(tolerances, dict) or set(tolerances) - {'absolute', 'relative', 'ignore_paths'}:
        raise ValueError('Unknown comparison tolerance fields')
    absolute, relative = tolerances.get('absolute', 0), tolerances.get('relative', 0)
    for v in (absolute, relative):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError('Tolerances must be finite nonnegative numbers')
    ignored = tolerances.get('ignore_paths', [])
    if not isinstance(ignored, list) or len(set(ignored)) != len(ignored) or any(
            not isinstance(p, str) or not p.startswith('/') or re.search(r'~(?![01])', p) for p in ignored):
        raise ValueError('ignore_paths must be distinct exact JSON pointers')
    report = {'changes': [], 'compared_values': 0, 'within_tolerance': 0,
              'ignored_paths': [], 'tolerances': tolerances,
              'array_alignment': 'positional; reorderings are not silently aligned'}
    def difference(path, kind, a=None, b=None, **extra):
        report['changes'].append(dict(path=path, kind=kind, old=a, new=b, **extra))
    def walk(a, b, path):
        if path in ignored:
            report['ignored_paths'].append(path); return
        report['compared_values'] += 1
        numbers = (isinstance(a, (int, float)) and not isinstance(a, bool)
                   and isinstance(b, (int, float)) and not isinstance(b, bool))
        if numbers:
            if a == b:
                return
            x, y = Decimal(str(a)), Decimal(str(b))
            limit = Decimal(str(absolute)) + Decimal(str(relative))*max(abs(x), abs(y))
            if abs(x-y) <= limit:
                report['within_tolerance'] += 1
            else:
                difference(path, 'number', a, b)
        elif type(a) is not type(b):
            difference(path, 'type', a, b)
        elif isinstance(a, dict):
            for k in sorted(a.keys() | b.keys()):
                p = path + '/' + _pointer_part(k)
                if k not in a:
                    difference(p, 'added', b=b[k], old_present=False, new_present=True)
                elif k not in b:
                    difference(p, 'removed', a=a[k], old_present=True, new_present=False)
                else:
                    walk(a[k], b[k], p)
        elif isinstance(a, list):
            for i in range(max(len(a), len(b))):
                p = path + '/' + str(i)
                if i >= len(a):
                    difference(p, 'added', b=b[i], old_present=False, new_present=True)
                elif i >= len(b):
                    difference(p, 'removed', a=a[i], old_present=True, new_present=False)
                else:
                    walk(a[i], b[i], p)
        elif a != b:
            difference(path, 'value', a, b)
    walk(old, new, '')
    return report


def conclusion_changes(old, new, checks):
    """Evaluate declared answer/threshold predicates; missing evidence fails closed."""
    changes = []
    if not isinstance(checks, list):
        raise ValueError('conclusions must be a list')
    ids = set()
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get('id'), str) or check['id'] in ids:
            raise ValueError('Conclusion checks need distinct ids')
        ids.add(check['id'])
        try:
            a = pipeline.result_pointer(old, check['pointer'])
            b = pipeline.result_pointer(new, check['pointer'])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError('Conclusion evidence missing at ' + str(check.get('pointer'))) from exc
        op = check.get('operator', 'identity')
        if op == 'identity':
            before, after = a, b
        elif op in {'gt', 'ge', 'lt', 'le', 'eq'}:
            t = check.get('threshold')
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (a, b, t)):
                raise ValueError('Threshold predicates require finite numbers')
            compare = {'gt': lambda x: x > t, 'ge': lambda x: x >= t, 'lt': lambda x: x < t,
                       'le': lambda x: x <= t, 'eq': lambda x: x == t}[op]
            before, after = compare(a), compare(b)
        else:
            raise ValueError('Unknown conclusion predicate operator')
        if type(before) is not type(after) or before != after:
            changes.append({**check, 'old': a, 'new': b, 'old_answer': before, 'new_answer': after})
    return changes


def _safe(workspace, value):
    path = Path(value)
    if '..' in path.parts:
        raise ValueError('Path traversal forbidden')
    path = path if path.is_absolute() else workspace / path
    if not path.is_relative_to(workspace):
        raise ValueError('Refresh paths must remain inside the workspace')
    cursor = workspace
    for part in path.relative_to(workspace).parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError('Symlink paths forbidden')
    if not path.resolve().is_relative_to(workspace):
        raise ValueError('Refresh paths must remain inside the workspace')
    return path


def load_manifest(manifest, workspace):
    workspace = Path(workspace).resolve()
    data = pipeline.read_json(_safe(workspace, manifest)) if not isinstance(manifest, dict) else manifest
    _finite_tree(data)
    if not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1:
        raise ValueError('Refresh manifest requires schema 1')
    entries = data.get('cases')
    if not isinstance(entries, list) or not entries:
        raise ValueError('Refresh manifest requires a nonempty cases list')
    ids, paths = set(), set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', entry['id']):
            raise ValueError('Each case requires an id')
        case = _safe(workspace, entry['case'])
        if entry['id'] in ids or str(case) in paths:
            raise ValueError('Duplicate case id or path')
        ids.add(entry['id']); paths.add(str(case))
        if 'baseline_case' in entry:
            _safe(workspace, entry['baseline_case'])
        if not re.fullmatch(r'[A-Za-z0-9_-]+', entry.get('baseline_run', '')):
            raise ValueError('Each case needs an explicit baseline_run id')
    return data


@contextmanager
def _workspace(workspace):
    old = pipeline.PROJECT
    pipeline.PROJECT = Path(workspace).resolve()
    try:
        yield pipeline.PROJECT
    finally:
        pipeline.PROJECT = old


def _result(case, run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid run id')
    directory = _safe(case, 'runs/' + run_id)
    receipt = pipeline.read_json(directory/'receipt.json')
    path = directory/'output/results.json'
    expected = receipt.get('outputs', {}).get('output/results.json')
    if not expected or not path.is_file() or pipeline.digest(path) != expected:
        raise ValueError('Result missing or its receipt hash changed: ' + run_id)
    return pipeline.read_json(path)


def _file_changes(entries, workspace):
    changes = []
    for item in entries:
        path = _safe(workspace, item['path'])
        current = pipeline.digest(path) if path.is_file() else None
        if current != item['sha256']:
            changes.append({**item, 'current_sha256': current})
    return changes


def assess_case(entry, workspace):
    case = _safe(workspace, entry['case'])
    baseline_case = _safe(workspace, entry.get('baseline_case', entry['case']))
    old = _result(baseline_case, entry['baseline_run'])
    state = pipeline.status(case)
    latest = state['runs'][-1] if state['runs'] else None
    usable = latest is not None and latest['usable_automatic_evidence']
    row = {'id': entry['id'], 'case': str(case), 'baseline_run': entry['baseline_run'],
           'latest': latest, 'categories': [], 'recompute_required': not usable,
           'numeric_delta': None, 'conclusion_changes': [], 'affected_facts': [],
           'auto_revision_allowed': False, 'review_required': [],
           'conclusion_scope': 'Declared predicates only, not an automated reading of all natural-language claims',
           'note': 'A dry run cannot know new results that have not been computed.'}
    row['layout_changes'] = _file_changes(entry.get('presentation', []), workspace)
    row['guidance_changes'] = _file_changes(entry.get('guidance', []), workspace)
    if row['layout_changes']:
        row['categories'].append('layout'); row['review_required'].append('Rebuild and inspect changed pages')
    if row['guidance_changes']:
        row['categories'].append('guidance'); row['review_required'].append('Review listed rules at declared manuscript locations; do not rewrite the whole paper')
    if not usable:
        row['categories'].append('unknown')
        row['review_required'].append('Run one authorized attempt before claiming numeric changes')
        return row
    run_id = Path(latest['run']).name
    row['candidate_run'] = run_id
    new = _result(case, run_id)
    row['numeric_delta'] = compare_results(old, new, entry.get('tolerances'))
    if row['numeric_delta']['changes']:
        row['categories'].append('numbers')
    try:
        row['conclusion_changes'] = conclusion_changes(old, new, entry.get('conclusions', []))
    except ValueError as exc:
        row['categories'].append('unknown'); row['review_required'].append(str(exc))
    if row['conclusion_changes']:
        row['categories'].append('conclusions')
        row['review_required'].append('Main answer changed: author must revise reasoning before generating prose')
    facts = entry.get('facts')
    if facts:
        from scripts import paper_facts
        manifest = _safe(workspace, facts['manifest'])
        before = paper_facts.resolve(baseline_case, manifest, entry['baseline_run'], workspace=workspace, historical=True)
        after = paper_facts.resolve(case, manifest, run_id, workspace=workspace, historical=True)
        sentences = pipeline.read_json(_safe(workspace, facts['sentence_map'])) if facts.get('sentence_map') else []
        if isinstance(sentences, dict):
            sentences = sentences.get('occurrences', [])
        for key, value in after['facts'].items():
            previous = before['facts'][key]
            if previous['raw'] != value['raw'] or previous['display'] != value['display']:
                row['affected_facts'].append({'key': key, 'old': previous, 'new': value,
                    'occurrences': [s for s in sentences if s.get('key') == key]})
        row['facts_resolved'] = True
        if row['affected_facts']:
            row['review_required'].append('Review changed numbers, comparative wording and conditions before accepting the new candidate')
    else:
        row['facts_resolved'] = False
        if row['numeric_delta']['changes']:
            row['review_required'].append('No semantic facts manifest: numeric matching cannot certify bindings')
    row['auto_revision_allowed'] = bool(facts and entry.get('conclusions')) and not row['conclusion_changes'] and 'unknown' not in row['categories']
    if not row['categories']:
        row['categories'].append('unaffected')
    return row


def changed_pdf_pages(old_pdf, new_pdf, *, scale=1.5):
    """Pixel comparison is a locator for review, not a new visual approval."""
    import pypdfium2 as pdfium
    documents = [pdfium.PdfDocument(str(p)) for p in (old_pdf, new_pdf)]
    changes, pages = [], []
    try:
        for i in range(max(map(len, documents))):
            hashes = []
            for doc in documents:
                if i >= len(doc):
                    hashes.append(None); continue
                page = doc[i]; bitmap = page.render(scale=scale)
                try:
                    pil = bitmap.to_pil()
                    hashes.append({'size': list(pil.size), 'sha256': hashlib.sha256(pil.tobytes()).hexdigest()})
                finally:
                    bitmap.close(); page.close()
            pages.append({'page': i+1, 'old': hashes[0], 'new': hashes[1]})
            if hashes[0] != hashes[1]:
                changes.append(i+1)
    finally:
        for doc in documents:
            doc.close()
    return {'changed_pages': changes, 'pages': pages, 'scale': scale,
            'visual_review': 'required on changed pages; pixel equality alone does not establish science'}


def run_paper_driver(spec, case, run_id, destination, workspace):
    """Execute an explicitly reviewed local adapter with fixed argv, never a shell."""
    driver = _safe(workspace, spec['path'])
    if not driver.is_file() or pipeline.digest(driver) != spec.get('sha256'):
        raise ValueError('Paper driver hash mismatch; review the actual adapter first')
    dependencies = spec.get('dependencies', [])
    if (not isinstance(dependencies, list) or any(not isinstance(item, dict)
            or not isinstance(item.get('path'), str)
            or not isinstance(item.get('sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', item['sha256']) for item in dependencies)):
        raise ValueError('Paper driver dependencies need paths and SHA256 hashes')
    if _file_changes(dependencies, workspace):
        raise ValueError('Paper driver dependency hash mismatch; review declared helpers first')
    if destination.exists():
        raise FileExistsError(destination)
    timeout = spec.get('timeout_seconds', 120)
    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise ValueError('Paper driver timeout must be 1..300 seconds')
    command = [sys.executable, str(driver), '--case', str(case), '--run-id', run_id,
               '--output', str(destination)]
    run = subprocess.run(command, cwd=workspace, capture_output=True, timeout=timeout)
    if pipeline.digest(driver) != spec['sha256']:
        raise ValueError('Paper adapter changed during execution')
    if _file_changes(dependencies, workspace):
        raise ValueError('Paper driver dependency changed during execution')
    if run.returncode:
        raise ValueError('Paper adapter failed: ' + run.stderr.decode('utf-8', errors='replace'))
    return {'argv': command, 'exit_code': run.returncode,
            'stdout': run.stdout.decode('utf-8', errors='replace'), 'adapter_sha256': spec['sha256'],
            'dependencies': dependencies}


def refresh(manifest, *, workspace=None, dry_run=True, output=None, rebuild=False):
    workspace = Path(workspace or Path.cwd()).resolve()
    data = load_manifest(manifest, workspace)
    report = {'schema': 1, 'dry_run': dry_run, 'cases': [], 'status': 'reported',
              'started_utc': pipeline.stamp(), 'budget_policy': 'Existing workflow only; never reset or bypass'}
    if output is not None:
        output = _safe(workspace, output); output.mkdir(parents=True, exist_ok=False)
    with _workspace(workspace):
        for entry in data['cases']:
            try:
                row = assess_case(entry, workspace)
                if not dry_run and row['recompute_required']:
                    from scripts import workflow
                    case = _safe(workspace, entry['case'])
                    try:
                        receipt = workflow.run(case, workflow.canonical_hash(pipeline.source_snapshot(case)))
                        execution = {'status': receipt['status'], 'run': receipt['run']}
                        row = assess_case(entry, workspace)
                        row['execution'] = execution
                    except Exception as exc:
                        row['execution'] = {'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'}
                if rebuild and not dry_run and row['auto_revision_allowed'] and output is not None:
                    from scripts import paper_facts, paper_template
                    facts = entry['facts']; revision = output/entry['id']/'revision'
                    revision.parent.mkdir(parents=True, exist_ok=True)
                    if facts.get('driver'):
                        adapter = run_paper_driver(facts['driver'], _safe(workspace, entry['case']),
                                                  row['candidate_run'], revision, workspace)
                        expanded = pipeline.read_json(revision/'facts-resolution.json')
                        row['paper_adapter'] = adapter
                    else:
                        expanded = paper_facts.expand(_safe(workspace, facts['source']), revision,
                            _safe(workspace, facts['manifest']), case=_safe(workspace, entry['case']),
                            run_id=row['candidate_run'], workspace=workspace, historical=True)
                    build_dir = output/entry['id']/'compiled'
                    paper_template.compile_paper(revision/'paper.tex', entry.get('contest', 'mcm'), build_dir)
                    row['revision'] = {'source': str(revision), 'pdf': str(build_dir/'paper.pdf'),
                                       'expansion': expanded, 'new_review_required': True}
                    if facts.get('baseline_pdf'):
                        row['visual_delta'] = changed_pdf_pages(_safe(workspace, facts['baseline_pdf']), build_dir/'paper.pdf')
                report['cases'].append(row)
            except Exception as exc:
                report['cases'].append({'id': entry.get('id'), 'categories': ['unknown'],
                    'status': 'failed', 'error': f'{type(exc).__name__}: {exc}', 'auto_revision_allowed': False})
    report['ended_utc'] = pipeline.stamp()
    if any(r.get('status') == 'failed' or r.get('execution', {}).get('status') == 'failed' for r in report['cases']):
        report['status'] = 'failed'
    if output is not None:
        pipeline.save(output/'report.json', report)
        for i, row in enumerate(report['cases'], 1):
            lines = [f"# {row['id']}", '', '状态：' + ', '.join(row['categories']),
                     '', '需要重算：' + str(row.get('recompute_required', 'unknown')),
                     '数字变化：' + ('未计算，未知' if row.get('numeric_delta') is None else str(len(row['numeric_delta']['changes'])) + ' fields'),
                     '结论变化：' + str(len(row.get('conclusion_changes', []))), '', '复查：']
            lines += ['- ' + x for x in row.get('review_required', [])]
            if row.get('error'):
                lines.append('- ' + row['error'])
            (output/f'case-{i}.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true', help='Read-only computations; default')
    parser.add_argument('--execute', action='store_true', help='Use an already authorized workflow attempt')
    parser.add_argument('--rebuild', action='store_true', help='Generate a new fact-bound candidate; never freeze it')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.dry_run and args.execute:
        parser.error('--dry-run and --execute are mutually exclusive')
    destination = _safe(args.workspace.resolve(), args.output) if args.output is not None else args.workspace.resolve()/'outputs/refresh'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8])
    report = refresh(args.cases, workspace=args.workspace, dry_run=not args.execute,
                     rebuild=args.rebuild, output=destination)
    print(json.dumps({'status': report['status'], 'report': str(destination/'report.json'),
                      'cases': [{k: row.get(k) for k in ('id', 'categories', 'recompute_required')} for row in report['cases']]}, ensure_ascii=True))
    return 1 if report['status'] == 'failed' else 0


if __name__ == '__main__':
    sys.exit(main())
