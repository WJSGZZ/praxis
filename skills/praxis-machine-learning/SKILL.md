---
name: praxis-machine-learning
description: 设计和核验监督预测：目标、人群和信息时点，独立或分组留出，训练内预处理，基线、调参与误差分析。用于“训练预测模型、分类/回归、交叉验证、模型是不是泄漏、哪个预测器好”。Supervised machine learning, regression, classification, cross-validation, grouped holdout, preprocessing leakage and predictive evaluation. 预测未来时间交 praxis-time-series；相关/预测不自动成为因果或真实产品缺陷认证。
license: MIT
---

# Praxis · 监督学习与预测验证

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [machine-learning.md](../../references/machine-learning.md) 定谁、何时、已知什么、预测什么与损失，核目标派生特征和重复主体。
- 按部署对象选 iid／group／时间留出；训练前定切分，同题暴露按 [learning-loop.md](../../references/learning-loop.md)，数据接 [data-computing.md](../../references/data-computing.md)。
- `cross_validate_predictor` 限数值 Ridge 与0/1 Logistic，显式 task／split，group 给完整 groups；逐折 Pipeline 填补／标准化并对照 Dummy，缺目标、非有限或无有效训练类保留拒绝。
- 锁定目标、损失、参数；编码、调参、阈值和概率校准仅在训练／内层做，需扩展用成熟 sklearn 与嵌套验证并保存实现。
- 交 OOF 预测、折索引／组、样本／类数、原尺度 RMSE／MAE 或 Brier／accuracy；核组权重、罕见类、移位及失败。
- 用手算基线、分母与真实泄漏反例核完整预测链；保留所有尝试，开发、最终测试与部署验证分开，折间离散保持原身份。

## 交接

测量交 [data-analysis](../praxis-data-analysis/SKILL.md)，未来交 [time-series](../praxis-time-series/SKILL.md)，因果交 [causal-analysis](../praxis-causal-analysis/SKILL.md)，实验交 [experimental-design](../praxis-experimental-design/SKILL.md)，区间交 [statistics](../praxis-statistics/SKILL.md)，运行／核验交 [compute](../praxis-compute/SKILL.md)／[verify](../praxis-verify/SKILL.md)。
