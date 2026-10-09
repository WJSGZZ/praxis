# Paying for the bottleneck

**2017 MCM B · Merge After Toll**　[简体中文](README.md) · [Full report](paper/paper.pdf) · [First draft](baseline/paper.pdf) · [Results](reference/accepted.json)

More tollbooths can increase service capacity and still make vehicles wait longer. This study connects payment compatibility, receiving lanes, departure geometry and finite downstream occupancy to explain when that happens.

The archive records **one autonomous AI development study**. Its purpose is research; the two flagship contest demonstrations retain their separate roles. Iterative development is not presented as a blind capability evaluation.

The final manuscript now uses the same `praxis-mcm-v1` layout as the original MCM flagship. The scientific text and numerical results are unchanged; the historical first draft retains its original layout. The [layout revision](reviews/layout-revision.json) links the earlier semantic review to this typesetting update.

## Findings

| Result | Conditions and evidence |
|---|---|
| Pooled service capacity can be misleading | The initial layout has a 5,400-vehicle/hour aggregate bound but sustains only 3,000 arrivals/hour at the nominal payment composition. A compatible-flow network gives the conditional threshold. |
| A nominal eight-booth design reaches 4,000/hour | Enumeration covers 441 clustered layouts and compares them with 6,750 unrestricted matrices. The selected staffed/exact/ETC count is 4/3/1; distinct maximum-flow and LP checks support the result. |
| Payment uncertainty can force expansion | With 12/6/2-second service means, at least 11 booths are necessary for 3,600/hour across the three mixtures, and a feasible layout is supplied. Under 15/10/3-second means, 14 is only a necessary count; no fourteen-booth design is verified. |
| Limited occupancy can reverse the preferred design | At 16 downstream slots per group, nominal heavy-traffic waiting averages 21.9 s for the robust eight-booth design and 54.3 s for expansion. At 64 slots, expansion falls to 8.3 s. |
| Geometry needs an operating rule | The nominal departure zone combines 91.44 m of recovery and a 230 m taper. Entry metering is equivalent to the discharge recurrence under a common taper speed and travel time. The spacing argument is conditional and does not predict crashes. |

The 17-page English report contains a one-page summary, the solution, four figures, a one-page authority letter, references and an AI-use report. It follows the historical problem's requested structure; it is not certification against present contest rules or engineering standards.

## What changed during the study

The first screen exposed payment-incompatible idle capacity. A minimum-cut certificate replaced the pooled recommendation. Historical FHWA guidance then prompted a separate recovery section, changing area, cost and traversal time. Finite-token queues challenged the apparent advantage of expansion, and an analytic occupancy bound explained the reversal.

An alternative routing objective minimized the largest resource utilization. Its waiting outcomes were mixed, so it was retained as a rejected candidate rather than described as a universal improvement. A separate agent role read the complete English report and identified ambiguous comparisons and missing local conditions; the final summary, tables and authority letter were synchronized.

The nine-page first draft was assembled while candidate research was already underway and uses earlier geometry assumptions. It is an authentic draft, **not a preregistered baseline arm**. See the [study record](reviews/study.md) for chronology, failures, exposure and review scope.

## Reproduce the archive

Run from the Praxis repository root. Choose a fresh output directory; archived files are not replaced.

```bash
uv run --locked python research/merge-after-toll/reproduce.py --output .session/merge-replay
```

The command recomputes the selected study, runs the validator and reviewer-authored audit, compares numerical reference values and verifies archive hashes. Main computation took roughly 3 seconds on the recorded machine. The audit includes 256 independent LP comparisons, hand-solvable queues, finite/unlimited equivalence, analytic occupancy witnesses and entry-metering checks.

```bash
uv run --locked python research/merge-after-toll/reproduce.py --candidate --output .session/merge-candidate
uv run --locked python research/merge-after-toll/reproduce.py --baseline --output .session/merge-baseline
uv run --locked python research/merge-after-toll/paper/build_report.py \
  --results research/merge-after-toll/reference/accepted.json --output .session/merge-paper
```

The last command generates editable LaTeX from the frozen results. To compile it, use Tectonic 0.17.0 through `uv run --locked python -m scripts.paper_template research/merge-after-toll/paper/paper.tex --contest mcm --compile --output-directory outputs/toll-build-001` from the repository root. This pins the complete TeX bundle and records source/PDF hashes; review every page before freezing a new deliverable.

## Read the evidence

[paper/](paper/) holds the final report and generator; [baseline/](baseline/) preserves the earlier manuscript and source. The current model and rejected route are in [code/](code/). Numerical outputs and [reviewer-authored audit results](reference/independent-audit.json) are in [reference/](reference/); [reviews/](reviews/) records reading feedback and assessment scope. The[manifest](manifest.json) binds source fingerprints, environment, inputs, timing, exposure, receipts and file hashes. Internal diagnostics do not establish an award tier.

## Sources, rights and limits

The source problem is[COMAP's official 2017 statement](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2017/problems/2017_MCM_Problem_B.pdf), linked rather than redistributed. General sources are FHWA's[calibration guidance](https://ops.fhwa.dot.gov/trafficanalysistools/tat_vol3/sect5.htm),[historical departure-zone guidance](https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter642.htm) and [toll-lane layout guidance](https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter224.htm). These are not a complete set of current engineering requirements.

An [exposure erratum dated 2026-10-09](reviews/exposure-correction.json) corrects an omission: the project had already read same-problem paper 56731 before this study. The episode reported no new solution reading, but that does not erase prior project exposure. Full historical context for each role cannot be reconstructed; pretraining exposure remains unknown. Frozen manuscripts and numerical outputs are preserved. This is development research with known prior exposure. Review was performed by another role of the same model family with author code visible. No human modeled or verified this case. Product-development delegation is recorded separately, and missing raw model transcripts are not reconstructed from summaries.

Original code, text and report are provided under the repository's MIT license. External statements and references retain their owners' rights. This archive is excluded from the default plugin bundle and routine skill context. Field calibration, physical storage mapping, braking, heavy vehicles and driver compliance remain open modeling limits.
