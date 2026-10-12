---
name: praxis-dynamical-modeling
description: 建立和核查随时间／空间演化的机制模型：守恒、ODE/PDE、初值边界、状态与观测、平衡稳定性、参数辨识及数值收敛。用于“写动力学方程、扩散／传热／种群模型、为何不守恒、边界怎么设、平衡稳定吗、步长和网格”。Mechanistic dynamics, ODE/PDE, conservation, initial and boundary conditions and numerical modeling. 纯时间序列预测归 praxis-time-series；一维求解器不冒充通用CFD或PDE软件。
license: MIT
---

# Praxis · 机制与动力学建模

专业深度归 [dynamical-modeling.md](../../references/dynamical-modeling.md)。实际领域机制见 [domain-models.md](../../references/domain-models.md)，独立数值规范共用 [scientific-foundations.md](../../references/scientific-foundations.md)。

## 调用契约

输入：研究对象、时空尺度与目标量、状态／单位、守恒和机制依据、初始及边界条件、参数／观测、允许控制与预算。产出：状态与观测方程、前提和量纲、解析基线或数值轨迹、守恒／边界／收敛检查、可辨识范围与实际预测／控制条件。

## 专业处理

- 区分守恒机制、经验状态模型和纯统计时序；先用足够回答任务的平衡或解析关系，只有时空异质性会改变答案才增加ODE/PDE。
- 方程含所有参与动力学的状态；逐项核流入流出、源项、参数与量纲。说明初态如何获得、边界作用及观测对应，不以隐藏真值作为可免费测量的状态。
- 现有 `solve_ode`、`sir_simulate`、`sir_fit`、`equilibria`、一维 `solve_diffusion`／`solve_layered_diffusion` 按实际范围选择；需要时用原模型代码调用成熟SciPy，不能向MCP传未注册的events等字段。
- 校准误差、机制适用与求解误差分别判断。核守恒、非负性、解析特例、有效初值与相同物理量的网格／时间比较；有限多起点平衡搜索或数值稳定性不作完整证明。
- 受约束动态决策须查控制切换、极值及采样之间；只有方案自己的证据才能支持它。数值失败、模型失配和真实不可行分别记录。

## 交接

任务／前提有误回 [praxis-model](../praxis-model/SKILL.md)，未来信息和统计外推交 [praxis-time-series](../praxis-time-series/SKILL.md)，控制优化交 [praxis-optimization](../praxis-optimization/SKILL.md)，输入与结构情景交 [praxis-uncertainty-analysis](../praxis-uncertainty-analysis/SKILL.md)，独立结论核验交 [praxis-verify](../praxis-verify/SKILL.md)。实现、运行与报告沿 praxis-compute／praxis-report；不另建模拟平台或物理“真值”标签。
