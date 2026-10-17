"""C6 calibration checks: per-coordinate basins, failing random starts and log-uniform starts."""
import json
import math

import numpy as np
import pytest

from modeling import calibrate


def _scaled_symmetric():
    rng = np.random.default_rng(1)
    x = np.linspace(0, 1, 40)
    y = 1000*x+0.0004+1e-5*rng.normal(size=40)
    return x, y


def test_basins_separate_symmetric_small_parameter_beside_large_one():
    x, y = _scaled_symmetric()
    # Independent answer: theta0*x + theta1**2 is the line a*x + c, so theta1 = +/-sqrt(c).
    slope, intercept = np.polyfit(x, y, 1)
    assert intercept > 0
    result = calibrate.calibrate(lambda th, x: th[0]*x+th[1]**2, x, y, [900, .05], bounds=[[0, 2000], [-1, 1]], multistart=16)
    best = [p['estimate'] for p in result['parameters']]
    assert best[0] == pytest.approx(slope, rel=1e-6)
    assert abs(best[1]) == pytest.approx(math.sqrt(intercept), rel=1e-4)
    report = result['multistart']
    random_converged = [a for a in report['attempts'] if a['kind'] == 'random' and a.get('converged')]
    same_sign = [a for a in random_converged if np.sign(a['theta'][1]) == np.sign(best[1])]
    assert 0 < len(same_sign) < len(random_converged)
    assert report['best_basin_random_hits'] == len(same_sign)
    assert report['best_basin_fraction'] == len(same_sign)/16
    assert all(a['best_basin'] == (np.sign(a['theta'][1]) == np.sign(best[1])) for a in random_converged)
    assert 'per coordinate' in report['basin_definition']
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('error', [ZeroDivisionError, OverflowError, np.linalg.LinAlgError, RuntimeError])
def test_random_start_exceptions_are_recorded_and_counted(error):
    x = np.linspace(0, 10, 80)
    y = np.sin(2.3*x)

    def model(theta, x):
        if theta[0] > 4:
            raise error('outside model domain')
        return np.sin(theta[0]*x)
    result = calibrate.calibrate(model, x, y, [2.2], bounds=[[0.1, 5]], multistart=8, seed=4)
    report = result['multistart']
    failed = [a for a in report['attempts'] if a.get('error_type') == error.__name__]
    assert failed and all(a['kind'] == 'random' and a['converged'] is False and 'outside model domain' in a['error'] for a in failed)
    assert len(report['attempts']) == 9
    assert report['failed_starts'] == len(failed)
    assert report['best_basin_random_hits'] <= 8-len(failed)
    assert report['best_basin_fraction'] == report['best_basin_random_hits']/8
    assert result['parameters'][0]['estimate'] == pytest.approx(2.3, abs=1e-6)
    json.dumps(result, allow_nan=False)


def test_math_overflow_in_random_start_is_recorded():
    x = np.linspace(0, 10, 80)
    result = calibrate.calibrate(lambda th, x: np.array([math.exp(th[0]*v) for v in x]), x, np.exp(.5*x), [.4],
                                 bounds=[[0, 100]], multistart=8)
    assert result['parameters'][0]['estimate'] == pytest.approx(.5, rel=1e-6)
    assert any(a.get('error_type') == 'OverflowError' for a in result['multistart']['attempts'])


def test_theta0_failure_still_raises():
    def model(theta, x):
        raise ZeroDivisionError('theta0 is outside the model domain')
    with pytest.raises(ZeroDivisionError):
        calibrate.calibrate(model, np.arange(10.), np.arange(10.), [1.], bounds=[[0, 2]], multistart=8)


def test_default_uniform_starts_are_unchanged():
    seed = 9
    result = calibrate.calibrate(lambda th, x: th[0]*x, np.arange(10.), 2*np.arange(10.), [1.], bounds=[[-3, 3]], multistart=8, seed=seed)
    generator = np.random.default_rng(np.random.SeedSequence(seed).spawn(2)[1])
    expected = [generator.uniform([-3.], [3.]).tolist() for _ in range(8)]
    assert [a['theta_initial'] for a in result['multistart']['attempts'][1:]] == expected
    assert result['multistart']['start_sampling'] == 'uniform'


def test_log_uniform_starts_cover_orders_of_magnitude():
    x = np.linspace(0, 5, 30)
    result = calibrate.calibrate(lambda th, x: np.exp(-x/th[0]), x, np.exp(-x/.01), [1.], bounds=[[1e-3, 1e3]],
                                 multistart=64, start_sampling='log_uniform', seed=3)
    starts = np.array([a['theta_initial'][0] for a in result['multistart']['attempts'][1:]])
    assert ((starts >= 1e-3) & (starts <= 1e3)).all()
    # Log-uniform on [1e-3, 1e3]: P(theta < 1) = 1/2; linear uniform gives about 1e-6.
    assert .3 < np.mean(starts < 1) < .7
    assert result['multistart']['start_sampling'] == 'log_uniform'
    assert 'log' in result['multistart']['basin_definition']


@pytest.mark.parametrize('kwargs', [dict(start_sampling='log_uniform', bounds=[[0, 2]]), dict(start_sampling='log_uniform', bounds=[[-1, 2]]),
                                    dict(start_sampling='normal', bounds=[[1, 2]])])
def test_bad_start_sampling_is_rejected_before_model_call(kwargs):
    with pytest.raises(ValueError):
        calibrate.calibrate(lambda th, x: pytest.fail('invalid sampling reached model'), np.arange(10.), np.arange(10.), [1.],
                            multistart=8, **kwargs)
