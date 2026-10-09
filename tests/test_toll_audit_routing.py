"""Event-engine agreement requires matching actual routing, not just arrivals."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]/'research/merge-after-toll'
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
@pytest.mark.parametrize('strategy',['capacity','balanced'])
@pytest.mark.parametrize('scenario',['nominal','cash_heavy','electronic_heavy'])
def test_multiroute_large_storage_limit(strategy,scenario):
    model=load(ROOT/'code/model.py','routing_model');finite=load(ROOT/'code/finite_queue.py','routing_finite');audit=load(ROOT/'audit.py','routing_audit')
    cfg=json.loads((ROOT/'code/config.json').read_text());cfg['routing_strategy']=strategy
    counts=np.ones((3,3),dtype=int)
    design={'counts':counts.tolist(),**model.geometry(counts,cfg)}
    shares=cfg['payment_scenarios'][scenario];seed=cfg['seeds'][0]
    stream=model.arrival_stream(cfg['heavy_vph'],shares,cfg,seed)
    old=model.simulate(design,shares,cfg,cfg['heavy_vph'],seed,stream=stream)
    types,groups,weights=audit.queue_inputs(model,counts,shares,cfg)
    actual=finite.run(stream,types,groups,weights,audit.free_travel(design,cfg),model.headway(0,cfg),cfg['horizon_s'],len(stream)+1)
    for key in ['arrivals','completed','residual','observed_output_vph','mean_delay_s','p95_delay_s','clearance_s']:
        assert actual[key]==pytest.approx(old[key],abs=1e-9)
    assert actual['total_booth_blocked_s']==0

def test_finite_balanced_routing_receives_storage_inputs():
    audit=load(ROOT/'audit.py','routing_contract')
    class Model:
        @staticmethod
        def operating_routing(counts,shares,cfg,rate,*,slots,design):
            assert rate==7 and slots==4 and design=={'identity':'case'}
            return {'type_lane_flow_vph':[[0,0,7]]}
        @staticmethod
        def routing(*args):
            raise AssertionError('Different policy called')
    assert audit.queue_inputs(Model,np.array([[0,0,1]]),[0,0,1],{'routing_strategy':'balanced','heavy_vph':7},slots=4,design={'identity':'case'})==([2],[0],[7.0])
