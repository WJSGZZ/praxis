# 统计设计、估计与推断

由 [praxis-statistics](../skills/praxis-statistics/SKILL.md)调用。共用 [scientific-foundations.md](scientific-foundations.md)的不确定性和尺度规范、[methods.md](methods.md)的证据层次；本参考补具体设计选择，不把诊断是否显著变成自动换检验规则。可复现运行仍归 [automation.md](automation.md)。

## 从目标效应推到分析设计

先记录 estimand：群体与选择范围、结果／单位／时点、比较或干预、估计量和尺度。均值差、分位数差、概率差、赔率比与分布排序回答不同问题。然后明确抽样／分配单位、分析单位、配对身份、组／批次／时间相关、协变量可用时点、缺失及权重。100行来自5个实体的重复测量不能直接作为100个独立样本；配对不是两数组长度相等，而是同一已核单位的差值。

| 问题和真实设计 | 可选成熟计算 | 决定前必须核对 |
|---|---|---|
| 独立群体的连续均值差 | SciPy Welch t／适配的 `hypothesis_test(kind="welch_t")` | 选择与独立单位、效应方向、极端尾部与小样本、均值是否目标 |
| 同一对象的前后／配对差 | 对齐差值的配对t／适配工具 | 配对键、差值尺度、缺失对如何处理；诊断差值而非两组边际 |
| 分布／随机排序差异 | Mann–Whitney等秩方法 | 目标是否分布或排序、平移解释条件、ties／零差／精确性；不自动解释为中位数差 |
| 依赖或重复测量的平均关联 | Statsmodels GEE／MixedLM，或明确聚类的OLS | 组間条件、簇数／大小、结果分布、均值与相关结构；有限簇不因大行数可靠 |
| 比例、二元、计数或生存结果 | 对应分布与设计的成熟模型 | 分母／暴露、独立性、过度离散／删失；不硬套连续t检验 |
| 时序误差、动态关联 | 有理由的HAC／误差结构，或时序模型 | 真正顺序、带宽／滞后、日历和依赖条件，交time-series参考 |

表是条件入口，不是要求每题试遍算法。诊断模型形态、异常影响和可辨识性，再按已规定方案或科学理由做敏感性；Shapiro不拒绝不证明正态，Levene不拒绝不证明同方差，更不证明独立。秩变换可能改变estimand；HC3不能修复混杂、聚类或错误均值模型。`hypothesis_test`返回的estimand用于说明计算目标，`sample_design.status="not_checked"`及requirements必须与真实设计审查分开；flags为空不意味着这些条件已经成立。

## 工具、效果与区间要绑定同一个设计

已有 `ols_report(X, y, ..., covariance="cluster", groups=...)`提供显式一维分组的CRV1协方差和基于G−1自由度的t推断；使用前核该版本的支持选项、对齐、组间独立与簇数。小样本修正不能保证少量簇下有效，需设计相称的限制／敏感性。其他结构用Statsmodels GEE或MixedLM：前者估群体平均关联，后者需随机效应分布／组间结构。不要把两个软件输出相似当设计证据。

已有 `bootstrap_ci`假设独立观察。重复测量需按实体或簇抽整个单位；配对须一起重采样，时序可考虑有理由的block方案。库版本和“bootstrap”名称不确认重采样单位正确。其他API是可选成熟路线，只有实际执行与核过的部分才写通过。

稀有事件重采样可能没有阳性。按科学指标定义逐项保留状态：AP或recall在零阳性时若未定义，输出null及原因；若采用软件的零值约定，明示约定及其解释。对非空二元评价样本和有效概率预测，Brier在零阳性时仍有定义，应保留全部重采样值，不能复用AP的“只留有阳性”筛选。报告总抽样次数、零阳性次数、各指标有效次数及区间是全体还是条件于有阳性的抽样；条件recall区间为1也不保证新事件的recall为1。失败拟合与未定义评价是不同状态，不加伪阳性让它们消失。

报告原尺度效应和方向、CI与构造、观察数及独立单位数、缺失／权重／协变量处理。标准化效应明确分母，Cohen阈值不是实际重要性的通用标准。CI、可信区间、均值不确定性与未来单次观测区间不能互换；更复杂模型的窄区间也可能只反映漏掉的结构不确定性。

解释二次项、交互或非线性关系时，先核实际响应、编码／中心化、链接函数和观测域。二次项显著或系数为正不单独证明域内呈U形；检查完整导数、域内转折点及端点方向，必要时给条件预测和不确定性。例如 logit 下线性预测子含正的一次与二次项，而输入全为正时，其概率可以在整个观测域严格递增。打印方程与软件输出不一致时分别记录，不假设未见的编码替它们消除矛盾。

效应或检验成立需要输入和估计契约：全部数值有限、类别／配对／组对齐、有效自由度、定义中的尺度及条件。诊断未定义写原因，不强设0；保留有效估计与无法完成的推断，不静默清洗结果。

## 概率目标与选择运输

部分对象得到裁定时，先按 [data-analysis.md](data-analysis.md) 定义已裁定、全体和未裁定的概率目标。固定特征 `x`，令 `a=P(V=1|Y=1,x)`、`b=P(V=1|Y=0,x)`；当 `0<a,b<1` 且两类均有正概率时，Bayes关系给出

\[
\eta(x)=\frac{a(1-b)}{b(1-a)}
=\frac{\operatorname{odds}(p_V)}{\operatorname{odds}(p_U)},\qquad
p_U=\frac{p_V}{\eta(1-p_V)+p_V}.
\]

`a/b` 是已裁定相对全体的阳性赔率倍率，不能把它当作已裁定相对未裁定的 `eta`。跨期／跨域使用需保持标签含义和选择机制，或重新识别部署时的机制；使用拟合分数还需要它对相应已裁定目标有校准证据。未估计的 `eta` 只能给情景或相容范围，不能称置信区间或部署概率；`eta=1` 也须说明两群体条件阳性赔率相等的假设。常量正 `eta` 保持分数排序，特征相关的 `eta(x)` 可能反转排序，常量 `a/b` 本身不保护未裁定排序。用精确Bayes小例核目标和方向，再单独检查现实选择与校准条件；公式正确不能替代后两项。

## 多重比较是完整族的计算

先写 `multiplicity-family` 的科学范围、所有hypothesis ID、方向／对比、主次或探索性身份、控制目标与依赖。FWER控制至少一次错误拒绝的概率；FDR控制被拒绝项中错误比例的期望，二者不能解释成单个结论为假的概率。

`adjust_pvalues(pvalues, hypothesis_ids=..., family_id=..., method=..., alpha=...)`使用Statsmodels，支持 `holm`／`bonferroni`（FWER）和 `bh`／`by`（FDR），保留原顺序、原与校正p、依赖条件及可选调用者提供的effects。它验证数值／ID，不证明原检验p有效、族选得正确或效应算得正确。Holm／Bonferroni可在任意依赖下使用有效p；BH需要独立或相应正依赖条件，BY处理任意依赖但更保守。

只传显著p、按同一结果拆族、反复试亚组／阈值后只校正最后一组都不能恢复原确认性解释。保留全部计划结果及探索偏离；数据后形成的问题需新的确认设计或明确探索身份。无效原p不会被校正变有效。

手算四项例子：p按原顺序 `[.01,.04,.03,.20]`，Holm为 `[.04,.09,.09,.20]`，BH为 `[.04,4/75,4/75,.20]`。核原ID与结果顺序，拒绝NaN、负p、p>1、空族或重复ID。直接调用某版本Statsmodels可能不提供所有输入保护；使用已核适配契约，不能据最新版文档追认旧安装行为。

## 样本量、缺失与解释失败

规划功效由有意义最小效应、方差、独立／簇／配对、失访和检验族决定，模型／参数依据不足就给范围或仿真设计。观察效应计算的“observed power”不能解释不显著结果；已完成研究用CI、可检出效应或有定义的等效性分析说明精度。

完整案例分析与填补各需机制条件，MCAR并非所有模型下唯一允许完整案例的条件；缺失机制不清时检查合理情景及影响。模型调整变量来源与时点必须一致，选择改变群体时重写estimand。因果解释先交 [causal-analysis.md](causal-analysis.md)，高拟合或小p不能代替识别。

交付设计、全部估计／区间与族、诊断、敏感性和限定结论。计算错误修实现；设计或目标不成立回praxis-model／data-analysis；主要数学主张独立核验交praxis-verify。不是所有局部统计请求都需要完整案例、重新拟合或整稿评价。

## 第一手来源与复用范围

- [K-Dense statistical-analysis](https://github.com/K-Dense-AI/scientific-agent-skills/blob/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/statistical-analysis/SKILL.md)，固定 `a1043ef`，MIT：参考estimand、依赖单位、诊断非认证、效应／区间和检验族；不安装其Pingouin／PyMC全栈。
- Statsmodels固定 `35a8e0b`，BSD-3-Clause：[multipletests](https://github.com/statsmodels/statsmodels/blob/35a8e0b7483211f5be7e60926be082136263cac3/statsmodels/stats/multitest.py)、[聚类协方差](https://github.com/statsmodels/statsmodels/blob/35a8e0b7483211f5be7e60926be082136263cac3/statsmodels/stats/sandwich_covariance.py)、[GEE](https://github.com/statsmodels/statsmodels/blob/35a8e0b7483211f5be7e60926be082136263cac3/statsmodels/genmod/generalized_estimating_equations.py)、[MixedLM](https://github.com/statsmodels/statsmodels/blob/35a8e0b7483211f5be7e60926be082136263cac3/statsmodels/regression/mixed_linear_model.py)。API可用性与验收以实际锁定安装及适配器为准，不授予识别／抽样有效性。
