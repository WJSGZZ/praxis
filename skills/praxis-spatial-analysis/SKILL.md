---
name: praxis-spatial-analysis
description: 审查空间数据的坐标／高程基准、距离面积、空间连接、栅格对齐以及覆盖和可达约束。用于“点位怎么匹配、距离单位对吗、哪个地点覆盖需求、地图数据怎么叠加”。Spatial data analysis, CRS-aware measurement, spatial joins, raster alignment, coverage and accessibility. 单纯地图美化交praxis-visualization；优化方案交praxis-optimization，水动力／CFD须另核机制。
license: MIT
---

# Praxis · 空间分析

为需要空间关系、距离面积、空间连接、栅格叠置、覆盖或可达约束的任务提供专业判断；仅作地图展示时不触发本技能。专业参考见 [spatial-analysis.md](../../references/spatial-analysis.md)。

## 输入与交付

输入：获准使用的空间表／矢量／栅格、问题和目标量、数据来源及日期、CRS与单位（未知则明确未知）、测量／定位精度、稳定ID来源、栅格分辨率与nodata定义，以及决策中的阈值或成本含义。
交付：数据与基准审计、选定的距离／面积或谓词定义、匹配和覆盖结果及基数、未匹配／边界／掩码影响、约束可行性、独立小例核验、来源追溯和未知项；按任务规模裁剪，不给每个小任务套完整GIS流程。

## 专业判断

- 先核水平和垂直CRS、轴序、单位、基准／坐标历元（适用时）、来源日期、几何有效性、ID唯一性及精度。已知单位和共用原点／轴的本地直角坐标不要求EPSG；仅所需框架、单位或基准未知时限制相关结论，不按数值范围猜；`set_crs`只赋标签，`to_crs`才变换坐标。
- GeoPandas／Shapely几何运算是平面计算。经纬度的度不能当公里；Web Mercator不作通用测量基准。选择适合区域与量的投影，或在地表距离需要时用PyProj／GeographicLib测地线方法；坐标数组明确轴序（如 `always_xy=True`）。
- 明确 `within`／`covers` 等边界纳入规则。空间连接前声明预期基数，事后检查一对多／并列最近、未匹配和重复ID；几何修复前后比较类型、拓扑和面积变化，不把修复成功等同分析有效。
- 栅格须核CRS、仿射变换、范围、像元注册、形状、分辨率、nodata／有效掩码；同shape不代表对齐。分类数据用最近邻或有明确语义的众数／类别聚合；连续数据按测量过程选重采样，并复核单位、范围与总量变化。
- 地理直线最近不等于道路、河道或通行网络可达。候选地点保留完整列表、筛选约束及数据来源；容量总和足够不代表局部需求可分配。把空间生成的边／成本交现有LP/MILP或网络工具求解，不另建优化器。
- 空间邻近、聚集或分块结构意味着样本可能相关；不得默认普通随机切分满足独立同分布。按目标部署空间或时间尺度构造评估切分，交统计／预测技能解释推断范围。
- 独立核对最终坐标变换、距离／面积、边界阈值和掩码的小例。米制平面图保持equal aspect；地理图使用与表达目标相称的投影，标真实单位、有效掩码和有意义的色标；图面不认证选址或工程安全。

## 工具与交接

默认复用已有SciPy（KDTree用于明确单位的投影／本地直角坐标点查询）和NetworkX网络能力。GeoPandas、PyProj、Rasterio是按需选用的可选GIS依赖；确需执行时再核版本并固定项目环境，不假称已安装或已验证。
空间推断交 [statistics](../praxis-statistics/SKILL.md)，干预识别交 [causal-analysis](../praxis-causal-analysis/SKILL.md)；目标和前提交 [model](../praxis-model/SKILL.md)，覆盖分配交 [optimization](../praxis-optimization/SKILL.md)，机制交 [dynamical-modeling](../praxis-dynamical-modeling/SKILL.md)，独立证据交 [verify](../praxis-verify/SKILL.md)，地图成品交 [visualization](../praxis-visualization/SKILL.md)。本技能不认证水动力、CFD、现场工程或因果结论。

具体API语义及外部研究固定版本见参考末尾来源清单；使用时按实际环境版本复核。
