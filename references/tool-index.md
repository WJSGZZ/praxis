# 工具索引

由 `scripts/gen_tool_index.py` 从工具表生成，不要手改。字段后带 * 的必填；`--describe 工具名` 看完整输入格式和一个可运行示例。

| 工具 | 字段 | 做什么 |
|---|---|---|
| `audit_data` | path*, sheet | Read-only audit of a CSV/Excel file: shape, missing values, duplicates, column types; hashes the original |
| `check_references` | references*, mailto | Check each reference line with a DOI against Crossref (title and year); lines without a DOI are reported as no_doi |
| `solve_lp` | c*, A_ub, b_ub, A_ge, b_ge, A_eq, b_eq, bounds, maximize | Linear program (HiGHS) with a duality-gap certificate |
| `solve_milp` | c*, A_ub, b_ub, A_ge, b_ge, A_eq, b_eq, bounds, integrality, maximize, time_limit | Mixed-integer linear program (HiGHS) with proved bound and gap |
| `search_literature` | query*, limit, mailto | Search OpenAlex (free, no key) for papers: title, year, DOI, citations and a free full-text link when one exists |
| `find_open_access` | doi*, mailto* | Find the legal open-access copy of a DOI via Unpaywall; needs a real contact email in mailto |
| `solve_assignment` | cost*, maximize | Optimal one-to-one assignment (Hungarian algorithm) from a cost matrix |
| `solve_tsp` | distance* | Round-trip tour heuristic (nearest neighbour + 2-opt) from a symmetric distance matrix, with a 1-tree lower bound and gap |
| `ahp_weights` | matrix* | AHP weights and consistency ratio from a reciprocal pairwise-comparison matrix (order 1-10) |
| `entropy_weights` | matrix*, directions | Entropy weights from a decision matrix (rows alternatives, columns criteria); a dispersion measure, not importance |
| `evaluate_alternatives` | matrix*, weights*, directions*, alternatives, criteria, trials, weight_sigma, seed | TOPSIS ranking with min-max normalisation and rank stability under perturbed weights |
| `sobol_sensitivity` | expression*, names*, bounds*, n, seed | Sobol indices for a scalar arithmetic expression over independent uniform inputs |
| `shortest_path` | edges*, source*, target*, directed | Dijkstra shortest path; edges [[u, v, weight]], non-negative weights |
| `max_flow` | edges*, source*, sink* | Maximum flow and a minimum cut; edges [[u, v, capacity]] |
| `minimum_spanning_tree` | edges* | Minimum spanning tree of a connected undirected graph; edges [[u, v, weight]] |
| `queue_mmc` | arrival_rate*, service_rate*, servers* | M/M/c steady-state queue: utilization, Erlang C, mean waits and lengths |
| `sir_simulate` | beta*, gamma*, population*, infected0*, days* | SIR epidemic model; daily S, I, R and R0 |
| `sir_fit` | infected*, population* | Fit SIR beta and gamma to daily infected counts; reports whether the data can separate them |
| `gm11_forecast` | series*, horizon | Grey GM(1,1) forecast of a short positive series with the posterior-error grade |
| `backtest_baselines` | series*, horizon*, min_train, season | Rolling-origin comparison of naive, seasonal naive, drift, linear trend and Holt baselines |
| `probe_structure` | property*, expression*, names*, bounds*, variable, permutation, rhs | Probe an expression for structure: convexity, monotone, symmetry, power_law, or an invariant of dx/dt=rhs |
| `dimensional_analysis` | matrix*, names* | Dimensionless groups (Buckingham Pi) from a dimension matrix: rows are base dimensions, columns are variables |
| `check_total_unimodularity` | matrix* | Is a constraint matrix totally unimodular (integral LP vertices)? Exact for incidence-type matrices and small matrices |
| `route_graph` | graph, graph_file, question, mode, operations* | Keep the record of routes tried on a problem |
| `route_to_lesson` | graph*, problem*, principle*, verified_by, tags | Draft a lesson from a finished route record (one chosen route); you supply the transferable principle |
| `test_conjecture` | lhs*, rhs*, relation*, names*, bounds*, points, tolerance | Test lhs (==, <=, >=) rhs for random points in a box (double precision) |
| `find_counterexample` | claim*, names*, domain*, trials, exhaustive_limit | Search for a counterexample of a claim (arithmetic, comparisons, and/or, abs/min/max/gcd/isprime) over integer or real ranges; exhaustive when the integer domain is small, with shrinking |
| `check_recurrence` | sequence*, coefficients*, order_bound | Check that a sequence satisfies a_n = c_1 a_{n-1} +  |
| `guess_sequence` | sequence*, max_order, max_degree, holdout | Guess a constant-coefficient linear recurrence and a polynomial formula for a sequence of rationals (exact) |
| `find_relation` | value*, constants*, dps, max_coeff | Integer relation (PSLQ) between a value and constants, e.g |
| `lesson_add` | path*, lesson* | Append a lesson to the project memory (JSON lines): problem, structure, how it was recognised, routes tried, what failed, what worked, how verified, and a transferable principle |
| `lesson_search` | path*, query, tags, limit | Search the project memory for lessons by keywords and tags before starting a new problem; also returns recurring structures |
| `solve_diffusion` | length*, cells, k*, rho_c*, initial*, t_end*, steps, left, right, source, theta, points | One-dimensional heat/diffusion equation rho_c u_t = (k u_x)_x + s by finite volumes (theta scheme), with an energy account |
| `grid_convergence_index` | f_fine*, f_medium*, f_coarse*, refinement_ratio*, safety_factor | Observed order, Richardson-extrapolated value and grid convergence index (Roache) from three refined solutions of the same quantity |
| `ols_report` | X*, y*, names, add_constant, alpha | Ordinary least squares with confidence intervals and diagnostics (normality, heteroscedasticity, autocorrelation, VIF, influential rows); `flags` lists every problem found |
| `compare_models` | X*, y*, scheme, folds | Cross-validated RMSE of a baseline, OLS, ridge and gradient boosting with fold standard errors; a model beats the baseline only by more than one standard error |
| `solve_layered_diffusion` | layers*, t_end*, t_initial*, left*, right*, times, cells_per_layer | Heat conduction through layers in series (1-D): finite volumes with a stiff integrator |
| `layered_diffusion_laplace` | layers*, times*, t_initial*, left*, right*, dps | Independent semi-analytic solution of the same layered conduction problem by transfer matrices in the Laplace domain (no mesh, no time step); the result a finite-volume solution must match |
| `calibrate_curve` | expression*, parameters*, x*, y*, theta0*, bounds, holdout | Least-squares fit of an expression in x and named parameters to data, with local confidence intervals, identifiability (Jacobian condition, parameter correlation), residual autocorrelation and an optional hold-out of the last points |
| `sobol_convergence` | expression*, names*, bounds*, n, seed | Sobol indices at base sizes n and 2n for an arithmetic expression, with the largest shift between them; indices that move by more than their confidence half-width have not converged |
| `markov_stationary` | matrix* | Stationary distribution of a finite Markov chain (row-stochastic matrix); reports irreducibility |
| `markov_absorption` | matrix*, absorbing* | Absorption probabilities and expected steps to absorption of a Markov chain with absorbing states |
| `matrix_game` | payoff* | Value and optimal mixed strategies of a zero-sum matrix game (row player maximises), by linear programming |
| `eoq` | demand*, order_cost*, holding_cost*, stockout_cost | Economic order quantity, optionally with planned backorders (stockout_cost per unit per year) |
| `newsvendor` | price*, cost*, salvage*, mean*, sd* | Newsvendor order quantity for normal demand: critical fractile, expected lost sales and expected profit |
| `cvar_portfolio` | returns*, target*, alpha, long_only | Minimum-CVaR portfolio for scenario returns (rows are scenarios) with expected return at least target (linear program) |
| `pareto_front` | points*, senses* | Non-dominated rows of a table of objective values; senses is +1 to maximise a column and -1 to minimise |
| `equilibria` | rhs*, names*, bounds*, starts | Equilibria of dx/dt = rhs(x) inside a box, classified by Jacobian eigenvalues (random multi-start; completeness not guaranteed) |
| `kalman_filter` | F*, H*, Q*, R*, x0*, P0*, observations* | Linear-Gaussian Kalman filter: state x_{t+1}=F x_t+w (cov Q), observation y_t=H x_t+v (cov R); returns filtered means, covariances and the log-likelihood |

调用方式：`uv run --locked python -m scripts.mcp_server --call 工具名 '{"字段": 值}'`；Python 入口见 [praxis-explore](../skills/praxis-explore/SKILL.md) 的对照表。
