---
name: praxis-machine-learning
description: 设计和核验监督预测：目标、人群和信息时点，独立或分组留出，训练内预处理，基线、调参与误差分析。用于“训练预测模型、分类/回归、交叉验证、模型是不是泄漏、哪个预测器好”。Supervised machine learning, regression, classification, cross-validation, grouped holdout, preprocessing leakage and predictive evaluation. 预测未来时间交 praxis-time-series；相关/预测不自动成为因果或真实产品缺陷认证。
license: MIT
---

# Praxis · 监督学习与预测验证

专业判断归 [machine-learning.md](../../references/machine-learning.md)，数据接收与契约共用 [data-computing.md](../../references/data-computing.md)。单独预测任务直接进入，不要求先形成完整论文。

## 调用契约

输入：预测对象及使用场景、目标与损失、行/组身份、信息可用时间、特征及缺失来源、历史分割和已看过的结果。产出：可复验的分割与特征契约、同条件基线和候选预测、折内与OOF误差、子群/失败分析、部署范围及未验条件。目标或预测时点不清时先澄清定义，不把高拟合分数当作回答。

## 专业判断与执行

- 确定一次预测对应谁、何时、已知什么、预测什么；连续值、二类概率、计数、排序与代价敏感标签需不同损失。每个特征注明当时可得依据，目标派生字段、重复主体和同源文本不能跨留出形成泄漏。
- 独立可交换行用明确的iid分割；重复患者、产品、学校或地块的跨新主体任务按group整体留出。预测未来交 [praxis-time-series](../praxis-time-series/SKILL.md)，随机分割或把年号设group不能认证未来外推。已有同题/最终测试暴露共用 [learning-loop.md](../../references/learning-loop.md)。
- `cross_validate_predictor`实际支持数值Ridge回归和0/1 Logistic分类，显式`task`、`split`；group必须给完整groups。工具逐折fit成熟Pipeline的中位数填补与标准化，并与仅用训练目标的Dummy比较。null特征可填补，缺失目标和非有限输入拒绝；训练折全缺失列或缺训练类别时拒绝，不能静默丢坏折。
- 锁定目标、分割、损失与候选参数，再比较。调参、筛特征、编码、阈值和概率校准均只能在训练/内层验证中学习；本工具不做调参或校准。需要这些时用成熟sklearn Pipeline/ColumnTransformer和嵌套验证，在用户项目保留实际实现与数据身份。
- 报实际OOF预测、每折索引/组、样本和类别数、模型及Dummy的同一指标；回归用原尺度RMSE/MAE，分类区分Brier概率误差与固定阈值accuracy。总体行权重不等于每组同权；小簇、罕见类、分布移位、残差形状和失败案例需要相称检查。

## 验证、交付与回退

先核可手算预测/基线、分母和真实泄漏反例，再审完整预测链；训练成功不能认证特征可得、组独立、外部校准或因果。保留原分割、所有尝试和OOF输出，区分开发比较、独立最终测试与部署后验证。折间离散不直接给置信区间；重复同一测试选最好也不再是未见检验。

数据测量/连接交 [praxis-data-analysis](../praxis-data-analysis/SKILL.md)，干预识别交 [praxis-causal-analysis](../praxis-causal-analysis/SKILL.md)，实验收集交 [praxis-experimental-design](../praxis-experimental-design/SKILL.md)，统计区间交 [praxis-statistics](../praxis-statistics/SKILL.md)。可复现运行与独立主张核验分别共用 [praxis-compute](../praxis-compute/SKILL.md)／[praxis-verify](../praxis-verify/SKILL.md)。
