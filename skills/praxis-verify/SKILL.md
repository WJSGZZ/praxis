---
name: praxis-verify
description: 数值结果与具体主张的独立核验：用手算、另一推导、解析解、穷举、界或不变量核对答案、前提和结论范围。用于“独立检查这个数值、核验这条数学主张、找反例”。整稿水平与奖档意见交 praxis-review，模型设计交 praxis-model。 Independently verify numerical results and specific mathematical claims with appropriate evidence, counterexamples and scope checks.
license: MIT
---

# Praxis · 独立验证与审查

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [methods.md](../../references/methods.md)“证据的层次”选择当前主张需要的独立检查，说明不共享的推导、实现或信息来源及证伪条件。
- 核手算、解析解、穷举、守恒与约束；目标、机制、定义、可用信息和替代解释的检查分别支持对应层面的结论。
- 最优性与上下界读 [mathematical-reasoning.md](../../references/mathematical-reasoning.md)；数值误差、收敛与统计规范读 [scientific-foundations.md](../../references/scientific-foundations.md)。
- 敏感性只查有依据且影响建议的因素，记录阈值、适用范围和失败；工具条件与回退以 methods.md 为准。
- 重要主张按 [review-protocol.md](../../references/review-protocol.md) 核实际影响；同一助手换角色仅算自查，局部证明或一个数值结果不启动整稿评奖。
- 每项交付允许表达的结论、依据、独立性、反例或限制；证据不足返回原因所在环节。

## 交接

设计回 [model](../praxis-model/SKILL.md)，抽样交 [statistics](../praxis-statistics/SKILL.md)，因果识别交 [causal-analysis](../praxis-causal-analysis/SKILL.md)，预测外推交 [time-series](../praxis-time-series/SKILL.md)，整稿按 [judging.md](../../evals/judging.md) 交 [praxis-review](../praxis-review/SKILL.md)，解释交 [dialogue](../praxis-dialogue/SKILL.md)。
