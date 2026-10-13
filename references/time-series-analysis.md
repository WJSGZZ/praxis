# 时序信息、预测与动态统计

由 [praxis-time-series](../skills/praxis-time-series/SKILL.md)调用。训练／留出契约共用 [data-computing.md](data-computing.md)，尺度与区间共用 [scientific-foundations.md](scientific-foundations.md)，机制方程与数值误差仍归 [scientific-foundations.md](scientific-foundations.md)／[mathematical-reasoning.md](mathematical-reasoning.md)。模型拟合与干预识别是两类判断。

## 预测契约先决定评价

明确预测起点、实际目标日期、跨度h、实体／地点、预测量和损失。每条输入标事件时间、发布／可获取时间和修订版本；起点时可知的信息才可作特征。真正可知的日历与已定计划可以使用，未来天气、未知政策响应或未来结果滞后不能因为数据表存在就视为已知。

规则时间、季节周期、重复实体、缺时点与结构变化先核定义。缺一年的表必须保留真实年间隔，不能按删行后的索引做一年差分。对不规则观测可使用适合的模型／真实时间特征，或给有科学理由的规则化方法和敏感性，不能静默插值成新增观测。个体随访与汇总宏观序列的单位不同，组别一换，推广主张也换。

必须分开以下任务：

- 一步滚动预测：每到一个新时点允许纳入已实际到达的观察。
- 从起点开放多步预测：后续真实目标尚未到达，递推只能使用预测／可知驱动；直接多步也需各h的信息契约。
- 动态机制模拟／情景：给定驱动与结构的条件结果，不自动是可部署预测或干预证据。

一步效果不能为开放多步背书；把未来真实滞后补进测试特征会改变任务。未知外生变量需另预测或给显式情景，并计入误差；真实未来外生值下的回测只能称该信息条件下结果。

外生字段和历史目标可能被修订。逐起点保存实体×事件×字段的可用版本账本，调用 `asof_join` 返回当时可用的原行索引，再构造训练与预测特征；具体语义及未决政策共用 [data-analysis.md](data-analysis.md#按决策时刻选择数据版本)。单个记录日期不能代表所有字段的发布时点。缺时点或冲突的查询保留在原目标名单，标明未预测／未决，不能以最终快照补齐再称实时回测。改变起点之后的版本值应不影响该起点预测，这是信息边界检查，不能单独证明实际来源可用或预测性能。

## 同条件基线与路线选择

先用已存在 `backtest_baselines` 比较朴素、季节朴素、漂移／趋势等实际支持的基线，核其输入频率、季节和跨度。候选在同一目标、信息、起点／h、群体、指标和预算下比较，不只展示胜出的窗口。短序列、不足季节周期、频率不齐时收窄候选，复杂模型不能补出历史信息。

该名称是 MCP 工具名，其现有 Python 适配调用 `modeling.forecast.rolling_origin`，不是 `modeling.inference.backtest_baselines`。用 `python -m scripts.mcp_server --describe backtest_baselines` 核完整参数；不能因猜错 import 而判断工具不存在。工具的起点、默认训练长度与输出跨度也必须匹配本任务，不能直接把不同折或不同目标的平均误差拼在一起。

已有Statsmodels `SARIMAX`／状态空间可处理有理由的趋势、季节、动态回归和误差结构；先核季节s、差分和外生项的含义、辨识与样本支持。`kalman_filter(F,H,Q,R,x0,P0,observations)`提供限定的线性高斯filter：核状态／观察单位、矩阵维度、过程／观察协方差及初值；过滤历史状态不自动成为任意h预测或因果模型。`enforce_stationarity`或诊断不拒绝不证明整个现实过程平稳。AIC与残差诊断只在相称设定中解释，不代替未来回测；拟合优度不认证机制。

`get_forecast(steps=..., exog=...)`给未来点及区间相关结果；使用实际模型的未来外生维度、顺序和日期，不能把正确shape当正确可用信息。默认预测观察与 `signal_only`有不同不确定性定义；差分／对数／标准化及季节还原要回报告尺度，具体联合传播按scientific-foundations.md。参数、结构与未知驱动不确定性是否纳入另说明。

## 评价划分与指标

按真实时间取rolling-origin或相应窗口，起点前完成各折处理、选型和重训。选择最终参数后才进入未参与结构／阈值选择的留出目标；若看过反馈再修改，该集合属于开发，不能保持“未见”标签。

Scikit-learn `TimeSeriesSplit(gap=..., test_size=..., max_train_size=...)`是行索引划分器。gap不是日历天数，也不自动解决标签覆盖窗口、发布滞后或实体泄漏；可比fold时长要求相应规则间隔，多个实体要另设计组／时间划分与目标日期。按时间排所有行但把同对象未来结果混入过去训练仍可能泄漏。

已有 `compare_models(X,y,scheme="time",folds=...)`以每折训练末端为固定起点，整块test共同用该起点信息；朴素baseline将最后训练值保持到整块结束，不用test中的真实y滚动更新。这是 `fixed_origin_test_blocks`，不是一步滚动。X[test]各列也必须在起点已知或来自声明的预测／情景，否则模型虽不读取test y仍可能泄漏。fold RMSE混合多个h，应按部署需要另看各跨度；工具的fold标准误与`beats_baseline`一标准误规则是比较提示，不是独立折的正式检验／覆盖保证。随机kfold方案仍按新对象／独立样本条件解释，不能用于时序部署认证。

保存起点×h×实体的目标日期、可知截点、实际观察、预测、区间和误差。指标选原尺度MAE／RMSE／有意义的相对损失等；MAPE遇零或近零需另选或声明。看按h、季节、关键组和结构变化的误差、coverage与宽度，整体均值不能掩盖无预测或失败组。区间覆盖不是置信区间正确性的全局认证，也不证明分布外行为。

## 相称核验与失败返回

对已知递推／基线先手算；制造真实日历缺口、同实体跨折、起点后外生值或未来真实lag的反例检查契约。误差算法可对独立逐项汇总，避免仅调用同一评分函数再当答案。

出现数据／日历错误回data-analysis；目标跨度或信息条件不可能回praxis-model收窄任务或请求必要输入；主要数学数值交praxis-verify。预测失败、拒绝、未知驱动和未测h保留，不能删去后让平均误差变好。需要干预主张先走 [causal-analysis.md](causal-analysis.md)，运行交automation，不新建第二套回测状态。

## 第一手来源与复用范围

- Statsmodels固定 `35a8e0b`，BSD-3-Clause：[SARIMAX](https://github.com/statsmodels/statsmodels/blob/35a8e0b7483211f5be7e60926be082136263cac3/statsmodels/tsa/statespace/sarimax.py)、[MLEModel及get_forecast](https://github.com/statsmodels/statsmodels/blob/35a8e0b7483211f5be7e60926be082136263cac3/statsmodels/tsa/statespace/mlemodel.py)。[官方预测示例](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_forecasting.html)说明结果对象与逐起点评价；接口以实际锁定安装核对。
- Scikit-learn `1.9.1`固定 `866c0f51`，BSD-3-Clause：[TimeSeriesSplit实际实现](https://github.com/scikit-learn/scikit-learn/blob/866c0f51e7560ef0303cbcc5f159df5382ea9e3f/sklearn/model_selection/_split.py)。本参考不声明所有时序或状态空间算法已经执行／验证。
