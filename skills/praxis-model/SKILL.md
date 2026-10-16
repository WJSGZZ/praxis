---
name: praxis-model
description: 把原题变成可回答的任务和最小可验证的模型：读题与定义、变量与候选假设、没有数据时怎样给参数找依据、路线与模型选择、可辨识性／尺度／优化结构判断。用于“这题怎么做、用什么模型、参数怎么定”。单独梳理或审查假设交 praxis-assumptions，不负责大规模计算或写论文；整题推进用 praxis。 Define the problem, choose a model, justify parameters and compare modeling routes.
license: MIT
---

# Praxis · 问题与模型

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 产出 `planning/model-contract.json`，按 [modeling-gate.md](../../references/modeling-gate.md) 完成算前门禁，通过后才交 compute。
- 按 [methods.md](../../references/methods.md) 将原题写成目标量、单位、约束与验收任务；改变答案的歧义读 [definition-review.md](../../references/definition-review.md)，合理替代解释保留条件答案。
- 参数、可辨识性与保证读 [mathematical-reasoning.md](../../references/mathematical-reasoning.md)；参数依据表接 [writing.md](../../references/writing.md)，未知值标情景。
- 路线数量与比较条件以 methods.md 为准；适用工具读 [model-library.md](../../references/model-library.md)，结构未知交 [explore](../praxis-explore/SKILL.md)。
- 机制与量级读 [domain-models.md](../../references/domain-models.md)，验证设计读 [scientific-foundations.md](../../references/scientific-foundations.md)；先试最便宜的推翻检查。
- 沿已有任务按 [tasks-template.md](../../references/tasks-template.md) 记录定义、前提、基线、备选与失效转向；关键偏好与用户确认。

## 交接

前提专审交 [assumptions](../praxis-assumptions/SKILL.md)，契约与验证设计交 [compute](../praxis-compute/SKILL.md)，结果核验交 [verify](../praxis-verify/SKILL.md)，共同取舍交 [dialogue](../praxis-dialogue/SKILL.md)。
