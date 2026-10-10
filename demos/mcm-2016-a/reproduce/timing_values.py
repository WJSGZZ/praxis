"""Local delay sensitivity on a fixed terminal-floor policy branch."""
from pathlib import Path
import json,math,hashlib
from spatial_functional_values import spatial_functional_values

def timing_values(root):
 root=Path(root);spatial_functional_values(root);folder=root/'reference/spatial-functional'
 r=json.loads((folder/'timing-results.json').read_text());c=json.loads((folder/'timing-checks.json').read_text())
 if c['timing_source_sha256']!=hashlib.sha256((folder/'timing-results.json').read_bytes()).hexdigest() or c['checker_sha256']!=hashlib.sha256((folder/'check_timing.py').read_bytes()).hexdigest():raise ValueError('Timing evidence stale')
 if hashlib.sha256((root/'code/model.py').read_bytes()).hexdigest()!='6c9d1c4deef48552084234c1158fb928eeee73e566c7d4a4231061c1696035db':raise ValueError('Timing physical source changed')
 rows=r['rows']+[r['local_root']];checks=c['independent_rows']
 if len(rows)!=5 or len(checks)!=5 or [x['D'] for x in rows[:4]]!=[.0007,.001,.002,.003]:raise ValueError('Timing coverage changed')
 for x,y in zip(rows,checks):
  numbers=[x[k] for k in ['D','q','Fq','Fd','second_cell_gap','water_delay_derivative_l_per_s']]+[y[k] for k in ['D','q','Fq','Fd','slope','terminal_min']]+list(y['envelope'].values())
  if not all(math.isfinite(v) for v in numbers):raise ValueError('Nonfinite timing evidence')
  slope=(-1800*x['Fd']/x['Fq']-x['q'])/60
  if x['delay']!=0 or x['Fq']<=0 or x['second_cell_gap']<=0 or x['terminal_cell']!=89 or y['terminal_cell']!=89 or x['D']!=y['D'] or x['q']!=y['q'] or not 0<x['q']<3:raise ValueError('Timing branch changed')
  if abs(slope-x['water_delay_derivative_l_per_s'])>1e-12 or abs(y['slope']-slope)>1e-8 or abs(y['Fq']-x['Fq'])>1e-7 or abs(y['Fd']-x['Fd'])>1e-7 or abs(y['terminal_min']-39.03)>1e-7:raise ValueError('Timing sensitivity mismatch')
  e=y['envelope']
  if e['floor']<=39 or e['ceiling']>=41 or e['spread']>=1.5:raise ValueError('Timing physical envelope failed')
 if rows[1]['water_delay_derivative_l_per_s']<=0 or rows[3]['water_delay_derivative_l_per_s']>=0:raise ValueError('Timing comparison changed')
 bracket=c['local_sign_bracket']
 if len(bracket)!=2 or not bracket[0]['D']<r['local_root']['D']<bracket[1]['D'] or not bracket[0]['slope']>0>bracket[1]['slope']:raise ValueError('Timing local numerical bracket invalid')
 return {'baseline_slope':rows[1]['water_delay_derivative_l_per_s'],'strong_slope':rows[3]['water_delay_derivative_l_per_s'],'local_D':r['local_root']['D'],'scope':'Local constant-after-delay branch with terminal39.03C, original96 only; no exact/unique root or arbitrary-control optimality'}
