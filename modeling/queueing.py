"""M/M/c queue in steady state (Poisson arrivals, exponential service, c identical servers)."""
import math


def mmc(arrival_rate, service_rate, servers):
    """Return utilization, probability of waiting (Erlang C) and mean queue/system measures.

    Valid only when the system is stable (utilization below one) and the arrival and service
    assumptions hold; real queues with other distributions need simulation."""
    if arrival_rate <= 0 or service_rate <= 0 or servers < 1 or int(servers) != servers:
        raise ValueError('Rates must be positive and servers a positive integer')
    c = int(servers)
    a = arrival_rate / service_rate
    rho = a / c
    if rho >= 1:
        raise ValueError(f'Unstable queue: utilization {rho:.3f} >= 1')
    head = sum(a ** k / math.factorial(k) for k in range(c))
    tail = a ** c / (math.factorial(c) * (1 - rho))
    wait = tail / (head + tail)
    lq = wait * rho / (1 - rho)
    wq = lq / arrival_rate
    return dict(utilization=rho, prob_wait=wait, mean_queue_length=lq, mean_wait=wq,
                mean_system_time=wq + 1 / service_rate, mean_in_system=lq + a)
