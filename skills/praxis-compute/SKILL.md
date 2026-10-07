---
name: praxis-compute
description: 把已确定的模型变成可复现的计算：数据文件接收与审计、原件保全、模型与独立验证器的执行、运行快照、结果过期检测和任务证据索引。用于“跑一下这个模型、检查这份数据、保存可复现的结果”。不决定模型是否适用，也不写论文。
license: MIT
---

# Praxis · 数据与计算

BUNDLE 指 `praxis` 技能目录；脚本在 `BUNDLE/scripts/`。需要 Python 3.12 和 uv，`uv sync --locked --project <BUNDLE>` 后用 `uv run --locked` 执行。没有终端时只做设计，不声称已运行。

## 做什么

- 数据：先读 [data-computing.md](../../references/data-computing.md)。接收文件后保留原件，用 `scripts/audit_data.py` 做只读的 CSV／Excel 审计（不推断单位、不静默修复），再决定怎样处理；变换只使用允许的信息，时间序列的开发目标与最终留出目标分开。
- 运行：模型与独立验证器写完并审核后，才用 `scripts/pipeline.py` 执行。命令、产物布局和过期规则见 [automation.md](../../references/automation.md)。参数、种子、失败运行保留，不覆盖。
- 证据：任务清单与 planning/tasks.md 使用同一组 ID。evidence 只证明已记录的连接，不证明题目被完整覆盖；程序检查、科学判断和人工核验分别表述。

- 工具：`praxis-tools` MCP 提供规划、网络、权重、排队、传染病、预测基线、敏感性与参考文献核对；宿主没有 MCP 时用 `python -m scripts.mcp_server --call` 或直接调用 `modeling/` 模块。清单与检查见 [model-library.md](../../references/model-library.md)。

## 交接

结果、单位、不确定性、可用结论和未解决问题写回对应任务 ID。运行失败先定位原因：实现错误修代码，模型不适用回 praxis-model，不用改假设掩盖错误。
