import importlib.util,json
from pathlib import Path
import numpy as np
base=Path(__file__).resolve().parent;r=json.loads((base/'reference/results.json').read_text())
spec=importlib.util.spec_from_file_location('model',base/'code/model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
(base/'reproduced').mkdir(exist_ok=True)
checks=[]
for key in ['four','fifteen']:
 group=r['groups'][key];d=group['selected'][1]
 data=np.array([[float(a[k]) for k in ['return_pct','risk_pct','fee_pct','threshold_yuan']] for a in group['assets']])
 critical=max(float(a['threshold_yuan'])/(x/d['budget_yuan']) for a,x in zip(group['assets'],d['investments_yuan']) if x>1e-7)
 for budget in [critical,np.ceil(critical)]:
  got=m.solve(data,budget,d['risk_cap'])
  gap=abs(got['net_return']-d['net_return'])
  assert gap<1e-7
  checks.append({'group':key,'sufficient_threshold_yuan':critical,'budget_yuan':float(budget),'net_return_gap':gap,'passed':True})
(base/'reproduced/capital-threshold-check.json').write_text(json.dumps(checks,indent=2))
print(checks)
