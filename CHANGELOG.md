# 更新记录 · Changelog

版本号按语义版本：0.x 表示仍在快速变化，技能名或工具接口有不兼容改动时升次版本号。只记录对使用者有影响的变化。
Versions follow semantic versioning; 0.x means the skills and tools are still changing. Only user-visible changes are listed.

## 未发布 · Unreleased

（发布前把这一节改成新版本号。版本号只增不改：已发布的版本不再修改，修复发下一个小版本。小改动只提交，不发版；新增或改名技能与工具、结果格式变化才升次版本号。）

## 未发布 · Unreleased

- 新技能 `praxis-explore`：结构发现、路径搜索（`route_graph` 记录路线的产生、攻击、淘汰、重组与选定）、没有标准答案时的实验数学、经验沉淀；对应参考文件 `structure-discovery`、`path-search`、`research-mode`、`learning-loop`。
  New skill `praxis-explore`: structure discovery, route search recorded by `route_graph`, experimental mathematics when there is no answer key, and lessons that carry over.
- 新技能 `praxis-dialogue`：向不懂数学的用户讲清模型，结果出来后共同复盘。
  New skill `praxis-dialogue`: explain models in plain language and review results together.
- 新工具：`probe_structure`、`dimensional_analysis`、`check_total_unimodularity`、`test_conjecture`、`find_counterexample`、`guess_sequence`、`find_relation`、`lesson_add`、`lesson_search`、`solve_diffusion`、`markov_stationary`、`markov_absorption`、`matrix_game`、`eoq`、`newsvendor`、`cvar_portfolio`、`pareto_front`、`equilibria`、`kalman_filter`。
  New tools for structure probes, experimental mathematics, lesson memory, finite-volume diffusion, Markov chains, games, inventory, CVaR portfolios, Pareto fronts, equilibria and Kalman filtering.
- `evals.planted`：已知答案的合成题，用于盲测与回归。
  `evals.planted`: synthetic problems with known answers for blind checks and regression.
- 证据分七层并要求写证伪陈述；国赛案例补三张图并修正审计发现的问题。
  Evidence now has seven layers with a falsification statement; the CUMCM case gains three figures and fixes found in an independent audit.

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
