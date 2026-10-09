# Calculation and report build

数学复现从仓库根目录运行 `uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py`。源码只依赖锁定环境中的 NumPy 与 SciPy；没有原题专属观测数据，也不连接 AI 服务。生成目录存在时拒绝覆盖。

`reference/` 保留报告使用的实际数值、17 项检查、完整基准温度轨迹，以及分段流量优化与范围分析的 `extended.json`（由 `run_extended.py` 生成，约 20 分钟，另有 2 项检查）、候选验收 `mesh_check.json`（由 `run_mesh_check.py` 生成，读取 `extended.json`，保留失败候选并按三套网格独立积分与连续时间包络选择可行方案）。复现另加一个水量对照，所以复现入口共有 18 项；两种数量分别表述。`check_structure.py`重放归档恒流与六段方案，比较有限接触热容量和替代流路；`reference/structure.json`包含四结构、两方案、输入及源码哈希、能量平衡与时间步长检查。它只检查一个空间网格上的采样可行性，不重复优化，也不替代原网络三网格连续验收。基准恒流检查已加密至半秒包络，物理阈值容差为零。

报告用 Tectonic 0.17.0 与固定 v33 资源包排版（Times 系 newtxtext/newtxmath，随 TeX 发行版提供，不依赖某个系统的字体）；线图、柱状图、热图和流程图由 `scripts/texplot.py` 从归档数值直接生成 pgfplots／TikZ 源码，公式、表格和交叉引用都由 LaTeX 处理。

可选重建 PDF（只在已有计算目录中进行）：

```bash
uv run --locked python demos/mcm-2016-a/reproduce/build_report.py --run demos/mcm-2016-a/reproduce/reference
```

需要 Tectonic 0.17.0 在 PATH 中；资源包 URL 和 SHA256 见 `templates/typesetting-runtime.json`，构建器核验后才编译，生成源码和 PDF 对应的 `.build.json`；构建器输出到自身目录的 `paper/`（`main.tex` 与编译日志）和 `submission/`，不会覆盖上级 `deliverables/` 中的最终 PDF。重建只保证重新排版，仍须重新检查每页。

The calculation is portable Python. Report builds require Tectonic 0.17.0 with the resource bundle pinned in `templates/typesetting-runtime.json`; a build receipt binds the source and PDF: figures are generated as pgfplots/TikZ source by `scripts/texplot.py`, and the fonts come with the TeX distribution. Rebuilding is optional and does not change the archived deliverable. Render and inspect any rebuilt PDF before treating it as a final document.

历史 `reference/mesh_check.json` 仍绑定原验证器，精确源码保留为 `reference/mesh-validator-335052c.py`。当前 `run_mesh_check.py` 另修复了空候选恢复；本次只在短合成案例验证新分支，没有重跑原全时域三网格验收。报告重建可引用哈希匹配的历史验证器及未变的物理源码，不将旧结果认证为新版验证器运行；新验收须生成自己的新收据。

The archived mesh receipt keeps its original validator, preserved byte-for-byte as `reference/mesh-validator-335052c.py`. The current validator adds failed-candidate recovery, checked on short synthetic cases only. Report reconstruction can use the hash-matched historical source and unchanged physical code; it does not claim a new full-horizon validation.

`study_control.py --output <new.json> --seconds 180` 在归档基线之外重算有限测温与已知混合系数的条件策略；`reference/control-study.json` 保存九情景探头诊断、两候选的完整流量、优化尝试和三网格条件连续核验。拒绝覆盖输出；时间边界在计算节点检查，不是操作系统强制超时。它不重跑原基线优化，也不提供真实参数辨识、噪声传感或人工执行保证。报告构建器核对该收据的源码哈希与基线流量。

The focused control study reuses the archived baseline and records fixed-probe diagnostics plus independently replayed schedules at two known mixing coefficients. Choose a new output path. Its cooperative time checks do not provide an operating-system deadline; the study does not establish parameter identification or a deployable feedback controller.
