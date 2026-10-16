---
name: praxis-dynamical-modeling
description: 建立和核查随时间／空间演化的机制模型：守恒、ODE/PDE、有限状态转移、初值边界、状态与观测、平衡稳定性、参数辨识及数值收敛。用于“写动力学方程、扩散／传热／种群模型、马尔可夫迁移、转移矩阵、为何不守恒、边界怎么设、步长和网格”。Mechanistic dynamics, ODE/PDE, Markov population transitions, conservation, initial and boundary conditions and numerical modeling. 纯时间序列预测归 praxis-time-series，决策优化归 praxis-optimization；一维求解器不冒充通用CFD或PDE软件。
license: MIT
---

# Praxis · 机制与动力学建模

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [dynamical-modeling.md](../../references/dynamical-modeling.md) 区分守恒机制、经验状态与统计时序；先平衡／解析，异质性影响答案再加 ODE/PDE。
- 状态／观测方程逐项核对象、量纲、流与源、初态来源及边界；机制与量级接 [domain-models.md](../../references/domain-models.md)。
- 活动压力与服务对象存量分别入账；用相同存量／充足供给对照后再核受限服务，修耦合重算实际下游。
- 有限状态转移核方向、非负质量、归一、零分母、吸收边界与多步传播；连续速率、一步概率与平稳分布分开。
- 按范围选 `solve_ode`、SIR、`equilibria` 或一维扩散；核真实接口，需扩展时在项目用成熟 SciPy。
- 按 [scientific-foundations.md](../../references/scientific-foundations.md) 分别核校准、机制、求解误差、守恒、非负、解析极限及收敛；控制检查切换、极值和采样间，失败身份分别保留。

## 交接

定义回 [model](../praxis-model/SKILL.md)，预测交 [time-series](../praxis-time-series/SKILL.md)，控制交 [optimization](../praxis-optimization/SKILL.md)，情景交 [uncertainty-analysis](../praxis-uncertainty-analysis/SKILL.md)，运行／核验／报告交 [compute](../praxis-compute/SKILL.md)／[verify](../praxis-verify/SKILL.md)／[report](../praxis-report/SKILL.md)。
