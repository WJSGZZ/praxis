<div align="center">

<img src="demos/assets_src/praxis-logo.png" alt="Praxis: an open curve reaching beyond the known" width="160">

# Praxis

### A modeling workflow your agent can put to work.

Build a model, challenge its conclusions, and deliver the evidence.

[![Version](https://img.shields.io/badge/Version-0.3.0-263B9B?style=flat-square)](CHANGELOG.md)
[![Agent Plugins](https://img.shields.io/badge/Agent_Plugins-1.0-302B31?style=flat-square)](https://agent-plugins.org/specification)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square)](pyproject.toml)
[![Paper](https://img.shields.io/badge/Paper-LaTeX-C8533B?style=flat-square)](templates/)
[![License](https://img.shields.io/badge/License-MIT-302B31?style=flat-square)](LICENSE)

[简体中文](README.md) · **English**

[Modeling cases](#two-complete-cases-to-explore) · [Quick start](#quick-start) · [Skills](#skills) · [Tools](#math-tools) · [Compatibility](#agent-compatibility) · [Reliability](#reliability)

</div>

**Praxis is an agent plugin for mathematical modeling**: seven skills (one for whole problems, six for single kinds of request), a set of math tools your agent can call, and an evidence workflow behind them. Work from a question and data toward **a model, independent checks, and a finished report**, or use a focused capability to examine assumptions, validate a result, or improve a draft.

Use it in research, coursework, and competitions, or to study resource allocation, environmental questions, public services, and engineering decisions. Define the objective, constraints, and available data; establish an interpretable baseline before adding complexity. On an unfamiliar problem it looks for the mathematical structure first and compares several different routes on record; with no answer key it produces conclusions labelled by how sure they are, through conjectures, counterexample searches and high-precision checks. Connected records reduce bookkeeping, repeated computation, and handoff overhead, leaving more attention for the decisions that matter.

You can contribute without writing every line of code. Question an assumption in everyday language; Praxis turns it into a check and keeps a trace of what changed. Chinese and English drafts are edited for their own readers. Contest feedback leads with award-level estimates, evidence and useful next steps, while numerical diagnostics stay behind the scenes. A complete draft provides the foundation for deeper work on the questions that matter.

<table>
<tr>
<td width="33%"><strong>Get to a complete draft</strong><br>Establish a baseline, finish the report, then improve as time allows.</td>
<td width="33%"><strong>Make claims inspectable</strong><br>Keep each result connected to its checks and its place in the report.</td>
<td width="33%"><strong>Work with the team you have</strong><br>Plan responsibilities around skills, availability, and team size.</td>
</tr>
</table>

## Two complete cases to explore

The competition cases make the full workflow inspectable; they do not define the limits of Praxis. Follow an investment decision through discrete fee thresholds, or examine how spatial heat transport changes a water-saving strategy. Each case comes with a finished report and runnable evidence, organized as a complete submission package.

<table>
<tr>
<td width="50%" valign="top"><strong>CUMCM · Investment and risk</strong><br>1998 CUMCM A</td>
<td width="50%" valign="top"><strong>MCM · A Hot Bath</strong><br>2016 MCM A</td>
</tr>
<tr>
<td width="50%" valign="top"><a href="demos/cumcm-1998-a/README.en.md"><img src="demos/cumcm-1998-a/assets/overview-en.png" alt="Investment case: optimal net return across risk limits for two asset sets" width="100%"></a></td>
<td width="50%" valign="top"><a href="demos/mcm-2016-a/README.en.md"><img src="demos/mcm-2016-a/assets/overview-en.png" alt="Bath case: spatial temperatures, control, and energy bounds" width="100%"></a></td>
</tr>
<tr>
<td valign="top"><strong>When do transaction fees change the best allocation?</strong><br>Model fee thresholds and risk constraints together, then check the solution through regime enumeration and analytical bounds.</td>
<td valign="top"><strong>Can a warm average hide cold water?</strong><br>Compare a proved well-mixed benchmark with a three-dimensional thermal network, testing replenishment and temperature uniformity.</td>
</tr>
<tr>
<td valign="top"><strong>23-page Chinese report · 12 model checks</strong><br>At a CNY 1,000,000 budget, net returns are 21.90% for four assets at a 1% risk cap and 33.53% for fifteen assets at a 10% cap, under the problem's inputs and stated risk definition.</td>
<td valign="top"><strong>25-page English report · 17 model checks</strong><br>Over the 30-minute baseline, the best constant rate adds 24.14 L and a buffered six-segment schedule 21.48 L (about 11% less), against a 16.01 L ideal optimum and a 15.41 L energy bound. Coefficients come from textbook correlations, with stated ranges.</td>
</tr>
<tr>
<td valign="top"><strong>Report PDF + supporting ZIP</strong><br>Modeling code and reproduction evidence are available on the case page.</td>
<td valign="top"><strong>One report PDF</strong><br>Includes a one-page user guide and AI disclosure, with reproduction sources and evidence available separately.</td>
</tr>
<tr>
<td valign="top"><a href="demos/cumcm-1998-a/README.en.md"><strong>Explore the CUMCM case →</strong></a><br><a href="demos/cumcm-1998-a/deliverables/paper.pdf">Read the report</a> · <a href="demos/cumcm-1998-a/reproduce/">Run the model</a></td>
<td valign="top"><a href="demos/mcm-2016-a/README.en.md"><strong>Explore the MCM case →</strong></a><br><a href="demos/mcm-2016-a/deliverables/7391856.pdf">Read the report</a> · <a href="demos/mcm-2016-a/reproduce/">Run the model</a></td>
</tr>
</table>

**[Browse all cases →](demos/README.en.md)** Explore mathematical research and decision studies, with papers, code, and checks.

Reports share checked layout sources: separate contest profiles and an [AMS-style research template](templates/research-paper.tex). A pinned build environment and cross-platform typesetting checks keep layouts reproducible, while sections and figures follow the argument. Final pages are inspected as PDFs; plots use verified data and PGFplots/TikZ vector output, with other established scientific libraries available where the data require them.

Explore either case or bring your own problem. **Star Praxis** if you would like to follow its development.

## Quick start

### 1. Install for your agent

Get all seven skills, mathematical tools and the evidence workflow as one plugin. Clone the public source and choose a target:

```bash
git clone https://github.com/WJSGZZ/praxis.git
cd praxis
uv run --locked python -m scripts.build_plugin --host codex --output ../praxis-dist/codex/praxis
```

Build into a new directory. Use the matching target and follow its installation steps:

| Agent | Target | Installation |
|---|---|---|
| Codex | `codex` | [Local marketplace](references/installation.en.md#codex) |
| Claude Code | `claude` | [Plugin marketplace](references/installation.en.md#claude-code) |
| Gemini CLI | `gemini` | [Native extension](references/installation.en.md#gemini-cli) |
| GitHub Copilot CLI | `copilot` | [Local plugin](references/installation.en.md#github-copilot-cli) |
| Cursor | `cursor` | [Local plugin directory](references/installation.en.md#cursor) |

**[Open the installation guide →](references/installation.en.md)** Prefer guidance without MCP? Choose the [skills-only option](references/installation.en.md#skills-only-option).

### 2. Prepare the computing environment

Scripts and tools need **Python 3.12**, [uv](https://docs.astral.sh/uv/), and a host with local file and terminal access:

```bash
uv sync --project /path/to/plugin/skills/praxis --locked
```

Point this command at `skills/praxis` inside your installed bundle, or at the repository for a skills-only installation. Guidance alone needs no Python environment.

### 3. Use Praxis in your project

Reload or start a new session, confirm that your host has loaded Praxis, and describe the work:

> Use Praxis to analyze this problem and its data, choose an appropriate approach, and work through implementation, independent validation, and the report.

Or start with a focused request:

> Review my model. Which assumptions lack support, and which conclusions still need validation?

> We have three team members. Organize tasks around our skills and available time, prioritizing a complete report.

**The skill directory stores reusable capabilities. Your workspace stores problems, data, cases, and reports.** Scripts handle execution and traceability; the agent handles interpretation, method selection, and scientific judgment.

## Skills

The entry skill takes a problem end to end; each focused skill handles one kind of request. If you only need one thing, call that skill instead of running the whole workflow.

| Skill | Ask it to | What it covers |
|---|---|---|
| [`praxis`](SKILL.md) | "Take this problem all the way" | The shared line of reasoning, the task record, team and deadline coordination, handoffs |
| [`praxis-model`](skills/praxis-model/SKILL.md) | "How should I model this? Where do the parameters come from?" | Problem definition, assumptions and parameter grounding, route and model choice, identifiability and optimization structure |
| [`praxis-compute`](skills/praxis-compute/SKILL.md) | "Run it and keep it reproducible" | CSV/Excel audit, preserved inputs, model and validator runs, stale-result detection, evidence links |
| [`praxis-verify`](skills/praxis-verify/SKILL.md) | "Can I trust this? Did I claim too much?" | Independent checks, bounds and optimality, sensitivity, strength of each claim |
| [`praxis-explore`](skills/praxis-explore/SKILL.md) | "What kind of problem is this?", "Is there another way?", "There is no answer key" | Structure discovery, route search and elimination, experimental mathematics, lessons that carry over; `route_graph` and structure probes |
| [`praxis-dialogue`](skills/praxis-dialogue/SKILL.md) | "Explain this model", "something feels off" | Explain the model, turn objections into checks, and trace meaningful user contributions |
| [`praxis-report`](skills/praxis-report/SKILL.md) | "Write it up, fix the abstract, check the PDF" | Natural Chinese and English, paper and figure editing, references, AI disclosure, and PDF delivery |

All seven share the [methodology](references/methods.md) and one task record; see [capability handoffs](references/capabilities.md) for how work passes between them.


### Competitions are one application

Real-world and social questions, research, coursework, and competitions use the same modeling core. For a competition, verify the applicable edition and institutional rules, then configure team eligibility, report language, formats, attachments, AI disclosure, and deadlines.

The [edition registry](evals/competitions.json) separates contest rules by event and year. It includes CUMCM’s 2026 AI policy and the 2026 graduate contest’s paper format, submission windows, and defense requirements, so delivery checks start from the relevant edition.

Tell Praxis the target up front: a contest with a deadline, a contest worked through in depth first, research, or teaching. It does the work to research standard, with a stopping rule, then condenses the evidence into a paper a judge can read quickly; see [deep work and contest convergence](references/convergence.md). Before a paper goes out, independent reviewer roles try to break it ([review protocol](references/review-protocol.md)).

For solo work under time pressure, Praxis defaults to one current user action and develops the report as results become available. Team tasks are assigned around skills and dependencies. Competition requirements are not applied to unrelated projects.

## Math tools

`praxis-tools` turns common methods into callable tools with JSON in and out. Hosts without MCP can run `python -m scripts.mcp_server --call <tool> '<json>'`. The [coverage map](references/coverage-map.md) shows which kinds of problem have a ready tool and what to do when none exists. Every tool is tested against an answer derived separately: a textbook example, a closed form, or brute-force enumeration.

| Group | Tools |
|---|---|
| Programming and networks | `solve_lp` (dual-gap certificate), `solve_milp` (proved bound and gap), `solve_assignment`, `solve_tsp` (with a lower bound), `knapsack` (exact), `shortest_path`, `max_flow` (with the minimum cut), `min_cost_flow`, `minimum_spanning_tree` |
| Nonlinear and robust optimisation | `minimize_nlp` (multi-start, distinguishes converged candidates from failed feasible points), `robust_lp` (budgeted robustness with its price), `solve_mdp` (exact backward induction or value iteration) |
| Regression, tests and statistics | `ols_report` (intervals and diagnostics), `compare_models` (cross-validated against a baseline), `hypothesis_test` (effect sizes and assumption flags), `bootstrap_ci`, `arima_forecast`, `pca_report`, `cluster_report` (with stability), `calibrate_curve` (identifiability and hold-out) |
| Evaluation and weights | `ahp_weights` (consistency ratio), `entropy_weights`, `evaluate_alternatives` (TOPSIS with weight-stability) |
| Forecasting and dynamics | `backtest_baselines` (rolling-origin), `gm11_forecast`, `sir_simulate`, `sir_fit` (reports identifiability), `queue_mmc`, `equilibria` (equilibria and stability), `kalman_filter`, `solve_ode` (re-run at tighter tolerance), `solve_layered_diffusion` with the independent `layered_diffusion_laplace`, `grid_convergence_index`, `solve_diffusion` (finite volumes with an energy account) |
| Decisions and risk | `markov_stationary`, `markov_absorption`, `matrix_game`, `bimatrix_nash`, `eoq`, `newsvendor`, `cvar_portfolio` (minimum CVaR over scenarios), `pareto_front` |
| Structure and exploration | `probe_structure` (convexity, monotonicity, symmetry, power laws, invariants), `dimensional_analysis`, `check_total_unimodularity`, `route_graph` (route records), `test_conjecture`, `find_counterexample`, `guess_sequence`, `check_recurrence` (finite-check proof), `find_relation`, `route_to_lesson`, `lesson_add`, `lesson_search` |
| Uncertainty | `sobol_sensitivity`, `sobol_convergence`, `monte_carlo` (with a settled check) |
| Data and free literature | `audit_data`, `search_literature` (OpenAlex, with free full-text links), `find_open_access` (Unpaywall), `check_references` (DOI, title and year against Crossref) |

Portable, Codex, Claude and Copilot exports also include the open-source [arXiv server](https://github.com/blazickjp/arxiv-mcp-server) (Apache-2.0, pinned version) for preprint full text, LaTeX sections, and BibTeX export. For paywalled journal papers the tools find legal free copies; the rest can come from a school library.

When to use each method, what to check, and the usual misuse are in the [method and tool library](references/model-library.md). Python covers the ordinary uses of MATLAB and R.

## Agent compatibility

Praxis keeps its modeling logic shared across agents. Host-specific exports supply the manifests and path variables each agent expects, while all seven skills and the core engine come from the same source.

Start with the [plugin installation guide](references/installation.en.md), or use the [standalone skill](references/installation.en.md#skills-only-option) where appropriate. Installing on a desktop or CLI does not provision browser-only sessions, cloud agents or remote machines.

See [host compatibility](references/agent-compatibility.md) for capability requirements, skill discovery paths, official references and the scope of validation.

## Command line and plugin layout

<details>
<summary><strong>CLI: initialize a case in a separate workspace</strong></summary>

These commands use POSIX shell syntax. Replace the paths with your actual locations:

```bash
BUNDLE="$HOME/.agents/skills/praxis"
WORKSPACE="/absolute/path/to/your/project"

"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" \
  --workspace "$WORKSPACE" init \
  --name example \
  --problem "$WORKSPACE/problem.pdf" \
  --data "$WORKSPACE/data.csv"
```

The agent writes and reviews the case's `model.py` and `validate.py`, then executes `run`. Data, cases, and outputs are excluded from Git by default; project rules come from your workspace.

See the [Execution contract](references/automation.md) for the complete interface. For work that spans several rounds, the [task coordinator](references/workflow.md) retrieves relevant local lessons at initialization and tracks one next action against the budget, current evidence, reviews and report. Failed or stale runs block delivery. A valid draft can remain open for a worthwhile improvement; the agent still chooses the mathematics and reviews the science.

For troubleshooting after delivery, [run feedback](references/feedback.md) preserves the stages, reviews, revisions and stopping reason you actually record. Select the files to include in a local sharing copy; folders and ZIPs use the same read-only checks. Nothing is uploaded automatically. Unavailable model identity, costs and chat history remain unknown, and a readable feedback package does not certify the underlying research.

</details>

<details>
<summary><strong>Plugin layout</strong></summary>

The export follows [Agent Plugins 1.0](https://agent-plugins.org/specification) and includes both component types that version defines:

```text
praxis-plugin/
  plugin.json
  mcp.json                  # core tools and applicable external services
  .codex-plugin/            # Codex compatibility entry
  # Other manifests are generated by --host
  skills/
    praxis/                 # entry skill, with all references, scripts and tool code
    praxis-model/  praxis-compute/  praxis-verify/  praxis-explore/  praxis-dialogue/  praxis-report/
```

Your problems, data, and cases stay in your own workspace, never in the plugin.

| Layer | What it does | How it connects |
|---|---|---|
| Skills | Frame the question, choose methods, assess evidence and write | Focused capabilities share one modeling method |
| MCP and scripts | Run calculations, audit data and check references | The same tools are available through MCP or the command line |
| Evidence workflow | Connect tasks to runs, checks and report claims | Changed inputs or code send affected results back for review |

The agent coordinates the work using deterministic scripts and your project's rules; no separate orchestration service is required.

</details>

## Reliability

- 550+ automated tests cover analytical answers, input protection, failed and stale results, PDF helpers, the math tools, and plugin export.
- Both complete cases ship independent checks and runnable reproduction code; every number traces back to the report.
- Each conclusion states its basis and the conditions it holds under; failed runs are kept, not rewritten.

<details>
<summary><strong>Development and exercise commands</strong></summary>

```bash
uv sync --locked --group dev
uv run --locked python -m pytest -q
uv run --locked python -m scripts.release_check   # before a release: rerun the demos, confirm records are unchanged, run the tests
uv run --locked python -m examples.decision_sensitivity_demo
uv run --locked python -m examples.structural_reasoning_demo
uv run --locked python -m examples.exploration_demo
```


</details>

## Sources and licensing

Original code and documentation use the [MIT License](LICENSE). Workflow design references MathModelHub; Sobol analysis and TOPSIS use SALib and pyMCDM. See [Third-party notices](THIRD_PARTY_NOTICES.md) for reuse scope and upstream licenses. Cite methods, data, and tools where they are actually used in your report.
