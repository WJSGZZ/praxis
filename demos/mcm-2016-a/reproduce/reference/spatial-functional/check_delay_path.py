from pathlib import Path
import sys,time,json,hashlib
import numpy as np
from scipy.integrate import solve_ivp
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parents[1]/'code'))
from model import BASE,network
from scipy.linalg import expm
from scipy.optimize import brentq
H=1800.
started=time.monotonic()
def check(x,step=1.):
 D,q,d=x['D'],x['q'],x['delay'];n=network({**BASE,'D':D});C=n['cap'];N=len(C);ha=n['ha'];hb=n['hb'];A0=(n['G']-np.diag(ha+hb))/C[:,None];v0=(22*ha+34*hb)/C;B=np.zeros((N,N));h=np.zeros(N);path=[(i*4+2)*3+2 for i in range(8)]
 for j,i in enumerate(path):
  beta=4180000/60000/C[i];B[i,i]-=beta
  if j:B[i,path[j-1]]+=beta
  else:h[i]+=50*beta
 A=A0+q*B;v=v0+q*h;y0=np.full(N,40.)
 def integrate(a,b,initial,horizon,augmented=False):
  if augmented:
   def rhs(t,z):
    y,sq,sd=np.split(z,3);return np.r_[a@y+b,a@sq+B@y+h,a@sd]
  else:rhs=lambda t,z:a@z+b
  sol=solve_ivp(rhs,(0,horizon),initial,method='DOP853',rtol=1e-11,atol=1e-12,max_step=10,dense_output=True);assert sol.success
  ts=np.linspace(0,horizon,max(2,int(np.ceil(horizon/step))+1));return sol.sol(ts).T
 passive=integrate(A0,v0,y0,d) if d else y0[None,:]
 ystart=passive[-1];active=integrate(A,v,np.r_[ystart,np.zeros(N),-q*(B@ystart+h)],1800-d,True)
 ys=active[:,:N];end=ys[-1];i=int(np.argmin(end));fq=active[-1,N+i];fd=active[-1,2*N+i];slope=((1800-d)*(-fd/fq)-q)/60
 assert i==x['terminal_cell'] and abs(end[i]-39.03)<1e-7 and abs(slope-x['water_delay_derivative_l_per_s'])<1e-8
 env=[]
 for a,b,y,initial in [(A0,v0,passive,y0),(A,v,ys,ystart)]:
  assert (a-np.diag(np.diag(a))).min()>=0 and a.sum(axis=1).max()<0
  allowance=float(np.max(abs(a@(a@initial+b)))*step**2/8+2e-6)
  env.append({'floor':float(y.min()-allowance),'ceiling':float(y[:,n['region']].max()+allowance),'spread':float(np.ptp(y[:,n['region']],axis=1).max()+2*allowance)})
 qualified=all(e['floor']>=39 and e['ceiling']<=41 and e['spread']<=1.5 for e in env)
 minimum_index,minimum_cell=np.unravel_index(np.argmin(ys),ys.shape)
 minimum_time=minimum_index*(1800-d)/(len(ys)-1)
 aug=np.zeros((N+1,N+1));aug[:N,:N]=A;aug[:N,N]=v
 matrix_minimum=float((expm(aug*minimum_time)@np.r_[ystart,1])[minimum_cell])
 assert abs(matrix_minimum-ys[minimum_index,minimum_cell])<1e-7
 return {'sample_min_time_s':float(d+minimum_time),'sample_min_cell':int(minimum_cell),'matrix_at_sample_min_c':matrix_minimum,'D':D,'delay':d,'q':q,'water_l':x['water_l'],'slope':float(slope),'terminal_cell':i,'terminal_min_c':float(end[i]),'envelopes':env,'qualified':qualified,'sample_min_c':float(min(passive.min(),ys.min()))}


def calc(D,delay=0,derivative=False):
 p={**BASE,'D':D};n=network(p);C=n['cap'];N=len(C);A0=(n['G']-np.diag(n['ha']+n['hb']))/C[:,None];v0=(22*n['ha']+34*n['hb'])/C;B=n['adv']/60000/C[:,None];h=n['hot']/60000/C;y0=np.full(N,40.)
 def matrix(q):
  A=A0+q*B;v=v0+q*h;aug=np.zeros((N+1,N+1));aug[:N,:N]=A;aug[:N,N]=v;return aug
 ystart=(expm(matrix(0)*delay)@np.r_[y0,1])[:N]
 def final(q):return (expm(matrix(q)*(H-delay))@np.r_[ystart,1])[:N]
 f=lambda q:final(q).min()-39.03
 assert f(0)<0 and f(3)>0
 q=brentq(f,0,3,xtol=1e-11);end=final(q);order=np.argsort(end);i=int(order[0]);gap=float(end[order[1]]-end[i]);A=matrix(q)
 # Differentiate the affine augmented propagator with the block Frechet identity.
 Q=np.zeros_like(A);Q[:N,:N]=B;Q[:N,N]=h
 K=np.block([[A,Q],[np.zeros_like(A),A]])
 fq=(expm(K*(H-delay))@np.r_[np.zeros(N+1),ystart,1])[:N]
 fd=(expm(A*(H-delay))@np.r_[-q*(B@ystart+h),0])[:N]
 assert fq[i]>0
 slope=((H-delay)*(-fd[i]/fq[i])-q)/60
 return {'D':D,'delay':delay,'q':q,'water_l':q*(H-delay)/60,'terminal_cell':i,'terminal_min_c':float(end[i]),'second_cell_gap':gap,'Fq':float(fq[i]),'Fd':float(fd[i]),'water_delay_derivative_l_per_s':float(slope)}

rows=[check(calc(.003,d),.1) for d in [700.,720.]]
assert rows[0]['qualified'] and rows[1]['sample_min_c']+2e-6<39
assert all(abs(x['q']*(1800-x['delay'])/60-x['water_l'])<1e-9 for x in rows)
result={'rows':rows,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'model_sha256':hashlib.sha256((root.parents[1]/'code/model.py').read_bytes()).hexdigest(),'elapsed_s':time.monotonic()-started,'scope':'Original96 network, D=.003, terminal39.03 branch; DOP853 independent stream with0.1s chord and assumed2e-6 error. Qualified700s and actual numerical violation at720s, not latest-delay/global-optimality claim.'}
assert result['elapsed_s']<120
print(json.dumps(result,indent=2))
