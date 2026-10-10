# Collatz First Contraction: A Finite Certificate

**A conditional theorem over an infinite domain · Structural bounds make the checks finite and reveal where this route stops.**

[简体中文](README.md) · [Complete paper](deliverables/paper.pdf) · [All cases](../README.en.md) · [Praxis](../../README.en.md)

[Results](#results) · [Review](#review) · [Reproduction](#reproduction)

[![First-contraction depth, unclassified density and finite scan bound](assets/overview-en.png)](deliverables/paper.pdf)

## The question

The shortcut Collatz map divides even integers by two and sends odd integers to (3n+1)/2. When does an orbit first fall below its starting value? Its step count differs from the map that leaves the odd step undivided.

A finite iterate has the form “coefficient × start + offset.” The coefficient can fall below one while the positive offset prevents an actual descent. Write τ for first coefficient contraction and σ for first descent. The study uses the constraints on every earlier prefix to establish conditions under which they coincide.

## Results

| Result | Evidence and scope |
|---|---|
| **For every n>1, τ(n)≤1024 implies σ(n)=τ(n)** | A sharp offset envelope, finite-reduction proof and exact checks. There is no upper bound on n; larger or infinite τ is outside the theorem. |
| Potential exceptions require only starts **2…72058** | The worst bound over 647 feasible crossing depths; all 72057 starts were checked without a failure or a trajectory censored at the cap. |
| Unclassified natural density is about **1.1537401×10⁻¹⁹** | Forward state counts agree with a separate binomial recurrence. This is neither a divergence probability nor zero. |
| Normalized maximal offsets tend to **1/(6 ln 2)** | An exact identity and equidistribution establish the limit, without a claimed finite-depth error rate. |
| A fixed horizon and one fixed envelope scan bound cannot cover the general case | Explicit uncovered starts and an unbounded sufficient scan limit; neither result supplies a counterexample or excludes other methods. |

## Argument and computation

The first-crossing condition supplies an integer barrier on every earlier parity prefix. It bounds the latest possible positions of odd steps, and one word attains all of those bounds, yielding the sharp offset envelope.

If the contracted endpoint has not descended, its start must be no larger than the offset divided by the contraction gap. Maximizing this bound over feasible depths reduces the potential exceptions to starts at most 72,058.

Generation and checking use different constructions: barrier words and forward counts on one side; max-plus extrema, binomial first-passage counts and direct integer trajectories on the other. Six damaged-certificate tests alter offsets, thresholds, crossing-depth coverage, density, scan range or histogram; each is rejected. The [verification summary](verification.json) binds the manuscript, source and recorded calculations.

Finally, envelope asymptotics and explicit uncovered starts establish what increasing this calculation alone would leave unresolved.

## Review

**A substantive computational synthesis with inspectable proofs and certificates; an original research contribution remains unestablished.**

Its strength is the connection between structural bounds and finite verification for a conditional all-integer statement. Distinct recurrences check the extrema and counts, while the exposition separates the theorem, density and unresolved domain.

Originality is the central gap. The cited Rozier–Terracol Theorem 5.3 and Corollary 5.4 state stronger coverage, so depth 1024 is not a new verification record. A theorem-level literature comparison is needed to determine the envelope and reduction's independent contribution; major new progress is not established by the present evidence.

An author-external AI role read the current seven-page paper and performed bounded independent checks. That review did not rerun the complete 72057-trajectory scan. The [version-bound assessment](evaluation.json) records the non-blind scope, distinct from human peer review or formal certification.

## Paper and materials

| Resource | Contents |
|---|---|
| [Complete 7-page English paper](deliverables/paper.pdf) | Conditional theorem, worked barrier example, proofs, two figures and route limitations |
| [Verification record](verification.json) | Evidence identities, versions and checking scope |
| [Source and certificates](reproduce/) | Generator, independent checker and frozen results |

The paper uses the shared [AMS-style research template](../../templates/research-paper.tex). Its barrier diagram explains the construction; a second figure separates the scan bound from residual density.

## Reproduction

From the repository root, create a fresh working copy:

```bash
uv sync --locked
uv run --locked python -c "from shutil import copytree; copytree('demos/collatz-research/reproduce', '.session/collatz-replay')"
uv run --locked python .session/collatz-replay/code/verify.py
uv run --locked python .session/collatz-replay/code/analyze.py
```

`copytree` refuses an existing target. The core scripts use only the Python standard library: `verify.py` checks the certificate, and `analyze.py` regenerates presentation decimals. Run the copy's `code/certify.py` to regenerate the certificate as well. Computation times exclude reading, derivation and review.

## File structure

```text
deliverables/paper.pdf     Complete English paper
reproduce/paper/paper.tex  Corresponding LaTeX source
reproduce/code/           Generation, independent checking and analysis
reproduce/runs/           Exact certificate and checking results
verification.json         Evidence identities and scope
evaluation.json           Full-paper review
assets/                   Case illustrations
```

## Background and license

Parity vectors, stopping times and offset comparisons have a classical literature; references appear in the paper. This is a literature-informed development study extending an earlier project replication. It is neither an unseen-problem evaluation nor an estimate of the plugin's causal benefit, and does not claim to resolve the Collatz conjecture.

Original scripts, documentation and paper use the repository's [MIT License](../../LICENSE). Cited publications retain their rights and are not redistributed in full.
