---
name: praxis-data-analysis
description: 理解数据实际测量什么，开展探索性分析、缺失与采样审查、单位和多表连接核验，并形成可供建模的数据契约。用于“这份数据说明什么、先做EDA、检查缺失、这些表怎么连接、样本是否有偏”。Understand a dataset, exploratory data analysis, missingness, sampling, measurement units and join cardinality. 文件接收和运行快照共用 praxis-compute；统计推断交 praxis-statistics，完整任务仍由 praxis 协调。
license: MIT
---

# Praxis · 数据理解与探索

BUNDLE 指 `praxis` 技能目录。专业深度归 [data-analysis.md](../../references/data-analysis.md)；文件接收、处理与运行仍按 [data-computing.md](../../references/data-computing.md) 和 [automation.md](../../references/automation.md)，不建立第二套数据流水线。

## 调用契约

输入：本次获准分析的表／文件、研究问题、数据字典或其缺口、来源与目标群体、已知分组／时间及后续用途。产出：观察与测量契约、实际覆盖和缺失摘要、连接／处理选择及其影响、探索性发现和仍不能支持的结论。只有数据时先做可确认的结构与范围检查；不从列名猜单位、身份或科学含义。

## 专业判断

- 定义每行、每实体、每次测量和目标统计量分别是什么；说明独立单位、重复测量、抽样框、权重与时间／空间结构。行数不自动等于独立样本量，重复行也不自动应删除。
- 分清真零、未记录、不适用、未检出、删失与未知键；缺失编码、检测限及允许范围从数据字典或来源核实。未知对象不并入零类，填补／筛选／单位转换只生成有说明的派生数据。
- 连接前声明键含义、时效和 `1:1`／`m:1` 等基数，检查空键、唯一性、别名和覆盖；连接后对账实体、行数、关键分组及计数／总量。已有 `audit_join` 接收记录数组、声明的基数与空键政策，复用Pandas核coverage和行膨胀；直接用 `merge(validate=..., indicator=True)` 时同样另查空键语义。工具通过不证明关联语义成立。
- EDA 比较分组／时序覆盖、稳健和常规摘要、异常影响及不同合理处理的敏感性。声明实际扫描范围、截断和抽样方法；有序前缀不是总体随机样本，相关或分布图不能诊断出 MCAR／MAR／MNAR。
- 复用 Pandas、NumPy 与已有审计工具；复杂声明式表契约可评估 Pandera，未安装时给出设计或用现有接口完成必要检查，不假称已运行。成熟 API 的条件及反例见专业参考。

- 时序连接保存实体×事件×字段的版本与可用时点；用 `asof_join` 选择决策截点前的原行索引。记录日期不自动等于字段可用日期，缺时点和同刻冲突保留未决；完整政策与反例共用专业参考，不用最终快照填回过去。

## 交付、验证与回退

按已有任务 ID 交付数据字典、覆盖／缺失／连接证据、派生变换与影响、可回答问题和未知事项，不强迫单次小请求建立案例。至少核一个已知小例、单位换算或独立对账，以及当前高风险边界；已核结构、待确认含义与探索推测分开写。

推断和效应区间交 [praxis-statistics](../praxis-statistics/SKILL.md)，文本构念交 [praxis-text-analysis](../praxis-text-analysis/SKILL.md)，预测信息契约交 [praxis-time-series](../praxis-time-series/SKILL.md)。数据无法定义目标或支持路线时回 [praxis-model](../praxis-model/SKILL.md)；前提需专审时用 [praxis-assumptions](../praxis-assumptions/SKILL.md)。持久运行交 [praxis-compute](../praxis-compute/SKILL.md)，结论强度交 [praxis-verify](../praxis-verify/SKILL.md)。
