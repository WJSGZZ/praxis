# 独立输运对照 / A different transport closure

同一份总热容量、热损、供水条件和原控制指令，改用一维轴向对流—扩散方程及守恒通量边界，检验三维热网络的主要解释。它是约化结构对照，不是实测数据，也不声称比原模型更真实。

## 得到了什么

- 原恒流与六段方案共 36 次原样重放：两种损失分布、三种有效扩散率、三套网格。弱混合下平均温度仍合格，远端却过冷；中、强混合下两原方案均通过采样检查。
- 分开的有限延迟恒流搜索：中等混合的入选方案从零分钟补水，强混合从第十分钟开始；均匀／局部人体热损对应 22.7110／22.6844 L 和 18.8674／18.8560 L。弱混合两组未找到接受候选，不能据此证明无解。
- 原三维基线的出口相对平均温度的额外焓流为 −31.5108 kJ，匹配恒流的轴向模型为 −26.2751 kJ。两者都是冷出口，不能从这些轨迹声称热水短路造成额外耗水。均匀损失模型可由温度梯度的最大值原理解释这一符号；局部人体损失不在该证明范围内。

## 证据与边界

`design.json` 固定输入与搜索；`results.json` 保留 36 重放、六组搜索、四个接受候选和失败；`checks.json` 包含 24 项独立核验。解析无流冷却、连续稳态及瞬态特解检验离散；另组直接通量 RK45 检查守恒与四候选、两失败轨迹。最细网格所测瞬态误差不超过 0.002614°C，独立积分差不超过 3.30×10⁻⁷°C。收敛与采样检查不等于连续 PDE 可行性认证或全局最优。

一维模型匹配总量，但均匀横截面热容量不保留三维人体置换，且不解析竖向分层、浮力或真实速度场。扩散率仍是情景参数。COMSOL 官方文档只用于核对入流通量边界；没有运行 COMSOL。`manifest.json` 绑定归档字节，报告消费者还核对原基线身份；哈希验证不代替数学核验。

## Reproduce without overwriting the archive

From the repository root, copy only the five source/input files to a **new** working directory. The producer and checker refuse existing result files:

```bash
mkdir -p .local/bath-transport
cp demos/mcm-2016-a/reproduce/reference/transport/{model.py,run.py,check.py,design.json,design.md} .local/bath-transport/
uv run --locked python .local/bath-transport/run.py
uv run --locked python .local/bath-transport/check.py
```

The frozen producer took 0.2893 s and the separate checker 11.4999 s, excluding imports and startup; these are recorded runs, not speed guarantees. Full baseline optimization is not rerun. Original and matched overflow diagnostics are separate reanalyses of explicitly identified trajectories.

The substantive finding is a distinction between distribution and replenishment efficiency: a cool outlet retains heat while remote water can still violate comfort. Timing dependence survives this alternative closure; exact water prescriptions remain model-dependent. The search is finite and mesh-based, with sampled extrema. Neither this study nor successful numerical checks establish empirical performance or an award.
