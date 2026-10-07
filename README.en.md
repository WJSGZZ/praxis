<div align="center">

# Praxis

### A modeling workflow your agent can put to work.

Build a model, challenge its conclusions, and deliver the evidence.

[![Agent Skills](https://img.shields.io/badge/Agent_Skills-portable-334155?style=flat-square)](https://agentskills.io/specification)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-526B55?style=flat-square)](LICENSE)

[简体中文](README.md) · **English**

[CUMCM case](demos/cumcm-1998-a/README.en.md) · [MCM case](demos/mcm-2016-a/README.en.md) · [Quick start](#quick-start) · [Capabilities](#capabilities) · [Agent compatibility](#agent-compatibility) · [Validation and limitations](#validation-and-limitations)

</div>

**Praxis equips AI agents for mathematical modeling**, combining a portable skill, computing scripts, evidence workflows, and plugin export. Work from a question and data toward **a model, independent checks, and a finished report**, or use a focused capability to examine assumptions, validate a result, or improve a draft.

Use it in research, coursework, and competitions, or to study resource allocation, environmental questions, public services, and engineering decisions. Define the objective, constraints, and available data; establish an interpretable baseline before adding complexity. Connected records reduce bookkeeping, repeated computation, and handoff overhead, leaving more attention for the decisions that matter.

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
<td width="50%" valign="top"><a href="demos/cumcm-1998-a/README.en.md"><img src="demos/cumcm-1998-a/assets/overview-en.png" alt="Investment case: allocation, validation, and a complete report" width="100%"></a></td>
<td width="50%" valign="top"><a href="demos/mcm-2016-a/README.en.md"><img src="demos/mcm-2016-a/assets/overview-en.png" alt="Bath case: spatial temperatures, control, and energy bounds" width="100%"></a></td>
</tr>
<tr>
<td valign="top"><strong>When do transaction fees change the best allocation?</strong><br>Model fee thresholds and risk constraints together, then check the solution through regime enumeration and analytical bounds.</td>
<td valign="top"><strong>Can a warm average hide cold water?</strong><br>Compare a proved well-mixed benchmark with a three-dimensional thermal network, testing replenishment and temperature uniformity.</td>
</tr>
<tr>
<td valign="top"><strong>16-page Chinese report · 12 model checks</strong><br>At a CNY 1,000,000 budget, net returns are 21.90% for four assets at a 1% risk cap and 33.53% for fifteen assets at a 10% cap, under the problem's inputs and stated risk definition.</td>
<td valign="top"><strong>19-page English report · 17 model checks</strong><br>Over the 30-minute baseline, the spatial candidate adds 10.48 L, versus a 6.53 L ideal optimum and a 5.98 L energy bound. Explore 16 scenario variations; coefficients are assumed, not measured.</td>
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

Explore either case or bring your own problem. **Star Praxis** if you would like to follow its development.

## Quick start

### 1. Install the skill

For local agents that support the shared personal skills directory, clone into a destination that does not already exist:

```bash
git clone https://github.com/WJSGZZ/praxis.git ~/.agents/skills/praxis
```

For Claude Code, use `~/.claude/skills/praxis`. See [Agent compatibility](#agent-compatibility) for other locations. Enable only one copy per host; existing installations are not migrated automatically.

### 2. Prepare the computing environment

Running scripts requires **Python 3.12**, [uv](https://docs.astral.sh/uv/), and a host with local file and terminal access:

```bash
uv sync --project ~/.agents/skills/praxis --locked
```

You can use the methodological guidance without setting up Python. Adjust the skill path if you installed elsewhere.

### 3. Use Praxis in your project

Reload skills or start a new session, confirm that your host has loaded Praxis, and describe the work:

> Use Praxis to analyze this problem and its data, choose an appropriate approach, and work through implementation, independent validation, and the report.

Or start with a focused request:

> Review my model. Which assumptions lack support, and which conclusions still need validation?

> We have three team members. Organize tasks around our skills and available time, prioritizing a complete report.

**The skill directory stores reusable capabilities. Your workspace stores problems, data, cases, and reports.** Scripts handle execution and traceability; the agent handles interpretation, method selection, and scientific judgment.

This is the English project overview. The skill instructions and most detailed references are currently in Chinese; an English README does not imply a fully translated instruction set.

## Capabilities

| Capability | What it provides | Reference |
|---|---|---|
| Problem analysis | Requirements, variables, constraints, success criteria, and task dependencies | [Shared methodology](references/methods.md) |
| Models and mathematical reasoning | Baselines and necessary extensions; conditional guidance on dimensions, invariance, identifiability, and optimization structure | [Mathematical reasoning](references/mathematical-reasoning.md) |
| Data and computation | CSV/Excel audits, preserved inputs, reproducible runs, Sobol analysis, and TOPSIS evaluation | [Data and computation](references/data-computing.md) |
| Independent validation | Appropriate comparisons and checks, failed-run records, stale-evidence detection, and numerical task evidence links | [Execution contract](references/automation.md) |
| Visualization and writing | Figures, arguments, and reports grounded in valid results, with consistent numbers, units, and sources | [Visualization](references/visualization.md) · [Writing](references/writing.md) |
| Coordination and delivery | Starting strategies for one-, two-, and three-person teams; ownership, handoffs, fallback approaches, and delivery reserves | [Team adaptation](references/context-and-team.md) · [Solo delivery](references/solo-delivery.md) |

Capabilities follow the same reasoning workflow; you do not have to activate every capability for every request. See [Capability handoffs](references/capabilities.md) for shared inputs and outputs.

### Competitions are one application

Real-world and social questions, research, coursework, and competitions use the same modeling core. For a competition, verify the applicable edition and institutional rules, then configure team eligibility, report language, formats, attachments, AI disclosure, and deadlines.

For solo work under time pressure, Praxis defaults to one current user action and develops the report as results become available. Team tasks are assigned around skills and dependencies. Competition requirements are not applied to unrelated projects.

## Agent compatibility

Use the same `SKILL.md`, references, and Python tools, with the discovery directory your host expects:

| Agent | Project directory | Local personal directory |
|---|---|---|
| Codex | `.agents/skills/praxis` | `~/.agents/skills/praxis` |
| Claude Code | `.claude/skills/praxis` | `~/.claude/skills/praxis` |
| Gemini CLI | `.agents/skills/praxis` or `.gemini/skills/praxis` | `~/.agents/skills/praxis` or `~/.gemini/skills/praxis` |
| GitHub Copilot | `.github/skills/praxis` or `.agents/skills/praxis` | CLI: `~/.copilot/skills/praxis` or `~/.agents/skills/praxis` |
| Cursor | `.agents/skills/praxis` or `.cursor/skills/praxis` | `~/.agents/skills/praxis` or `~/.cursor/skills/praxis` |

**Compatibility evidence:** Codex collaboration and local Python execution have existing validation records. The official formats and discovery paths for all five hosts have been reviewed. The other four hosts, newly documented discovery paths, Windows, and remote environments still need actual testing. Natural-language invocation depends on the host.

Official sources, invocation differences, and required capabilities are documented in [Host compatibility](references/agent-compatibility.md).

## Tools and plugins

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

The agent writes and reviews the case's `model.py` and `validate.py` before executing `run`. The CLI does not interpret arbitrary problems or generate models by itself. Data, cases, and outputs are excluded from Git by default; project rules come from your workspace.

See the [Execution contract](references/automation.md) for the complete interface.

</details>

<details>
<summary><strong>Plugin: export from the same maintained source</strong></summary>

Run from the repository root. The output directory must not already exist:

```bash
uv run --locked python -m scripts.build_plugin --output outputs/praxis-plugin
```

The export includes the skill, scripts, references, locked dependencies, both README versions, and license notices. Set up the environment explicitly and keep user materials in the workspace.

The skill is the cross-host entry point. The current plugin export follows OpenAI's plugin format, which does not imply universal plugin installation across hosts. Directory export is implemented; host installation and discovery remain unverified, and the plugin has not been published to the official directory.

See [Architecture](ARCHITECTURE.md) for the layout and conditions for future extensions.

</details>

## Validation and limitations

| Status | Current evidence |
|---|---|
| **Validated** | 45 local tool tests have previously passed, covering analytical answers, input protection, failed and stale evidence, PDF helpers, and self-contained plugin export; synthetic exercises and complete historical CUMCM and MCM cases are recorded |
| **Implemented guidance; field testing pending** | Context and team adaptation, solo deadline coordination, capability handoffs, and writing guidance |
| **Not yet completed** | Full cases in other agent hosts, real team competition runs, a complete three-day exercise, and host plugin installation tests |

Passing automatic checks does not establish real-world model validity. Weight-scenario shares are not objective probabilities, and execution logs are not complete AI conversations. Review task coverage against the original problem; PDF formulas, figures, and layout still need visual inspection. Large files and unsupported formats are explicitly marked for deferred auditing.

Praxis does not guarantee autonomous completion of arbitrary problems, competition awards, or submission without review.

<details>
<summary><strong>Development and exercise commands</strong></summary>

```bash
uv sync --locked --group dev
uv run --locked python -m pytest -q
uv run --locked python -m examples.decision_sensitivity_demo
uv run --locked python -m examples.structural_reasoning_demo
```

Code test records are distinguished from cross-host and real-task behavioral validation.

</details>

## Sources and licensing

Original code and documentation use the [MIT License](LICENSE). Workflow design references MathModelHub; Sobol analysis and TOPSIS use SALib and pyMCDM. See [Third-party notices](THIRD_PARTY_NOTICES.md) and [Review records](references/upstream-review.md) for reuse scope, upstream licenses, and selection decisions. Cite methods, data, and tools where they are actually used in your report.

Homepage and case graphics follow the shared [Praxis visual language](design/README.md), with maintained color, typography, and layout tokens.
