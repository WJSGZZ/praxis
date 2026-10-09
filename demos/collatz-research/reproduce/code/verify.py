"""Independent certificate checker using different extremum/count recurrences."""
import copy
import json
import math
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(ok, why):
    if not ok:
        raise ValueError(why)


def extrema_dp(cap):
    """Keep maximum offset among surviving words, not mechanical-word formula."""
    powers = [3**q for q in range(cap+1)]
    survivors = {0: 0}
    crossing = {}
    for k in range(1, cap+1):
        nxt = {}
        for q, b in survivors.items():
            for bit in (0, 1):
                qq = q+bit
                bb = 3*b+(1 << (k-1)) if bit else b
                if powers[qq] < 1 << k:
                    old = crossing.get(k)
                    require(old is None or old[0] == qq, 'Nonunique crossing q')
                    crossing[k] = (qq, bb if old is None else max(old[1],bb))
                else:
                    nxt[qq] = max(nxt.get(qq,-1),bb)
        survivors = nxt
    return crossing


def renewal_counts(cap, crossing):
    """First-passage decomposition of binomial counts, no forward-state DP."""
    first = {}
    checkpoints = {}
    for k in range(1, cap+1):
        if k in crossing:
            q = crossing[k][0]
            value = math.comb(k-1,q) if q <= k-1 else 0
            for j, L in first.items():
                delta = q-crossing[j][0]
                if 0 <= delta <= k-1-j:
                    value -= L*math.comb(k-1-j,delta)
            require(value >= 0, 'Negative first passage count')
            first[k] = value
        R = (1 << k)-sum(L*(1 << (k-j)) for j,L in first.items())
        require(R > 0, 'No all-ones survivor')
        if k in (16,32,64,128,256,512,1024):
            checkpoints[k] = (R,first.get(k,0),sum(first.values()))
    return first, checkpoints


def trajectory_scan(H,cap):
    failures, censored = [], []
    histogram = {}
    for n in range(2,H+1):
        x, q = n, 0
        for k in range(1,cap+1):
            if x & 1:
                q += 1
                x = (3*x+1)//2
            else:
                x //= 2
            if pow(3,q) < pow(2,k):
                histogram[k] = histogram.get(k,0)+1
                if x >= n:
                    failures.append((n,k,x))
                break
        else:
            censored.append(n)
    return failures,censored,histogram


def validate_object(cert, expected, checkpoints, scan):
    require(cert['cap'] == 1024, 'Wrong cap')
    require(len(cert['envelope_rows']) == len(expected), 'Incomplete envelope set')
    seen = set()
    H = 0
    for row in cert['envelope_rows']:
        k = row['k']
        require(k in expected and k not in seen, 'Missing/duplicate crossing depth')
        seen.add(k)
        q,B = expected[k]
        A,D = 3**q,1 << k
        bound = B//(D-A)
        H = max(H,bound)
        require((row['q'],row['A'],row['D'],row['maximum_offset'],row['exception_floor'],row['prefix_maximum_floor']) == (q,A,D,B,bound,H),'Bad extremum/threshold')
    require(seen == set(expected),'Missing crossing')
    require([row['k'] for row in cert['checkpoints']] == sorted(checkpoints),'Missing checkpoint')
    for row in cert['checkpoints']:
        k = row['k']
        R,L,total = checkpoints[k]
        rho = Fraction(R,1 << k)
        h = max(B//((1 << j)-3**q) for j,(q,B) in expected.items() if j<=k)
        require((row['unresolved_words'],row['first_crossing_words'],row['cumulative_leaf_words'],row['unresolved_density_numerator'],row['unresolved_density_denominator'],row['H']) == (R,L,total,rho.numerator,rho.denominator,h),'Bad count/density/checkpoint bound')
    record = cert['finite_scan']
    require(record['domain'] == [2,H] and record['initial_values'] == H-1 and record['cap'] ==1024,'Wrong finite scan coverage')
    failures,censored,histogram = scan
    require(record['failures'] == failures == [],'CST exception')
    require(record['tau_above_cap'] == censored,'Wrong censoring')
    require({int(k):v for k,v in record['histogram'].items()} == histogram,'Wrong finite histogram')
    return H


def main():
    start = time.perf_counter()
    cert = json.loads((ROOT/'runs/certificate.json').read_text())
    extrema = extrema_dp(1024)
    first,counts = renewal_counts(1024,extrema)
    H = max(B//((1 << j)-3**q) for j,(q,B) in extrema.items())
    scan = trajectory_scan(H,1024)
    validate_object(cert,extrema,counts,scan)
    mutations = []
    for name,edit in [
        ('wrong_offset',lambda c:c['envelope_rows'][0].__setitem__('maximum_offset',1)),
        ('wrong_threshold',lambda c:c['envelope_rows'][-1].__setitem__('exception_floor',0)),
        ('missing_crossing',lambda c:c['envelope_rows'].pop()),
        ('wrong_density',lambda c:c['checkpoints'][-1].__setitem__('unresolved_density_numerator',0)),
        ('finite_domain_shortened',lambda c:c['finite_scan'].__setitem__('domain',[2,H-1])),
        ('wrong_tau_histogram',lambda c:c['finite_scan']['histogram'].__setitem__('1',0)),
    ]:
        bad = copy.deepcopy(cert)
        edit(bad)
        try:
            validate_object(bad,extrema,counts,scan)
        except ValueError:
            mutations.append(dict(name=name,rejected=True))
        else:
            raise RuntimeError(f'Accepted mutation {name}')
    result = dict(status='passed',cap=1024,H=H,crossing_lengths=len(extrema),
                  maximum_offset_method='independent max-plus state dynamic program',
                  count_method='independent binomial first-passage renewal',
                  finite_domain=[2,H],finite_failures=scan[0],tau_above_cap=scan[1],
                  mutations=mutations,seconds=time.perf_counter()-start)
    (ROOT/'runs/independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
