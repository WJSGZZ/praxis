"""Combine judge score files (see judging.md) into weighted percentages with the spread between judges.

    uv run --locked python -m evals.aggregate judge1.json judge2.json ...      # each file: a JSON list of judge outputs"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WEIGHTS = {'coverage': 10, 'assumptions': 15, 'model': 15, 'correctness': 25, 'robustness': 10, 'writing': 10, 'verifiability': 15}


def percent(scores: dict) -> float:
    missing = set(WEIGHTS) - set(scores)
    if missing:
        raise ValueError(f'Missing dimensions: {sorted(missing)}')
    bad = {k: v for k, v in scores.items() if k in WEIGHTS and not 0 <= v <= 4}
    if bad:
        raise ValueError(f'Scores must lie in 0-4: {bad}')
    return 100 * sum(WEIGHTS[k] * scores[k] / 4 for k in WEIGHTS) / sum(WEIGHTS.values())


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


def aggregate(files: list[Path]) -> dict:
    per_paper: dict[str, list[float]] = {}
    dims: dict[str, dict[str, list[float]]] = {}
    basis: dict[str, dict[str, set]] = {}
    for path in files:
        for item in json.loads(Path(path).read_text()):
            scores = dimension_scores(item)
            for k, b in item.get('basis', {}).items():
                basis.setdefault(item['paper'], {}).setdefault(b, set()).add(k)
            per_paper.setdefault(item['paper'], []).append(percent(scores))
            for k, v in scores.items():
                dims.setdefault(item['paper'], {}).setdefault(k, []).append(v)
    out = {}
    for paper, values in per_paper.items():
        spread = {k: max(v) - min(v) for k, v in dims[paper].items()}
        out[paper] = dict(judges=len(values), percent_each=[round(v, 1) for v in values], percent_mean=round(sum(values) / len(values), 1),
                          percent_range=round(max(values) - min(values), 1), unstable_dimensions=sorted(k for k, d in spread.items() if d > 1),
                          basis={b: sorted(v) for b, v in basis.get(paper, {}).items()})
    return out


if __name__ == '__main__':
    print(json.dumps(aggregate([Path(a) for a in sys.argv[1:]]), ensure_ascii=False, indent=1))
