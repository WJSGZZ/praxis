<div align="center">

<img src="demos/assets_src/praxis-logo.png" alt="Praxis：向未知延伸的开放曲线" width="160">

# Praxis

### 让 AI Agent 成为你的数学建模伙伴。

读懂题目，建好模型，把结果写成一份有依据的报告。

[![Version](https://img.shields.io/badge/Version-0.3.0-263B9B?style=flat-square)](CHANGELOG.md)
[![Agent Plugins](https://img.shields.io/badge/Agent_Plugins-1.0-302B31?style=flat-square)](https://agent-plugins.org/specification)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square)](pyproject.toml)
[![Paper](https://img.shields.io/badge/Paper-LaTeX-C8533B?style=flat-square)](templates/)
[![License](https://img.shields.io/badge/License-MIT-302B31?style=flat-square)](LICENSE)

**简体中文** · [English](README.en.md)

[数学建模案例](#两个完整案例两种建模问题) · [快速开始](#快速开始) · [技能](#技能一览) · [工具](#数学工具) · [兼容](#agent-兼容) · [可靠性](#可靠性)

</div>

**Praxis 是面向通用数学建模的 Agent 插件**：七个技能（一个负责整题，六个各管一类请求）加一组可直接调用的数学工具，并带着证据工作流。它帮助个人或团队从问题和数据出发，完成**模型、核验和报告**；也可以只用于分析问题、审查模型、验证结果或改进论文。

研究、课程、比赛，以及资源分配、环境分析、公共服务和工程决策等现实问题，都可以使用这套工作方式。先明确目标、约束与数据，再建立可解释的基线，按需要增加复杂度；遇到陌生问题，先找出它背后的数学结构，比较几条不同的路线并留下记录；没有标准答案时，用猜想、反例和高精度检验产出带把握等级的结论；让需求、计算、验证和报告中的结论彼此对应，减少整理、重复计算与协作交接的负担，把精力留给关键判断。

不需要先会写全部代码：你可以用日常语言质疑模型，Praxis 将疑问转成可检查的情景，并记录实际采纳与修改。写作按中文、英文各自的表达习惯处理；赛事评估先讲奖项档次、依据与改进价值，诊断分用于内部定位。目标是更有竞争力的作品，先形成完整交付，再深入值得改进的关键问题。

<table>
<tr>
<td width="33%"><strong>完成优先</strong><br>先形成基线和完整稿，再按剩余预算改善。</td>
<td width="33%"><strong>证据贯穿</strong><br>任务、结果、独立检查和论文位置相互对应。</td>
<td width="33%"><strong>按团队适配</strong><br>根据实际人数、能力和可用时间安排责任与交接。</td>
</tr>
</table>

## 两个完整案例，两种建模问题

国赛与美赛是展示完整流程的两个 Demo，代表不同的问题类型，项目能力不以这两项赛事为边界。两份案例都按完整交付标准组织：从题目分析、模型与验证，到论文和复现材料；你可以从更感兴趣的问题进入。

<table>
<tr>
<td width="50%" valign="top"><strong>国赛 · 投资的收益和风险</strong><br>1998 CUMCM A</td>
<td width="50%" valign="top"><strong>美赛 · A Hot Bath</strong><br>2016 MCM A</td>
</tr>
<tr>
<td width="50%" valign="top"><a href="demos/cumcm-1998-a/README.md"><img src="demos/cumcm-1998-a/assets/overview-zh.png" alt="国赛案例：两组资产的风险上限与最优净收益率" width="100%"></a></td>
<td width="50%" valign="top"><a href="demos/mcm-2016-a/README.md"><img src="demos/mcm-2016-a/assets/overview-zh.png" alt="美赛案例：空间水温、补水策略与能量证据" width="100%"></a></td>
</tr>
<tr>
<td valign="top"><strong>费用门槛怎样改变最优投资？</strong><br>分段费用与风险约束进入同一个模型，通过费用分区穷举和解析上界核验方案。</td>
<td valign="top"><strong>平均水温够高，远处的水也够暖吗？</strong><br>从可证明的完混基线进入三维热网络，比较补水策略、空间温差与能量下界。</td>
</tr>
<tr>
<td valign="top"><strong>23 页中文报告 · 12 项模型检查</strong><br>资金 100 万元时，四资产风险上限 1% 下的净收益率为 21.90%；十五资产风险上限 10% 下为 33.53%。</td>
<td valign="top"><strong>26 页英文报告 · 17 项模型检查</strong><br>30 分钟基准情景中，最佳恒定流量补水 24.14 L，带余量的六段方案 21.48 L（少约 11%），理想完混 16.01 L，能量下界 15.41 L。系数由教材关联式推导，并给出取值范围。</td>
</tr>
<tr>
<td valign="top"><strong>论文 PDF + 支撑材料 ZIP</strong><br>完整代码与复现证据在案例页开放。</td>
<td valign="top"><strong>一份论文 PDF</strong><br>复现代码与证据单独开放，论文内附一页使用者说明及 AI 披露。</td>
</tr>
<tr>
<td valign="top"><a href="demos/cumcm-1998-a/README.md"><strong>查看完整国赛 Demo →</strong></a><br><a href="demos/cumcm-1998-a/deliverables/paper.pdf">阅读论文</a> · <a href="demos/cumcm-1998-a/reproduce/">复现计算</a></td>
<td valign="top"><a href="demos/mcm-2016-a/README.md"><strong>查看完整美赛 Demo →</strong></a><br><a href="demos/mcm-2016-a/deliverables/7391856.pdf">阅读论文</a> · <a href="demos/mcm-2016-a/reproduce/">复现计算</a></td>
</tr>
</table>

**[更多案例 →](demos/README.md)** 从组合计数与开放数学探索，到有完整证据的决策研究。

论文由共享版式源生成：国赛、美赛分别适配，数学研究稿使用 [AMS 风格模板](templates/research-paper.tex)。固定编译环境、样式漂移检查和三系统排版 CI 用来维持一致；章节与图按论证需要选择，最终仍检查实际 PDF。图由有效数据生成，使用 PGFplots/TikZ 矢量绘制，复杂数值场可按需求使用成熟科学绘图库。

如果你也希望把建模推进到一份可核查的完整作品，欢迎 **Star Praxis**，或先用下面的方式试一次。

## 快速开始

### 1. 选择你的 Agent

**安装完整插件：七个技能 + 数学工具 + 证据工作流。** 从公开仓库获取源码，按宿主生成安装包：

```bash
git clone https://github.com/WJSGZZ/praxis.git
cd praxis
uv run --locked python -m scripts.build_plugin --host codex --output ../praxis-dist/codex/praxis
```

将 `codex` 换为下表中的目标，输出到新的目录，再按对应指南安装：

| Agent | 导出目标 | 安装入口 |
|---|---|---|
| Codex | `codex` | [本地 marketplace → 安装插件](references/installation.md#codex) |
| Claude Code | `claude` | [插件 marketplace](references/installation.md#claude-code) |
| Gemini CLI | `gemini` | [原生扩展](references/installation.md#gemini-cli) |
| GitHub Copilot CLI | `copilot` | [本地插件安装](references/installation.md#github-copilot-cli) |
| Cursor | `cursor` | [本地插件目录](references/installation.md#cursor) |

**[查看完整安装指南 →](references/installation.md)**　只需要方法指导？也可以[仅安装技能](references/installation.md#仅安装技能)。

### 2. 准备计算环境

脚本和工具需要 **Python 3.12**、[uv](https://docs.astral.sh/uv/) 和宿主的本地文件／终端能力：

```bash
uv sync --project /path/to/plugin/skills/praxis --locked
```

路径替换为实际安装包中的 `skills/praxis`；只安装技能时使用仓库目录。仅使用分析方法无需准备环境。

### 3. 在你的项目中使用

重载或重新开始会话，确认宿主加载了 Praxis，然后提出任务：

> 使用 Praxis 分析这道题和这些数据，选择合适的路线，推进模型实现、独立验证与报告。

也可以从一个明确的小任务开始：

> 审查我的模型：哪些假设没有依据，哪些结论还缺验证？

> 我们有三个人，请根据成员能力和可用时间安排任务，先完成一份完整报告。

**技能目录保存可复用能力，你的工作区保存题目、数据、案例和论文。** 程序负责执行与追溯，助手负责题意、选择和科学判断。

## 技能一览

一个入口负责整题，六个专项各管一类请求。只想做一件事时，直接调用对应技能，不必走完整流程。

| 技能 | 适合的请求 | 内容 |
|---|---|---|
| [`praxis`](SKILL.md) | “把这道题做完” | 统一主线、任务记录、团队与限时协调、环节交接 |
| [`praxis-model`](skills/praxis-model/SKILL.md) | “这题怎么做？参数怎么定？” | 读题与定义、假设和参数依据、路线与模型选择、可辨识性与优化结构 |
| [`praxis-compute`](skills/praxis-compute/SKILL.md) | “跑一下，保存可复现的结果” | CSV／Excel 审计、原件保全、模型与验证器执行、过期检测、证据索引 |
| [`praxis-verify`](skills/praxis-verify/SKILL.md) | “结果可信吗？结论说过头了吗？” | 独立检查、界与最优性、敏感性、证据与结论强度审查 |
| [`praxis-explore`](skills/praxis-explore/SKILL.md) | “这题属于什么类型”“还有没有别的路”“没有标准答案怎么办” | 结构发现、路径搜索与淘汰、实验数学、经验沉淀；`route_graph` 与结构探测工具 |
| [`praxis-dialogue`](skills/praxis-dialogue/SKILL.md) | “给我讲讲这个模型”“我觉得哪里不对” | 解释模型，把直觉转成检查，复盘结果并保留真实参与记录 |
| [`praxis-report`](skills/praxis-report/SKILL.md) | “写论文、改摘要、查 PDF” | 中英文语言优化、论文与图表、引用及 AI 披露、PDF 检查与交付 |

七个技能共用 [统一方法](references/methods.md) 和同一份任务记录；能力之间的交接见 [能力分工](references/capabilities.md)。

### 比赛是一个使用场景

社会与现实问题、研究、课程和比赛共用建模核心。参赛时，再分别核验该届赛事与学校／赛区要求，配置人数、交付语言、格式、附件、AI 披露和截止时间。

规则按“赛事—赛项—届次”查询[赛事档案](evals/competitions.json)，包括国赛 2026 的 AI 使用细则和研究生赛 2026 的格式、提交及答辩要求；具体交付时再按该届规则检查。

开始时先确认交付目标（竞赛有截止、先做透再收敛、研究、教学）：内部按科研标准做透并设停止规则，再把证据收敛成评委读得懂的论文，做法见[深度工作与竞赛收敛](references/convergence.md)；交稿前有[独立评审协议](references/review-protocol.md)。

单人限时任务默认只给用户一个当前事项，边取得结果边写报告；多人任务按能力和依赖安排主责与复核。通用项目不套用赛事规则。

## 数学工具

`praxis-tools` 把常用方法做成可直接调用的计算工具，输入输出都是 JSON；没有 MCP 的宿主可用 `python -m scripts.mcp_server --call 工具名 '参数'`。哪类问题有现成工具、没有时怎么办，见[能力覆盖地图](references/coverage-map.md)。每个工具都有独立答案的测试：教科书例题、闭式解或暴力枚举。

| 类别 | 工具 |
|---|---|
| 规划与网络 | `solve_lp`（对偶间隙证书）、`solve_milp`（证明界与间隙）、`solve_assignment`、`solve_tsp`（附下界）、`knapsack`（精确）、`shortest_path`、`max_flow`（附最小割）、`min_cost_flow`、`minimum_spanning_tree` |
| 非线性与稳健优化 | `minimize_nlp`（多起点，区分收敛候选与失败可行点）、`robust_lp`（预算型稳健，给出稳健的代价）、`solve_mdp`（精确逆向递推或值迭代） |
| 回归、检验与统计 | `ols_report`（置信区间与诊断）、`compare_models`（对基线的交叉验证比较）、`hypothesis_test`（含效应量与假设提示）、`bootstrap_ci`、`arima_forecast`、`pca_report`、`cluster_report`（含稳定性）、`calibrate_curve`（可辨识性与留出） |
| 评价与权重 | `ahp_weights`（一致性比）、`entropy_weights`、`evaluate_alternatives`（TOPSIS 与权重稳定性） |
| 预测与动态 | `backtest_baselines`（滚动起点基线）、`gm11_forecast`、`sir_simulate`、`sir_fit`（报可辨识性）、`queue_mmc`、`equilibria`（平衡点与稳定性）、`kalman_filter`、`solve_ode`（紧容差复算）、`solve_diffusion`（有限体积，附能量收支）、`solve_layered_diffusion` 与独立的 `layered_diffusion_laplace`、`grid_convergence_index` |
| 决策与风险 | `markov_stationary`、`markov_absorption`、`matrix_game`、`bimatrix_nash`、`eoq`、`newsvendor`、`cvar_portfolio`（情景下最小 CVaR）、`pareto_front` |
| 结构与探索 | `probe_structure`（凸、单调、对称、幂律、守恒量）、`dimensional_analysis`（量纲分析）、`check_total_unimodularity`、`route_graph`（路线记录）、`test_conjecture`、`find_counterexample`、`guess_sequence`、`check_recurrence`（有限核对证明）、`find_relation`、`route_to_lesson`、`lesson_add`、`lesson_search` |
| 不确定性 | `sobol_sensitivity`、`sobol_convergence`、`monte_carlo`（附收敛检查） |
| 数据与文献（均免费） | `audit_data`、`search_literature`（OpenAlex，附免费全文链接）、`find_open_access`（Unpaywall）、`check_references`（对照 Crossref 核对 DOI、题名与年份） |

通用、Codex、Claude 和 Copilot 安装包还接入开源的 [arXiv 服务](https://github.com/blazickjp/arxiv-mcp-server)（Apache-2.0，固定版本），可读预印本全文和 LaTeX 分节、导出 BibTeX。付费期刊论文由工具找合法的免费版本，其余可通过学校图书馆或知网获取。

每种方法什么时候用、必须做哪些检查、常见误用，见 [方法与工具库](references/model-library.md)。常规的 MATLAB 与 R 用法，Python 基本都能覆盖。

## Agent 兼容

同一套建模方法，按宿主生成对应插件或扩展。七个技能与核心计算代码共用，安装清单和路径变量由导出器适配；不必为不同 Agent 维护不同的建模流程。

推荐从[完整插件安装](references/installation.md)开始；仅支持技能的环境仍可使用 [Agent Skills 入口](references/installation.md#仅安装技能)。桌面与 CLI 的本地安装不会自动配置网页会话、云端 Agent 或远程机器。

宿主能力、技能目录、官方依据与实际验证范围见 [兼容说明](references/agent-compatibility.md)。

## 命令行与插件结构

<details>
<summary><strong>命令行：在独立工作区建立案例</strong></summary>

以下命令以 POSIX shell 为例，路径需替换为实际位置：

```bash
BUNDLE="$HOME/.agents/skills/praxis"
WORKSPACE="/absolute/path/to/your/project"

"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" \
  --workspace "$WORKSPACE" init \
  --name example \
  --problem "$WORKSPACE/problem.pdf" \
  --data "$WORKSPACE/data.csv"
```

助手在案例中写好并审核 `model.py` 和 `validate.py`，再执行 `run`。数据、案例与输出默认不进入 Git，项目规则由工作区提供。

完整接口见 [执行契约](references/automation.md)。多轮任务可使用[任务协调](references/workflow.md)：开始时检索本工作区的相关经验，随后给出一个当前行动，将预算、最新证据、审阅和报告连接在同一份接续记录里。失败与过期结果会阻断交付；已经能交稿，也可明确选择继续改善。模型选择和科学审阅仍由助手完成。

交付后如需复盘问题，可使用[运行反馈](references/feedback.md)：记录实际阶段、评审、修订和停止原因，按明确清单生成本地分享副本。目录与 ZIP 共用只读检查，不自动上传；模型身份、费用和聊天记录拿不到时保留未知。反馈包帮助定位问题，不能代替研究正确性或完整交付的验收。

</details>

<details>
<summary><strong>插件包的结构</strong></summary>

导出目录按 [Agent Plugins 1.0](https://agent-plugins.org/specification) 组织，这一版规范包含的两类组件都有：

```text
praxis-plugin/
  plugin.json
  mcp.json                  # 核心工具与适用的外部服务
  .codex-plugin/            # Codex 兼容入口
  # 其他宿主由 --host 生成对应清单
  skills/
    praxis/                 # 入口技能，带全部参考、脚本与工具代码
    praxis-model/  praxis-compute/  praxis-verify/  praxis-explore/  praxis-dialogue/  praxis-report/
```

用户的题目、数据与案例继续保存在你的工作区，不进入插件。

| 组成 | 职责 | 连接方式 |
|---|---|---|
| 技能 | 理解问题、选择方法、判断证据、组织报告 | 共享一条建模主线，按请求调用 |
| MCP 与脚本 | 执行计算、检查数据、核对文献 | 同一组数学工具，支持 MCP 或命令行 |
| 证据工作流 | 保存任务、运行、检查与报告之间的对应关系 | 结果失效时回到相关环节重算 |

工作流由助手和确定性脚本共同推进，沿用用户工作区的规则；不是需要另外安装的一套调度服务。

</details>

## 可靠性

- 550 余项自动测试，覆盖解析答案、输入保护、失败与过期结果、PDF 辅助、数学工具与插件导出。
- 两份完整案例都带独立检查与可运行的复现代码，数字可对回报告。
- 每个结论标明依据与适用条件；失败的运行保留，不改写。

<details>
<summary><strong>开发与演练命令</strong></summary>

```bash
uv sync --locked --group dev
uv run --locked python -m pytest -q
uv run --locked python -m scripts.release_check   # 发布前：重跑示例、核对记录未漂移、跑测试
uv run --locked python -m examples.decision_sensitivity_demo
uv run --locked python -m examples.structural_reasoning_demo
uv run --locked python -m examples.exploration_demo
```


</details>

## 来源与许可

本地原创代码与文档采用 [MIT](LICENSE)。工作流参考 MathModelHub，Sobol 与 TOPSIS 分别使用 SALib 和 pyMCDM；实际复用范围与上游许可见 [第三方声明](THIRD_PARTY_NOTICES.md)。报告中实际使用的方法、数据与工具仍需在使用处引用原始来源。
