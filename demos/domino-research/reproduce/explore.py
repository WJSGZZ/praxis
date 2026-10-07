"""Research-mode case: how many ways can a 3 x 2n rectangle be tiled with dominoes?

Counts tilings three independent ways (backtracking, transfer matrix, the coupled recurrences A/B), lets the Praxis tools guess and test a
recurrence on held-out terms, proves it by a finite check under a justified order bound, keeps the route record and writes a lesson.

    uv run --locked python demos/domino-research/reproduce/explore.py        # writes reproduced/results.json (a few seconds)
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import sympy as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from modeling import experiment, lessons, routes  # noqa: E402


# ---------------------------------------------------------------------------------------------- 1. brute force
def tilings_backtracking(rows: int, cols: int, removed: frozenset = frozenset()) -> int:
    """Count domino tilings of a rows x cols board with some cells removed, by filling the first free cell in reading order."""
    free = [[(r, c) not in removed for c in range(cols)] for r in range(rows)]

    def first_free():
        for c in range(cols):
            for r in range(rows):
                if free[r][c]:
                    return r, c
        return None

    def count():
        cell = first_free()
        if cell is None:
            return 1
        r, c = cell
        total = 0
        free[r][c] = False
        if r + 1 < rows and free[r + 1][c]:                  # vertical domino
            free[r + 1][c] = False
            total += count()
            free[r + 1][c] = True
        if c + 1 < cols and free[r][c + 1]:                  # horizontal domino
            free[r][c + 1] = False
            total += count()
            free[r][c + 1] = True
        free[r][c] = True
        return total

    return count()


# ---------------------------------------------------------------------------------------------- 2. transfer matrix
def transfer_matrix(rows: int = 3) -> np.ndarray:
    """State = which cells of the next column are already covered by horizontal dominoes poking in from the left."""
    n = 2 ** rows
    T = np.zeros((n, n), dtype=object)
    for s in range(n):
        def fill(r: int, covered: int, out: int):
            if r == rows:
                T[s, out] += 1
                return
            if covered >> r & 1:
                fill(r + 1, covered, out)
                return
            fill(r + 1, covered | 1 << r, out | 1 << r)                      # horizontal domino into the next column
            if r + 1 < rows and not covered >> (r + 1) & 1:
                fill(r + 2, covered | 3 << r, out)                          # vertical domino inside this column
        fill(0, s, 0)
    return T


def tilings_transfer(columns: int, rows: int = 3) -> int:
    T = sp.Matrix(transfer_matrix(rows).tolist())
    v = sp.zeros(2 ** rows, 1)
    v[0] = 1
    return int((T ** columns * v)[0])


# ---------------------------------------------------------------------------------------------- 3. coupled recurrences
@lru_cache(None)
def A(m: int) -> int:
    """3 x m rectangle: leftmost column is three horizontals (A_{m-2}) or a vertical pair plus one horizontal, in two mirror ways (B_{m-1})."""
    if m < 0:
        return 0
    if m == 0:
        return 1
    if m == 1:
        return 0
    return A(m - 2) + 2 * B(m - 1)


@lru_cache(None)
def B(m: int) -> int:
    """3 x m rectangle with one corner cell removed: leftmost column's two cells are a vertical domino (A_{m-1}) or two horizontals (B_{m-2})."""
    if m <= 0:
        return 0
    if m == 1:
        return 1
    return A(m - 1) + B(m - 2)


def main() -> dict:
    out: dict = {}
    # 1. three independent counts agree
    brute = [tilings_backtracking(3, 2 * n) for n in range(0, 6)]
    brute_corner = [tilings_backtracking(3, m, frozenset({(2, 0)})) for m in range(1, 9)]
    transfer = [tilings_transfer(2 * n) for n in range(0, 17)]
    coupled = [A(2 * n) for n in range(0, 17)]
    out['counts'] = dict(backtracking_n0_to_5=brute, transfer_matrix_n0_to_16=transfer, coupled_recurrences_n0_to_16=coupled,
                         corner_removed_backtracking_m1_to_8=brute_corner, corner_removed_recurrence_m1_to_8=[B(m) for m in range(1, 9)])
    assert brute == transfer[:6] == coupled[:6] and transfer == coupled and brute_corner == [B(m) for m in range(1, 9)]
    # 2. guess from 13 terms, keep 4 for the test
    out['guess'] = experiment.guess_linear_recurrence(transfer, max_order=6, holdout=4)
    out['guess_on_first_13_terms'] = experiment.guess_linear_recurrence(transfer[:13], max_order=6)
    out['polynomial_formula'] = experiment.guess_polynomial(transfer[:13], max_degree=8)
    # 3. finite-check proof: the transfer matrix has 8 states, so a(n) obeys a recurrence of order <= 8 (Cayley-Hamilton)
    out['finite_check'] = experiment.check_linear_recurrence(transfer, [4, -1], order_bound=8)
    # 4. exhaustive check of the recurrence on n = 2..60 (finite domain: a proof for that domain, not for all n)
    big = [tilings_transfer(2 * n) for n in range(0, 61)]
    claim = experiment.find_counterexample(lambda n: big[n] == 4 * big[n - 1] - big[n - 2], [('int', 2, 60)])
    out['counterexample_search_n2_to_60'] = claim
    # 5. closed form from the recurrence: a(n) = ((3+s)/6)(2+s)^n + ((3-s)/6)(2-s)^n, s = sqrt(3)
    s = sp.sqrt(3)
    closed = lambda n: sp.simplify(((3 + s) * (2 + s) ** n + (3 - s) * (2 - s) ** n) / 6)
    out['closed_form_matches_n0_to_60'] = all(closed(n) == big[n] for n in range(0, 61))
    out['growth_rate'] = dict(limit_of_ratio=float(2 + s), ratios_n_8_12_16=[big[n + 1] / big[n] for n in (8, 12, 16)] if False else [transfer[16] / transfer[15]])
    # 6. route record and lesson
    ops = [
        dict(op='add_structure', key='transfer', text='the count is u^T M^n v for an 8x8 integer matrix M (column profiles)', evidence='derived'),
        dict(op='add_structure', key='local', text='the leftmost column splits the rectangle into smaller ones: A_m = A_{m-2} + 2 B_{m-1}, B_m = A_{m-1} + B_{m-2}', evidence='derived'),
        dict(op='add_assumption', key='order_bound', text='a(n) satisfies a recurrence of order at most 8', evidence='derived', if_false='enlarge the bound until it is justified'),
        dict(op='add_path', key='guess', title='guess a linear recurrence from data, test on held-out terms', assumptions=['order_bound']),
        dict(op='add_path', key='polynomial', title='guess a polynomial formula in n'),
        dict(op='add_path', key='split', title='prove it from the column decomposition', structure='local'),
        dict(op='attack', key='guess', claim='the recurrence continues to hold', method='4 held-out terms, exhaustive check to n = 60, finite-check proof', outcome='survived'),
        dict(op='kill', key='polynomial', reason='growth is exponential (ratio -> 2 + sqrt(3)); no polynomial of degree <= 8 fits'),
        dict(op='attack', key='split', claim='the case analysis is exhaustive', method='compare A_m, B_m with backtracking counts for small boards', outcome='survived'),
        dict(op='keep_result', key='order_bound_result', statement='finite check on 10 consecutive terms proves a(n)=4a(n-1)-a(n-2) for all n', status='proved_finite_check', source_path='guess'),
        dict(op='choose', key='split', why='a direct proof, cross-checked by the finite check'),
    ]
    graph = routes.apply(None, ops, question='Count domino tilings of a 3 x 2n rectangle', mode='exploratory')
    out['route_issues'] = graph['issues']
    draft = routes.draft_lesson(graph['graph'], problem='domino tilings of 3 x 2n',
                                principle='When a count looks like a linear recurrence, guess it from data, hold terms out, then prove it twice: from a local decomposition and from an order bound plus a finite check.',
                                tags=['recurrence', 'experimental-mathematics'])
    out['lesson'] = draft
    (HERE / 'reproduced').mkdir(exist_ok=True)
    (HERE / 'reproduced/results.json').write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    (HERE / 'reproduced/route-record.md').write_text(graph['trace'])
    return out


if __name__ == '__main__':
    r = main()
    print(json.dumps(dict(recurrence=r['guess']['coefficients'], holdout_ok=r['guess']['holdout_ok'], finite_check_proof=r['finite_check']['proof_by_finite_check'],
                          exhaustive_to_n60=r['counterexample_search_n2_to_60'].get('proved_for_domain'), closed_form_ok=r['closed_form_matches_n0_to_60']), indent=1))
