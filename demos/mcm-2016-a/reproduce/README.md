# Calculation and report build

数学复现从仓库根目录运行 `uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py`。源码只依赖锁定环境中的 NumPy 与 SciPy；没有原题专属观测数据，也不连接 AI 服务。生成目录存在时拒绝覆盖。

`reference/` 保留报告使用的实际数值、17 项检查、完整基准温度轨迹，以及分段流量优化与文献范围分析的 `extended.json`（由 `run_extended.py` 生成，约 4–5 分钟，另有 2 项检查）。复现另加一个水量对照，所以复现入口共有 18 项；两种数量分别表述。

报告用 XeLaTeX 排版（Times 系 newtxtext/newtxmath，随 TeX 发行版提供，不依赖某个系统的字体）；线图、柱状图、热图和流程图由 `scripts/texplot.py` 从归档数值直接生成 pgfplots／TikZ 源码，公式、表格和交叉引用都由 LaTeX 处理。

可选重建 PDF（只在已有计算目录中进行）：

```bash
uv run --locked python demos/mcm-2016-a/reproduce/build_report.py --run demos/mcm-2016-a/reproduce/reference
```

需要 XeLaTeX（TeX Live）或 tectonic 在 PATH 中；构建器输出到自身目录的 `paper/`（`main.tex` 与编译日志）和 `submission/`，不会覆盖上级 `deliverables/` 中的最终 PDF。重建只保证重新排版，仍须重新检查每页。

The calculation is portable Python. The report is typeset with XeLaTeX (TeX Live or tectonic): figures are generated as pgfplots/TikZ source by `scripts/texplot.py`, and the fonts come with the TeX distribution. Rebuilding is optional and does not change the archived deliverable. Render and inspect any rebuilt PDF before treating it as a final document.
