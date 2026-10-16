---
name: praxis-text-analysis
description: 将文本转成有明确构念、边界和测量误差的研究变量，完成抽取、编码、文本分类或主题探索并审核语义与抽样证据。用于“分析评论或文档、提取事件、关键词规则靠谱吗、标注文本、检查否定和转述、评价文本分类”。Text measurement, document coding, information extraction, text classification, semantic audit and annotation validation. 普通翻译／润色不启动本入口；不把关键词或模型标签当事实真值。
license: MIT
---

# Praxis · 文本测量与语义审核

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [text-analysis.md](../../references/text-analysis.md) 定构念、文档／句／事件／实体单位与来源，区分作者表述、引用、事实和态度，标明重复与来源依赖。
- 编码契约保留正例、反例和 unknown／ambiguous；核否定范围、计划、转述、时间、比较及指代，标签只承担声明的测量含义。
- 先透明规则或词袋基线；TfidfVectorizer／Pipeline 等在实体、来源或时间拆分后仅用训练部分学词典、阈值与映射，最终评价数据留出。
- 分层审核兼顾总体随机样本、稀有类、分歧和低置信度；区分总体误差估计与定向找错，真实人工标注与AI自查分别记录。
- 报逐类 precision／recall、混淆方向、样本与抽样权重，检查标签误差对下游比例、排序和回归的影响。
- 交原文定位、记录ID、规则版本、标签状态、审核与限制；先核明确正例和当前误判反例。

## 交接

测量交 [data-analysis](../praxis-data-analysis/SKILL.md)，推断交 [statistics](../praxis-statistics/SKILL.md)，时点交 [time-series](../praxis-time-series/SKILL.md)，定义／前提交 [model](../praxis-model/SKILL.md)／[assumptions](../praxis-assumptions/SKILL.md)，独立审核交 [verify](../praxis-verify/SKILL.md)，论文措辞交 [scientific-writing](../praxis-scientific-writing/SKILL.md)。
