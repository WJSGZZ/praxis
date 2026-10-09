"""Independent one-dimensional axial-dispersion closure; imports no bath producer."""
import numpy as np
from scipy.linalg import eigh_tridiagonal, solve_banded
from scipy.special import ndtr


def fields(p, cells, profile):
    x=(np.arange(cells)+.5)*p['L']/cells
    if profile=='uniform': w=np.ones(cells)/cells
    elif profile=='localized_body':
        edges=np.linspace(0,p['L'],cells+1)
        w=np.diff(ndtr((edges-.55*p['L'])/.4));w/=w.sum()
    else: raise ValueError('Unknown loss profile')
    capacity=np.full(cells,p['C']/cells)
    ha=np.full(cells,p['Ha']/cells);hb=p['Hb']*w
    return x,capacity,ha,hb


class Stage:
    def __init__(self,p,cells,profile,D,flow):
        self.p=p;self.cells=cells;self.D=D;self.flow=flow
        self.x,self.capacity,self.ha,self.hb=fields(p,cells,profile)
        dx=p['L']/cells;v=flow/60000*p['L']/p['V'];a=D/dx**2;b=a+v/dx
        diag=-(self.ha+self.hb)/self.capacity-(a+b)
        diag[0]+=a;diag[-1]+=a
        self.diag=diag;self.low=b;self.high=a
        self.c=(self.ha*p['Ta']+self.hb*p['Tb'])/self.capacity
        self.c[0]+=v/dx*p['Tin']
        # Similarity to a real symmetric tridiagonal operator, not a bath matrix.
        self.weight=np.exp(np.arange(cells)*.5*np.log(b/a))
        self.eigen,self.Q=eigh_tridiagonal(diag,np.full(cells-1,np.sqrt(a*b)))
        band=np.zeros((3,cells));band[1]=diag;band[0,1:]=a;band[2,:-1]=b
        self.steady=solve_banded((1,1),band,-self.c)
        assert np.max(self.eigen)<0

    def propagate(self,initial,times):
        initial=np.asarray(initial);times=np.asarray(times)
        coef=self.Q.T@((initial-self.steady)/self.weight)
        values=((np.exp(times[:,None]*self.eigen)*coef)@self.Q.T)*self.weight+self.steady
        return values

    def rhs(self,y):
        out=self.diag*y+self.c
        out[1:]+=self.low*y[:-1];out[:-1]+=self.high*y[1:]
        return out


def trajectory(p,cells,profile,D,segments,dt=5.):
    """Segments contain (duration_s, commanded_lpm); every switch is sampled."""
    y=np.full(cells,p['T0']);times=[0.];data=[y.copy()];elapsed=0.
    for duration,flow in segments:
        if duration<=0:continue
        stage=Stage(p,cells,profile,D,flow)
        ts=np.unique(np.r_[np.arange(dt,duration,dt),duration])
        yy=stage.propagate(y,ts);times.extend(elapsed+ts);data.extend(yy);y=yy[-1];elapsed+=duration
    return np.asarray(times),np.asarray(data)


def metrics(p,cells,times,temperatures,segments):
    x=(np.arange(cells)+.5)*p['L']/cells;outside=x>=p['jet_m']
    outside_t=temperatures[:,outside]
    return {'floor_c':float(temperatures.min()),'outside_ceiling_c':float(outside_t.max()),
            'outside_span_c':float(np.ptp(outside_t,axis=1).max()),
            'final_outlet_c':float(temperatures[-1,-1]),'final_mean_c':float(temperatures[-1].mean()),
            'coldest_final_x_m':float(x[np.argmin(temperatures[-1])]),
            'command_l':float(sum(d*q/60 for d,q in segments)),
            'sample_s':float(np.max(np.diff(times))),
            'sampled_physical_passed':bool(temperatures.min()>=p['floor'] and outside_t.max()<=p['ceiling'] and np.ptp(outside_t,axis=1).max()<=p['span'])}
