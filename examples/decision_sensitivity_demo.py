"""Validated synthetic examples of the two newly adopted GitHub libraries."""
import argparse
from importlib.metadata import version
import json
from pathlib import Path
import numpy as np
from modeling.decision import evaluate_alternatives
from modeling.sensitivity import sobol_sensitivity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('outputs/decision-sensitivity'))
    args = parser.parse_args()
    # Uniform [0,1] independent inputs: Var(2*x1)=4/12, Var(x2)=1/12.
    # Thus S1=ST=[.8,.2,0] exactly; x3 is an intentionally irrelevant input.
    sensitivity = sobol_sensitivity(lambda X: 2*X[:, 0]+X[:, 1],
                                     ['x1','x2','unused'], [[0,1]]*3)
    s1 = np.array([p['S1'] for p in sensitivity['parameters']])
    st = np.array([p['ST'] for p in sensitivity['parameters']])
    if not np.allclose(s1, [.8,.2,0], atol=.02) or not np.allclose(st, [.8,.2,0], atol=.02):
        raise RuntimeError('Sobol results do not match analytic variance decomposition')
    # Alternative C dominates B, which dominates A; constant criterion is ignored.
    decisions = evaluate_alternatives([[3,1,7],[2,2,7],[1,3,7]], [.4,.4,.2], [-1,1,1],
                                     alternatives=['A','B','C'], criteria=['cost','benefit','constant'])
    if not np.allclose([a['score'] for a in decisions['alternatives']], [0,.5,1]):
        raise RuntimeError('TOPSIS disagrees with independently known ideal distances')
    if decisions['alternatives'][2]['first_place_scenario_share'] != 1:
        raise RuntimeError('Dominant alternative lost under positive-weight scenarios')
    args.output.mkdir(parents=True, exist_ok=True)
    result = {'synthetic_only': True, 'versions': {p:version(p) for p in ['SALib','pymcdm']},
              'analytic_sobol': [.8,.2,0], 'sensitivity':sensitivity, 'decisions':decisions}
    (args.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
