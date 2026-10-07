"""A record of the routes tried on a problem: candidates, attacks, deaths, merges, and why one was chosen.

The graph is plain JSON so it can live in the task record. It does not search for routes; it keeps the search honest:
a route cannot be killed without a reason, chosen without surviving an attack, or chosen while its assumptions have no fallback."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

STATUS = ('open', 'exploring', 'killed', 'merged', 'chosen')
OUTCOME = ('survived', 'weakened', 'killed')
EVIDENCE = ('derived', 'cited', 'checked', 'assumed', 'unknown')
CRITERIA = ('assumptions', 'information', 'tractability', 'robustness', 'verifiability', 'explanatory_power')


def new_graph(question: str) -> dict:
    if not question.strip():
        raise ValueError('A route graph starts from a question')
    return dict(question=question, structures={}, paths={}, assumptions={}, attacks=[], partial_results={}, edges=[], log=[])


def _need(g, kind, key):
    if key not in g[kind]:
        raise KeyError(f'Unknown {kind[:-1]}: {key}')
    return g[kind][key]


def _fresh(g, kind, key):
    if key in g[kind]:
        raise ValueError(f'{kind[:-1]} already exists: {key}')


def add_structure(g, key, text, *, evidence='assumed'):
    """A structure noticed in the problem (conservation law, graph, convexity, recursion...), with how it was established."""
    _fresh(g, 'structures', key)
    if evidence not in EVIDENCE:
        raise ValueError(f'evidence must be one of {EVIDENCE}')
    g['structures'][key] = dict(text=text, evidence=evidence)


def add_assumption(g, key, text, *, evidence='assumed', if_false=''):
    """An assumption a route relies on, with its evidence level and what to do if it fails."""
    _fresh(g, 'assumptions', key)
    if evidence not in EVIDENCE:
        raise ValueError(f'evidence must be one of {EVIDENCE}')
    g['assumptions'][key] = dict(text=text, evidence=evidence, if_false=if_false)


def add_path(g, key, title, *, structure=None, assumptions=(), needs='', scores=None, parent=None, note=''):
    """A candidate route. scores: optional 1-5 ratings on CRITERIA, each needing a reason elsewhere (note or attack)."""
    _fresh(g, 'paths', key)
    for a in assumptions:
        _need(g, 'assumptions', a)
    if structure is not None:
        _need(g, 'structures', structure)
    if scores:
        bad = set(scores) - set(CRITERIA)
        if bad or any(not 1 <= v <= 5 for v in scores.values()):
            raise ValueError(f'scores must use {CRITERIA} with values 1-5')
    g['paths'][key] = dict(title=title, structure=structure, assumptions=list(assumptions), needs=needs, scores=dict(scores or {}),
                           status='open', reason='', note=note, parent=parent)
    if parent:
        _need(g, 'paths', parent)
        g['edges'].append([parent, key, 'refines'])


def attack(g, key, claim, method, outcome, evidence=''):
    """Try to break a route: the claim being attacked, how, and what happened. 'killed' also kills the route."""
    p = _need(g, 'paths', key)
    if outcome not in OUTCOME:
        raise ValueError(f'outcome must be one of {OUTCOME}')
    if not claim.strip() or not method.strip():
        raise ValueError('An attack names the claim and the method')
    g['attacks'].append(dict(path=key, claim=claim, method=method, outcome=outcome, evidence=evidence))
    if outcome == 'killed':
        p['status'], p['reason'] = 'killed', evidence or claim
    elif p['status'] == 'open':
        p['status'] = 'exploring'


def kill(g, key, reason):
    p = _need(g, 'paths', key)
    if not reason.strip():
        raise ValueError('A route is killed for a stated reason')
    p['status'], p['reason'] = 'killed', reason


def keep_result(g, key, statement, *, status='checked', source_path=None, reusable_in=()):
    """A partial result worth keeping even if its route dies (a bound, an identity, a failed approach's lesson)."""
    _fresh(g, 'partial_results', key)
    if status not in EVIDENCE:
        raise ValueError(f'status must be one of {EVIDENCE}')
    if source_path:
        _need(g, 'paths', source_path)
    g['partial_results'][key] = dict(statement=statement, status=status, source=source_path, reusable_in=list(reusable_in))


def merge(g, keys, new_key, title, how):
    """A hybrid route built from surviving parts of others; the parts are marked merged, not erased."""
    for k in keys:
        _need(g, 'paths', k)
    if len(keys) < 2 or not how.strip():
        raise ValueError('Merging needs two or more routes and a stated way of combining them')
    assumptions = sorted({a for k in keys for a in g['paths'][k]['assumptions']})
    add_path(g, new_key, title, assumptions=assumptions, note=how)
    for k in keys:
        g['edges'].append([k, new_key, 'merges'])
        if g['paths'][k]['status'] != 'killed':
            g['paths'][k]['status'] = 'merged'


def choose(g, key, why):
    """Select a route. Requires: two other routes considered, a surviving attack, and a fallback for each assumption."""
    p = _need(g, 'paths', key)
    issues = check_choice(g, key)
    if issues:
        raise ValueError('Cannot choose ' + key + ': ' + '; '.join(issues))
    p['status'], p['reason'] = 'chosen', why
    for k, q in g['paths'].items():
        if k != key and q['status'] == 'chosen':
            q['status'] = 'open'


def check_choice(g, key):
    p = _need(g, 'paths', key)
    issues = []
    others = [k for k in g['paths'] if k != key]
    if len(others) < 2:
        issues.append('fewer than two alternative routes were considered')
    if not any(a['path'] == key and a['outcome'] == 'survived' for a in g['attacks']):
        issues.append('no attack on this route has been survived')
    if any(a['path'] == key and a['outcome'] == 'killed' for a in g['attacks']):
        issues.append('an attack killed this route')
    for a in p['assumptions']:
        if not g['assumptions'][a]['if_false'].strip():
            issues.append(f'assumption {a} has no fallback if it fails')
    return issues


def validate(g) -> list[str]:
    """Problems with the record as a whole."""
    issues = []
    for k, p in g['paths'].items():
        if p['status'] == 'killed' and not p['reason'].strip():
            issues.append(f'{k}: killed without a reason')
        if p['status'] == 'chosen':
            issues += [f'{k}: {m}' for m in check_choice(g, k)]
    for k, r in g['partial_results'].items():
        if r['source'] and r['source'] not in g['paths']:
            issues.append(f'partial result {k}: unknown source route')
    chosen = [k for k, p in g['paths'].items() if p['status'] == 'chosen']
    if len(chosen) > 1:
        issues.append('more than one route is marked chosen: ' + ', '.join(chosen))
    used = {a for p in g['paths'].values() for a in p['assumptions']}
    for a in g['assumptions']:
        if a not in used:
            issues.append(f'assumption {a} is used by no route')
    return issues


def apply(graph: dict | None, operations: list[dict[str, Any]], *, question: str | None = None) -> dict:
    """Apply operations [{"op": "add_path", ...}, ...] to a copy of the graph; the first call may pass question instead of a graph."""
    g = copy.deepcopy(graph) if graph else new_graph(question or '')
    table = dict(add_structure=add_structure, add_assumption=add_assumption, add_path=add_path, attack=attack, kill=kill,
                 keep_result=keep_result, merge=merge, choose=choose)
    for number, step in enumerate(operations, 1):
        step = dict(step)
        name = step.pop('op', None)
        if name not in table:
            raise ValueError(f'operation {number}: unknown op {name!r}')
        try:
            table[name](g, **step)
        except (KeyError, ValueError, TypeError) as error:
            raise type(error)(f'operation {number} ({name}): {error}') from error
        g['log'].append(name)
    return dict(graph=g, issues=validate(g), trace=trace_markdown(g))


def trace_markdown(g) -> str:
    """The route record as a readable trace: what was considered, why routes died, what was chosen, what depends on what."""
    out = [f'# 路线记录：{g["question"]}', '']
    if g['structures']:
        out += ['## 发现的结构', *[f'- **{k}**（{s["evidence"]}）：{s["text"]}' for k, s in g['structures'].items()], '']
    out += ['## 候选路线']
    for k, p in g['paths'].items():
        out.append(f'### {k}：{p["title"]}  〔{p["status"]}〕')
        if p['structure']:
            out.append(f'- 依据的结构：{p["structure"]}')
        if p['needs']:
            out.append(f'- 需要的信息：{p["needs"]}')
        if p['assumptions']:
            out.append('- 假设：' + '；'.join(f'{a}（{g["assumptions"][a]["evidence"]}；若不成立：{g["assumptions"][a]["if_false"] or "未写"}）' for a in p['assumptions']))
        if p['scores']:
            out.append('- 比较：' + '，'.join(f'{c} {v}' for c, v in p['scores'].items()))
        for a in g['attacks']:
            if a['path'] == k:
                out.append(f'- 攻击〔{a["outcome"]}〕：{a["claim"]}；方法：{a["method"]}' + (f'；证据：{a["evidence"]}' if a['evidence'] else ''))
        if p['reason']:
            out.append(f'- 结论：{p["reason"]}')
        if p['note']:
            out.append(f'- 说明：{p["note"]}')
        out.append('')
    merges = [e for e in g['edges'] if e[2] == 'merges']
    if merges:
        out += ['## 合并', *[f'- {a} → {b}' for a, b, _ in merges], '']
    if g['partial_results']:
        out += ['## 保留的中间结果', *[f'- **{k}**（{r["status"]}）：{r["statement"]}' + (f'；可用于：{", ".join(r["reusable_in"])}' if r['reusable_in'] else '') for k, r in g['partial_results'].items()], '']
    issues = validate(g)
    if issues:
        out += ['## 记录中的问题', *[f'- {i}' for i in issues], '']
    return '\n'.join(out)


def save(g: dict, path: Path) -> None:
    Path(path).write_text(json.dumps(g, ensure_ascii=False, indent=2))


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text())
