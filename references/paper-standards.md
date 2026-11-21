# 科研图表与论文规范：按论文类型检索

画图、制表、写图注或评审版式前先用本页。科研规范有两层：一层是各类论文都认的共通核心（数据忠实、误差有定义、矢量与嵌入字体、按成品尺寸设计、色盲与灰度可读）；另一层随论文类型变化，比如 Nature 图内 5–7 pt 无衬线体、分图标小写 **a**，Science 分图标大写 **A**，IEEE 表号用罗马数字，美赛和国赛对图表样式根本没有官方规定。把一种刊物的做法当成普遍规范，和不看规范一样会出错。

本页的规则表是唯一来源；`scripts/paper_standards.py` 解析这些表供检索和校验，不另存副本。选图与数据核验见 [visualization.md](visualization.md)，图题与正文分工见 [writing.md](writing.md)。

## 怎么用

1. **先定论文类型**：目标期刊、赛事届次或学位授予单位。有终端时运行

   ```bash
   uv run --locked python -m scripts.paper_standards --venue "SIAM Journal on Applied Mathematics" [--topic 配色]
   ```

   输出共通核心、该类型的规则和“尚无已证实规则的主题”。名称识别只是提示：例如 *Science China* 系列不是 *Science*，*Scientific Reports* 不归 Nature 主刊，识别不出时只用核心，再去读该刊须知。无终端时直接读下面对应小节。
2. **优先级**：当届或目标刊现行作者须知 > 本页“已证实” > “已推导” > Praxis 项目默认 > 通用建议。“待确认”“未查到”的主题必须回到原页面核对，或在交付中写明未核。
3. **证据状态**：已证实＝查阅日读到官方原文；已推导＝由本项目代码或计算得到（来源列写文件）；往届参考＝从往届获奖论文观察到的做法，写明年份、题号和读取位置，只说明评委接受过什么，不是规则；待确认＝来源存在但非现行版本、非官方地址或只能从模板推断；未查到＝找过但没读到（来源列写找过的地址）；项目默认＝ Praxis 的选择，不是外部规定。规范会改版，查阅日期超过一年或换届时重新核。
4. **评审口径**：只有目标类型的“已证实”规则能作为“不合规范”的依据；项目默认与共通核心用于判断可读性和专业程度，不说成违规。

## 共通核心

下列做法在本次核对的多家来源中一致出现，是所有类型的底线；具体数值仍以各类型规则为准。

| ID | 类型 | 主题 | 规范 | 适用条件 | 状态 | 来源 | 查阅 |
|---|---|---|---|---|---|---|---|
| `core-final-size` | core | 尺寸 | 按刊出时的栏宽设计图，再在该尺寸下检查字号与线宽；不要先画大图再任意缩放 | 所有论文 | 已证实 | https://www.elsevier.com/authors/policies-and-guidelines/artwork-and-media-instructions/artwork-sizing ；https://www.nature.com/nature/for-authors/final-submission | 2026-11-20 |
| `core-vector` | core | 格式 | 数据图与示意图交矢量文件并嵌入字体（不用 Type 3，不把文字转轮廓或栅格化）；只有照片、密集场图等用位图 | 所有论文 | 已证实 | https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ ；https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/file-formatting/ | 2026-11-20 |
| `core-error` | core | 误差 | 误差线、区间带和统计量写明是 SD、SE、CI 还是情景范围，并给样本量 n | 含统计或不确定性的图表 | 已证实 | https://www.nature.com/nature/for-authors/formatting-guide ；https://www.nature.com/documents/nr-reporting-summary-flat.pdf | 2026-11-20 |
| `core-colorblind` | core | 可及性 | 分类色用色盲友好色板（如 Okabe–Ito），避免只靠红绿区分；颜色之外加线型、标记或直接标注 | 所有彩色图 | 已证实 | https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ ；https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/ | 2026-11-20 |
| `core-colormap` | core | 配色 | 连续量用感知均匀的顺序色图（如 viridis），只有围绕有意义的中心才用发散色图，不用彩虹色图 | 热图、场图 | 已证实 | https://matplotlib.org/stable/users/explain/colors/colormaps.html | 2026-10-09 |
| `core-units` | core | 单位 | 轴标签写量和 SI 单位，单位放括号内（如 Time (s)），数字与单位间留空格 | 所有含量纲的图表 | 已证实 | https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ ；https://res.cloudinary.com/apsphysics/image/upload/v1715884920/aps-journals-style-guide_tnoyln.pdf | 2026-11-20 |
| `core-caption-order` | core | 图注 | 本次核对的来源凡写明位置者都是图题在图下、表题在表上；图表按正文首次引用顺序编号且都被正文引用 | 未另行规定的论文 | 已证实 | https://files.taylorandfrancis.com/asa-style-guide.pdf ；https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-formats-checklist ；https://grd.bit.edu.cn/docs/2026-04/8baf5a45d0424c68addba9c036d202c5.pdf | 2026-11-20 |
| `core-gray` | core | 可及性 | Praxis 论文色 main #0072B2、accent #D55E00、muted #7A7F85 的相对亮度为 0.15、0.22、0.21，转灰度几乎无差别；可能黑白印刷或要求灰度可读时必须靠线型、标记或直接标注区分 | 用 texplot／praxis.mplstyle 的图 | 已推导 | `tests/test_paper_standards.py` 中的亮度计算 | 2026-11-20 |
| `core-palette` | core | 配色 | 论文图用 Okabe–Ito 科研配色：蓝 main 为关注量，朱红 accent 为对比或警示，灰 muted 为背景与界限；品牌色只用于宣传图 | Praxis 论文图 | 项目默认 | [texplot.py](../scripts/texplot.py)、[praxis.mplstyle](../templates/praxis.mplstyle) | 2026-11-20 |

## 各类型差异一览

同一项在不同类型里的要求（数值见下文对应规则，“—”表示本次未查到明文）：

| 项目 | 数学（SIAM） | 应用（Elsevier／IEEE／APS） | 综合（Nature／Science） | 统计（JASA／AOS／JRSSB） | 美赛 MCM/ICM | 国赛 CUMCM | 中文期刊／学位论文 |
|---|---|---|---|---|---|---|---|
| 图内字号 | ≥7 pt（2013 手册，待确认） | Elsevier 7 pt；IEEE 9–10 pt；APS 字高 ≥2 mm | Nature 5–7 pt；Science 6–9 pt | JASA ≥8 pt | 正文 ≥12 pt，图未单独规定 | 不限 | 期刊例 6 pt；学校各定 |
| 图内字体 | — | Arial/Helvetica 或 Times | 无衬线（Arial/Helvetica） | — | 未规定（项目默认 Times） | 不限 | 期刊例 Times New Roman |
| 分图标签 | — | IEEE、APS 用 (a)(b) | Nature 8 pt 粗体 a；Science 10 pt 粗体 A | JRSSB 左上 A、B | 未规定 | 未规定 | 学校各定 |
| 表号与表线 | 表题在上，三条横线（待确认） | IEEE、APS 罗马数字 TABLE I | Nature 一行粗体表题 | JASA、JRSSB 表体内不用横竖线 | 未规定；COMAP 建议文章要求表头可读 | 未规定 | 学校例：三线表 |
| 位图分辨率 | — | Elsevier 300/500/1000 dpi；IEEE 300/600 | 300 dpi 起（Nature 页另写 450） | JASA 300；JRSSB 350/600/1200 | 未规定；PDF ≤25 MB | 未规定；≤20 MB | — |
| 复现要求 | 编辑政策要求能重得表中或图中数值 | — | Nature 统计清单 | JASA、AOS、JRSSB 要求代码与数据 | AI 报告附完整对话 | 附录放完整可运行程序 | — |

Praxis 模板的 12 pt Times 只符合美赛的正文下限，投 Nature、Science 时要改成 5–9 pt 无衬线；投 IEEE 时改成 9–10 pt。下文“现有工具与规范的冲突”给出改法。

## 数学期刊：SIAM（SIAP、SINUM、SISC 等）

SIAM 最终版式由编辑按 siamart 排版，作者主要负责编号、图题和图中文字可读。现行作者须知与 2019 版排版手册在本次查阅时被人机验证挡住，下面的样式数值取自 2013 版手册，只能作“待确认”：投稿前读 SIAM 作者页和 siamart 文档。内容层面的要求（研究贡献、可重得数值）见 [siam-research.md](siam-research.md)。

| ID | 类型 | 主题 | 规范 | 适用条件 | 状态 | 来源 | 查阅 |
|---|---|---|---|---|---|---|---|
| `siam-reproduce` | siam | 复现 | 记录代码、输入、求解与后处理，使读者能重得论文指明的表项或图中数值 | SINUM（SISC 要求重放关键结果的入口与容差） | 已证实 | https://epubs.siam.org/journal/sinum/editorial-policy | 2026-11-08 |
| `siam-caption` | siam | 图注 | 图题以 “Fig. 2.1.” 起头、以句点结尾，一律放在图下方；正文引用写全称 “Figure 3.2”“Table 2” | SIAM 期刊 | 待确认 | https://wwwarchive.z13.web.core.windows.net/journals/pdf/stylemanual.pdf （SIAM Style Manual 2013，旧站归档；现行 2019 版 https://epubs.siam.org/pb-assets/files/SIAM_STYLE_GUIDE_2019-1635349464.pdf 未取得） | 2026-11-20 |
| `siam-numbering` | siam | 编号 | 图可全文连续编号或按节编号；按节编号的图必须排在本节内，否则改全文连续 | SIAM 期刊 | 待确认 | https://wwwarchive.z13.web.core.windows.net/journals/pdf/stylemanual.pdf （SIAM Style Manual 2013，旧站归档；现行 2019 版 https://epubs.siam.org/pb-assets/files/SIAM_STYLE_GUIDE_2019-1635349464.pdf 未取得） | 2026-11-20 |
| `siam-table` | siam | 表格 | 表号居中在表上，表题在其下；表题后、列标题下、表末各一条横线，竖线和额外横线只在必要时用 | SIAM 期刊 | 待确认 | https://wwwarchive.z13.web.core.windows.net/journals/pdf/stylemanual.pdf （SIAM Style Manual 2013，旧站归档；现行 2019 版 https://epubs.siam.org/pb-assets/files/SIAM_STYLE_GUIDE_2019-1635349464.pdf 未取得） | 2026-11-20 |
| `siam-font` | siam | 字体 | 图内文字不小于 7 pt，过细的线加粗；同类图做成一样大，最宽 31 pica | SIAM 期刊 | 待确认 | https://wwwarchive.z13.web.core.windows.net/journals/pdf/stylemanual.pdf （SIAM Style Manual 2013，旧站归档；现行 2019 版 https://epubs.siam.org/pb-assets/files/SIAM_STYLE_GUIDE_2019-1635349464.pdf 未取得） | 2026-11-20 |
| `siam-color` | siam | 配色 | 现行彩色政策（灰度可分、少用黄色、配线型标记）只见于搜索摘要，原文未读到 | SIAM 期刊 | 未查到 | https://epubs.siam.org/journal-authors | 2026-11-20 |
| `siam-house` | siam | 字体 | 英文研究稿用 amsart 与 Latin Modern，图题小号置于图下、表题置于表上；投 SIAM 时换用 siamart 并让图内字体跟随正文 | Praxis 研究模板 | 项目默认 | [research-style.tex](../templates/research-style.tex) | 2026-11-20 |

## 统计期刊：JASA、Annals of Statistics、JRSS B

统计期刊比其他类型更看重表格的数字精度和可复现：JASA 和 JRSS B 要求表体内不画横竖线、数字对齐并适当舍入，三家都要求代码与数据。本次核对的页面都没有关于标准误、置信区间或显著性星号写法的明文规定，这些按共通核心 `core-error` 处理并在表注中说明。

| ID | 类型 | 主题 | 规范 | 适用条件 | 状态 | 来源 | 查阅 |
|---|---|---|---|---|---|---|---|
| `statistics-jasa-caption` | statistics | 图注 | 图题置于每张图下方，图表按引用顺序用阿拉伯数字连续编号，每张表都在正文引用并有简短描述性标题 | JASA 等 ASA 期刊 | 已证实 | https://files.taylorandfrancis.com/asa-style-guide.pdf | 2026-11-20 |
| `statistics-jasa-table` | statistics | 表格 | 表体内不用横线和竖线；小数点对齐，括号内数值单独对齐；数字大幅舍入，两位以上有效数字很少需要 | JASA 等 ASA 期刊 | 已证实 | https://files.taylorandfrancis.com/asa-style-guide.pdf | 2026-11-20 |
| `statistics-jasa-figure` | statistics | 字体 | 缩到刊出尺寸后文字与符号不小于 8 pt；位图 300 dpi；轴标签大小写混排 | JASA 等 ASA 期刊 | 已证实 | https://files.taylorandfrancis.com/asa-style-guide.pdf | 2026-11-20 |
| `statistics-jasa-repro` | statistics | 复现 | 修改稿须交代码、数据、工作流程与 ACC 表，代码能复现关键结果（含图表），数据用非专有格式并附数据字典 | JASA 两个栏目的受邀修改稿 | 已证实 | https://jasa-acs.github.io/repro-guide/pages/author-guidelines | 2026-11-20 |
| `statistics-aos-template` | statistics | 版面 | 必须用 AOS 的 LaTeX 模板且不改版式，正文一般不超过 25 页；补充文件（含数据与代码）随文在 Euclid 发布 | Annals of Statistics | 已证实 | https://imstat.org/journals-and-publications/annals-of-statistics/annals-of-statistics-manuscript-preparation/ | 2026-11-20 |
| `statistics-aos-caption` | statistics | 图注 | 官方样例中表题在表格之前、图题在图之后，表格画横线 | Annals of Statistics | 待确认 | https://github.com/vtex-soft/texsupport.ims-aos （只能从模板推断） | 2026-11-20 |
| `statistics-jrssb-format` | statistics | 分辨率 | 图优先矢量（eps、ai、pdf）；照片至少 350 dpi，线条图 600 dpi，精细线条 1200 dpi；不收 doc 与 jpg | JRSS B | 已证实 | https://academic.oup.com/jrsssb/pages/general-instructions | 2026-11-20 |
| `statistics-jrssb-color` | statistics | 配色 | 每张印刷彩图收费 £50；印刷版交灰度、网络版交彩图可免费 | JRSS B | 已证实 | https://academic.oup.com/jrsssb/pages/general-instructions | 2026-11-20 |
| `statistics-jrssb-caption` | statistics | 图注 | 图题表题简短自明并写明单位，写在稿件里不放进图片；多面板左上角标 A、B、C；每图另附以 “Alt text:” 开头的替代文字 | JRSS B | 已证实 | https://academic.oup.com/jrsssb/pages/general-instructions | 2026-11-20 |
| `statistics-jrssb-table` | statistics | 表格 | 表体内不用竖线与横线，数字右对齐或按小数点对齐并适当舍入，表用可编辑格式放在正文末 | JRSS B | 已证实 | https://academic.oup.com/jrsssb/pages/general-instructions | 2026-11-20 |
| `statistics-jrssb-repro` | statistics | 复现 | 复现全部实证结果的代码投稿时提供给审稿人，录用前公开并带 DOI，另设数据可得性声明 | JRSS B | 已证实 | https://academic.oup.com/jrsssb/pages/general-instructions | 2026-11-20 |
| `statistics-uncertainty` | statistics | 误差 | 标准误、置信区间与显著性星号的写法 | JASA、AOS、JRSS B | 未查到 | https://academic.oup.com/jrsssb/pages/general-instructions ；https://files.taylorandfrancis.com/asa-style-guide.pdf | 2026-11-20 |

## 物理、工程与应用期刊：Elsevier、IEEE、APS

三家都要求按成品尺寸设计、字体嵌入、灰度可读，但宽度、字号下限、编号写法各不相同。按目标期刊所属出版社取对应行；Elsevier 各刊的 Guide for Authors 可能另有要求，投稿前读该刊页面。

| ID | 类型 | 主题 | 规范 | 适用条件 | 状态 | 来源 | 查阅 |
|---|---|---|---|---|---|---|---|
| `elsevier-font-size` | elsevier | 字体 | 成品尺寸下正文字 7 pt，上下标不小于 6 pt；带网点或阴影的图约 10 pt | Elsevier 期刊插图 | 已证实 | https://www.elsevier.com/authors/policies-and-guidelines/artwork-and-media-instructions/artwork-sizing | 2026-11-20 |
| `elsevier-width` | elsevier | 尺寸 | 最小 30 mm，单栏 90 mm，1.5 栏 140 mm，双栏 190 mm | Elsevier 期刊插图 | 已证实 | https://www.elsevier.com/authors/policies-and-guidelines/artwork-and-media-instructions/artwork-sizing | 2026-11-20 |
| `elsevier-dpi` | elsevier | 分辨率 | 位图：照片 300 dpi，图文混合 500 dpi，线条图 1000 dpi（很细的线 1200 dpi）；矢量图不受此限 | 交位图时 | 已证实 | https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-types | 2026-11-20 |
| `elsevier-line` | elsevier | 格式 | 线宽 0.10–1.5 pt，推荐 0.25 pt，主要曲线约 1 pt；低于 0.1 pt 不保证印出 | Elsevier 期刊插图 | 已证实 | https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-faq | 2026-11-20 |
| `elsevier-format` | elsevier | 格式 | 用 EPS、PDF、TIFF 或 JPEG，嵌入字体；图内字体用 Arial/Helvetica、Times、Courier、Symbol | Elsevier 期刊插图 | 已证实 | https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-overview | 2026-11-20 |
| `elsevier-color` | elsevier | 配色 | 交 RGB；在线彩色免费、印刷彩色多需付费；黑白印刷的图避开转灰后相近的颜色，改用图案或虚线，每图颜色不超过 3–4 种 | 可能黑白印刷的图 | 已证实 | https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-faq | 2026-11-20 |
| `elsevier-caption` | elsevier | 图注 | 图注不画进图内，单独提交或列在稿末；图按正文出现顺序编号且都被正文引用；图内字号不要相差太大 | Elsevier 期刊插图 | 已证实 | https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-formats-checklist | 2026-11-20 |
| `elsevier-table` | elsevier | 表格 | 表格编号、竖线和 SI 单位条款在各刊 Guide for Authors 中，本次未取得 | Elsevier 具体期刊 | 未查到 | https://www.sciencedirect.com/ （各刊 Guide for Authors 页对自动抓取返回 403） | 2026-11-20 |
| `ieee-dpi` | ieee | 分辨率 | 彩色与灰度位图高于 300 dpi，黑白线条图高于 600 dpi；推荐 PS、EPS、PDF 矢量 | IEEE 期刊 | 已证实 | https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/ | 2026-11-20 |
| `ieee-width` | ieee | 尺寸 | 单栏 3.5 in（88.9 mm），双栏 7.16 in（182 mm），不小于一栏；最大 7.16 × 8.8 in | IEEE 期刊 | 已证实 | https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/ | 2026-11-20 |
| `ieee-font` | ieee | 字体 | 推荐 Helvetica、Times New Roman、Arial、Cambria、Symbol，嵌入或转曲；全尺寸下约 9–10 pt，全文图表字体字号一致 | IEEE 期刊 | 已证实 | https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/file-formatting/ | 2026-11-20 |
| `ieee-color` | ieee | 可及性 | 用灰度打印检查曲线可读；颜色与线型同时编码，曲线直接标注而不只靠图例 | IEEE 期刊 | 已证实 | https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/ | 2026-11-20 |
| `ieee-caption` | ieee | 图注 | 正文与句首都写 “Fig.”；图注写 “Fig. 1.” 加空格再接首字母大写的说明；子图 (a)(b) 写在各自说明前 | IEEE 期刊 | 已证实 | https://docs.google.com/document/d/1OalFYqVfxKKMelF79U3B93SjmIEiTnJC12wPJrKeSDM/ （IEEE Editorial Style Manual，作者中心链接） | 2026-11-20 |
| `ieee-table` | ieee | 编号 | 表号写 “TABLE” 加罗马数字，居中置于表上方，表题在其下居中、末尾不加句号 | IEEE 期刊 | 已证实 | https://docs.google.com/document/d/1OalFYqVfxKKMelF79U3B93SjmIEiTnJC12wPJrKeSDM/ | 2026-11-20 |
| `ieee-units` | ieee | 单位 | 数字与单位间留空格，复合单位用中点（4 V · s）；小数点前补 0 | IEEE 期刊 | 已证实 | https://docs.google.com/document/d/1OalFYqVfxKKMelF79U3B93SjmIEiTnJC12wPJrKeSDM/ | 2026-11-20 |
| `aps-size` | aps | 尺寸 | 按单栏 8.5 cm 设计，细节多的用 1.5 或 2 栏；成品上字高与符号至少 2 mm，数据点至少 1 mm，线宽至少 0.5 pt | Physical Review 系列 | 已证实 | https://res.cloudinary.com/apsphysics/image/upload/v1715884920/aps-journals-style-guide_tnoyln.pdf （APS Journals Style Guide, 2024-11） | 2026-11-20 |
| `aps-axis` | aps | 单位 | 轴标签单位写缩写放括号内，如 R (10³ Ω)，不写 R × 10³ Ω；同轴小数位一致，写 0.2 不写 .2 | Physical Review 系列 | 已证实 | https://res.cloudinary.com/apsphysics/image/upload/v1715884920/aps-journals-style-guide_tnoyln.pdf | 2026-11-20 |
| `aps-caption` | aps | 图注 | 图注不看正文也能读懂；子图 (a)(b) 都在图注中说明；句首写 “Figure”，其余写 “Fig.” | Physical Review 系列 | 已证实 | https://res.cloudinary.com/apsphysics/image/upload/v1715884920/aps-journals-style-guide_tnoyln.pdf | 2026-11-20 |
| `aps-table` | aps | 编号 | 表用罗马数字编号，表题以 “TABLE I.” 开头；表脚注用上标小写字母 | Physical Review 系列 | 已证实 | https://res.cloudinary.com/apsphysics/image/upload/v1715884920/aps-journals-style-guide_tnoyln.pdf | 2026-11-20 |
| `aps-color` | aps | 配色 | 只在线彩色时印刷与在线共用一个文件：选灰度差别明显的颜色并配不同线型，在图注里说明线型；配色符合 WCAG | Physical Review 系列 | 已证实 | https://res.cloudinary.com/apsphysics/image/upload/v1715884920/aps-journals-style-guide_tnoyln.pdf | 2026-11-20 |
| `aps-si` | aps | 单位 | 用 SI（引 NIST SP 330／811），单位间细空格，写 6 J cm⁻³ s⁻¹ 而不写 6 J/cm³/s | Physical Review 系列 | 已证实 | https://res.cloudinary.com/apsphysics/image/upload/v1715884920/aps-journals-style-guide_tnoyln.pdf | 2026-11-20 |

## 综合类期刊：Nature、Science

两刊都要求无衬线字体、可编辑矢量、RGB 和色盲友好配色，但字号和分图标签恰好相反：Nature 用 8 pt 加粗小写 a、b、c，Science 用 10 pt 加粗大写 A、B、C。综合刊图很小，Praxis 论文默认的 12 pt Times 不适用。

| ID | 类型 | 主题 | 规范 | 适用条件 | 状态 | 来源 | 查阅 |
|---|---|---|---|---|---|---|---|
| `nature-font` | nature | 字体 | 图内用无衬线体（Arial 或 Helvetica），全文各图同一字体；正文字 5–7 pt；希腊字母用 Symbol | Nature 及 Nature 系列研究论文 | 已证实 | https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ | 2026-11-20 |
| `nature-panel` | nature | 编号 | 分图标签 8 pt、加粗、正体、小写 a、b、c | Nature 正式稿 | 已证实 | https://www.nature.com/nature/for-authors/final-submission | 2026-11-20 |
| `nature-width` | nature | 尺寸 | 单栏 89 mm、一栏半 120–136 mm、双栏 183 mm、整页高 247 mm；格式指南另写 90/180/170 mm，两页不一致，以正式稿页和当期要求为准 | Nature 正式稿 | 已证实 | https://www.nature.com/nature/for-authors/final-submission ；https://www.nature.com/nature/for-authors/formatting-guide | 2026-11-20 |
| `nature-vector` | nature | 格式 | 线图交 AI、EPS 或 PDF 可编辑矢量，文字线条不栅格化、不转轮廓；字体以 Type 42／TrueType 嵌入（matplotlib 设 `pdf.fonttype: 42`）；线宽 0.25–1 pt | Nature 系列 | 已证实 | https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ | 2026-11-20 |
| `nature-dpi` | nature | 分辨率 | 照片按最大使用尺寸至少 300 dpi；图形指南同页又写建议或最低 450 dpi，取 450 dpi 较稳 | 含照片或显微图 | 已证实 | https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ | 2026-11-20 |
| `nature-style` | nature | 版面 | 有轴线和刻度，单位写在括号里 “Data (unit)”；避免网格线、阴影、填充图案、彩色文字；图内文字只首字母大写、不加句号 | Nature 系列数据图 | 已证实 | https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ | 2026-11-20 |
| `nature-color` | nature | 可及性 | 用无障碍配色（如 Wong 2011 的 Okabe–Ito 色板），色盲滤镜下仍有足够对比，目标 WCAG 2.1 AA；交 RGB | Nature 系列 | 已证实 | https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ | 2026-11-20 |
| `nature-legend` | nature | 图注 | 图注少于 300 词：先一句短标题，再逐个说明分图；有 Methods 时不写方法细节；所有误差线和统计量必须在图注中定义 | Nature 研究论文 | 已证实 | https://www.nature.com/nature/for-authors/formatting-guide | 2026-11-20 |
| `nature-units` | nature | 单位 | 数字与单位间空一格，用 SI 或领域通用单位，千位用逗号；用比例尺不用放大倍数 | Nature 研究论文 | 已证实 | https://www.nature.com/nature/for-authors/formatting-guide | 2026-11-20 |
| `nature-table` | nature | 表格 | 表题为一行加粗短标题，表尽量小，符号与缩写在表下紧接定义 | Nature 研究论文 | 已证实 | https://www.nature.com/nature/for-authors/formatting-guide | 2026-11-20 |
| `nature-stats` | nature | 误差 | 报告每组精确 n、独立样本还是重复测量、检验名称及单双侧、集中趋势与离散度（SD 或 CI）、检验统计量与自由度、尽量给精确 P 值 | Nature 系列含统计的论文 | 已证实 | https://www.nature.com/documents/nr-reporting-summary-flat.pdf | 2026-11-20 |
| `science-font` | science | 字体 | 无衬线体（最好 Arial 或 Helvetica）；标签 6–9 pt，一幅图最多 3 种字号；最细线 0.28 pt | Science 主刊（2025 版制图指南） | 已证实 | https://www.science.org/cms/asset/62583409-a188-466e-8cc0-6fb5f083bbff/author_prep_guide_2025.pdf | 2026-11-20 |
| `science-panel` | science | 编号 | 分图标签 10 pt 加粗大写 A、B、C、D | Science 主刊 | 已证实 | https://www.science.org/cms/asset/62583409-a188-466e-8cc0-6fb5f083bbff/author_prep_guide_2025.pdf | 2026-11-20 |
| `science-width` | science | 尺寸 | 1 栏 9 cm，2 栏 18.3 cm；旧版说明的 5.7/12.1/18.4 cm 只见于搜索摘要，不再采用 | Science 主刊 | 已证实 | https://www.science.org/cms/asset/62583409-a188-466e-8cc0-6fb5f083bbff/author_prep_guide_2025.pdf | 2026-11-20 |
| `science-format` | science | 格式 | 矢量优先 ai、eps、pdf（R 图可存 svg）；位图 psd、png、tif 按最终尺寸 300 ppi，照片 300–500 dpi，不人为插值放大；不栅格化、不合并图层、文字不转轮廓；交 RGB | Science 主刊 | 已证实 | https://www.science.org/cms/asset/62583409-a188-466e-8cc0-6fb5f083bbff/author_prep_guide_2025.pdf | 2026-11-20 |
| `science-color` | science | 可及性 | 避免红绿搭配；避不开时用深浅对比强的两色并加形状或纹理 | Science 主刊 | 已证实 | https://www.science.org/cms/asset/62583409-a188-466e-8cc0-6fb5f083bbff/author_prep_guide_2025.pdf | 2026-11-20 |
| `science-legend` | science | 图注 | 图注格式、长度、误差线定义与表格规则在投稿说明页，本次被人机验证拦截未读到；兄弟刊的规定不能代用 | Science 主刊 | 未查到 | https://www.science.org/content/page/instructions-preparing-initial-manuscript | 2026-11-20 |

## 美赛 MCM/ICM

COMAP 的规则只管页数、摘要页、字号下限、匿名、文件、出处与 AI 报告，**没有规定图表编号、题注位置、配色或灰度**；对图表的期待来自题面（个别题直接要求某种图）、新闻稿中的 “effective writing and visualization” 和 COMAP 站上的评委建议文章。往届 O 奖论文只说明评委接受过什么，标“往届参考”，不是规则。届次规则每年更新，按原题届次再核；交付流程与模板见 [contest-delivery.md](contest-delivery.md#届次格式与阅读文件)。

| ID | 类型 | 主题 | 规范 | 适用条件 | 状态 | 来源 | 查阅 |
|---|---|---|---|---|---|---|---|
| `mcm-pages` | mcm | 版面 | 全文不超过 25 页，摘要页、目录、参考文献、注释与附录都计入；目录为“鼓励”项，参考文献与附录放正文之后 | 2027 届；Tips V20240912 第 5 页同 | 已证实 | https://www.contest.comap.com/undergraduate/contests/mcm/instructions.php ；https://www.contest.comap.com/undergraduate/contests/mcm/flyer/MCM-ICM_Tips.pdf | 2026-11-20 |
| `mcm-summary` | mcm | 版面 | 摘要页（Summary Sheet）是 PDF 第 1 页，用 COMAP 的 Word 或 LaTeX 模板，不能单独提交；FAQ 写明摘要写得差的论文，评委不太可能往下读多少 | 2027 届 | 已证实 | https://www.contest.comap.com/undergraduate/contests/mcm/instructions.php ；https://www.contest.comap.com/undergraduate/contests/mcm/faq.php | 2026-11-20 |
| `mcm-font` | mcm | 字体 | 英文撰写，可读字体且至少 12 pt（含摘要页）；US Letter 或 A4；未指定字体族 | 2027 届；Tips 第 6 页 | 已证实 | https://www.contest.comap.com/undergraduate/contests/mcm/instructions.php ；https://www.contest.comap.com/undergraduate/contests/mcm/flyer/MCM-ICM_Tips.pdf | 2026-11-20 |
| `mcm-file` | mcm | 格式 | 只交一个 PDF，以队号命名；大小上限说明页写 25 MB，Tips（V20240912）第 7 页写 20 MB，两者冲突，按说明页但尽量控制在 20 MB 内 | 2027 届 | 已证实 | https://www.contest.comap.com/undergraduate/contests/mcm/instructions.php ；https://www.contest.comap.com/undergraduate/contests/mcm/flyer/MCM-ICM_Tips.pdf | 2026-11-20 |
| `mcm-identity` | mcm | 版面 | 不得出现学生、教师、学校或地区名；每页页首写队号与页码（如 “Team # 0000000, Page 6 of 25”）；信件落款写 “Sincerely, Team #…” | 2027 届；Tips 第 6 页 | 已证实 | https://www.contest.comap.com/undergraduate/contests/mcm/instructions.php ；https://www.contest.comap.com/undergraduate/contests/mcm/flyer/MCM-ICM_Tips.pdf | 2026-11-20 |
| `mcm-deliverables` | mcm | 版面 | 每题另有交付物，按题面执行。2025：B、D、F 各一页 memo，E 一页 letter，A、C 无；2026：B 一页 letter，C 1–2 页 memo，D、E 1–2 页 letter，A 要 executive-style summary，F 无。各题都要求摘要页、目录、完整解答、参考文献和不计页数的 AI 报告 | 2025、2026 届原题；新届重读题面 | 已证实 | https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/problems/ ；https://www.contest.comap.com/undergraduate/contests/mcm/contests/2026/problems/ | 2026-11-20 |
| `mcm-ai-report` | mcm | 复现 | 25 页之后附 “Report on Use of AI Tools”，不限页数：每条写工具名（版本日期、型号），附 Query 原文和完整 Output；正文用到处行内引用并列入参考文献；翻译软件、代码补全和软件内嵌的 AI 都算，翻译只需一句说明 | AI 政策 v102025（2025-10） | 已证实 | https://www.contest.comap.com/undergraduate/contests/mcm/flyer/Contest_AI_Policy.pdf | 2026-11-20 |
| `mcm-ai-images` | mcm | 格式 | AI 生成的图片、插图是否允许、怎样披露，政策没有专门规定 | AI 政策 v102025 | 未查到 | https://www.contest.comap.com/undergraduate/contests/mcm/flyer/Contest_AI_Policy.pdf | 2026-11-20 |
| `mcm-credit` | mcm | 图注 | 图表须由本队制作，否则在所在位置注明出处；未注明出处的图片、图形、图表可能降奖，构成抄袭的取消资格 | 2027 届；Tips 第 5 页 | 已证实 | https://www.contest.comap.com/undergraduate/contests/mcm/instructions.php ；https://www.contest.comap.com/undergraduate/contests/mcm/flyer/MCM-ICM_Tips.pdf | 2026-11-20 |
| `mcm-visual` | mcm | 版面 | ICM 各题公告都写明团队要用 “effective writing and visualization” 在 25 页内传达结果；2024 MCM C 题直接要求画比赛走势图，2023 春季 Y 题要求报告 “supported with well-chosen graphs” | 2022–2025 届获奖结果 PDF 的新闻稿 | 已证实 | https://www.contest.comap.com/undergraduate/contests/mcm/contests/2025/results/ ；https://www.contest.comap.com/undergraduate/contests/mcm/contests/2024/results/ | 2026-11-20 |
| `mcm-advice-figures` | mcm | 图注 | 每张图表都在正文引用并解释，图注说明内容并标出物理量单位，图要有刻度和轴标签；页、表、图、方程都编号，字号要够大 | COMAP 站点的评委建议文章（Driscoll，《MCM@21》，2014）第 4、6 页；是建议不是规则 | 已证实 | https://www.contest.comap.com/undergraduate/contests/resources/PDF/20YearsofGoodAdvice.pdf | 2026-11-20 |
| `mcm-advice-tables` | mcm | 表格 | 表头不用一眼看不懂的希腊字母或缩写，定义不要埋在段落中间，方程变量都要定义——这是初筛评委最反感的问题 | 同上，第 5–6 页 | 已证实 | https://www.contest.comap.com/undergraduate/contests/resources/PDF/20YearsofGoodAdvice.pdf | 2026-11-20 |
| `mcm-advice-count` | mcm | 版面 | 评委每篇读 5–30 分钟，不放与模型无关的图表；非技术报告（memo、新闻稿）给结论，不写方法和方程 | 同上，第 5–6 页 | 已证实 | https://www.contest.comap.com/undergraduate/contests/resources/PDF/20YearsofGoodAdvice.pdf | 2026-11-20 |
| `mcm-commentary` | mcm | 图注 | 2022–2025 各题评委评语（Judges' Commentary）中对图表的具体意见；全文刊于 UMAP Journal，需会员下载，mathmodels.org 连接失败 | 2022–2025 届 | 未查到 | https://www.comap.org/membership/member-resources/item/umap-journal-46-4-winter-2025-edition | 2026-11-20 |
| `mcm-color` | mcm | 配色 | COMAP 的说明页、Tips、FAQ 与 AI 政策都没有提到彩色、灰度，也没说评委在屏幕上还是打印后阅读 | 2027 届 | 未查到 | https://www.contest.comap.com/undergraduate/contests/mcm/instructions.php ；https://www.contest.comap.com/undergraduate/contests/mcm/flyer/MCM-ICM_Tips.pdf ；https://www.contest.comap.com/undergraduate/contests/mcm/faq.php | 2026-11-20 |
| `mcm-o-figures` | mcm | 版面 | 18 篇可抽取文本的 O 奖论文图数最少 5、中位 13、四分位 11.25–16；只描述展示量，不是评分线或最低图数 | 2018、2021、2022 届 O 奖样本（ICM 偏多，MCM A/B/C 仅 4 篇），2026-10-16 统计 | 往届参考 | [visualization.md 的竞赛图表计划](visualization.md#竞赛论文计划复查默认项) | 2026-10-16 |
| `mcm-house` | mcm | 字体 | 图内文字与正文同为 Times 系（newtx）、普通字号 12 pt，图题为短名置于图下、表题置于表上，配色 Okabe–Ito；按屏幕彩色阅读设计，同时保证灰度可读（`core-gray`） | Praxis 美赛模板 | 项目默认 | [mcm-style.tex](../templates/mcm-style.tex)、[praxis.mplstyle](../templates/praxis.mplstyle) | 2026-11-20 |
| `mcm-house-plan` | mcm | 版面 | 前两页放一张问题—方法—答案总览图，安排一张模型结构图，涉及空间单元时附地图；少于 8 张图只触发计划复查 | Praxis 美赛默认，规则与例外见 visualization.md | 项目默认 | [visualization.md](visualization.md#竞赛论文计划复查默认项) | 2026-11-20 |

## 国赛 CUMCM

国赛规范同样不规定图表编号、题注或字体字号，Praxis 国赛模板的样式都是项目默认。

| ID | 类型 | 主题 | 规范 | 适用条件 | 状态 | 来源 | 查阅 |
|---|---|---|---|---|---|---|---|
| `cumcm-page` | cumcm | 版面 | 白色 A4，四边页边距至少 2.5 cm；摘要页为第 3 页并从此编页码；正文从第 4 页起、无目录、不超过 30 页 | 2026 年修订版格式规范 | 已证实 | https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html | 2026-11-20 |
| `cumcm-font` | cumcm | 字体 | 字体、字号、行距、颜色均不作统一要求，赛区可补充规定 | 2026 年修订版格式规范 | 已证实 | https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html | 2026-11-20 |
| `cumcm-figures` | cumcm | 编号 | 规范中没有图表编号或题注位置的条款 | 2026 年修订版格式规范 | 已证实 | https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html | 2026-11-20 |
| `cumcm-refs` | cumcm | 复现 | 参考文献按科技论文规范列出并在正文标注（未点名 GB/T 7714）；附录放全部可运行源程序；论文与支撑材料各不超过 20 MB 且全部匿名 | 2026 年修订版格式规范 | 已证实 | https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html | 2026-11-20 |
| `cumcm-ai` | cumcm | 复现 | 参考文献前写“AI工具使用声明”，用过 AI 的在支撑材料附“AI工具使用详情.pdf”；声明是否计入页数页面未说明 | 2026 年 AI 工具使用规定（试行） | 已证实 | https://www.mcm.edu.cn/html_cn/node/fef94648f2836ab6cc81586f4c38512b.html | 2026-11-20 |
| `cumcm-house` | cumcm | 图注 | 图题在图下、表题在表上，加粗“图1”“表1”标签、small 字号（约五号）居中；配色 Okabe–Ito；参考文献格式模板未规定，中文稿建议按 `zh-gbt7714` | Praxis 国赛模板 | 项目默认 | [cumcm-style.tex](../templates/cumcm-style.tex) | 2026-11-20 |

## 中文期刊与学位论文

国家标准管参考文献、学位论文结构、量和单位与数字用法；图表细节多由学校规范和期刊须知落实，彼此并不统一。学位论文先找本校当年规范，期刊先读该刊投稿须知，国标只作共同底线。

| ID | 类型 | 主题 | 规范 | 适用条件 | 状态 | 来源 | 查阅 |
|---|---|---|---|---|---|---|---|
| `zh-gbt7714` | zh | 复现 | 参考文献著录用 GB/T 7714-2025（2025-12-02 发布，2026-07-01 实施，现行）；2015 版已废止，旧稿注明所依版本 | 中文期刊、学位论文 | 已证实 | https://openstd.samr.gov.cn/bzgk/gb/std_list | 2026-11-20 |
| `zh-gbt7713` | zh | 版面 | 学位论文编写依 GB/T 7713.1-2025（2025-08-01 发布，2026-02-01 实施，现行），2006 版已废止；其图表条款原文本次未取得 | 学位论文 | 已证实 | https://openstd.samr.gov.cn/bzgk/gb/std_list | 2026-11-20 |
| `zh-gbt7713-figures` | zh | 图注 | GB/T 7713.1-2025 原文中图序、图题、表序、表题位置与编号方式 | 学位论文 | 待确认 | https://openstd.samr.gov.cn/bzgk/gb/std_list （全文未取得） | 2026-11-20 |
| `zh-thesis-example` | zh | 图注 | 机构例：图号图题在图下、表号表题在表上；“图1”“表1”式编号，图表多时可分章编号；宜用三线表；跨页表续排表号与表头；题注宋体五号居中 | 北京理工大学研究生学位论文（研函〔2026〕024号，参照 GB/T 7713.1-2025）；其他学校以本校规范为准 | 已证实 | https://grd.bit.edu.cn/docs/2026-04/8baf5a45d0424c68addba9c036d202c5.pdf | 2026-11-20 |
| `zh-units` | zh | 单位 | 量和单位按 GB 3100-1993、GB/T 3101-1993、GB/T 3102 系列（现行）；GB/T 3102.7-2026、3102.8-2026 将于 2028-01-01 实施；查不到所谓 GB/T 3101-2024 | 中文期刊、学位论文 | 已证实 | https://openstd.samr.gov.cn/bzgk/gb/std_list | 2026-11-20 |
| `zh-numbers` | zh | 单位 | 数字用法按 GB/T 15835-2011（现行） | 中文期刊、学位论文 | 已证实 | https://openstd.samr.gov.cn/bzgk/gb/std_list | 2026-11-20 |
| `zh-journal-example` | zh | 字体 | 期刊例：图中变量用斜体，数字与英文用 Times New Roman 6 pt，一律灰度图；参考文献按引用顺序编号并标 [J]/[M]/[C] | 《数学的实践与认识》；其他刊以本刊须知为准 | 已证实 | https://ssjs.cbpt.cnki.net/EditorA2N/PromptPageInfo.aspx?c=1&t=v | 2026-11-20 |
| `zh-journals-missing` | zh | 图注 | 《应用数学学报》《系统工程理论与实践》《中国科学：数学》的图表须知 | 对应期刊 | 未查到 | https://sysengi.cjoe.ac.cn/ （空页；其余站点证书或权限问题） | 2026-11-20 |
| `zh-house` | zh | 字体 | 中文研究稿用 ctex 与 Fandol 字体，图题在下、表题在上，配色与英文稿相同 | Praxis 中文研究模板 | 项目默认 | [research-zh-style.tex](../templates/research-zh-style.tex) | 2026-11-20 |

## 现有工具与规范的冲突

2026-11-20 对照模板、`texplot.py` 和 `praxis.mplstyle` 的结果。已改的保持旧案例可复现；未改的写明原因，进度在私有工作区 BACKLOG 跟踪。

| 位置 | 与规范的出入 | 处理 |
|---|---|---|
| `texplot.flow_diagram` | 默认用品牌色 teal 框、clay 箭头画论文流程图，违反 `core-palette` | 已改：默认中性灰框黑箭头，可用 `border`／`arrow` 另指定。美赛 2016 A 演示的冻结 PDF 仍是旧色路线图；其生成器的哈希受冻结记录约束，未改，下次重建会得到新配色，重建前另行决定 |
| `texplot.PREAMBLE` 与 `*-paper.tex` | 仍定义 teal、clay、slate、sand | 保留定义以免存档稿编译失败，注释改为“不用于新论文图” |
| `praxis.mplstyle` 的 `savefig.dpi: 180` | 低于各刊位图下限（300 dpi 起，线条图 600–1200 dpi） | 未改：矢量 PDF 不受影响；空间演示记录了该文件哈希且另一项改动未提交。交位图时在 `savefig` 里按目标刊显式给 dpi |
| `praxis.mplstyle` 的 12 pt Times、浅网格 | 只适合美赛；Nature 要 5–7 pt 无衬线且不要网格线，Science 6–9 pt，IEEE 9–10 pt | 不改默认；投这些刊时在样式后追加覆盖，例如 `plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'], 'font.size': 7, 'axes.grid': False})`，并按 89 mm 或 183 mm 宽出图 |
| `research-style.tex`（amsart、Latin Modern） | SIAM 用 siamart，统计刊 AOS 必须用自己的模板 | 模板首行已写“目标刊模板优先”；投稿时换类文件，图内字体跟随正文 |
| `cumcm-style.tex` 题注 small、粗体标签 | 国赛规范不规定字号；学校规范例为宋体五号 | 不冲突，属项目默认；用于学位论文时按本校规范改 |
| 主色与灰度 | main、accent、muted 转灰度几乎相同（`core-gray`） | 规则已写入；texplot 不自动配线型，作者对比两条以上曲线时自己指定 `style`／`mark` |

## 学习与回写

- **检索**：写作、制图、评审动手前按论文类型查本页；用到哪条规则、哪条不适用及理由，记在任务记录里，与 [learning-loop.md](learning-loop.md) 的课程检索相同。
- **被纠正时**：用户、编辑或评审指出某类论文的要求不同，先读该刊或赛事的原页面。读到原文就改本页对应行（规范、来源、查阅日期、状态），旧说法写进 CHANGELOG，不在表里留两条互相矛盾的规则；只有口头说法、读不到原文时，改为“待确认”并在来源列写出处，不当作已证实。
- **项目内的个别要求**（某导师、某会议的特殊格式）不写进本页：在用户项目里用 `lesson_add` 记一条课程，`tags` 含 `paper-standards` 和类型 ID，`evidence` 按实际情况标；同类要求在不同项目里反复出现、并找到一手来源后，再提升为本页规则。
- **新增类型**：在 `scripts/paper_standards.py` 的 `VENUES` 加类型与别名，在本页加一节规则表；`--check` 要求每条有状态、来源、日期和适用条件，每个类型至少一条已证实规则，否则测试失败。
- **复核**：规则以查阅日期为准；换届、改版或超过一年未核的行，用前重读原页。赛事届次规则仍以 [contest-delivery.md](contest-delivery.md#届次格式与阅读文件) 记录的原题届次为准。

## 来源说明

所有链接都在规则表的来源列。本页内容由 Praxis 整理转述，未复制原文；数值照原文抄录。以下页面在 2026-11-20 读不到，相关行已标“待确认”或“未查到”：SIAM 现行作者须知与 2019 版手册、Science 投稿说明页、各 Elsevier 期刊 Guide for Authors、JASA 在 Taylor & Francis 的作者须知、GB/T 7713.1-2025 全文、《应用数学学报》《系统工程理论与实践》《中国科学：数学》的投稿须知。
