"""Small network models: shortest path, maximum flow with a minimum cut, minimum spanning tree."""
import networkx as nx


def shortest_path(edges, source, target, *, directed=True):
    """edges: [[u, v, weight], ...]. Negative weights are rejected rather than silently mishandled."""
    g = nx.DiGraph() if directed else nx.Graph()
    for u, v, w in edges:
        if w < 0:
            raise ValueError('Negative edge weight: use a method that handles it explicitly')
        g.add_edge(u, v, weight=w)
    if source not in g or target not in g or not nx.has_path(g, source, target):
        return dict(reachable=False)
    path = nx.dijkstra_path(g, source, target)
    return dict(reachable=True, path=path, length=float(nx.dijkstra_path_length(g, source, target)))


def max_flow(edges, source, sink):
    """edges: [[u, v, capacity], ...] (directed). Returns the flow value and one minimum cut; they agree by max-flow min-cut."""
    g = nx.DiGraph()
    for u, v, cap in edges:
        if cap < 0:
            raise ValueError('Negative capacity')
        g.add_edge(u, v, capacity=cap)
    value, (reach, rest) = nx.minimum_cut(g, source, sink)
    cut = [[u, v] for u in reach for v in g[u] if v in rest]
    return dict(flow=float(value), cut_edges=cut, cut_capacity=float(sum(g[u][v]['capacity'] for u, v in cut)))


def minimum_spanning_tree(edges):
    g = nx.Graph()
    for u, v, w in edges:
        g.add_edge(u, v, weight=w)
    if not nx.is_connected(g):
        raise ValueError('Graph is not connected: no spanning tree')
    tree = nx.minimum_spanning_tree(g)
    return dict(edges=[[u, v, d['weight']] for u, v, d in tree.edges(data=True)], total=float(tree.size(weight='weight')))
