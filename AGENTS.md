# Developing Praxis

This is the public plugin source, not a user modeling workspace. Start with [CONTRIBUTING.md](CONTRIBUTING.md) for boundaries, verification and export commands. Read the current branch, HEAD, working tree and relevant handoff before editing; preserve other agents' effective changes.

- Follow one concrete issue through its implementation, callers, evidence and public claims. Reproduce suspected defects before changing behavior; distinguish confirmed failures from hypotheses.
- Keep authority where it belongs: method and change reasoning in `references/methods.md`, execution contracts in `references/automation.md`, material exposure in `references/learning-loop.md`, figure selection in `references/visualization.md`, typography in shared templates, and original-year delivery requirements in contest profiles. Reference these sources rather than duplicating rules.
- Use `uv run --locked` or the existing `.venv/bin/python`. Run focused independent-answer/boundary checks first, then necessary integration checks. Do not install large dependencies or rerun expensive research just to refresh a hash.
- Frozen cases retain their actual source, inputs, environment and evidence. A changed validator does not retroactively certify old results. Record revisions and failed attempts; never silently substitute an old success after a new failure.
- Modify figure/report generators, rebuild affected artifacts and inspect their actual output. Check linked numbers, conditions and conclusions; compilation and matching hashes alone do not establish correctness.
- Save a concise handoff with the exact version (including uncommitted differences), commands, outcomes, remaining uncertainty and next action in the project's existing record. Keep private materials outside this source. Do not publish without authorization.

Useful entry points: `scripts/pipeline.py` (runs and stale evidence), `modeling/` (mathematical contracts), `tests/` (regressions), `scripts/build_plugin.py` (explicit export). Research archives have their own README and reproduction entry; inspect their configuration and audit before interpreting a failed check. A short same-input replay can distinguish a model error from inconsistent comparison conditions.

For plugin use rather than development, start at [SKILL.md](SKILL.md); this developer navigation is not part of the runtime skill payload.
