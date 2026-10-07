"""Praxis tools as a stdio MCP server (no SDK needed), also callable from the command line.

    python -m scripts.mcp_server                      # serve MCP over stdio
    python -m scripts.mcp_server --list               # list tools
    python -m scripts.mcp_server --call solve_lp '{"c":[3,2],...}'

Each tool takes plain JSON and returns JSON. Tools compute; they do not decide whether a model fits the problem."""
import argparse
import ast
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modeling import decision, epidemic, forecast, graph, optimize, queueing, sensitivity, weights  # noqa: E402
from scripts import audit_data, check_references  # noqa: E402

VERSION = '0.1.0'
FUNCTIONS = {'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt, 'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
             'abs': np.abs, 'minimum': np.minimum, 'maximum': np.maximum}


def _compile(expression, names):
    """Vectorised evaluation of an arithmetic expression; anything but arithmetic, names and a few functions is rejected."""
    tree = ast.parse(expression, mode='eval')
    for node in ast.walk(tree):
        ok = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd)
        if isinstance(node, ok):
            if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
                raise ValueError('Only numeric constants are allowed')
        elif isinstance(node, ast.Name):
            if node.id not in names and node.id not in FUNCTIONS:
                raise ValueError(f'Unknown name: {node.id}')
        elif isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS and not node.keywords):
                raise ValueError('Only simple calls to exp, log, sqrt, sin, cos, tan, abs, minimum, maximum are allowed')
        else:
            raise ValueError(f'Disallowed syntax: {type(node).__name__}')
    code = compile(tree, '<expression>', 'eval')

    def model(x):
        scope = {**FUNCTIONS, **{name: x[:, i] for i, name in enumerate(names)}}
        return np.asarray(eval(code, {'__builtins__': {}}, scope), float) * np.ones(len(x))
    return model


def _sobol(a):
    return sensitivity.sobol_sensitivity(_compile(a['expression'], a['names']), a['names'], a['bounds'],
                                         n=a.get('n', 1024), seed=a.get('seed', 2027))


def _num(description='', **extra):
    return {'type': 'number', 'description': description, **extra}


MATRIX = {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'number'}}}
EDGES = {'type': 'array', 'items': {'type': 'array', 'minItems': 3, 'maxItems': 3}, 'description': '[[from, to, weight_or_capacity], ...]'}
SERIES = {'type': 'array', 'items': {'type': 'number'}}


def _tool(name, description, properties, required, function):
    return name, dict(description=description, function=function,
                      schema={'type': 'object', 'properties': properties, 'required': required})


TOOLS = dict([
    _tool('audit_data', 'Read-only audit of a CSV/Excel file: shape, missing values, duplicates, column types; hashes the original.',
          {'path': {'type': 'string'}, 'sheet': {'type': 'string'}}, ['path'],
          lambda a: audit_data.audit(Path(a['path']), sheet=a.get('sheet', 0))),
    _tool('check_references', 'Check each reference line with a DOI against Crossref (title and year); lines without a DOI are reported as no_doi. Needs internet.',
          {'references': {'type': 'array', 'items': {'type': 'string'}}, 'mailto': {'type': 'string'}}, ['references'],
          lambda a: check_references.check(a['references'], a.get('mailto', 'unknown@example.org'))),
    _tool('solve_lp', 'Linear program (HiGHS) with a duality-gap certificate. bounds default to x>=0.',
          {'c': SERIES, 'A_ub': MATRIX, 'b_ub': SERIES, 'A_eq': MATRIX, 'b_eq': SERIES, 'bounds': {'type': 'array'}, 'maximize': {'type': 'boolean'}}, ['c'],
          lambda a: optimize.solve_lp(a['c'], **{k: v for k, v in a.items() if k != 'c'})),
    _tool('solve_milp', 'Mixed-integer linear program (HiGHS) with proved bound and gap. integrality: 1 for integer variables.',
          {'c': SERIES, 'A_ub': MATRIX, 'b_ub': SERIES, 'A_eq': MATRIX, 'b_eq': SERIES, 'bounds': {'type': 'array'}, 'integrality': SERIES,
           'maximize': {'type': 'boolean'}, 'time_limit': _num('seconds')}, ['c'],
          lambda a: optimize.solve_milp(a['c'], **{k: v for k, v in a.items() if k != 'c'})),
    _tool('ahp_weights', 'AHP weights and consistency ratio from a reciprocal pairwise-comparison matrix (order 1-10).',
          {'matrix': MATRIX}, ['matrix'], lambda a: weights.ahp(a['matrix'])),
    _tool('entropy_weights', 'Entropy weights from a decision matrix (rows alternatives, columns criteria); a dispersion measure, not importance.',
          {'matrix': MATRIX, 'directions': {'type': 'array', 'items': {'type': 'number'}, 'description': '+1 larger is better, -1 smaller is better'}}, ['matrix'],
          lambda a: weights.entropy_weights(a['matrix'], a.get('directions'))),
    _tool('evaluate_alternatives', 'TOPSIS ranking with min-max normalisation and rank stability under perturbed weights.',
          {'matrix': MATRIX, 'weights': SERIES, 'directions': SERIES, 'alternatives': {'type': 'array'}, 'criteria': {'type': 'array'},
           'trials': {'type': 'integer'}, 'weight_sigma': _num(), 'seed': {'type': 'integer'}}, ['matrix', 'weights', 'directions'],
          lambda a: decision.evaluate_alternatives(**a)),
    _tool('sobol_sensitivity', 'Sobol indices for a scalar arithmetic expression over independent uniform inputs. n must be a power of two >= 64.',
          {'expression': {'type': 'string', 'description': 'e.g. "2*a + b*b"; functions: exp log sqrt sin cos tan abs minimum maximum'},
           'names': {'type': 'array', 'items': {'type': 'string'}}, 'bounds': MATRIX, 'n': {'type': 'integer'}, 'seed': {'type': 'integer'}},
          ['expression', 'names', 'bounds'], _sobol),
    _tool('shortest_path', 'Dijkstra shortest path; edges [[u, v, weight]], non-negative weights.',
          {'edges': EDGES, 'source': {}, 'target': {}, 'directed': {'type': 'boolean'}}, ['edges', 'source', 'target'],
          lambda a: graph.shortest_path(a['edges'], a['source'], a['target'], directed=a.get('directed', True))),
    _tool('max_flow', 'Maximum flow and a minimum cut; edges [[u, v, capacity]].',
          {'edges': EDGES, 'source': {}, 'sink': {}}, ['edges', 'source', 'sink'],
          lambda a: graph.max_flow(a['edges'], a['source'], a['sink'])),
    _tool('minimum_spanning_tree', 'Minimum spanning tree of a connected undirected graph; edges [[u, v, weight]].',
          {'edges': EDGES}, ['edges'], lambda a: graph.minimum_spanning_tree(a['edges'])),
    _tool('queue_mmc', 'M/M/c steady-state queue: utilization, Erlang C, mean waits and lengths.',
          {'arrival_rate': _num(), 'service_rate': _num(), 'servers': {'type': 'integer'}}, ['arrival_rate', 'service_rate', 'servers'],
          lambda a: queueing.mmc(a['arrival_rate'], a['service_rate'], a['servers'])),
    _tool('sir_simulate', 'SIR epidemic model; daily S, I, R and R0.',
          {'beta': _num(), 'gamma': _num(), 'population': _num(), 'infected0': _num(), 'days': {'type': 'integer'}},
          ['beta', 'gamma', 'population', 'infected0', 'days'],
          lambda a: epidemic.simulate_sir(a['beta'], a['gamma'], a['population'], a['infected0'], a['days'])),
    _tool('sir_fit', 'Fit SIR beta and gamma to daily infected counts; reports whether the data can separate them.',
          {'infected': SERIES, 'population': _num()}, ['infected', 'population'],
          lambda a: epidemic.fit_sir(a['infected'], a['population'])),
    _tool('gm11_forecast', 'Grey GM(1,1) forecast of a short positive series with the posterior-error grade. Compare with backtest_baselines first.',
          {'series': SERIES, 'horizon': {'type': 'integer'}}, ['series'], lambda a: forecast.gm11(a['series'], a.get('horizon', 3))),
    _tool('backtest_baselines', 'Rolling-origin comparison of naive, seasonal naive, drift, linear trend and Holt baselines.',
          {'series': SERIES, 'horizon': {'type': 'integer'}, 'min_train': {'type': 'integer'}, 'season': {'type': 'integer'}}, ['series', 'horizon'],
          lambda a: forecast.rolling_origin(a['series'], a['horizon'], min_train=a.get('min_train'), season=a.get('season'))),
])


def _json(value):
    def default(o):
        if isinstance(o, np.generic):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(f'Not serialisable: {type(o).__name__}')
    return json.dumps(value, ensure_ascii=False, default=default)


def call(name, arguments):
    if name not in TOOLS:
        raise KeyError(f'Unknown tool: {name}')
    return TOOLS[name]['function'](arguments or {})


def handle(message):
    method, identifier = message.get('method'), message.get('id')
    if identifier is None:
        return None  # notifications such as notifications/initialized need no reply
    try:
        if method == 'initialize':
            requested = (message.get('params') or {}).get('protocolVersion', '2025-06-18')
            result = dict(protocolVersion=requested, capabilities={'tools': {}}, serverInfo=dict(name='praxis-tools', version=VERSION))
        elif method == 'ping':
            result = {}
        elif method == 'tools/list':
            result = dict(tools=[dict(name=n, description=t['description'], inputSchema=t['schema']) for n, t in TOOLS.items()])
        elif method == 'tools/call':
            params = message.get('params') or {}
            try:
                payload = _json(call(params.get('name'), params.get('arguments')))
                result = dict(content=[dict(type='text', text=payload)], isError=False)
            except Exception as error:  # a failed computation is a tool result, not a protocol error
                result = dict(content=[dict(type='text', text=f'{type(error).__name__}: {error}')], isError=True)
        else:
            return dict(jsonrpc='2.0', id=identifier, error=dict(code=-32601, message=f'Method not found: {method}'))
    except Exception as error:
        return dict(jsonrpc='2.0', id=identifier, error=dict(code=-32603, message=str(error)))
    return dict(jsonrpc='2.0', id=identifier, result=result)


def serve():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError:
            reply = dict(jsonrpc='2.0', id=None, error=dict(code=-32700, message='Parse error'))
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + '\n')
            sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--call', nargs=2, metavar=('TOOL', 'JSON'))
    args = parser.parse_args()
    if args.list:
        for name, tool in TOOLS.items():
            print(f'{name}: {tool["description"]}')
    elif args.call:
        print(_json(call(args.call[0], json.loads(args.call[1]))))
    else:
        serve()


if __name__ == '__main__':
    main()
