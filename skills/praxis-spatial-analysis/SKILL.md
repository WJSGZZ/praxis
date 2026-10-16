---
name: praxis-spatial-analysis
description: 审查空间数据的坐标／高程基准、距离面积、空间连接、栅格对齐以及覆盖和可达约束。用于“点位怎么匹配、距离单位对吗、哪个地点覆盖需求、地图数据怎么叠加”。Spatial data analysis, CRS-aware measurement, spatial joins, raster alignment, coverage and accessibility. 单纯地图美化交praxis-visualization；优化方案交praxis-optimization，水动力／CFD须另核机制。
license: MIT
---

# Praxis · 空间分析

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [spatial-analysis.md](../../references/spatial-analysis.md) 核水平／垂直 CRS、轴序、单位、历元、日期、几何、ID与精度；本地共原点直角坐标可明确声明，`set_crs` 与变换分开。
- 距离／面积选合适投影或测地线，平面运算保留实际单位，坐标数组明确轴序。
- 声明 within／covers 边界与连接基数，查并列最近、一对多、未匹配和重复；修复几何前后核拓扑、类型与面积。
- 栅格核变换、注册、范围、分辨率、掩码与 nodata；分类／连续重采样按测量语义，并复核单位和总量。
- 直线距离、网络可达、容量覆盖分别求证；保留候选与空间边／成本，交已有优化器；依部署时空尺度划分相关样本。
- 独立小例核变换、距离、阈值和掩码；平面图 equal aspect，真实单位和色标；SciPy／NetworkX 优先，可选 GIS 库核实际版本与环境。

## 交接

推断交 [statistics](../praxis-statistics/SKILL.md)，干预交 [causal-analysis](../praxis-causal-analysis/SKILL.md)，定义交 [model](../praxis-model/SKILL.md)，覆盖交 [optimization](../praxis-optimization/SKILL.md)，机制交 [dynamical-modeling](../praxis-dynamical-modeling/SKILL.md)，独立证据交 [verify](../praxis-verify/SKILL.md)，地图交 [visualization](../praxis-visualization/SKILL.md)。
