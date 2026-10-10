# Domino Tilings: From Exact Counts to a Recurrence Proof

**A 3×2n rectangle · Independent computations suggest the pattern; two arguments establish it for every size.**

[简体中文](README.md) · [Complete note](deliverables/paper.pdf) · [All cases](../README.en.md) · [Praxis](../../README.en.md)

[Results](#results) · [Review](#review) · [Reproduction](#reproduction)

[![Exact tiling counts, held-out terms and two proofs](assets/overview-en.png)](deliverables/paper.pdf)

## The problem

How many ways can 1×2 dominoes tile a 3×2n rectangle? Let a(n) denote the count. Small boards can be enumerated directly, but larger ones call for a recurrence and a reason to trust it beyond the observed terms.

This case reconstructs a classical enumeration. Its focus is the transition from computational evidence to an all-size proof: **many successful tests do not, by themselves, establish a theorem.**

## Results

| Result | Justification |
|---|---|
| **a(n)=4a(n−1)−a(n−2)**, with a(0)=1 and a(1)=3 | Two independent arguments: a board decomposition and a transfer-matrix proof. |
| a(n)=((3+√3)/6)(2+√3)ⁿ + ((3−√3)/6)(2−√3)ⁿ | Solving the recurrence; successive ratios tend to 2+√3. |
| a(0)…a(16): 1, 3, 11, 41, 153, …, **1117014753** | All three counting methods agree through n=5; matrix and recurrence counts agree through n=16. |
| No polynomial formula of degree ≤8 | The exponential growth rules out a polynomial count. |

## Derivation and checks

Backtracking, an eight-state transfer matrix, and coupled recurrences from local board configurations first produce independent small-case counts. An exact recurrence search uses only the first 13 terms; a(13)…a(16) are held out. A further counterexample search covers 2≤n≤60.

The all-size result has two proofs:

- **Decomposition:** an exhaustive classification at the left edge yields two coupled recurrences, from which the auxiliary count can be eliminated.
- **Finite-state argument:** the matrix supplies a proved order bound of eight. The difference sequence for the proposed recurrence inherits that bound, so eight zero initial terms establish that it vanishes identically.

The order bound comes from the mathematical structure, not the fitted data. Held-out tests and counterexample searches challenge the guess; the theorem rests on the separate arguments. The [archived results](reproduce/reference/) retain the computations and rejected route.

## Review

**A sound, readable reconstruction of a classical result, with a useful account of discovery and proof checking.**

The complementary proofs are its main strength. The decomposition explains where the recurrence comes from; the matrix argument explains why a finite check is sufficient. Computational agreement, conjecture testing and proof are clearly distinguished.

Its contribution is expository rather than original mathematical research. The central enumeration is known, and no new theorem or major consequence has been established. Further computation or typesetting would not resolve that originality gap.

This is an author-external AI review of the current four-page note, conducted non-blind. The [version-bound assessment](evaluation.json) records its scope; it is neither human peer review nor proof-assistant certification.

## Note and materials

| Resource | Contents |
|---|---|
| [Complete 4-page English note](deliverables/paper.pdf) | Three counting methods, two proofs, diagrams and theorem scope |
| [Calculation source](reproduce/explore.py) | Exact counts, recurrence search, held-out checks and route record |
| [Reference results](reproduce/reference/) | Frozen computations and evidence |

The note uses the shared [AMS-style research template](../../templates/research-paper.tex). Open the complete PDF for the arguments and diagrams.

## Reproduction

From the Praxis repository root:

```bash
uv sync --locked
uv run --locked python demos/domino-research/reproduce/explore.py
```

The script recomputes the counts and checks into `reproduce/reproduced/`, leaving the reference archive intact. Repeated runs update that reproduction directory. No typesetting tools or AI service are needed for the calculations.

Optional typesetting: `uv run --locked python demos/domino-research/reproduce/build_note.py`, using Tectonic 0.17.0 and the pinned resource bundle.

## File structure

```text
deliverables/paper.pdf   English research note
reproduce/explore.py     Counts, conjectures and checks
reproduce/build_note.py  Builds the note from archived values
reproduce/reference/    Frozen results and route record
evaluation.json         Full-note review and checking scope
assets/                 Case illustrations
```

## Sources and license

The count is [OEIS A001835](https://oeis.org/A001835), with an index shift of one. The case presents a reconstruction, without claiming a new discovery. Original code, note and figures use the repository's [MIT License](../../LICENSE).
