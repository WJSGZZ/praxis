---
name: praxis-time-series
description: 设计和评估与真实信息时点、日历、实体和预测跨度一致的时序预测或动态统计模型，比较基线、处理趋势季节与外生变量、传播预测不确定性。用于“预测未来、时间序列、滚动回测、缺年份、一步还是多步、动态回归”。Time series forecasting, temporal models, forecast horizons, rolling-origin evaluation, calendar gaps and future regressors. 机制方程整体设计归 praxis-model；干预识别归 praxis-causal-analysis，不用拟合优度替代二者。
license: MIT
---

# Praxis · 时序预测与动态分析

专业深度归 [time-series-analysis.md](../../references/time-series-analysis.md)。共用 [data-computing.md](../../references/data-computing.md) 的训练／留出契约与 [scientific-foundations.md](../../references/scientific-foundations.md) 的误差及尺度规范；不另建回测流水线。

## 调用契约

输入：预测／动态问题、实体和真实时间索引、历史观测与发布时点、使用时可知的变量、预测起点／跨度、损失和目标群体。产出：信息与时间契约、基线和候选模型的同条件回测、按跨度／组别的误差与区间、有效未来预测或有界情景、稳定性及未验限制。

## 专业判断与执行

- 先辨认规则／不规则日历、重复实体、季节周期、结构突变和目标量；缺记录、未发生与真零分开。排好行序不等于修复日历，删掉缺失年份不能将相邻行当相邻年。
- 每个预测起点列可知信息，检查特征事件时间、发布滞后、修订和实体边界。一步滚动可用已到达的下一期历史，多步开放预测不能读未来真实滞后；未知未来驱动变量用独立预测或明确情景，并传播其不确定性。
- 相同起点、群体、跨度、可用信息、指标和预算比较朴素／季节朴素等基线与候选。训练中的变换与调参逐折完成；最终留出目标不参与筛选。`TimeSeriesSplit`按行给索引，不能自动解决不规则日历、发布延迟或组泄漏。
- `compare_models(scheme="time")`的test块共用训练末端起点，baseline不读test y；这不是一步滚动。核X[test]各列在起点是否可知，按实际h解释混合块误差；fold标准误和`beats_baseline`提示不能替代正式推断。
- 已有 `backtest_baselines` 及相称Statsmodels `SARIMAX`／状态空间接口优先，线性高斯状态估计可用 `kalman_filter` 的实际矩阵契约，只有数据／结构需要才增加复杂度。季节周期和差分有解释，短序列不够就收窄模型；诊断不显著不证明平稳或白噪声。外生字段同名不证明未来可获得。
- 按实际部署跨度评估误差、区间覆盖和代价；还原差分／对数／季节尺度与联合不确定性。动态机制的守恒、稳定性或可辨识性另交相应模型与验证入口，不能凭高预测分数认证机制。

## 交付、验证与回退

保留起点×跨度×实体的真实目标时间、信息截点、预测／区间、基线及误差；说明缺失、拒绝预测、失败拟合、变化的目标与模型。核一个可手算递推／已知基线和当前信息泄漏或日历缺口反例，实际未测的跨度与新实体不外推验收。

数据单位／连接缺口交 [praxis-data-analysis](../praxis-data-analysis/SKILL.md)，依赖推断与多重比较交 [praxis-statistics](../praxis-statistics/SKILL.md)，干预问题先交 [praxis-causal-analysis](../praxis-causal-analysis/SKILL.md)。机制／任务要改时回 [praxis-model](../praxis-model/SKILL.md)，前提专审交 [praxis-assumptions](../praxis-assumptions/SKILL.md)，运行／证据与独立核验分别交 [praxis-compute](../praxis-compute/SKILL.md)／[praxis-verify](../praxis-verify/SKILL.md)。
