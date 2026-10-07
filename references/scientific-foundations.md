# 科研基础：不确定性、数值误差与统计检验的规范

建模结论的可信度取决于三件事：输入有多不确定、数值计算有多大误差、统计推断有没有按规范做。这份参考给出各自的最低做法。按需读对应一节，不当作必经步骤。

## 一、不确定性：先分清是哪一种

| 类型 | 含义 | 例子 | 怎么处理 |
|---|---|---|---|
| 参数不确定 | 参数值未知但结构正确 | 损失系数的范围 | 范围或分布，传播到结果，做全局敏感性 |
| 输入或测量不确定 | 数据有噪声 | 温度读数 | 误差模型；重复测量；误差传播 |
| 结构不确定 | 模型本身是近似 | 把人体当固定温度热库 | 换模型对比；情景；不用概率去包装 |
| 数值不确定 | 离散与舍入误差 | 网格、步长 | 收敛研究（见第二节） |
| 随机变异 | 系统本身随机 | 到达过程 | 概率模型；重复仿真给区间 |

不同类型不能混成“一个概率”。结构不确定与缺乏依据的参数范围，只能写成情景，不能当作置信区间或发生概率。

**传播的方法**：小模型用一阶误差传播或解析式；一般用蒙特卡洛或拉丁超立方；要分解“谁贡献了不确定性”用 Sobol 全局敏感性（`sobol_sensitivity`，限独立均匀输入与确定性标量输出）；模型昂贵时先训练代理模型并验证代理误差。样本量要通过收敛检查确定，而不是凭感觉。

**怎么报告**：对测量类结果按《测量不确定度表示指南》（JCGM 100:2008，GUM）：A 类（重复观测的统计）与 B 类（其他信息）分量合成为标准不确定度，再乘包含因子 k（正态近似下 k=2 约对应 95%）；写成“估计值 ± U（k=2）”，并说明分布假设。区间必须说明它是什么：置信区间、可信区间、预测区间还是情景范围；预测区间不同于均值的置信区间。

## 二、数值误差：验证先于验证现实

“验证”（verification）回答“方程解对了吗”，“确认”（validation）回答“方程对吗”。两者不能互相代替；先验证，再确认。

- **误差来源**：截断误差（离散）、舍入误差（有限精度，双精度机器精度约 2.2e-16）、迭代误差（求解器容差）、模型误差。
- **一致、稳定、收敛**：线性适定问题中，相容加稳定等价于收敛（Lax 等价定理）。数值格式要查稳定性条件（如显式扩散格式的步长限制），隐式格式无条件稳定但精度仍受步长限制。
- **观测收敛阶**：用系统加密的三套网格，观测阶 p = ln((f₃−f₂)/(f₂−f₁)) / ln r（r 为加密比）；理查森外推值 f₁ + (f₁−f₂)/(rᵖ−1)。`grid_convergence_index` 给出观测阶、外推值与网格收敛指数（Roache 提出，三套网格常用安全系数 1.25）。观测阶应接近格式的设计阶，否则误差不主要来自网格，或没有进入渐近区。
- **被约束的量也要收敛**：目标量收敛不代表被约束的量收敛，点源、尖角处尤其如此（见 [mathematical-reasoning.md](mathematical-reasoning.md) 的“数值收敛”）。
- **条件数**：相对误差大致不超过条件数乘以机器精度。条件数很大时，结果的有效数字少于输入精度；`numpy.linalg.cond` 可估计；病态问题要重新表述（缩放、正则化、换基）。
- **灾难性相消**：两个相近的大数相减会丢精度；改写公式（如 log1p、expm1、对数和指数技巧）。
- **ODE 容差**：`rtol` 与 `atol` 要写出并做敏感性；用另一个积分器或更紧容差复算；事件检测要检查漏检。
- **求解器报告**：优化与整数规划看返回状态、间隙与可行性容差；“成功”不等于全局最优。

## 三、统计检验：做之前就要规定的事

- **先规定假设与分析方案**，再看数据。看完数据再选检验或分组，会让 p 值失去含义（分叉路径）。探索性发现要标为探索性。
- **效应量加区间，而不只是 p 值**。报告效应大小、置信区间、样本量与确切 p 值；“显著”不等于“重要”，“不显著”不等于“无差异”。美国统计学会 2016 年声明（Wasserstein & Lazar, *The American Statistician* 70:129）给出六条关于 p 值的原则：p 值不衡量假设为真的概率，也不衡量效应大小，不应只凭是否过 0.05 下结论。
- **检验前检查假设**：独立性、分布形态、方差齐性、线性；用残差图与诊断而不是只看检验。违反时换稳健或非参数方法，或用自助法（bootstrap）估计区间。
- **多重比较要校正**：做 m 次检验，至少一次假阳性的概率快速上升。控制族错误率用 Bonferroni 或 Holm（Holm, 1979）；探索性大量检验控制错误发现率用 Benjamini–Hochberg（1995）。
- **功效与样本量**：先估计要检出的最小效应所需样本量；样本很小时不做强结论。
- **预测模型的评估**：按时间或分组留出；预处理只用训练信息；调参只用训练折；最终留出集只用一次。交叉验证的指标要给区间。
- **因果与相关**：观察数据的关联不是干预效应；要说“改变 X 会怎样”，须写明识别假设并做反驳检验。
- **贝叶斯结果**：区间以模型与先验为条件，做先验与后验预测检查，并做先验敏感性；不与频率学派置信区间混称。

## 四、检查清单（交付前过一遍）

1. 报告的每个区间是否说明了它是什么？
2. 结构不确定和无依据的范围是否写成情景而不是概率？
3. 关键数值是否在至少三套网格或步长下收敛，被约束的量是否也收敛？
4. 检验方案是否在看数据前规定，多重比较是否校正，效应量与区间是否一并报告？
5. 预测评估是否把最终留出集与调参分开？

## 来源

- JCGM 100:2008，*Evaluation of measurement data — Guide to the expression of uncertainty in measurement*（GUM）。
- Roache，“Perspective: A method for uniform reporting of grid refinement studies”，*Journal of Fluids Engineering* 116(3):405–413，1994；Roache，*Verification and Validation in Computational Science and Engineering*，Hermosa，1998。
- ASME V&V 20-2009，*Standard for Verification and Validation in Computational Fluid Dynamics and Heat Transfer*。
- Lax 与 Richtmyer，“Survey of the stability of linear finite difference equations”，*Communications on Pure and Applied Mathematics* 9:267–293，1956。
- Wasserstein 与 Lazar，“The ASA's statement on p-values: context, process, and purpose”，*The American Statistician* 70(2):129–133，2016。
- Holm，“A simple sequentially rejective multiple test procedure”，*Scandinavian Journal of Statistics* 6:65–70，1979。
- Benjamini 与 Hochberg，“Controlling the false discovery rate”，*Journal of the Royal Statistical Society B* 57(1):289–300，1995。
