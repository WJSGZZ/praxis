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


def aggregate(files: list[Path]) -> dict:
    per_paper: dict[str, list[float]] = {}
    dims: dict[str, dict[str, list[float]]] = {}
    for path in files:
        for item in json.loads(Path(path).read_text()):
            per_paper.setdefault(item['paper'], []).append(percent(item['scores']))
            for k, v in item['scores'].items():
                dims.setdefault(item['paper'], {}).setdefault(k, []).append(v)
    out = {}
    for paper, values in per_paper.items():
        spread = {k: max(v) - min(v) for k, v in dims[paper].items()}
        out[paper] = dict(judges=len(values), percent_each=[round(v, 1) for v in values], percent_mean=round(sum(values) / len(values), 1),
                          percent_range=round(max(values) - min(values), 1), unstable_dimensions=sorted(k for k, d in spread.items() if d > 1))
    return out


if __name__ == '__main__':
    print(json.dumps(aggregate([Path(a) for a in sys.argv[1:]]), ensure_ascii=False, indent=1))
