---
name: praxis-experimental-design
description: 在采数据前设计能回答目标问题的实验：处理与对照、随机化单位、区组/因子、精度或功效、主要结局和停止规则。用于“怎么设计实验、A/B测试、试验要多少样本、控制混杂、区组/析因、什么时候停止”。Experimental design, randomization, blocking, factorial experiments, sample size, precision, power and stopping rules. 已有观测数据的EDA交 praxis-data-analysis，分析与区间交 praxis-statistics，因果识别共用 praxis-causal-analysis。
license: MIT
---

# Praxis · 实验设计与证据收集

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [experimental-design.md](../../references/experimental-design.md) 定处理、比较、目标效应、最小有意义差异与结局；随机化、观察及分析单位分别明确。
- 写分配的执行与留存，纳入配对、重复、交叉、批次、时间顺序、干扰和现实限制；按预处理异质性选区组，交互问题比较析因／部分因子及混叠。
- 精度／事前功效说明差异、方差／事件率、alpha、allocation 与独立单位；缺方差或 ICC 给范围及先导动作，Statsmodels 或模拟须匹配设计。
- 开始前固定主要结局、比较族、纳排、缺失／遵从、样本和停止规则；序贯查看用相应方法，保留偏离、失访与中止。
- 核分配单位、处理覆盖、区组、重复身份、seed 与分配前信息，用独立已知精度／功效例验证调用。
- 交真实协议、分配与测量计划、条件依据及可验证范围，协议完成与实验执行分别记。

## 交接

识别交 [causal-analysis](../praxis-causal-analysis/SKILL.md)，推断交 [statistics](../praxis-statistics/SKILL.md)，测量交 [data-analysis](../praxis-data-analysis/SKILL.md)，运行／核验交 [compute](../praxis-compute/SKILL.md)／[verify](../praxis-verify/SKILL.md)，预测验证交 [machine-learning](../praxis-machine-learning/SKILL.md)，成稿交 [report](../praxis-report/SKILL.md)。
