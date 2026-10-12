---
name: praxis-optimization
description: 把资源分配、调度、路径、多目标取舍与序贯决策写成目标、约束和信息明确的优化问题，选择求解方法、检查可行解与界、分析策略适用范围。用于“怎么优化、最优吗、整数规划、Pareto、稳健优化、CVaR、动态规划、求解无解”。Optimization, LP/MILP, constrained optimization, Pareto trade-offs, robust decisions and MDP. 指标排名不自动是优化；不以多起点一致或搜索失败证明全局最优／不可行。
license: MIT
---

# Praxis · 优化与决策

专业方法归 [optimization.md](../../references/optimization.md)。任务／前提与路线共用 [methods.md](../../references/methods.md)，实际运行和证据共用原计算管线。

## 调用契约

输入：决策变量与可用动作、目标及单位、硬／软约束、数据和不确定性、决策时可知信息、预算与接受精度。产出：明确模型、基线与所选方法、可执行方案、原始约束残差、目标与证明界／间隙、失败及条件建议。

## 专业处理

- 先核目标、约束和变量域，再识别线性、整数、网络、动态或非线性结构。能精确求解时优先已有HiGHS／SciPy、流与动态规划；手工可行方案或小例先检验符号、单位与信息条件。
- 按实际契约调用 `solve_lp`、`solve_milp`、`solve_assignment`、`min_cost_flow`、`knapsack`、`solve_mdp` 或 `minimize_nlp`，不猜字段或把另一个库的不等式符号套进来。
- 多目标先核支配与硬底线，再表达偏好；`pareto_front` 只筛给定点表。稳健系数模型可用 `robust_lp`，情景尾损失可用 `cvar_portfolio`，分布、动作与风险条件须单列。
- 原模型复评选定方案，区分可行解、收敛候选、松弛界和全局证明；限时整数解保留incumbent与gap，搜索未找到不等于无解。策略族／信息结构改变后不能继承旧最优性。
- 反向求资源时区分一个可行向量、某坐标必要下界和联合可行域；允许重新分配后，固定分配所需向量不是普遍必要条件。按optimization.md的“必要资源与可行见证”用割界／原问题求解和替代配置核验。
- 黑箱多目标或更复杂组合结构确有收益时，才核固定版本的pymoo／OR-Tools等外部工具与许可，在允许预算内适配；它们不是本插件默认安装依赖。

## 交接

目标或机制未定回 [praxis-model](../praxis-model/SKILL.md)，联合输入与决策稳健性交 [praxis-uncertainty-analysis](../praxis-uncertainty-analysis/SKILL.md)，实现运行交 [praxis-compute](../praxis-compute/SKILL.md)，独立最优性与约束证据交 [praxis-verify](../praxis-verify/SKILL.md)。需要论文交付时将实际方案、界和限制交 [praxis-report](../praxis-report/SKILL.md)，不只交一个最优值。
