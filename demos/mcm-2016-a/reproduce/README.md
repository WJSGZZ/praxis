# Calculation and report build

数学复现从仓库根目录运行 `uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py`。源码只依赖锁定环境中的 NumPy 与 SciPy；没有原题专属观测数据，也不连接 AI 服务。生成目录存在时拒绝覆盖。

`reference/` 保留报告使用的实际数值、17 项检查、完整基准温度轨迹，以及分段流量优化与范围分析的 `extended.json`（由 `run_extended.py` 生成，约 20 分钟，另有 2 项检查）、候选验收 `mesh_check.json`（由 `run_mesh_check.py` 生成，读取 `extended.json`，保留失败候选并按三套网格独立积分与连续时间包络选择可行方案）。复现另加一个水量对照，所以复现入口共有 18 项；两种数量分别表述。`check_structure.py`重放归档恒流与六段方案，比较有限接触热容量和替代流路；`reference/structure.json`包含四结构、两方案、输入及源码哈希、能量平衡与时间步长检查。它只检查一个空间网格上的采样可行性，不重复优化，也不替代原网络三网格连续验收。基准恒流检查已加密至半秒包络，物理阈值容差为零。

报告用 Tectonic 0.17.0 与固定 v33 资源包排版（Times 系 newtxtext/newtxmath，随 TeX 发行版提供，不依赖某个系统的字体）；线图、热图和散点图由 `scripts/texplot.py` 从归档数值直接生成 pgfplots／TikZ 源码，公式、表格和交叉引用都由 LaTeX 处理。

可选重建 PDF（只在已有计算目录中进行）：

```bash
uv run --locked python demos/mcm-2016-a/reproduce/build_report.py --run demos/mcm-2016-a/reproduce/reference
```

需要 Tectonic 0.17.0 在 PATH 中；资源包 URL 和 SHA256 见 `templates/typesetting-runtime.json`，构建器核验后才编译，生成源码和 PDF 对应的 `.build.json`；构建器输出到自身目录的 `paper/`（`paper.tex` 与编译日志）和 `submission/`，不会覆盖上级 `deliverables/` 中的最终 PDF。重建只保证重新排版，仍须重新检查每页。

The calculation is portable Python. Report builds require Tectonic 0.17.0 with the resource bundle pinned in `templates/typesetting-runtime.json`; a build receipt binds the source and PDF: figures are generated as pgfplots/TikZ source by `scripts/texplot.py`, and the fonts come with the TeX distribution. Rebuilding is optional and does not change the archived deliverable. Render and inspect any rebuilt PDF before treating it as a final document.

历史 `reference/mesh_check.json` 仍绑定原验证器，精确源码保留为 `reference/mesh-validator-335052c.py`。当前 `run_mesh_check.py` 另修复了空候选恢复；本次只在短合成案例验证新分支，没有重跑原全时域三网格验收。报告重建可引用哈希匹配的历史验证器及未变的物理源码，不将旧结果认证为新版验证器运行；新验收须生成自己的新收据。

The archived mesh receipt keeps its original validator, preserved byte-for-byte as `reference/mesh-validator-335052c.py`. The current validator adds failed-candidate recovery, checked on short synthetic cases only. Report reconstruction can use the hash-matched historical source and unchanged physical code; it does not claim a new full-horizon validation.

`study_control.py --output <new.json> --seconds 180` 在归档基线之外重算有限测温与已知混合系数的条件策略；`reference/control-study.json` 保存九情景探头诊断、两候选的完整流量、优化尝试和三网格条件连续核验。拒绝覆盖输出；时间边界在计算节点检查，不是操作系统强制超时。它不重跑原基线优化，也不提供真实参数辨识、噪声传感或人工执行保证。报告构建器核对该收据的源码哈希与基线流量。

The focused control study reuses the archived baseline and records fixed-probe diagnostics plus independently replayed schedules at two known mixing coefficients. Choose a new output path. Its cooperative time checks do not provide an operating-system deadline; the study does not establish parameter identification or a deployable feedback controller.

`study_calibration.py --output <new.json> --seconds 180` 完整复现合成脉冲、有限测量相容集、约束生成和三网格独立检查，本地实跑约103秒。逐点误差与恒定偏移分别进入筛选；原方案采样失败和新候选检查都保留。输出拒绝覆盖，预算为协作式检查；超时不产生已接受记录。两实验均从均匀40°C开始，另计6L脉冲、未知填充／复位成本；同设计目标不是全模型同余量保证。报告绑定该收据、物理源、验证器及原基线。

The calibration study reconstructs a synthetic finite ambiguity set, optimizes a conditional candidate and checks every retained model on three meshes. Choose a fresh output path; cooperative budget checks do not enforce a system deadline. Calibration and control are separate trials with the same initial state. Report pulse costs and unknown reset costs separately; do not interpret finite-grid acceptance as identification, a confidence region or deployable feedback.

`check_calibration_transfer.py --output <new.json>` 不重跑优化：以同一178模型、5秒采样比较归档恒流，并在十个搜索选定模型、四种结构中重放新方案（2／1秒采样和能量检查）。`reference/calibration-transfer.json` 绑定实际源码与输入，约7秒；不将这40个组合称为完整结构范围或连续保证。

The frozen-policy transfer check keeps the ambiguity set and physical limits fixed. It adds a constant-policy comparison and sampled structural replays of the new policy, with no optimization. The ten selected models do not establish coverage of every compatible model under alternative structures.


`study_information_value.py --output <new.json> --seconds 360` 比较两种替代测量设计：30分钟零入水冷却观测与既有6L脉冲。公开入口实际运行272.40秒，保留510模型与1,530项三网格条件包络；相容集合不是概率分布，试验复位成本另计，不是先后做两次试验的联合推断。`reference/information-value.json`绑定当时实际执行的源码；后加的过期输入拒绝检查不改变旧运行身份，原执行源逐字节保留在`reference/information-study-27f9e95.py`。新运行使用当前入口并生成新收据；预算为协作式检查，不是系统硬截止。

The information-design study compares alternative passive and pulse observations under a common finite prior. Its archived run took 272.40 seconds and checked all 510 retained models on three meshes. Reset water is unknown and separate; neither sequential joint inference nor expected information value is established. The exact executed source is retained alongside the receipt; a subsequent stale-input guard is tested separately rather than presented as part of that historical run.

`check_finite_volume.py --output <new.json>` 使用独立解析答案核验空域极限：绝热三维扩散模态的单元平均解，及零扩散入口路径的串联搅拌单元响应。四套逐步加密网格的最细观测阶约1.98，最粗两网格约1.76也保留；网格16→24不是嵌套划分。实跑约0.075秒。这不检验人体占据几何、浮力、湍流或真实浴缸。文件与数值见`reference/finite-volume-verification.json`。

The discretization check uses an independent continuum diffusion mode and analytical inlet-cascade response. Successive refinement approaches second order in the empty domain; the coarser pre-asymptotic result is retained. This verifies implementation in those limits, not the bath's unresolved velocity or mixing closure.


`screen_observations.py --output <new-screen.json> --seconds 120` 在预先指定的两个合成机制中生成四个独立观测相容集合，保留旧策略的采样失败；公开入口实际7.19秒。`study_observation_control.py --input <new-screen.json> --output <new-control.json> --seconds 180` 接续该集合，实际55.31秒完成有界搜索和255项独立三网格物理包络。预算为协作式检查，控制阶段会保存到达预算时的部分运行，两入口拒绝覆盖已有输出；两份reference收据与实际源哈希相绑，`observation_values.py`在生成论文前核验覆盖、参数、来源及实际水量。弱混合脉冲的物理通过与优化器失败分开，弱被动未接受不是不可行证明。

The alternative-observation run took 7.19 seconds for screening and 55.31 seconds for bounded optimization and independent replay. Three candidates passed 255 physical model-grid envelopes; the weak-passive search failed, while the weak-pulse solver failed its additional design target despite physical acceptance. The report consumer checks source and bank bindings, unique replay coverage and delivered-water arithmetic. These cooperative budgets are not operating-system timeouts; alternative synthetic trials are neither sequential inference nor empirical calibration.

`study_structure_inference.py --output <new.json> --seconds 150` 检查试验未激发的机制与结构拟合歧义：两端点、深层流路／有限接触节点、被动／脉冲观测，共八组原结构筛选与六次既有策略重放。实际公开源约7.62秒，与先前私有候选的数值记录完全一致；没有重新优化。矩阵传播与独立RK45只比较四项轨迹摘要，采样通过不等于连续保证，更不是针对新相容集重新推断策略。`reference/structure-inference.json`绑定执行源及输入；报告消费前另检查覆盖、策略、结构、水量和物理条件。超时／异常保留部分记录并以失败退出，已有输出拒绝覆盖。
