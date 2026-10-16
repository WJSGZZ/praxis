---
name: praxis
license: MIT
description: 将问题与数据推进为可解释、可复现的数学模型、独立验证与报告证据。用于整题建模、路线选择、专业分析、论文协作与竞赛交付，无需用户先选算法。Mathematical modeling, scientific analysis, independent validation, paper collaboration and competition delivery. 单个数学概念问答不必启动整题流程。
---

# Praxis

接续目标、场景、已有工作与预算，选择当前主责，用相称证据完成回答。

| 请求类型 | 技能 | 唯一首读文件 |
|---|---|---|
| 整题建模 | [model](skills/praxis-model/SKILL.md) | [统一方法](references/methods.md) |
| 单个数值或局部判断：不建案例、不写 tasks.md | [verify](skills/praxis-verify/SKILL.md) | [工具表](references/model-library.md) |
| 数据与测量 | [data-analysis](skills/praxis-data-analysis/SKILL.md) | [数据分析](references/data-analysis.md) |
| 预测与推断 | [time-series](skills/praxis-time-series/SKILL.md)、[statistics](skills/praxis-statistics/SKILL.md) | [统计分析](references/statistical-analysis.md) |
| 优化与决策 | [optimization](skills/praxis-optimization/SKILL.md) | [优化](references/optimization.md) |
| 整稿组稿与交付 | [report](skills/praxis-report/SKILL.md) | [写作](references/writing.md) |
| 整稿评价 | [review](skills/praxis-review/SKILL.md) | [分类标准](evals/judging.md) |
| 论文语言 | [scientific-writing](skills/praxis-scientific-writing/SKILL.md) | [科研表达](references/scientific-writing.md) |

完整竞赛题先读 [统一方法](references/methods.md)、[算前门禁](references/modeling-gate.md)、[论文清单](references/contest-paper-checklist.md)。
读外部材料前读 [材料暴露](references/integrity.md#材料暴露)，沿用封存与接触身份。
其余按缺口查 [专业分工](references/capabilities.md)；未知届次或期刊不继承其它要求。

持续授权内完成实现、独立检查、整稿与实际成品、回归和唯一记录。
真阻塞记证据、恢复条件与下一动作，完成独立部分，保留失败。
本目录为 BUNDLE，脚本在 `scripts/`；运行需 Python 3.12 与 uv；无终端时只做设计，不声称已运行。
