# Transport, loss and comfort: a signed spatial-functional criterion

This is a new interpretation and check of existing finite-network evidence, not a new optimizer, physical experiment or independent award rating. The first remote Dirichlet probe deliberately grants an unrealistically favorable ceiling on every stream cell. All six96cell cases remain above39C; this route is inconclusive and is closed. It cannot see the shared-flow/spread coupling, and the two comfort masks give the same controlled-cell ceilings. No failure is hidden or promoted into feasibility.

## Statement and derivation

Let z=T−f, where f is the all-cell floor. The autonomous controlled thermal network is

z'=Kz+d+q(Sz+h), 0≤q≤U,

and P is the safe-state polytope: 0≤z_i≤ceiling_i−f (50C barrier inside the inlet region), and max(z_outside)−min(z_outside)≤span. The initial state z0 is fixed. For any fixed signed weights w define

E(z)=wᵀz; E_min=min_{z∈P}wᵀz;
R=max{max_{z∈P}wᵀ(Kz+d), max_{z∈P}wᵀ((K+US)z+d+Uh)}.

For each fixed z, wᵀz' is affine in q; hence its maximum on[0,U] is at an endpoint. No q monotonicity or product-of-means assumption is needed. While a trajectory is safe, E'≤R almost everywhere, including measurable flow policies. Therefore

E_min≤E(z(t))≤E(z0)+tR.

If R<0, safety cannot persist beyond t*=(E(z0)−E_min)/(−R). If E_min−E(z0)−HR>0, no safe trajectory of duration H exists. Equality alone does not exclude safety, and a nonpositive gap does not prove feasibility. For multiple independently bounded controls evaluate all endpoint combinations only when dynamics are affine in each control jointly with no unaccounted interactions.

The weights may have both signs; E is a spatial-temperature contrast, not average bath temperature or physical stored energy. Equivalently use energy weights ψ_i=w_i/C_i; signs identify spatial competition, not negative heat capacities. For an exactly conservative symmetric conductance matrix, diffusion contributes sum_{i<j}Gij(ψ_i−ψ_j)(z_j−z_i). Archived binary coefficients have tiny nonzero row sums; their exact identity additionally retains sum_i ψ_i(z_i+f)sum_jGij. The exact checker includes this term rather than silently treating it as zero; losses contribute −sum_iψ_i[ha_i(z_i+f−Ta)+hb_i(z_i+f−Tb)]. The stream contribution telescopes as q*rho_cp/60000 * [ψ_0(Tin−f)+sum_{j<last}(ψ_{j+1}−ψ_j)z_j−ψ_last z_last]. This shows exactly where transport, loss, initial reserve and permitted temperature contrast enter. They share one safe-state support calculation: maximizing each contribution separately loses coupling and weakens the conclusion. It is not an identified physiological mechanism or a general mixing threshold.

## Actual extraction, computation and exact check

Freeze public source a5be607 and the original/fixed-region certificate packet bytes. Take the signed balance-row dual difference, normalized numerically once and then treated as exact binary rational weights. Test both signs rather than choosing the successful sign retrospectively without recording the other. Three small state-support LPs per sign give endpoint supports and terminal minimum; no original certificate LP or heat simulation is rerun. Eight signs × three support solves are included. Bounds3seconds per solve, phase120seconds; actual producer elapsed is in potential-results.json.

A separate checker uses no LP solver and reconstructs every flux coefficient from archived primitives with Fraction, exact209/3 flow conversion, safe bounds and spread constraints. It clips candidate dual signs and corrects stationarity errors over the finite box before accepting each support bound. New support bounds are not copied from the old certificate's final number. Eight zero-weight/zero-dual controls lose positivity. The opposite signs all have negative horizon gaps.

| Fixed input | Exact corrected positive gap at1800s, displayed | Conservative safe-duration upper bound |
|---|---:|---:|
| Original96, moving mask |0.05111355532245605|less than1717s|
| Fixed-region96 |0.11505590003895615|less than1619s|
| Fixed-region288 |0.21762179016435163|less than1481s|
| Fixed-region768 |0.17934400044793608|less than1533s|

Displays are approximations; inequalities in the time column use ceiling integers above the exact ratio. The original96 derived upper bound is about28.60minutes; this is an all-control necessary limitation of that particular thermal network. The fixed-region masks define different safe sets and the source lane still moves with the grid. Their time bounds cannot be read as mesh convergence, a continuum limit, the original288verdict or real-bath safe durations.

This decomposes rather than independently reproduces the prior whole-horizon conclusion: the weights come from that previously exposed dual. The positivity is checked independently using new state-support duals and exact coefficient reconstruction. It is not blind discovery, a new empirical model or proof of originality. A low-dimensional analytic example and fixed-weight transfer will test what can be reused without refitting.

## Fixed-weight transfer, without fitting

A separately declared extension freezes the original96weights and changes only diffusion conductance by1,10/3 and10 (D≈.0003/.001/.003); all geometry, capacity, losses, stream and comfort constraints remain fixed. The first reproduces the positive functional gap. The latter two exact support bounds are nonpositive (about−2.75067 and−10.75515), so the criterion stops excluding. These are same-scenario changes, not unseen-task transfer, and do not prove a feasible control. The added reach of diffusion changes the maximum attainable spatial functional drift; reordering q cannot overcome a strictly negative maximum at weak mixing, whereas stronger mixing requires actual policy qualification rather than an impossibility assertion. Floating optimum values and exact conservative support values need not be identical: the independently corrected dual support can be weaker when solver tolerances leave small stationarity residuals.

## Continuous exclusion region

`boundary.json` freezes the original96 weights and support duals. It varies only diffusion scale s=D/0.0003, a common multiplier ℓ of both loss arrays, and spread z; all other physical inputs remain fixed. Exact finite-box dual correction gives a concave piecewise-affine horizon gap. Strict positivity excludes every measurable flow in [0,3] L/min on this network. Enumerating residual breakpoints gives seven nonempty intervals among twelve declared slices, without another support LP or heat optimization.

At original losses and 1.5°C spread, inward-rounded 0.00029047<D<0.00030957 m²/s is excluded. At D=0.0003, separately, loss multipliers [0.97894,1.2] or spreads [0.75,1.53242]°C are excluded. Root equality does not exclude; outside these sufficient windows the frozen certificate is uninformative, not a feasible-policy claim. The low-diffusion boundary is therefore not evidence that weaker mixing restores feasibility. These are conditional finite-network results, not a real-bath or continuum theorem.

`derive_boundary.py --output NEW.json` and `boundary_thresholds.py --output NEW.json` refuse existing destinations. `check_boundary.py` independently checks support intervals against direct network LP diagnostics and prints a fresh receipt without replacing the archive. `boundary_values.py` verifies the accepted capsule, exact root brackets and strict positivity of every printed inward bound before the paper consumes them. Mathematical derivation and independent checks, rather than hashes alone, support the claim.

## Spatial shape of the frozen contrast

On the original96network, significant negative weights (threshold1e-9 only for descriptive counts) lie in the first two x-slabs near the inlet. The largest positive weights lie at the remote x end, especially the side-wall corner across all three vertical layers. The signed negative mass is≈0.02657 and positive mass≈0.97343 under unit absolute-weight normalization; these are mathematical weights, not mass fractions. This contrasts remote warmth with inlet-near warmth rather than measuring mean heat. Precise coordinates and weights are in weight-shape.json. The exact support bound simultaneously restricts transport, losses and the same safe-state temperature spread; neither independent hottest stream cells nor total bath energy alone supplies that coupling. This is spatial attribution within the constructed model, not causal identification from measurements.

## Replaying the evidence

From the repository root, use the locked project environment:

```sh
.venv/bin/python demos/mcm-2016-a/reproduce/reference/spatial-functional/check.py
.venv/bin/python demos/mcm-2016-a/reproduce/reference/spatial-functional/check_transfer.py
```

These two checkers reconstruct the exact bounds without solving an LP or modifying the archive. `potential.py`, `transfer.py` and `analytic_check.py` require an explicit `--output` pointing to a new scratch directory; they never replace the accepted receipts. `manifest.json` binds the current portable files and the two external certificate archives. Historical checker hashes inside original receipts identify their original execution, while the manifest and a fresh replay identify the portable checker version.
