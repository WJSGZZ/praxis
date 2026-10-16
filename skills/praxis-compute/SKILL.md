---
name: praxis-compute
description: 把已确定的模型变成可复现的计算：原始输入保全、模型与独立验证器执行、运行快照、结果过期检测与任务证据索引。用于“运行这个模型、保存可复现结果、检查运行是否过期”。模型适用性交 praxis-model，测量与数据审查交 praxis-data-analysis。 Execute established models and validators, preserve inputs, track reproducible runs and stale evidence.
license: MIT
---

# Praxis · 数据与计算

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- schema 2 案例没有通过门禁的 `planning/model-contract.json` 不运行 pipeline；门禁见 [modeling-gate.md](../../references/modeling-gate.md)。
- 按 [data-computing.md](../../references/data-computing.md) 保全原始输入，接续已确认的处理、单位、参数和信息时点。
- 审核模型与独立验证器后用 `scripts/pipeline.py` 执行；命令、快照、失败保留与过期判据只按 [automation.md](../../references/automation.md)。
- MCP 工具、CLI 与 `modeling/` 的适用范围查 [model-library.md](../../references/model-library.md)，按实际接口调用。
- 任务与 evidence 沿同一 ID 连接结果、单位、不确定性和未决项；运行记录、科学判断与人工核验分别报告。

## 交接

测量／连接交 [data-analysis](../praxis-data-analysis/SKILL.md)，统计设计交 [statistics](../praxis-statistics/SKILL.md)，预测信息交 [time-series](../praxis-time-series/SKILL.md)，实现失败修代码，模型失配回 [model](../praxis-model/SKILL.md)，独立证据交 [verify](../praxis-verify/SKILL.md)。
