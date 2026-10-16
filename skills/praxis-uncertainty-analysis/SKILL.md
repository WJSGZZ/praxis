---
name: praxis-uncertainty-analysis
description: 定义联合输入、依赖与误差来源，传播参数／测量／随机／结构不确定性，分析敏感性、阈值风险与决策是否改变。用于“不确定性怎么传播、参数相关、联合达标概率、蒙特卡洛、Sobol、情景与置信区间、方案是否稳健”。Uncertainty propagation, dependent inputs, sensitivity analysis and decision robustness. 抽样推断归 praxis-statistics，独立数学证据与结论强度归 praxis-verify；范围不自动变成概率。
license: MIT
---

# Praxis · 不确定性与决策稳健性

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [uncertainty-analysis.md](../../references/uncertainty-analysis.md) 分测量、参数、结构、随机与数值误差，定义分布、超限、贡献或决策目标；无依据范围保留情景。
- 联合结构、边际、相关、总量约束与共同冲击一起声明，检查生成状态的可行性。
- 比例、分母、组概率、非线性损失与行动量分别定义，在相容域上核界、可达见证及无界情形，与同费用期限的替代比较。
- 先用解析／协方差传播；`monte_carlo` 当前逐变量独立，Sobol 限独立连续均匀输入与确定性标量，相关输入另用有依据的联合生成／成组情景。
- 按 [scientific-foundations.md](../../references/scientific-foundations.md) 分清 SE、输出波动、置信区间与情景极值，查尾部和决策精度。
- 交分布与条件、阈值、收益风险代价和有价值的新观测；模型／分布／检查条件改变另产真实运行，沿原记录保留失败。

## 交接

抽样推断交 [statistics](../praxis-statistics/SKILL.md)，风险优化交 [optimization](../praxis-optimization/SKILL.md)，机制／定义交 [dynamical-modeling](../praxis-dynamical-modeling/SKILL.md)／[model](../praxis-model/SKILL.md)，独立结论交 [verify](../praxis-verify/SKILL.md)。
