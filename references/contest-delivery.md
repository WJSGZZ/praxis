<!-- praxis:core:start -->
# 竞赛交付

先核赛事—赛项—届次、模拟/正式用途与官方原规范，区分强制要求、项目默认和本稿选择；未知届次保持待核，不继承别届。新稿用现有paper_template API生成骨架与共享样式，模板展示不代表各组件必需，不要求全文读样式源码。特殊组件/赛事才查对应API或profile。

MCM current交付顺序：current编译→当前PDF字体候选与全部页面实际审阅→current冻结→workflow.report登记；一门失败保留候选/失败，不称已交付。全页核标题、图表/公式、版心、居中、遮挡、引用、分页、匿名与真实身份；数学小字号须同PDF逐项真实说明，不批量豁免。改源后重建并复核受影响成品；archive保留原证据，不能追称当前通过。

上传目录仅当届论文、规定附件与支撑；开发收据/工作源另放。国赛附录与支撑包对清单，真实解压并重跑入口。披露按真实工作与当届政策，正式上传/公开/提交另须明确授权。在BUNDLE运行 `PYTHON -m scripts.paper_template TEX --contest mcm --compile --output-directory NEW`，随后 `PYTHON -m scripts.freeze_pdf --help`核必填审阅参数。骨架用paper_template.preamble/summary_header/summary_heading生成。新稿不熟骨架函数签名时先读delivery-api，特殊组件/接口不清亦同；读者字段不清才加载reader-api。
<!-- praxis:core:end -->

<!-- praxis:details:start -->
# 竞赛论文的版式与真实交付

交付时先核赛事—赛项—届次与实际使用模式。官方条款从 [competitions.json](../evals/competitions.json) 的对应档案和原文件核验，把官方要求、附加要求与本稿选择分别记录。未知届次标待核，练习与正式提交分别验收。公共表达归 [writing.md](writing.md)，必备件归 [contest-paper-checklist.md](contest-paper-checklist.md)，奖档意见归 [竞赛评审](../evals/contest-judging.md)，AI 披露与贡献归 [integrity.md](integrity.md#ai-披露与贡献)。研究稿选 [research-mode.md](research-mode.md)，确定期刊后核投稿要求。

## 共享模板与实际成品

先审内容与章节职责，再选择模板和执行入口。完整命令、组件参数、身份 API、源码绑定与审阅字段唯一见 [automation.md](automation.md#写作连接)。下表是导航，赛事参数按实际用途选用。

| 赛事 | 模板 | 编译命令 | 冻结命令 | 身份参数 |
|---|---|---|---|---|
| MCM/ICM | `templates/mcm-paper.tex`；共享 `mcm-style.tex` | [paper_template --compile --contest mcm](automation.md#竞赛模板与组件-api) | [freeze_pdf --contest mcm](automation.md#竞赛模板与组件-api) | [simulation／contest／archive](automation.md#竞赛模板与组件-api) |
| CUMCM | `templates/cumcm-paper.tex`；共享 `cumcm-style.tex` | [paper_template --compile --contest cumcm](automation.md#竞赛模板与组件-api) | [freeze_pdf --contest cumcm](automation.md#竞赛模板与组件-api) | 匿名；[用途与届次参数](automation.md#竞赛模板与组件-api) |
| 研究生赛 | 按对应官方封面及报告规范选模板 | [固定编译入口，核实际支持的 profile](automation.md#竞赛模板与组件-api) | [真实用途的冻结入口](automation.md#竞赛模板与组件-api) | 匿名；完整 submission 含官方封面 |

共享样式是唯一版式源，改题沿用同一字体、页边距、段落、标题与页眉配置。版式变更先改唯一源和骨架，再重建受影响产物并逐页审阅。历史研究另存 layout revision，保留首稿和数值验证身份。三个系统的持续编译、嵌入与文字提取核对见 portable-typesetting CI；真实 PDF 继续检查标题层级、目录、段落、图表、公式、引用、分页和匿名。

组件按论证与当届要求选择：短单一论证可只有一级标题，多个独立问题才拆节；相邻章节粒度相称，标题覆盖实际内容。孤立 x.1 优先并入父节，确有独立定位／交叉引用／规定职责则保存源码绑定理由。采用摘要、目录、符号、假设、算法框、附录或客户信时，各自承担明确职责；赛事强制组件逐项对照原规范。图表选型按 [visualization.md](visualization.md)，删选组件后仍沿共享外观和编号。

| 固定排版角色 | MCM v5 | CUMCM v2 |
|---|---|---|
| 纸张 | A4是项目默认；当届允许时可选Letter | 以当届规范为准 |
| 正文 | newtx Times 系，12pt | FandolSong，12pt；西文与数学 newtx |
| 一级至三级标题 | 17.28pt／14.4pt／12pt，三级左对齐粗体 | 四号／小四，一级居中、二级左对齐粗体 |
| 行距因子 | 1.12 | 1.3 |
| 目录（若适用） | 默认二级；按导航价值选一级或三级，点线与缩进统一 | 无目录 |
| 图表 | 图下／表上，12pt图注、普通表格、轴标题、刻度及图例；数学脚标独立 | 图下／表上，小号图注 |
| 参考文献 | 12pt；连续排版 | 按共享国赛样式 |
| 页码 | 摘要三栏为题号／当届年份与标签／队号；后页队号／PDF连续页码 | 页脚居中，摘要起第1页 |

中文 v2 固定 TeX 发行版的 Fandol 0.3 宋体及粗体、黑体，西文与数学用 newtx；清单见 `templates/cumcm-fonts.json`。当前 MCM v5 的普通英文段落首行缩进2em，一级至三级标题后的首段同样缩进。列表、图注、参考文献悬挂缩进和信件称呼／签名保留各自角色。正文、caption、bibliography 用 normal，数学脚标按数学角色审阅。

MCM v5 增加可选 `memo` 环境（收件人、日期、主题，前后各清页）、`strengths`／`weaknesses` 列表、`algorithm`／`algorithmic` 伪代码、`subfigure` 子图和 theorem／lemma／proposition／corollary／definition／remark 定理组件。`scripts.paper_template.memo` 转义三个文字字段，正文保留调用者的 TeX。完整示例在 `templates/mcm-paper.tex`；按题意选用，模板展示不代表每篇必须出现。旧 v4 样式逐字节保留在 `mcm-style-v4.tex`，旧稿编译和冻结显式选 `--layout-mode archive`，当前模式拒绝旧版。

章节连续排版，浮动体页顶端对齐，标题后跟正文或表图；参考文献自然续排。摘要单页，采用目录时摘要／目录／正文分别起页；默认目录二级，细导航按共享组件选层级。美赛完整 AI 报告独立尾部，首个国赛附录按计页边界独立起页；其他组件按实际规则连续或独立。保留真实的公式、上下标和编号，表格按共享三线表样式；图中文字用论文语言。每次改版逐页核版心、居中、遮挡、引用与自然分页，页数变化同步当前 README 和预览页码。

独立图的源码字号与最终字号分别核对：完整 bbox、导入宽度及缩放一起决定实际角色大小。图生成器显式选对应 font profile，旧 profile 保留原身份。源码静态检查、图单独编译、最终 PDF 字号与视觉审查各保存实际覆盖范围。当前 MCM 的十二点、摘要单页、AI 独立尾部、日志零溢出、依赖字节与完整页审阅门禁见 [automation.md](automation.md#写作连接)。

## 届次、格式与阅读文件

同时阅读当届文字规则、官方模板源码和真实页面，优秀论文／截图只辅助理解实现。局部阅读记录页码与范围。以下保留既有核查日期和来源；本轮整理文档未重新网络复核。

- **MCM/ICM**：2026-10-11 核对现行2027入口的 [MCM/ICM Tips，V20240912，第6页](https://contest.comap.org/undergraduate/contests/mcm/flyer/MCM-ICM_Tips.pdf)，允许 US Letter 或 A4，可读字体至少12pt；实际稿按原题届次核规则。A4、26pt题号／队号、目录外观和2em缩进均标项目选择。
- **摘要身份与官方归档**：同日核对 [COMAP说明](https://contest.comap.org/undergraduate/contests/mcm/instructions.php) 和 [官方TeX样例](https://contest.comap.org/undergraduate/contests/mcm/flyer/MCM-ICM_Summary.tex)。说明要求摘要为PDF第1页且每页顶部有队号与页码；样例摘要空运行页眉、三栏身份，后文重置页码。样例注释2027而可见2026，按实际原题校正。已取得 [2024 TeX](https://contest.comap.org/undergraduate/contests/mcm/contests/2024/problems/MCM-ICM_Summary.tex) 和 [2025 Word](https://contest.comap.org/undergraduate/contests/mcm/contests/2025/problems/MCM-ICM_Summary.docx) 分别显示2024／2025，2025 TeX可见年份仍为2024；记录取得字节身份与比赛当时原件可得性。Praxis摘要沿三栏且无 Page 字样，后文按实际PDF连续编号。
- **CUMCM 2026**：2026-10-14 复核 [官方格式规范第3–5、9–11条](https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html)。电子稿摘要起编号，正文不超过30页，不含摘要专用页与附录，无目录；附录列支撑清单及完整可运行程序。论文与支撑包各≤20MB，电子文件仅按电子对象整理，纸质版承诺书／编号页另按纸质流程。摘要、正文、附录和支撑均匿名。字体与行距标项目默认。
- **CUMCM 2026 AI**：声明在参考文献之前连续排版，核唯一标题；使用 AI 时另交“AI工具使用详情.pdf”。按该政策核正文计页与附件，独立美赛尾部按 MCM 自己的规则处理。
- **研究生赛2026**：完整 submission 的官方封面在PDF第1页、摘要第2页；匿名及从1开始页脚从摘要起。默认 report 只检查匿名报告部分，完整提交另核封面。按2026-09-16独立AI档案核用途对应的工具／版本／来源、数据结果说明与代码注释；按本赛事原条款组织披露。

模拟稿固定用 `7391856`，角色为项目模拟身份；真实编号从用户／任务的实际分配来源取得，当前编译、冻结与展示拒绝全0。历史身份显式 archive 并选择原布局。具体生成参数、摘要年份、目录、连续／独立组件和编译归 [automation.md](automation.md#竞赛模板与组件-api)。旧检查、当前样式和注册身份各写实际范围。

正式主源与成品命名按 [writing.md](writing.md#正式报告文件命名)，新任务使用 `report.tex`／`report.pdf`，交付目录中的主报告也使用 `report.pdf`；兼容入口从同一已验收PDF复制并核字节。现有展示案例的 `paper.*` 等路径是保留的历史身份，不作为新任务默认名。比赛上传名称另核当届要求。目录、字号、假设条数、引文数、修改次数等经验建议按实际价值采用，官方与项目选择分开记录。

## 披露与提交结构

report 阶段按 [integrity.md 的AI披露与贡献](integrity.md#ai-披露与贡献) 汇总真实记录，原始交互和缺口接 [feedback.md](feedback.md)。正文围绕题意、模型、结果与论证；工作状态放项目记录或交付说明，必要假设、条件、来源和官方AI声明保留在对应位置。科学内容未变时只重编受影响产物。

最终上传目录按当届提交对象整理：论文、规定附件与支撑；本地收据、审查报告、交付说明和工作源放开发目录。demo 采用对应提交文件结构与附录要求。国赛完整可运行代码同时进入支撑包并列于论文附录，交付前核附录清单与压缩包成员，真实解压并重跑计算入口；美赛及其他赛事分别核自己的单文件／附件政策。科研内容、格式、页面、披露和提交授权分别留验收结论。
<!-- praxis:details:end -->
