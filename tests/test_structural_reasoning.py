from fractions import Fraction
import pytest
from examples.structural_reasoning_demo import dimensional_example,identifiability_example,optimization_example


def test_dimension_check_distinguishes_length_from_acceleration():
    r=dimensional_example()
    # Independent exponent arithmetic: (L/T)*T=L; (L/T)/T=L/T^2.
    assert r['correct_distance_v_times_t']
    assert not r['incorrect_distance_v_divided_by_t']


def test_nonidentifiable_parameters_have_distinct_exact_solutions():
    r=identifiability_example()
    assert r['same_predictions_for_all_positive_t']
    assert r['observation_jacobian_rank']==1
    # Independent integer counterexample: two distinct pairs fit all x equally.
    assert (2,3)!=(1,6)
    for x in [1,2,9]:
        assert 2*3*x==1*6*x


def test_linear_solution_matches_independent_primal_dual_bound():
    r=optimization_example()
    x1=x2=Fraction(4,3);y1=Fraction(4,3);y2=Fraction(1,3)
    assert 2*x1+x2<=4 and x1+2*x2<=4
    assert 2*y1+y2>=3 and y1+2*y2>=2
    assert 3*x1+2*x2==4*y1+4*y2==Fraction(20,3)
    assert Fraction(r['exact_dual_upper_bound'])==Fraction(20,3)
    assert r['numerical_objective']==pytest.approx(float(Fraction(20,3)))
    assert r['numerical_feasible'] and r['exact_certificate']
