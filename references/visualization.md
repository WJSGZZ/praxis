# 图表表达能力

当用户需要图表或交付中的图形时使用；先从任务判断读者需要看趋势、比较、分布、关系还是不确定性，再选形式。画图使用实际有效结果，不为视觉完整编造数据。以下原则归纳自公开的图表规范（文末来源），再按本项目的论文场景改写。

## 先判断是否需要图

画图前先明确正文中的读者问题、有效证据以及希望读者看清的关系，再比较“不画、用表、用另一种图”。一句话已能准确表达的孤立结果可以不画；重点是精确查值时优先用表；趋势、分布、空间差异、方案权衡或不确定性才通常需要图。正文已说明的结论不因配图而自动多一份证据。

| 读者要判断什么 | 优先考虑 | 需要避免 |
|---|---|---|
| 随时间／连续参数的变化、收益与代价的权衡 | 折线、阶梯线、前沿曲线 | 用无序柱状图隐藏连续关系；将离散情景连成可插值规律 |
| 少量方案的水平或变化幅度 | 点图、条形图、配对图 | 只凭漂亮选择饼图或复杂堆叠；没有必要的零点截断 |
| 离散、尾部与误差／不确定性 | 分布图、误差条、区间带 | 只给均值；把情景极差称为置信区间 |
| 空间位置、局部热点或结构关系 | 地图、热图、带尺度的几何／网络图 | 用总量曲线替代局部差异；无依据的平滑与插值 |
| 多变量机制或算法步骤 | 必要的机制／流程图 | 仅把目录或段落再画一遍，没有帮助理解依赖与机制 |

这些是判断起点，不是固定图型清单。多面板和图表并用只有在承担不同阅读任务时才保留；同一数据重复展示须说明新增的信息。每篇论文的选图与例外理由在下节计划表集中维护，不要求正文增加制作日志。理由不足的图删除、合并或换形式；数量不足先检查是否漏掉主要阅读任务，不能为凑数重复作图。最终同时审查论证价值、数据忠实度与实际尺寸可读性。

## 图表计划

每篇论文附图表计划表，沿用现有账本：图／表｜回答哪个读者问题｜数据来源｜放在哪节｜相对文字／表格的增益。竞赛论文默认在前两页放一张同时说明问题、方法和核心答案的总览图，可与模型结构图合并；受当届摘要／目录格式、页限或阅读增益等限制而不适用时，在计划表写明理由。缺省只作计划复查告警，不设硬门，也不以强塞图片改变赛事规定的页面内容。每项对应题问与论断，来源绑定实际输入或有效结果。比较图默认标出共同基线、变化因素及关键差值或边界；需要解释机制时关联相应中间量，不用另一个装饰图代替依据。图数、图密度与篇幅的样本差别只描述展示量，不能认证结果完成、图像质量或奖档。出图后核单位、版本、区间含义与实际支持的论断，计划与成品逐项对照；多面板合为一个编号图时注明各面板职责。

2026-10-16 的结构量样本包含18篇可抽取英文文本的 O 奖论文：图数最少5、中位13，四分位区间按 inclusive 线性分位数计算为11.25到16，原样排序为 `5, 6, 9, 11, 11, 12, 12, 13, 13, 13, 13, 14, 16, 16, 17, 17, 18, 20`。

样本局限：从60篇候选经材料守卫放行21篇，再排除3篇图像PDF，仅剩18篇；年份为2018、2021、2022，ICM偏多，MCM A/B/C只有4篇。图数以可抽取的最大 Figure 编号（不超过60）近似，部分“数学家版”可能经过编辑；结构统计未核读内容或图的论证价值。这不是获奖因果、通用最低图数或评分线。

- 默认安排一张模型结构图，说明输入、主要变量、机制与输出的依赖；动笔前先画草稿，以图中依赖顺序组织全文提纲，正文沿这一顺序展开，成稿前再按实际内容精修并核对图文对应。每个主要比较默认检查图、表或文字哪种能使读者直接判断，选择省图时在计划表说明理由。
- 涉及区域、县、网格等空间单元时默认包含地图，标明边界／坐标来源、单位、图例、缺失单元及真实位置或示意身份。空间问题通常不能只用总量曲线回答。
- 少于8张图是本轮采纳的**实验参数**，仅触发计划复查。少于8张、缺模型结构图、涉及空间单元却缺地图时，计划表分别写明为什么文字或表格更好；无空间单元时写“不适用”及理由。短解析题可合理省图，不能用重复图、无效示意图或编造地图满足数量。
- 不设固定图型清单。选型按读者问题决定，数量与例外先作告警；有无图不能代替题意覆盖与科学核验。

## 地图与网络图的最小入口

地图和网络图可用 Matplotlib 直接绘制，不新增 shapefile 或 geopandas 依赖。先核 GeoJSON 的坐标基准和区域标识与数值表一一对应；真实几何与抽象网络示意分别标记。网络图保留实际边、方向和权重，节点位置若仅用于排版须明确说明。

下面读取 RFC 7946 经纬度 GeoJSON 的 Polygon／MultiPolygon，以区域值填色；内环按相反方向保留孔洞，缺值和其他几何明确拒绝。示例适合小区域展示，纵横比例按中央纬度近似调整，不用于测量距离或面积；跨经线、极区或大区域须先选择合适投影。数值应取同一有效结果，颜色与数值使用同一个 `Normalize`。

```python
import json, math
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

with open("regions.geojson", encoding="utf-8") as stream:
    features = json.load(stream)["features"]
with open("region-values.json", encoding="utf-8") as stream:
    values = json.load(stream)  # {"region-id": finite numeric value}
data = [float(values[str(f["id"])]) for f in features]
if not data or not all(math.isfinite(v) for v in data):
    raise ValueError("Every mapped region needs a finite value")
norm, cmap = Normalize(min(data), max(data)), plt.get_cmap("viridis")
fig, ax = plt.subplots(figsize=(7, 5), layout="constrained")
for feature, value in zip(features, data):
    geometry = feature["geometry"]
    if geometry["type"] not in ("Polygon", "MultiPolygon"):
        raise ValueError("Only polygon regions are supported")
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    for polygon in polygons:
        paths = []
        for index, ring in enumerate(polygon):
            ring = [tuple(point[:2]) for point in ring]
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError("Polygon rings must be closed")
            area2 = sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(ring, ring[1:]))
            if (area2 > 0) != (index == 0):
                ring.reverse()  # Outer counterclockwise, holes clockwise.
            paths.append(Path(ring, [Path.MOVETO] + [Path.LINETO]*(len(ring)-2) + [Path.CLOSEPOLY]))
        ax.add_patch(PathPatch(Path.make_compound_path(*paths), facecolor=cmap(norm(value)),
                               edgecolor="white", linewidth=.5))
ax.autoscale_view()
latitude = sum(ax.get_ylim()) / 2
ax.set_aspect(1 / math.cos(math.radians(latitude)))
ax.set(xlabel="Longitude (degrees)", ylabel="Latitude (degrees)")
fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, label="Value (state unit)")
fig.savefig("region-map.pdf")
```

## 一张图一个结论

- 每张图只回答一个问题；图题简洁命名具体对象、比较或有证据支持的发现，说明按 writing.md 分工放置；不强迫每张图用结论句，也不使用无法定位内容的泛泛主题。一张图只有一个标题，论文里放在图下的图注中，不再在图内重复。
- 图注与表题的内容分工、长度复查和多行说明的排版原则统一见 [writing.md](writing.md) 的图表段，不另维护一套规则。表题放在表上方，图题放在图下方；必要的读法、数据版本、样本与区间含义不能丢。
- 坐标轴写量与单位（有量纲变量必须有单位，无量纲量写清定义或比例口径），类别变量不必加单位；不重复写明显的信息。

## 颜色只承载信息

- 先问“这个颜色在编码什么”。能用一种颜色表达的图用一种颜色；不为好看使用多种颜色，更不随手选一种鲜艳的颜色。一个变量对应一种颜色，在全文所有图里保持一致：本项目论文里蓝色表示关注的量，朱红表示对比或需要提醒的量（最冷的单元、失败的情形、搜索得到的恒定方案），灰色表示背景、界限和理论上界。
- 强调用“暗淡的基线加鲜明的重点色”；基线色不能抢眼。
- 分类用 Okabe–Ito 这类色盲友好的区分色，各色视觉权重相当，顺序不暗示等级；连续量用感知均匀的顺序色图（如 viridis），只有围绕有意义的中心（零点、基准）才用发散色图，不用彩虹色图。
- 颜色之外再加冗余编码（线型、标记），让黑白打印和色觉障碍读者也能读；图例顺序要与图中视觉顺序一致。

## 图例、网格与版面

- 能直接标注就不用图例：在曲线端点或旁边写文字，颜色与曲线一致、字色略深；确需图例，放在绘图区外（图上方或右侧），绝不遮挡数据，也不要放在“看起来空”的角落而不核对。
- 减少非数据墨水：去掉图外框和多余的边框，用开放的坐标轴；网格线只保留浅灰色的主网格，方向与比较方向一致（柱状图横条用竖线）。
- 柱状图从零开始，长标签用横条；按数值或有意义的顺序排列；用颜色区分类别时在图注里写明含义；数值直接标在条端。
- 多面板图：轴范围与刻度一致，绘图区对齐（长短不同的轴标签不能把绘图区挤歪，需要时固定绘图区宽度）；面板用 (a)(b) 小字标注；共享一个图例；面板按有意义的顺序排列。
- 刻度标签不得互相重叠；刻度数量适中；截断轴或对数轴必须标明并说明必要性。

## 不确定性与统计含义

误差条说明是标准差、标准误、置信区间、可信区间还是情景范围；若库自动计算区间，核对其统计含义与采样假设，不把默认值包装成实验证据。分布、比例与跨组比较需注明分母和样本量。

## 数学与数据核验

- 图的输入绑定有效运行、生成脚本、变量、单位和参数；默认保留完整绘图点，不做静默步长抽稀；点数超过明确上限则返回错误，确需聚合／降采样时先选方法、验证峰值／边界／关键事件未被误表并记录用途。从实际数组生成，不靠手工描点或图像生成模型合成科研结果。抽查端点、极值、阈值交点及正文引用值与原始数值一致；异常值、缺失、失败求解不可为了曲线完整静默删去。
- 对照实际绘图对象检查“数据系列—颜色／线型—图例文字”的对应，不能只核对生成源里写过这些名字。无图例的基线、置信带边界和参考线不得占后续命名系列的图例槽；`texplot.Axis` 只把显式 `label` 的系列加入图例，直接标注不需要空图例项。PGFplots 会延后按已记住的曲线配图例；手写代码应对不入图例的 `addplot` 使用 `forget plot`。Matplotlib 也应检查实际 handles 与 labels，而非依赖位置拼接。导出清单及标签哈希只证明记录存在，最终图仍需查看。
- 连线、平滑、插值、拟合各有数学含义：离散决策用点／阶梯表达，连续量的插值须有依据；观测、拟合和外推分清。不得把插值网格当成新增观测，把平滑隐藏的波动当作收敛。涉及数值场、窄峰或边界时，按结论风险检查采样／网格是否足够；只在相关时做收敛检查，不强迫每张图跑一次重计算。
- 坐标变换、截断、归一化、密度估计和分母写明；对数轴处理非正值不得私自加常数。几何图保持实际纵横尺度或注明示意；二维比较不因装饰改成透视3D。可比较面板采用共同轴／色标范围，确需不同范围时明确标注。
- 统计图标明独立样本数、重复／重采样单位、区间定义及计算条件；不把标准差、置信区间、情景范围或数值误差互换。概率密度／频数、均值／中位数等按实际估计量标注；不因图形更平滑就提高结论强度。
- 科研绘图优先采用成熟数值库和科学绘图库，版本随锁定环境保存；小样本用解析关系、独立汇总或已知边界核对。探索画图与最终绘图可用不同工具，但必须共用同一有效数据及定义。

## 工具与检查

- 论文常规曲线、表意图优先用 pgfplots／TikZ 由数据直接绘制（`scripts/texplot.py` 提供线图、置信带、阶梯线、散点、柱状图（含负值的龙卷风图）、热图与流程图；新增 `Axis.errorbar(..., interval="95% confidence interval")`、`grouped_bar_chart`、`Axis.histogram`、`Axis.boxplot`、`shared_legend_panels`、`diverging_heatmap`。误差条输入绝对上下界并必填区间含义，含义随系列名显示在图例；直方图用显式边界、末端闭区间，越界样本拒绝；箱线图用线性分位数和1.5 IQR范围内的观测须线，插值一侧无观测时止于四分位数，保留离群点；共享图例拒绝同标签不同样式；发散色图围绕明确中心对称，拒绝静默截断色值。图中的标签自动转义 `%`、`_`、`&`、`#`，已写 LaTeX 或数学的标签原样保留），图中字体与正文一致；Matplotlib 适用于探索、统计图和复杂数值场；最终输出可用 PDF／SVG 或 pgf 后端，合理保留高密度场的栅格层与矢量文字／坐标，不强行把所有场图重画成 TikZ。线条、文字和几何图优先矢量，必须位图时按最终尺寸验证分辨率与清晰度。保存生成脚本、数据与版本。
- 先从当前作品的共享样式确认正文、数学、图内标签与数据的字体职责，再配置最终绘图；换环境须接续这份配置，不能退回绘图库默认。同一职责的字体全文一致，目标格式明确允许的分工可以不同；不能把某篇论文的具体字体或字号推广为所有科研图规范。导入独立 PDF 图后检查整稿及图文件的实际字体名称与嵌入状态，正文 TeX 的字体包不足以证明图内一致。MCM v3/v4/v5生成器显式传入 `font_profile="mcm-v3"`（Axis、条形图、热图及流程图共用），将普通轴标题、刻度、图例和标注设为normal；旧profile默认输出保留。最终字号还取决于整稿嵌入比例：用含全部标签的图形bbox控制宽度，在最终PDF按文字角色测量，不只检查独立图的源字号。使用 `uv run --locked python -m scripts.check_pdf 论文.pdf --require-embedded-fonts`；若当前作品明确排除某一默认字体，按 [automation.md](automation.md) 加 `--forbidden-font '实际名称或通配模式'` 并保留退出状态与检查结果。字体转曲或栅格化会超出文本字体检查的范围，必须在最终尺寸下目视复核；不能用转曲规避风格检查。
- 版心边界是硬约束：图、表、代码框的外沿（含坐标轴标签、直接标注、图例）不得超出正文区，整体相对版心居中。pgfplots 的 `width` 默认只量绘图框，轴标签在框外，所以用 `scale only axis` 并把绘图框设为版心宽度的 0.6–0.85 倍；表格列宽要扣除列间距（`@{}` 加 `\tabcolsep`），带框代码用 `xleftmargin/xrightmargin` 留出边框。交付前渲染每页，量每页墨迹的左右空白，两侧相差明显即回头修，TeX 日志里的 Overfull 也要清零；`uv run --locked python -m scripts.check_pdf 论文.pdf --margins` 会渲染并列出左右空白不一致或贴近页边的页面（带行号的代码页、悬挂缩进的参考文献页本来就不对称，会一并列出，由人判断）。
- 实际尺寸下逐张检查：普通文字符合本稿角色字号（MCM v3至少12pt），数学脚标按数学角色保留，图例不遮数据，刻度不互相覆盖，绘图区居中对齐，转灰度仍可读；再看缩略效果。生成源、完整绘图数组、字体配置与最终图同步保留，修图前后核对点数、坐标变换、色标范围及关键值；纯排版修订复用有效数据，不重算无关模型。发现异常返回相应数据／模型任务，不能只调整坐标掩盖。
- 实际期刊或比赛格式优先于任何统一绘图样式；图与图注交给写作时附上数据版本和能支持的结论。

## 来源

- Claus O. Wilke，*Fundamentals of Data Visualization*（clauswilke.com/dataviz，开放获取）：颜色用途、冗余编码、数据与背景的平衡、多面板图、标题与图注。
- Rougier, Droettboom, Bourne，“Ten Simple Rules for Better Figures”，PLOS Computational Biology，2014（开放获取）。
- Wong，“Color blindness”，Nature Methods 8:441，2011；Okabe 与 Ito 的色盲友好调色板。
- Matplotlib 色图指南（matplotlib.org/stable/users/explain/colors/colormaps.html）。

核验的第一手技术资料（2026-10-09）：[PGFplots 误差条](https://tikz.dev/pgfplots/reference-errorbars)、[坐标范围](https://tikz.dev/pgfplots/reference-specifyrange)、[Matplotlib 色图指南](https://matplotlib.org/stable/users/explain/colors/colormaps.html)、[Nature 制图规范](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/)、[Nature 作者格式指南](https://www.nature.com/nature/for-authors/formatting-guide)。采用其数据表达、可编辑矢量、误差定义与可读性原则；期刊指定字体／版面尺寸不是比赛强制规定，也不冒称“顶尖质量已认证”。
