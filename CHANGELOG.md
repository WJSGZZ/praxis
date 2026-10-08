# 更新记录 · Changelog

版本号按语义版本：0.x 表示仍在快速变化，技能名或工具接口有不兼容改动时升次版本号。只记录对使用者有影响的变化。
Versions follow semantic versioning; 0.x means the skills and tools are still changing. Only user-visible changes are listed.

## 未发布 · Unreleased

- 两个完整案例为图表补入正文解释和自动交叉引用；美赛使用者说明保持独立单页，论文共 24 页（23 页解答加 1 页 AI 报告）；国赛支撑包排除 LaTeX 编译中间文件。修复图表引用检查误判段首引用的问题，并加入成稿回归检查。
  Both cases now connect figures and tables to their arguments through automatic references. The MCM user guide stays on one page; the report has 24 pages (23 solution pages plus the AI report). The CUMCM archive excludes TeX intermediates. Float checks accept paragraph-initial references, with regressions against the final documents.

- 评委评分表改为条目核对为主：每个维度由可对照的条目换算，印象只能在 ±1 内微调且须写理由，并标明分数来自复算还是判断；新增限时阅读评委模式和注入错误的校准；`evals/aggregate.py` 接受条目清单。
  The judging sheet now works from checkable items per dimension, with at most a documented ±1 adjustment and a record of whether a score is computed or judged; a time-boxed reading-judge mode and error-injection calibration are added; `evals/aggregate.py` accepts checklists.
- 修复（外部复核发现）：教训检索支持中文查询（字二元组与中文标签，种子教训补了中文标签，并把尚未在另一道题上验证过的两条降为“观察到一次”）；任何嵌套的乘方都被拒绝；相对路径一律相对工作区；国赛附录标题检测排除带句读的行。
  Fixes from an external review: lesson search works for Chinese queries (character bigrams and Chinese tags; two seed lessons not yet checked on another problem are downgraded); any nested power is rejected; relative paths always mean the workspace; appendix detection ignores lines with sentence punctuation.
- 证据索引新增可选的 `claims`：每条结论声明强度（computed／checked／independent），报告没有结论支撑的问题要求和强度超过证据的结论；路线记录里细化另一条路线时必须写明“简单一层解释不了什么”；教训新增失败做法、发现方式和信号三个字段，附带 5 条种子教训（`templates/lessons-seed.jsonl`），`route_graph` 启动新记录时用 `lessons_path` 返回相关教训。
  The evidence index accepts optional `claims` with a declared strength and reports uncovered requirements and overclaims; a refining route must say what the simpler route cannot explain; lessons gain failure-pattern, detection and signal fields with five seed lessons, returned by `route_graph` when a new record starts.
- 修复：环境快照覆盖全部声明的依赖；相对案例路径先按工作区解析；国赛附录标题检测不再被正文行误触发；表达式中失控的乘方被拒绝；工具说明写明 `proved`。
  Fixes: the environment snapshot covers every declared dependency; relative case paths resolve against the workspace; appendix detection ignores body lines; runaway powers are rejected; `proved` is explained in the tool descriptions.
- 案例展示图去掉“多少页报告”的链接行，两个案例的页脚统一；三个案例页的结尾邀请语统一；新增中文与英文论文各自的写作习惯和语言评审角色。
  Case overview images lose the page-count link line and share one footer; the three case pages close with the same invitation; Chinese and English writing habits and a language reviewer role are added.
- 版式：没有官方要求时按数学期刊连续排版，只有摘要页和不计页的 AI 使用报告另起一页；浮动体页顶端对齐。美赛案例据此重排，共 23 页（正文 22 页加 AI 使用报告）。
  Layout: continuous journal-style flow unless the contest requires otherwise; only the summary sheet and the uncounted AI report start new pages; float pages align to the top. The MCM case was reflowed to 23 pages.
- 新增 `scripts/contest_rules.py`：按美赛（COMAP 2026）与国赛（格式规范 2019/2021/2023）的硬性规则检查 PDF；两个论文模板按各自规则收紧并有测试；美赛 AI 使用报告标题与官方一致；国赛案例的代码页与参考文献不再侵入 2.5 厘米页边距。
  `scripts/contest_rules.py` checks a PDF against the published hard rules of MCM/ICM and CUMCM; both paper templates follow their rules and are tested; the MCM case's AI report carries the official title and the CUMCM case keeps its code and references out of the 2.5 cm margin.

（发布前把这一节改成新版本号。版本号只增不改：已发布的版本不再修改，修复发下一个小版本。小改动只提交，不发版；新增或改名技能与工具、结果格式变化才升次版本号。）

## 0.3.0 · 2026-10-08

由三次封存模拟比赛和两轮盲比较驱动：补齐工具覆盖，加入覆盖地图、评审协议与“先做透再收敛”的工作方式。
Driven by three sealed simulated contests and two blind comparisons: wider tool coverage, a coverage map, a review protocol, and a deep-work-then-converge way of working.

- `ols_report`、`compare_models`（回归诊断与对基线的交叉验证比较）；`check_pdf --margins`（渲染后检查每页左右空白与溢出，新增依赖 pypdfium2）。
  `ols_report` and `compare_models` for regression diagnostics and baseline-honest comparison; `check_pdf --margins` renders pages and flags uneven margins and overflow (new dependency pypdfium2).
- 第一次封存模拟比赛暴露的缺口：分层热传导 `solve_layered_diffusion` 与独立的拉普拉斯解 `layered_diffusion_laplace`、参数标定 `calibrate_curve`（可辨识性与留出点）、`sobol_convergence`、路线记录落盘 `graph_file`、工具索引（自动生成）、图的负值条形与标签转义、`check_pdf --margins` 增加大块空白检测；MCP 服务按需加载重的库，启动更快。
  Gaps found by the first sealed simulation: layered conduction with an independent Laplace solution, parameter calibration with identifiability and hold-out, Sobol convergence, persistent route records, a generated tool index, signed bars and label escaping in figures, white-gap detection in `check_pdf --margins`, and lazy imports that speed up the tool server.
- 第二、三次模拟比赛暴露的缺口：`bimatrix_nash`（非零和博弈全部纳什均衡）、LP/MILP 接受稀疏矩阵、`mcp_server --list --filter`、案例运行只打印摘要；序贯决策（信息结构、松弛上界与遍历证书、规则变体表）、Word 附件、并行预算等指南。
  Gaps from the second and third simulations: Nash equilibria of bimatrix games, sparse LP/MILP input, a tool filter, a compact `run` summary; guidance on sequential decisions, Word attachments and parallel budgets.

## 0.2.0 · 2026-10-08

在 0.1.0 之上，让 Praxis 能面对陌生问题：先找结构、比较路线、没有答案时也能产出带把握等级的结论。
On top of 0.1.0, Praxis can now face an unfamiliar problem: find the structure first, compare routes, and produce conclusions labelled by confidence even when there is no answer key.

- 新技能 `praxis-explore`（结构发现、路径搜索、实验数学、经验沉淀）与 `praxis-dialogue`（向不懂数学的用户讲清模型、结果出来后共同复盘）；新参考：结构发现、路径搜索、研究模式、学习回路、科研基础（不确定性、数值收敛、统计检验）、竞赛题型与丢分点、领域机制速查。
  New skills `praxis-explore` and `praxis-dialogue`, and new references on structure discovery, route search, research mode, the learning loop, scientific foundations, contest playbook and domain mechanisms.
- 新工具共 20 余个：结构探测（凸、单调、对称、幂律、守恒量、量纲分析、全单模）、路线记录 `route_graph`、实验数学（反例搜索、猜想检验、递推猜测与有限核对证明、整数关系）、经验记忆、一维热扩散（附收敛阶与网格收敛指数）、马尔可夫链、矩阵博弈、库存、CVaR 组合、Pareto 前沿、平衡点稳定性、卡尔曼滤波；线性规划支持 ≥ 约束与影子价格；每个工具带可运行示例，字段缺失时报错会列出必填字段。
  More than twenty new tools: structure probes, the route record, experimental mathematics, lesson memory, finite-volume diffusion with convergence indices, Markov chains, games, inventory, CVaR portfolios, Pareto fronts, equilibria and Kalman filtering; LP gains >= rows and shadow prices; every tool carries a runnable example.
- 证据分七层并要求写证伪陈述；`evals.planted` 提供九类已知答案的合成题与盲测规程；新增研究模式案例（3×2n 多米诺铺法数）。
  Evidence has seven layers with a falsification statement; `evals.planted` offers nine kinds of known-answer problems with a blind-evaluation protocol; a research-mode case (domino tilings) is added.
- 国赛案例补三张图并按独立审计修正；美赛案例按独立审计重算：被约束的温度改为在入口射流区之外施加并在三套网格上收敛，分段方案 19.35 L，论文 24 页。
  Both cases were corrected after independent audits; the MCM case was recomputed with mesh-converged constraints (schedule 19.35 L, 24-page paper).
- 修复：`sir_fit` 给出终态规模并说明假设；`mcp_server` 版本号取自 `pyproject.toml`。
  Fixes: `sir_fit` reports the final size and its assumptions; the server reads its version from `pyproject.toml`.

## 0.1.0 · 2026-10-07

首个公开版本 · First public release

- 六个技能：整题入口 `praxis`，以及 `praxis-model`、`praxis-compute`、`praxis-verify`、`praxis-dialogue`、`praxis-report`；按 Agent Plugins 1.0 导出，附 `praxis-tools` 数学工具服务。
  Six skills (the whole-problem entry plus five focused ones) exported as an Agent Plugins 1.0 plugin, with the `praxis-tools` math tool server.
- 两个完整案例：1998 年国赛 A 题（17 页中文论文与支撑材料）和 2016 年美赛 A 题（23 页英文论文），均用 XeLaTeX 与 pgfplots 排版，附复现代码与验收记录。
  Two complete cases: 1998 CUMCM A (17-page Chinese paper plus supporting archive) and 2016 MCM A (23-page English paper), typeset with XeLaTeX and pgfplots, with reproduction code and acceptance records.
- 方法库覆盖优化、微分方程、排队、敏感性、预测与学习类方法，每种附适用条件与必做检查；图表规范与 LaTeX 论文模板（`templates/`）。
  A model library covering optimization, differential equations, queueing, sensitivity, forecasting and learning methods, each with conditions and required checks; figure guidelines and LaTeX paper templates.
- 持续集成：每次推送自动运行测试。
  Continuous integration runs the tests on every push.
- 新增 12 个工具（共 62 个）：`minimize_nlp`、`knapsack`、`min_cost_flow`、`robust_lp`、`solve_mdp`、`hypothesis_test`、`bootstrap_ci`、`monte_carlo`、`solve_ode`、`arima_forecast`、`pca_report`、`cluster_report`，均有已知答案或暴力枚举的测试；新增能力覆盖地图（哪类结构有现成路线、没有时怎么办）、论文评审协议（独立评审角色与反方）、赛前规则清单。
  Twelve new tools (62 in all) with known-answer or brute-force tests; a capability coverage map, a paper review protocol with independent reviewer roles, and a pre-contest rule checklist.
- 新增《深度工作与竞赛收敛》：开始时确认交付目标，先按科研标准做透并设停止规则，再用收敛账本把证据池分流到正文、附录、池或删除；写明评委阅读方式与收敛检查。
  New guide on deep work and contest convergence: declare the delivery target first, work to research standard with a stopping rule, then route the evidence pool into main text, appendix, pool or deletion with a convergence ledger.
