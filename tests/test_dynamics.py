import numpy as np

from modeling import dynamics as dyn


def kinds(result):
    return sorted((round(e['point'][0], 6), e['kind']) for e in result['equilibria'])


def test_logistic_and_lotka_volterra_equilibria():
    r = dyn.equilibria(lambda x: [x[0] * (1 - x[0])], [[-0.5, 2.0]])
    assert kinds(r) == [(0.0, 'unstable node'), (1.0, 'stable node')]
    a, b, c, d = 1.1, .4, .4, .1
    lv = lambda z: [a * z[0] - b * z[0] * z[1], d * z[0] * z[1] - c * z[1]]
    r = dyn.equilibria(lv, [[-1, 10], [-1, 10]])
    by_point = {tuple(np.round(e['point'], 6)): e['kind'] for e in r['equilibria']}
    assert by_point[(0.0, 0.0)] == 'saddle'
    assert by_point[(c / d, a / b)].startswith('non-hyperbolic')           # centre: purely imaginary eigenvalues


def test_damped_pendulum_is_a_stable_focus_at_rest_and_a_saddle_upright():
    f = lambda z: [z[1], -np.sin(z[0]) - .3 * z[1]]
    r = dyn.equilibria(f, [[-1, 4], [-1, 1]])
    by_x = {round(e['point'][0], 6): e['kind'] for e in r['equilibria']}
    assert by_x[0.0] == 'stable focus' and by_x[round(np.pi, 6)] == 'saddle'


def test_kalman_local_level_reaches_the_closed_form_steady_state():
    q, rr = .5, 2.0
    rng = np.random.default_rng(1)
    truth = np.cumsum(rng.normal(0, np.sqrt(q), 400))
    y = truth + rng.normal(0, np.sqrt(rr), 400)
    out = dyn.kalman_filter([[1]], [[1]], [[q]], [[rr]], [0.], [[10.]], y)
    P_pred = (q + np.sqrt(q * q + 4 * q * rr)) / 2          # steady-state predicted variance
    K = P_pred / (P_pred + rr)
    P_filt = (1 - K) * P_pred
    assert abs(out['filtered_cov'][-1][0][0] - P_filt) < 1e-9
    est = np.array(out['filtered_mean'])[:, 0]
    assert np.mean((est[50:] - truth[50:]) ** 2) < 0.75 * rr     # filtering beats the raw observations
    skipped = dyn.kalman_filter([[1]], [[1]], [[q]], [[rr]], [0.], [[10.]], [1.0, np.nan, 1.5])
    assert skipped['filtered_cov'][1][0][0] > skipped['filtered_cov'][0][0][0] - 1e-12     # no update, uncertainty grows
    assert np.isfinite(out['log_likelihood'])
