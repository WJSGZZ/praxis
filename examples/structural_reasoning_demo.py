"""Synthetic checks of mathematical structure, not a general model classifier.

Locally authored examples using existing SymPy/SciPy dependencies; no upstream
examples or algorithm implementations copied. See mathematical-reasoning.md.
"""
import argparse
import json
from importlib.metadata import version
from pathlib import Path
import numpy as np
import sympy as sp
from sympy.physics.units import length, time
from sympy.physics.units.systems.si import SI
from scipy.optimize import linprog


def dimensional_example():
    dimensions = SI.get_dimension_system()
    velocity = length / time
    correct = dimensions.equivalent_dims(velocity * time, length)
    incorrect = dimensions.equivalent_dims(velocity / time, length)
    return {'correct_distance_v_times_t': bool(correct),
            'incorrect_distance_v_divided_by_t': bool(incorrect),
            'scope': 'Declared dimensions only; dimensional consistency does not prove a law.'}


def identifiability_example():
    a, b, t, x = sp.symbols('a b t x', positive=True)
    prediction = a*b*x
    transformed = prediction.subs({a:a*t,b:b/t}, simultaneous=True)
    invariant = sp.simplify(prediction-transformed) == 0
    observation_map = sp.Matrix([a*b,2*a*b,3*a*b])
    rank = observation_map.jacobian([a,b]).rank()
    return {'parameter_count': 2, 'observation_jacobian_rank': rank,
            'same_predictions_for_all_positive_t': bool(invariant),
            'identifiable_combination': 'a*b',
            'scope': 'For this model, a and b cannot be separately identified even with exact observations. The explicit family, not rank alone, establishes ambiguity.'}


def optimization_example():
    # Max 3*x1+2*x2, x>=0, 2*x1+x2<=4, x1+2*x2<=4.
    A = np.array([[2.,1.],[1.,2.]])
    bound = np.array([4.,4.])
    benefit = np.array([3.,2.])
    result = linprog(-benefit,A_ub=A,b_ub=bound,bounds=(0,None),method='highs')
    if not result.success:
        raise RuntimeError(f'LP failed: {result.message}')
    # Independently constructed exact primal and dual witnesses.
    exact_A = sp.Matrix([[2,1],[1,2]])
    exact_b = sp.Matrix([4,4]); exact_c = sp.Matrix([3,2])
    primal = sp.Matrix([sp.Rational(4,3),sp.Rational(4,3)])
    dual = sp.Matrix([sp.Rational(4,3),sp.Rational(1,3)])
    primal_feasible = all(v>=0 for v in primal) and all(v>=0 for v in exact_b-exact_A*primal)
    dual_feasible = all(v>=0 for v in dual) and all(v>=0 for v in exact_A.T*dual-exact_c)
    primal_value = (exact_c.T*primal)[0]
    upper_bound = (exact_b.T*dual)[0]
    certified = bool(primal_feasible and dual_feasible and primal_value==upper_bound)
    numerical_feasible = bool(np.all(result.x>=-1e-9) and np.all(A@result.x<=bound+1e-9))
    matches = bool(np.isclose(benefit@result.x,float(upper_bound),rtol=0,atol=1e-9))
    if not certified or not numerical_feasible or not matches:
        raise RuntimeError('Numerical solve or exact independent certificate disagrees')
    return {'model': 'Maximize 3*x1+2*x2; x>=0; 2*x1+x2<=4; x1+2*x2<=4',
            'numerical_solution':result.x.tolist(),'numerical_objective':float(benefit@result.x),
            'exact_primal_value':str(primal_value),'exact_dual_upper_bound':str(upper_bound),
            'exact_certificate':certified,'numerical_feasible':numerical_feasible,
            'scope': 'Certificate proves the optimum of this stated LP; it does not prove realism of its assumptions.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('outputs/structural-reasoning'))
    a=p.parse_args()
    report={'synthetic_only':True,'versions':{p:version(p) for p in ['sympy','scipy']},'dimensions':dimensional_example(),
            'identifiability':identifiability_example(),'optimization':optimization_example()}
    if not report['dimensions']['correct_distance_v_times_t'] or report['dimensions']['incorrect_distance_v_divided_by_t']:
        raise RuntimeError('Dimension check disagrees with independent length/time arithmetic')
    if not report['identifiability']['same_predictions_for_all_positive_t'] or report['identifiability']['observation_jacobian_rank']!=1:
        raise RuntimeError('Identifiability example disagrees with product invariance')
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
