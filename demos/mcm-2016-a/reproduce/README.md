# Calculation and report build

数学复现从仓库根目录运行 `uv run --locked python demos/mcm-2016-a/reproduce/run_demo.py`。源码只依赖锁定环境中的 NumPy 与 SciPy；没有原题专属观测数据，也不连接 AI 服务。生成目录存在时拒绝覆盖。

`reference/` 保留报告使用的实际数值、17 项检查和完整基准温度轨迹。复现另加一个水量对照，所以复现入口共有 18 项；两种数量分别表述。

报告采用 ReportLab 排版，Matplotlib MathText/STIX 将公式转为矢量轮廓；这是明确的工具选择，不宣称导出 PDF 来自完整 LaTeX 引擎。Times New Roman 正文/粗体嵌入，构建器另按需注册斜体，正文、表格、参考文献和页眉均为 12pt；公式基准为 14pt，包含常规较小上下标和分式。图表实际缩放后的基础标签约为 12pt。官方要求是至少 12pt 的可读字体，不指定这套字体。

可选重建 PDF（只在已有计算目录中进行）：

```bash
uv run --locked --with reportlab==4.4.9 python demos/mcm-2016-a/reproduce/build_report.py --run demos/mcm-2016-a/reproduce/reference
```

此命令使用独立工具依赖，不更改项目锁文件。构建器默认读取 macOS 已有的 Times New Roman TTF 文件，没有随项目分发字体。其他平台需提供获准使用的对应字体并调整 `fontdir`；数学复现不受影响。构建器输出到自身目录的 `submission/` 和 `figures/`，不会覆盖上级 `deliverables/` 中的最终 PDF。重建只保证重新排版，仍须重新检查每页。

The calculation is portable Python. PDF regeneration has separate ReportLab and licensed-font requirements, currently documented for the macOS rendering environment. It is optional and does not change the archived deliverable. Render and inspect any rebuilt PDF before treating it as a final document.
