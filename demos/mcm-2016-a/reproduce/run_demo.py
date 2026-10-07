"""Recalculate this explicit historical scenario and independently check its evidence."""
from pathlib import Path
import json,sys
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'code'))
import model, validate
output=HERE/'reproduced'
output.mkdir(exist_ok=False)
result=model.run(output)
checks=validate.validate(output/'results.json')
reference=json.loads((HERE/'reference/results.json').read_text())
error=abs(result['policy']['water_l']-reference['policy']['water_l'])
checks.append(dict(name='archived_report_water_amount',passed=bool(error<1e-5),evidence=f'Absolute water difference {error:.3g} L; tolerance 1e-5 L'))
(output/'checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps({'checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),'report_water_l':result['policy']['water_l'],'absolute_difference_l':error}))
raise SystemExit(0 if all(c['passed'] for c in checks) else 1)
