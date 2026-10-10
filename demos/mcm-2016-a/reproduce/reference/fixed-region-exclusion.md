# A fixed physical target changes the spatial obstruction

The original jet exclusion follows the first inlet-cell center. Refinement therefore moves both the mesh and the physical comfort target. This study declares a separate radius0.15m exclusion ball at `(0,W/2,H)=(0,13/40,23/100)m`. Membership uses exact rational cell-center distances; it is not a bound at every point in a cell or a measured source location.

Keep D=.0003m²/s,34°C contact,40°C initial water,50°C supply,22°C air,1800s horizon and every measurable q in0–3L/min. The floor is39°C everywhere; ceiling41°C and spread1.5°C apply outside the ball. The archived thermal coefficients and original grid-lane stream are unchanged. Only the comfort mask changes: non-nested on96cells and strictly tighter on288cells. The768extension has its own pre-solve design and frozen physics source; it was not part of the initial two-network design.

| Cells | Necessary rows | Variables | Corrected rational bound, displayed °C |
|---|---:|---:|---:|
|96|1332|298|0.1150559000387309|
|288|4004|874|0.21762179016332908|
|768|10644|2314|0.1793440004463907|

The [two weighted-state argument](whole-horizon-exclusion.md) applies to each declared safe-state polytope. Any safe trajectory produces zero whole1800s integrated-balance residual. Exact row reconstruction, a finite-box dual and downward coefficient-rounding correction give positive lower bounds, excluding such a trajectory on each archived coefficient network. Stored exchange-row rounding residuals are retained. These bounds are neither instantaneous temperature violations nor water savings.

The source lane still shifts with the mesh. Three specified finite-network obstructions do not establish fixed-source convergence, a continuum limit, real-bath impossibility, or a verdict for the original moving-mask288target. Both old288relaxations remain inconclusive; a nonpositive relaxed bound does not establish feasibility. Baseline24.14/21.48L policies and original certificates are unchanged.

## Independent replay

`fixed-region-exclusion.npz` contains39byte-array members without pickle, including a hash manifest, all three matrices/duals/primitives, original thermal primitives, checker, scope and distinct historical phases. Extract into a new directory, verify manifest hashes, and run `verify_exact.py` using the locked repository NumPy/SciPy environment. It reconstructs all rows and requires all three positive certificates; it does not rerun an LP or heat simulation. A fresh extraction and independent-working-directory replay produced identical complete rational bounds.

The portable checker changes only the original-primitive comparison path and its entry point: three positive statuses and a20000digit text-conversion limit. The original768checker completed the mathematics but failed to serialize its5912digit denominator at Python's default4300digit limit; only the checker was replayed. The retained failure note is a retrospective transcription, not original captured stderr. `research_values.fixed_region_exclusion()` parses bounded integer chunks without changing the host's global limit; it checks receipt scope and identity, not mathematical correctness in place of executing the verifier.

The portable phase records15 actual in-memory corruptions: zero dual, wrong initial value, wrong unit factor, altered thermal primitive and altered region, on each network. All reject certification. Initial checks were five cases on96only; their identity is not retroactively expanded. The historical producer files retain old path assumptions and inherited metadata labels/limits, so they are provenance rather than portable rerun commands. Independent reviews cover exact scope and bindings, not award calibration or experimental validation.
