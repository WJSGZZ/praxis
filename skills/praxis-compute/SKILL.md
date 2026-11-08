---
name: praxis-compute
description: 把已确定的模型变成可复现的计算：原始输入保全、模型与独立验证器执行、运行快照、结果过期检测与任务证据索引。用于“运行这个模型、保存可复现结果、检查运行是否过期”。模型适用性交 praxis-model，测量与数据审查交 praxis-data-analysis。 Execute established models and validators, preserve inputs, track reproducible runs and stale evidence.
license: MIT
---

# 计算

按automation核心执行已审模型/验证器，保全快照与题问证据；结果交verify。

沿主入口加 `--stage compute`；接口不清按`--list-details`选细则。实现错修代码，模型失配回model。
