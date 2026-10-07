"""Does the optimized schedule survive mesh refinement? Re-optimize the 6-segment schedule on a finer mesh and replay the archived
12-segment schedule on three meshes. About 10-20 minutes; writes reproduced/mesh_check.json. Requires reproduced/extended.json."""
from pathlib import Path
import json,sys
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'code'))
import model,control
p=model.BASE.copy()
E=json.loads((HERE/'reproduced/extended.json').read_text());best=E['control']['best']
replay=[]
for grid in ((8,4,3),(12,6,4),(16,8,6)):
    net=model.network(p,grid);Y=control.piecewise(p,net,best['flow_lpm'],5.);V=model.view(net,Y)
    replay.append(dict(grid=list(grid),min_temp=float(Y.min()),max_temp=float(V.max()),max_span=float(np.ptp(V,axis=1).max())))
coarse=[r for r in E['control']['runs'] if r and r['segments']==6][0]
fine_net=model.network(p,(12,6,4));fine=control.optimize(p,fine_net,6)
out=dict(schedule_replayed=dict(segments=best['segments'],flow_lpm=best['flow_lpm'],water_l=best['water_l'],meshes=replay),
         reoptimized_on_12x6x4=dict(coarse_mesh_solution=dict(segments=6,flow_lpm=coarse['flow_lpm'],water_l=coarse['water_l']),fine_mesh_solution=fine))
(HERE/'reproduced/mesh_check.json').write_text(json.dumps(out,indent=1));print(json.dumps(out['reoptimized_on_12x6x4'],indent=1))
