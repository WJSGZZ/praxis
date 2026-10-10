from pathlib import Path
import sys,time,json
import numpy as np
from scipy.linalg import expm
from scipy.optimize import brentq
b=Path(__file__).resolve().parent;sys.path.insert(0,str(b.parents[1]/'code'));from model import BASE,network
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);output=parser.parse_args().output
if output.exists():raise FileExistsError(output)
start=time.monotonic();H=1800.;rows=[]
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
 return {'D':D,'delay':delay,'q':q,'water_l':q*(H-delay)/60,'terminal_cell':i,'second_cell_gap':gap,'Fq':float(fq[i]),'Fd':float(fd[i]),'water_delay_derivative_l_per_s':float(slope)}
for D in [.0007,.001,.002,.003]:rows.append(calc(D));assert time.monotonic()-start<120
print(json.dumps(rows,indent=2))
if rows[0]['water_delay_derivative_l_per_s']*rows[-1]['water_delay_derivative_l_per_s']<0:
 Droot=brentq(lambda D:calc(D)['water_delay_derivative_l_per_s'],.0007,.003,xtol=1e-11);root=calc(Droot)
else:root=None
checks=[]
for x in rows+([root] if root else []):
 # One-sided difference at d=0, two step sizes, using newly solved q.
 fds=[(calc(x['D'],dt)['water_l']-x['water_l'])/dt for dt in [.1,.01]]
 checks.append({'D':x['D'],'analytic_slope':x['water_delay_derivative_l_per_s'],'finite_difference_slopes':fds})
r={'elapsed_s':time.monotonic()-start,'rows':rows,'local_root':root,'difference_checks':checks,'scope':'Local terminal-floor policy branch only. Full trajectory physical constraints and independent direct RHS not yet checked; candidate mathematical mechanism, not adopted recommendation/global optimum.'};output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['elapsed_s']<120
