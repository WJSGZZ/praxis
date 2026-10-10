# A whole-horizon obstruction from two weighted safe states

This is a shorter proof of the **same fixed96-network impossibility claim**, not a larger physical exclusion domain or a larger temperature violation. The [original windowed certificate](all-control-exclusion.md) remains byte-preserved with its own residual definition, failures and independent feasible-control trajectory. The two relaxations are not asserted to be equivalent.

Use precisely the original archived96 coefficient network: D=.0003m²/s, fixed34°C contact, uniform40°C initial water,50°C supply,22°C air,1800s horizon, q in0–3L/min; floor39°C everywhere and ceiling41°C/spread1.5°C outside the declared jet. Cooperative exchange and the uniform50°C inward barrier bound jet temperatures by50°C. Primitive floats are treated as exact constants, not certified empirical values.

## Why both weights are needed

Set θ=T−39 and let P={θ:Bθ≤d} include θ_i in[0,2] outside the jet,[0,11] inside, and outside pairwise differences at most1.5. Define Q=mean(q), m=mean(θ), v=mean(qθ) over the **whole1800s**. U=3L/min. Do not identify v with Qm. Nonnegative weights q and U−q give

Bv≤dQ,

B(Um−v)≤d(U−Q).

For0<Q<U, the corresponding conditional states v/Q and(Um−v)/(U−Q) lie in P. Conversely a mixture of these states with weights Q/U and1−Q/U and control U/0 realizes the static moments. At Q0/U the individual product envelopes give the degenerate products without division. Thus these inequalities express the exact static moment hull for this bounded polytope; they do **not** establish dynamical or endpoint realizability.

The implementation uses all96 product moments, individual envelopes for box constraints, and maxima/minima auxiliaries for both weighted outside spreads. Integrating the archived linear heat exchange and affine-in-q stream dynamics is exact in m,v,Q. Retain the initial θ=1 and final θ in P. Each balance is relaxed by a common absolute residual e. Any safe trajectory would yield e=0. The LP has1332necessary inequalities and298bounded variables.

## Exact separation and replay

The candidate dual is checked with exact Fraction arithmetic, clipped multiplier signs and a finite-box stationarity correction. Every row is reconstructed from primitive capacities/conductances, including the stored exchange row sums. Uniform stored-row perturbations are explicitly charged downward to the dual, as detailed in the original certificate. The resulting exact lower bound exceeds **1/25°C**, displayed as0.05111355532219199°C. This is an1800s **integrated-balance residual**, not temperature shortfall, water amount, or the old30s objective.

`whole-horizon-exclusion.npz` stores manifest-bound byte members without pickle. Extract into a new directory, verify each manifest hash, and run `verify_exact.py` using the locked repository environment. It reconstructs the certificate and rejects four corruptions without rerunning optimization. `moment_fixtures.py` separately checks64 constructed exact safe-state mixtures including zero/max flow, an impossible moment rejected by the complementary weight, and an artificial no-loss analytic positive control. These are not exhaustive physical tests.

The portable verifier differs from its privately audited original only in selecting96 rather than also requiring the unincluded288 archive. `archive-scope.json` records that change and original source hash. The historical producer/design/results preserve the actual96/288 experiment; their original input directories are not recreated by extraction. Fresh proof replay uses the stored primitive/matrix/dual, not those historical directory assumptions. `research_values.whole_horizon_exclusion()` checks recorded identity, physical scope and the same primitive as the old certificate; it does not replace executing the verifier.

The actual288 whole-horizon and six300s chronological necessary relaxations did not yield a positive conservative bound. Three one-step feedback families terminated before1800s; independent direct-flux RK45 replay showed an Euler-safe prefix slightly exceeded the ceiling. Failed policies do not prove universal infeasibility, and zero relaxed residual does not construct a safe policy. No finer-network certificate, fixed-domain convergence, alternative-closure theorem, real experiment or award claim follows. These unsuccessful and inconclusive results remain distinct in the research record.

A separate [fixed-physical-region study](fixed-region-exclusion.md) now has three positive finite-network certificates. It changes the comfort masks and therefore does not resolve the original288target or extend this original96theorem.
