# A Hot Bath: Temperature and Water Use

**2016 MCM Problem A · How transport, heat loss and imperfect observations change when—and how much—hot water to add.**

[简体中文](README.md) · [Paper](paper.pdf) · [Reproduction guide](reproduce/README.md) · [All cases](../README.en.md) · [Praxis](../../README.en.md)

[Results](#results) · [Review](#review) · [Reproduction](#reproduction)

[![Spatial temperature, supply strategies and energy bounds](assets/overview-en.png)](paper.pdf)

## The modeling problem

Keep a bath close to its initial temperature while adding as little hot water as possible. The task also asks how tub geometry, the bather, movement and a bubble layer affect the answer, and requires advice for the user.

**A warm average can conceal a cold part of the bath.** With no measured temperature series supplied, the study starts with an interpretable ideal benchmark, then examines spatial transport, uncertain parameters and imperfect delivery.

## Results

The baseline uses **164.25 L at 40°C for 30 minutes**. Every cell must stay at or above 39°C. Outside a 0.15 m inlet jet zone, the ceiling is 41°C and the maximum spatial spread is 1.5°C.

| Model or policy | Added water | Interpretation |
|---|---:|---|
| Best accepted constant-flow spatial candidate | **24.14 L** | The spatial comparison baseline |
| Buffered six-stage spatial schedule | **21.48 L** | About **11%** less water; independent integration and conditional continuous-time checks pass on three meshes |
| Perfectly mixed model | **16.01 L** | A proved optimum: coast to the lower limit, then hold |
| Energy-conservation bound | **15.41 L** | A conditional lower bound for any feasible policy under the stated assumptions |

The spatial schedules are checked candidates, not global optima over all controls. Heat-loss parameters use textbook correlations and published magnitude estimates; mixing remains a scenario input. These quantities are not measured savings or operating standards.

### What changes the decision

- **Transport determines whether waiting helps.** A delay shortens delivery but may require a larger rate to protect the remote region. On the checked local branch, baseline mixing favors immediate supply and stronger mixing can favor a short delay.
- **A smaller water budget may be invalid.** The 19.35 L twelve-stage candidate reaches a 1.531°C spread on the finest mesh, exceeding 1.5°C, and is rejected. The accepted 21.48 L schedule retains planning reserves.
- **Measurement must repay its preparation cost.** With the same synthetic readings, three structures and common reserves, passive/pulse candidates command **26.09/23.63 L**. The pulse also consumes 6 L. It pays back from the **third** use if the trial is reusable, delivery bias is stable and total reset costs match. The earlier seventh-use crossover concerns different, original-structure candidates.
- **There is a limit to delaying.** A two-stage policy after a 780-second wait uses **19.26 L** and passes whole-path checks with stated integration-error assumptions. In the specified strong-mixing 96-cell network, waiting at least 790 seconds excludes every common supply up to 3 L/min. A ten-second gap remains unresolved.

## Model and argument

| Component | Purpose |
|---|---|
| Ideal benchmark | Heat balance gives a proved mixed-model optimum and an energy lower bound. |
| Spatial model | A conservative three-dimensional finite-volume network represents surface, wall and body exchange, mixing, inlet and overflow. |
| Policy comparison | Constant and staged supply are connected to sensitivity and paired delay bounds, explaining the action rather than just reporting a solver result. |
| Observation and feedback | Retain all models compatible with the readings, qualify the next action and remaining backup, and reassess when that support disappears. |
| Task extensions | Vary the mechanisms associated with geometry, the bather, movement and bubbles to test their effect on the answer. |

A compatibility set contains models that explain the readings within the declared error bounds; it is not a probability distribution. Unique parameter identification is unnecessary if the proposed action is checked over the relevant compatible set.

## Verification and scope

| Layer | Evidence and limit |
|---|---|
| Equations and implementation | Independent heat-flux and energy checks, matrix-exponential and independent-integrator comparisons; an empty-domain diffusion example has a finest observed order near 1.98. |
| Recommended schedules | Independent integration restarts at switches and bounds behavior between samples on three meshes. A valid terminal temperature does not establish whole-path safety. |
| Parameter and structural ambiguity | Common-reserve comparison covers **5,796** model–mesh objects; 54 extrema receive separate integration and energy checks. Finite-set coverage is not empirical reliability. |
| Feedback and mismatch | Two parameter cases excluded from design complete service; other mechanism changes empty the model set. Four specified mismatches have separately checked continuation, with up to **30.76 L** commanded—completion rather than further savings. |
| Limits of control | An exact certificate excludes all measurable 0–3 L/min supply on a fixed weak-mixing network. A separate three-mesh study changes the physical target region; neither proves continuum or real-bath impossibility. |

The buffered nominal schedule also fails some trials under the specified random tap-error model. No real-bath calibration has been performed. Numerical acceptance, model scope and practical implementation therefore remain distinct.

The [technical guide](reproduce/README.md) retains detailed checks and failed candidates, with supplements on [continuous parameter neighborhoods](reproduce/reference/continuous-transfer.md), [transport](reproduce/reference/transport/README.md), [timing](reproduce/reference/spatial-functional/README.md), [delay bounds](reproduce/reference/delayed-upper/README.md), [whole-horizon exclusion](reproduce/reference/whole-horizon-exclusion.md) and [region sensitivity](reproduce/reference/fixed-region-exclusion.md).

## Review

**Reference assessment: Outstanding-level competitiveness, with an adjacent F–O range.**

The paper's strength is a complete decision argument. A proved ideal benchmark leads to a spatial explanation of timing, independently checked schedules, and observation-dependent actions with a qualified backup. It offers both conditional policies and mathematical limits that adjusting flow alone cannot overcome.

Its principal limitation is the conditional transport closure. Observation and control results rely on synthetic scenarios and an offline-maintained model set. Connecting observable movement and mixing to effective transport parameters would most improve practical applicability.

An author-external AI reviewed all 26 pages and the five scientific figures. The review is non-blind and uncalibrated against award boundaries; it is not an official award or winning probability. [Review record](verification.json)

## Paper and deliverables

| Resource | Contents |
|---|---|
| <a href="paper.pdf">The complete 26-page paper</a> | English; 25 solution pages including user advice, followed by one AI-use page |
| [Submission copy](deliverables/7391856.pdf) | Byte-identical to the reading copy; 7391856 is the case's placeholder team number |
| [Technical guide](reproduce/README.md) | Calculations, verification, certificates and report builds |

The submission directory contains one PDF. Reproduction resources are provided separately. The paper uses the [shared MCM template](../../templates/mcm-paper.tex) and pinned Tectonic resources.

## Reproduction

Run the baseline from the Praxis repository root:

```bash
uv sync --locked
uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py
```

It writes to `demos/mcm-2016-a/reproduce/reproduced/` and refuses an existing directory. The **18 reproduction checks** include one water comparison beyond the paper's 17 baseline checks; this entry does not rerun every subsequent study.

Use the [specialist reproduction index](reproduce/README.md#复现索引) to choose an archive audit, independent replay or new solve. Long optimizations are optional. Mathematical reproduction requires neither a typesetting engine nor an AI service.

## File structure

```text
paper.pdf                     Public reading copy
deliverables/7391856.pdf       Single-file submission copy
reproduce/                    Calculations, checks, evidence and report builds
assets/                       Presentation images
sources.json                  Provenance
verification.json             Review and acceptance record
AI-use.md                     AI-use record
```

## Sources and license

The task is [COMAP's official 2016 Problem A](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2016/problems/2016_MCM_Problem_A.pdf). After an earlier final version was sealed, the project studied same-problem papers and judges' commentary. This page presents the resulting development case; [provenance](sources.json) and [AI-use records](AI-use.md) retain the actual process.

Original models, code, manuscript and figures use the repository's [MIT License](../../LICENSE). External statements and publications retain their owners' rights and are not redistributed with the case.
