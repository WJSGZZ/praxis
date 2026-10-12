---
name: praxis-causal-analysis
description: 把“改变某因素会怎样”转成明确干预、目标群体和效应，审查研究设计、时间顺序、混杂、选择与识别条件，条件成立后再估计并做敏感性。用于“这是因果吗、政策或处理有效吗、控制哪些变量、干预效应、识别不了怎么办”。Causal inference, intervention effects, identification, confounding, adjustment, treatment effects and study design. 预测或相关分析不自动升级为因果；统计估计交 praxis-statistics协作，完整建模仍归 praxis。
license: MIT
---

# Praxis · 因果问题与识别

专业深度归 [causal-analysis.md](../../references/causal-analysis.md)。共用 [methods.md](../../references/methods.md) 的条件与证据层次、[mathematical-reasoning.md](../../references/mathematical-reasoning.md#干预与预测哪些结论能用于改变系统) 的干预／预测边界；本入口不另设假设台账。

## 调用契约

输入：具体可实施干预与对照、结果和测量时点、目标群体／时期、观察或分配机制、候选混杂／选择机制、已有估计和拟写因果主张。产出：目标效应、因果结构与证据、识别依据或不能识别的理由、设计／数据补充或条件估计方案、反驳与敏感性、允许的因果或关联表述。

## 专业判断

- 区分描述关联、预测、机制情景与实际干预效应；写清处理版本、时点、对照、随访、目标群体和ATE／ATT等比较量。没有可定义干预或时间顺序，先收窄问题。
- 在估计前构造因果结构／时间线及其来源，检查混杂、碰撞点、选择、测量、治疗后变量和相互影响；不能把所有可预测变量都拿来调整。数据中相关性或拟合优度不能确定箭头方向。
- 说明设计如何识别目标：随机分配、观察研究的条件可交换性／一致性／重叠，或其他特定准实验条件；每项条件写证据、未可检验部分及失效影响。前提评审可直接交 [praxis-assumptions](../praxis-assumptions/SKILL.md)，不以运行分数替代识别。
- 条件支持时再与 [praxis-statistics](../praxis-statistics/SKILL.md) 选择调整／加权／标准化估计与相应推断。已有Statsmodels `TreatmentEffect`可用于限定的条件独立、二元处理和线性结果模型；接口不提供任意设计的识别保证。重叠／极端权重、目标群体改变和缺失需实查。
- 选择能攻击主要解释的负对照、时点／安慰剂、设计特有诊断或未测混杂敏感性。通过这些检查仍不证明全部识别条件；若同一观测分布可来自不同干预效应，明确不能从现有资料唯一识别。

## 交付、验证与回退

沿已有任务记录保留因果问题、结构／时间线、识别条件和来源、实际估计与诊断、替代解释及剩余不确定性。先对照一个可解析的干预小例或非识别反例；真实设计证据与合成算法核验分别表述，不把AI生成的标注／机制设定当自然实验。

不能识别时可给有边界的关联、部分识别／情景或需要的研究设计，不直接多装模型。定义／结构要改回 [praxis-model](../praxis-model/SKILL.md)，数据来源及目标选择交 [praxis-data-analysis](../praxis-data-analysis/SKILL.md)，数值与主张独立检查交 [praxis-verify](../praxis-verify/SKILL.md)；实际运行交 [praxis-compute](../praxis-compute/SKILL.md)，写作交 [praxis-report](../praxis-report/SKILL.md)。
