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
| 3-D thermal network, 12-segment schedule | **19.77 L** | A constrained local optimum; no added water in the first 2.5 and last 10 minutes |
| Perfectly mixed model | **16.01 L** | A proved optimum ("coast, then hold") for that ideal model |
| Energy-conservation bound | **15.41 L** | A conditional lower bound for any feasible strategy under the stated heat-loss assumptions |

Volume 164.25 L, start 40°C, limits 39–41°C, largest spatial spread 1.5°C. Surface loss comes from natural-convection, radiation and evaporation correlations (about 35.6 W/(m² K) for open water, 25 after the bather's cover); body exchange is anchored in the core-temperature rise of an [immersion study](https://doi.org/10.1113/EP092761); mixing has no anchor and stays a scenario. No tub experiment exists, so the numbers demonstrate a method and are not a use or safety standard.

**The answer depends strongly on the loss coefficients.** Across 64 Sobol draws over literature ranges, 37 had an accepted constant-rate policy, needing 12–31 L (5th–95th percentile, median 21 L); the rest had none.

## How it is solved

1. **State the decision first.** "Warm" and "uniform" become per-cell temperature limits; least water is the objective, with no arbitrary weights between unlike units.
2. **A model that can be proved.** For a well-mixed tub, coasting down to the lower limit and then holding it is proved optimal, and energy conservation bounds any strategy from below.
3. **A 3-D thermal network.** A finite-volume network handles surface and wall loss, body displacement and exchange, internal mixing, inlet and overflow, with limits on every cell. Time stepping uses matrix exponentials; piecewise-constant flow is optimized by multi-start sequential quadratic programming.
4. **Ranges and scenarios.** Coefficients vary over literature ranges in a Sobol analysis; geometry, body, motion, bubble layer and comfort window are changed to see whether the strategy moves.
5. **Can anyone follow it?** Measure how sensitive the least-water schedule is to tap error, then price a margin: how much slack, at what cost in water.

## Evidence

- **Spatial differences change the strategy.** The ideal model says wait; with transport a constant trickle should start immediately, and a time-varying schedule saves about 18% more. A mean can hide a cold corner.
- **Claims carry their own evidence level.** The ideal model has a proof; the spatial model has feasible constant and scheduled policies; energy conservation gives a conditional bound. The constant rate sits 8.7 L above the bound and the schedule narrows that to 4.4 L; the rest stays open.
- **Verification is more than rerunning.** An independent heat-flow right-hand side integrated with RK45 is compared with the matrix-exponential result; energy accounting, analytic limits, geometry arithmetic and scenario replays are checked too. Seventeen checks are not seventeen algorithms; the schedule adds two more. A derivative envelope covers the times between samples for the baseline.
- **The least-water schedule has no tolerance.** It sits right on the spread limit, so a tap that runs 10% hot or cold crosses it by about 0.08–0.13°C; with independent 10% errors on each segment, none of 200 draws stays within the limits; one segment opened 20% too far does far more harm than one opened 20% too little. A 0.1°C margin costs 12.5% more water (19.84 → 22.32 L), and then 53% of random draws stay within limits; a 0.2°C margin leaves no feasible schedule under the 1.5°C spread limit.
- **Failures and corrections stay visible.** Six scenarios, including weak mixing and a tight window, have no accepted candidate; the first 40.5°C upper limit had no solution on the finer mesh and was raised to 41°C; the first, too-low loss coefficients were re-derived from the literature; the fine-grid result (24.12 L, 0.11% apart) is a diagnostic, not a convergence proof.

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

**[Read the complete 23-page paper →](deliverables/7391856.pdf)** Typeset with XeLaTeX: Times-family text and equations, figures drawn by pgfplots and TikZ straight from the archived numbers, automatically numbered and cross-referenced. Twenty-one pages of solution include a one-page plain-language note for the user, followed by a one-page AI-use report. It follows the 2027 MCM submission rules: at least 12-point type, anonymous running header with page numbers, and a one-page Summary Sheet.

## Run it yourself

From the Praxis repository root:

```bash
uv sync --locked
uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py        # baseline, 18 scenarios, fine grid, 17 checks; about a minute
uv run --locked python demos/mcm-2016-a/reproduce/run_extended.py    # schedules, literature ranges, execution tolerance; about 4–5 minutes
```

Output goes to `reproduce/reproduced/`; existing output is never overwritten, and the archived evidence and final PDF are untouched. The 18 reproduction checks must not be written back as the paper's 17 model checks. Rebuilding the PDF needs XeLaTeX or tectonic; see the [build notes](reproduce/README.md). The numerical reproduction needs neither a TeX engine nor an AI service.

## File map

```text
deliverables/7391856.pdf      # the only submission file (English, 23 pages)
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
