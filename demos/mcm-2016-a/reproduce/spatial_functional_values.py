"""Scope-aware consumer of an independently checked spatial functional."""
from pathlib import Path
from fractions import Fraction
import hashlib,json,math

def _integer(text):
    if not isinstance(text,str) or not text or len(text)>20000:
        raise ValueError('Invalid rational integer')
    sign=-1 if text.startswith('-') else 1
    digits=text[1:] if sign<0 else text
    if not digits or any(c<'0' or c>'9' for c in digits):raise ValueError('Invalid rational digits')
    out=0
    for i in range(0,len(digits),1000):
        chunk=digits[i:i+1000];out=out*10**len(chunk)+int(chunk)
    return sign*out

def spatial_functional_values(root):
    folder=Path(root)/'reference/spatial-functional';read=lambda n:json.loads((folder/n).read_text())
    manifest=read('manifest.json')
    for name,digest in manifest['members'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:raise ValueError('Spatial functional member stale')
    for name,digest in manifest['external_archives'].items():
        if hashlib.sha256((folder.parent/name).read_bytes()).hexdigest()!=digest:raise ValueError('Spatial functional external input stale')
    source=read('potential-results.json');exact=read('exact-checks.json')
    if exact['source_sha256']!=hashlib.sha256((folder/'potential-results.json').read_bytes()).hexdigest():raise ValueError('Spatial functional source stale')
    expected={('whole-horizon-exclusion','network96'),('fixed-region-exclusion','network96'),('fixed-region-exclusion','network288'),('fixed-region-exclusion','network768')}
    if len(source['records'])!=8 or len(exact['checks'])!=8 or len(exact['negative_checks'])!=8:raise ValueError('Spatial functional coverage differs')
    identities={(r['archive'],r['network'],r['sign']) for r in exact['checks']}
    if identities!={(a,b,sign) for a,b in expected for sign in [-1,1]}:raise ValueError('Spatial functional identities differ')
    negative_ids={(r['archive'],r['network'],r['mutation']) for r in exact['negative_checks']}
    if negative_ids!={(a,b,defect) for a,b in expected for defect in ['zero_weight','zero_dual']}:raise ValueError('Spatial functional negative scope differs')
    time_bounds={}
    for row in exact['checks']:
        key=(row['archive'],row['network'])
        if key not in expected or row['sign'] not in [-1,1]:raise ValueError('Spatial functional scope differs')
        gap=Fraction(_integer(row['gap_exact_numerator']),_integer(row['gap_exact_denominator']))
        if row['positive']!=(gap>0) or (gap>0)!=(row['sign']==-1):raise ValueError('Spatial functional positivity differs')
        if not math.isclose(float(gap),row['gap_display'],abs_tol=1e-12):raise ValueError('Spatial functional display differs')
        if row['sign']==-1:
            ratio=Fraction(_integer(row['safe_time_exact_numerator']),_integer(row['safe_time_exact_denominator']))
            bound=row['strict_safe_time_upper_integer_s']
            if not 0<ratio<bound<1800 or row['exact_time_below_integer'] is not True:raise ValueError('Spatial functional time bound differs')
            time_bounds[key]=bound
    if set(time_bounds)!=expected or any(x['positive'] is not False for x in exact['negative_checks']):raise ValueError('Spatial functional negative evidence differs')
    transfer=read('transfer-exact-checks.json');tr=read('transfer-results.json')['records']
    frozen=next(r['weights'] for r in source['records'] if r['archive']=='whole-horizon-exclusion' and r['network']=='network96' and r['sign']==-1)
    if len(tr)!=3 or not all(math.isclose(r['D'],v,rel_tol=1e-14) for r,v in zip(tr,[.0003,.001,.003])) or any(r['weights']!=frozen for r in tr):raise ValueError('Fixed-weight transfer was refitted')
    if len(transfer['checks'])!=3 or [x['positive'] for x in transfer['checks']]!=[True,False,False]:raise ValueError('Fixed-weight transfer scope differs')
    if transfer['source_sha256']!=hashlib.sha256((folder/'transfer-results.json').read_bytes()).hexdigest():raise ValueError('Fixed-weight transfer stale')
    return {'safe_time_upper_s':time_bounds,'scope':'signed functional; specified finite networks only','exact':exact}
