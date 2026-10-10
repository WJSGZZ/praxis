# Toll-Plaza Layout and Downstream Queues

**2017 MCM B · Merge After Toll: when do extra booths improve the journey, and when does downstream space become the constraint?**

[简体中文](README.md) · [Complete report](paper/paper.pdf) · [Results](reference/accepted.json) · [All cases](../../demos/README.en.md) · [Praxis](../../README.en.md)

[Results](#results) · [Review](#review) · [Reproduction](#reproduction)

## The decision problem

More tollbooths raise service capacity, but vehicles must still accelerate, merge and fit into the departure area. Payment restrictions create another bottleneck: a cash driver cannot use an idle electronic booth.

The study connects these constraints to layout choice. Its central question is whether added capacity actually reduces delay once the complete journey is modeled.

## Results

These findings apply to the declared scenarios, rather than measurements of a particular toll plaza.

| Finding | Conditions and evidence |
|---|---|
| Aggregate capacity overstates usable capacity | The initial layout has a **5,400-vehicle/hour** pooled bound but sustains only **3,000/hour** at the nominal payment mix. A compatible-flow network establishes the threshold. |
| An eight-booth design reaches **4,000/hour** | The selected staffed/exact/ETC count is **4/3/1**, from 441 clustered layouts, compared with 6,750 unrestricted matrices; distinct maximum-flow and LP checks agree. |
| Payment uncertainty can require expansion | With 12/6/2-second service means, **11 booths** are necessary and a feasible layout covers 3,600/hour across three mixtures. Under 15/10/3-second means, **14 is only a necessary count**; no corresponding layout has been verified. |
| Limited space reverses the preferred design | At 16 downstream slots per group, nominal heavy-traffic mean waiting is **21.9 s** for the robust eight-booth design and **54.3 s** for expansion. With 64 slots, expansion falls to **8.3 s**. |
| Geometry needs an operating rule | The nominal departure zone contains **91.44 m** of parallel recovery and a **230 m** taper. Entry metering matches the discharge recurrence under common speed and travel time; the spacing argument does not predict crashes. |

## Modeling and verification

A flow network connects payment types to receiving groups. Minimum-cut conditions replace a pooled capacity estimate that counted incompatible idle service. A separate recovery zone and taper determine footprint, cost and traversal time.

Finite-occupancy queues test the apparent benefit of expansion. Little's law supplies a necessary occupancy bound, and an analytical flow witness attains it; the bound is not a sufficient physical storage design. An alternative routing objective minimizes peak utilization but produces mixed waiting outcomes. It remains a rejected candidate rather than a claimed minimum-delay policy.

The evidence includes 256 independent LP comparisons, hand-solvable queues, finite/unlimited occupancy comparisons, analytical occupancy witnesses and entry-metering checks. The [original audit](reference/independent-audit.json) and [strategy-input revision](reviews/routing-audit-revision.json) distinguish historical checks from a later correction. Two archives pass 21 revised checks each; numerical references and failed candidates are retained.

## Review

**The paper offers a coherent explanation of why payment compatibility and downstream space can matter more than booth count alone.**

Its strongest feature is the connection between mechanisms: capacity constrains layout, geometry determines traversal and occupancy, and finite queues change the recommendation. The summary, result tables and authority letter preserve the same facts and conditions. Reversal scenarios and an unsuccessful routing alternative make the argument inspectable.

The principal limitation is field calibration. Service inputs, driver behavior and the mapping from occupancy slots to physical space remain unmeasured; braking, heavy vehicles and several safety factors fall outside the spacing argument. The result supports conditional decision analysis rather than immediate construction.

An author-external AI reviewed the full source and its agreement with recorded results. Numerical audits and PDF layout checks have separate records. The existing assessment abstains from an award tier because reliable edition-specific boundaries are unavailable. [Full review](reviews/final-review.json) · [Assessment scope](reviews/user-assessment.json)

## Report and materials

| Resource | Contents |
|---|---|
| [Complete 17-page English report](paper/paper.pdf) | Summary, solution, four figures, authority letter, references and AI-use disclosure |
| [Manuscript and generator](paper/) | Tables, figures and LaTeX generated from frozen results |
| [Reference results](reference/) | Accepted layout, rejected routing, original baseline and checks |
| [Study record](reviews/study.md) | Actual chronology, versions and failures |

The current report uses the shared MCM template; one page is the AI-use disclosure. The historical first draft is preserved. The archive follows the historical problem's structure without certifying present contest compliance or engineering standards.

## Reproduction

Run from the Praxis repository root with a fresh output directory:

```bash
uv sync --locked
uv run --locked python research/merge-after-toll/reproduce.py --output .session/merge-replay
```

This recomputes the selected study, runs the validator and reviewer-authored audit, compares reference values and checks archive hashes. Existing reports and reference results are not replaced.

<details>
<summary>Candidate, baseline and report builds</summary>

```bash
uv run --locked python research/merge-after-toll/reproduce.py --candidate --output .session/merge-candidate
uv run --locked python research/merge-after-toll/reproduce.py --baseline --output .session/merge-baseline
uv run --locked python research/merge-after-toll/paper/build_report.py \
  --results research/merge-after-toll/reference/accepted.json --output .session/merge-paper
uv run --locked python -m scripts.paper_template research/merge-after-toll/paper/paper.tex \
  --contest mcm --compile --output-directory outputs/toll-build-001
```

The third command generates editable source from the frozen results; the fourth compiles the archived source with pinned Tectonic resources. Both require fresh output destinations. Build receipts bind source and PDF; inspect every page before adopting a new report.

</details>

## File structure

```text
paper/          Final report, LaTeX and generator
baseline/       Historical first draft and its calculation source
code/           Current model, independent validator and rejected route
reference/      Frozen results and numerical audits
reviews/        Full-paper review, chronology and revision scope
manifest.json   Source, environment, timing, provenance and hashes
reproduce.py    Reproduction entry point
```

## Sources and license

The task is [COMAP's official 2017 Problem B](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2017/problems/2017_MCM_Problem_B.pdf). General references include FHWA's [calibration guidance](https://ops.fhwa.dot.gov/trafficanalysistools/tat_vol3/sect5.htm), [historical departure-zone guidance](https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter642.htm) and [toll-lane layout guidance](https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter224.htm). These are not a complete set of current engineering requirements.

This is AI development research with known prior exposure to same-problem material, rather than a blind evaluation. Review scopes are attributed separately. Original code, report and documentation use the repository's [MIT License](../../LICENSE); external statements and purchased material are not redistributed. The archive is excluded from the default plugin bundle.

<details>
<summary>Version and research provenance</summary>

The nine-page first draft was assembled while candidate research was underway, not as a preregistered baseline arm. The [study record](reviews/study.md) preserves chronology and failures. An [exposure erratum](reviews/exposure-correction.json) records the project's prior reading of same-problem paper 56731. Missing context and raw transcripts are not reconstructed. No end-user modeling or verification is recorded; product-development contributions are separate.

The [layout](reviews/layout-revision.json) and [frontmatter](reviews/frontmatter-revision.json) revisions bind their actual artifacts without reattributing an earlier mathematical review to later typesetting. `manifest.json` retains archive identities and the relationship to this documentation revision.

</details>
