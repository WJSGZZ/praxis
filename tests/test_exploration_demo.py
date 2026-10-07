from examples import exploration_demo as demo


def test_exploration_demo_gives_the_known_answers():
    t = demo.transport_case()
    assert t['total_unimodular'] is True and t['chosen'] == ['lp'] and t['issues'] == []
    s = demo.structure_case()
    assert s['convex'] and s['symmetric']
    e = demo.experiment_case()
    assert e['euler_polynomial_fails_at'] == [40] and e['pell_recurrence'] == ['2', '1']
