# MCM Demo: Keeping a Bath Warm With Less Water

**2016 MCM Problem A, "A Hot Bath": from mean water temperature to spatial differences, strategy comparison, and whether anyone can follow the answer.**

[中文](README.md) · [Full paper (PDF, English)](deliverables/7391856.pdf) · [Reproduction code](reproduce/) · [Back to Praxis](../../README.en.md)

[![MCM case: spatial water temperature and three water budgets](assets/overview-en.png)](deliverables/7391856.pdf)

## What the problem asks

Someone lies in a full tub of hot water and the water slowly cools. How should hot water be added so that the temperature stays near its starting value while using as little water as possible? The statement also asks about the tub's shape and size, the bather's size and movement, and a bubble-bath layer, and wants a plain-language note for the user.

The difficulty is that no temperature data are given. Heat-loss coefficients, body heat uptake and mixing all need evidence from standard correlations and published experiments, and "temperature" cannot mean only the mean, because water far from the tap can be colder.

## Results first

| Same 30-minute scenario | Added water | What it supports |
|---|---:|---|
| 3-D thermal network, best constant rate | **24.14 L** | The least water among accepted candidates; not a global optimum over all controls |
| 3-D thermal network, buffered six-stage schedule | **21.48 L** | A 0.1°C design margin; independent integration and continuous-time bounds pass on three meshes, using about 11% less water than constant flow |
| Perfectly mixed model | **16.01 L** | A proved optimum ("coast, then hold") for that ideal model |
| Energy-conservation bound | **15.41 L** | A conditional lower bound for any feasible strategy under the stated heat-loss assumptions |

Volume 164.25 L, start 40°C, limits 39–41°C, largest spatial spread 1.5°C (the ceiling and spread apply outside a 0.15 m jet zone around the inlet; the floor holds in every cell). Surface loss comes from textbook natural-convection, radiation and evaporation correlations (about 35.4 W/(m² K) for open water, 25 after the bather's cover); body exchange is anchored in the core-temperature rise of an [immersion study](https://doi.org/10.1113/EP092761); mixing has no anchor and stays a scenario. No tub experiment exists, so the numbers demonstrate a method and are not a use or safety standard.

**The water needed depends strongly on the loss coefficients; whether the search accepts a policy depends mainly on mixing.** Across 64 Sobol draws over the scenario ranges, 41 had an accepted constant-rate policy, needing 12–31 L (5th–95th percentile, median 22 L); the rest had none, mostly because of weak mixing.

## How it is solved

1. **State the decision first.** "Warm" and "uniform" become per-cell temperature limits; least water is the objective, with no arbitrary weights between unlike units.
2. **A model that can be proved.** For a well-mixed tub, coasting down to the lower limit and then holding it is proved optimal, and energy conservation bounds any strategy from below.
3. **A 3-D thermal network.** A finite-volume network handles surface and wall loss, body displacement and exchange, internal mixing, inlet and overflow, with an all-cell floor and ceiling/spread limits outside the inlet zone. Time stepping uses matrix exponentials; piecewise-constant flow is optimized by multi-start sequential quadratic programming.
4. **Ranges and scenarios.** Coefficients vary over the scenario ranges of the textbook correlations in a Sobol analysis; geometry, body, motion, bubble layer and comfort window are changed to see whether the strategy moves.
5. **Can anyone follow it?** Measure how sensitive the least-water schedule is to tap error, then price a margin: how much slack, at what cost in water.

## Evidence

- **The mean does not determine the strategy.** Waiting is optimal in the ideal mixed model; the accepted constant-flow spatial policy starts immediately. A buffered six-stage schedule saves another 11% in the baseline scenario.
- **A smaller number can fail the problem.** The 19.35 L, twelve-stage candidate reaches a 1.524°C spread on the finest mesh and is rejected. The selected 21.48 L policy produces sampled spreads of 1.400, 1.395 and 1.416°C on three meshes, with independent continuous-time bounds also passing.
- **Bounds and policies answer different questions.** The mixed optimum is proved. The spatial policies are verified candidates, without a global optimality claim. Their gaps above the energy bound are 8.7 L for constant flow and 6.1 L for the buffered schedule.
- **Checks follow the policy being recommended.** Seventeen baseline checks cover a separate RHS, energy, analytical limits, geometry and scenario replay. Scheduled flow has its own three-grid RK45 replay, restarted at each switch, and segment-specific derivative bounds between samples.
- **Numerical slack is not operational reliability.** A 0.1°C margin costs about 10% more water than the unbuffered six-stage candidate (19.50 → 21.48 L). Under the stated independent 10% segment-error model, about 74% of 200 draws stay within the limits. That supports a margin comparison, not a general manual faucet prescription; calibration and temperature feedback are still needed.
- **Failed searches retain their scope.** Weak mixing, high loss and the wide shallow tub yield no accepted constant-flow candidate. Finite search does not prove that all constant flows fail. The fine-grid constant-flow result, 24.12 L (0.11% apart), is a diagnostic rather than a convergence-order or physical-accuracy certificate.

## Two pages of the paper

<table>
<tr>
<td width="50%"><a href="deliverables/7391856.pdf"><img src="assets/report-summary.png" alt="Summary Sheet: method, results and validation" width="100%"></a></td>
<td width="50%"><a href="deliverables/7391856.pdf"><img src="assets/report-proof.png" alt="Proof of the optimal ideal-model strategy and the energy bound" width="100%"></a></td>
</tr>
<tr>
<td><strong>Summary Sheet: problem, method, result</strong><br>The decision, the numbers and the evidence level on one page.</td>
<td><strong>Argument: from proof to bound</strong><br>The optimal strategy of the ideal model and the energy bound.</td>
</tr>
</table>

**[Read the complete 24-page paper →](deliverables/7391856.pdf)** Typeset with XeLaTeX: Times-family text and equations, figures drawn by pgfplots and TikZ straight from the archived numbers, automatically numbered and cross-referenced. Twenty-three pages of solution include a one-page plain-language note for the user, followed by a one-page AI-use report. It follows the 2027 MCM submission rules: at least 12-point type, anonymous running header with page numbers, and a one-page Summary Sheet.

## Run it yourself

From the Praxis repository root:

```bash
uv sync --locked
uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py        # baseline, 18 scenarios, fine grid, 17 checks; about a minute
uv run --locked python demos/mcm-2016-a/reproduce/run_extended.py    # schedules, range analysis, execution tolerance; about 20 minutes
uv run --locked python demos/mcm-2016-a/reproduce/run_mesh_check.py   # candidate selection and three-grid continuous-time checks
```

The baseline entry point refuses an existing `reproduce/reproduced/` directory. The extension and acceptance scripts write their own results there; archived evidence and the final PDF remain untouched. The 18 reproduction checks must not be written back as the paper's 17 model checks. Rebuilding the PDF needs XeLaTeX or tectonic; see the [build notes](reproduce/README.md). The numerical reproduction needs neither a TeX engine nor an AI service.

## File map

```text
deliverables/7391856.pdf      # the only submission file (English, 24 pages)
reproduce/                    # entry points, archived numbers, paper builder
assets/                       # images for the homepage and this page
sources.json                  # provenance record
verification.json             # acceptance record
AI-use.md                     # AI-use record
```

The submission folder holds a single English PDF, as the MCM requires; `7391856` is a placeholder control number and borrows no real team identity.

## Sources, limits and license

- The official [COMAP problem](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2016/problems/2016_MCM_Problem_A.pdf) is used; no prize-winning paper or other solution to this problem was read or copied. A judges' commentary was read once during development and every change it prompted was reverted, so this is not a fully blind case.
- It is not an official answer or a prize result, and the statement is linked, not redistributed. The layout follows the [current submission rules](https://www.contest.comap.org/undergraduate/contests/mcm/instructions.php) as checked on 2026-10-07; AI involvement is disclosed truthfully, with no claim of a full chat export or independent human review. [Sources](sources.json) · [Verification](verification.json) · [AI record](AI-use.md)
- Model, code, paper and original figures are under the repository's MIT license; outside materials keep their own rights. The case tests a thermal network and a delivery process under stated conditions; it is not certification of measured accuracy.

If this case helps you, a **Star on Praxis** is welcome, as are issues with a concrete question and a reproduction.
