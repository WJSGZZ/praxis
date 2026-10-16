"""Independent analytic moments and rolling OLS predictions; bad information stays rejected."""
import math
import numpy as np
import pytest
from modeling import inference, forecast
from scripts import mcp_server


def test_normal_covariance_has_analytic_sum_variance():
    d={'a':dict(dist='norm',params=dict(loc=1,scale=1)),'b':dict(dist='norm',params=dict(loc=2,scale=2))}
    r=inference.monte_carlo(lambda s:s['a']+s['b'],d,covariance=[[1,.5],[.5,4]],n=30000,seed=7)
    assert r['mean']==pytest.approx(3,abs=.05)
    assert r['sd']**2==pytest.approx(6,rel=.025)
    assert r['input_order']==['a','b']
    lo,hi=r['quantile_bootstrap']['intervals'][.5]
    assert lo<r['quantiles'][.5]<hi


def test_uniform_copula_has_analytic_transformed_correlation():
    d={k:dict(dist='uniform') for k in ['a','b']};rho=.6
    r=inference.monte_carlo(lambda s:s['a']+s['b'],d,correlation=[[1,rho],[rho,1]],n=30000,seed=3)
    corr=6/math.pi*math.asin(rho/2)
    assert r['mean']==pytest.approx(1,abs=.015)
    assert r['sd']**2==pytest.approx((1+corr)/6,abs=.007)
    assert r['dependence']=='gaussian_copula_latent_correlation'


def test_lhs_linear_integral_and_uncertainty_scope():
    r=inference.monte_carlo(lambda s:s['a']+2*s['b'],{k:dict(dist='uniform') for k in ['a','b']},n=1024,sampling='lhs',threshold=1.5)
    assert abs(r['mean']-1.5)<3/(2*1024)
    assert r['mc_standard_error'] is None and r['settled'] is None
    assert r['quantile_bootstrap']['intervals'] is None and r['exceedance']['ci'] is None
    assert 'LHS' in r['quantile_bootstrap']['reason']


def test_constant_bootstrap_and_discrete_compatibility():
    r=inference.monte_carlo(lambda _:np.ones(4),{},n=4)
    assert all(v==[1,1] for v in r['quantile_bootstrap']['intervals'].values())
    r=inference.monte_carlo(lambda s:s['k'],dict(k=dict(dist='poisson',params=dict(mu=2))),n=6000,seed=4)
    assert r['mean']==pytest.approx(2,abs=.06)
    assert r['sd']**2==pytest.approx(2,abs=.12)


@pytest.mark.parametrize('extra',[
 dict(correlation=[[1,2],[2,1]]),dict(correlation=[[1,.2],[.3,1]]),dict(correlation=[[2,0],[0,1]]),
 dict(covariance=[[1,0],[0,2]]),dict(covariance=[[1,0],[0,1]],correlation=[[1,0],[0,1]]),
 dict(correlation=[[1]]),dict(sampling='sobol'),dict(bootstrap_resamples=True),dict(confidence=1),dict(n=True)])
def test_bad_joint_design_rejected_before_model(extra):
    def forbidden(_):raise AssertionError('invalid design reached model')
    with pytest.raises(ValueError):inference.monte_carlo(forbidden,{k:dict(dist='norm') for k in ['a','b']},**extra)


def test_non_normal_covariance_rejected():
    with pytest.raises(ValueError,match='normal marginals'):
        inference.monte_carlo(lambda s:s['x'],dict(x=dict(dist='uniform')),covariance=[[1]])


def test_arima_exogenous_00_matches_independent_ols():
    x=np.linspace(-2,2,60);y=3+2*x+.02*np.cos(np.arange(60));future=np.array([2.1,2.2])
    b=np.linalg.lstsq(np.column_stack([np.ones(60),x]),y,rcond=None)[0]
    r=inference.arima_forecast(y,2,max_p=0,max_q=0,max_d=0,exog=x,future_exog=future)
    assert r['forecast']==pytest.approx(b[0]+b[1]*future,abs=.001)
    assert r['order']==[0,0,0] and len(r['residuals'])==60


def test_backtest_reselection_and_baselines_against_hand_calculations():
    y=10+.2*np.arange(30)+.4*np.sin(np.arange(30));h=2
    r=inference.arima_forecast(y,h,max_p=0,max_q=0,max_d=0,backtest={'min_train':20})['backtest']
    errors={k:[] for k in ['naive','drift','arima']}
    for o in range(20,len(y)-h+1):
        train=y[:o];truth=y[o:o+h]
        b=np.linalg.lstsq(np.column_stack([np.ones(o),np.arange(o)]),train,rcond=None)[0]
        predictions=dict(naive=np.full(h,train[-1]),drift=train[-1]+(train[-1]-train[0])/(o-1)*np.arange(1,h+1),arima=b[0]+b[1]*np.arange(o,o+h))
        for k,v in predictions.items():errors[k].append(np.abs(truth-v).mean())
    assert r['origins']==9
    for k,e in errors.items():assert r['mae'][k]==pytest.approx(np.mean(e),abs=.003 if k=='arima' else 1e-12)


@pytest.mark.parametrize('change',[dict(horizon=0),dict(series=[1]*8),dict(series=[1]*20+[float('nan')]),dict(max_p=True),dict(exog=list(range(25))),dict(future_exog=[1]),dict(exog=list(range(25)),future_exog=[1,2,3]),dict(exog=list(range(25)),future_exog=[26,27],backtest=True),dict(backtest={'min_train':1})])
def test_bad_arima_shapes_and_information(change):
    a=dict(series=10+np.sin(np.arange(25)),horizon=2,max_p=0,max_q=0,max_d=0);a.update(change)
    with pytest.raises(ValueError):inference.arima_forecast(**a)


def test_rolling_candidate_failure_keeps_denominator():
    calls=[]
    def candidate(train,h,origin):
        assert np.array_equal(train,np.arange(origin,dtype=float));calls.append(origin)
        if origin==4:raise ValueError('independent planned failure')
        return np.full(h,train[-1])
    r=forecast.rolling_origin(np.arange(9.),2,min_train=3,candidates={'custom':candidate})
    assert calls==list(range(3,8)) and r['origins']==5
    assert r['methods']['custom']['status']=='partial' and r['methods']['custom']['origins']==4
    assert 'custom' not in r['mae']


def test_where_exact_piecewise_and_rejected_syntax():
    f=mcp_server._compile('where(x <= 0, -x, 2*x)',['x'])
    assert np.array_equal(f(np.array([[-3],[0],[2.]])),[3,0,4])
    for e in ['where(x<0,1)','where(x<0<2,1,0)','where(True,1,0)','np.where(x<0,1,0)','where(x<0,(2**200)**200,0)']:
        with pytest.raises(ValueError):mcp_server._compile(e,['x'])


def test_actual_nlp_frontier_adapter_is_bounded():
    assert 'epsilon_constraint_nlp' in mcp_server.EXPRESSION_TOOLS
    r=mcp_server.call('epsilon_constraint_nlp',dict(objectives=['x','(x-1)**2'],names=['x'],senses=[-1,-1],epsilon_grid=[[.25],[0]],bounds=[[0,1]],starts=8))
    assert r['expression_inputs']['objectives']==['x','(x-1)**2']
    # Analytic constrained primary minima: x=.5 and x=1 respectively.
    assert sorted(p['x'][0] for p in r['points'] if p.get('feasible'))==pytest.approx([.5,1],abs=1e-5)


def test_registered_backtest_union_and_exog_information_are_validated():
    # Exercise the actual registry schema: supported union types, no ignored keywords.
    base=dict(series=(4+.3*np.arange(28)+.1*np.sin(np.arange(28))).tolist(),horizon=2,max_p=0,max_q=0,max_d=0)
    for flag in [False,True,dict(min_train=20)]:
        result=mcp_server.call('arima_forecast',dict(base,backtest=flag))
        if flag:assert result['backtest']['origins']>0
    for invalid in [3,'yes',dict(unused=1),dict(exog_known_at_origin='true')]:
        with pytest.raises(ValueError):mcp_server.call('arima_forecast',dict(base,backtest=invalid))
    x=(np.cos(np.arange(28))+.02*np.arange(28))[:,None]
    result=mcp_server.call('arima_forecast',dict(base,exog=x.tolist(),future_exog=[[1.],[2.]],backtest=dict(min_train=24,exog_known_at_origin=True)))
    assert result['backtest']['origins']==3


def test_registered_new_graph_examples_retain_analytic_answers():
    for name in ['pagerank','betweenness','greedy_modularity_communities','epsilon_constraint_lp','epsilon_constraint_nlp']:
        result=mcp_server.call(name,mcp_server.EXAMPLES[name])
        assert result  # The independent numeric answers are in test_c5_model_tools.
