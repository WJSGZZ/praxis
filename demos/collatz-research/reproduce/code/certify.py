"""Exact first-crossing envelopes and compressed coefficient certificates.

No code from outside sources is imported. Standard-library arithmetic only.
"""
import hashlib
import json
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
K = 1024
CHECKPOINTS = (16, 32, 64, 128, 256, 512, 1024)


def barriers(cap):
    """h[j]=min q with3**q >=2**j, using exact comparisons."""
    h = [0]
    p, q = 1, 0
    for j in range(1, cap+1):
        while p < 1 << j:
            q += 1
            p *= 3
        h.append(q)
    return h


def envelope_rows(cap):
    h = barriers(cap)
    # A,B are for the unique prefix with cumulative odd counts h[j].
    A, B = 1, 0
    rows = []
    H = 0
    for k in range(1, cap+1):
        D = 1 << k
        # Every first crossing ends even, with q=h[k-1].
        if A < D:
            q = h[k-1]
            floor = B // (D-A)
            H = max(H, floor)
            rows.append(dict(k=k, q=q, A=A, D=D, maximum_offset=B,
                             exception_floor=floor, prefix_maximum_floor=H))
        if h[k] > h[k-1]:
            B = 3*B + (1 << (k-1))
            A *= 3
        assert A == 3**h[k]
    return rows, h


def count_prefixes(cap):
    powers = [3**q for q in range(cap+1)]
    surviving = {0: 1}
    leaves = 0
    rows = []
    state_updates = 0
    for k in range(1, cap+1):
        nxt = {}
        first = 0
        for q, count in surviving.items():
            for qq in (q, q+1):
                state_updates += 1
                if powers[qq] < 1 << k:
                    first += count
                else:
                    nxt[qq] = nxt.get(qq, 0)+count
        assert sum(nxt.values())+first == 2*sum(surviving.values())
        surviving = nxt
        leaves += first
        if k in CHECKPOINTS:
            R = sum(surviving.values())
            rho = Fraction(R, 1 << k)
            rows.append(dict(k=k, unresolved_words=R, first_crossing_words=first,
                             cumulative_leaf_words=leaves,
                             unresolved_density_numerator=rho.numerator,
                             unresolved_density_denominator=rho.denominator,
                             unresolved_density_float=float(rho),
                             active_states=len(surviving)))
    return rows, state_updates


def scan_exceptions(H, cap):
    histogram = {}
    unresolved, failures = [], []
    max_tau, maximizers, evaluations = 0, [], 0
    for n in range(2, H+1):
        x, coefficient_numerator = n, 1
        for k in range(1, cap+1):
            if x % 2:
                coefficient_numerator *= 3
                x = (3*x+1)//2
            else:
                x //= 2
            evaluations += 1
            if coefficient_numerator < 1 << k:
                histogram[k] = histogram.get(k, 0)+1
                if x >= n:
                    failures.append(dict(n=n, tau=k, value=x))
                if k > max_tau:
                    max_tau, maximizers = k, [n]
                elif k == max_tau:
                    maximizers.append(n)
                break
        else:
            unresolved.append(n)
    return dict(domain=[2,H], initial_values=max(0,H-1), cap=cap,
                failures=failures, tau_above_cap=unresolved, max_tau=max_tau,
                maximizers=maximizers, iterations=evaluations,
                histogram=histogram)


def main():
    start = time.perf_counter()
    envelopes, h = envelope_rows(K)
    counts, updates = count_prefixes(K)
    H = max(row['exception_floor'] for row in envelopes)
    scan = scan_exceptions(H, K)
    assert not scan['failures']
    # tau>cap would be outside the theorem, not a failure of CST.
    checkpoints = []
    for row in counts:
        k = row['k']
        compatible = [e for e in envelopes if e['k'] <= k]
        best = max(compatible, key=lambda e:e['exception_floor'])
        checkpoints.append(dict(**row, H=best['exception_floor'], H_attained_at=best['k']))
    result = dict(map='shortcut Collatz', cap=K, envelope_rows=envelopes,
                  barriers=h, checkpoints=checkpoints, finite_scan=scan,
                  state_updates=updates, seconds=time.perf_counter()-start,
                  theorem_scope='Every n>1 with coefficient stopping time tau(n)<=1024 has actual first descent sigma(n)=tau(n). No assertion for tau>1024 or infinite.',
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (ROOT/'runs/certificate.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('cap','checkpoints','finite_scan','state_updates','seconds')},indent=2))


if __name__ == '__main__':
    main()
