---
name: praxis-statistics
description: 设计并完成与实际抽样和目标效应匹配的统计分析：独立、配对、重复或聚类样本，估计与区间、效应量、多重比较、缺失和诊断解释。用于“比较组间差异、怎么检验、这个CI怎么算、样本有依赖、多重比较、估计效应”。Statistical design, estimands, hypothesis tests, effect sizes, confidence intervals, paired or clustered observations and multiple testing. 因果识别交 praxis-causal-analysis；完整作品评价与独立数学认证另有入口。
license: MIT
---

# Praxis · 统计设计与推断

专业深度归 [statistical-analysis.md](../../references/statistical-analysis.md)。推进、假设和证据层次共用 [methods.md](../../references/methods.md)，运行按 [automation.md](../../references/automation.md)。单独统计请求直接进入本入口，不要求先走完整建模流程。

## 调用契约

输入：问题与目标效应、变量／单位、样本选择和独立单位、配对／簇／时序结构、缺失规则、已规定或探索性的比较、已有结果和拟写主张。产出：匹配设计的估计／检验与理由、实际效应和区间、完整比较族、诊断及敏感性、允许的统计解释。设计信息缺失时先给能确认的描述和条件分析，不默认逐行独立。

## 专业判断与执行

- 先确定 estimand（要估计的群体、比较、效应与尺度）、抽样／分配单位、分析单位和可用信息；区分独立均值比较、已对齐的配对差、重复／聚类、时序相关与非连续结果。数据契约缺口交 [praxis-data-analysis](../praxis-data-analysis/SKILL.md)。
- 检验由问题和设计选择，诊断用来质疑模型和设计相称的敏感性。不得按 Shapiro／Levene 的是否显著切换检验；不拒绝不是证实前提。独立均值比较可预定 Welch；配对检查差值，回归检查残差；秩检验通常不是中位数检验。
- 使用已有 `hypothesis_test`、`ols_report` 或相称SciPy／Statsmodels接口，先核条件和输入有限性。`sample_design.status='not_checked'`保留真实设计未核状态，不能因flags为空改成已成立。`ols_report`的cluster模式须显式groups；其他依赖可评估GEE／MixedLM或按独立单位重采样，时序相关需相应误差模型。HC3不处理簇依赖；可选API不自动成为已执行工具。
- 同时给原尺度效应、方向、CI及其构造、纳入样本／独立单位数和缺失处理。CI、预测区间、可信区间、SD／SE和情景范围分别定义；大样本显著不等于重要，不显著不证明无效。
- 多次比较先声明 `multiplicity-family` 和全部 hypothesis ID，用 `adjust_pvalues` 按控制目标与依赖选Holm／Bonferroni或BH／BY，保留原始与校正p、ID和调用者提供的效应。工具不认证原检验和族定义；不能先删不显著项再校正或按结果改族。

## 交付、验证与回退

保留分析设计、实际版本／输入、全部计划比较、探索偏离、效应／CI／p 值和诊断结论。用精确小例、解析答案、独立公式或合适模拟核主要计算及错误输入；软件成功或一个诊断数不认证抽样、独立性或因果性。未运行、未支持的模型与未确认前提明列。

干预问题先交 [praxis-causal-analysis](../praxis-causal-analysis/SKILL.md) 判断识别，再估计；结构／定义有误回 [praxis-model](../praxis-model/SKILL.md)，假设专审交 [praxis-assumptions](../praxis-assumptions/SKILL.md)。可复现批次交 [praxis-compute](../praxis-compute/SKILL.md)，已有数值主张的独立核验交 [praxis-verify](../praxis-verify/SKILL.md)，解释与表格交 [praxis-report](../praxis-report/SKILL.md)。
