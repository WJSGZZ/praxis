# 美赛 Demo：一缸水，怎样保持温暖又少补水？

**2016 MCM A《A Hot Bath》：从平均水温走到空间差异、策略比较，再到能不能照着做。**

[English](README.en.md) · [完整英文论文](deliverables/7391856.pdf) · [复现源码](reproduce/) · [返回 Praxis](../../README.md) · [案例总览](../README.md)

[![美赛案例：空间水温与三种补水量证据](assets/overview-zh.png)](deliverables/7391856.pdf)

## 这道题问什么

一个人躺在盛满热水的浴缸里，水会逐渐变凉。怎样补热水，才能让水温尽量保持在初始温度附近、同时用水最少？题目还要求考虑浴缸的形状和大小、人体的大小与动作，以及泡泡浴层的影响，并写一份给使用者看的说明。

难点在于题目没有给任何温度数据：热损失系数、人体吸热和水的混合程度都要从标准关联式和已发表的实验里找依据；而且“水温”不能只看平均值，远离水龙头的水可能更冷。

## 先看结果

| 同一 30 分钟情景 | 补水量 | 能支持什么结论 |
|---|---:|---|
| 三维热网络，最佳恒定流量 | **24.14 L** | 已接受候选中用水最少的恒定流量；不声称任意控制的全局最优 |
| 三维热网络，留余量的六段方案 | **21.48 L** | 增加 0.1°C 设计余量；三套网格独立积分与连续时间包络通过，比恒定流量少约 11% |
| 理想充分混合模型 | **16.01 L** | 在该理想模型中证明“先等再维持”最优 |
| 能量守恒给出的下界 | **15.41 L** | 给定温度与热损假设下，任意可行策略的条件下界 |

水量 164.25 L，初始 40°C，温度限制 39–41°C，允许最大空间温差 1.5°C（上限与温差施加在入口射流区之外，射流区半径取 0.15 m；下限对所有单元成立）。表面散热由自然对流、辐射与蒸发的教材关联式推出（敞开水面约 35.4 W/(m² K)，按人体遮挡取 25）；人体换热以[浸浴实验](https://doi.org/10.1113/EP092761)的核心温升为量级依据；混合系数没有依据，只作情景。没有实测浴缸实验，数值用于展示方法，不是使用或安全标准。

**所需水量强烈依赖损失系数，能否找到被接受的方案主要取决于混合强度。** 在情景范围内取 64 个 Sobol 点，41 个点有可接受的恒定流量，所需水量 12–31 L（5%–95% 分位，中位数 22 L）；其余点没有找到可接受候选，主要是弱混合所致。

## 怎样解的

1. **先把问题说清。** 把“保持温暖”和“均匀”写成全单元下限与射流区外的上限、温差约束，用水最少为目标，不给不同单位的量硬加权重。
2. **可证明的简单模型。** 整缸水充分混合时，证明“先等水温降到下限，再补水维持”最优，并由能量守恒给出任意策略的下界。
3. **三维热网络。** 有限体积网络显式处理表面和壁面散热、人体置换与换热、内部混合、入流与溢流；下限覆盖所有单元，上限与温差排除入口射流区。用矩阵指数推进时间，用多起点序列二次规划优化分段流量。
4. **范围与情景。** 系数在教材关联式给出的情景范围内做 Sobol 分析；换几何、人体、运动、泡泡层、舒适区间，看策略是否变化。
5. **能不能照着做。** 检查最省水的方案对水龙头偏差有多敏感，再定价格：留多少余量、多花多少水。

## 证据与验证

- **平均值不足以决定策略。** 理想模型中可以先等水变凉；空间模型的已接受恒定流量候选则从一开始补水。留余量的六段方案进一步节水约 11%，但只对当前情景成立。
- **更少的水不一定是更好的答案。** 19.35 L 的十二段候选在最细网格上温差达到 1.531°C，超过 1.5°C，已被拒绝。选用 21.48 L 的六段方案：前三套网格的最大温差分别约为 1.400、1.395、1.416°C，独立连续时间检查也通过。
- **证明与候选分开。** 理想模型有最优性证明；空间结果是经过检查的候选，不是全局最优。恒定流量比能量下界多 8.7 L，带余量方案多 6.1 L。
- **每个推荐都检查自己的证据。** 17 项基准检查核对独立 RHS、能量、解析极限、几何与情景；分段方案另外在每次流量切换处重启独立 RK45，并按每段导数界检查采样点之间的温度，不能借基准检查代替。
- **数值余量不等于使用可靠性。** 留 0.1°C 余量比无余量六段候选多用约 10% 的水（19.50 → 21.48 L）；在每段独立的正态乘法误差试验中（均值 1、标准差 0.1，负乘子截为 0，并非 ±10% 的有界误差），200 次试验中约 74% 不越界。这不足以支持通用手动操作建议，实际使用还需要标定和温度反馈。
- **搜索失败保留其范围。** 弱混合、高损失、宽浅缸等情景没有被搜索接受的恒定流量，有限搜索不能推出所有恒定流量均不可行。恒流细网格用水 24.12 L（差 0.11%）是诊断，不是收敛阶或真实物理精度认证。

- **结构对照补的是模型边界。** 原有恒流和六段方案在有限接触热容量、深层流路及组合情景中均通过采样检查；没有重优化，也没有据此声称实际浴缸已标定。恒流另以半秒回放通过零阈值放宽的连续包络。

- **混合条件会改变候选时序。** 在已知混合系数与准确供水条件下，两份六段候选分别用 27.00 L 和 20.30 L，三网格条件连续核验通过；它们不是跨情景全局最优比较。固定两探头在九个情景中漏掉两个采样违例，说明有限测温不能直接替整缸水背书。完整流量、失败尝试与检查收据见 `reference/control-study.json`。

**从测量歧义走到策略。** 合成双探头脉冲观测在 2,835 个参数组合中留下 178 个相容模型；原六段方案有四个模型采样越界。新开环候选指令用水 **23.48 L**，三个指定网格的 534 项条件数值包络全部通过。代价是比名义方案多约 9.33% 的指令用水，并另需 **6 L** 标定脉冲及未计的复位成本；有限相容集不是实测置信区间或现实可靠性保证。完整条件与流量见 `reference/calibration-study.json`。

**测量也有用水成本。** 同样的有限先验、探头和误差条件下，30 分钟被动冷却观测留下 510 个模型；相应候选补水 **24.39 L**，1,530 项三网格条件包络全部通过。脉冲候选少补约 0.91 L，却先用 6 L 做试验。若两种试验复位成本相同，且浴缸、人体、探头和供水条件保持不变，累计到第 7 次使用才由脉冲候选更省水。这是两组名义合成观测与候选的成本比较；被动观测不等于没有测量，也不等于准备成本为零。

**数值方法另有解析答案对照。** 空域三维扩散在四套逐步加密的网格上接近二阶（最细观测阶 1.98），无扩散入口链与独立串联搅拌单元解析解一致。这检验离散实现，未验证真实流场、湍流或浴缸实验。

**拟合正确，不代表机制正确。** 无入水时，供水倍率和入口流路从方程中消失；再密的被动测温也识别不了它们。用深层流路或有限接触热容量生成八组观测，原结构仍能在规定误差内拟合。六次既有端点策略在这些替代机制下通过采样检查，说明“结构没有唯一识别”和“策略在所测变化下仍可用”可以同时成立。这是固定策略诊断，没有针对新观测重新求解，也不是新相容集上的全覆盖保证。

**让测量、结构和成本真正连起来。** 同一组名义读数下，三种结构保留被动／脉冲 1465／467 个相容组合。旧方案在基础网格通过，却有两个细网格最高温越界；局部减流修补也没有统一设计余量。新比较对两组候选都要求最低温 39.13°C、入口区外最高温 40.9°C、温差 1.4°C，全部 **5,796 项模型—网格条件包络**通过，54 个极端对象另由独立积分与能量核验。候选指令水量为 **26.09／23.63 L**；一次 6 L 试验可复用、稳定正供水倍率和总复位费用相同时，脉冲从第 **3** 次使用更省。三次和前面的七次对应不同结构范围与候选，不能混用。这是有限模型上的公平余量比较，尚未证明全局最优或现实节水效果。

**让观测直接调整下一分钟的供水。** 从同一 1,465 模型集合和 26.09 L 备份出发，恒定探头偏差与零噪声／单个有界随机序列分别得到 23.59／23.16 L 的完整服务；最后保留 114／1 个模型。六条实际反馈轨迹另有 18 次独立三网格采样重放。两种第十分钟条件漂移在一分钟后清空相容集，停止沿用旧证书；11 分钟部分服务不算节水成功，故障识别也不等于安全恢复。前述第三次成本交叉只比较两条固定候选，反馈与脉冲的重复使用交叉尚未测定。

## 翻两页报告

<table>
<tr>
<td width="50%"><a href="deliverables/7391856.pdf"><img src="assets/report-summary.png" alt="英文 Summary Sheet：方法、结果与验证" width="100%"></a></td>
<td width="50%"><a href="deliverables/7391856.pdf"><img src="assets/report-proof.png" alt="理想完混模型的最优策略证明" width="100%"></a></td>
</tr>
<tr>
<td><strong>Summary Sheet：问题、方法、结果</strong><br>一页写清决策、数值与证据等级。</td>
<td><strong>论证：为什么先等待再补水</strong><br>完混模型的四步最优性证明。</td>
</tr>
</table>

**观测结果会改变行动。** 两种另外设定的合成参数情景让被动／主动试验分别保留 60／14 和 70／11 个模型。较强混合下，两个条件候选需要 16.51／15.37 L 控制水量，等复位成本的交叉改为第六次使用。较弱混合下，被动搜索未找到可接受方案；脉冲候选 35.05 L 通过物理包络，但优化器没有成功、额外设计余量没有满足。共 255 项新增三网格检查通过；搜索失败不证明无解，物理检查通过也不等于求得最优。这些是分开的观测情景，不是事先已知的试验收益。

**[阅读完整 26 页英文论文 →](deliverables/7391856.pdf)** 使用固定的 Tectonic 0.17.0 与 v33 资源包排版：Times 系字体与公式，图由 pgfplots 与 TikZ 从归档数值直接绘制，图表自动编号与交叉引用；25 页解答含一页给使用者的非技术说明，后接 1 页 AI 使用披露。按 2027 年美赛提交规范编排：正文 12 磅，匿名页眉与页码，Summary 单页。

**从两个点，走向有边界的适用范围。** [连续参数补充验证](reproduce/reference/continuous-transfer.md)保留原供水指令，在四个静态参数同时变化的窄邻域内，推导一阶变分与完整余项界；两条流路、三套网格均满足物理温度约束，102 次独立角点及中心重放用于核对实现。更严的统一设计余量并未全部满足，也未认证每种参数下的反馈分支。完整论文 §11.3 已纳入必要条件与精确余项证明，详细推导和失败记录留在补充页；论文奖项由完整稿另行审读。

**换机制，也检查解释。** [轴向输运对照](reproduce/reference/transport/README.md)匹配原热容量、损失和供水条件，原样重放 36 个对象；另做六组有限延迟恒流搜索和 24 项解析／独立通量核验。平均水温仍可能隐藏远端过冷，中等／强混合入选方案分别从零／十分钟补水。原三维和匹配轴向恒流的出口额外焓流为 −31.51／−26.28 kJ：冷出口与远端过冷可以同时出现。论文 §11.4 将这一诊断、条件梯度论证与数值边界连起来，没有把约化对照当成真实流场验证。

## 作品评议

目标是 **Outstanding Winner（O）**。作者外 AI 重新通读原题和当前 26 页全稿，查看全部页概览与五幅实际图，给出 **强 Finalist（F）中心、F—O 相邻参考范围**；尚不认定达到 O，评议非盲、未校准。依据包括完整题意覆盖、完混最优证明、守恒空间模型、结构歧义与试验成本，以及观测到行动的连接。本轮独立轴向输运对照进一步支持远端冷却和混合条件下的时序差异，并纠正了热水短路归因：采用轨迹的出口比平均水温低，不能据其额外耗水断言短路损失。

§12 已把证据收敛为三项决策：只有零入水加上完整备份尾段仍对每个相容模型合格时才等待；有合格候选才减少补水；相容集为空或备份失去支持时重评。摘要和一页指南同步更新，未新增模拟或改变数值结果。新一轮完整稿评议仍以强 F 为中心，但判断更接近 F／O 交界。当前最有价值的差距是证书失效后尚无合格的续行方案；应固定失配范围，验证保守续行或结束规则。拒绝证书复用不等于安全恢复。§11.3 的邻域只覆盖固定动作和静态参数；固定候选的回本次数仍不移用于反馈。

[版本与检查范围](verification.json)绑定当前 PDF；这不是实际评奖结果或获奖概率。

## 自己跑一次

在 Praxis 仓库根目录运行：

```bash
uv sync --locked
uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py        # 基准、18 个情景、细网格与 18 项复现检查，约一分钟
uv run --locked python demos/mcm-2016-a/reproduce/run_extended.py    # 分段优化、范围分析、执行容差，约 20 分钟
uv run --locked python demos/mcm-2016-a/reproduce/run_mesh_check.py   # 候选筛选、三网格独立连续时间检查
uv run --locked python demos/mcm-2016-a/reproduce/check_structure.py --output demos/mcm-2016-a/reproduce/reproduced/structure.json  # 原方案的结构对照，不重优化
uv run --locked python demos/mcm-2016-a/reproduce/study_control.py --output demos/mcm-2016-a/reproduce/reproduced/control-study.json --seconds 180
uv run --locked python demos/mcm-2016-a/reproduce/study_calibration.py --output demos/mcm-2016-a/reproduce/reproduced/calibration-study.json --seconds 180
uv run --locked python demos/mcm-2016-a/reproduce/study_information_value.py --output demos/mcm-2016-a/reproduce/reproduced/information-value.json --seconds 360
uv run --locked python demos/mcm-2016-a/reproduce/check_finite_volume.py --output demos/mcm-2016-a/reproduce/reproduced/finite-volume-verification.json
uv run --locked python demos/mcm-2016-a/reproduce/screen_observations.py --output demos/mcm-2016-a/reproduce/reproduced/observation-screening.json --seconds 120
uv run --locked python demos/mcm-2016-a/reproduce/study_observation_control.py --input demos/mcm-2016-a/reproduce/reproduced/observation-screening.json --output demos/mcm-2016-a/reproduce/reproduced/observation-control.json --seconds 180
uv run --locked python demos/mcm-2016-a/reproduce/study_structure_inference.py --output demos/mcm-2016-a/reproduce/reproduced/structure-inference.json --seconds 150
uv run --locked python demos/mcm-2016-a/reproduce/study_structure_decision.py --output demos/mcm-2016-a/reproduce/reproduced/structure-decision.json --seconds 180
uv run --locked python demos/mcm-2016-a/reproduce/study_common_reserve.py --mode audit --output demos/mcm-2016-a/reproduce/reproduced/common-reserve-audit.json
uv run --locked python demos/mcm-2016-a/reproduce/study_common_reserve.py --mode replay-extrema --seconds 180 --output demos/mcm-2016-a/reproduce/reproduced/common-reserve-extrema.json
uv run --locked python demos/mcm-2016-a/reproduce/study_feedback.py --mode audit --output demos/mcm-2016-a/reproduce/reproduced/feedback-audit.json
uv run --locked python demos/mcm-2016-a/reproduce/study_feedback.py --mode replay --seconds 30 --output demos/mcm-2016-a/reproduce/reproduced/feedback-replay.json
```

基准入口拒绝覆盖既有 `reproduce/reproduced/`；扩展与验收脚本在该目录写各自的结果，不改归档证据或最终 PDF。复现入口的 18 项检查不能回写成论文里的 17 项。重新排版 PDF 需要 Tectonic 0.17.0，使用固定资源包，见[构建说明](reproduce/README.md)；数学复现不依赖排版工具，也不连接 AI 服务。

## 策略在哪些变化下还能用？

六个预先确定的合成条件没有参加控制器的设计或筛选，控制规则保持不变。两种采样点之间的参数情景完成了 30 分钟服务；改变接触蓄热、等体积盆形、供水温度或表面散热，则使观测相容集清空。停止前的温度仍通过检查，拒绝的是继续使用旧模型证书，不能把部分用水少解释成节水成果。

| 条件 | 完整服务 | 实际用水／停止时间 |
|---|---|---|
| 参数点间情景 · 表层路径 | 是 | 22.88 L |
| 参数点间情景 · 深层路径 | 是 | 23.08 L |
| 接触蓄热改变 | 否 | 第 28 分钟拒绝复用 |
| 等体积盆形改变 | 否 | 第 5 分钟拒绝复用 |
| 进水降至 49°C | 否 | 第 11 分钟拒绝复用 |
| 表面散热超出先验 | 否 | 第 9 分钟拒绝复用 |

两条完整轨迹另在三种网格上通过独立 RHS／能量与条件数值包络检查；四条部分轨迹只核查已执行时段。共 10 个检查对象，不是现实成功率或连续参数邻域保证。[冻结输入、源码与结果](reproduce/reference/feedback-transfer.json)；详细范围见[复现说明](reproduce/README.md#off-bank-transfer-boundaries)。

## 文件地图

```text
deliverables/7391856.pdf      # 唯一提交文件（英文，26 页）
reproduce/                    # 复现入口、归档数值、论文构建器
assets/                       # 首页与案例页图片
sources.json                  # 来源记录
verification.json             # 验收记录
AI-use.md                     # AI 使用记录
```

提交目录仅含一份英文 PDF，符合美赛的单文件形态；`7391856` 是案例占位编号，没有借用真实队伍身份。

## 来源、边界与许可

- 使用 [COMAP 官方原题](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2016/problems/2016_MCM_Problem_A.pdf)；原终稿封存后，对照阅读了同题 O 奖论文 44845、54164 的全文，并检查整篇版面概览及选定图表及官方评语，随后开展条件控制研究；没有复制其数据或图形。这是对照学习后的开发案例，不能作为未见题测试。实际阅读范围见来源记录。
- 不是标准答案或获奖成果；原题只给链接，不重新分发。历史题按 2026-10-07 核查的[当前提交规范](https://www.contest.comap.org/undergraduate/contests/mcm/instructions.php)编排；AI 参与范围真实披露，未声称有完整聊天导出或独立人工审核。[来源记录](sources.json) · [验收记录](verification.json) · [AI 记录](AI-use.md)
- 模型、代码、论文和原创图形按仓库 MIT 许可；外部资料各保留自身权利。本案例检验的是给定条件下的热网络与交付流程，不是实测准确性认证。

如果这个案例对你有帮助，欢迎 **Star Praxis**，也欢迎带着具体问题和复现结果提交 Issue。

同一178模型和5秒采样下，恒流／原六段／相容集六段分别通过130／174／178例；表8直接比较指令与实际水量。新方案另在十个选定模型的四种结构中通过40个采样检查；这不扩大原三网格连续保证。
