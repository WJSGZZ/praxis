---
name: praxis-text-analysis
description: 将文本转成有明确构念、边界和测量误差的研究变量，完成抽取、编码、文本分类或主题探索并审核语义与抽样证据。用于“分析评论或文档、提取事件、关键词规则靠谱吗、标注文本、检查否定和转述、评价文本分类”。Text measurement, document coding, information extraction, text classification, semantic audit and annotation validation. 普通翻译／润色不启动本入口；不把关键词或模型标签当事实真值。
license: MIT
---

# Praxis · 文本测量与语义审核

专业深度归 [text-analysis.md](../../references/text-analysis.md)。本入口处理研究数据中的文本变量，写作措辞归 [praxis-report](../praxis-report/SKILL.md)，读题定义归 [praxis-model](../praxis-model/SKILL.md)。

## 调用契约

输入：获准分析的语料及来源、单位和时间／实体结构、目标构念、已有标签／规则／模型、拟测量的统计量与用途。产出：可审核的编码契约、来源片段与派生标签、抽样审核及错误分析、可复现提取或分类方案和测量限制。原文不充分时保留 unknown／ambiguous，不能靠合理补全生成事实。

## 专业判断与执行

- 先定义测量对象和编码单位：文档、句子、事件还是实体；区分作者表述、被引用观点、事实事件和态度。同一来源的转载、长文切片或同一事件的多条文本不自动独立。
- 从真实文本和构念形成编码规则，保留正例、反例与无法判断的例子。审核否定范围、条件／计划、转述、时点、比较和实体指代；“提到某事”不能替代“发生某事”，词频／情绪／主题编号不能自动解释为真实程度或有序等级。
- 先做透明规则或词袋基线；已有 Scikit-learn `TfidfVectorizer`、`Pipeline` 和分类／聚类接口可复用。词典／IDF／阈值／提示／标签映射都是开发选择，按实体、来源或时间拆分后只在训练部分学习，保留最终未参与选择的评价数据；具体语言处理与接口局限见专业参考。
- 采用分层抽样审核，兼顾随机总体样本、稀有标签、模型分歧和低置信度；后两者不能单独估计总体错误率。人工标注实际发生才写人工；同一AI换角色、关键词自造标签或开发者事后确认均不算独立真值。
- 依据审核标签报告混淆方向、逐类 precision／recall、样本与置信限制，另检查覆盖、重复和抽样权重。标签判断错误会怎样改变后续比例、排序或回归需要敏感性分析；没有代表性审核就只报告代理指标。

## 交付、验证与回退

交付定义／规则／版本、记录ID与原文定位、标签和判断状态、审核抽样与来源、错误类型及下游影响。最少检查一个明确正例和能使规则误判的当前反例；程序提取成功不认证构念效度，主题或相似度也不是事实判定。

来源与记录单位有误交 [praxis-data-analysis](../praxis-data-analysis/SKILL.md)，群体推断及区间交 [praxis-statistics](../praxis-statistics/SKILL.md)，预测任务的信息时点交 [praxis-time-series](../praxis-time-series/SKILL.md)。需要改变研究问题回 [praxis-model](../praxis-model/SKILL.md)，前提专审交 [praxis-assumptions](../praxis-assumptions/SKILL.md)，独立审核和结论强度交 [praxis-verify](../praxis-verify/SKILL.md)。
