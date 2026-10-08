"""Blocking-after-service event model with finite downstream occupancy tokens.

Tokens count vehicles from toll release to exit. A full group blocks completed
service at its booth; that booth cannot start its next service. This is a queue
resource model, not a geometric collision or empirically calibrated spillback model.
"""
import heapq
from collections import deque
import math
import numpy as np


def run(stream, booth_types, booth_groups, weights, travel_by_type, headway, horizon, slots):
    if type(slots) is not int or slots<1:
        raise ValueError('Finite occupancy slots must be a positive integer')
    types=np.asarray(booth_types); weights=np.asarray(weights,float)
    lanes=max(booth_groups)+1
    options=[]
    for t in range(3):
        ids=np.where(types==t)[0]
        options.append((ids, np.cumsum(weights[ids]/weights[ids].sum()) if len(ids) else []))
    queues=[deque() for _ in types]; busy=[False for _ in types]
    blocked=[deque() for _ in range(lanes)];occupancy=[0]*lanes
    peak=[0]*lanes; last=[-math.inf]*lanes
    events=[];serial=0;exits=[];delays=[];blocked_time=0.0
    def push(at,kind,data):
        nonlocal serial
        serial+=1;heapq.heappush(events,(at,serial,kind,data))
    def start(booth,now):
        if queues[booth] and not busy[booth]:
            job=queues[booth].popleft();busy[booth]=True
            push(now+job[2],'service',(booth,job))
    def admit(booth,job,now):
        lane=booth_groups[booth];occupancy[lane]+=1
        peak[lane]=max(peak[lane],occupancy[lane])
        push(now+travel_by_type[job[1]],'ready',(lane,job))
        busy[booth]=False;start(booth,now)
    for job in stream:push(job[0],'arrival',job)
    while events:
        now,_,kind,data=heapq.heappop(events)
        if kind=='arrival':
            job=data;ids,prob=options[job[1]]
            if not len(ids):raise ValueError('No compatible booth')
            booth=int(ids[min(np.searchsorted(prob,job[3]),len(ids)-1)])
            queues[booth].append(job);start(booth,now)
        elif kind=='service':
            booth,job=data;lane=booth_groups[booth]
            if occupancy[lane]<slots:admit(booth,job,now)
            else:blocked[lane].append((booth,job,now))
        elif kind=='ready':
            lane,job=data;depart=max(now,last[lane]+headway);last[lane]=depart
            push(depart,'exit',(lane,job))
        else:
            lane,job=data;occupancy[lane]-=1;exits.append(now)
            delays.append(now-job[0]-job[2]-travel_by_type[job[1]])
            if blocked[lane]:
                booth,waiting,at=blocked[lane].popleft()
                blocked_time+=now-at;admit(booth,waiting,now)
    if any(busy) or any(occupancy) or any(queues) or any(blocked):
        raise RuntimeError('Undrained queues')
    completed=int(sum(x<=horizon for x in exits))
    return dict(arrivals=len(stream),completed=completed,residual=len(stream)-completed,
                observed_output_vph=completed*3600/horizon,
                mean_delay_s=float(np.mean(delays)) if delays else 0.,
                p95_delay_s=float(np.quantile(delays,.95)) if delays else 0.,
                clearance_s=max(0.,max(exits,default=0)-horizon),
                peak_occupancy_by_group=peak, occupancy_slots_per_group=slots,
                total_booth_blocked_s=blocked_time)
