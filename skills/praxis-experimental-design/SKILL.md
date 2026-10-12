---
name: praxis-experimental-design
description: 在采数据前设计能回答目标问题的实验：处理与对照、随机化单位、区组/因子、精度或功效、主要结局和停止规则。用于“怎么设计实验、A/B测试、试验要多少样本、控制混杂、区组/析因、什么时候停止”。Experimental design, randomization, blocking, factorial experiments, sample size, precision, power and stopping rules. 已有观测数据的EDA交 praxis-data-analysis，分析与区间交 praxis-statistics，因果识别共用 praxis-causal-analysis。
license: MIT
---

# Praxis · 实验设计与证据收集

专业判断归 [experimental-design.md](../../references/experimental-design.md)。本入口设计现实或可控数值实验的证据采集，不等同EDA、搜索反例或把观察关联升级为干预效果。

## 调用契约

输入：研究问题、目标效应和最小有意义差异、可操纵因素、可随机化单位、依赖/干扰、测量误差、预算与实际执行限制。产出：实验协议和分配方案、对照与测量计划、精度/功效的条件依据、样本/区组/重复结构、事前分析和停止规则、失败/偏离处理与可验证范围。缺关键方差或ICC时给范围/曲线与补先导数据的动作，不能编一个确定样本量。

## 专业判断与执行

- 先定处理、比较、目标群体和结局尺度；分清随机化单位、观察单位、分析单位。对同一器件测十次不会产生十个独立器件，按班级分配也不能按学生独立检验。
- 明确谁能获得何种处理，随机化怎样执行与保留。重复测量、配对、交叉、时间顺序、场地/批次和干扰效应须进入设计与分析；随机化提供的识别保证有遵从、缺失与溢出范围，不从分配表宣称任意推广。
- 明显预处理异质性可用区组内随机化；多个可控因素有交互疑问时比较析因/部分因子等设计，而非只逐因素改一个。说明可估计效应与混叠，保留随机运行顺序、中心点/重复的实际用途，不机械凑一个标准实验表。
- 先选精度目标或事前功效，再声明目标差异、方差/事件率、alpha、allocation、独立单位与依赖假设。相称时直接用现有Statsmodels功效接口或设计匹配的模拟；两独立均值接口不能直接认证簇/重复/序贯设计。观察到的效应算“事后功效”不能解释非显著结果。
- 实验开始前固定主要结局、比较族、纳排/缺失/遵从分析、样本与停止条件；探索偏离另记。逐批看p<.05就停会改变错误率，需要预先说明的相应序贯方法，不能把未调整反复检验称固定样本检验。

## 验证、交付与回退

核分配人数/单位、处理覆盖、区组约束、重复身份、seed及分配前信息；用一个可独立核查的精度/功效例验证软件调用，再针对当前设计核方差与分析单位。协议完成不代表试验已实际执行；保留真实偏离、失访、未遵从和中止，结果不佳也不能改变原停止线。

识别与干扰交 [praxis-causal-analysis](../praxis-causal-analysis/SKILL.md)，估计/依赖与比较族交 [praxis-statistics](../praxis-statistics/SKILL.md)，数据接收/测量交 [praxis-data-analysis](../praxis-data-analysis/SKILL.md)。可重复模拟与证据共用 [praxis-compute](../praxis-compute/SKILL.md)，数学独立核验交 [praxis-verify](../praxis-verify/SKILL.md)。预测模型的验证交 [praxis-machine-learning](../praxis-machine-learning/SKILL.md)，全文写作交 [praxis-report](../praxis-report/SKILL.md)。
