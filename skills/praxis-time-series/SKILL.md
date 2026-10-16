---
name: praxis-time-series
description: 设计和评估与真实信息时点、日历、实体和预测跨度一致的时序预测或动态统计模型，比较基线、处理趋势季节与外生变量、传播预测不确定性。用于“预测未来、时间序列、滚动回测、缺年份、一步还是多步、动态回归”。Time series forecasting, temporal models, forecast horizons, rolling-origin evaluation, calendar gaps and future regressors. 机制方程整体设计归 praxis-model；干预识别归 praxis-causal-analysis，不用拟合优度替代二者。
license: MIT
---

# Praxis · 时序预测与动态分析

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [time-series-analysis.md](../../references/time-series-analysis.md) 核实体、真实日历、目标、季节及突变；缺记录、未发生与真零分开。
- 列逐起点可知信息与字段版本账本，用 `asof_join` 核发布滞后／修订；多步预测的未知驱动另预测或设情景，保留缺时点和冲突。
- 依 [data-computing.md](../../references/data-computing.md) 在同起点、跨度、群体、信息和指标比较基线与候选，折内变换／选型，最终留出不参与筛选。
- `compare_models(scheme="time")` 是训练末端起点的块预测；逐跨度核 X 可得性。`backtest_baselines`、SARIMAX／状态空间和 `kalman_filter` 按真实接口及信息条件选择。
- 分别评数量、固定事件概率及行动代价，按实际投影／截断执行值选型；区间覆盖、失败／回退分母和尺度按 [scientific-foundations.md](../../references/scientific-foundations.md) 核。
- 交起点×跨度×实体的目标时间、截点、预测、基线与误差，保留失败与拒绝；核手算基线和泄漏／日历缺口反例。

## 交接

测量交 [data-analysis](../praxis-data-analysis/SKILL.md)，推断交 [statistics](../praxis-statistics/SKILL.md)，干预交 [causal-analysis](../praxis-causal-analysis/SKILL.md)，机制／前提交 [model](../praxis-model/SKILL.md)／[assumptions](../praxis-assumptions/SKILL.md)，运行与独立核验交 [compute](../praxis-compute/SKILL.md)／[verify](../praxis-verify/SKILL.md)。
