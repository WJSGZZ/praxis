"""Audit archives, replay extremal cases or qualify the finite banks anew.

Every execution writes a new receipt. Limits are cooperative, checked between
numerical calls, not an operating-system timeout. No optimization is repeated.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
import numpy as np
import scipy
from common_reserve import ROOT, GRIDS, common_reserve_values, replay, model
import check_structure


def run(output, mode, seconds):
    if output.exists():
        raise ValueError('Existing evidence is never overwritten')
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Positive finite time limit required')
    output.parent.mkdir(parents=True, exist_ok=True)
    files = ['common_reserve.py', 'study_common_reserve.py', 'code/model.py',
             'check_structure.py', 'reference/structure-decision.json',
             'reference/common-reserve.json', 'reference/common-reserve.npz',
             'reference/common-reserve-independent.json']
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    hashes = {n: sha(ROOT/n) for n in files}
    start = time.monotonic()
    state = dict(status='started', mode=mode, rows=[], source_sha256=hashes,
                 python=sys.version, scipy=scipy.__version__, seconds_limit=seconds,
                 scope='Finite banks and specified grids; conditional floating-point envelopes, not global optimality, interval-roundoff proof or experimental validation.')

    def save(status):
        state.update(status=status, elapsed_s=time.monotonic()-start)
        output.write_text(json.dumps(state, indent=2)+'\n')

    def budget():
        if time.monotonic()-start >= seconds:
            raise TimeoutError('Common-reserve cumulative time limit')

    save('started')
    try:
        budget()
        archived = common_reserve_values()
        state['policies'] = archived['manifest']['policies']
        if mode == 'audit':
            state['archive_summary'] = {k: archived[k] for k in (
                'objects','groups','volumes','delta_l','crossover','strict_n_greater_than',
                'lower','upper','spread','independent_cases')}
            state['scope'] = 'Receipt/identity/arithmetic audit only; no new numerical replay.'
        elif mode == 'replay-extrema':
            seen = set()
            for group in archived['rows']:
                for metric, choose in [('min_temp',min),('max_temp',max),('max_span',max)]:
                    record = choose(group['records'], key=lambda r: r[metric])
                    identity = (group['structure'],group['design'],tuple(group['grid']),record['prior_index'])
                    if identity in seen:
                        continue
                    seen.add(identity); budget()
                    params = {**model.BASE, **record['parameters']}
                    bank = json.loads((ROOT/'reference/structure-decision.json').read_text())
                    route, capacity = bank['structures'][identity[0]]
                    flows = state['policies'][identity[1]]
                    portable = replay([params], identity[2], route, capacity, flows, budget)[0]
                    budget()
                    independent = check_structure.replay(params, model.network(params, identity[2]),
                        np.array(flows)*params['flow_multiplier'], route, capacity, sample_s=1.)
                    difference = max(abs(portable[k]-record[k]) for k in ('min_temp','max_temp','max_span','water_l'))
                    accepted = (portable['fair_reserve_passed'] and difference < 2e-6 and
                        independent['min_temp'] >= max(39.13,portable['lower_bound_c']-2e-6) and
                        independent['max_temp'] <= min(40.9,portable['upper_bound_c']+2e-6) and
                        independent['max_span'] <= min(1.4,portable['span_bound_c']+4e-6) and
                        independent['instantaneous_balance_residual_w'] < 1e-6 and
                        independent['integrated_balance_residual_j'] < .1 and
                        abs(independent['water_l']-portable['water_l']) < 1e-8)
                    state['rows'].append(dict(identity=list(identity), portable=portable,
                        independent=independent, archive_sample_delta_c_or_l=difference, passed=bool(accepted)))
                    save('checkpoint')
                    if not accepted:
                        raise ValueError('Extremal replay failed')
            if len(seen) != archived['independent_cases']:
                raise ValueError('Extremal coverage differs')
        else:
            bank = json.loads((ROOT/'reference/structure-decision.json').read_text())
            for group in bank['banks']:
                route, capacity = bank['structures'][group['structure']]
                for grid in GRIDS:
                    current = dict(structure=group['structure'],design=group['design'],grid=list(grid),records=[])
                    state['current'] = current
                    for offset in range(0,len(group['indices']),48):
                        budget(); indices = group['indices'][offset:offset+48]
                        params = [{**model.BASE,**archived['prior'][i]} for i in indices]
                        values = replay(params,grid,route,capacity,state['policies'][group['design']],budget)
                        current['records'].extend(dict(prior_index=i,parameters=archived['prior'][i],**r)
                            for i,r in zip(indices,values))
                        save('checkpoint')
                        if not all(r['fair_reserve_passed'] for r in values):
                            raise ValueError('New qualification unresolved or failed; archive not substituted')
                    state['rows'].append(current); state.pop('current'); save('checkpoint')
            actual = [(g['structure'],g['design'],tuple(g['grid']),r['prior_index']) for g in state['rows'] for r in g['records']]
            expected = {(g['structure'],g['design'],grid,i) for g in bank['banks'] for grid in GRIDS for i in g['indices']}
            if len(actual) != len(set(actual)) or set(actual) != expected:
                raise ValueError('Exact canonical coverage differs')
        budget()
        if any(sha(ROOT/n) != h for n,h in hashes.items()):
            raise ValueError('Sources changed during execution')
        save('completed')
    except Exception as error:
        save('failed: '+repr(error))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mode',choices=['audit','replay-extrema','qualify'],default='audit')
    parser.add_argument('--seconds',type=float,default=180.)
    args = parser.parse_args()
    run(args.output,args.mode,args.seconds)
