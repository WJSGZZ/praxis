# 更新记录 · Changelog

版本号按语义版本：0.x 表示仍在快速变化，技能名或工具接口有不兼容改动时升次版本号。只记录对使用者有影响的变化。
Versions follow semantic versioning; 0.x means the skills and tools are still changing. Only user-visible changes are listed.

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

## 未发布 · Unreleased

- `ols_report`、`compare_models`（回归诊断与对基线的交叉验证比较）；`check_pdf --margins`（渲染后检查每页左右空白与溢出，新增依赖 pypdfium2）。
  `ols_report` and `compare_models` for regression diagnostics and baseline-honest comparison; `check_pdf --margins` renders pages and flags uneven margins and overflow (new dependency pypdfium2).

（发布前把这一节改成新版本号。版本号只增不改：已发布的版本不再修改，修复发下一个小版本。小改动只提交，不发版；新增或改名技能与工具、结果格式变化才升次版本号。）

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
