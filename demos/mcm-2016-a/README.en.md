# MCM Case: A Hot Bath

**When resolving space changes the water-saving strategy.**

[简体中文](README.md) · [Read the report](deliverables/7391856.pdf) · [Run the evidence](reproduce/) · [Back to Praxis](../../README.en.md)

[![Spatial temperatures, a proved benchmark, and a conditional energy bound](assets/overview-en.png)](deliverables/7391856.pdf)

For a perfectly mixed bath, waiting before replenishing is provably optimal. In the spatial model the best constant trickle starts at once, and a schedule that withholds hot water at both ends needs about 18% less. Heat-loss and body coefficients come from standard correlations and a published immersion study, with ranges, so the case also shows how much the answer depends on them.

| Evidence under the same 30-minute conditions | Added water | Interpretation |
|---|---:|---|
| Spatial network, best constant rate | **24.14 L** | Best accepted constant-rate candidate in the stated search |
| Spatial network, 12-segment schedule | **19.77 L** | Local optimum from constrained optimization; no flow in the first 2.5 and last 10 minutes |
| Ideal well-mixed control | **16.01 L** | Proved optimum of the idealized model |
| Conservative energy argument | **15.41 L** | Conditional lower bound for feasible spatial policies |

The scenario contains 164.25 L of water, initially at 40°C, with cell-average limits of 39–41°C and a spread limit of 1.5°C. Surface loss is derived from natural-convection, radiation and evaporation relations (35.6 W/(m² K) for open water, 25 with the bather covering part of the surface); body exchange is anchored to the core-temperature rise in an [immersion study](https://doi.org/10.1113/EP092761); the mixing coefficient has no anchor and stays a scenario. No bathtub experiment was performed, and the example is not a universal bathing or safety prescription.

**The answer depends strongly on the loss coefficients.** Across 64 Sobol draws over the stated ranges, 37 have an accepted constant-rate policy, needing 12–31 L (5th–95th percentile, median 21 L); the rest have none.

## What makes the result inspectable

A three-dimensional conservative thermal network includes surface and shell losses, body displacement and exchange, mixing, and an explicit inlet-to-overflow stream. Constraints apply to every cell. The paper distinguishes a control theorem, feasible spatial policies, and an energy lower bound instead of calling all of them “optimal”; the schedule narrows the gap to the bound from 8.7 L to 4.4 L, and the rest stays open.

The **17 recorded checks** include independent heat-flow arithmetic and RK45 integration, a constructed analytic cooling limit, geometric input checks, and scenario replays. A derivative envelope supplements sampling for the selected baseline; scenario checks remain sampled checks. The optimized schedule has two further checks. A finer grid changes the constant-rate result by 0.11%, but two meshes remain a resolution diagnostic, not a convergence proof. Six scenarios have no accepted candidate and are kept without claiming mathematical infeasibility. Two choices were revised in the open: a 40.5°C upper limit had no accepted policy on the finer mesh and became 41°C, and the first, lower loss coefficients were replaced after the literature derivation.

## Read the complete solution

<table>
<tr>
<td width="50%"><a href="deliverables/7391856.pdf"><img src="assets/report-summary.png" alt="Summary Sheet: the model, result and evidence" width="100%"></a></td>
<td width="50%"><a href="deliverables/7391856.pdf"><img src="assets/report-proof.png" alt="Optimal ideal control and the spatial energy bound" width="100%"></a></td>
</tr>
</table>

[Open the 20-page English report →](deliverables/7391856.pdf)

The PDF has 19 solution pages, including scenario definitions, followed by one AI-use page. It contains the required one-page explanation for a non-technical bather. Sources are cited where used; development status notes stay outside the paper.

`deliverables/` contains **one PDF only**, matching the MCM submission structure. `7391856` is an example control number, not an actual team identity. Reproduction sources, this guide and verification records are development resources outside the submission directory; there is no CUMCM-style support ZIP.

## Recalculate the case

From the Praxis repository root:

```bash
uv sync --locked
uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py
```

The script recalculates the baseline, 17 variations and a finer grid. It runs the 17 model checks and adds one comparison with the water amount archived for the report. A run typically takes about a minute, depending on hardware. Results go to `reproduce/reproduced/`; an existing directory is preserved by refusing to overwrite it. The extra reproduction check does not change the report’s model-check count.

An optional second entry point runs the schedule optimization and the literature-range analysis (about 4–5 minutes):

```bash
uv run --locked python demos/mcm-2016-a/reproduce/run_extended.py
```

It re-optimizes 3-, 6- and 12-segment schedules, replays the best one with an independent RK45 integrator (two checks), and reruns the constant-rate search at 64 Sobol points. Results go to the same `reproduced/` directory.

[Report-building instructions](reproduce/README.md) document the separate PDF tool and font requirements. Mathematical reproduction requires no AI service or report-rendering library.

## Attribution and limits

The task is [COMAP’s 2016 MCM Problem A](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2016/problems/2016_MCM_Problem_A.pdf). Kathleen M. Shannon’s [judges’ commentary](https://faculty.winthrop.edu/abernathyz/MathComps/2016_MCM_A-Com.pdf) informed the emphasis on explanation and usable advice. This is an original development case, not an official solution or an award-winning entry. Source documents are linked, not redistributed.

The historical problem is formatted using the [current 2027 instructions](https://www.contest.comap.org/undergraduate/contests/mcm/instructions.php), checked on 7 October 2026: English text of at least 12pt, anonymous headers, page numbering, a single-page summary and the problem’s single-page user explanation. Times New Roman is a typesetting choice. AI participation is disclosed; a complete interaction export and independent human review are not claimed. [Sources](sources.json) · [Verification](verification.json) · [AI record](AI-use.md)

Original code, report text and figures use the repository’s MIT license. External publications and fonts retain their own rights. Numerical consistency of this assumed thermal network does not establish experimental accuracy.
