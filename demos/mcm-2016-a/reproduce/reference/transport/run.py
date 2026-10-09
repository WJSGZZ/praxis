import hashlib,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from threadpoolctl import threadpool_limits
from model import Stage,trajectory,metrics

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results.json'
if OUT.exists():raise FileExistsError(OUT)
design=json.loads((ROOT/'design.json').read_text());p=design['p'];start=time.monotonic()
rows=[];search=[];failures=[];cache={}
source={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['model.py','run.py','design.json','design.md']}

def checkpoint():
    if time.monotonic()-start>design['producer_seconds']:raise TimeoutError('Cumulative producer deadline')
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in source.items()),'source changed during run'


def evaluate(profile,D,cells,delay,rate,dt=5):
    checkpoint();segments=[(delay,0.),(p['horizon']-delay,rate)]
    key=lambda q:(profile,D,cells,q)
    zero=cache.setdefault(key(0.),Stage(p,cells,profile,D,0.)) if key(0.) not in cache else cache[key(0.)]
    y=np.full(cells,p['T0']);ts0=np.r_[0.,np.arange(dt,delay,dt),delay] if delay>0 else np.array([0.])
    ts0=np.unique(ts0);ys0=zero.propagate(y,ts0);y=ys0[-1]
    if key(rate) not in cache:cache[key(rate)]=Stage(p,cells,profile,D,rate)
    stage=cache[key(rate)];duration=p['horizon']-delay;ts=np.unique(np.r_[np.arange(dt,duration,dt),duration])
    ys=stage.propagate(y,ts);times=np.r_[ts0,delay+ts];values=np.vstack([ys0,ys]);m=metrics(p,cells,times,values,segments)
    m.update(delay_s=delay,rate_lpm=rate,cells=cells,profile=profile,D=D)
    return m

status='completed'
try:
 with threadpool_limits(limits=1):
    for profile in design['profiles']:
      for D in design['diffusivities']:
        for name,segments in design['policies'].items():
          for cells in design['cells']:
            checkpoint();times,yy=trajectory(p,cells,profile,D,segments,dt=design['sample_s']);m=metrics(p,cells,times,yy,segments)
            rows.append(dict(kind='original_policy',policy=name,profile=profile,D=D,cells=cells,metrics=m))
        candidates=[]
        for delay in design['starts_s']:
          below=evaluate(profile,D,80,delay,0.)
          if below['floor_c']<p['floor'] and delay>0:
            # A pre-start floor violation is independent of the subsequent rate.
            zero=cache[(profile,D,80,0.)].propagate(np.full(80,p['T0']),[delay])
            if zero.min()<p['floor']:
              failures.append(dict(profile=profile,D=D,delay_s=delay,reason='prestart floor violation'));continue
          previous=below;accepted=None
          for rate in design['rates_lpm'][1:]:
            value=evaluate(profile,D,80,delay,rate)
            if previous['floor_c']<=design['floor_target_c']<=value['floor_c']:
              root=brentq(lambda q:evaluate(profile,D,80,delay,q)['floor_c']-design['floor_target_c'],previous['rate_lpm'],rate,xtol=1e-7)
              value=evaluate(profile,D,80,delay,root)
              if value['sampled_physical_passed']:accepted=value
              else:failures.append(dict(profile=profile,D=D,delay_s=delay,reason='floor root violates ceiling/spread',metrics=value))
              break
            previous=value
          if accepted is None:
            failures.append(dict(profile=profile,D=D,delay_s=delay,reason='none accepted in first-crossing search'))
          else:candidates.append(accepted)
        if candidates:
          chosen=min(candidates,key=lambda x:x['command_l']);refine=[]
          for cells in design['cells']:
            for dt in [5.,1.]:refine.append(evaluate(profile,D,cells,chosen['delay_s'],chosen['rate_lpm'],dt=dt))
          search.append(dict(profile=profile,D=D,candidates=candidates,selected=chosen,refinement=refine))
        else:search.append(dict(profile=profile,D=D,candidates=[],selected=None,refinement=[]))
except Exception as exc:
 status='failed_or_partial';error=repr(exc)
finally:
 result={'status':status,'source_sha256':source,'elapsed_s':time.monotonic()-start,'rows':rows,'search':search,'failures':failures,'scope':'Sampled three-resolution reduced closure, finite delayed-constant family, unchanged original policies; not physical validation or global/continuous guarantee'}
 if status!='completed':result['error']=error
 OUT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':status,'elapsed_s':result['elapsed_s'],'replays':len(rows),'search_groups':len(search),'chosen':[(s['profile'],s['D'],None if s['selected'] is None else {k:s['selected'][k] for k in ['delay_s','rate_lpm','command_l']}) for s in search]}))
if status!='completed':raise SystemExit(1)
