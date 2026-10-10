# Why changing the supply schedule cannot repair this network

The result in §11.4 concerns one specified thermal network, not an actual bathtub or the continuum PDE. It excludes **every measurable supply function** with values in 0–3 L/min, including delayed, pulsed and feedback-generated functions once their realized trajectory is fixed. It does not assume six constant stages.

## Fixed conditions

Use the archived 8×4×3 network, D=0.0003 m²/s, original surface-stream route, fixed contact at 34°C, uniform initial water at 40°C, supply at 50°C and horizon 1800 s. The floor is 39°C in every cell. The ceiling 41°C and spread 1.5°C apply outside the predefined inlet jet region. Geometry, capacities and heat-exchange coefficients are byte-bound in `primitives.npz`; their stored floating values are interpreted as exact rational constants. This distinction is essential: exact arithmetic on those constants does not certify their empirical accuracy.

## A necessary condition, rather than another policy search

Partition the horizon into sixty 30 s windows. Keep endpoint temperatures, time averages, mean flow and the separate moments w_i=mean(q T_i). Never replace the last by mean(q) mean(T_i); the independent checker includes a counterexample to that equality.

The integrated heat balance is exact in those moments because the unforced network is linear and the stream exchange is affine in q. A feasible trajectory has zero residual. Within the feasible temperature box, pointwise McCormick inequalities imply the four product bounds printed in the paper after integration. Common nonnegative q and occupied-region spread also imply |w_i−w_j|≤1.5 mean(q). This couples the stream cells; omitting it made the earlier relaxation inconclusive.

The network is cooperative. Positive capacity, nonnegative off-diagonal exchange and a strictly negative RHS at the uniform 50°C barrier establish T_i≤50°C for every nonnegative supply. The exact verifier checks these conditions, including the tiny row-sum rounding in the archived exchange matrix. Under the feasible temperature box, vertex extrema bound each derivative between f_min and f_max. Integrating forward and backward from each endpoint gives four endpoint–mean inequalities. Node and mean ceiling/spread constraints are necessary as well.

These conditions produce 61,869 rows and 12,399 bounded variables. The optimization objective is the largest absolute per-window heat-balance residual e, measured in °C, not a temperature constraint violation. Safety would imply e=0.

## Exact finite-box dual certificate

Let the stored relaxation be Ax≤b, l≤x≤h, objective c·x=e. Clip its candidate multipliers to μ≤0, ν≥0 and η≤0. Set r=c−Aᵀμ−ν−η. Regardless of solver convergence or stationarity accuracy, every feasible x satisfies

c·x ≥ μ·b + ν·l + η·h + sum_j min(r_j l_j, r_j h_j).

The verifier evaluates this inequality with Python Fraction arithmetic. It independently reconstructs every row from the archived heat-flux primitives. If a reconstructed row differs from a stored row, its uniformly bounded perturbation is ε_i=|b_i−b_i*|+sum_j |A_ij−A_ij*| max(|l_j|,|h_j|). Any exact physical moment vector then satisfies the stored row with RHS b_i+ε_i. Accordingly the conservative dual correction is sum_i μ_i ε_i, which is nonpositive.

The resulting exact bound is strictly greater than **1/5000°C**. Its decimal display is approximately 0.00028979098006699°C, with a coefficient-rounding correction about −1.55×10⁻¹⁴°C. The simple rational threshold, rather than the displayed digits, is the accepted certificate. Zero residual is impossible. No error allowance for a simulated weak-mixing trajectory is needed in this argument: such a trajectory is never assumed to exist.

## Independent rejection checks and retained failures

The known-feasible D=0.001, q=1.125 L/min case supplies a separate direct-flux/RK45 trajectory and integrated temperature moments. They satisfy its analogous full matrix to 4.3×10⁻¹³ in floating arithmetic; physical limits pass on sampled points. Its LP solver timed out after its declared five-second allocation and is **not** reported as solved.

The exact verifier rejects a zeroed dual, a changed balance coefficient, a wrong initial-state bound and a changed primitive capacity. These checks distinguish certificate validity from solver status and receipt hashing. Earlier unrestricted/coarse relaxations were inconclusive; two six-stage searches produced physically invalid candidates. Those are different forms of evidence and are not retrospectively relabeled as impossibility proofs.

## Replay without repeating research

`all-control-exclusion.npz` is a non-pickle byte archive. Extract its members into a fresh directory after checking `manifest.json`. Run `verify_exact.py` there with the repository's locked Python environment. It reconstructs the rows and exact certificate from the archived matrices and primitives, prints a new JSON receipt and does not rerun either LP or the baseline optimization. It takes roughly one second on the development machine; its cooperative guard is 60 s. `research_values.all_control_exclusion()` checks archived identity/scope before report generation; it does not substitute for this fresh exact replay.

The original `run.py`, numerical check and first/second exact check remain byte preserved with their actual receipts. A stale “near zero” comment in the original numerical checker belongs to its earlier coarse ancestor; the positive weighted-spread result is established by the separately named exact verifier. Source changes are not attributed to earlier runs.

The claim currently stops at the fixed 96-cell network. Finer-network, alternative-route, uncertain-parameter, continuum and empirical validity need their own evidence. It gives a decision boundary—change the assumptions or physical arrangement—rather than a globally optimal intervention.
