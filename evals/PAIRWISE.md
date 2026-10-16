# Same-problem pairwise evaluation

This protocol measures whether a judge prefers official O-labelled manuscripts over M/H-labelled manuscripts for the same MCM problem. It produces relative comparisons and descriptive evidence. It does not assign an absolute award, certify correctness, or estimate a real probability of winning. The program prepares files and analyses returned judgments; it never calls a model.

The private corpus, award bindings, anchors, access grants and exposure records belong in the user's workspace. Public source contains only this protocol, the script and synthetic tests. Do not use previously reused papers, protected problems, or non-candidate records. A fresh context does not erase project exposure or establish pretraining isolation.

## Preparation and input binding

Run from the public source with its locked environment. Paths below refer to a separate private workspace. Keep the answer key outside the coordinator bundle and every judge input. The bundle produced by `make-pairs` is coordinator-only: its complete comparison graph leaks group roles even when awards are omitted. Never expose that directory to a judge. Directory separation is necessary but does not provide filesystem access isolation; the coordinator must restrict the judge's actual available files/tools and record whether that restriction was tested.

`make-pairs` accepts the private schema-1 index with a `papers` array. Only entries with `use: evaluation_candidate` and `award: O`, `M`, or `H` are eligible. `excluded_reused`, F/S and other records are excluded before their file paths are opened. Each candidate requires `problem` (`MCM-YYYY-A/B/C`), matching `year`, digit-only `team`, `award`, `local_path`, `sha256`, and `version` (`original_submission`, `journal_edited`, `unknown`). Optional `school`, `institution`, and `school_aliases` improve identity redaction. Hashes bind the actual local PDF bytes, not the original submission identity.

The preregistered corpus target is 10 problems with two O plus three M/H each; the minimum is eight problems, at least two A, two B and two C problems, with at least two O and two M/H per problem. The script rejects a corpus below this minimum. Reaching the minimum does not mean reaching the full target. Do not change thresholds to turn a failed run into a success.

Pass a separate `--contexts` JSON containing `schema: 1` and `problems`. Every selected problem needs an explicit binding, for example:

```json
{
  "schema": 1,
  "problems": [{
    "problem": "MCM-2014-A", "year": 2014,
    "statement": {"path": "contexts/2014-A-statement.txt", "sha256": "ACTUAL_SHA256", "problem": "MCM-2014-A", "year": 2014, "completeness": "complete", "limitations": []},
    "rules": {"path": "contexts/2014-rules.txt", "sha256": "ACTUAL_SHA256", "contest": "MCM", "year": 2014, "completeness": "complete", "limitations": []},
    "anchor": {"path": "anchors/MCM-2014-A.md", "sha256": "ACTUAL_SHA256", "problem": "MCM-2014-A", "year": 2014, "anchor_level": "generic", "completeness": "partial", "limitations": ["Generic guidance; no original-year problem-specific commentary"]}
  }]
}
```

All three resources must be nonempty UTF-8 text and explicitly declare `completeness` (`complete` or `partial`) and a `limitations` array. Partial original-year statements/rules produce a concrete preparation packet with `ready_for_formal_eval: false`, selected/complete-context problem counts, and per-problem blockers. They are not silently dropped and never replaced with current rules. The packet remains available for reviewing anonymous word counts and budget; any formal use of incomplete historical rules needs the coordinator to present those limitations in the user approval decision. Generic partial anchors remain usable with their limitations. Optional `source_url` and `source_sha256` are preserved in judge inputs; local `source_file` paths and full private bindings stay in the key. The coordinator must verify their real correspondence to the problem and historical contest year. Field matching and SHA256 checks alone cannot establish that correspondence. Use the original-year rules; never silently substitute current rules. The complete statement must include the relevant task text, rather than a guessed summary. Anchors have three to five priorities, common weaknesses and core subquestions, within 40 lines, paraphrased from the authorised source. Use `official` for the same-year problem's Judges' Commentary, `member` for authorised member material, or `generic` for the original problem plus public general guidance. Record source provenance privately and report these levels separately. A missing historical rules resource, statement or anchor, a mismatched year/problem, or a bad hash is **pending preparation** and is rejected before manuscript text extraction. A real, correctly bound partial historical resource is preserved as partial, rather than passed off as complete or rejected by a newly invented completeness threshold.

```bash
uv run --locked python -m scripts.pairwise_eval make-pairs \
  --workspace /absolute/private-workspace \
  --index /absolute/private-workspace/data/study/judge-corpus/index.json \
  --contexts /absolute/private-workspace/data/study/judge-corpus/contexts.json \
  --packet /absolute/private-workspace/.session/c3/coordinator/bundle \
  --key /absolute/private-workspace/.session/c3/secrets/key.json
```

The key must be outside `--packet`; a descendant path or symlink into the bundle is rejected. The coordinator must also ensure that neither the bundle nor key is in a judge's actual accessible file/tool scope. Fresh destinations are required, so rerunning cannot overwrite an old packet, key or result. An interrupted partial preparation is retained for diagnosis. Save command output, failures and actual exposure in the existing private records. Do not declare a real review before it occurred.

The original problem can include maps, tables or figures that plain text does not preserve. For an authorised, verified **single-problem** original statement PDF, supply `statement.source_file`, its actual `source_sha256`, and `source_scope: single_problem` (or an explicitly matching `source_problem`). The script validates the source hash before manuscript extraction, retains a verified coordinator copy, then exports only `problem-original.pdf` beside a singleton comparison. Its request explicitly asks the judge to inspect the original maps/figures and question labels. The judge metadata contains only the local filename, source URL/hash and declared limits, never the original local path.

HTML, multi-problem sources and PDFs whose single-problem scope is unknown are not copied. Scope is an upstream source fact that the coordinator must verify; a filename alone does not prove it. No network retrieval occurs. Do not attach manuscript source PDFs or an entire contest's collection. A graphical statement supplement does not upgrade declared partial historical rules or missing data attachments to complete; their original status and limits remain visible. A bad source hash or tampered coordinator copy causes rejection.

## Anonymous texts, pairs and judge inputs

All candidate manuscripts explicitly use `scripts/pdf_text.extract_pages(..., text_backend="pdfium")`, including standard CJK mapping support, then receive the same page/L-number plain-text representation. A different or mixed backend is rejected instead of silently falling back. The shared extractor's default `auto` keeps its existing pypdf / CJK-PDFium selection and return values for other callers; effective-font measurement is unchanged in both modes. Invalid backend names are rejected before the PDF is opened. Redaction covers NFKC-normalised and separated team-number variants, school/institution lines, common identity headers, repeated page-edge lines, award banners, and acknowledgment sections. Optional school aliases are matched without case sensitivity. The private key records word counts, redaction counts, sparse pages, extraction limitations, version and labels. Each paper records requested and actual text backends and page count; the key and `make-pairs` receipt also aggregate actual backend counts and state the extractor limits. Using one backend reduces selection differences between award groups but does not certify that every glyph, equation or reading order is correct. Retain earlier preparations when changing extraction and create a fresh coordinator bundle; do not overwrite old text hashes or rebind old judgments to the new extraction. Anonymous text hashes and context hashes are checked when a packet is consumed.

The three observed publisher markers `校苑数模`, `微信公众号` and `获取更多资讯` are removed uniformly from every candidate, with occurrence counts in `redactions.publisher_markers`. Only those exact strings are removed, including when attached to scientific text; the remainder of the line is retained and an empty remainder is skipped. This does not introduce a general CJK, URL or paragraph filter; scientific text and ordinary reference URLs remain subject to the existing identity/header checks.

This is heuristic text anonymisation. Figures, layout, some mathematics, raster content and names without a recognisable identity marker can be lost or missed. No OCR is performed. The coordinator must inspect leakage and extraction quality before giving a packet to a judge; retain failures or excluded/unreadable manuscripts explicitly. Do not claim perfect anonymity from this script. Do not silently replace a selected paper after seeing its judgment.

For each problem the program builds **all O-versus-M/H pairs**, one randomly selected O-versus-O pair, and one randomly selected M/H-versus-M/H pair. These pair types and the complete graph remain coordinator-only. In the target two-O/three-MH design, the O papers have degree four, while M/H papers have degree two or three; a complete anonymous graph therefore reveals all group roles. A single-pair directory is the mandatory judge input boundary, not an optional view over a shared full packet.

Blinding uses `SystemRandom` and cryptographically unpredictable document/pair/presentation tokens. The public statistical seed `20261016` controls the external sample and bootstrap, **never blinding**. The key seals the actual identities, random control choices, left/right placement, local A/B mappings, and two unrelated presentation tokens per pair. Same statistical seed does not reproduce these choices; reproduce an existing experiment from its saved private choices. No generation counters, public seeds, group sizes, control categories, stable cross-pair document IDs or full index are exported to judges.

`judge-packet` **requires exactly one `--pair-id`** and exports only that comparison. Its `pair.json` contains the opaque pair/presentation IDs, key SHA256, problem, two local aliases, content hashes and that problem's context limitations. The files `A.txt` and `B.txt` are local to the pair; the normal presentation shows A/B and the swapped presentation B/A. Repeated manuscripts receive different local identities in other pairs. There is no `pairs.json`, population summary or selection record in a judge directory.

Give **each pair two fresh GPT contexts**, with distinct `judge.id` values (for example `gpt-one` and `gpt-two`), distinct actual `judge.instance` identifiers, and opposite presentation orders. A context identifier cannot be reused across different pairs. Keep merged outputs in the coordinator area, outside judge inputs. This changes both instance and order; it does not isolate an order effect. A separately identified repeat of one fixed judge can measure same-instance order stability, but cannot fill the two-fresh-instance plan.

```bash
uv run --locked python -m scripts.pairwise_eval judge-packet \
  --packet /absolute/private-workspace/.session/c3/coordinator/bundle \
  --output /absolute/private-workspace/.session/c3/judges/gpt-one \
  --judge-id gpt-one --family GPT --instance ACTUAL_PAIR_FRESH_ONE --pair-id OPAQUE_PAIR_ID_FROM_COORDINATOR
uv run --locked python -m scripts.pairwise_eval judge-packet \
  --packet /absolute/private-workspace/.session/c3/coordinator/bundle \
  --output /absolute/private-workspace/.session/c3/judges/gpt-two \
  --judge-id gpt-two --family GPT --instance ACTUAL_PAIR_FRESH_TWO --pair-id OPAQUE_PAIR_ID_FROM_COORDINATOR --swap
```

A judge's context must not load Praxis `references/` or the coordinator key. Its fixed question is: Which manuscript is closer to the O level for this problem and year? It must choose `left`, `right`, or an explicit `abstain`; give confidence in `[0.5,1]`; and provide exactly three reasons, each with specific locations in both texts. An extraction failure is grounds for abstention. Keep the complete output and actual model/family/instance identity. The program checks nonempty locations, not whether they are truthful citations.

```json
{
  "schema": 1, "key_sha256": "ACTUAL_KEY_SHA256",
  "judge": {"id": "gpt-one", "family": "GPT", "instance": "fresh-one"},
  "judgments": [{
    "pair_id": "OPAQUE_PAIR_ID", "presentation_id": "OPAQUE_PRESENTATION_ID", "left": "A", "right": "B",
    "preferred": "left", "confidence": 0.7,
    "reasons": [
      {"left_location": "page 001 L00004", "right_location": "page 001 L00008", "reason": "Actual comparison"},
      {"left_location": "page 003 L00091", "right_location": "page 004 L00102", "reason": "Actual comparison"},
      {"left_location": "page 010 L00305", "right_location": "page 012 L00346", "reason": "Actual comparison"}
    ],
    "mechanical_findings": []
  }]
}
```

The three review roles connect as follows:

| Role | Bound input and output | Consumer |
| --- | --- | --- |
| `mechanical` | Actual PDF/TeX, results and declared metadata; the C2 scripts return scoped findings with status and locations. | Keep the original diagnostic JSON/hash. A full judge may cite an actual finding in `mechanical_findings`, identifying its source and limits. |
| `reader` | The reader packet and quoted problem items; one fresh reader returns `answer_found`, `answer_one_line`, `why_credible` and `top_question` per item. | Preserve the reader JSON/hash. In a full review record, attach its declared contents under `reader`; the existing `evals/aggregate.py` CLI retains that block in both aggregate and user views. |
| `full` | A singleton pair, original problem resources and anchor; two fresh contexts each produce the comparison template above. | Pass the unchanged pairwise outputs to `fit` and `agreement`, with the private key supplied only to the coordinator. Retain each judge's reasons, citations, instance and actual inputs. |

`fit` never converts findings, severity, reader answers, a diagnostic score or confidence into a preference. Mechanical and reader results cannot fill a missing full judgment. Their presence does not turn a partial historical context into a complete one.

The existing whole-manuscript aggregator also preserves an optional `comparison` object/list and each issue's declared `severity`, associated with the original `review_id` and reviewer. That whole-review format uses `self` / `reference` / `tie` with textual reasons; pairwise results use pair-local A/B, presentation tokens, `left` / `right` / `abstain`, and locations in both texts. Keep the formats distinct: there is no implicit A/B-to-self conversion, and an abstention cannot become a tie. The coordinator may link the unchanged pairwise result and its hash from the review record; any explicit summary must identify the manuscript mapping and retain the source. Aggregate competition scores carry `diagnostic_only: true`; none of these blocks generates an award estimate.

## Estimation and uncertainty

```bash
uv run --locked python -m scripts.pairwise_eval fit \
  --key /absolute/private-workspace/.session/c3/secrets/key.json \
  --results /absolute/private-workspace/.session/c3/judges/gpt-one/judgments.json \
            /absolute/private-workspace/.session/c3/judges/gpt-two/judgments.json \
  --output /absolute/private-workspace/outputs/pairwise-fit.json
```

The key preregisters `planned_judgments_per_pair: 2` and `planned_family: GPT`. Accuracy uses every **observed planned-family** O-versus-M/H judgment as its denominator; missing judgments are never silently counted as observed. Abstention is not a correct identification; conditional accuracy among decided judgments and decision coverage are also shown. Same-award controls are excluded from accuracy but contribute to the comparison graph. Confidence is descriptive and is not a fit weight. The `coverage` report compares observations with the entire sealed plan, including cross-award and both control types. It lists planned, observed, effective and missing counts; completion fraction; each pair's distinct judge IDs, fresh instances and opposite-order status; repeated identifiers; contexts reused across pairs; excess judgments; and counts by kind and judge ID. External-family judgments do not fill planned GPT slots. Exact duplicate instance/order records are rejected; repeated IDs or the same context in two orders are reported and do not satisfy the fresh-instance plan. More than two eligible judgments per pair also prevents silently choosing a favourable subset.

For incomplete plans, `status` is `incomplete_observed_subset`, the accuracy/CI/BT estimates explicitly describe only observed data, and both C3.7 accuracy/CI pass fields are **null**, even if observed accuracy is 1 and its bootstrap interval is `[1,1]`. `complete_preregistered_coverage` must be true before either numerical gate can be evaluated. Missing controls count as incomplete. The 0.70 / lower-bound-above-0.5 thresholds are unchanged. True freshness and model provenance still require external execution evidence; declared IDs alone cannot establish them. For coordinator-merged files, an optional nonempty `fresh_instance` per judgment supplies its actual context ID; otherwise the enclosing `judge.instance` is used. Show separately described per-judge subset estimates alongside the complete pooled result, without treating those partial fits as full-plan acceptance.

Bradley–Terry uses `P(i preferred to j) = logistic(score_i - score_j)`. The graph has no comparisons between problems. The implementation therefore fits each problem separately and centres its scores at zero; absolute rankings between different problems are not identified. Default `--ridge 1.0` minimises the negative log likelihood plus `ridge * sum(score²) / 2`. It is explicitly called **penalized_BT**. The parameter, optimiser outcome, gradient, connected components and separation status are reported. Separated data do not have a finite unpenalised MLE; `--ridge 0` reports `no_finite_identifiable_MLE` instead of reporting diverging values as convergence. Isolated papers have null scores. Penalty-dependent comparisons across disconnected components are flagged.

The O-minus-M/H difference is the difference of the two paper-weighted group means of available, within-problem-centred scores. It is descriptive under the stated ridge. Both accuracy and this difference receive 95% percentile intervals from **1000 bootstrap samples of whole problems**, with replacement, fixed seed `20261016`. Papers and repeated judgments stay together in their problem. Separate per-problem BT fits do not change when a whole cluster is duplicated, so bootstrap replicates resample those fitted score sets with cluster multiplicity. The independent sampling unit is the problem, not a pair or judgment. A single informative problem receives no interval; fewer than eight informative clusters are exploratory; point intervals are marked degenerate. Empty or all-abstention inputs cannot produce successful BT evidence.

Accuracy is also reported by problem, anchor level and the pair's version combination. Length preference is the descriptive Pearson and Spearman correlation between left-minus-right anonymous word count and choice of left. Constant/no-data cases return null with a reason. This association can expose a length preference but is not a causal effect; papers and judgments repeat and no independent-observation p-value is reported.

## Cross-family export and agreement

```bash
uv run --locked python -m scripts.pairwise_eval export-packet \
  --packet /absolute/private-workspace/.session/c3/coordinator/bundle \
  --output /absolute/private-workspace/.session/c3/judges/external16 \
  --judge external
uv run --locked python -m scripts.pairwise_eval agreement \
  --first /absolute/private-workspace/.session/c3/judges/gpt-one/judgments.json \
  --second /absolute/private-workspace/.session/c3/judges/external16/judgments.json \
  --output /absolute/private-workspace/outputs/family-agreement.json
```

Before any judgment, `make-pairs` freezes exactly 16 distinct external pairs from the **whole** pair population, stratified by problem with seeded shuffled round-robin sampling without replacement. Each problem is represented before another round; controls remain eligible. The selected IDs, seed and method are sealed in the private key and coordinator bundle. `export-packet --judge external` must use that frozen seed; it cannot resample after observed results. Fewer than 16 pairs or more than 16 problems is rejected, without padding.

The external export contains 16 opaque subdirectories. **Each subdirectory alone** is a self-contained single-pair judge input, with local A/B files, context provenance/limits, request and blank result. It has no full graph, stable cross-pair manuscript identifier, seed, selection record, group counts, labels or original paper paths. The parent directory is a transfer container for the human coordinator; do not give it or its siblings to a judge context. Use new Claude contexts for the individual pairs, rather than the adviser conversation. Record the export command's selection receipt privately; do not add it to judge inputs. Export neither sends a message nor runs a review.

Text itself can identify repeated manuscripts if multiple pairs are pooled in one context, or if a judge has previous exposure. Pair-local aliases cannot prevent content recognition, and independently reviewing a singleton cannot prove that the model never saw its text. Report the actual isolation and exposure conditions. Statement/rules/anchor source URLs, source hashes and resource limitations remain visible as context provenance, not paper labels.

`agreement` compares the shared opaque pair IDs and pair-local manuscript aliases. A/B denote the same manuscript within a sealed pair across its two presentation orders; they do not identify manuscripts across other pairs. `fit` also validates each returned presentation token and A/B order against the private key before resolving global manuscript identities. Preferences are normalised to the chosen manuscript identity, so opposite display sides are handled correctly. It reports coverage/unmatched pairs, raw agreement and explicit abstentions. Across different families it reports Cohen's κ, returning null for no observations or a degenerate marginal distribution. Same-family fresh instances are explicitly named **same_family_two_instance_agreement**, with no claim of external independence and no external κ. For each shared pair, actual identity is `(judge.id, judge.family, fresh_instance)`; a row's `fresh_instance` overrides the enclosing `judge.instance`, which remains the fallback for older records. Only matching actual identities for every shared pair receive `same_judge_repeated`. Mixed same/different actual identities receive `same_family_mixed_instance_agreement`, never an overall claim of isolated same-judge order stability. `instance_comparisons` counts matching and differing identities; `swap_stability.same_instance` and `.cross_instance` separately report reversed-order sample counts and identity-normalised agreement. The existing overall reversed-order fraction remains descriptive across the combined observations. Different row instances under identical coordinator batch headers remain cross-instance comparisons. Different family names alone do not establish independent exposure.

## Preregistered acceptance and runtime boundary

C3.7 needs user approval of a concrete token estimate before any real review. Preparing this script or testing synthetic PDFs does not authorise a real-paper review. Estimate pair count × review count × two full anonymous texts plus anchor/statement/rules, add expected outputs, and preserve the proposed budget in the existing C3 status. Do not test statistics by generating labels from real papers.

The predeclared experimental conditions all apply: O-versus-M/H accuracy at least `0.70`; the problem-cluster 95% interval lower bound strictly greater than `0.5`; and GPT-versus-Claude κ strictly greater than `0.4` on the preselected 16-pair subset. Missing Claude judgments mean **not tested**, not passed. `fit` and `agreement` report the components; they do not certify the full experiment's provenance or completeness. Failed criteria remain failed; report strata, retain all failures, and use a new problem set in a later round rather than changing the rules and repeating the same set. Put the discrimination table first in the eventual real-run report, and engineering receipts separately.
