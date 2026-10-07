"""SIR compartment model: simulation, final size, and a least-squares fit that reports identifiability."""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, least_squares


def simulate_sir(beta, gamma, population, infected0, days, *, recovered0=0.):
    """Integrate dS=-beta S I/N, dI=beta S I/N - gamma I, dR=gamma I at daily output."""
    if min(beta, gamma, population) <= 0 or not 0 < infected0 <= population:
        raise ValueError('beta, gamma, population and infected0 must be positive and consistent')
    y0 = [population - infected0 - recovered0, infected0, recovered0]
    sol = solve_ivp(lambda t, y: [-beta * y[0] * y[1] / population, beta * y[0] * y[1] / population - gamma * y[1], gamma * y[1]],
                    (0, days), y0, t_eval=np.arange(0, days + 1.), rtol=1e-9, atol=1e-9)
    return dict(t=sol.t.tolist(), S=sol.y[0].tolist(), I=sol.y[1].tolist(), R=sol.y[2].tolist(), r0=beta / gamma)


def final_size(r0):
    """Attack-rate fraction z solving z = 1 - exp(-R0 z), for a fully susceptible population."""
    if r0 <= 1:
        return 0.
    return brentq(lambda z: z - 1. + np.exp(-r0 * z), 1e-12, 1.)


def fit_sir(infected, population, *, recovered=None, starts=((.4, .2), (.2, .1), (.8, .3))):
    """Fit beta and gamma to daily infected counts; flags weak identifiability from the Jacobian.

    With only infected counts early in an outbreak, beta and gamma are strongly correlated; a
    large condition number or correlation means the data cannot separate them."""
    y = np.asarray(infected, float)
    days = len(y) - 1

    def residual(theta):
        return np.asarray(simulate_sir(theta[0], theta[1], population, max(y[0], 1e-6), days)['I']) - y

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
    cov = np.linalg.pinv(jac.T @ jac) * (2 * best.cost / max(1, len(y) - 2))
    sd = np.sqrt(np.diag(cov))
    corr = float(cov[0, 1] / (sd[0] * sd[1])) if sd.min() > 0 else float('nan')
    return dict(beta=float(best.x[0]), gamma=float(best.x[1]), r0=float(best.x[0] / best.x[1]), rmse=float(np.sqrt(2 * best.cost / len(y))),
                std_error=sd.tolist(), parameter_correlation=corr, jacobian_condition=cond,
                weakly_identified=bool(cond > 1e6 or abs(corr) > .98))
