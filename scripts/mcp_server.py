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
from modeling import decision, decision_models, dynamics, epidemic, experiment, forecast, graph, lessons, optimize, pde, queueing, regression, routes, sensitivity, structure, weights  # noqa: E402
from scripts import audit_data, check_references, literature  # noqa: E402

def _project_version():
    """The single source of the version number is pyproject.toml."""
    import tomllib
    return tomllib.loads((Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text())['project']['version']


VERSION = _project_version()
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


def _scalar(expression, names):
    """Scalar function of a point (list of floats) from an arithmetic expression."""
    model = _compile(expression, names)
    return lambda x: float(model(np.atleast_2d(np.asarray(x, float)))[0])


PREDICATE_FUNCTIONS = {'abs': abs, 'min': min, 'max': max, 'gcd': __import__('math').gcd, 'isprime': lambda n: bool(__import__('sympy').isprime(n))}


def _predicate(expression, names):
    """Boolean function of integer or float arguments: arithmetic, comparisons, and/or/not and a few functions. Nothing else."""
    tree = ast.parse(expression, mode='eval')
    arithmetic = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
                  ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Load) + arithmetic):
            continue
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)) or isinstance(node.value, bool):
                raise ValueError('Only numeric constants are allowed')
        elif isinstance(node, ast.Name):
            if node.id not in names and node.id not in PREDICATE_FUNCTIONS:
                raise ValueError(f'Unknown name: {node.id}')
        elif isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in PREDICATE_FUNCTIONS and not node.keywords):
                raise ValueError('Only simple calls to abs, min, max, gcd, isprime are allowed')
        else:
            raise ValueError(f'Disallowed syntax: {type(node).__name__}')
    code = compile(tree, '<predicate>', 'eval')
    return lambda *args: bool(eval(code, {'__builtins__': {}}, {**PREDICATE_FUNCTIONS, **dict(zip(names, args))}))


def _probe(a):
    names, bounds, kind = a['names'], a['bounds'], a['property']
    if kind == 'invariant':
        rhs = [_scalar(e, names) for e in a['rhs']]
        return structure.check_invariant(lambda x: np.array([f(x) for f in rhs]), _scalar(a['expression'], names), bounds)
    f = _scalar(a['expression'], names)
    if kind == 'convexity':
        return structure.check_convexity(f, bounds)
    if kind == 'monotone':
        return structure.check_monotone(f, bounds, names.index(a['variable']))
    if kind == 'symmetry':
        return structure.check_symmetry(f, bounds, a['permutation'])
    if kind == 'power_law':
        return structure.check_power_law(f, bounds)
    raise ValueError('property must be convexity, monotone, symmetry, power_law or invariant')


def _conjecture(a):
    names, bounds = a['names'], a['bounds']
    left, right = _scalar(a['lhs'], names), _scalar(a['rhs'], names)
    rng = np.random.default_rng(a.get('seed', 2027))
    lo, hi = np.asarray(bounds, float).T
    worst, where = 0.0, None
    for _ in range(a.get('points', 5000)):
        x = lo + (hi - lo) * rng.random(len(lo))
        u, v = left(x), right(x)
        gap = abs(u - v) if a['relation'] == '==' else (u - v if a['relation'] == '<=' else v - u)
        if gap > worst:
            worst, where = gap, x.tolist()
    tol = a.get('tolerance', 1e-9)
    return dict(holds=worst <= tol, proved=worst > tol, worst_violation=worst, at=where, precision='double',
                note='Double precision; use modeling.experiment.test_conjecture for high precision.' if worst <= tol else 'Violation found.')


def _profile(expression):
    """Function of x (array) from an arithmetic expression in x."""
    model = _compile(expression, ['x'])
    return lambda xs: model(np.asarray(xs, float)[:, None])


def _bc(spec):
    if spec is None:
        return ('neumann', 0.0)
    return tuple(spec)


def _diffusion(a):
    r = pde.solve_diffusion(a['length'], a.get('cells', 100), a['k'], a['rho_c'], _profile(a['initial']), a['t_end'], a.get('steps', 200),
                            left=_bc(a.get('left')), right=_bc(a.get('right')), source=_profile(a['source']) if a.get('source') else None, theta=a.get('theta', .5))
    out = {k: (v.tolist() if hasattr(v, 'tolist') else v) for k, v in r.items()}
    if a.get('points'):
        ends = [None, None]
        for i, bc in enumerate((_bc(a.get('left')), _bc(a.get('right')))):
            ends[i] = float(bc[1]) if bc[0] == 'dirichlet' else None
        out['values_at'] = pde.values_at(r, a['points'], left=ends[0], right=ends[1])
    return out


def _equilibria(a):
    names = a['names']
    funcs = [_scalar(e, names) for e in a['rhs']]
    return dynamics.equilibria(lambda x: [f(x) for f in funcs], a['bounds'], starts=a.get('starts', 200))


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
    _tool('solve_lp', 'Linear program (HiGHS) with a duality-gap certificate. Rows: A_ub x <= b_ub, A_ge x >= b_ge, A_eq x = b_eq; bounds default to x >= 0. Shadow prices (change in the optimal objective per unit increase of the right-hand side) are returned as ineq_duals (<= rows) and ge_duals (>= rows).',
          {'c': SERIES, 'A_ub': MATRIX, 'b_ub': SERIES, 'A_ge': MATRIX, 'b_ge': SERIES, 'A_eq': MATRIX, 'b_eq': SERIES, 'bounds': {'type': 'array'}, 'maximize': {'type': 'boolean'}}, ['c'],
          lambda a: optimize.solve_lp(a['c'], **{k: v for k, v in a.items() if k != 'c'})),
    _tool('solve_milp', 'Mixed-integer linear program (HiGHS) with proved bound and gap. Rows: A_ub x <= b_ub, A_ge x >= b_ge, A_eq x = b_eq. integrality: 1 for integer variables.',
          {'c': SERIES, 'A_ub': MATRIX, 'b_ub': SERIES, 'A_ge': MATRIX, 'b_ge': SERIES, 'A_eq': MATRIX, 'b_eq': SERIES, 'bounds': {'type': 'array'}, 'integrality': SERIES,
           'maximize': {'type': 'boolean'}, 'time_limit': _num('seconds')}, ['c'],
          lambda a: optimize.solve_milp(a['c'], **{k: v for k, v in a.items() if k != 'c'})),
    _tool('search_literature', 'Search OpenAlex (free, no key) for papers: title, year, DOI, citations and a free full-text link when one exists. Needs internet.',
          {'query': {'type': 'string'}, 'limit': {'type': 'integer'}, 'mailto': {'type': 'string'}}, ['query'],
          lambda a: literature.search_works(a['query'], a.get('limit', 5), a.get('mailto', 'unknown@example.org'))),
    _tool('find_open_access', 'Find the legal open-access copy of a DOI via Unpaywall; needs a real contact email in mailto. Paywalled papers are reported as such.',
          {'doi': {'type': 'string'}, 'mailto': {'type': 'string'}}, ['doi', 'mailto'],
          lambda a: literature.open_access_for(a['doi'], a['mailto'])),
    _tool('solve_assignment', 'Optimal one-to-one assignment (Hungarian algorithm) from a cost matrix.',
          {'cost': MATRIX, 'maximize': {'type': 'boolean'}}, ['cost'], lambda a: optimize.assignment(a['cost'], maximize=a.get('maximize', False))),
    _tool('solve_tsp', 'Round-trip tour heuristic (nearest neighbour + 2-opt) from a symmetric distance matrix, with a 1-tree lower bound and gap.',
          {'distance': MATRIX}, ['distance'], lambda a: optimize.tsp(a['distance'])),
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
    _tool('probe_structure', 'Probe an expression for structure: convexity, monotone, symmetry, power_law, or an invariant of dx/dt=rhs. A found violation is a proof; otherwise it is evidence on sampled points only.',
          {'property': {'type': 'string', 'enum': ['convexity', 'monotone', 'symmetry', 'power_law', 'invariant']}, 'expression': {'type': 'string'},
           'names': {'type': 'array', 'items': {'type': 'string'}}, 'bounds': MATRIX, 'variable': {'type': 'string'},
           'permutation': {'type': 'array', 'items': {'type': 'integer'}}, 'rhs': {'type': 'array', 'items': {'type': 'string'}, 'description': 'dx_i/dt expressions, for property=invariant'}},
          ['property', 'expression', 'names', 'bounds'], _probe),
    _tool('dimensional_analysis', 'Dimensionless groups (Buckingham Pi) from a dimension matrix: rows are base dimensions, columns are variables.',
          {'matrix': MATRIX, 'names': {'type': 'array', 'items': {'type': 'string'}}}, ['matrix', 'names'],
          lambda a: structure.buckingham_pi(a['matrix'], a['names'])),
    _tool('check_total_unimodularity', 'Is a constraint matrix totally unimodular (integral LP vertices)? Exact for incidence-type matrices and small matrices.',
          {'matrix': MATRIX}, ['matrix'], lambda a: structure.is_network_matrix(a['matrix'])),
    _tool('route_graph', 'Keep the record of routes tried on a problem. Pass the current graph (or a question to start) and a list of operations: add_structure, add_assumption, add_path, attack, kill, keep_result, merge, choose. Returns the graph, record problems and a readable trace.',
          {'graph': {'type': 'object'}, 'question': {'type': 'string'}, 'mode': {'type': 'string', 'enum': ['exploratory', 'standard']}, 'operations': {'type': 'array', 'items': {'type': 'object'}}}, ['operations'],
          lambda a: routes.apply(a.get('graph'), a['operations'], question=a.get('question'), mode=a.get('mode', 'exploratory'))),
    _tool('route_to_lesson', 'Draft a lesson from a finished route record (one chosen route); you supply the transferable principle. Pass the result to lesson_add.',
          {'graph': {'type': 'object'}, 'problem': {'type': 'string'}, 'principle': {'type': 'string'}, 'verified_by': {'type': 'string'}, 'tags': {'type': 'array', 'items': {'type': 'string'}}},
          ['graph', 'problem', 'principle'], lambda a: routes.draft_lesson(a['graph'], problem=a['problem'], principle=a['principle'], verified_by=a.get('verified_by', ''), tags=a.get('tags'))),
    _tool('test_conjecture', 'Test lhs (==, <=, >=) rhs for random points in a box (double precision). A violation refutes the conjecture; passing is evidence only.',
          {'lhs': {'type': 'string'}, 'rhs': {'type': 'string'}, 'relation': {'type': 'string', 'enum': ['==', '<=', '>=']},
           'names': {'type': 'array', 'items': {'type': 'string'}}, 'bounds': MATRIX, 'points': {'type': 'integer'}, 'tolerance': _num()},
          ['lhs', 'rhs', 'relation', 'names', 'bounds'], _conjecture),
    _tool('find_counterexample', 'Search for a counterexample of a claim (arithmetic, comparisons, and/or, abs/min/max/gcd/isprime) over integer or real ranges; exhaustive when the integer domain is small, with shrinking.',
          {'claim': {'type': 'string'}, 'names': {'type': 'array', 'items': {'type': 'string'}},
           'domain': {'type': 'array', 'items': {'type': 'array'}, 'description': "[['int'|'real', lo, hi], ...] one per name"}, 'trials': {'type': 'integer'},
           'exhaustive_limit': {'type': 'integer', 'description': 'integer domains with at most this many cases are checked exhaustively (default 200000)'}},
          ['claim', 'names', 'domain'],
          lambda a: experiment.find_counterexample(_predicate(a['claim'], a['names']), [tuple(d) for d in a['domain']], trials=a.get('trials', 20000), exhaustive_limit=a.get('exhaustive_limit', 200000))),
    _tool('check_recurrence', 'Check that a sequence satisfies a_n = c_1 a_{n-1} + ... + c_d a_{n-d} and list failing indices; with order_bound (e.g. a transfer-matrix size) a clean check on order_bound + d terms is a complete proof.',
          {'sequence': SERIES, 'coefficients': SERIES, 'order_bound': {'type': 'integer'}}, ['sequence', 'coefficients'],
          lambda a: experiment.check_linear_recurrence(a['sequence'], a['coefficients'], order_bound=a.get('order_bound'))),
    _tool('guess_sequence', 'Guess a constant-coefficient linear recurrence and a polynomial formula for a sequence of rationals (exact). Results are conjectures beyond the data.',
          {'sequence': SERIES, 'max_order': {'type': 'integer'}, 'max_degree': {'type': 'integer'}, 'holdout': {'type': 'integer', 'description': 'last terms kept out of the fit and used to test the guess'}}, ['sequence'],
          lambda a: dict(recurrence=experiment.guess_linear_recurrence(a['sequence'], a.get('max_order', 6), a.get('holdout', 0)),
                         polynomial=experiment.guess_polynomial(a['sequence'], a.get('max_degree', 8)))),
    _tool('find_relation', 'Integer relation (PSLQ) between a value and constants, e.g. value "zeta(2)", constants {"pi2": "pi**2"}. A hint to prove, not a proof.',
          {'value': {'type': 'string'}, 'constants': {'type': 'object'}, 'dps': {'type': 'integer'}, 'max_coeff': {'type': 'integer'}}, ['value', 'constants'],
          lambda a: experiment.find_relation(a['value'], a['constants'], dps=a.get('dps', 50), max_coeff=a.get('max_coeff', 1000))),
    _tool('lesson_add', 'Append a lesson to the project memory (JSON lines): problem, structure, how it was recognised, routes tried, what failed, what worked, how verified, and a transferable principle.',
          {'path': {'type': 'string', 'description': 'e.g. planning/lessons.jsonl inside the project'}, 'lesson': {'type': 'object'}}, ['path', 'lesson'],
          lambda a: lessons.add_lesson(Path(a['path']), a['lesson'])),
    _tool('lesson_search', 'Search the project memory for lessons by keywords and tags before starting a new problem; also returns recurring structures.',
          {'path': {'type': 'string'}, 'query': {'type': 'string'}, 'tags': {'type': 'array', 'items': {'type': 'string'}}, 'limit': {'type': 'integer'}}, ['path'],
          lambda a: dict(lessons=lessons.search_lessons(Path(a['path']), a.get('query', ''), tags=a.get('tags'), limit=a.get('limit', 5)), patterns=lessons.patterns(Path(a['path'])))),
    _tool('solve_diffusion', 'One-dimensional heat/diffusion equation rho_c u_t = (k u_x)_x + s by finite volumes (theta scheme), with an energy account. Boundaries: ["dirichlet", value], ["neumann", flux_in], ["robin", h, u_inf].',
          {'length': _num(), 'cells': {'type': 'integer'}, 'k': _num(), 'rho_c': _num(), 'initial': {'type': 'string', 'description': 'expression in x'}, 't_end': _num(), 'steps': {'type': 'integer'},
           'left': {'type': 'array'}, 'right': {'type': 'array'}, 'source': {'type': 'string', 'description': 'expression in x (W/m^3)'}, 'theta': _num(),
           'points': {'type': 'array', 'items': {'type': 'number'}, 'description': 'positions at which to return the temperature (linear interpolation; Dirichlet end values are used at the ends)'}},
          ['length', 'k', 'rho_c', 'initial', 't_end'], _diffusion),
    _tool('grid_convergence_index', 'Observed order, Richardson-extrapolated value and grid convergence index (Roache) from three refined solutions of the same quantity.',
          {'f_fine': _num(), 'f_medium': _num(), 'f_coarse': _num(), 'refinement_ratio': _num(), 'safety_factor': _num()}, ['f_fine', 'f_medium', 'f_coarse', 'refinement_ratio'],
          lambda a: pde.grid_convergence_index(a['f_fine'], a['f_medium'], a['f_coarse'], a['refinement_ratio'], safety_factor=a.get('safety_factor', 1.25))),
    _tool('ols_report', 'Ordinary least squares with confidence intervals and diagnostics (normality, heteroscedasticity, autocorrelation, VIF, influential rows); `flags` lists every problem found.',
          {'X': MATRIX, 'y': SERIES, 'names': {'type': 'array', 'items': {'type': 'string'}}, 'add_constant': {'type': 'boolean'}, 'alpha': _num()}, ['X', 'y'],
          lambda a: regression.ols_report(a['X'], a['y'], names=a.get('names'), add_constant=a.get('add_constant', True), alpha=a.get('alpha', .05))),
    _tool('compare_models', 'Cross-validated RMSE of a baseline, OLS, ridge and gradient boosting with fold standard errors; a model beats the baseline only by more than one standard error. scheme: kfold or time (rows in time order).',
          {'X': MATRIX, 'y': SERIES, 'scheme': {'type': 'string', 'enum': ['kfold', 'time']}, 'folds': {'type': 'integer'}}, ['X', 'y'],
          lambda a: regression.compare_models(a['X'], a['y'], scheme=a.get('scheme', 'kfold'), folds=a.get('folds', 5))),
    _tool('markov_stationary', 'Stationary distribution of a finite Markov chain (row-stochastic matrix); reports irreducibility.', {'matrix': MATRIX}, ['matrix'], lambda a: decision_models.markov_stationary(a['matrix'])),
    _tool('markov_absorption', 'Absorption probabilities and expected steps to absorption of a Markov chain with absorbing states.',
          {'matrix': MATRIX, 'absorbing': {'type': 'array', 'items': {'type': 'integer'}}}, ['matrix', 'absorbing'], lambda a: decision_models.markov_absorption(a['matrix'], a['absorbing'])),
    _tool('matrix_game', 'Value and optimal mixed strategies of a zero-sum matrix game (row player maximises), by linear programming.', {'payoff': MATRIX}, ['payoff'], lambda a: decision_models.matrix_game(a['payoff'])),
    _tool('eoq', 'Economic order quantity, optionally with planned backorders (stockout_cost per unit per year).',
          {'demand': _num(), 'order_cost': _num(), 'holding_cost': _num(), 'stockout_cost': _num()}, ['demand', 'order_cost', 'holding_cost'],
          lambda a: decision_models.eoq(a['demand'], a['order_cost'], a['holding_cost'], stockout_cost=a.get('stockout_cost'))),
    _tool('newsvendor', 'Newsvendor order quantity for normal demand: critical fractile, expected lost sales and expected profit.',
          {'price': _num(), 'cost': _num(), 'salvage': _num(), 'mean': _num(), 'sd': _num()}, ['price', 'cost', 'salvage', 'mean', 'sd'],
          lambda a: decision_models.newsvendor(a['price'], a['cost'], a['salvage'], a['mean'], a['sd'])),
    _tool('cvar_portfolio', 'Minimum-CVaR portfolio for scenario returns (rows are scenarios) with expected return at least target (linear program). Conditional on the scenarios; not a forecast.',
          {'returns': MATRIX, 'target': _num(), 'alpha': _num(), 'long_only': {'type': 'boolean'}}, ['returns', 'target'],
          lambda a: decision_models.cvar_portfolio(a['returns'], a['target'], alpha=a.get('alpha', .95), long_only=a.get('long_only', True))),
    _tool('pareto_front', 'Non-dominated rows of a table of objective values; senses is +1 to maximise a column and -1 to minimise.',
          {'points': MATRIX, 'senses': {'type': 'array', 'items': {'type': 'integer'}}}, ['points', 'senses'], lambda a: decision_models.pareto_front(a['points'], a['senses'])),
    _tool('equilibria', 'Equilibria of dx/dt = rhs(x) inside a box, classified by Jacobian eigenvalues (random multi-start; completeness not guaranteed).',
          {'rhs': {'type': 'array', 'items': {'type': 'string'}}, 'names': {'type': 'array', 'items': {'type': 'string'}}, 'bounds': MATRIX, 'starts': {'type': 'integer'}}, ['rhs', 'names', 'bounds'], _equilibria),
    _tool('kalman_filter', 'Linear-Gaussian Kalman filter: state x_{t+1}=F x_t+w (cov Q), observation y_t=H x_t+v (cov R); returns filtered means, covariances and the log-likelihood.',
          {'F': MATRIX, 'H': MATRIX, 'Q': MATRIX, 'R': MATRIX, 'x0': SERIES, 'P0': MATRIX, 'observations': {'type': 'array'}}, ['F', 'H', 'Q', 'R', 'x0', 'P0', 'observations'],
          lambda a: dynamics.kalman_filter(a['F'], a['H'], a['Q'], a['R'], a['x0'], a['P0'], a['observations'])),
])


# One minimal, runnable call per tool that needs a shape to be guessed; a test calls every example, so they stay correct.
EXAMPLES = {
    'solve_lp': dict(c=[2, 3], A_ge=[[1, 1]], b_ge=[4]),
    'solve_milp': dict(c=[-1, -1], A_ub=[[2, 2]], b_ub=[5], integrality=[1, 1], bounds=[[0, 10], [0, 10]]),
    'probe_structure': dict(property='convexity', expression='x**2 + y**2', names=['x', 'y'], bounds=[[-1, 1], [-1, 1]]),
    'dimensional_analysis': dict(matrix=[[0, 0, 0, 1], [0, 1, 1, 0], [1, 0, -2, 0]], names=['T', 'L', 'g', 'm']),
    'check_total_unimodularity': dict(matrix=[[1, 1, 0], [-1, 0, 1], [0, -1, -1]]),
    'route_graph': dict(question='Ship goods at least cost', operations=[dict(op='add_path', key='lp', title='linear program'), dict(op='add_path', key='greedy', title='greedy rule'),
                                                                         dict(op='kill', key='greedy', reason='no optimality guarantee')]),
    'test_conjecture': dict(lhs='x**2', rhs='x', relation='<=', names=['x'], bounds=[[0, 3]]),
    'find_counterexample': dict(claim='isprime(n*n + n + 41)', names=['n'], domain=[['int', 0, 100]]),
    'guess_sequence': dict(sequence=[1, 3, 11, 41, 153, 571, 2131, 7953, 29681, 110771, 413403, 1542841], holdout=3),
    'check_recurrence': dict(sequence=[1, 3, 11, 41, 153, 571, 2131, 7953, 29681, 110771, 413403, 1542841], coefficients=[4, -1], order_bound=8),
    'find_relation': dict(value='zeta(2)', constants={'pi2': 'pi**2'}),
    'solve_diffusion': dict(length=1, k=1, rho_c=1, initial='sin(3.141592653589793*x)', t_end=0.1, cells=100, steps=100, left=['dirichlet', 0], right=['dirichlet', 0], points=[0.5]),
    'matrix_game': dict(payoff=[[3, 2], [1, 4]]),
    'ols_report': dict(X=[[1, 2], [2, 1], [3, 5], [4, 3], [5, 8], [6, 4], [7, 9], [8, 6], [9, 11], [10, 7]], y=[3.1, 3.9, 8.2, 8.8, 14.1, 12.9, 19.7, 18.2, 25.1, 22.8], names=['a', 'b']),
    'compare_models': dict(X=[[i] for i in range(40)], y=[2.0 * i + (i % 3) for i in range(40)], folds=4),
    'equilibria': dict(rhs=['x*(1-x)'], names=['x'], bounds=[[-0.5, 2]]),
    'sir_fit': dict(infected=[10, 14, 20, 28, 40, 57, 80, 112, 156, 215], population=1000000),
    'lesson_search': dict(path='planning/lessons.jsonl', query='recurrence'),
    'eoq': dict(demand=1200, order_cost=50, holding_cost=2),
    'newsvendor': dict(price=10, cost=6, salvage=2, mean=100, sd=20),
}
for _name, _example in EXAMPLES.items():
    TOOLS[_name]['schema']['examples'] = [_example]


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
    schema = TOOLS[name]['schema']
    given = arguments or {}
    missing = [k for k in schema.get('required', []) if k not in given]
    unknown = [k for k in given if k not in schema['properties']]
    if missing or unknown:
        raise ValueError(f'{name}: ' + (f'missing field(s) {missing}; ' if missing else '') + (f'unknown field(s) {unknown}; ' if unknown else '')
                         + f'required: {schema.get("required", [])}; all fields: {list(schema["properties"])}')
    return TOOLS[name]['function'](given)


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
    parser.add_argument('--list', action='store_true', help='list tools with their fields (* = required)')
    parser.add_argument('--describe', metavar='TOOL', help='print one tool\'s full input schema')
    parser.add_argument('--call', nargs=2, metavar=('TOOL', 'JSON'))
    args = parser.parse_args()
    if args.list:
        for name, tool in TOOLS.items():
            required = tool['schema'].get('required', [])
            fields = ', '.join(f'{k}*' if k in required else k for k in tool['schema']['properties'])
            print(f'{name}({fields}): {tool["description"]}')
    elif args.describe:
        tool = TOOLS[args.describe]
        print(json.dumps(dict(name=args.describe, description=tool['description'], input=tool['schema']), ensure_ascii=False, indent=1))
    elif args.call:
        print(_json(call(args.call[0], json.loads(args.call[1]))))
    else:
        serve()


if __name__ == '__main__':
    main()
