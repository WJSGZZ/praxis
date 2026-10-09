"""Portable common-reserve replay; archived producers and new guards stay distinct.

The archived 5,796 records were produced by the byte-preserved sources in
reference/. This relocated implementation is checked separately on selected
cases. Its contraction/chord bounds are conditional floating-point evidence.
"""
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix, block_diag, diags, bmat
from scipy.sparse.linalg import expm_multiply
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'code'))
import model


GRIDS = ((8, 4, 3), (12, 6, 4), (16, 8, 6))
METRICS = ('lower_bound_c', 'upper_bound_c', 'span_bound_c',
           'min_temp', 'max_temp', 'max_span', 'water_l')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_records(manifest, bank, rows, independent):
    """Check identities, conditions and arithmetic, not just receipt hashes."""
    require(manifest['status'] == independent['status'] == 'completed', 'Incomplete qualification')
    require(manifest['grids'] == [list(g) for g in GRIDS], 'Changed grids')
    require(manifest['common_reserve'] == dict(floor=39.13, ceiling=40.9, span=1.4), 'Changed common reserve')
    require(manifest['physical_limits'] == dict(floor=39, ceiling=41, span=1.5), 'Changed physical limits')
    prior = [dict(zip(bank['parameter_grid'], v)) for v in itertools.product(*bank['parameter_grid'].values())]
    groups = {(b['structure'], b['design']): b for b in bank['banks']}
    require(len(groups) == len(bank['banks']) == 6, 'Changed or duplicate banks')
    expected_groups = {(s, d, g) for s, d in groups for g in GRIDS}
    require(len(rows) == len(expected_groups) and
            {(r['structure'], r['design'], tuple(r['grid'])) for r in rows} == expected_groups,
            'Missing or duplicate qualification groups')
    require(set(manifest['policies']) == {'passive', 'pulse'}, 'Changed policies')
    for flows in manifest['policies'].values():
        validate_replay_inputs([{**model.BASE, **prior[0]}], GRIDS[0], 'surface', None, flows)
    volumes = {d: 5*sum(q) for d, q in manifest['policies'].items()}
    expected = {(s, d, g, i) for (s, d), b in groups.items() for g in GRIDS for i in b['indices']}
    records, extrema = {}, set()
    for group in rows:
        key = (group['structure'], group['design'], tuple(group['grid']))
        require(len(group['records']) == len(groups[key[:2]]['indices']), 'Bank cardinality changed')
        for r in group['records']:
            idx = r['prior_index']
            require(type(idx) is int and 0 <= idx < len(prior), 'Invalid prior identity')
            identity = (*key, idx)
            require(identity not in records and identity in expected, 'Duplicate or unexpected model identity')
            require(r['parameters'] == prior[idx], 'Changed model coefficients')
            require(all(type(r[k]) in (float, int) and math.isfinite(r[k]) for k in METRICS), 'Nonfinite or invalid metric')
            require(r['lower_bound_c'] <= r['min_temp'] <= r['max_temp'] <= r['upper_bound_c'] and
                    0 <= r['max_span'] <= r['span_bound_c'], 'Bounds do not enclose sampled extrema')
            require(r['lower_bound_c'] >= 39.13 and r['upper_bound_c'] <= 40.9 and r['span_bound_c'] <= 1.4,
                    'Common-reserve envelope failed')
            require(all(r[k] is True for k in ('sampled_passed', 'continuous_passed', 'fair_sample_passed', 'fair_reserve_passed')),
                    'Qualification flag disagrees')
            require(abs(r['water_l']-volumes[key[1]]*prior[idx]['flow_multiplier']) < 1e-8, 'Delivered water mismatch')
            require(r['max_initial_gap_s'] == 1 and r['refinement_depth_cap'] == 4 and
                    type(r['midpoint_count']) is int and r['midpoint_count'] >= 0, 'Invalid interval metadata')
            require(math.isfinite(r['min_off_diagonal']) and r['min_off_diagonal'] >= -1e-12 and
                    math.isfinite(r['max_row_sum']) and r['max_row_sum'] <= 1e-12, 'Contraction premise failed')
            records[identity] = r
        for metric, choose in [('min_temp', min), ('max_temp', max), ('max_span', max)]:
            selected = choose(group['records'], key=lambda x: x[metric])
            extrema.add((*key, selected['prior_index']))
    require(set(records) == expected, 'Exact canonical bank coverage differs')
    require(manifest['coverage']['groups'] == len(rows) and manifest['coverage']['unique_objects'] == len(records), 'Coverage metadata differs')
    reuse = manifest['reuse_provenance']
    reuse_keys = {(s,d,tuple(g)) for s,d,g in reuse['groups']}
    reused = [g for g in rows if (g['structure'],g['design'],tuple(g['grid'])) in reuse_keys]
    require(len(reused) == len(reuse_keys) == 3 and
            reuse_keys == {('surface_fixed','passive',g) for g in GRIDS}, 'Reuse coverage differs')
    require(reuse['policy'] == manifest['policies']['passive'] and
            reuse['shared_inputs'] == manifest['inputs'] and
            reuse['producer_sources'] == manifest['producer_sources'], 'Reuse policy or inputs changed')
    require(hashlib.sha256(json.dumps(reused,separators=(',',':')).encode()).hexdigest() == reuse['records_sha256'],
            'Reused records differ from predecessor')
    require(manifest['coverage']['reused_objects'] == sum(len(g['records']) for g in reused) == 1530 and
            manifest['coverage']['new_objects'] == len(records)-1530, 'Reuse cardinality differs')
    seen = set()
    for r in independent['rows']:
        identity = (r['structure'], r['design'], tuple(r['grid']), r['prior_index'])
        require(identity in extrema and identity not in seen, 'Independent check identity differs')
        seen.add(identity)
        actual = r['actual']; bound = records[identity]
        route, capacity = bank['structures'][identity[0]]
        require(actual['route'] == route and actual['body_capacity_j_per_k'] == capacity and actual['sample_s'] == 1,
                'Independent structure differs')
        require(all(math.isfinite(actual[k]) for k in ('min_temp','max_temp','max_span','water_l',
                    'instantaneous_balance_residual_w','integrated_balance_residual_j')), 'Independent result nonfinite')
        require(actual['min_temp'] >= max(39.13, bound['lower_bound_c']-2e-6) and
                actual['max_temp'] <= min(40.9, bound['upper_bound_c']+2e-6) and
                actual['max_span'] <= min(1.4, bound['span_bound_c']+4e-6), 'Independent limits or enclosure failed')
        require(abs(actual['water_l']-bound['water_l']) < 1e-8 and
                actual['instantaneous_balance_residual_w'] < 1e-6 and
                actual['integrated_balance_residual_j'] < .1, 'Independent energy/water mismatch')
    require(seen == extrema, 'Independent extremal coverage missing')
    require(len(manifest['rejected_candidates']) == 2, 'Rejected candidates missing')
    for f in manifest['rejected_candidates']:
        idx = f['identity']['prior_index']; design = f['identity']['design']; actual = f['actual']
        require(f['identity']['structure'] == 'surface_fixed' and tuple(f['identity']['grid']) == GRIDS[0]
                and idx in groups[('surface_fixed', design)]['indices'], 'Rejected identity differs')
        require(39 <= actual['min_temp'] < 39.13 and actual['max_temp'] <= 41 and actual['max_span'] <= 1.5,
                'Failure no longer a common-reserve counterexample')
        require(abs(actual['water_l']-5*sum(f['flow_lpm'])*prior[idx]['flow_multiplier']) < 1e-8,
                'Rejected candidate water differs')
    delta = volumes['passive']-volumes['pulse']
    require(delta > 0, 'Unexpected cost order')
    return dict(manifest=manifest, rows=rows, independent=independent, prior=prior,
                objects=len(records), groups=len(rows), volumes=volumes, delta_l=delta,
                crossover=math.floor(6/delta)+1, strict_n_greater_than=6/delta,
                lower=min(r['lower_bound_c'] for r in records.values()),
                upper=max(r['upper_bound_c'] for r in records.values()),
                spread=max(r['span_bound_c'] for r in records.values()),
                independent_cases=len(seen))


def common_reserve_values(root=ROOT):
    root = Path(root)
    manifest = json.loads((root/'reference/common-reserve.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, digest in {**manifest['inputs'], **manifest['producer_sources']}.items():
        require(sha(root/name) == digest, 'Common-reserve source/input stale: '+name)
    archive = root/'reference/common-reserve.npz'
    independent_path = root/'reference/common-reserve-independent.json'
    require(sha(archive) == manifest['archive_sha256'] and sha(independent_path) == manifest['independent_sha256'], 'Common-reserve archive stale')
    independent = json.loads(independent_path.read_text())
    require(independent['qualification_archive_sha256'] == sha(archive), 'Independent qualification binding differs')
    with np.load(archive, allow_pickle=False) as data:
        rows = json.loads(data['records_utf8'].tobytes())
    bank = json.loads((root/'reference/structure-decision.json').read_text())
    return validate_records(manifest, bank, rows, independent)


def validate_replay_inputs(params, grid, route, capacity, flows):
    if not params or any(type(v) is not int for v in grid) or tuple(grid) not in GRIDS:
        raise ValueError('Nonempty bank and one of three declared grids required')
    if route not in ('surface','deep') or capacity not in (None,253310.):
        raise ValueError('Unsupported structure')
    if isinstance(capacity, bool):
        raise ValueError('Invalid capacity')
    if len(flows)!=6 or any(isinstance(f,bool) or not isinstance(f,(int,float)) or not math.isfinite(f) or not 0<=f<=2 for f in flows):
        raise ValueError('Six finite flows in [0,2] L/min required')
    varying={'D','h_surface','h_body','flow_multiplier'}
    for p in params:
        if set(p)!=set(model.BASE)|varying or any(p.get(k)!=v for k,v in model.BASE.items() if k not in varying):
            raise ValueError('Frozen geometry changed')
        if any(isinstance(p.get(k),bool) or not isinstance(p.get(k),(int,float)) or not math.isfinite(p[k]) or p[k]<=0 for k in varying):
            raise ValueError('Finite positive bank coefficients required')

GEOMETRY={}
def geometry(grid):
 key=tuple(grid)
 if key not in GEOMETRY:
  net=model.network(model.BASE,grid);nx,ny,nz=grid;N=len(net['cap'])
  area=model.BASE['L']/nx*model.BASE['W']/ny
  surf=np.array([area*model.BASE['foam'] if i%nz==nz-1 else 0. for i in range(N)])
  GEOMETRY[key]=(net,csr_matrix(net['G'])/model.BASE['D'],surf,net['ha']-model.BASE['h_surface']*surf,net['hb']/model.BASE['h_body'])
 return GEOMETRY[key]

def matrices(params,grid,route,capacity):
 net,g,surface,fixed,hb_unit=geometry(grid);cap=net['cap'];N=len(cap);nx,ny,nz=grid
 idx=lambda i,j,k:(i*ny+j)*nz+k
 path=[idx(i,ny//2,nz-1) for i in range(nx)]
 if route=='deep':path=[idx(0,ny//2,k) for k in range(nz-1,-1,-1)]+[idx(i,ny//2,0) for i in range(1,nx)]+[idx(nx-1,ny//2,k) for k in range(1,nz)]
 elif route!='surface':raise ValueError('Unknown route')
 A=[];Q=[]
 for p in params:
  ha=fixed+p['h_surface']*surface;hb=p['h_body']*hb_unit
  water=diags(1/cap)@(p['D']*g-diags(ha+hb))
  body=csr_matrix(hb.reshape(1,-1)/capacity) if capacity is not None else csr_matrix((1,N))
  body_self=csr_matrix([[-hb.sum()/capacity]]) if capacity is not None else csr_matrix((1,1))
  a=bmat([[water,csr_matrix((hb/cap).reshape(-1,1)),csr_matrix((ha*p['air_temp']/cap).reshape(-1,1))],
          [body,body_self,csr_matrix((1,1))],[csr_matrix((1,N)),csr_matrix((1,1)),csr_matrix((1,1))]],format='csr')
  rows=[];cols=[];values=[]
  for j,c in enumerate(path):
   f=p['rho']*p['cp']/60000/cap[c]*p['flow_multiplier']
   rows.extend([c,c]);cols.extend([c,path[j-1] if j else N+1]);values.extend([-f,f if j else f*p['inlet_temp']])
  q=csr_matrix((values,(rows,cols)),shape=(N+2,N+2))
  A.append(a);Q.append(q)
 return A,Q,net

def check_premise(b,N):
 m=b[:N+1,:N+1];off=m-diags(m.diagonal());minimum=float(off.data.min()) if off.nnz else 0.
 rowsum=float(np.asarray(m.sum(1)).max())
 if minimum < -1e-12 or rowsum > 1e-12:raise ValueError('No derivative contraction')
 return minimum,rowsum

def segment_bounds(states,rates,curvatures,net,dt):
 N=len(net['cap']);water=states[:,:,:N];visible=water[:,:,net['region']]
 lo=water.min(2);hi=visible.max(2);span=np.ptp(visible,axis=2)
 # Constant coordinates have identically zero derivatives; body is included.
 first=np.max(abs(rates[:,:,:N+1]),axis=2);second=np.max(abs(curvatures[:,:,:N+1]),axis=2)
 radius=np.minimum(first[:-1]*dt/2,second[:-1]*dt*dt/8)
 return (np.minimum(lo[:-1],lo[1:])-radius-2e-6,
         np.maximum(hi[:-1],hi[1:])+radius+2e-6,
         np.maximum(span[:-1],span[1:])+2*radius+4e-6,
         lo.min(0),hi.max(0),span.max(0))

def replay(params,grid,route,capacity,flows,budget):
 validate_replay_inputs(params,grid,route,capacity,flows)
 A,Q,net=matrices(params,grid,route,capacity);N=len(net['cap']);count=len(params)
 y=np.array([np.r_[np.full(N,p['initial']),p['body_temp'],1.] for p in params]).reshape(-1)
 lower=np.full(count,np.inf);upper=np.full(count,-np.inf);spread=upper.copy();sl=lower.copy();sh=upper.copy();ss=upper.copy();premises=[];refinements=np.zeros(count,dtype=int)
 def sampled(states,ids):
  water=states[:,:N];v=water[:,net['region']]
  np.minimum.at(sl,ids,water.min(1));np.maximum.at(sh,ids,v.max(1));np.maximum.at(ss,ids,np.ptp(v,axis=1))
 def accumulate(lb,ub,sb,ids):
  np.minimum.at(lower,ids,lb);np.maximum.at(upper,ids,ub);np.maximum.at(spread,ids,sb)
 for flow in flows:
  budget();local=[a+float(flow)*q for a,q in zip(A,Q)];premises.extend(check_premise(b,N) for b in local)
  B=block_diag(local,format='csr');trace=float(B.diagonal().sum())
  for _ in range(10):
   budget();values=expm_multiply(B,y,start=0.,stop=30.,num=31,traceA=trace)
   if not np.isfinite(values).all():raise ValueError('Nonfinite trajectory')
   shaped=values.reshape(-1,count,N+2)
   if np.max(abs(shaped[:,:,-1]-1.))>1e-10:raise ValueError('Constant drift')
   rates=(B@values.T).T.reshape(shaped.shape);curv=(B@((B@values.T))).T.reshape(shaped.shape)
   lb,ub,sb,_,_,_=segment_bounds(shaped,rates,curv,net,1.)
   sampled(shaped.reshape(-1,N+2),np.tile(np.arange(count),31))
   valid=(lb>=39.13)&(ub<=40.9)&(sb<=1.4)
   good_time,good_ids=np.where(valid);accumulate(lb[good_time,good_ids],ub[good_time,good_ids],sb[good_time,good_ids],good_ids)
   times,ids=np.where(~valid);left=shaped[times,ids].copy();right=shaped[times+1,ids].copy();width=1.
   # Only unresolved intervals are propagated again, including multiple
   # different time intervals for the same model as separate block copies.
   for level in range(1,5):
    if not len(ids):break
    budget();operator=block_diag([local[int(i)] for i in ids],format='csr')
    mids=expm_multiply(operator*(width/2),left.reshape(-1),traceA=float(operator.diagonal().sum())*width/2).reshape(-1,N+2)
    if not np.isfinite(mids).all() or np.max(abs(mids[:,-1]-1.))>1e-10:raise ValueError('Invalid midpoint state')
    sampled(mids,ids);np.add.at(refinements,ids,1)
    pairs=np.array([np.concatenate([left,mids]),np.concatenate([mids,right])]);pair_ids=np.tile(ids,2)
    flat=pairs.reshape(2,-1);op=block_diag([local[int(i)] for i in pair_ids],format='csr')
    rr=(op@flat.T).T.reshape(pairs.shape);cc=(op@(op@flat.T)).T.reshape(pairs.shape)
    lo,hi,sp,_,_,_=segment_bounds(pairs,rr,cc,net,width/2);lo,hi,sp=lo[0],hi[0],sp[0]
    accept=(lo>=39.13)&(hi<=40.9)&(sp<=1.4)
    # At the cap retain unresolved bounds; final reserve flags remain false.
    if level==4:accept=np.ones(len(pair_ids),dtype=bool)
    accumulate(lo[accept],hi[accept],sp[accept],pair_ids[accept])
    pending=~accept;left=pairs[0,pending].copy();right=pairs[1,pending].copy();ids=pair_ids[pending];width/=2
   y=values[-1]
 return [dict(lower_bound_c=float(lower[i]),upper_bound_c=float(upper[i]),span_bound_c=float(spread[i]),min_temp=float(sl[i]),max_temp=float(sh[i]),max_span=float(ss[i]),sampled_passed=bool(sl[i]>=39 and sh[i]<=41 and ss[i]<=1.5),continuous_passed=bool(lower[i]>=39 and upper[i]<=41 and spread[i]<=1.5),fair_sample_passed=bool(sl[i]>=39.13 and sh[i]<=40.9 and ss[i]<=1.4),fair_reserve_passed=bool(lower[i]>=39.13 and upper[i]<=40.9 and spread[i]<=1.4),water_l=float(5*sum(flows)*params[i]['flow_multiplier']),max_initial_gap_s=1.,refinement_depth_cap=4,midpoint_count=int(refinements[i]),min_off_diagonal=min(x[0] for x in premises),max_row_sum=max(x[1] for x in premises)) for i in range(count)]
