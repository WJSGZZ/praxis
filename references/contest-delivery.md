# 竞赛论文的版式与真实交付

仅在交付竞赛作品时读取相应段落，公共来源与语言表达归 [writing.md](writing.md)，作品质量归 [竞赛评审](../evals/contest-judging.md)。先接续赛事—赛项—届次与实际使用模式，官方要求唯一从 [competitions.json](../evals/competitions.json) 对应档案及原官方文件核验；模板默认不是官方规定。未知届次不能继承已确认要求。国赛2026 PDF正式预检显式使用 `python -m scripts.contest_rules paper.pdf --contest cumcm --edition 2026`，检查AI使用／未使用声明的唯一标题及参考文献前位置；不传届次只做兼容机械检查，不能称2026验收。研究生赛2026完整提交使用 `--contest graduate --edition 2026 --document-kind submission`：官方封面在PDF第1页、摘要第2页，匿名与从1开始的页脚计数从摘要起；默认`document_kind=report`仅检查匿名论文部分，不代表完整提交。其2026-09-16 AI规定要求用途对应的工具／版本／来源标注、数据结果说明和代码注释等，不能套用国赛统一声明及详情附件；具体条款按独立官方档案核验。格式检查的机械子集不代表完整赛事验收。

数学研究稿改读 [research-mode.md](research-mode.md) 的研究模板，确定期刊后再核投稿要求；本参考不适用于所有研究论文。

国赛2026的计页与附件边界按[官方格式规范](https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html)（2026-10-14复核第3–5、9–11条）：电子稿从摘要页开始，正文不超过30页，不含摘要专用页与附录，且不放目录。附录包含支撑清单和完整可运行程序；论文与支撑压缩包各不超过20MB，电子文件不放纸质版承诺书及编号页。摘要、正文、附录和支撑内容均按规定匿名。软件默认字体与行距仍是项目排版选择，不能声称官方统一要求；完整AI责任另核同届政策。

## 共享模板与实际成品

内容结构先按 writing.md 的论证职责审阅，再运行 `python -m scripts.paper_template main.tex --contest mcm --review-structure`（其它用途选择对应参数）。最终冻结在源码和构建绑定之后检查同一静态标题树：无实际作用的孤立编号子标题须整理，确有独立作用者用 automation.md 的当前源码绑定理由保留。该检查使用成熟解析库，仍须看实际目录与正文；宏展开、外部章节和完整逻辑质量不由它认证。历史冻结收据保留原范围，不能重标为经过新门禁。

- **共用模板与防漂移**：美赛版式唯一源为 `templates/mcm-style.tex`，正文骨架为 `templates/mcm-paper.tex`，生成器用 `scripts.paper_template` 内嵌同一块样式，输出仍为独立可编译TeX。修改题目不得另外定义全局字体、页边距、段距／行距、标题或页眉；检查命令 `python -m scripts.paper_template main.tex` 会拒绝共享块漂移和常见直接覆盖。中文 v2 固定 TeX 发行版自带的 Fandol 0.3 宋体及粗体、Fandol 黑体、西文 newtx；字体文件清单和SHA256在 `templates/cumcm-fonts.json`，不随操作系统替换。新版式必须经过原生编译、嵌入检查、正确中文提取与逐页渲染；三个系统的持续编译检查见 portable-typesetting CI。旧v1的系统字体依赖已迁移，不继续生成旧版。国赛对应 `templates/cumcm-style.tex` 与同一生成／检查器（`--contest cumcm`），无目录、摘要起页脚编号，禁止套用美赛队号页眉。共同检查覆盖标题层级、目录引线／缩进、段落、图表字号／图注、公式、引用、分页与匿名；按实际赛事选择差异，不硬套同一视觉模板。它不是任意TeX的安全沙箱，也不判断数学或当届合规。正式成品使用 `uv run --locked python -m scripts.paper_template main.tex --contest mcm --compile --output-directory outputs/build-001`（国赛改为 `cumcm`）。编译器 Tectonic 0.17.0 和完整资源包 URL／SHA256 由 `templates/typesetting-runtime.json` 固定；不会自动退回另一编译器。最终冻结使用 `uv run --locked python -m scripts.freeze_pdf outputs/build-001/main.pdf final.pdf --tex main.tex --contest mcm --build-receipt outputs/build-001/main.build.json`；入口在创建文件前验证样式、资源版本、源码与PDF哈希对应。美赛新成品必须走 [automation.md 的当前交付门禁](automation.md#写作连接)：current 编译、同 PDF 字体与全页审阅、current 冻结后再登记 workflow.report；具体必需字段和日志检查只在该处维护。构建记录不代替逐页视觉检查，也不是防篡改认证。确有版式变更先调整唯一源、更新骨架和受影响产物，再做逐页视觉审查；冻结研究另记layout revision，不回写历史首稿或冒充重新数学验证。

- **结构按需选择**：模板规定组件的外观，不规定每篇必须出现同样的组件。标题层级按论证需要使用，不强制二级／三级标题，不设置空章节。短而单一的论证可以只有一级标题；一节含多个独立问题、模型或检验时才按逻辑拆成二级标题。避免单个孤立子标题、标题复述上级、仅一两句话的连续碎节；三级标题仅在确需导航时使用，不为数量整齐而增加。交付前通读整篇，检查相邻章节颗粒度与标题是否准确概括内容；这些是编辑判断，不是固定数量的机器门槛。目录、符号表、假设表、算法框、附录以及客户信按任务与当届规则选择；配图是否必要与图形选择按 visualization.md 比较文字／表格／替代图的阅读价值，不能因模板有位置就画；赛事强制的摘要、编号、披露或附件结构不能因“可选”省略。删组件不改变剩余组件的字体、字号、间距或编号体系。

| 固定排版角色 | MCM v4 | CUMCM v2 |
|---|---|---|
| 纸张 | A4是项目默认；按当届规则可选择Letter，不称A4强制 | 以当届规范为准 |
| 正文 | newtx Times 系，12pt | FandolSong，12pt；西文与数学 newtx |
| 一级至三级标题 | 17.28pt／14.4pt／12pt，三级左对齐粗体 | 四号／小四，一级居中、二级左对齐粗体 |
| 行距因子 | 1.12 | 1.3 |
| 目录（若适用） | 默认二级；需要时选一级或三级，统一点线与层级缩进 | 无目录 |
| 图表 | 图下／表上，12pt图注与普通表格文字；普通轴标题、刻度与图例12pt，数学脚标独立 | 图下／表上，小号图注 |
| 参考文献 | 12pt；连续排版 | 按共享国赛样式 |
| 页码 | 摘要三栏为题号／当届年份与标签／队号，无运行页眉及 Page 字样；后页队号／页码，按PDF连续编号 | 页脚居中，摘要起第1页 |

- **版式**：章节连续排版，不一节一页（官方没有要求时按顶级数学期刊的版式：只有必须独立成页的内容或需明确计页边界的组件另起一页，如摘要页、不计页的美赛AI使用报告和国赛首个附录；普通参考文献及后续附录连续排版，不一节一页）；浮动体页顶端对齐，不垂直居中；标题不孤立在页底；摘要单页；美赛如使用目录则默认列到二级，确需更细导航可通过共享组件选三级，目录与摘要、正文分别起页；使用 `scripts.paper_template.table_of_contents()` 生成前后 `\clearpage`，检查器拒绝遗漏的分页。这是 Praxis 的默认排版约束，不称美赛官方统一要求。 独立尾部用 `scripts.paper_template.ai_report(body)`（完整美赛AI报告）或 `section_component(title, body, separate_page=True, in_contents=False)` 生成，组件前后均用 `\clearpage` 清出浮动体；检查器拒绝标记组件缺任一边界、美赛AI报告缺前分页、重复AI报告或AI之后再放正文／参考文献。已有正确手写分页与历史布局仍可检查，冻结原件不批量重排。国赛2026的“AI工具使用声明”在参考文献之前，用默认连续的 `section_component`；使用AI时另交“AI工具使用详情.pdf”，不能改成美赛式不计页尾部。研究稿的声明和附录按目标期刊选择连续或独立，通用骨架不强制AI节；未知赛事／届次不继承这些政策。国赛不放目录（以当届规范为准）。 中文论文一级标题居中、二级及以下左对齐（国赛优秀论文多如此，字号区分层级），英文论文标题通常左对齐。图中文字用论文的语言；不让标题孤悬在页底（标题后至少跟一段或一张表），参考文献允许在条目之间自然分页，避免同一条目只留半行续页；公式与正文里的变量下标用真正的下标，不写 wi、gi 这样的纯文本。排版用 LaTeX（使用 `templates/cumcm-paper.tex`、`templates/mcm-paper.tex` 的共享版式起步，图形选择与工具按 visualization.md；正式编译走上述固定 Tectonic 入口；其他编译器可辅助预览，但不保证版式相同；中文用 ctexart，Times 系西文用 newtxtext/newtxmath，图由有效数据直接生成，工具按 visualization.md，表用 booktabs 三线表），不用手拼 PDF；公式必须是真公式。每次改版后逐页渲染查看，页数变化时同步 README 的页数与预览页码。


MCM v3/v4的A4选择不提升为官方规定：2026-10-11核对现行2027入口链接的 [MCM/ICM Tips（V20240912，第6页）](https://contest.comap.org/undergraduate/contests/mcm/flyer/MCM-ICM_Tips.pdf)允许US Letter或A4，并要求可读字体至少12pt；按题目届次核其规则。共享PGF默认只影响未局部覆盖的轴；图形生成器必须显式采用相应字体profile，旧版profile保留原字号。正文、caption与bibliography用normal，不能全局重定义small或把数学脚标当正文放大。独立figure即使源字号12pt，`includegraphics`缩放仍会改变最终大小；应控制完整bbox与目标宽度，并在最终PDF核对实际角色字号。静态检查只拒绝共享块和字面全局版式覆盖，不判断任意宏展开，caption中显式normal本身不构成违规；源码检查或独立图编译成功不代替最终字号核验。

## 届次、格式与阅读文件

核对模板要同时阅读当届文字规则、发布方的实际模板源码，并查看真实页面；优秀论文／截图用于理解实现细节，不自动成为当届强制规范。只读到局部时记录页码和范围，不称完成全文对标。2026-10-11核对的 [COMAP说明](https://contest.comap.org/undergraduate/contests/mcm/instructions.php)要求摘要为PDF第1页且每页顶部有队号和页码；[官方TeX样例](https://contest.comap.org/undergraduate/contests/mcm/flyer/MCM-ICM_Summary.tex)在摘要页用空白运行页眉，三栏为题号／年份、MCM/ICM、Summary Sheet／队号，后文重置页码。其文件注释2027、可见年份2026，不能直接沿用这个年份。Praxis新稿用 `summary_header('A', edition=2025)` 明确传入原题届次：摘要不添加 Page 字样，后续按PDF实际页连续编号，不复制样例中重置为1的计数。题号／队号26pt是参考优秀稿的项目字号，官方TeX的 `\Large` 为17.28pt，不能把26pt称官方硬要求。已取得官方[2024 TeX归档](https://contest.comap.org/undergraduate/contests/mcm/contests/2024/problems/MCM-ICM_Summary.tex)与[2025 Word归档](https://contest.comap.org/undergraduate/contests/mcm/contests/2025/problems/MCM-ICM_Summary.docx)：分别含2024／2025；2025 TeX归档的可见年份却仍为2024，需按原题改正。这是当前取得的官方归档字节，不证明与比赛时发布字节完全相同。历届原件不可得时注明实际来源范围。

官方样例只有可选的 `\tableofcontents`，没有统一规定目录点线、标题字重、缩进或层级数量。Praxis共享样式固定一级至三级的外观，正文允许 `\subsubsection`；目录默认两级，按导航价值用 `table_of_contents(depth=1|2|3)` 选择，不手改全局字号或目录计数。摘要／目录／正文分别起页。子标题按论证需要，不为了整齐补空标题或零碎小节。检查器拒绝重复目录、正文后插目录及直接重置页码；静态检查不覆盖任意宏展开，实际PDF仍须核对。历史编译与冻结传 `--layout-mode archive`，并用 `layout_version` 显式选择保留版本，例如1、2或3，分别读取原有 `mcm-style-v1.tex`、`mcm-style-v2.tex` 或 `mcm-style-v3.tex`；只复现原稿，不回写历史。新默认为v4：A4是项目统一选择，正文、图注、参考文献及普通图轴文字用12pt，标题与数学脚标按各自角色。普通英文段落首行缩进2em，一级至三级标题后的首段同样缩进；摘要标题用 `summary_heading()`（TeX为共享 `\PraxisSummaryHeading{Summary}`）接回普通正文段落。列表、图注、参考文献悬挂缩进与信件称呼／签名保持各自角色，不机械改成正文缩进；本改动不改变v3的十二点图形font profile。不能把旧检查通过称为新模板认证，迁移另存排版修订及前后对应关系。

国赛以[2026电子论文规范](https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html)为准，无目录，摘要为第1页且页脚居中。开发生成源／阅读成品统一用 `paper.tex`／`paper.pdf`；已有冻结历史源名保留并明确入口，不批量改写历史引用。公开Demo交付成品统一用 `deliverables/paper.pdf`；已有 `paper.pdf` 阅读入口保留，从同一已验收PDF复制并检查字节一致。实际比赛提交文件按当届要求命名，构建器可保留队号文件名，不能将公开归档名当成官方要求。模拟稿的唯一队号配置为 `scripts.paper_template.MCM_SIMULATION_TEAM`（`7391856`）；它只是项目模拟身份，不声称官方注册。生成模拟稿用 `preamble(title='...', identity_mode='simulation')`，所有当前展示共用这项身份并声明 simulation。真实比赛用 `preamble(actual_team, '...', identity_mode='contest')`，必须由用户／任务明确提供实际分配编号，不能用模拟默认替代。当前编译、冻结与公开展示检查拒绝全0；显式非零旧调用保留兼容，不自动认证注册。历史复现仅显式 `identity_mode='archive'` 加 `layout_version` 保留旧身份，并使用 archive 编译／冻结。文件迁移同步当前链接、导出与证据定位，冻结历史记录保留当时名称。

格式验收区分官方强制要求、赛区／期刊附加要求与本稿排版选择，不把常见模板字号或参考文献样式说成官方规定。 备赛手册中的固定假设条数、引文条数、摘要占页比例、修改次数和字体组合属于经验建议；有用时采用，不设为统一验收门槛。摘要先随结果滚动记录，结果稳定后重写终稿，不到最后才第一次整理。检查字体实际字面与最终 PDF 的嵌入，不只看字体文件名；数学公式用真正的上下标、分式、求和与编号。引文须在使用处标注，责任者、题名、类型、可核实日期和链接一致；未知元数据不补造。验证项数从实际结果读取，性质检查不冒充多套独立算法；最终 PDF 的科研论证审查与版面审查分别验收。写作完成不自动授权公开或提交。


## 披露与提交结构

AI用途、实际模型／工具、真实输入输出与缺日志按 [feedback.md](feedback.md) 和工作项目记录接续；要求以对应届次政策为准。程序日志或贡献摘要不能冒充完整聊天，历史缺失不补造；历史演练身份不改写为正式合规。科学内容不变只重编译受影响产物，不为补旧日志重跑研究。

比赛练习和 demo 按实际题目形成完整论文，正文直接服务题意、模型、结果与论证。不自动插入“演练／非正式作品／尚未人工核验”等工作状态旁注，状态与审查记录放在项目记录或交付说明；必要的假设、适用条件、来源和赛事要求的 AI 声明仍保留。AI 详情据真实过程填写，不能以删除正文旁注为由伪造人工核验。参考官方公开案例时先核实发布方与可读范围，借鉴组织和评价要点；未读全文不声称完整对标，优秀论文不冒称唯一标准答案。

最终交付目录严格按当届赛事的提交对象整理；本地哈希清单、审查报告、交付说明与未压缩工作源不混入上传目录。demo 使用相同文件结构和附录要求。国赛的代码须同时作为完整可运行文件放入支撑包，并列于论文附录，不能仅给仓库链接、伪代码或片段；美赛等其他赛事按自己的单文件／附件规则另行核验，不沿用国赛结构。交付前核对附录清单与压缩包成员一致，真实解压重跑数学计算入口。
