# Delayed upper: error and domain contract

The adopted candidate for acceptance is the archive-only checker, not the producer's incompletely documented rounding scalar. The first producer run and its receipt remain unchanged. Primitive reconstruction took place after that run; the second execution binds actual primitive bytes and replays a different flux assembly. Both executions treat these binary primitive values as exact, with subsequent physical divisions interpreted rationally. This is a fixed finite-network result.

## Exact dynamics and comparison

Let A=(G−diag(ha+hb))/C rowwise, v=(22ha+34hb)/C, B=adv/(60000C), h=hot/(60000C). The only eight nonzero adv rows form the archived inlet chain; the checker reconstructs this chain rather than calling network(). All off-diagonals of A and B are nonnegative; A row sums are negative, B row sums nonpositive. The physical vector field is f_q(y)=Ay+v+q(By+h), 0≤q≤3. Each component is bounded above by g(y)=Ay+v+3max(By+h,0).

Every generalized Jacobian row of g is A_i+3λ_i B_i, 0≤λ_i≤1. Thus g is cooperative, globally Lipschitz with L=max_i Σ_j(|Aij|+3|Bij|), and its flow is nonexpansive in infinity norm. The exact Euler map is monotone and nonexpansive when h max_i[−Aii−3Bii]≤1. The analogous passive restriction holds for h_p. Exact inward barriers at 21 and 51 prove invariance of [21,51]^96 for both exact dynamics and the stable Euler map. Heun/SSP2 is (y+E(E(y)))/2 and inherits box preservation and nonexpansion. Max kinks do not require second classical derivatives.

## Independent arithmetic DAG

Assume ordinary IEEE binary64 round-to-nearest arithmetic, finite primitives, no flush-to-zero affecting ordinary magnitudes, and the usual dot-product bound gamma_n=n u/(1−n u), u=2^−53. BLAS reassociation or FMA may reduce the error; the absolute dot bound covers ordinary serial/pairwise/FMA evaluation. This is an explicit floating-point assumption, not a formal verified implementation of BLAS.

The checker evaluates passive f directly as (G@y−ha*(y−22)−hb*(y−34))/C. At the eight stream cells it adds 209*max(upstream−y,0)/C, since 3*4180000/60000=209 exactly. Upstream is 50 for the first row and the previous stream cell otherwise. This equals g for the archived stream, but has different rounding and operation order from the producer.

On |y|≤52, define

S=max_i [52 Σ_j |Gij| +74 ha_i+86 hb_i +209·104·1_stream(i)]/C_i.

The dot has at most N products and N−1 additions. Each scalar branch has a subtraction, product, two sum/difference operations and a division; max is a selection of an already-rounded operand. The sum of absolute exact operands in these branches is bounded by the numerator defining S. Errors in differences before multiplication are included by counting their multiplication descendants. With m=4N+64, all of these paths, including the two evaluations in SSP2, have fewer than m rounding sites. A conservative per-field bound is gamma_m(S+1); the extra 1 and the generously enlarged m absorb absolute subnormal errors (also included separately as 10^−280 per map).

For Euler update, addition and multiplication contribute at most gamma_m(52+h(S+1)), in addition to h gamma_m(S+1) from field evaluation. A perturbed trial changes its second field by at most L times its error. For SSP2 in the implemented form (y+trial+h f(trial))/2, propagate those errors through the second evaluation, two additions and division by 2. An overestimate covering both maps is

R(h)=gamma_m[8·52(1+hL)^2+16h(S+1)(1+hL)]
     +2|float(h)−h|(S+1)(1+hL)+10^−280.

Factors 8 and 16 respectively exceed the four state-addition magnitudes and the two field evaluations plus their scalar descendants, each amplified at most twice by 1+hL. This loose expression is checked exactly with Fraction; both R(1/20) and R(86.5/1000000) are below 10^−9°C. Unlike the producer, this direct-flux expression does not store approximate A/v/B/h coefficients, so no separate coefficient-mismatch term is needed. Every division/multiplication during flux evaluation is covered by the DAG bound.

## Noncircular domain induction

The exact Euler and SSP2 maps preserve the box and are infinity-norm nonexpansive. If the current floating state is within r of the box, its exact next map remains within r, and the floating next map is within r+10^−9. In the passive SSP2 trial the same argument adds one additional 10^−9; no temporal truncation error is needed for this numerical-map-to-box argument.

Starting at 40, the cumulative passive/active map distance is at most (18000+1000000+1)·10^−9=0.001018001°C<1°C. The passive trial bound is 18001·10^−9<1. Thus every complete state and trial is inside |y|<52. This establishes the domain used for the arithmetic bound by induction; sparse runtime assertions are only diagnostic. The exact step satisfies the stability inequality; rounded-step conversion is already in R(h). No overflow is possible under the checked finite primitive bounds and this domain.

## Truncation and propagated initial error

For passive dynamics, z0=A(40·1)+v is componentwise negative. M3=||A²z0||∞ bounds the third time derivative because exp(At) contracts. For t/h_p complete SSP2 steps, accumulated error is t h_p² M3/6+(t/h_p)10^−9. The 790 s initial error is delta_p; a separate 900 s bound is checked.

For the autonomous optimistic flow, time-shift nonexpansion bounds ||g(y(t))||∞ by its initial value. Starting from uncertain passive state, M2=L(||g(computed_prefix)||∞+L delta_p). The Euler local integral defect is at most M2 h²/2. The total endpoint radius is delta_p+86.5² M2/(2·1000000)+1000000·10^−9. The checker computes every constant from primitive rational values, then adds this exact radius to its binary computed cell-89 endpoint. The strict rational upper bound is 38.99797708255518°C<39°C.

## Quantifiers and limits

The passive derivative stays componentwise negative, as exp(At)z0<0. A start d between 790 and 900 has a colder initial state; by comparison its optimistic cell 89 after 86.5 s is no warmer than the bounded 790 witness. This time is inside the 1800 s horizon. For d≥900 the passive prefix itself violates the floor by 900 s. Therefore every common measurable command in [0,3] with a zero-flow prefix of at least 790 s fails to maintain all cells at or above 39°C throughout the horizon.

This excludes the original fixed archived 96-cell network with D=.003 and the stated temperatures. It does not establish a sharp threshold, feasibility below 790, a feasible rowwise-max control, a PDE limit, a physiological model or empirical bathtub validation. The replay only changes numerical assembly, not the underlying physical model.
