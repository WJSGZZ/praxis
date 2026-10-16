---
name: praxis-causal-analysis
description: 把“改变某因素会怎样”转成明确干预、目标群体和效应，审查研究设计、时间顺序、混杂、选择与识别条件，条件成立后再估计并做敏感性。用于“这是因果吗、政策或处理有效吗、控制哪些变量、干预效应、识别不了怎么办”。Causal inference, intervention effects, identification, confounding, adjustment, treatment effects and study design. 预测或相关分析不自动升级为因果；统计估计交 praxis-statistics协作，完整建模仍归 praxis。
license: MIT
---

# Praxis · 因果问题与识别

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [causal-analysis.md](../../references/causal-analysis.md) 定干预版本、对照、时点、随访、目标群体与 ATE／ATT，区分关联、预测、情景与效应。
- 估计前画因果结构／时间线并记来源，核混杂、碰撞点、选择、测量、处理后变量及干扰，调整变量由结构决定。
- 写清随机化或观察／准实验的识别条件、依据、未可检验部分与失效影响，边界接 [mathematical-reasoning.md](../../references/mathematical-reasoning.md#干预与预测哪些结论能用于改变系统)。
- 条件支持再选调整、加权或标准化及推断；Statsmodels TreatmentEffect 按限定接口，实查重叠、极端权重、缺失与目标变化。
- 用负对照、安慰剂、设计诊断或未测混杂敏感性攻击主解释；不能识别时交关联、部分识别／情景或补充设计。
- 沿 [methods.md](../../references/methods.md) 交结构、条件、来源、估计和替代解释，用解析干预小例或非识别反例核计算，合成核验与真实设计分开。

## 交接

前提专审交 [assumptions](../praxis-assumptions/SKILL.md)，估计交 [statistics](../praxis-statistics/SKILL.md)，定义回 [model](../praxis-model/SKILL.md)，数据交 [data-analysis](../praxis-data-analysis/SKILL.md)，运行／核验交 [compute](../praxis-compute/SKILL.md)／[verify](../praxis-verify/SKILL.md)，成稿交 [report](../praxis-report/SKILL.md)。
