---
name: praxis
license: MIT
description: 数学建模、独立核验及研究/竞赛交付。 Mathematical modeling for research and competitions.
---

# Praxis

接续目标/已有工作/允许输入/预算。完整竞赛从[model](skills/praxis-model/SKILL.md)进compute→verify→report；研究用`--stage research`；局部只进对应阶段，不建案例、不写 tasks.md。未知届次或期刊不继承其它要求。

按请求选：[数据](skills/praxis-data-analysis/SKILL.md)、[预测](skills/praxis-time-series/SKILL.md)、[推断](skills/praxis-statistics/SKILL.md)、[优化](skills/praxis-optimization/SKILL.md)、[整稿评价](skills/praxis-review/SKILL.md)、[语言](skills/praxis-scientific-writing/SKILL.md)；其余查[分工](references/capabilities.md)。仅加载当前主责。

`uv --directory "$BUNDLE" run --locked python -m scripts.instruction_packet`输出完整核心；阶段包含本责和安全原文。无终端按[读取索引](references/instruction-index.md)选区。`--list-details`按缺口选`--detail ID`；核心上限9390，模板另计。

持续授权内完成关联工作；阻塞记证据/恢复条件并做独立部分。BUNDLE为本目录；Python3.12/uv；无终端仅设计，不称已运行。
