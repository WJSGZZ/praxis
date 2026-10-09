"""Independent edge cases found by the bde50dd author-external audit."""
import mpmath as mp
import numpy as np
import pytest
from modeling import forecast, inference, graph, nonlinear, experiment, decision_models
from scripts import mcp_server


def test_constant_grey_response_has_exact_zero_development_limit():
    # For x(k)=10 the accumulated response is 10(k+1); first differences are 10.
    result = forecast.gm11([10]*6, 3)
    assert result['fitted'] == pytest.approx([10]*6)
    assert result['forecast'] == pytest.approx([10]*3)
    assert result['posterior_ratio_c'] is None
    assert result['small_error_probability_p'] is None
    assert result['grade'] == 'not_applicable'


@pytest.mark.parametrize('series,horizon', [([10,10,np.nan,10],2), ([[1,2],[3,4]],2), ([1,2,3,4],0), ([1,2,3,4],True)])
def test_grey_rejects_undefined_input(series, horizon):
    with pytest.raises(ValueError):
        forecast.gm11(series,horizon)


@pytest.mark.parametrize('output', [1., [1.,2.], [[1.]]*4, [1.,2.,np.nan,4.], [1.,2.,np.inf,4.]])
def test_monte_carlo_cannot_change_sample_count_or_accept_undefined_outcomes(output):
    with pytest.raises(ValueError, match='exactly n finite'):
        inference.monte_carlo(lambda samples:output, {}, n=4, threshold=0)


def test_monte_carlo_constant_output_has_zero_sampling_error():
    r=inference.monte_carlo(lambda _:np.ones(4), {}, n=4, threshold=0)
    assert r['mc_standard_error']==0 and r['exceedance']['probability']==1


@pytest.mark.parametrize('tool,args', [
    (graph.shortest_path, ([['a','b',1],['a','b',5]], 'a','b')),
    (graph.max_flow, ([['s','t',2],['s','t',3]], 's','t')),
    (graph.minimum_spanning_tree, ([['a','b',1],['b','a',5]],)),
    (nonlinear.min_cost_flow, ([['s','t',1,1],['s','t',2,3]], {'s':-2,'t':2})),
])
def test_simple_graph_contract_does_not_silently_overwrite_parallel_edges(tool,args):
    with pytest.raises(ValueError, match='Parallel or duplicate'):
        tool(*args)


@pytest.mark.parametrize('bad', [mp.nan, mp.inf, mp.mpc(0,1)])
def test_high_precision_evidence_refuses_nonreal_or_nonfinite_samples(bad):
    with pytest.raises(ValueError, match='finite real'):
        experiment.test_conjecture(lambda x:bad, lambda x:mp.mpf(0), '==', [[0,1]], points=2)


def test_no_samples_cannot_support_a_conjecture():
    with pytest.raises(ValueError,match='positive integer'):
        experiment.test_conjecture(lambda x:x,lambda x:0,'==',[[0,1]],points=0)
    with pytest.raises(ValueError,match='positive integer'):
        mcp_server.call('test_conjecture',dict(lhs='x',rhs='0',relation='==',names=['x'],bounds=[[0,1]],points=0))


def test_mcp_undefined_log_does_not_return_holds_true():
    with np.errstate(invalid='ignore'):
        with pytest.raises(ValueError,match='finite real'):
            mcp_server.call('test_conjecture',dict(lhs='log(x)',rhs='0',relation='==',names=['x'],bounds=[[-2,-1]],points=2))


def test_unattainable_portfolio_target_keeps_solver_failure():
    # Every convex mixture earns at most .02 in each scenario: .5 is impossible.
    r=decision_models.cvar_portfolio([[.01,.02],[.01,.02]],target=.5)
    assert r['success'] is False and r['status']==2 and 'infeasible' in r['message'].lower()
    assert 'weights' not in r and 'cvar' not in r


def test_mcp_comparison_overflow_is_an_error_not_a_refutation_certificate():
    reply=mcp_server.handle({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'test_conjecture','arguments':dict(lhs='1e308',rhs='-1e308',relation='==',names=['x'],bounds=[[0,1]],points=1)}})
    assert reply['result']['isError'] is True
    assert 'finite numeric range' in reply['result']['content'][0]['text']


def test_undefined_samples_remain_errors_through_mcp_protocol():
    with np.errstate(invalid='ignore'):
        reply=mcp_server.handle({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'test_conjecture','arguments':dict(lhs='sqrt(-1)',rhs='0',relation='==',names=['x'],bounds=[[0,1]],points=1)}})
    assert reply['result']['isError'] is True
    assert 'finite real' in reply['result']['content'][0]['text']
