"""Combine judge score files (see judging.md) into weighted percentages with the spread between judges.

    uv run --locked python -m evals.aggregate [--contest=cumcm|mcm] judge1.json judge2.json ...      # each file: a JSON list of judge outputs"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WEIGHTS = {'coverage': 10, 'assumptions': 15, 'model': 15, 'correctness': 25, 'robustness': 10, 'writing': 10, 'verifiability': 15}


PROFILES = json.loads((Path(__file__).with_name('profiles.json')).read_text())
CONTEST_WEIGHTS = {k: v['weights'] for k, v in PROFILES.items() if k != 'general'}      # per-contest data lives in profiles.json, with its sources


def percent(scores: dict, weights: dict | None = None) -> float:
    weights = weights or WEIGHTS
    missing = set(weights) - set(scores)
    if missing:
        raise ValueError(f'Missing dimensions: {sorted(missing)}')
    bad = {k: v for k, v in scores.items() if k in weights and not 0 <= v <= 4}
    if bad:
        raise ValueError(f'Scores must lie in 0-4: {bad}')
    return 100 * sum(weights[k] * scores[k] / 4 for k in weights) / sum(weights.values())


def dimension_scores(item: dict) -> dict:
    """0-4 scores for one judge output: given directly (`scores`) or computed from the checklist (4 x share of met items, to the nearest half, plus a documented adjust of at most 1)."""
    if 'scores' in item:
        return item['scores']
    out = {}
    for dim in WEIGHTS:
        items = item.get('checklist', {}).get(dim)
        if not items:
            raise ValueError(f'No checklist for {dim}')
        base = round(4 * sum(bool(v['met']) for v in items.values()) / len(items) * 2) / 2
        adjust = item.get('adjust', {}).get(dim)
        if adjust:
            if not str(adjust.get('reason', '')).strip() or abs(adjust['value']) > 1:
                raise ValueError(f'adjust for {dim} needs a reason and a value within 1')
            base += adjust['value']
        out[dim] = min(4.0, max(0.0, base))
    return out


def aggregate(files: list[Path], contest: str | None = None) -> dict:
    if contest and contest not in PROFILES:
        raise ValueError(f'No profile for {contest!r}; known: {sorted(PROFILES)}. Add one to evals/profiles.json, or omit --contest for the general weights.')
    weights = PROFILES[contest]['weights'] if contest else WEIGHTS
    per_paper: dict[str, list[float]] = {}
    awards: dict[str, list[dict]] = {}
    dims: dict[str, dict[str, list[float]]] = {}
    basis: dict[str, dict[str, set]] = {}
    for path in files:
        for item in json.loads(Path(path).read_text()):
            scores = dimension_scores(item)
            if 'award_estimate' in item:
                awards.setdefault(item['paper'], []).append(item['award_estimate'])
            for k, b in item.get('basis', {}).items():
                basis.setdefault(item['paper'], {}).setdefault(b, set()).add(k)
            per_paper.setdefault(item['paper'], []).append(percent(scores, weights))
            for k, v in scores.items():
                dims.setdefault(item['paper'], {}).setdefault(k, []).append(v)
    out = {}
    for paper, values in per_paper.items():
        spread = {k: max(v) - min(v) for k, v in dims[paper].items()}
        out[paper] = dict(judges=len(values), percent_each=[round(v, 1) for v in values], percent_mean=round(sum(values) / len(values), 1),
                          percent_range=round(max(values) - min(values), 1), unstable_dimensions=sorted(k for k, d in spread.items() if d > 1),
                          basis={b: sorted(v) for b, v in basis.get(paper, {}).items()},
                          award_estimates=awards.get(paper, []))
    return out


if __name__ == '__main__':
    args = sys.argv[1:]
    contest = None
    if args and args[0].startswith('--contest='):
        contest, args = args[0].split('=', 1)[1], args[1:]
    print(json.dumps(aggregate([Path(a) for a in args], contest), ensure_ascii=False, indent=1))
