# CUMCM Demo: Investment Return and Risk

**1998 CUMCM Problem A: a portfolio problem with minimum transaction fees, taken from model and proof through robustness checks to a paper others can verify.**

[中文](README.md) · [Full paper (PDF, Chinese)](deliverables/paper.pdf) · [Supporting archive (ZIP)](deliverables/supporting_materials.zip) · [Reproduction code](reproduce/) · [Back to Praxis](../../README.en.md)

![Risk–return curves for the two asset sets, with representative portfolios](assets/risk-return.png)

## What the problem asks

A firm has a sum M and can buy any of n assets or put money in a bank (5% a year, riskless, no fee). Each asset has an average return, a loss rate and a fee rate; a purchase below a threshold is still charged as if it were at the threshold. Overall risk is the largest loss among the assets bought. The statement supplies one set of 4 assets and one of 15, and asks for portfolios with high net return and low risk.

The difficulty is not computation. It is three things: the fee is piecewise, two goals must be traded off, and the problem never says how much risk the firm accepts.

## Results first

| Case | Risk cap | Best net return | Supporting argument |
|---|---:|---:|---|
| 4 assets | 1% | **21.90%** | MILP solve, enumeration of fee regimes, analytic upper bound |
| 15 assets | 10% | **33.53%** | MILP solve, analytic upper bound |

Capital is **CNY 1,000,000**; risk is the largest asset-level loss amount divided by capital; net return is after fees. The two risk caps differ, so the rows do not rank the asset sets, and neither is a forecast of real returns. With no stated risk appetite the paper recommends the knee of the return–risk curve: a 0.6% cap for 4 assets (20.19%) and 8% for 15 assets (32.29%).

## How it is solved

1. **Read the statement into a model.** Zero fee when nothing is bought, otherwise the larger of the amount and the threshold, times the fee rate; bank balance, principal and fees share one budget.
2. **Mixed-integer linear program.** A binary variable switches each asset on; maximize net return under a risk cap and sweep the cap to trace the return–risk curve.
3. **An independent argument.** Dropping the minimum fee gives a proportional-fee relaxation whose analytic bound cannot be below the original optimum; a feasible plan that reaches it is globally optimal. The 4-asset case is also checked by enumerating 81 fee regimes.
4. **Capital scale.** A sufficient condition: once capital covers every active threshold, the original problem attains the relaxed bound. At the representative caps this is **CNY 339 and CNY 2,602**. It is sufficient, not necessary.
5. **Recommendation and robustness.** The knee is the recommendation without preferences; then test whether it can be executed as written and whether it survives data error.

## Evidence

- **12 model checks** cover constraints, fees, boundaries and parameter scenarios, plus 4 capital-threshold checks and 2 knee checks. They are different kinds of check, not 12 independent algorithms.
- **The recommended plan uses the whole risk cap, so following it loosely breaks the cap.** With ±5% error on each amount, about nine in ten random trials exceed the cap (median overshoot 2–3%). With ±10% error on every data field the same assets are chosen in over 99.5% of trials. The margin to keep is therefore on risk: tightening the cap by 5% costs only about 0.3–0.6 points of net return.
- **How far simple rules go.** At CNY 1,000,000, greedy by the per-budget gain from the paper's Proposition 2, buying each asset up to its risk allowance, matches the integer optimum in all six cases tested: the minimum fee is inactive at this scale, and the integer model matters at small budgets. Ranking by return over risk loses up to 4.3 points; equal weights reach only 11.8% and 22.0%.
- **Every chosen asset matters.** Removing any one lowers net return noticeably.
- **The risk definition changes the answer.** Reading risk as a standard deviation with independent returns, the same caps give net returns of only 13.4% and 17.4%, and the stated max-loss knee portfolios carry several times the cap under that reading. The paper answers as stated and flags this as something to confirm with the decision maker.

## Two pages of the paper

<table>
<tr>
<td width="50%"><a href="deliverables/paper.pdf"><img src="assets/report-abstract.png" alt="Report page 1: abstract and quantitative results" width="100%"></a></td>
<td width="50%"><a href="deliverables/paper.pdf"><img src="assets/report-proof.png" alt="Report page 7: proof of the analytic bound and certificates" width="100%"></a></td>
</tr>
<tr>
<td><strong>Abstract: problem, method, result</strong><br>States the risk definition, fee treatment and representative numbers.</td>
<td><strong>Argument: from computation to proof</strong><br>The analytic bound, an exchange argument and the capital condition.</td>
</tr>
</table>

**[Read the complete 19-page paper →](deliverables/paper.pdf)** Typeset with XeLaTeX: ctex for Chinese, a Times family for Latin text and equations, and figures drawn by pgfplots straight from the data. Level-1 headings are centered, figure captions sit below figures and table captions above tables. The body has no table of contents, and the appendix lists the supporting files and the full source code, as the 2026 CUMCM format rules require; the rules leave fonts and sizes free.

## Run it yourself

From the Praxis repository root:

```bash
uv sync --locked
uv run --locked python demos/cumcm-1998-a/reproduce/run_demo.py                 # both asset sets, curves and the 12 checks
uv run --locked python demos/cumcm-1998-a/reproduce/check_capital_threshold.py  # capital threshold (4 checks)
uv run --locked python demos/cumcm-1998-a/reproduce/check_recommendation.py     # knee and analytic bound
uv run --locked python demos/cumcm-1998-a/reproduce/check_robustness.py         # execution error, margin, data error (seeded)
uv run --locked python demos/cumcm-1998-a/reproduce/check_alternatives.py       # simple rules, drop-one, alternative risk reading
```

The whole set takes a few minutes. Results go to `reproduce/reproduced/`, excluded from Git; the first script will not overwrite an existing results folder. You can also unzip the [supporting archive](deliverables/supporting_materials.zip) and reproduce the paper's computation on its own, with no Praxis and no AI service.

## File map

```text
deliverables/                 # the two electronic submission files
  paper.pdf                   # 19 pages, with file list and full source appendix
  supporting_materials.zip    # 25 files, including the LaTeX sources and AI-use details
reproduce/                    # entry points, archived numbers and check scripts
assets/                       # images for the homepage and this page
manifest.json                 # bytes, MD5 and SHA-256 of the two deliverables
verification.json             # acceptance record
```

Only the PDF and ZIP belong to the submission; previews, notes and hashes stay outside. The PDF was rendered and reviewed page by page, the ZIP was extracted and rerun independently, and the appendix list matches its members.

## Sources, limits and license

- The problem and its two parameter tables come from the organizers' [official collection of past problems](https://www.mcm.edu.cn/upload_cn/node/1/SkAh1A7Q6f2dd01e58aa621f920e79f45cd5d255.pdf), page 11; only the parameters needed to reproduce and their provenance are included.
- Paper and attachments follow the [2026 format rules](https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html); the AI statement follows the [2026 AI-use rules](https://www.mcm.edu.cn/html_cn/node/fef94648f2836ab6cc81586f4c38512b.html).
- The solution, code, figures and paper were made for this project. They are not an official answer, a prize-winning paper or a real contest result; AI involvement and verification are recorded truthfully in the supporting archive.
- This case validates one conditional optimization model and the delivery chain; it does not claim arbitrary problems finish automatically.

Implementation, documents and figures are under the repository's MIT license; problem parameters keep their stated origin and third-party tools their own licenses. No private contest material is included.

If this case helps you, a **Star on Praxis** is welcome, as are issues with a concrete question and a reproduction.
