"""Simple graphs only; parallel/duplicate edges are rejected, never overwritten.

Small network models: shortest path, maximum flow with a minimum cut, minimum spanning tree."""
import networkx as nx
import math


def _finite_total(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Graph objective exceeds finite numerical range')
    return result


def _simple_edge(g, u, v, value):
    if not math.isfinite(value):
        raise ValueError('Edge values must be finite')
    if g.has_edge(u, v):
        raise ValueError('Parallel or duplicate edges are not supported; supply a simple graph')


def shortest_path(edges, source, target, *, directed=True):
    """edges: [[u, v, weight], ...]. Negative weights are rejected rather than silently mishandled."""
    g = nx.DiGraph() if directed else nx.Graph()
    for u, v, w in edges:
        _simple_edge(g, u, v, w)
        if w < 0:
            raise ValueError('Negative edge weight: use a method that handles it explicitly')
        g.add_edge(u, v, weight=w)
    if source not in g or target not in g or not nx.has_path(g, source, target):
        return dict(reachable=False)
    path = nx.dijkstra_path(g, source, target)
    return dict(reachable=True, path=path, length=_finite_total(nx.dijkstra_path_length(g, source, target)))


def max_flow(edges, source, sink):
    """edges: [[u, v, capacity], ...] (directed). Returns the flow value and one minimum cut; they agree by max-flow min-cut."""
    g = nx.DiGraph()
    for u, v, cap in edges:
        _simple_edge(g, u, v, cap)
        if cap < 0:
            raise ValueError('Negative capacity')
        g.add_edge(u, v, capacity=cap)
    value, (reach, rest) = nx.minimum_cut(g, source, sink)
    cut = [[u, v] for u in reach for v in g[u] if v in rest]
    return dict(flow=_finite_total(value), cut_edges=cut, cut_capacity=_finite_total(sum(g[u][v]['capacity'] for u, v in cut)))


def minimum_spanning_tree(edges):
    g = nx.Graph()
    for u, v, w in edges:
        _simple_edge(g, u, v, w)
        g.add_edge(u, v, weight=w)
    if not nx.is_connected(g):
        raise ValueError('Graph is not connected: no spanning tree')
    tree = nx.minimum_spanning_tree(g)
    return dict(edges=[[u, v, d['weight']] for u, v, d in tree.edges(data=True)], total=_finite_total(tree.size(weight='weight')))


def _analysis_graph(edges, nodes, directed, *, distances=False):
    """JSON-friendly node labels, positive weights, no loops or overwritten edges."""
    if type(directed) is not bool:
        raise ValueError('directed must be a boolean')
    g = nx.DiGraph() if directed else nx.Graph()

    def node(value):
        if isinstance(value, bool) or not isinstance(value, (str, int)) or isinstance(value, str) and not value.strip():
            raise ValueError('Node identifiers must be nonempty strings or integers')
        return value

    if nodes is not None:
        for value in nodes:
            value = node(value)
            if value in g:
                raise ValueError('Duplicate node identifiers are not supported')
            g.add_node(value)
    declared = set(g) if nodes is not None else None
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 3:
            raise ValueError('Each analysis edge must be [source, target, positive weight]')
        u, v, weight = edge
        node(u), node(v)
        if declared is not None and (u not in declared or v not in declared):
            raise ValueError('All edge endpoints must occur in the declared nodes')
        if u == v:
            raise ValueError('Self loops are not supported by these simple-graph analysis tools')
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight <= 0:
            raise ValueError('Analysis weights must be finite positive numbers; betweenness weights are distances')
        _simple_edge(g, u, v, weight)
        g.add_edge(u, v, weight=float(weight))
    if not len(g):
        raise ValueError('Supply at least one node or edge')
    if len(g) > 2000 or g.number_of_edges() > 20000:
        raise ValueError('Graph analysis exceeds the 2000-node/20000-edge budget')
    _finite_total(g.size(weight='weight'))
    return g


def pagerank(edges, *, nodes=None, directed=True, alpha=.85, tol=1e-10, max_iter=1000):
    """Weighted PageRank with uniform teleportation and uniform redistribution from dangling nodes.

    Edge weights are positive transition strengths, normalized within each outgoing row.
    """
    g = _analysis_graph(edges, nodes, directed)
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError('alpha must be finite and lie in (0,1)')
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(tol) or tol <= 0:
        raise ValueError('tol must be finite and positive')
    if type(max_iter) is not int or not 1 <= max_iter <= 10000:
        raise ValueError('max_iter must be an integer from 1 to 10000')
    try:
        scores = nx.pagerank(g, alpha=alpha, tol=tol, max_iter=max_iter, weight='weight')
    except nx.PowerIterationFailedConvergence:
        return dict(converged=False, scores=None, alpha=alpha, max_iter=max_iter,
                    note='Power iteration did not meet its tolerance; no converged scores are reported.')
    return dict(converged=True, scores=[dict(node=n, score=float(scores[n])) for n in g],
                alpha=alpha, directed=directed, nodes=len(g), edges=g.number_of_edges(),
                note='Uniform teleportation and dangling redistribution; positive weights are transition strengths. Ranking is conditional on this supplied graph.')


def betweenness(edges, *, nodes=None, directed=False, normalized=True):
    """Exact all-source shortest-path betweenness; positive weights mean distances/costs, not strengths."""
    if type(normalized) is not bool:
        raise ValueError('normalized must be a boolean')
    g = _analysis_graph(edges, nodes, directed, distances=True)
    scores = nx.betweenness_centrality(g, normalized=normalized, weight='weight')
    return dict(scores=[dict(node=n, score=float(scores[n])) for n in g], normalized=normalized,
                directed=directed, nodes=len(g), edges=g.number_of_edges(),
                note='Positive weights are distances, endpoints are excluded, and equal shortest paths share credit. Strengths must be transformed into justified distances before calling.')


def greedy_modularity_communities(edges, *, nodes=None, resolution=1., baseline_trials=20, seed=2027):
    """Greedy weighted communities and a seeded fixed-n/fixed-m G(n,m) comparison.

    The random null is an undirected simple G(n,m), with observed positive weights
    randomly permuted onto its edges. It does not preserve degree or strength.
    This descriptive baseline supplies no significance test or p-value.
    """
    import numpy as np
    g = _analysis_graph(edges, nodes, False)
    if isinstance(resolution, bool) or not isinstance(resolution, (int, float)) or not math.isfinite(resolution) or resolution <= 0:
        raise ValueError('resolution must be finite and positive')
    if type(baseline_trials) is not int or not 1 <= baseline_trials <= 200:
        raise ValueError('baseline_trials must be an integer from 1 to 200')
    if type(seed) is not int or seed < 0:
        raise ValueError('seed must be a nonnegative integer')
    if not g.number_of_edges():
        raise ValueError('Modularity is undefined for an edgeless graph')
    if baseline_trials*max(1, g.number_of_edges())*len(g) > 5_000_000:
        raise ValueError('Modularity baseline exceeds the 5000000 trials*edges*nodes budget')
    communities = list(nx.community.greedy_modularity_communities(g, weight='weight', resolution=resolution))
    score = float(nx.community.modularity(g, communities, weight='weight', resolution=resolution))
    rng = np.random.default_rng(seed)
    weights = [data['weight'] for _, _, data in g.edges(data=True)]
    baseline = []
    for _ in range(baseline_trials):
        random_graph = nx.gnm_random_graph(len(g), g.number_of_edges(), seed=int(rng.integers(2**32)))
        for (u, v), weight in zip(random_graph.edges(), rng.permutation(weights)):
            random_graph[u][v]['weight'] = float(weight)
        random_communities = nx.community.greedy_modularity_communities(random_graph, weight='weight', resolution=resolution)
        baseline.append(float(nx.community.modularity(random_graph, random_communities, weight='weight', resolution=resolution)))
    order = {value: i for i, value in enumerate(g)}
    return dict(communities=[sorted(group, key=order.__getitem__) for group in communities], modularity=score,
                resolution=resolution, nodes=len(g), edges=g.number_of_edges(),
                baseline=dict(null_model='Undirected simple G(n,m), fixed node/edge counts; observed weights randomly permuted onto random edges. Degrees and strengths are not preserved.',
                              seed=seed, trials=baseline_trials, modularities=baseline,
                              mean=float(np.mean(baseline)), sd=float(np.std(baseline, ddof=1)) if baseline_trials > 1 else None,
                              observed_minus_mean=float(score-np.mean(baseline)),
                              interpretation='Descriptive algorithm-matched random baseline only; no significance test or p-value.'),
                note='Greedy modularity is a heuristic partition, not a certified maximum. Resolution and the supplied graph define this comparison.')
