---
name: praxis-uncertainty-analysis
description: 定义联合输入、依赖与误差来源，传播参数／测量／随机／结构不确定性，分析敏感性、阈值风险与决策是否改变。用于“不确定性怎么传播、参数相关、联合达标概率、蒙特卡洛、Sobol、情景与置信区间、方案是否稳健”。Uncertainty propagation, dependent inputs, sensitivity analysis and decision robustness. 抽样推断归 praxis-statistics，独立数学证据与结论强度归 praxis-verify；范围不自动变成概率。
license: MIT
---

# Praxis · 不确定性与决策稳健性

专业方法归 [uncertainty-analysis.md](../../references/uncertainty-analysis.md)。区间、数值误差和尺度共用 [scientific-foundations.md](../../references/scientific-foundations.md)，不建立第二套验证记录。

## 调用契约

输入：有效模型、关键目标／约束／决策、误差和参数来源、联合分布或情景集合、依赖与物理限制、预算和接受判据。产出：不确定性契约、传播或敏感性结果、分清模拟误差与现实不确定性的区间、改变建议的阈值／情景及未识别范围。

## 专业处理

- 先分开测量、参数、结构、随机变异和数值误差，定义所问的是输出分布、方向、超限概率、输入贡献还是决策稳定性。缺依据的范围保持情景，不自行赋均匀概率。
- 联合结构与边际分别说明。相关参数、总量约束、公共冲击与成组情景保持一起；独立抽样可能制造不可行状态、漏掉共同风险或夸大分散收益。
- 解析／协方差传播可用时先做。`monte_carlo` 当前逐变量独立抽样；`sobol_sensitivity`／`sobol_convergence` 限独立连续均匀输入、确定性标量输出。相关输入用有依据的联合生成或成组情景，不能把同名参数表直接交Sobol。
- 区间说明对象、来源和条件：模拟均值的标准误不是输出波动，情景极值不是置信区间，结构差异不自动有概率权重。样本加倍或工具settled只是采样诊断，仍须核尾部和实际决策精度。
- 同时分析推荐是否在可行情景下保持、收益／风险代价及何时应改方案；识别最有价值的新观测。敏感性不能自动解释因果或变量可删除。

## 交接

抽样设计、聚类与置信推断交 [praxis-statistics](../praxis-statistics/SKILL.md)，稳健／风险优化交 [praxis-optimization](../praxis-optimization/SKILL.md)，机制或状态定义交 [praxis-dynamical-modeling](../praxis-dynamical-modeling/SKILL.md)／[praxis-model](../praxis-model/SKILL.md)，独立证据与允许结论交 [praxis-verify](../praxis-verify/SKILL.md)。复用原运行证据、失败和记录；分布、模型或检查条件改变时另产真实运行，不追认旧结果。
