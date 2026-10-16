---
name: praxis-statistics
description: 设计并完成与实际抽样和目标效应匹配的统计分析：独立、配对、重复或聚类样本，估计与区间、效应量、多重比较、缺失和诊断解释。用于“比较组间差异、怎么检验、这个CI怎么算、样本有依赖、多重比较、估计效应”。Statistical design, estimands, hypothesis tests, effect sizes, confidence intervals, paired or clustered observations and multiple testing. 因果识别交 praxis-causal-analysis；完整作品评价与独立数学认证另有入口。
license: MIT
---

# Praxis · 统计设计与推断

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [statistical-analysis.md](../../references/statistical-analysis.md) 定 estimand、群体、尺度和抽样／分配／分析单位，辨认配对、重复、聚类与时序依赖。
- 依设计预定方法，诊断用于质疑而非按 Shapiro／Levene 显著性切换；配对看差值，回归看残差，秩检验核目标含义。
- `hypothesis_test`／`ols_report` 先核条件；`sample_design.status='not_checked'` 保留未核，cluster 须 groups，HC3 与簇依赖分别处理；可选 GEE／MixedLM 按实际接口执行。
- 同报原尺度效应、方向、CI 构造、样本／独立单位数与缺失处理；CI、预测区间、可信区间、SD／SE和情景范围分清。
- 预定 `multiplicity-family` 与完整 hypothesis ID，`adjust_pvalues` 按目标和依赖选 Holm／Bonferroni／BH／BY，保留原始及校正 p 与效应。
- 用解析或精确小例核主要计算及坏输入；设计、探索偏离、实际结果与未确认前提沿 [methods.md](../../references/methods.md) 记录。

## 交接

测量交 [data-analysis](../praxis-data-analysis/SKILL.md)，因果识别交 [causal-analysis](../praxis-causal-analysis/SKILL.md)，定义／前提交 [model](../praxis-model/SKILL.md)／[assumptions](../praxis-assumptions/SKILL.md)，批次交 [compute](../praxis-compute/SKILL.md)，独立核验交 [verify](../praxis-verify/SKILL.md)，报告交 [report](../praxis-report/SKILL.md)。
