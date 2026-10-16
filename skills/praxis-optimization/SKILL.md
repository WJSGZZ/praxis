---
name: praxis-optimization
description: 把资源分配、调度、路径、多目标取舍与序贯决策写成目标、约束和信息明确的优化问题，选择求解方法、检查可行解与界、分析策略适用范围。用于“怎么优化、最优吗、整数规划、Pareto、稳健优化、CVaR、动态规划、求解无解”。Optimization, LP/MILP, constrained optimization, Pareto trade-offs, robust decisions and MDP. 指标排名不自动是优化；不以多起点一致或搜索失败证明全局最优／不可行。
license: MIT
---

# Praxis · 优化与决策

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [optimization.md](../../references/optimization.md) 定变量域、目标／单位、约束、可用信息及接受精度；用可行基线或小例核符号与机制。
- 识别线性、整数、网络、动态或非线性结构，按实际契约选 `solve_lp`／`solve_milp`、分配、流、背包、MDP 或 NLP。
- 多目标先核支配与硬底线再表达偏好；`pareto_front` 只筛给定点，`robust_lp`／`cvar_portfolio` 显式列分布、动作与风险条件。
- 在原约束复评方案，分别报可行向量、残差、候选、界与 gap；换策略族或信息结构重核保证。
- 反求资源区分可行见证、单坐标必要界和联合可行域，用割界／原问题与替代配置核验；条件和失败沿 [methods.md](../../references/methods.md) 留存。
- pymoo／OR-Tools 仅在确需时核固定版本、许可与预算；它们是可选依赖。

## 交接

定义回 [model](../praxis-model/SKILL.md)，联合不确定性交 [uncertainty-analysis](../praxis-uncertainty-analysis/SKILL.md)，实现交 [compute](../praxis-compute/SKILL.md)，独立最优性／约束交 [verify](../praxis-verify/SKILL.md)，方案、界与限制交 [report](../praxis-report/SKILL.md)。
