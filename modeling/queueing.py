"""M/M/c queue in steady state (Poisson arrivals, exponential service, c identical servers)."""
import math


def mmc(arrival_rate, service_rate, servers):
    """Return utilization, probability of waiting (Erlang C) and mean queue/system measures.

    Valid only when the system is stable (utilization below one) and the arrival and service
    assumptions hold; real queues with other distributions need simulation."""
    if (not math.isfinite(arrival_rate) or not math.isfinite(service_rate)
            or isinstance(servers, bool) or not isinstance(servers, (int, float))
            or not math.isfinite(servers) or arrival_rate <= 0 or service_rate <= 0
            or servers < 1 or int(servers) != servers):
        raise ValueError('Rates must be positive and servers a positive integer')
    c = int(servers)
    a = arrival_rate / service_rate
    rho = a / c
    if rho >= 1:
        raise ValueError(f'Unstable queue: utilization {rho:.3f} >= 1')
    # Erlang B recurrence stays in [0,1], avoiding a**c and c! overflow.
    # Erlang C = B / (1-rho+rho*B), algebraically identical to its sum formula.
    erlang_b = 1.0
    for k in range(1, c + 1):
        erlang_b = a * erlang_b / (k + a * erlang_b)
    wait = erlang_b / (1 - rho + rho * erlang_b)
    lq = wait * rho / (1 - rho)
    wq = lq / arrival_rate
    result = dict(utilization=rho, prob_wait=wait, mean_queue_length=lq, mean_wait=wq,
                  mean_system_time=wq + 1 / service_rate, mean_in_system=lq + a)
    if not all(math.isfinite(value) for value in result.values()):
        raise ValueError('Queue measures exceed finite numerical range')
    return result
