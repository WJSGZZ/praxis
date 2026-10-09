"""Audit feedback archives or independently replay the six realized policies.

No control optimization is launched. The elapsed limit is cooperative between
RHS replays, not an operating-system hard timeout. A new receipt preserves
partial work on failure; existing evidence is never overwritten.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
import scipy
from feedback_study import ROOT, feedback_values, require


def run(output, mode, seconds):
    output = Path(output)
    require(not output.exists(), 'Existing evidence is never overwritten')
    require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0,
            'Positive finite time limit required')
    require(mode in ('audit', 'replay'), 'Unknown mode')
    files = ['feedback_study.py', 'study_feedback.py', 'check_structure.py', 'code/model.py',
             'reference/feedback-study.json', 'reference/feedback-study.npz']
    state = dict(status='started', mode=mode, rows=[], seconds_limit=seconds,
                 source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files},
                 python=sys.version, scipy=scipy.__version__, numpy=np.__version__,
                 scope='Archive audit only; no historical source execution or mathematical certification.')
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    def save(status):
        state.update(status=status, elapsed_s=time.monotonic()-start)
        output.write_text(json.dumps(state, indent=2)+'\n')
    def budget():
        if time.monotonic()-start >= seconds:
            raise TimeoutError('Feedback replay cumulative time limit')
    save('started')
    try:
        budget()
        v = feedback_values()
        state['summary'] = dict(complete_services=len(v['completed']), observed_complete_services=6,
                               matched_ablation_services=3, archived_mesh_checks=v['recorded_mesh_checks'],
                               backup_command_l=v['backup_command_l'], faults=v['terminal'])
        if mode == 'replay':
            import check_structure
            import model
            state['scope'] = 'Six frozen realized policies, three grids, independently assembled RHS and half-second samples. Not a fine-grid closed-loop run, continuous certificate or experimental validation.'
            for (stage, case), row in v['completed'].items():
                if stage == 'no-observer':
                    continue
                route, cap = {'surface_fixed':('surface',None), 'deep_fixed':('deep',None),
                              'surface_finite':('surface',253310.)}[row['truth']]
                p = row['parameters']
                for grid in ((8,4,3), (12,6,4), (16,8,6)):
                    budget()
                    result = check_structure.replay(p, model.network(p,grid),
                               np.asarray(row['flows'])*p['flow_multiplier'], route,cap,sample_s=.5)
                    result.update(stage=stage, case=case, grid=list(grid))
                    state['rows'].append(result)
                    save('running')
                    require(result['min_temp'] >= 39.13 and result['max_temp'] <= 40.9 and
                            result['max_span'] <= 1.4 and abs(result['water_l']-sum(row['flows'])*p['flow_multiplier']) < 1e-8 and
                            result['instantaneous_balance_residual_w'] < 1e-6 and
                            result['integrated_balance_residual_j'] < .1, 'Independent realized policy failed')
            require(len(state['rows']) == 18, 'Incomplete realized-policy coverage')
        budget()
        save('completed')
        return state
    except Exception as error:
        state['error'] = repr(error)
        save('budget exhausted' if isinstance(error,TimeoutError) else 'failed')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('audit','replay'), default='audit')
    parser.add_argument('--seconds', type=float, default=30)
    args = parser.parse_args()
    state = run(args.output, args.mode, args.seconds)
    print(json.dumps(dict(status=state['status'], rows=len(state['rows']),elapsed_s=state['elapsed_s'])))
