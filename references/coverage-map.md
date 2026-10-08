# 能力覆盖地图：哪些问题结构有现成路线，哪些没有

用途：拿到陌生题、判断出数学结构之后，查这里有没有现成工具；没有时看后备路线，不要硬套手边的工具。目标不是列出所有算法，而是**每一类常见建模结构至少有一条可靠、可验证的路线**。工具名见 [tool-index.md](tool-index.md)，用法和必做检查见 [model-library.md](model-library.md)。

图例：**工具** = 有带检查的现成工具；**库** = 无专门工具，用 scipy、statsmodels、scikit-learn、networkx、OR-Tools（需自装）等直接写，仍按本技能的验证要求核对；**缺** = 没有现成路线，后备办法写在最后一列。

| 结构 | 状态 | 起点 | 没有现成工具时的后备 |
|---|---|---|---|
| 线性、整数规划 | 工具 | `solve_lp`（对偶与影子价格）、`solve_milp`（界与间隙） | — |
| 非线性规划 | 工具 | `minimize_nlp`（多起点，列出各局部最优） | 凸性用 `probe_structure` 判断，凸才可称全局 |
| 不确定系数下的稳健决策 | 工具 | `robust_lp`（预算型）、`sobol_sensitivity` | 随机规划：情景展开成大规模 LP |
| 背包、指派、旅行商、匹配 | 工具 | `knapsack`、`solve_assignment`、`solve_tsp`（带下界） | 更大规模调度、装箱：OR-Tools CP-SAT／MILP 建模并报告间隙 |
| 车辆路径、作业车间调度、设施选址 | 库 | MILP 建模或 OR-Tools | 先用小规模精确解校验启发式，报告与下界的差距 |
| 网络：最短路、最大流、最小生成树、最小费用流 | 工具 | `shortest_path`、`max_flow`、`minimum_spanning_tree`、`min_cost_flow` | 中心性、社区：networkx |
| 分阶段决策、马尔可夫决策 | 工具 | `solve_mdp`（精确逆向递推或值迭代）、`markov_*` | 状态空间过大：近似动态规划，须与小规模精确解对照 |
| 博弈 | 工具 | `matrix_game`、`bimatrix_nash` | 多人、动态博弈：库，写清均衡概念 |
| 评价、权重、方案排序 | 工具 | `evaluate_alternatives`、`ahp_weights`、`entropy_weights`、`pareto_front` | 先查支配，再谈权重 |
| 回归与预测 | 工具 | `ols_report`、`compare_models`、`backtest_baselines`、`arima_forecast`、`gm11_forecast` | 结构时间序列、面板数据：statsmodels |
| 假设检验、区间估计 | 工具 | `hypothesis_test`（含效应量）、`bootstrap_ci` | 多重比较、贝叶斯推断：库（PyMC 自装） |
| 降维、聚类 | 工具 | `pca_report`、`cluster_report`（含稳定性） | 分类、深度学习：scikit-learn，必须有留出集与基线 |
| 随机模拟、不确定性传播 | 工具 | `monte_carlo`（误差与收敛）、`sobol_convergence`、`queue_mmc` | 离散事件仿真：SimPy 或自写，固定种子并重复 |
| 常微分方程 | 工具 | `solve_ode`（紧容差复算）、`calibrate_curve`、`equilibria` | 最优控制：先写出哈密顿量，再用 `minimize_nlp` 做直接法 |
| 偏微分方程（一维扩散、分层导热） | 工具 | `solve_diffusion`、`solve_layered_diffusion`、`layered_diffusion_laplace`、`grid_convergence_index` | 二、三维：有限元或有限体积库，网格收敛不可省 |
| 传染病、种群 | 工具 | `sir_simulate`、`sir_fit` | 年龄结构、网络传播：库 |
| 状态估计 | 工具 | `kalman_filter` | 非线性滤波：库 |
| 库存、金融 | 工具 | `eoq`、`newsvendor`、`cvar_portfolio` | 期权定价：解析式见 domain-models.md |
| 结构探索、反例、猜想 | 工具 | `probe_structure`、`find_counterexample`、`guess_sequence`、`find_relation`、`dimensional_analysis` | — |
| 空间统计、地理优化、图像与信号 | 缺 | — | 用库实现；这类题先回到机制和量纲，再决定是否值得做 |
| 符号推导 | 库 | sympy | 推导后用 `test_conjecture` 数值核对 |

## 用法

1. 判断结构后查此表；状态为“工具”，先用工具得到可核对的基线。
2. 状态为“库”或“缺”，在路线记录里写明：为什么选这条后备路线，它缺哪些现成检查，补了哪些独立核对。这是补缺口，不是降低标准。
3. 发现一类结构反复缺工具，说明该补工具了：先写已知答案的测试（暴力枚举、解析解、独立算法），再登记进工具表。
4. 工具数量不是目标。选型仍按 [path-search.md](path-search.md)：至少两条候选路线，写出放弃理由，用验证结果而不是工具的新旧来决定。
