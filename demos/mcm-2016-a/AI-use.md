# AI use and available development record

Date: 2026-10-07. Tools: OpenAI Codex, GPT-6-based assistant (original case); Anthropic Claude, Sonnet 5.5, in Claude Code (later revision: literature-based coefficients, schedule optimization, range analysis, rebuilt report). The precise service build was not independently established. No physical experiment or independent human review is claimed.

The task was to select a classic historical MCM problem and build a rigorous, professional case from it. The conversation wording is not reproduced here.

The assistant selected the problem, read official requirements and source material, derived the models and proofs, authored the model and report-building code, executed the mathematics, prepared figures, interpreted the results, and composed the report and bilingual case guides. A sub-agent authored the independently assembled RHS and numerical validation code; this was an AI-assisted division of work, not a second human reviewer.

Available outputs are the report itself, `reproduce/code/model.py`, `reproduce/code/validate.py`, the report builder, and the archived JSON/NPZ result and check records. Full chat export and every intermediate output are not included. This is a scope-and-artifact disclosure, not a reconstructed complete transcript.

Corrections retained in the process: the first baseline coefficients (surface 18, shell 5, body 12 W/(m² K)) and the 40.5°C upper limit were replaced after a literature-based derivation showed them at the low end of the range and the finer mesh rejected the limit; the baseline water amount rose from 10.48 L to 24.14 L as a result. A time-varying schedule found by constrained optimization (19.77 L) was added because the constant-rate family left the gap to the energy bound open. The correlations were checked against web summaries, not the textbook, and the immersion study was read as an abstract only.

Earlier corrections: an initial 38°C floor needed no replenishment; a stricter scenario with weak mixing had no accepted candidate; the claim that flow necessarily improves every cell monotonically was removed; a continuous-time derivative envelope rejected the initial 0.01°C reserve, which was increased to 0.03°C and verified. The numerical pipeline also rejected a run whose reviewed files changed during execution. Accepted evidence came from a subsequent unchanged-source run.

The PDF appends its own Report on Use of AI Tools and cites AI participation. This file is a development record outside the single-file submission, not a required second attachment. It does not claim that the unavailable interaction transcript was exported or reviewed.
