"""Archive-only flux replay and rational error enclosure. No model/producer import."""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,time
import numpy as np
root=Path(__file__).resolve().parent; start=time.monotonic()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=json.loads((root/'inputs.json').read_text())
for name,key in [('primitives.npz','primitives_sha256'),('enclosure-states.npz','states_sha256'),('enclosure.json','enclosure_sha256')]:
    assert sha(root/name)==inputs[key],name
assert inputs['grid']==[8,4,3] and inputs['flow_max_l_min']==3 and inputs['prefix_s']==790 and inputs['witness_relative_s']==86.5
assert all(inputs['parameters'][k]==v for k,v in {'D':.003,'initial':40.,'body_temp':34.,'air_temp':22.,'inlet_temp':50.,'horizon':1800.,'floor':39.}.items())
assert np.finfo(np.float64).nmant==52 and np.finfo(np.float64).eps==2**-52
data=np.load(root/'primitives.npz',allow_pickle=False)
for name,expected in inputs['array_hashes'].items():
    assert hashlib.sha256(data[name].tobytes()).hexdigest()==expected,name
    assert np.isfinite(data[name]).all()
G,C,ha,hb,adv,hot=(data[name] for name in ['G','cap','ha','hb','adv','hot'])
N=len(C);assert N==96 and (C>0).all()
path=np.array([(i*4+2)*3+2 for i in range(8)])
expected_adv=np.zeros((N,N));expected_hot=np.zeros(N)
for j,i in enumerate(path):
    expected_adv[i,i]=-4180000
    if j:expected_adv[i,path[j-1]]=4180000
    else:expected_hot[i]=4180000*50
assert np.array_equal(adv,expected_adv) and np.array_equal(hot,expected_hot)
Q=lambda x:F(float(x));dot=lambda a,x:sum((c*z for c,z in zip(a,x)),F(0))
A=[[(Q(G[i,j])-(Q(ha[i])+Q(hb[i]) if i==j else 0))/Q(C[i]) for j in range(N)] for i in range(N)]
v=[(22*Q(ha[i])+34*Q(hb[i]))/Q(C[i]) for i in range(N)]
B=[[Q(adv[i,j])/60000/Q(C[i]) for j in range(N)] for i in range(N)]
h=[Q(hot[i])/60000/Q(C[i]) for i in range(N)]
L0=max(sum(map(abs,row)) for row in A)
Lg=max(sum(abs(a)+3*abs(b) for a,b in zip(ar,br)) for ar,br in zip(A,B))
for i in range(N):
    assert all(A[i][j]>=0 and B[i][j]>=0 for j in range(N) if j!=i)
    assert sum(A[i])<0 and sum(B[i])<=0
    for low,sign in [(21,1),(51,-1)]:
        passive=low*sum(A[i])+v[i]
        assert sign*passive>0 and sign*(passive+3*max(low*sum(B[i])+h[i],0))>0
z=[40*sum(ar)+k for ar,k in zip(A,v)];assert max(z)<0
Az=[dot(ar,z) for ar in A];M3=max(abs(dot(ar,Az)) for ar in A)
hp=F(1,20);duration=F(173,2);steps=1000000;hu=duration/steps;R=F(1,10**9)
assert max(-hp*A[i][i] for i in range(N))<1
assert max(-hu*(A[i][i]+3*B[i][i]) for i in range(N))<1
# Physical flux evaluation DAG absolute-magnitude bound on |y|<=52.
S=max((52*sum(abs(Q(c)) for c in G[i])+74*Q(ha[i])+86*Q(hb[i])+ (209*104 if i in path else 0))/Q(C[i]) for i in range(N))
u=F(1,2**53);gamma=(4*N+64)*u/(1-(4*N+64)*u)
def map_rounding(step):
    dh=abs(Q(float(step))-step)
    return gamma*(8*52*(1+step*Lg)**2+16*step*(S+1)*(1+step*Lg))+2*dh*(S+1)*(1+step*Lg)+F(1,10**280)
assert map_rounding(hp)<R and map_rounding(hu)<R
# Exact stable maps preserve [21,51]. Rounded maps stay within accumulated
# R distance; the SSP trial adds one R. These inequalities close the induction.
assert 18001*R<1 and (18000+steps+1)*R<1
def passive(y):return (G@y-ha*(y-22)-hb*(y-34))/C
def upper(y):
    out=passive(y)
    upstream=np.concatenate(([50.],y[path[:-1]]))
    out[path]+=(209*np.maximum(upstream-y[path],0))/C[path]
    return out
y=np.full(N,40.);prefix=None
for k in range(18000):
    trial=y+float(hp)*passive(y)
    y=(y+trial+float(hp)*passive(trial))/2
    if k==15799:prefix=y.copy()
    if k%1000==0:assert time.monotonic()-start<90
passive900=y.copy();dp=790*hp**2*M3/6+15800*R;d900=900*hp**2*M3/6+18000*R
g0=[dot(ar,list(map(Q,prefix)))+k+3*max(dot(br,list(map(Q,prefix)))+hh,0) for ar,k,br,hh in zip(A,v,B,h)]
M2=Lg*(max(map(abs,g0))+Lg*dp)
y=prefix.copy()
for k in range(steps):
    y=y+float(hu)*upper(y)
    if k%10000==0:assert time.monotonic()-start<90
radius=dp+duration**2*M2/(2*steps)+steps*R
bound=Q(y[89])+radius;assert bound<39
cell900=int(np.argmin(passive900));assert Q(passive900[cell900])+d900<39
saved=np.load(root/'enclosure-states.npz',allow_pickle=False)
differences={name:float(np.max(np.abs(actual-saved[name]))) for name,actual in [('passive790',prefix),('passive900',passive900),('upper_end',y)]}
assert max(differences.values())<1e-7
enc=json.loads((root/'enclosure.json').read_text());decode=lambda d:F(int(d['numerator']),int(d['denominator']))
for name,value in [('L0',L0),('Lg',Lg),('M3',M3)]:assert decode(enc[name])==value
assert decode(enc['strict_upper_c'])==Q(enc['computed_witness_c'])+decode(enc['error_radius'])<39
assert decode(enc['error_radius'])==decode(enc['passive790_error'])+duration*decode(enc['coefficient_error_upper'])+duration**2*decode(enc['M2'])/(2*steps)+steps*R
encode=lambda x:{'numerator':str(x.numerator),'denominator':str(x.denominator),'display':float(x)}
result={'contract':{'grid':[8,4,3],'D':.003,'initial_c':40,'contact_c':34,'ambient_c':22,'inlet_c':50,'q_max_l_min':3,'prefix_s':790,'relative_s':86.5,'horizon_s':1800,'floor_c':39,'cell':89,'passive_steps':15800,'active_steps':steps},'error_terms':{'passive790':encode(dp),'M2':encode(M2),'round_step':encode(R)},'model_sha256':inputs['model_sha256'],'status':'passed','elapsed_s':time.monotonic()-start,'checker_sha256':sha(Path(__file__)),'inputs_sha256':sha(root/'inputs.json'),'witness_c':float(y[89]),'error_radius':encode(radius),'strict_upper_c':encode(bound),'passive900_strict_upper_c':encode(Q(passive900[cell900])+d900),'rounding_passive':encode(map_rounding(hp)),'rounding_active':encode(map_rounding(hu)),'state_domain_cumulative_radius':encode((18000+steps+1)*R),'producer_replay_max_difference_c':differences,'scope':'Archive-only physical-flux replay, independently assembled exact operators and truncation/rounding radius. Original fixed 96-cell binary primitive network, D=.003, q in [0,3], 790s zero prefix. IEEE64 ordinary rounding assumptions; not an interval package, PDE, empirical validation, latest-start threshold or award calibration.'}

print(json.dumps(result,indent=2))
