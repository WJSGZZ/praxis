"""Consume exact fixed-certificate parameter bounds, never infer feasibility."""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json
from spatial_functional_values import spatial_functional_values,_integer

def boundary_values(root):
    root=Path(root);spatial_functional_values(root)
    folder=root/'reference/spatial-functional';read=lambda name:json.loads((folder/name).read_text())
    data=read('boundary.json');checks=read('boundary-checks.json');thresholds=read('boundary-thresholds.json')
    digest=hashlib.sha256((folder/'boundary.json').read_bytes()).hexdigest()
    if checks['source_sha256']!=digest or thresholds['source_sha256']!=digest or checks['status']!='passed':raise ValueError('Boundary evidence stale')
    if checks['checker_sha256']!=hashlib.sha256((folder/'check_boundary.py').read_bytes()).hexdigest():raise ValueError('Boundary checker changed')
    fraction=lambda v:F(_integer(v[0]),_integer(v[1]))
    w=list(map(fraction,data['weights']));d=list(map(fraction,data['d']));hh=fraction(data['hh'])
    frozen=next(x['weights'] for x in read('potential-results.json')['records'] if x['archive']=='whole-horizon-exclusion' and x['network']=='network96' and x['sign']==-1)
    if w!=[F.from_float(float(x)) for x in frozen]:raise ValueError('Boundary weights refitted')
    if len(w)!=96 or len(data['boundary_rows'])!=12 or len(checks['exact_interval_checks'])!=7 or len(checks['direct_network_LP_diagnostics'])!=14:raise ValueError('Boundary scope changed')
    supports={k:(list(map(fraction,v['affine'])),[list(map(fraction,x)) for x in v['residuals']]) for k,v in data['supports'].items()}
    if set(supports)!={'end','q0','q3'} or any(len(a)!=4 or len(rr)!=98 or any(len(x)!=4 for x in rr) for a,rr in supports.values()):raise ValueError('Boundary dimensions changed')
    def dot(a,p):return sum(x*y for x,y in zip(a,p))
    def lower(k,p):a,rr=supports[k];return dot(a,p)+sum(min(F(0),dot(r,p)) for r in rr)
    def gap(s,l,z):
        p=[F(1),s,l,z];base=dot(d,p)
        return lower('end',p)-sum(w)-1800*max(-lower('q0',p)+base,-lower('q3',p)+base+3*hh)
    if gap(F(1),F(1),F(3,2))!=fraction(data['baseline_gap']):raise ValueError('Boundary baseline changed')
    expected={(l,z) for l in [F(4,5),F(1),F(6,5)] for z in [F(3,4),F(1),F(3,2),F(2)]}
    if {(fraction(x['loss_scale']),fraction(x['span_c'])) for x in data['boundary_rows']}!=expected:raise ValueError('Boundary slice identities changed')
    for row in data['boundary_rows']:
        l,z=map(fraction,[row['loss_scale'],row['span_c']])
        for interval in row['certified_intervals']:
            lo,hi=map(fraction,[interval['left'],interval['right']])
            if not F(1,2)<=lo<hi<=10 or gap((lo+hi)/2,l,z)<=0:raise ValueError('Invalid exclusion interval')
            if (gap(lo,l,z)>0)!=interval['left_included'] or (gap(hi,l,z)>0)!=interval['right_included']:raise ValueError('Boundary endpoint changed')
    roots={}
    for name,fn,direction in [('loss_root',lambda t:gap(F(1),t,F(3,2)),1),('span_root_c',lambda t:gap(F(1),F(1),t),-1)]:
        v=thresholds[name];lo,hi=F(v['lower']),F(v['upper'])
        if not 0<hi-lo<F(1,10**12) or direction*fn(lo)>=0 or direction*fn(hi)<=0:raise ValueError('Boundary root bracket invalid')
        roots[name]=(lo,hi)
    baseline=next(r for r in data['boundary_rows'] if fraction(r['loss_scale'])==1 and fraction(r['span_c'])==F(3,2))['certified_intervals'][0]
    dl,dh=[fraction(baseline[k])*F(3,10000) for k in ['left','right']]
    ceil=lambda x: -((-x.numerator)//x.denominator)
    floor=lambda x:x.numerator//x.denominator
    Dl=F(ceil(dl*10**8),10**8);Dh=F(floor(dh*10**8),10**8)
    loss=F(ceil(roots['loss_root'][1]*10**5),10**5);span=F(floor(roots['span_root_c'][0]*10**5),10**5)
    if not Dl<Dh or any(gap(s/F(3,10000),F(1),F(3,2))<=0 for s in [Dl,Dh]) or gap(F(1),loss,F(3,2))<=0 or gap(F(1),F(1),span)<=0:raise ValueError('Printed inward bound not certified')
    printed={'D_left':f'{float(Dl):.8f}','D_right':f'{float(Dh):.8f}','loss_min':f'{float(loss):.5f}','span_max':f'{float(span):.5f}'}
    return {'printed':printed,'roots':roots,'rows':data['boundary_rows'],'gap':gap,'scope':'Fixed-certificate exclusion, not a feasible strategy transition; original96network, common losses and fixed39/41bounds'}
