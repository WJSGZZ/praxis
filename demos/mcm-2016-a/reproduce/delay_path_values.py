"""Consume a qualified policy and a terminal-pass/interior-fail counterexample."""
from pathlib import Path
import hashlib,json,math
from spatial_functional_values import spatial_functional_values

def delay_path_values(root):
 root=Path(root);spatial_functional_values(root);folder=root/'reference/spatial-functional';r=json.loads((folder/'delay-path-checks.json').read_text())
 if r['checker_sha256']!=hashlib.sha256((folder/'check_delay_path.py').read_bytes()).hexdigest() or r['model_sha256']!=hashlib.sha256((root/'code/model.py').read_bytes()).hexdigest():raise ValueError('Delay path evidence stale')
 rows=r['rows']
 if len(rows)!=2 or [x['delay'] for x in rows]!=[700.,720.]:raise ValueError('Delay path identities changed')
 for x in rows:
  values=[x[k] for k in ['D','q','delay','water_l','terminal_min_c','sample_min_c','sample_min_time_s','matrix_at_sample_min_c']]+[v for e in x['envelopes'] for v in e.values()]
  if not all(math.isfinite(v) for v in values) or x['D']!=.003 or not 0<x['q']<3 or x['terminal_cell']!=89 or len(x['envelopes'])!=2 or abs(x['terminal_min_c']-39.03)>1e-7 or abs(x['water_l']-x['q']*(1800-x['delay'])/60)>1e-9:raise ValueError('Delay path branch changed')
  prefix=x['envelopes'][0]
  if prefix['floor']<39 or prefix['ceiling']>41 or prefix['spread']>1.5:raise ValueError('Delay prefix failed')
  if not x['delay']<x['sample_min_time_s']<1800 or x['sample_min_cell']!=89 or abs(x['matrix_at_sample_min_c']-x['sample_min_c'])>1e-7:raise ValueError('Delay interior replay differs')
  qualified=all(e['floor']>=39 and e['ceiling']<=41 and e['spread']<=1.5 for e in x['envelopes'])
  if x['qualified'] is not qualified:raise ValueError('Delay path qualification differs')
 if rows[0]['qualified'] is not True or rows[1]['qualified'] is not False or rows[1]['sample_min_c']+2e-6>=39:raise ValueError('Delay path counterexample missing')
 return {'qualified_delay_s':rows[0]['delay'],'failed_delay_s':rows[1]['delay'],'failed_min_c':rows[1]['sample_min_c'],'scope':'Two original96 constant-after-delay terminal-floor branch policies only; no latest feasible delay or global optimum'}
