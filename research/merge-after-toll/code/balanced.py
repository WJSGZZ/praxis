"""Rejected research candidate: optimize maximum resource utilization, not waiting."""
import argparse
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from model import HERE, execute

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    cfg=json.loads((HERE/'config.json').read_text());cfg['routing_strategy']='balanced'
    start=time.perf_counter();result=execute(cfg,'improved')
    result['compute_seconds']=time.perf_counter()-start;result['computed_utc']=datetime.now(timezone.utc).isoformat()
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({'candidate':'minimax-resource-load','compute_seconds':result['compute_seconds']}))
