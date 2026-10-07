# MCM Case: A Hot Bath

**When resolving space changes the water-saving strategy.**

[简体中文](README.md) · [Read the report](deliverables/7391856.pdf) · [Run the evidence](reproduce/) · [Back to Praxis](../../README.en.md)

[![Spatial temperatures, a proved benchmark, and a conditional energy bound](assets/overview-en.png)](deliverables/7391856.pdf)

For a perfectly mixed bath, waiting before replenishing is provably optimal. In this spatial scenario, an early, small trickle ranks ahead of the tested delayed starts. The case uses that disagreement to explain why the added model complexity matters.

| Evidence under the same 30-minute conditions | Added water | Interpretation |
|---|---:|---|
| Selected spatial-network policy | **10.48 L** | Best accepted candidate in the stated search |
| Ideal well-mixed control | **6.53 L** | Proved optimum of the idealized model |
| Conservative energy argument | **5.98 L** | Conditional lower bound for feasible spatial policies |

The scenario contains 164.25 L of water, initially at 40°C, with cell-average limits of 39–40.5°C and a spread limit of 1.5°C. Heat loss, mixing and body inputs are declared assumptions. No bathtub experiment was performed, and the example is not a universal bathing or safety prescription.

## What makes the result inspectable

A three-dimensional conservative thermal network includes surface and shell losses, body displacement and exchange, mixing, and an explicit inlet-to-overflow stream. Constraints apply to every cell. The paper distinguishes a control theorem, a feasible spatial candidate, and an energy lower bound instead of calling all three “optimal.”

The **17 recorded checks** include independent heat-flow arithmetic and RK45 integration, a constructed analytic cooling limit, geometric input checks, and scenario replays. A derivative envelope supplements sampling for the selected baseline; scenario checks remain sampled checks. A finer grid uses approximately 10.47 L but increases the local spread, so two meshes are presented as a resolution diagnostic rather than a convergence proof. Searches with no accepted candidate are retained without claiming mathematical infeasibility.

## Read the complete solution

<table>
<tr>
<td width="50%"><a href="deliverables/7391856.pdf"><img src="assets/report-summary.png" alt="Summary Sheet: the model, result and evidence" width="100%"></a></td>
<td width="50%"><a href="deliverables/7391856.pdf"><img src="assets/report-proof.png" alt="Optimal ideal control and the spatial energy bound" width="100%"></a></td>
</tr>
</table>

[Open the 19-page English report →](deliverables/7391856.pdf)

The PDF has 18 solution pages, including scenario definitions, followed by one AI-use page. It contains the required one-page explanation for a non-technical bather. Sources are cited where used; development status notes stay outside the paper.

`deliverables/` contains **one PDF only**, matching the MCM submission structure. `7391856` is an example control number, not an actual team identity. Reproduction sources, this guide and verification records are development resources outside the submission directory; there is no CUMCM-style support ZIP.

## Recalculate the case

From the Praxis repository root:

```bash
uv sync --locked
uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py
```

The script recalculates the baseline, 16 variations and a finer grid. It runs the 17 model checks and adds one comparison with the water amount archived for the report. A run typically takes about a minute, depending on hardware. Results go to `reproduce/reproduced/`; an existing directory is preserved by refusing to overwrite it. The extra reproduction check does not change the report’s model-check count.

[Report-building instructions](reproduce/README.md) document the separate PDF tool and font requirements. Mathematical reproduction requires no AI service or report-rendering library.

## Attribution and limits

The task is [COMAP’s 2016 MCM Problem A](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2016/problems/2016_MCM_Problem_A.pdf). Kathleen M. Shannon’s [judges’ commentary](https://faculty.winthrop.edu/abernathyz/MathComps/2016_MCM_A-Com.pdf) informed the emphasis on explanation and usable advice. This is an original development case, not an official solution or an award-winning entry. Source documents are linked, not redistributed.

The historical problem is formatted using the [current 2027 instructions](https://www.contest.comap.org/undergraduate/contests/mcm/instructions.php), checked on 7 October 2026: English text of at least 12pt, anonymous headers, page numbering, a single-page summary and the problem’s single-page user explanation. Times New Roman is a typesetting choice. AI participation is disclosed; a complete interaction export and independent human review are not claimed. [Sources](sources.json) · [Verification](verification.json) · [AI record](AI-use.md)

Original code, report text and figures use the repository’s MIT license. External publications and fonts retain their own rights. Numerical consistency of this assumed thermal network does not establish experimental accuracy.
