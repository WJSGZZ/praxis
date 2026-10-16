---
name: praxis-explore
description: 面对陌生问题、不知道用什么模型、想找更好的办法或没有标准答案时使用：发现问题背后的数学结构，比较几条结构不同的路线，攻击并淘汰它们，保留中间结果、重组，在没有答案时用实验数学（猜想、反例、高精度检验）产出可验证的结论，并把经验存成可迁移的课程。用于“这题属于什么类型”“还有没有别的路”“这个结论站得住吗”“没有答案怎么办”。不替代计算与独立验证。 Explore unfamiliar modeling problems, mathematical structure, alternative routes and conjectures without an answer key.
license: MIT
---

# Praxis · 结构、路径与探索

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [structure-discovery.md](../../references/structure-discovery.md) 找机制与数学结构，用 `probe_structure`、`dimensional_analysis` 等低成本探测并记依据等级。
- 按 [methods.md](../../references/methods.md) 决定路线数量与范围，再用 [path-search.md](../../references/path-search.md) 比较、攻击、淘汰与重组；`route_graph` 记录原因、后备和存活攻击。
- 无标准答案时按 [research-mode.md](../../references/research-mode.md) 从小例、序列／关系猜测、反例搜索到证明，声称新前检索文献。
- 工具范围与严格证据按 [automation.md](../../references/automation.md#数学工具的结果契约)：搜索未见反例、数值候选与证明分别记录。
- 有迁移价值时按 [learning-loop.md](../../references/learning-loop.md) 存真实课程，新候选前检索；实际预算、失败与停止条件沿原任务保留。
- MCP／CLI 先用 `--list`、`--describe` 核字段；Python 入口为 `modeling.structure`、`modeling.routes`、`modeling.experiment` 与 `modeling.lessons`。

## 交接

共同取舍交 [dialogue](../praxis-dialogue/SKILL.md)，选定路线经 [model](../praxis-model/SKILL.md) 门禁后交 [compute](../praxis-compute/SKILL.md)，证据交 [verify](../praxis-verify/SKILL.md)，路线被推翻回本入口。
