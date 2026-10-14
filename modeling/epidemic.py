"""SIR compartment model: simulation, final size, and a least-squares fit that reports identifiability."""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, least_squares
from modeling.contracts import diagnostic


def simulate_sir(beta, gamma, population, infected0, days, *, recovered0=0.):
    """Integrate dS=-beta S I/N, dI=beta S I/N - gamma I, dR=gamma I at daily output."""
    if (not np.isfinite([beta, gamma, population, infected0, recovered0]).all()
            or min(beta, gamma, population) <= 0 or infected0 < 0 or recovered0 < 0
            or infected0 + recovered0 > population):
        raise ValueError('Finite positive beta, gamma and population with nonnegative consistent initial compartments are required')
    if isinstance(days, bool) or not isinstance(days, (int, np.integer)) or days < 1:
        raise ValueError('days must be a positive integer for daily output')
    y0 = [population - infected0 - recovered0, infected0, recovered0]
    sol = solve_ivp(lambda t, y: [-beta * y[0] * y[1] / population, beta * y[0] * y[1] / population - gamma * y[1], gamma * y[1]],
                    (0, days), y0, t_eval=np.arange(0, days + 1.), rtol=1e-9, atol=1e-9)
    if not sol.success or not np.isfinite(sol.y).all():
        raise RuntimeError(f'SIR integration failed or exceeded finite range: {sol.message}')
    return dict(t=sol.t.tolist(), S=sol.y[0].tolist(), I=sol.y[1].tolist(), R=sol.y[2].tolist(), r0=beta / gamma)


def final_size(r0, *, susceptible_fraction=1.0, infected_fraction=None):
    """Final new-removal fraction under homogeneous SIR's initial-state invariant.

    z = i0 + s0*(1-exp(-R0*z)). With infected_fraction omitted, the
    supercritical infinitesimal-seed limit is returned (the traditional attack
    rate), not an outbreak starting with exactly zero infected people. With an
    explicit i0, the actual finite initial compartments determine z.
    """
    s0 = float(susceptible_fraction)
    i0 = 0.0 if infected_fraction is None else float(infected_fraction)
    if not np.isfinite([r0, s0, i0]).all() or r0 < 0 or min(s0, i0) < 0 or s0 + i0 > 1:
        raise ValueError('Finite nonnegative R0 and initial fractions with s0+i0 <= 1 are required')
    if infected_fraction is not None and i0 == 0:
        return 0.0
    if i0 > 0:
        return brentq(lambda z: z - i0 + s0 * np.expm1(-r0 * z), i0, i0 + s0,
                      xtol=np.finfo(float).tiny, rtol=4 * np.finfo(float).eps)
    if r0 * s0 <= 1:
        return 0.0
    # Divide out the zero root and use expm1 to avoid cancellation near R0=1.
    return brentq(lambda z: r0 * s0 - 1 if z == 0 else -s0 * np.expm1(-r0 * z) / z - 1,
                  0.0, s0, xtol=np.finfo(float).tiny, rtol=4 * np.finfo(float).eps)


def fit_sir(infected, population, *, recovered=None, starts=((.4, .2), (.2, .1), (.8, .3))):
    """Fit beta and gamma to daily infected counts; flags weak identifiability from the Jacobian.

    With only infected counts early in an outbreak, beta and gamma are strongly correlated; a
    large condition number or correlation means the data cannot separate them."""
    y = np.asarray(infected, float)
    if (y.ndim != 1 or len(y) < 4 or not np.isfinite(y).all() or (y < 0).any()
            or not np.isfinite(population) or population <= 0 or (y > population).any() or y[0] <= 0):
        raise ValueError('At least four finite daily infected counts in [0,population], with a positive initial count, are required')
    r = None if recovered is None else np.asarray(recovered, float)
    if r is not None and (r.shape != y.shape or not np.isfinite(r).all() or (r < 0).any() or (r + y > population).any()):
        raise ValueError('recovered must match infected counts and form nonnegative compartments within the population')
    recovered0 = 0.0 if r is None else float(r[0])
    days = len(y) - 1

    def residual(theta):
        simulated = simulate_sir(theta[0], theta[1], population, y[0], days, recovered0=recovered0)
        i_residual = np.asarray(simulated['I']) - y
        return i_residual if r is None else np.r_[i_residual, np.asarray(simulated['R']) - r]

    best = None
    for start in starts:
        try:
            fit = least_squares(residual, start, bounds=([1e-4, 1e-4], [5., 5.]))
        except ValueError:
            continue
        if best is None or fit.cost < best.cost:
            best = fit
    if best is None:
        raise RuntimeError('Fit failed from every start')
    jac = best.jac
    cond = float(np.linalg.cond(jac))
    rank = int(np.linalg.matrix_rank(jac))
    cov = np.linalg.pinv(jac.T @ jac) * (2 * best.cost / max(1, len(best.fun) - 2))
    sd = np.sqrt(np.diag(cov))
    corr_raw = float(cov[0, 1] / (sd[0] * sd[1])) if sd.min() > 0 else float('nan')
    identified = rank == 2 and bool(best.success)
    corr, corr_status = diagnostic(corr_raw, status=None if identified else 'not_identifiable',
                                   reason='Parameter correlation requires a converged full-rank fit and positive estimated variances')
    condition, condition_status = diagnostic(cond, reason='The fitted Jacobian is singular; its condition is unbounded')
    r0 = float(best.x[0] / best.x[1])
    susceptible0 = population - y[0] - recovered0
    return dict(beta=float(best.x[0]), gamma=float(best.x[1]), r0=r0,
                final_size=float(final_size(r0, susceptible_fraction=susceptible0 / population, infected_fraction=y[0] / population)),
                final_size_initial_state=dict(susceptible_fraction=float(susceptible0 / population), infected_fraction=float(y[0] / population),
                                              definition='Final removals minus initial recovered, divided by population; includes initially infected people'),
                rmse=float(np.sqrt(2 * best.cost / len(best.fun))),
                std_error=sd.tolist() if identified else None, parameter_correlation=corr, jacobian_condition=condition,
                jacobian_rank=rank, converged=bool(best.success),
                diagnostics=dict(parameter_correlation=corr_status, jacobian_condition=condition_status,
                                 parameter_inference=dict(status='computed' if identified else 'not_identifiable')),
                weakly_identified=bool(not identified or cond > 1e6 or corr is not None and abs(corr) > .98),
                fitted_observations=['infected'] if r is None else ['infected', 'recovered'],
                assumptions=dict(initial_infected=float(y[0]), initial_recovered=recovered0, population=float(population), model='SIR with the declared initial recovered compartment',
                                 weakly_identified_rule='condition number of the Jacobian above 1e6 or |parameter correlation| above 0.98',
                                 std_error_note='Local standard errors assuming the model is right and noise is independent; with noiseless or smooth data they are far too small to be believed.'))
