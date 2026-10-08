# Study record

## Scope and chronology

One delegated development episode selected the historical 2017 MCM B problem. The research task record started at 2026-10-08T16:20:35Z. The archive manifest records the actual freeze time and numerical run durations. Per-case model token consumption is unavailable; shared-account percentages and private scheduling constraints are not attributed to this case or published.

The initial numerical baseline ran at 16:24Z. Layout improvement began before the nine-page baseline manuscript was fully assembled. The first complete draft therefore demonstrates a recoverable written baseline, but does not constitute a preregistered control arm. Subsequent changes formed one development episode, with retained numerical attempts; they were not independent restarts from which only the best outcome was reported.

The original geometric model did not distinguish recovery from taper and used narrower booth spacing. Primary-source reading led to a 91.44 m recovery zone, 4.5 m booth pitch, payment clustering and finite occupancy. Those changes genuinely required new numerical runs. The frozen earlier draft and its original code retain their assumptions; its numbers should not be presented as if calculated with the final configuration.

The last accepted pipeline run began at 2026-10-08T17:07:17Z. The final report uses that run. Language edits and entry-metering interpretation did not change its trajectories. Local progress and contribution events were appended separately; the evidence chain remained usable afterward. The available source fingerprints, dependency hashes and actual step times are in the manifest. Full pipeline logs remain in the private workbench; this public archive contains derived summaries and their original receipt hashes, not fabricated raw logs.

## Research decisions

- **I1 — compatibility:** aggregate booth capacity is an upper bound, not a feasible arrival rate. The payment-to-group network and minimum-cut proof replace that recommendation. The same root cause affects throughput, the heavy-demand interpretation and booth selection.
- **I2 — recovery and grouping:** archived FHWA guidance prompted separate recovery and taper dimensions and an ETC-left clustered layout family. An unrestricted matrix comparison checks capacity loss for the declared scenarios; it does not prove all possible layouts equivalent.
- **I3 — finite holding:** the unlimited-holding experiment initially favored expansion. Finite occupancy reverses that preference at K=16. An independently derived occupancy cut plus explicit flow witness explains the necessary holding resource; satisfying the bound is not sufficient for a stable stochastic queue.
- **I4 — proxy objective:** minimax resource utilization routing is a valid numerical candidate, but mixed waiting outcomes reject a uniform improvement claim. The candidate's inputs and outputs remain in the archive.
- **I5 — control interpretation:** common taper travel time makes entrance metering algebraically equivalent to the modeled discharge recurrence. An actual finite-queue trace checks the equivalence without removing entrance waiting from occupancy. A simple passenger-car spacing condition is limited to the declared kinematics.
- **I6 — English presentation:** external-role reading found ambiguous table labels, rounded occupancy values hiding a ceiling, missing local service conditions and an overly broad description of larger holding. These were corrected throughout the summary, discussion and authority letter. A final symbol check distinguishes recovery-ready time from taper-end arrival.

Land cost was subsequently added as explicit 0/200/1000 USD/m² scenarios. Independent area and equipment arithmetic checks the new table; missing local quotes remain a limit, not invented evidence. This required one more candidate/accepted run pair.

## Failures and rejected objections

A natural candidate run at 16:25Z failed when NumPy integer counts could not be serialized to JSON. The model was corrected to emit native integers and rerun; no old success substituted for the failed attempt. Its receipt hash and failure status are retained in the manifest. The original traceback and source snapshot are preserved locally and are not redistributed as private machine paths.

The minimax routing candidate passes mathematical and accounting checks. It is rejected for the claimed performance objective, not mislabeled as a solver failure. For example, its cash-heavy nominal-design waiting can worsen despite a smaller maximum resource load.

An independent role initially expected zero waiting in a three-job finite queue with nonbinding occupancy. Hand calculation showed one second of mean booth waiting. The reviewer corrected that expectation rather than changing correct model output. Similarly, a finite-window departure rate above 3,000/hour does not refute the baseline's 3,000/hour sustainable arrival threshold: the composition of completed traffic can differ from arriving traffic. Review feedback must be checked against the claimed quantity.

A separate controlled plugin experiment tested successful run→injected timeout→rejection of old evidence→explicit rerun recovery, and discovered the same-second run-order defect. That experiment is not this toll case, and is not claimed as a real host interruption. The defect was repaired in the plugin before the final toll run. No raw transcript or uninterrupted background execution is inferred from these receipts.

## What was independently checked

The author-side validator checks selected-layout thresholds using NetworkX maximum flow, routing conservation, geometry, exhaustive booth-count lower bounds and simulation accounting. A separate reviewer-authored audit checks 256 cut/LP pairs, symbolic quintic extrema, hand-solvable queues, 48 large-occupancy comparisons, 48 bounded-queue cases, analytic occupancy bounds with feasible witnesses, 128 randomized metering recurrences and one actual finite-event trace. Five additional checks reconstruct road, equipment and land opportunity-cost scenarios from dimensions and counts. It also rejects a deliberately altered occupancy-bound fixture.

These are distinct computations by another agent role of the same model family with author code visible. They do not establish field calibration, empirical safety, an isolated blind test, overall plugin A/B benefit or award calibration.

All 17 final pages were rendered and visually checked by the executing agent, with full-size checks of the summary, geometry/control equations, occupancy bounds and authority letter. Both the desktop compiler and XeLaTeX succeeded; the final compile log had no overfull boxes or unresolved references. The first nine-page draft was also rendered and inspected as historical evidence. Its earlier limitations and imperfect typography were preserved rather than silently revised into a better baseline.

## Assessment and learning

The[final structured review](final-review.json) records seven diagnostic dimensions, six scoped claims and the actual reader's checks. Uncomputed or visually unreviewed items remain unreviewed for that reader, even where another role performed the work. The[user view](user-assessment.json) preserves their association with the review and explicitly abstains from an award tier: the 2017 award registry was not verified and there is no held-out award calibration.

A transferable lesson was saved locally: when demand types cannot substitute and transport consumes a holding resource, examine compatible cuts and traversal occupancy before optimizing aggregate capacity. A post-study retrieval found that lesson. Retrieval and storage alone are not evidence of benefit on a new task. The general routing/verification guidance was updated narrowly; no new mandatory phase, database or domain-specific default tool was introduced.

## Participation, sources and rights

No human supplied a case-specific assumption, route, correction or mathematical verification during this episode. The user delegated product development and research; that role is recorded separately from case execution. Numerical and English reviews were AI roles. Available contribution events are retrospective summaries with evidence, not complete interaction transcripts.

Only the official problem statement and general FHWA sources were read for this case. No same-problem submitted solution or judges' commentary was consulted; possible pretraining exposure is unknown. The official statement was stored privately for reading and is linked publicly, not redistributed. No purchased source materials, user prompts or local machine paths are included in this archive.

The remaining scientific limitation is clear: synthetic scenarios do not identify real service, compliance, lane-change or crash mechanisms. A calibrated spatial queue and traffic model may change the recommended design. The current archive establishes conditional capacity, occupancy and operating-rule results, and preserves the checks needed to challenge them.
