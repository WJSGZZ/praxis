"""Original teaching example: turn a peak-hour objection into a stability check.

Synthetic M/M/1 scenario, not an observed service system or award benchmark.
Uses exact queueing formulas, not the plugin queue implementation.
"""
from fractions import Fraction
import json


def scenario(arrivals_per_hour, service_per_hour):
    arrivals, service = Fraction(arrivals_per_hour), Fraction(service_per_hour)
    if arrivals < 0 or service <= 0:
        raise ValueError('Nonnegative arrivals and positive service required')
    stable = arrivals < service
    return {'arrivals_per_hour': float(arrivals), 'service_per_hour': float(service),
            'stable': stable, 'utilization': float(arrivals / service),
            'queue_wait_minutes': float(60 * arrivals / (service * (service - arrivals))) if stable else None}


if __name__ == '__main__':
    print(json.dumps({'scope': 'Synthetic M/M/1 with stationary Poisson arrivals, independent exponential service, one server and unlimited waiting space',
                      'baseline': scenario(48, 60), 'peak': scenario(72, 60),
                      'response': 'Peak arrivals exceed service capacity. Steady-state waiting time is undefined; use a finite-horizon/time-varying model or change capacity.'}, indent=2))
