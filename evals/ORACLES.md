# Synthetic oracle contracts

`planted-v2` is a **public development tool-regression suite**. Source, seeds and answer generators are available to the process. Hiding answer fields in CLI output does not isolate the oracle or make an Agent evaluation blind. `solve_with_tools` calls Python functions; it does not exercise an Agent, skill selection or host installation. Prior results retain their original meaning and version.

## Reference paths and model scope

| Task | Reference answer | Production path and independence limit |
|---|---|---|
| LP | Constructed primal/dual complementary-slackness certificate | HiGHS; checks value **and** vector feasibility, objective consistency and optimality; alternative optima accepted |
| Queue | Rational birth-death stationary weights plus infinite geometric tail | Erlang M/M/c calculation; separate implementation, same stationary Poisson/exponential assumptions; waiting time in reciprocal rate units |
| SIR | Known beta/gamma; finite-initial-condition final-size invariant solved by bisection | Fitting shares the forward simulator that synthesized observations; not a fully independent forward-model check. S0=999990, I0=10, initial recovered=0, N=1e6, rates per day. Attack fraction includes initial cases; production final-size approximation neglects finite initial infection, within tolerance here |
| Assignment | Enumeration of 6! permutations | Hungarian algorithm; exact discrete optimum |
| Structure | Analytic labels for nine finite families, positive integer coefficients 1..3, domain [1,3]^2 | Production probes are diagnostics; ground-truth labels no longer come from a finite grid |
| Heat PDE | Fourier sine-mode decay | Finite-volume integration and interpolation; consistent input units |
| Markov | Eigenvector nearest eigenvalue 1 of the displayed matrix | Stationary linear-system calculation; floating rounding makes this a numerical oracle |
| Game | Closed-form 2x2 mixed-strategy value without saddle point | Linear programming; row-player payoff convention |
| Inventory | Normal-density quadrature on mean +/- 8 sd and bounded scalar optimization on mean +/- 4 sd | Critical-fractile formula; approximate reference, not brute force. Mathematical untruncated normal demand includes a negative tail; not a physically nonnegative demand model |

The LP certificate uses x>=0, Ax>=b, y>=0, c>=A.T y and c.x=b.y. A matching value alone cannot certify the submitted allocation.

## Exact structure labels

Symmetry means x/y exchange; power law means constant elasticities in both variables. Proofs apply only to these families on [1,3]^2; adding a family requires a new proof and tests.

- `a*x^2+b*y^2`: positive diagonal Hessian; symmetric iff a=b; increasing in x; not a joint monomial.
- `a*(x+y)+b*x*y`: Hessian eigenvalues +/-b; symmetric and increasing in x; not a power law.
- `a*x^b/y^a`: Hessian determinant has sign b-a-1; first diagonal entry has factor b(b-1)>=0. Convex iff b>=a+1, including equality; asymmetric monomial; increasing in x.
- `a*sin(x)+b*y^2`: negative second x derivative throughout the domain; first derivative changes sign; asymmetric, not a power law.
- `a*x+b*y+exp(x*y/4)`: Hessian determinant `exp(x*y/2)*((x*y)^2-(x*y+4)^2)/256<0`; symmetric iff a=b; increasing in x; not a power law.
- `x*y`: indefinite Hessian; symmetric monomial; increasing in x.
- `exp(a*x)+exp(b*y)`: positive diagonal Hessian; symmetric iff a=b; increasing in x; not a power law.
- `a*x^2+b*x*y+a*y^2`: Hessian eigenvalues 2a+/-b; convex iff b<=2a, including equality; symmetric and increasing in x; not a power law.
- `log(x)+a*y`: negative second x derivative; asymmetric, not a power law; increasing in x.

## Submission contract and tolerances

Finite JSON numbers only: booleans, strings, NaN and infinities fail. Property lists require unique valid strings. LP requires a finite vector of the correct dimension. Missing/invalid fields fail explicitly without coercion or repair.

Scalar acceptance is `abs(got-want)<=tolerance*max(1,abs(want))`, except R0, attack fraction and order quantity which use absolute tolerance. Objective 1e-6, waiting time 1e-6, assignment total 1e-9, temperature 2e-3, state fraction 1e-6, order quantity 0.2; R0 0.1 absolute, attack fraction 0.03 absolute. Order quantity uses 0.2 absolute units, replacing the earlier size-dependent 20% allowance. This remains a numerical tool check rather than calibrated method ranking.

LP nonnegativity allows 1e-8 absolute; constraints allow 1e-6*max(1,abs(b_i)); objective consistency uses the objective tolerance. Tests include broken production outputs, malformed answers, alternative optima and semidefinite boundaries.

## Agent comparisons

Actual inputs, outputs, commands/tools, budgets and failures must be archived. Both arms need the same model/runtime/data/budget, with ordinary Python permitted in the baseline. Answers must be outside the tested process's accessible filesystem/tools; restrict network leakage and separate development from held-out tasks. Actual independent reviews and negative controls are needed. A JSON schema, review prompt, correct tool result or incomplete two-arm trial does not establish plugin benefit, reviewer calibration or award probability.
