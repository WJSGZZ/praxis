from pathlib import Path
import sys,json,time,hashlib
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
b=Path(__file__).resolve().parent;sys.path.insert(0,str(b.parents[1]/'code'));from model import BASE,network
r=json.loads((b/'timing-results.json').read_text());start=time.monotonic();rows=[]
def independent(D,q):
 n=network({**BASE,'D':D});C=n['cap'];G=n['G'];ha=n['ha'];hb=n['hb'];N=len(C);B=np.zeros((N,N));h=np.zeros(N);path=[(i*4+2)*3+2 for i in range(8)]
 for j,i in enumerate(path):
  beta=4180*1000/60000/C[i];B[i,i]-=beta
  if j:B[i,path[j-1]]+=beta
  else:h[i]+=50*beta
 A=(G-np.diag(ha+hb))/C[:,None]+q*B;v=(22*ha+34*hb)/C+q*h;y0=np.full(N,40.);z0=-q*(B@y0+h)
 def rhs(t,x):
  y,zq,zd=np.split(x,3);return np.r_[A@y+v,A@zq+B@y+h,A@zd]
 sol=solve_ivp(rhs,(0,1800),np.r_[y0,np.zeros(N),z0],method='DOP853',rtol=1e-11,atol=1e-12,max_step=10,dense_output=True);assert sol.success
 samples=sol.sol(np.arange(1801.)).T;ys=samples[:,:N];end=ys[-1];i=int(np.argmin(end));fq=samples[-1,N+i];fd=samples[-1,2*N+i];slope=(1800*(-fd/fq)-q)/60
 second=np.max(abs(A@(A@y0+v)));assert (A-np.diag(np.diag(A))).min()>=0 and A.sum(axis=1).max()<0
 e=second/8+2e-6;env={'floor':float(ys.min()-e),'ceiling':float(ys[:,n['region']].max()+e),'spread':float(np.ptp(ys[:,n['region']],axis=1).max()+2*e)}
 return {'D':D,'q':q,'terminal_cell':i,'terminal_min':float(end[i]),'Fq':float(fq),'Fd':float(fd),'slope':float(slope),'envelope':env}
for x in r['rows']+[r['local_root']]:
 row=independent(x['D'],x['q']);assert abs(row['terminal_min']-39.03)<1e-7 and row['terminal_cell']==x['terminal_cell'];assert abs(row['Fq']-x['Fq'])<1e-7 and abs(row['slope']-x['water_delay_derivative_l_per_s'])<1e-8
 env=row['envelope'];assert env['floor']>39 and env['ceiling']<41 and env['spread']<1.5;rows.append(row)
# Independent q branch and signs in a displayed local root bracket.
root_rows=[]
for D in [.00137752,.00137754]:
 q=brentq(lambda q:independent(D,q)['terminal_min']-39.03,.5,1.,xtol=1e-10);row=independent(D,q);root_rows.append(row)
assert root_rows[0]['slope']>0 and root_rows[1]['slope']<0
out={'elapsed_s':time.monotonic()-start,'independent_rows':rows,'local_sign_bracket':root_rows,'timing_source_sha256':hashlib.sha256((b/'timing-results.json').read_bytes()).hexdigest(),'scope':'Direct physical stream reconstruction and DOP853 augmented sensitivities vs matrix exponential Frechet producer. Floating bracket, integration allowance2e-6, no interval arithmetic/root uniqueness/global optimum guarantee. Strict physical envelopes at checked points plus unique terminal binding/Fqpositive support local IFT branch.'};assert out['elapsed_s']<120
out['checker_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();print(json.dumps(out,indent=2))
