"""Conservative three-dimensional thermal network; coefficients are literature-anchored scenario values, see literature.py."""
import argparse, json
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm_multiply
from scipy.optimize import brentq

BASE=dict(L=1.5,W=.65,H=.23,body_volume=.060,body_area=1.15,body_temp=34.,air_temp=22.,initial=40.,inlet_temp=50.,rho=1000.,cp=4180.,h_surface=25.,h_wall=6.5,h_body=25.,D=1e-3,body_shape=[.40,.16,.12],foam=1.,horizon=1800.,floor=39.,ceiling=41.,span=1.5)

def network(p, grid=(8,4,3)):
    nx,ny,nz=grid; n=nx*ny*nz; step=np.array([p['L']/nx,p['W']/ny,p['H']/nz]); dv=float(np.prod(step))
    xyz=np.array([[(i+.5)*step[0],(j+.5)*step[1],(k+.5)*step[2]] for i in range(nx) for j in range(ny) for k in range(nz)])
    center=np.array([p['L']*.55,p['W']/2,p['H']*.45]); widths=np.array(p['body_shape'])
    weights=np.exp(-.5*np.sum(((xyz-center)/widths)**2,axis=1)); weights/=weights.sum()
    occupied=p['body_volume']*weights/dv
    if occupied.max()>=.95: raise ValueError('Body displacement exceeds cell capacity: refine body representation')
    vol=dv*(1-occupied); cap=p['rho']*p['cp']*vol
    ha=np.zeros(n); hb=p['h_body']*p['body_area']*weights
    G=np.zeros((n,n)); adv=np.zeros((n,n)); idx=lambda i,j,k:(i*ny+j)*nz+k
    for i in range(nx):
      for j in range(ny):
       for k in range(nz):
        a=idx(i,j,k)
        # Air and shell conductances use actual 3-D face areas.
        if k==nz-1: ha[a]+=p['h_surface']*p['foam']*step[0]*step[1]
        if k==0: ha[a]+=p['h_wall']*step[0]*step[1]
        if i in (0,nx-1): ha[a]+=p['h_wall']*step[1]*step[2]
        if j in (0,ny-1): ha[a]+=p['h_wall']*step[0]*step[2]
        for axis,(ii,jj,kk) in enumerate([(i+1,j,k),(i,j+1,k),(i,j,k+1)]):
         if ii<nx and jj<ny and kk<nz:
          b=idx(ii,jj,kk); area=dv/step[axis]
          g=p['rho']*p['cp']*p['D']*area/step[axis]*min(1-occupied[a],1-occupied[b])
          G[a,b]+=g; G[b,a]+=g; G[a,a]-=g; G[b,b]-=g
    # An explicit conservative surface stream models inlet-to-overflow short circuit.
    path=[idx(i,ny//2,nz-1) for i in range(nx)]
    for a in path: adv[a,a]-=p['rho']*p['cp']
    for a,b in zip(path,path[1:]): adv[b,a]+=p['rho']*p['cp']
    hot=np.zeros(n); hot[path[0]]=p['rho']*p['cp']*p['inlet_temp']
    return dict(cap=cap,vol=vol,ha=ha,hb=hb,G=G,adv=adv,hot=hot,xyz=xyz,outlet=path[-1],grid=list(grid))

def system(p,net,q):
    B=net['G']+q*net['adv']-np.diag(net['ha']+net['hb'])
    b=net['ha']*p['air_temp']+net['hb']*p['body_temp']+q*net['hot']
    A=B/net['cap'][:,None]; b=b/net['cap']
    aug=np.zeros((len(b)+1,len(b)+1));aug[:-1,:-1]=A;aug[:-1,-1]=b
    return csr_matrix(aug)

def evolve(p,net,q,y,seconds,dt=10.):
    if seconds<=0: return np.array([0.]),np.array([y])
    steps=max(1,int(np.ceil(seconds/dt)));ts=np.linspace(0,seconds,steps+1)
    yy=expm_multiply(system(p,net,q),np.r_[y,1.],start=0,stop=seconds,num=steps+1,traceA=None)[:,:-1]
    return ts,yy

def trajectory(p,net,q_lpm,delay=0.,dt=10.):
    q=q_lpm/60000.;a,ya=evolve(p,net,0.,np.full(len(net['cap']),p['initial']),delay,dt)
    b,yb=evolve(p,net,q,ya[-1],p['horizon']-delay,dt)
    t=np.r_[a,b[1:]+delay];y=np.vstack([ya,yb[1:]])
    return t,y

def metrics(p,net,t,y,q,delay):
    mean=y@net['vol']/net['vol'].sum()
    return dict(flow_lpm=float(q),delay_s=float(delay),water_l=float(q*(p['horizon']-delay)/60),min_temp=float(y.min()),max_temp=float(y.max()),max_span=float(np.ptp(y,axis=1).max()),final_mean=float(mean[-1]),final_min=float(y[-1].min()),final_max=float(y[-1].max()))

def candidate(p,net,delay):
    # Locate the first feasible crossing on a stated flow grid; no global monotonicity claim.
    t,y=trajectory(p,net,0,delay,dt=20)
    if y.min()>=p['floor']: return metrics(p,net,t,y,0,delay)
    _,coast=evolve(p,net,0,np.full(len(net['cap']),p['initial']),delay,20)
    if coast.min()<p['floor']-1e-9: return None
    f=lambda q: trajectory(p,net,q,delay,dt=20)[1].min()-(p['floor']+.03)
    bracket=None
    previous=0.
    for trial in np.linspace(.2,3.,15):
        if f(trial)>=0:
            bracket=(previous,trial);break
        previous=trial
    if bracket is None:return None
    q=brentq(f,*bracket,xtol=1e-7)
    t,y=trajectory(p,net,q,delay,dt=5);m=metrics(p,net,t,y,q,delay)
    if m['min_temp']<p['floor']-.002 or m['max_temp']>p['ceiling']+.002 or m['max_span']>p['span']+.002:return None
    return m

def search(p,net,delays=None):
    delays=np.arange(0,1201,120) if delays is None else delays
    feasible=[m for d in delays if (m:=candidate(p,net,float(d))) is not None]
    if not feasible:return dict(feasible=False)
    best=min(feasible,key=lambda m:m['water_l']);return dict(feasible=True,**best,candidates=feasible)

def analytic(p,net):
    ha=float(net['ha'].sum());hb=float(net['hb'].sum());C=float(net['cap'].sum());h=ha+hb;eq=(ha*p['air_temp']+hb*p['body_temp'])/h
    coast=C/h*np.log((p['initial']-eq)/(p['floor']-eq));loss=ha*(p['floor']-p['air_temp'])+hb*(p['floor']-p['body_temp'])
    hold=60000*loss/(p['rho']*p['cp']*(p['inlet_temp']-p['floor']))
    exact=hold*max(0,p['horizon']-coast)/60
    bound=max(0,(loss*p['horizon']-C*(p['initial']-p['floor']))/(p['rho']*p['cp']*(p['inlet_temp']-p['floor'])))*1000
    constant=60000*(ha*(p['initial']-p['air_temp'])+hb*(p['initial']-p['body_temp']))/(p['rho']*p['cp']*(p['inlet_temp']-p['initial']))
    return dict(volume_l=float(net['vol'].sum()*1000),air_conductance=ha,body_conductance=hb,equilibrium=eq,coast_s=coast,hold_lpm=hold,mixed_optimum_l=exact,energy_lower_bound_l=bound,constant_at_target_lpm=constant,constant_at_target_l=constant*p['horizon']/60)

def run(output):
    output.mkdir(parents=True,exist_ok=True);p=BASE.copy();net=network(p);a=analytic(p,net);best=search(p,net)
    if not best.get('feasible'):raise RuntimeError('No feasible base policy; preserve failure rather than fabricate a policy')
    variants={'weak mixing':dict(D=3e-4),'strong mixing':dict(D=3e-3),'moving with added surface loss':dict(D=3e-3,h_surface=30.),'loose comfort':dict(floor=38.),'tight comfort':dict(floor=39.5),'foam':dict(foam=.4),'shallow wide':dict(L=1.7,W=.75,H=(p['L']*p['W']*p['H'])/(1.7*.75)),'deep narrow':dict(L=1.3,W=.6,H=(p['L']*p['W']*p['H'])/(1.3*.6)),'small bath':dict(H=.20),'large bath':dict(H=.27),'larger body':dict(body_volume=.075,body_area=1.35),'long body':dict(body_shape=[.48,.12,.10]),'warmer skin':dict(body_temp=36.),'cooler skin':dict(body_temp=32.),'high loss':dict(h_surface=36.,h_wall=8.5,h_body=40.),'low loss':dict(h_surface=17.,h_wall=4.5,h_body=12.),'cool supply':dict(inlet_temp=45.)}
    scenarios={}
    for label,changes in variants.items():
        pp={**p,**changes}; nn=network(pp); scenarios[label]=dict(changes=changes,analytic=analytic(pp,nn),policy=search(pp,nn))
    t,y=trajectory(p,net,best['flow_lpm'],best['delay_s'],dt=5)
    np.savez(output/'trajectory.npz',t=t,T=y,xyz=net['xyz'],volume=net['vol'])
    # Independent policy replay on a finer spatial mesh, with unchanged physical settings.
    fine=network(p,(12,6,4));fine_best=search(p,fine)
    _,yf=trajectory(p,fine,best['flow_lpm'],best['delay_s'],dt=5)
    grid=dict(fine_policy=fine_best,coarse_policy_on_fine=metrics(p,fine,t,yf,best['flow_lpm'],best['delay_s']))
    result=dict(parameters=p,grid=net['grid'],analytic=a,policy=best,scenarios=scenarios,mesh=grid,scope='Conditional thermal-network scenarios; no measured bathtub data; candidate-family optimum only.')
    (output/'results.json').write_text(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();r=run(args.output);print(json.dumps({'policy':r['policy'],'analytic':r['analytic']},indent=2))
