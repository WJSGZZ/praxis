"""Independent continuum and flux checks of the frozen axial-dispersion study."""
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from numpy.polynomial.legendre import leggauss
from threadpoolctl import threadpool_limits
from model import Stage, trajectory

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'checks.json'
if OUT.exists():
    raise FileExistsError(OUT)
design = json.loads((ROOT / 'design.json').read_text())
result = json.loads((ROOT / 'results.json').read_text())
p = design['p']
started = time.monotonic()
records = []
bindings = {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest()
            for n in ['design.json', 'design.md', 'model.py', 'run.py', 'results.json', 'check.py']}


def checkpoint():
    if time.monotonic() - started > design['checker_seconds']:
        raise TimeoutError('Cumulative checker deadline')


def steady_continuum(x, D, flow):
    """Closed-form solution of the uniform-loss boundary-value problem."""
    v = flow / 60000 * p['L'] / p['V']
    k = (p['Ha'] + p['Hb']) / p['C']
    te = (p['Ha']*p['Ta'] + p['Hb']*p['Tb'])/(p['Ha'] + p['Hb'])
    plus = (v + math.sqrt(v*v + 4*D*k))/(2*D)
    minus = (v - math.sqrt(v*v + 4*D*k))/(2*D)
    # Scale the growing exponential at L to avoid large entries.
    matrix = [[(v-D*plus)*math.exp(-plus*p['L']), v-D*minus],
              [plus, minus*math.exp(minus*p['L'])]]
    a, b = np.linalg.solve(matrix, [v*(p['Tin']-te), 0])
    return te + a*np.exp(plus*(np.asarray(x)-p['L'])) + b*np.exp(minus*np.asarray(x))


def continuum_average(D, flow, cells, t, modes=64, quadrature=256):
    """Sturm--Liouville expansion, independent of finite-volume matrices."""
    beta = flow / 60000 * p['L'] / p['V']/(2*D)
    assert beta > 0
    k = (p['Ha']+p['Hb'])/p['C']
    # Robin eigenvalues: mu L - 2 atan(beta/mu) = n pi.
    mus = np.array([brentq(lambda mu: mu*p['L']-2*np.arctan(beta/mu)-n*np.pi,
                          max(1e-12, n*np.pi/p['L']), (n+1)*np.pi/p['L'])
                    for n in range(modes)])
    g, w = leggauss(quadrature)
    x = (g+1)*p['L']/2
    phi = np.cos(mus[:,None]*x)+(beta/mus[:,None])*np.sin(mus[:,None]*x)
    coeff = (phi @ (w*np.exp(-beta*x)*(p['T0']-steady_continuum(x,D,flow)))) / ((phi*phi) @ w)
    gx, gw = leggauss(12)
    points = ((np.arange(cells)[:,None]+.5)+gx[None,:]/2)*p['L']/cells
    flat = points.ravel()
    phix = np.cos(mus[:,None]*flat)+(beta/mus[:,None])*np.sin(mus[:,None]*flat)
    values = steady_continuum(flat,D,flow)+np.exp(beta*flat)*((coeff*np.exp(-(D*mus*mus+k+D*beta*beta)*t)) @ phix)
    return (values.reshape(cells,-1) @ gw)/2


def independent_rhs(cells, profile, D, flow):
    """Derive conservative interface fluxes directly; no producer fields/matrix."""
    dx = p['L']/cells
    v = flow/60000*p['L']/p['V']
    cap = p['C']/cells
    ha = p['Ha']/cells
    if profile == 'uniform':
        hb = np.full(cells, p['Hb']/cells)
    else:
        edges = np.linspace(0,p['L'],cells+1)
        cumulative = np.array([.5*(1+math.erf((x-.55*p['L'])/(.4*math.sqrt(2)))) for x in edges])
        hb = p['Hb']*np.diff(cumulative)/(cumulative[-1]-cumulative[0])
    def rhs(t,y):
        checkpoint()
        flux = np.empty(cells+1)
        flux[0] = v*p['Tin']
        flux[-1] = v*y[-1]
        flux[1:-1] = v*y[:-1]-D*np.diff(y)/dx
        return -np.diff(flux)/dx-(ha*(y-p['Ta'])+hb*(y-p['Tb']))/cap
    return rhs, hb


def replay_check(profile,D,segments,label):
    cells = 160
    times, expected = trajectory(p,cells,profile,D,segments,dt=1.)
    state = np.full(cells,p['T0'])
    values = [state.copy()]
    elapsed = 0.
    integrated_net = integrated_excess = 0.
    max_residual = 0.
    for duration,flow in segments:
        if duration <= 0:
            continue
        rhs,hb = independent_rhs(cells,profile,D,flow)
        ts = np.unique(np.r_[np.arange(.5,duration,.5),duration])
        sol = solve_ivp(rhs,(0,duration),state,method='RK45',t_eval=ts,
                        rtol=2e-9,atol=2e-10)
        assert sol.success, sol.message
        tt = np.r_[0.,sol.t]
        yy = np.vstack([state,sol.y.T])
        mean = yy.mean(axis=1)
        body = yy @ hb/p['Hb']
        power = -p['Ha']*(mean-p['Ta'])-p['Hb']*(body-p['Tb'])+p['rho_cp']*flow/60000*(p['Tin']-yy[:,-1])
        excess = p['rho_cp']*flow/60000*(yy[:,-1]-mean)
        integrated_net += float(np.trapezoid(power,tt))
        integrated_excess += float(np.trapezoid(excess,tt))
        for j in [0,len(tt)//2,len(tt)-1]:
            residual = abs(p['C']*rhs(tt[j],yy[j]).mean()-power[j])
            max_residual = max(max_residual,float(residual))
        mask = np.isclose(sol.t,np.round(sol.t),atol=1e-8)
        values.extend(sol.y[:,mask].T)
        state = sol.y[:,-1]
        elapsed += duration
    actual = np.asarray(values)
    assert actual.shape == expected.shape, (actual.shape,expected.shape)
    difference = float(np.max(np.abs(actual-expected)))
    energy_error = float(abs(p['C']*(state.mean()-p['T0'])-integrated_net))
    assert difference < 2e-6, difference
    assert max_residual < 1e-7, max_residual
    assert energy_error < 1., energy_error
    records.append(dict(check='independent_flux_RK45',label=label,profile=profile,D=D,
                        cells=cells,max_temperature_difference_c=difference,
                        max_instant_energy_residual_w=max_residual,
                        trapezoid_step_s=.5,integrated_energy_error_j=energy_error,
                        excess_overflow_energy_j=integrated_excess,
                        interpretation='negative means outlet cooler than contemporaneous mean; not measured heat or a comparison of optimized controls'))


status = 'completed'
try:
    assert result['status'] == 'completed'
    assert all(bindings[name] == sha for name,sha in result['source_sha256'].items())
    with threadpool_limits(limits=1):
        te = (p['Ha']*p['Ta']+p['Hb']*p['Tb'])/(p['Ha']+p['Hb'])
        exact = te+(p['T0']-te)*math.exp(-(p['Ha']+p['Hb'])*1800/p['C'])
        for cells in design['cells']:
            for D in design['diffusivities']:
                diff = float(np.max(abs(Stage(p,cells,'uniform',D,0).propagate(np.full(cells,40.),[1800])[0]-exact)))
                assert diff < 1e-8, diff
                records.append(dict(check='no_flow_analytic',cells=cells,D=D,error_c=diff))
        for D in design['diffusivities']:
            errors=[]
            for cells in design['cells']:
                gx,gw=leggauss(12)
                points=((np.arange(cells)[:,None]+.5)+gx[None,:]/2)*p['L']/cells
                exactss=steady_continuum(points,D,.8047484179843053)@gw/2
                err=float(np.max(abs(Stage(p,cells,'uniform',D,.8047484179843053).steady-exactss)))
                errors.append(err)
            assert errors[2] < errors[1] < errors[0], errors
            records.append(dict(check='steady_continuum_refinement',D=D,cells=design['cells'],max_error_c=errors))
            for t in [600.,1800.]:
                errors=[]
                for cells in design['cells']:
                    exacttrans=continuum_average(D,.8047484179843053,cells,t)
                    fv=Stage(p,cells,'uniform',D,.8047484179843053).propagate(np.full(cells,40.),[t])[0]
                    errors.append(float(np.max(abs(fv-exacttrans))))
                convergence=float(np.max(abs(continuum_average(D,.8047484179843053,160,t,64,256)-continuum_average(D,.8047484179843053,160,t,96,384))))
                assert convergence < 1e-8, convergence
                assert errors[2] < errors[1] < errors[0], errors
                records.append(dict(check='transient_continuum_refinement',D=D,t_s=t,cells=design['cells'],max_error_c=errors,series_quadrature_difference_c=convergence))
        for entry in result['search']:
            chosen=entry['selected']
            if chosen is None:
                continue
            assert chosen['command_l'] == min(c['command_l'] for c in entry['candidates'])
            segments=[(chosen['delay_s'],0.),(1800-chosen['delay_s'],chosen['rate_lpm'])]
            replay_check(entry['profile'],entry['D'],segments,'selected_delayed_constant')
        for policy in ['original_constant','original_schedule']:
            replay_check('uniform',.0003,design['policies'][policy],policy)
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==sha for n,sha in bindings.items())
except Exception as exc:
    status='failed_or_partial'
    error=repr(exc)
finally:
    receipt=dict(status=status,elapsed_s=time.monotonic()-started,source_sha256=bindings,
                 records=records,scope='Continuum analytic checks and independent flux RK45. Sampled reduced counterfactual; not physical validation, continuous feasibility or global optimality.')
    if status!='completed':
        receipt['error']=error
    OUT.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(status=status,elapsed_s=receipt['elapsed_s'],checks=len(records),error=receipt.get('error'))))
if status!='completed':
    raise SystemExit(1)
