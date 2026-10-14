# 按能力调用，沿同一主线协作

methods.md 决定任务如何推进，本文件决定当前缺口需要哪种专长。能力不是新增阶段，也不要求不同代理承担；同一助手可按需切换。请求只涉及某一能力时完成该范围，不强制启动其他部分。

| 能力 | 输入与要解决的问题 | 产出与验收 | 专业参考与入口 |
|---|---|---|---|
| 问题分析 | 原题、目标、约束；哪些解释改变答案？ | 明确任务、定义与成功条件，不遗漏原始要求 | [praxis-model](../skills/praxis-model/SKILL.md)；methods.md；定义歧义时 definition-review.md |
| 文献与来源 | 待核验的机制、参数、方法或论断 | 支持具体用途的第一手来源，记录位置、条件与许可，不把引用数量当证据 | writing.md 的来源部分；实际研究领域的原始论文与官方数据 |
| 假设与适用条件 | 原题、模型／数据及拟写结论；前提是否充分、实际使用、合理？ | 显式与隐含前提、依据、作用位置及失效影响；明确检查和未验证条件 | [praxis-assumptions](../skills/praxis-assumptions/SKILL.md)；[methods.md](methods.md#假设理由与结论范围) |
| 模型设计 | 任务定义、机制、数据能力 | 基线与必要扩展、假设和验证设计；组合关系明确 | [praxis-model](../skills/praxis-model/SKILL.md)；mathematical-reasoning.md与成熟库条件路线 |
| 数据分析 | 原始表、观测单位、实体和时间口径；数据能回答什么？ | 只读审计、覆盖与缺失、明确分母、关联基数和可回答范围 | [praxis-data-analysis](../skills/praxis-data-analysis/SKILL.md)；Pandas；`audit_data`、`audit_join` |
| 图像测量 | 原图／ROI／mask、源家族与标签、像素尺度；测量对象和处理如何定义？ | 可追溯处理、面积／边界／连通测量、阈值与尺度敏感性；对象语义与识别效果另核 | [praxis-image-analysis](../skills/praxis-image-analysis/SKILL.md)；[image-analysis.md](image-analysis.md)；SciPy；`binary_components`限定给定有界二维二值mask |
| 空间分析 | 点位／矢量／栅格、坐标与单位、定位精度、空间阈值和目标 | 可核的距离／面积／匹配、对齐与掩码、覆盖边及局部可达约束 | [praxis-spatial-analysis](../skills/praxis-spatial-analysis/SKILL.md)；SciPy、NetworkX；按需采用GeoPandas／PyProj／Rasterio |
| 统计推断 | 估计对象、采样／配对／组结构、预先选择的比较族 | 效应与区间、实际假设、聚类或多重比较、不可推断的条件 | [praxis-statistics](../skills/praxis-statistics/SKILL.md)；Statsmodels、SciPy；`adjust_pvalues`、`ols_report` |
| 文本分析 | 语料、语言、分析单位、标签或待测主张 | 可追溯特征与实例、标注定义、误差和验证边界 | [praxis-text-analysis](../skills/praxis-text-analysis/SKILL.md)；scikit-learn 的条件路线 |
| 时间序列 | 时间／实体、可用信息、预测起点与跨度、日历 | 同一评价口径下的滚动基线、误差、区间与外推条件 | [praxis-time-series](../skills/praxis-time-series/SKILL.md)；`backtest_baselines`、`arima_forecast` |
| 因果分析 | 干预、目标人群、估计对象和识别依据 | 识别论证及敏感性，或无法识别的证据与可回答的关联 | [praxis-causal-analysis](../skills/praxis-causal-analysis/SKILL.md)；实际设计优先于估计器 |
| 文献综合 | 明确问题、实际已读来源及检索范围 | 检索／筛选位置、论断—证据对应及研究差异 | [praxis-literature-review](../skills/praxis-literature-review/SKILL.md)；literature-review.md |
| 监督预测 | 目标、时点、特征、行／组及分割 | 折内预处理、Dummy基线、OOF误差与外推范围 | [praxis-machine-learning](../skills/praxis-machine-learning/SKILL.md)；`cross_validate_predictor` |
| 实验设计 | 目标、随机化单位、可采集量与资源 | 设计、区组／重复、精度或功效及停止计划 | [praxis-experimental-design](../skills/praxis-experimental-design/SKILL.md)；Statsmodels、SciPy |
| 优化与运筹 | 动作、目标、原约束与信息 | 可行方案、原单位残差、独立界／gap及风险 | [praxis-optimization](../skills/praxis-optimization/SKILL.md)；HiGHS、SciPy |
| 机制动态模型 | 状态／单位、机制、初边条件与观测 | ODE／PDE、守恒与稳态、收敛与辨识 | [praxis-dynamical-modeling](../skills/praxis-dynamical-modeling/SKILL.md)；现动态／扩散工具 |
| 不确定性传播 | 参数与结构未知、联合依赖及目标 | 条件分布／界、敏感性、精度与建议翻转 | [praxis-uncertainty-analysis](../skills/praxis-uncertainty-analysis/SKILL.md)；SALib、SciPy |
| 科研表达 | 原稿、读者、有效结果及改动范围 | 论证、段落／公式连接及事实保真 | [praxis-scientific-writing](../skills/praxis-scientific-writing/SKILL.md)；scientific-writing.md |
| 数据与计算 | 已明确模型、原始输入、参数 | 可复现处理与实际运行；变换遵守信息边界 | [praxis-compute](../skills/praxis-compute/SKILL.md)；data-computing.md；执行用 automation.md |
| 独立验证 | 原始目标、模型、有效结果及拟写结论 | 与结论强度相称的对照、界、失败或限制 | [praxis-verify](../skills/praxis-verify/SKILL.md)；methods.md 的证据与反馈；现有解析演练及专业条件参考 |
| 作品评审 | 原题／研究问题、当前完整稿与有效证据、目标与版本 | 按交付用途评价主要答案、证据、作品质量与修改优先级；竞赛和研究标准分开 | [praxis-review](../skills/praxis-review/SKILL.md)；[judging.md](../evals/judging.md) 分类导航 |
| 图表表达 | 有效结果、单位、不确定性与需要表达的判断 | 回指数据版本的图与图注，实际数组、曲线与图例对应，最终尺寸可读 | [praxis-visualization](../skills/praxis-visualization/SKILL.md)；唯一规范 visualization.md |
| 论文与报告 | 任务答案、有效证据、图表和来源 | 读者能理解的论证，数字与引用一致，符合实际规范 | [praxis-report](../skills/praxis-report/SKILL.md)；writing.md、共享模板及披露 |

## 主技能、专业模块与用途适配

主技能接续目标、预算、当前状态和依赖，选择本次主责并组织交接。专业模块以能单独完成的一类任务为边界：有明确输入、专业判断、成品和验收。一个职责可以先由共享参考支持，真实独立请求或重复失败需要专门入口时再拆成技能；不是每个流程动作或论文标题都必须新增技能。假设审查归 assumptions，整题设计中的候选前提仍由 model 负责，数值检查归 verify，组织假设章归 report；已有入口交接输入，不让用户重讲题目。

数据分析负责观测单位、数据诊断和探索，compute负责已设计计算的执行及快照；统计推断负责抽样结构与估计，verify核对结论的独立依据。时间预测与因果效应分别按未来可用信息和识别条件判断，拟合分数不能替代二者。科研绘图由 visualization负责选型、生成和实际图检查，report把已验图表放入全文并核对文字与版面。专业技能可调用现有成熟库；可选方法尚未实测时明确其状态，不把参考清单当功能认证。

图片的来源、源家族、标签和时间归data-analysis；ROI、阈值、像素几何及连通测量归image-analysis；监督训练、源家族划分和部署概率目标归machine-learning。带地理参考的栅格还由spatial-analysis核CRS、对齐和距离／面积资格，visualization只表达已有有效测量或预测。`binary_components`不生成mask、不判真实对象；数值特征矩阵CV不训练CNN。完整图像任务仍由同一主技能按这些实际依赖协调，不另建一条总流程。

| 用途 | 复用的专业能力 | 按需加载的特有规则与流程 |
|---|---|---|
| 美赛 MCM／ICM | 题意、来源、假设、建模、计算、验证、科研图表、写作和作品评审 | [场景与当届档案](context-and-team.md#规则适配)、[开放题策略](contest-playbook.md)、[竞赛交付](contest-delivery.md)、[对应竞赛评审](../evals/contest-judging.md)；精确核对赛项与届次 |
| 国赛 CUMCM、研究生赛或其他竞赛 | 按题目需要选用同一组能力，不要求固定模块组合 | 同样从场景与届次档案选规则；交付、AI说明、附件与评审分别按该赛事加载，未接入档案保留待核验，不套美赛预设 |
| 数学研究、课程或应用 | 按问题需要复用上述能力，陌生结构可交 explore | 研究使用 [research-mode.md](research-mode.md) 和 [研究评审](../evals/research-judging.md)；课程／应用按实际交付约定，不默认奖项、限时或比赛模板 |

用途适配决定规范、证据要求和交付差异，专业模块处理问题本身；组合和返回上游都由当前缺口决定。协调由 Agent 执行，现有脚本仍负责运行与证据边界；这些路由说明不是自动多代理分派器或质量认证。

## 统一交接内容

在 planning/tasks.md 对应任务 ID 中注明：此次输入／来源位置、当前模型与假设、有效运行与结果字段、单位与不确定性、允许表达的结论、尚未解决的问题、需要下游形成的交付物。复用该记录与现有文件路径，不另建含义不同的总台账。

写作与图表拿到结果时，沿记录核对版本和结论边界。缺失证据返回验证或计算；问题本身改变返回分析／建模。画图和润色不能悄悄修改结果、补造依据或把条件结论变成事实。写作也能指出论证缺口，并反馈到对应任务。整稿水平与奖项／研究价值交作品评审；局部结论核验交 verify，纯论证与语言交 scientific-writing，组稿／模板与页面交 report，标准小计算继续小任务直通。旧入口收到整稿请求时交接已有输入，不要求使用者重讲题目或管理技能名。

## 各能力如何吸收外部经验

先在能力内指出缺口，再按 methods.md 的统一引入规则判断用途、条件、输出、验收、替代关系与许可。每个领域可有多个参考，但冲突时按任务证据和适用条件选择，不规定单一“大师”永远正确。不因新增参考就添加独立阶段或安装整套环境。

进一步细化以对应能力的实际失败和可复现任务为依据；新技能存在及链接有效，不等于专长切换带来真实任务质量提升。


## 人数与能力的协调入口

先按 [context-and-team.md](context-and-team.md) 了解真实场景、人数、能力和可用时间；按任务主责与依赖分配，而非固定建模手／代码手／写作手。用户不用分别管理这些能力。已确认单人限时目标启用 [solo-delivery.md](solo-delivery.md)，由 Praxis 根据同一任务工作板选择下一项必需工作，并维护能力间交接。默认一个当前用户事项、早期基线与滚动完整稿；质量提升按完成状态与剩余预算安排。能力细分不能增加用户的协调成本。
