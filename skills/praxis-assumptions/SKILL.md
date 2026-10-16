---
name: praxis-assumptions
description: 梳理和审查数学模型的显式与隐含假设，区分题面事实、定义、模型前提和参数情景，说明依据、实际用途及失效影响。用于“这题需要哪些假设、假设合理吗、补假设及理由、检查隐含前提”。不凭假设条数或章节判断质量；数值核验交 praxis-verify，纯论文排版交 praxis-report，整题设计与协调交 praxis-model／praxis。 Identify and review explicit or implicit model assumptions, reasons, uses and failure effects.
license: MIT
---

# Praxis · 假设与适用条件

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [methods.md](../../references/methods.md#假设理由与结论范围) 从方程、数据、抽样、比较和信息条件反查显式与隐含前提，区分事实、定义、约定、假设与参数情景。
- 每项说明依据、简化理由、使用位置及排除的机制；只有原题时保留候选身份，实际未选模型或未验证照实写。
- 检查影响而非条数：清理无用途或冲突前提，用边界、解析特例、替代结构或观测攻击主要建议，区分参数扰动与结构检验。
- 核摘要、数字与建议携带同一范围；失效影响定位到主张，区分模型内正确、现实获证及待检验。
- 沿已有任务记录前提、理由、用途、失效后答案与实际检查；集中／局部呈现接 [writing.md](../../references/writing.md)，赛事规则接 [context-and-team.md](../../references/context-and-team.md#规则适配)。

## 交接

定义／机制交 [model](../praxis-model/SKILL.md)，实验交 [compute](../praxis-compute/SKILL.md)，独立影响核验交 [verify](../praxis-verify/SKILL.md)，组稿交 [report](../praxis-report/SKILL.md)，完整作品评价交 [review](../praxis-review/SKILL.md)。
