# A continuous neighborhood for two fixed bath schedules

This supplement provides the detailed derivation and archive for Section 11.3 of the current [paper](../../deliverables/7391856.pdf). Its award assessment remains bound to the complete manuscript. The calculation certifies two **realized, fixed command sequences** over narrow four-dimensional parameter boxes. It does not certify every feedback decision, changing parameters, a real bath, or a global water optimum.

## Conditions and results

The two command sequences come from the previously completed surface/deep off-grid cases. Geometry, route, fixed 34°C contact node, uniform 40°C initial water, 50°C inlet, 22°C air and 30-minute duration are unchanged. The four parameters are constant throughout each service. The boxes are:

| Parameter | Center | Certified halfwidth |
|---|---:|---:|
| Effective diffusivity D (m²/s) | 0.001025 | 0.00000625 |
| Surface loss h_s (W/(m² K)) | 24.375 | 0.15625 |
| Body exchange h_b (W/(m² K)) | 26.25 | 0.3125 |
| Delivered/commanded flow α | 1.0125 | 0.003125 |

These are mathematical neighborhoods, not empirically established measurement tolerances. Each box covers all combinations of its four intervals, conditional on the stated numerical accuracy assumptions. On the 8×4×3, 12×6×4 and 16×8×6 networks, the combined outward bounds are a minimum ≥39.0759°C, an outside-inlet maximum ≤40.7769°C and an outside-inlet spread ≤1.1746°C. Thus the physical 39–41°C/1.5°C requirements pass. The stricter common design reserves **do not all pass**.

The commanded volumes remain 22.593389 and 22.797395 L. Delivered volume is α times the corresponding command sum; it is a range over each box. No control search or observation sequence was rerun to obtain these certificates.

## Exact remainder, not an unchecked linear approximation

Within each constant-command stage, write the dynamic temperatures (including the fixed contact state, excluding the augmented constant coordinate) as

$$U'=M_\theta U+c_\theta.$$

The operator is affine in the four parameters. Normalize full predeclared halfwidths into $K_j$ and $f_j$, and express a box member as a scale $s$ times $z_j\in[-1,1]$. The nominal state is $U_0$, and the normalized first variations solve

$$S_j'=M_0S_j+K_jU_0+f_j,\qquad S_j(0)=0.$$

For the exact error $e=U_\theta-U_0$, set $r=e-s\sum_jz_jS_j$. Direct substitution gives

$$r'=M_\theta r+s^2\sum_{j,k}z_jz_kK_jS_k.$$

At all 16 vertices the dynamic operator is Metzler with nonpositive row sums; affine dependence extends this premise throughout the box. Its infinity-norm semigroup is contractive. Variation of constants then gives the **exact** remainder bound

$$\|r(t)\|_\infty\le s^2 R(t),\qquad R(t)=\sum_{j,k}\int_0^t\|K_jS_k(u)\|_\infty\,du.$$

The semigroup/logarithmic-norm facts are standard; see [Higham's explanation](https://nhigham.com/2022/01/18/what-is-the-logarithmic-norm/). This is an application, not a claim of a new general theorem.

For a half-second interval of length h, contraction also bounds the integral by

$$h\|K_jS_k(a)\|_\infty+\tfrac12h^2\|K_j\|_\infty\|S_k'(a)\|_\infty+\tfrac16h^3\|K_j\|_\infty\|K_k\|_\infty\|U_0'(a)\|_\infty.$$

Sensitivity chord bounds use $S_k'''=M_0S_k''+K_kU_0''$. Add the endpoint sensitivity envelope, chord errors and $s^2R$ cell by cell. Subtract this radius for the all-cell floor, add it for the outside-inlet ceiling, and add twice the outside-inlet radius for spread. Restart one-sided derivatives at command changes; never reset the accumulated remainder. The finest-network remainder at scale 0.25 is at most 0.042666°C.

Temperature, first-derivative and second-derivative errors are respectively assumed bounded by 2×10⁻⁶°C, 2×10⁻⁶°C/s and 2×10⁻⁶°C/s² as used in the calculation. These are conditional floating-point bounds, **not directed-rounding interval proofs**. Vertex row sums are checked with a floating-point tolerance; the nonpositive mathematical premise follows from conservative positive-parameter assembly.

## Failed route and independent challenges

Four scales (1, 0.5, 0.25, 0.1) and three networks were specified before outcomes. The first accumulated max-norm defect bound failed all 24 qualifications. Its finest full-box error grew to about 28°C: a failure of a loose certificate, not a physical counterexample. The second route kept exactly the same boxes, scales and commands; preserving spatial first variations reduced the remainder. Both 0.25 and 0.1 pass all six physical qualifications; 0.5 and 1 do not. No extra smaller scale was added to obtain success.

An independently assembled conservative RHS, integrated by RK45 at half-second samples, challenged all 16 vertices and the center of the largest common qualifying box: 102 replays. All sampled extrema lie inside their corresponding derived bounds; maximum energy residuals are below 3.4×10⁻¹⁰ W and 3.3×10⁻⁷ J. Twenty independently calculated scalar analytic examples check the exact remainder identity. The independent RHS shares network geometry with the producer; it is not an independent physical calibration. Finite corners challenge implementation; the derivation supplies continuous coverage.

Actual producer time was 4.238 s for the failed route and 8.386 s for the structured route, within their shared 300 s boundary. Independent replays took 35.343 s within 120 s. These are computation times, not total research time or a model bill.

This supplement was developed with Codex and reviewed by an additional AI agent. “Independent” numerical checks mean a separate RHS and solver, not an independent human or physical experiment. This is a same-problem developmental study with prior solution exposure.

## Inspect or reproduce

`continuous-transfer.json` binds a non-pickle byte archive containing the predeclared conditions, both producers, both outcomes, corrected mathematical note, checker and frozen dependencies. `feedback_study.continuous_values()` checks hashes, frozen commands, parameter/scale identity, physical versus reserve flags, corner coverage, water units and budgets. This fast audit does **not** recompute temperatures.

To rerun, extract archive members to a fresh directory preserving their paths, remove the two producer result files and the checker result file only in that new copy, then run `derive.py` using the locked project environment. In the new copy only, bind `structured/design.json`’s `previous_result_sha256` to the newly written first result before running `structured/derive.py` and `structured/check.py`; elapsed time and receipt hashes belong to the new run. Keep all numerical conditions unchanged. Each refuses an existing result. Failed or partial receipts are retained. The archived results remain unchanged. The checker chooses its scale by the predeclared rule; it does not optimize a favorable test set.

The transferable lesson is to diagnose a failed bound before shrinking the question: exploit spatial dissipation, control the full remainder, and distinguish physical limits, design reserves and controller guarantees.
