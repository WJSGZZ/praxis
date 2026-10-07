# 更新记录 · Changelog

版本号按语义版本：0.x 表示仍在快速变化，技能名或工具接口有不兼容改动时升次版本号。只记录对使用者有影响的变化。
Versions follow semantic versioning; 0.x means the skills and tools are still changing. Only user-visible changes are listed.

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
