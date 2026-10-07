"""Locate the knee of each recorded risk-return frontier and certify it with the analytic upper bound."""
import csv,importlib.util,json
from pathlib import Path
import numpy as np
base=Path(__file__).resolve().parent;ref=base/'reference';r=json.loads((ref/'results.json').read_text())
def load(name):
 spec=importlib.util.spec_from_file_location(name,base/f'code/{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
model,validate=load('model'),load('validate')
out={'rule':'knee = point of the saturating frontier farthest above the chord from zero risk to the smallest risk that reaches the maximum return; both axes rescaled to [0,1]','groups':{}}
for key in ['four','fifteen']:
 rows=list(csv.DictReader((ref/f'{key}-frontier.csv').open()))
 x=np.array([float(a['risk_cap']) for a in rows]);y=np.array([float(a['net_return']) for a in rows])
 sat=x[np.argmax(y>=y.max()-1e-9)];keep=x<=sat
 gap=(y[keep]-y[0])/(y.max()-y[0])-x[keep]/sat;i=int(gap.argmax())
 group=r['groups'][key];data=np.array([[float(a[k]) for k in ['return_pct','risk_pct','fee_pct','threshold_yuan']] for a in group['assets']])
 got=model.solve(data,1e6,float(x[i]));bound=validate.relaxed_upper(data,float(x[i]))
 assert abs(got['net_return']-y[i])<1e-7 and abs(got['net_return']-bound)<1e-7
 out['groups'][key]={'grid_step':float(x[1]-x[0]),'saturation_risk':float(sat),'max_net_return':float(y.max()),'knee_risk':float(x[i]),'knee_net_return':float(y[i]),
  'share_of_gain':float((y[i]-y[0])/(y.max()-y[0])),'share_of_saturation_risk':float(x[i]/sat),
  'slope_before':float((y[i]-y[i-1])/(x[i]-x[i-1])),'slope_after':float((y[i+1]-y[i])/(x[i+1]-x[i])),
  'analytic_upper_bound':float(bound),'investments_yuan':got['investments_yuan'],'fees_yuan':got['fees_yuan'],'bank_yuan':got['bank_yuan'],'net_profit_yuan':got['profit_yuan']}
(base/'reproduced').mkdir(exist_ok=True);(base/'reproduced/recommendation.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:{a:b for a,b in v.items() if not isinstance(b,list)} for k,v in out['groups'].items()},indent=1))
