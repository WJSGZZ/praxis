# 更新记录 · Changelog

版本号按语义版本：0.x 表示仍在快速变化，技能名或工具接口有不兼容改动时升次版本号。只记录对使用者有影响的变化。
Versions follow semantic versioning; 0.x means the skills and tools are still changing. Only user-visible changes are listed.

## 未发布 · Unreleased

- 美赛与 ICM 模拟稿使用统一固定模拟队号 `7391856`；真实参赛显式提供实际队号，当前编译、冻结和展示检查拒绝全0占位。十篇当前公开作品的身份与元数据同步，历史冻结稿保留原件；不改变科学结论或奖档判断。
  MCM and ICM simulations use the fixed house team `7391856`. Real entries require an explicitly supplied assigned number, and current compilation, freezing and gallery checks reject all-zero placeholders. Current papers and metadata agree; frozen history, scientific conclusions and award references keep their original scope.

- 新增 `asof_join`，复用 Pandas 按决策截点选择声明的可用版本，保留缺失时点、同刻冲突与未发布查询。数据分析和时序专业入口共享字段版本契约；完整合成补货任务以独立时间扫描与整数穷举核对，并比较合法预测、固定基线与无效的事后快照。原工具接口与依赖保持。
  `asof_join` uses Pandas to map declared versions to decision cutoffs, preserving unknown availability, tied releases and unpublished queries. Data and time-series routes share the field-vintage contract. A complete synthetic replenishment exercise uses independent timestamp scans and integer enumeration to compare available forecasts, a fixed baseline and an invalid final snapshot. Existing tool interfaces and dependencies are unchanged.

- 公开美赛作品按题目展示，每题只保留最好的一份；十题十稿使用固定文件名与统一选择清单。主 Demo 同步为完整 28 页稿，旧研究版与失败证据保全到历史。双语入口、生成源、预览和导出同步，检查器拒绝重复题目及残留稿。
  The public MCM gallery selects one best paper per problem, with ten works under stable filenames and a shared catalog. The primary demo now presents the complete 28-page manuscript; earlier research versions and failures remain preserved in history. Bilingual links, source, previews and exports agree, with checks against duplicate problems and orphan papers.

- 当前美赛交付统一使用共享 v4：A4、普通正文和图表文字 12pt、摘要与标题后首段缩进 2em、身份一致的摘要页和独立起页的 AI 报告。15 份研究稿已完成格式迁移与逐页检查，公开展示按每题一份的清单选择成品；旧科学记录与冻结原件保留。
  Current MCM delivery uses the shared v4 layout: A4, 12pt ordinary prose and figure text, two-em indentation after summary and section headings, consistent identities and a separate AI-report start. Fifteen active reading copies were rebuilt and visually reviewed; frozen originals and scientific records retain their versions.
- 构建拒绝实际页框／身份不符及文字或浮动体溢出；冻结强制检查当前构建、真实字号、数学例外说明和绑定当前 PDF 的全部页面审阅。共用成熟 LaTeX/PDF 工具，不新增运行依赖。历史稿显式选择 archive，研究与国赛保持各自规则。
  Compilation rejects mismatched page geometry or identity and actual typesetting overflow. Freezing requires a current build, measured font sizes, explicit mathematical-role reviews and an exact-PDF all-page review. Existing LaTeX and PDF libraries are reused; archived layouts require explicit archive mode, while research and CUMCM keep their profiles.
- 次要案例增加三份完整学习作品，按问题类型组织版本、方法和局限；中英文首页、图库、复现入口和安装说明同步。AI 参考意见未校准，不等于正式获奖或首次自主 O 成功。
  Three complete learning works join the secondary gallery with organized methods, versions and limits. Both README languages, reproduction entry points and installation guidance are synchronized. Uncalibrated AI opinions establish neither actual awards nor first-autonomous O success.

### 收紧的交付要求 · Stricter delivery checks

- 美赛编译与布局冻结默认 `current`，旧版式必须显式 `--layout-mode archive`。只有实际审阅后的冻结副本才能登记为成品。浴缸复现的 `--candidate` 生成待审预览；正式交付要求当前字号及逐页审阅记录，并拒绝覆盖旧交付。
  MCM compilation and layout-gated freezing default to `current`; historical layouts require `--layout-mode archive`. Register reviewed frozen copies as deliveries. The bath generator's `--candidate` creates an unsealed preview; delivery requires current font and all-page review records and refuses to overwrite an earlier submission.

## 0.8.0 · 2026-10-13

- 新增图像分析专业入口与 `binary_components` 工具，复用 SciPy 测量显式二维二值掩码的连通区域、面积、边界框和质心。物理尺度由调用者显式声明，像素连接不自动等于真实对象；默认依赖保持。
  Image analysis adds a specialist route and a SciPy-backed `binary_components` tool for supplied 2-D binary masks. Measurements include connected regions, areas, boxes and centroids. Physical scale is caller-declared, and a connected region does not certify a real object. Default dependencies are unchanged.
- 新增可复现的原创图像测量案例，连接邻接、边界排除、区域面积过滤和尺度选择，给出独立小例核验与实际科研图；专业规范明确原图像家族先分割、后增强，语义标签和部署概率须另核。
  A reproducible synthetic image study links adjacency, border exclusion, region-size filtering and declared scale to independently checked measurements and scientific figures. Image-family splits precede augmentation; semantic labels and deployment probabilities retain separate validation requirements.
- 完善目标人群与选择运输、零事件重采样的指标定义、跨期资源与外部支持、共同情景比较和技术结果到读者动作的专业职责。三份自主美赛论文进入次要案例，保留各自版本、范围和未校准评议。
  Shared guidance covers population targets, selection transport, zero-event resampling, recurring resources, priced external support, matched comparison conditions and actionable scientific writing. Three autonomous competition papers join the secondary gallery with their version-specific scope and uncalibrated reviews.
- 双语首页与安装入口同步；发布说明从对应版本的双语更新记录生成。新增展示一致性检查，核对实际技能／工具目录、版本和下载入口；旧发布附件与数学证据保持原身份。
  Both README languages and installation entry points are synchronized. Release notes are rendered from the selected bilingual changelog entry. Presentation checks compare the actual skill/tool registry, version and download links; historical packages and mathematical evidence keep their identities.

## 0.7.1 · 2026-10-13

- 增加空间分析专业入口，共二十三个技能，处理坐标与单位、空间关系、栅格对齐和覆盖／可达约束；复用现有SciPy与网络优化，专业GIS库按实际需要另选，不增加默认依赖。
  Spatial analysis joins the specialist routes, with explicit coordinate frames, distance and join semantics, raster alignment and local accessibility. Existing scientific libraries support the runnable coverage example; larger GIS workflows retain their own dependencies and scope.
- 原创空间覆盖案例同时给名义与位置误差下的容量方案、解析界、局部故障割和科研图。优化与建模职责区分可行见证、必要资源、联合可行域及原题的更宽解释。
  A synthetic coverage study connects distance boundaries to allocation, uncertainty and resource guarantees. A feasible configuration does not establish a universally necessary resource vector, and added restrictions do not exclude the wider original task.
- 修复带替换关系的经验重试：同内容、同父集的活动记录复用原ID和历史字节；错误父集和退役记录仍拒绝。安装新进程与当前聊天服务分别验证，保留旧服务的失败诊断。
  Retrying an active lesson replacement now reuses its identity without appending history. Invalid targets and retired records stay rejected. Host guidance distinguishes installed files, fresh-process checks and a still-running chat service.

## 0.7.0 · 2026-10-13

- 增加七个专业入口：科研写作、文献比较、优化、动态建模、不确定性、监督学习和实验设计，共二十二个技能。入口按请求选择，共用计算、独立验证与交付规范；科学写作吸收成熟公开资源的论证机制，按许可原创整理。
  Seven focused skills cover scientific writing, literature, optimization, dynamics, uncertainty, supervised learning and experimental design. The twenty-two skills share existing execution, verification and delivery contracts, with writing guidance adapted from primary sources and attributed public resources.

- 新增 `cross_validate_predictor`，工具共六十五项：数值Ridge／0–1 Logistic、独立行或完整留组分割、训练折中位数填补与尺度变换、训练Dummy基线及逐行OOF损失。固定参数，不执行调参、最终refit或外部校准；分组独立和上游信息时点仍须审查。scikit-learn最低版本为1.6，对应分组分割API。
  The 65-tool registry adds numeric Ridge and binary Logistic cross-validation, with iid or whole-group splits, fold-local imputation/scaling, training-only dummy baselines and row-weighted out-of-fold losses. It does not tune, refit a deployment model or certify external calibration; group independence and upstream information availability remain explicit assumptions. The scikit-learn minimum is 1.6 for the group-split API.

- 新增次级美赛案例入口，区分自主、学习和研究身份及当前／历史评阅；完整自产论文在源码案例页开放，原题、参考论文和私有运行记录不进入插件。2020C学习稿完成论证修订、词法说明勘正及推荐模型参数补充，保留原自主稿与学习冻结。
  A secondary MCM gallery distinguishes autonomous, learning and research identities and current versus historical review scopes. Authored papers are available from the source gallery. The 2020C learning paper receives a substantive writing revision, corrected lexical descriptions and the recommended model's parameters; earlier autonomous and learning snapshots remain preserved.

- 经验检索的结构汇总支持历史多标签记录，每条经验同一标签只计一次，保留原JSONL字节与身份。真实旧记录触发的检索崩溃已修复。
  Lesson search accepts historical multi-label structures, counting each tag once per lesson while preserving stored records. This fixes a reproduced search failure on existing project history.

## 0.6.1 · 2026-10-12

- 共享美赛模板升级为v4：摘要和三级标题后的首段与普通正文统一缩进2em。独立摘要组件沿用LaTeX机制，实际PDF字框核验；旧v1/v2/v3样式继续支持明确的归档复编。公开浴缸论文、生成源及预览同步，数学数据和历史评议身份保持。
  The shared MCM v4 layout indents the summary and paragraphs following all three heading levels by 2em, matching ordinary prose. A shared summary component uses standard LaTeX behavior and is checked in rendered PDFs. Explicit archived v1/v2/v3 layouts remain reproducible; the bath paper and previews are synchronized without changing its mathematical evidence or historical reviews.

- 文本到行动的分析先区分对象、属性和评价方向，并保留上下文、重叠及比较分母；非线性回归的形状解释核实际编码、链接、导数和观测域。共用现有专业入口与数学工具。
  Text-based actions distinguish the object, attribute and evaluation direction, retaining context, overlap and comparison denominators. Nonlinear interpretations check coding, links, derivatives and the observed domain. Existing specialist routes and tool interfaces remain in use.

## 0.6.0 · 2026-10-12

- 新增六个专业入口：数据分析、统计推断、文本分析、时间序列、因果分析与科研绘图。主技能按问题调用十五个入口，复用现有成熟库与共享规范，不以技能数量认证能力。
  Six focused skills cover data analysis, statistical inference, text analysis, time series, causal reasoning and scientific visualization. The core routes to fifteen skills using established libraries and shared guidance; skill counts are not a capability certificate.

- 新增 `audit_join` 和 `adjust_pvalues`，工具共64项。连接审计声明键类型、基数、空值政策、覆盖与展开上限；多重检验声明完整比较族及FWER／FDR条件。OLS可显式使用分组稳健协方差与G−1参考，自采样设计和因果识别仍须另审。
  The 64-tool registry adds cardinality-aware join audits and family-aware multiplicity adjustments. OLS supports explicitly requested one-way cluster covariance with a G−1 reference; sampling validity and causal identification still need separate review.

- 数据审计保留原始表头、重复名及重命名位置，区分缺失、非有限原值与统计溢出；CLI拒绝覆盖原数据或源契约的直接路径、符号链接及硬链接。新合成门店Demo连接48条记录与12个独立组，核对有理协方差、Holm结果、原CSV和实际图形；不声称真实经营收益或因果效果。
  Data audits disclose raw headers and parser renaming, distinguish missing/non-finite observations from summary overflow, and refuse source-data or contract aliases as output targets. A synthetic 48-record, 12-store Demo checks rational covariance, Holm arithmetic, original inputs and the rendered figure without claiming real commercial or causal benefits.

- 共享PGF绘图把未命名辅助曲线排除出图例，拒绝NumPy非有限坐标，转义普通文字中的TeX特殊字符。实际图例反例、新Demo与原美赛26页逐页文字／栅格复现核对；原冻结稿及数值证据保留。
  Shared PGF figures exclude unnamed helper series from legends, reject NumPy non-finite coordinates and escape plain-text TeX characters. A real legend counterexample, the new Demo and a page-by-page 26-page MCM replay check the correction; archived outputs and numerical evidence remain intact.

### 不兼容变化 · Breaking changes

- `compare_models(scheme="time")` 的持久性基线改为每个测试块只用训练末值，与其它模型共享预测起点；过去逐步读取测试真实值的基线成绩会改变。历史结果不重写。
  The persistence baseline in time-based model comparisons now uses the last training observation for the entire test block. Scores change where the previous baseline read later test outcomes; historical results are not rewritten.

- 同一显示名对应多个不同类型表头时，旧的按名称汇总项返回 `null` 加原因，完整逐位置画像保留；源契约须解决歧义后才能匹配。
  When differently typed headers share a display name, legacy name-keyed summaries return `null` with a reason while positional profiles remain complete. Source contracts must resolve the ambiguity before matching.

- 证据JSON拒绝重复键；案例版本仅接收已支持的整数1或旧稿缺省v1；声明检查名称须为字符串列表。工作流状态与经验入口沿同一重复键门禁，不再静默接受歧义预算／结论。正常历史v1、共用定义及合法独立核验保留，不把独立声明升级为认证。
  Evidence readers refuse duplicate JSON keys, unsupported case versions and claim-check references that are not string lists. Workflow budgets and lesson intake use the same duplicate-key check. Legacy v1 and legitimate shared definitions remain supported; independence labels remain declarations requiring methodological review.

- MCP超限帧排空拒绝，重复键、非法UTF-8与过深JSON解析后仍可处理下一请求；注册表达式工作进程有限捕获stdout／stderr，超限拒绝并回收直接子进程。补公开安全政策和实际私密漏洞报告渠道，明确这不是CPU／内存、文件／网络或子进程树沙箱。
  MCP refuses oversized, ambiguous or invalid frames and recovers for the next request. Expression workers capture finite stdout/stderr and reject overflow, killing and reaping the direct child. A security policy and private reporting channel describe the protection and its limits; neither is a resource or permission sandbox.

- 安装指南提供六种宿主ZIP与校验入口、PowerShell和通用uv路径示例；同步十五技能与0.6.0状态，首页测试覆盖指向实际CI记录。
  Installation guides link the six released host packages and checksums and provide PowerShell and portable uv invocation examples. Skill/version descriptions are synchronized, and test coverage links to actual CI records.

- 表达式工作进程固定UTF-8文本协议，接受输出前复核墙钟截止；MCP拒绝未配对Unicode代理字符与非有限协议值，回复和pipeline路径JSON不依赖系统代码页。三OS小数值合同同时使用含空格及中文的工作区。
  Python expression workers use a fixed UTF-8 channel and recheck the deadline before accepting output. MCP refuses unpaired Unicode surrogates and non-finite protocol values; JSON replies and pipeline paths survive legacy code pages. The three-OS runtime contract includes spaces and Chinese workspace names.

- 投资案例新增“给定净收益目标，求原交易费与预算下的最小风险”，含六组精确原始／对偶证书、向上取分的充分资金门槛、银行边界、不可达目标和小资金反例。同步35页论文、32项支撑附件、预览及两个独立复现入口；历史几何拐点保留为条件示例，当前稿不继承未校准的旧奖项判断。
  The investment Demo now converts an explicit return target into the least risk under the original fees and budget. Six exact primal/dual certificates, sufficient funding thresholds rounded up to cents, bank and unreachable boundaries, and a small-budget counterexample accompany the updated 35-page report, 32-file support archive and two reproduction entry points. Geometric knees remain conditional examples; the current report abstains from an unverified historical award assessment.

- 方案比较先在原单位核对硬能力，再解释归一化分数；联合事件概率须核对边际、依赖与时间单位，不把加权绩效当作联合可靠性。上述条件融入原方法参考，不增加重复工作流。
  Decision comparisons check hard capacity in original units before interpreting normalized scores. Joint-event probabilities require explicit marginals, dependence and time units; weighted performance is not joint reliability. These conditions extend the existing method references.

## 0.5.0 · 2026-10-11

- 插件安装界面与输入框图标使用现有新版 Logo，与源码中的品牌资产共用来源并进入导出哈希；插件元数据不再保留过时的技能数量。保留原 `praxis` 身份，现有数学接口继续使用。
  Plugin presentation and the composer icon now use the maintained brand asset, included in the export receipt. Metadata describes the professional capabilities without a stale skill count. The `praxis` identity and existing mathematical interfaces are retained.

- 章节结构用 pylatexenc 的语法树预检，并接入带源码的最终冻结；孤立编号子标题须整理或给出当前源码绑定的具体保留理由。整稿审阅连接题意、前提、模型、证据和条件答案，学习按多个维度记录实际应用与未验证部分，不以阅读篇数认证掌握。
  Heading review uses pylatexenc and is enforced when freezing a source-bound paper. Sole numbered child headings need a revision or a documented reason tied to the exact source. Whole-paper review follows the question, premises, model, evidence and scoped answer; learning records distinguish observation, application and verification across dimensions.

- 新增薄 `praxis-assumptions` 入口，专管显式／隐含前提、依据、用途与失效影响；主技能按用途及届次选择共享专业模块，比赛规则保持单一档案，导出共含九个技能。
  A focused assumptions skill reviews premises, reasons, uses and failure effects. The core selects shared capabilities by task and contest edition; event-specific rules stay in their existing registry, and exports contain nine skills.

- 假设按实际用途、理由、关键影响与结论范围评审，明确最小模型不等于少列前提；重要共同假设通常集中成章，局部条件随模型交代，数量不作质量判据。规则依据COMAP说明、参赛指南与历年评委经验，保留现有诊断权重及历史评价。
  Assumptions are reviewed for their role, justification, effect on key conclusions and scope. A minimal model still states all relevant premises. Substantial shared assumptions usually receive a dedicated section, with local conditions explained alongside each model. Counts do not determine quality; guidance draws on COMAP instructions and judges' advice while preserving diagnostic weights and historical assessments.

- 最终字号预检测量PDF变换后的文字，较小数学字形须逐项审阅并绑定当前PDF；冻结入口可在写文件前执行同一检查。国赛2026显式届次检查AI声明位置，研究生赛区分匿名报告与保留封面的完整提交；其2026 AI政策按用途核验。目录标题约束与当前浴缸稿的四处范围标题同步，历史稿及科学评阅保持。
  Final-size inspection measures transformed PDF text, with individually reviewed mathematical exceptions bound to the current PDF; snapshot creation can enforce the same check before writing. Explicit CUMCM 2026 checks validate the disclosure position, while graduate checks distinguish an anonymous report from a submission with its official cover. Its 2026 AI policy is tracked by use. Contents-heading guidance and four scoped bath headings are synchronized; historical papers and scientific reviews remain intact.

- 美赛共享v3默认A4，正文、图注、参考文献与普通图中文字用12pt。绘图API提供显式字体profile，独立图的完整边界与最终嵌入字号一并核验；旧v1/v2、历史评议和数值记录保留，原默认绘图输出不变。
  The shared MCM v3 layout defaults to A4 with 12-point body text, captions, references and ordinary figure text. Plot generators select an explicit font profile, and imported figures are checked at their final displayed size. Archived v1/v2 layouts, review identities and numerical records remain intact; existing default plot output is preserved.

- 当前浴缸案例的生成器、PDF和预览改用含原题年份的统一美赛首页；历史稿及其科学评阅绑定保留。未检出结论另核观测努力、检出概率与独立性，避免把零记录直接解释为不存在。
  The active bath example now uses the shared MCM summary header with its original contest year, and its PDF and previews are synchronized. Historical review identities remain intact. Absence claims check observation effort, detectability and dependence before interpreting zero detections.

- 作品评审在确定严重度前独立核对时点、单位、定义及阈值是否改变实际推荐或资格，并按同一根因追踪受影响主张；影响未核明不默认归为可选澄清。
  Full-paper review checks how timing, units, definitions and thresholds affect the actual decision before assigning severity, and traces affected claims by root cause. Unchecked impact remains unresolved instead of becoming optional wording.

- 共享论文组件明确连续与独立分页；美赛AI报告的生成、检查及冻结阻止混页和后置正文，国赛骨架补参考文献前的2026 AI声明及清晰的首附录边界，研究稿仍按目标要求选择。PDF计页不再把AI或附录标题前的正文／参考文献整页漏算。
  Shared paper components distinguish continuous sections from isolated parts. MCM disclosure boundaries are checked before build and freeze; the CUMCM skeleton places its 2026 declaration before references and isolates the first appendix. Research structure remains selectable. PDF counting no longer exempts solution or reference text on a shared disclosure/appendix page.

- 提供显式 Codex 导出记录选择器，保留真实消息与工具输入／输出的来源和快照边界；不重建缺失聊天或认证正式 AI 披露完整性。
  An explicit Codex export selector preserves emitted messages and tool records with source hashes and snapshot limits, without reconstructing missing history or certifying disclosure completeness.

- 新增薄 `praxis-review` 入口，完整作品的竞赛／研究评价与数学核验、写作修改明确交接；赛事标准、共享交付和研究六项定性标准按需读取，未知届次及无数值 profile 的研究生赛不默套其它规则。
  A focused whole-work review skill separates contest and research judgments from claim verification and report editing. Criteria and delivery requirements load by purpose and edition; a graduate-contest review without a numerical profile remains qualitative.

- 美赛新稿采用 v2 摘要组件：原题年份必须明确传入，题号与队号加大，首页不叠加运行页码。正文可按需要使用三级标题，目录深度由共享组件选择，保持统一字号与引线；检查器拒绝缺年份、重复目录和直接覆盖。冻结案例显式保留 v1，保存其真实生成源，并核对活动入口的完整论文复现。
  New MCM papers require the original contest year in a shared three-column summary header, with larger problem and team identifiers and no running page label on the summary sheet. Optional third-level sections and selectable contents depth share the same typography. Frozen cases keep an explicit v1 layout and their actual historical generator; complete regeneration is checked separately from the sealed PDF identity.

- 修正数学接口证据与交付：数值违例不自动成为证明，有理候选单独精确核验；零残差及秩亏诊断保留结果并说明未定义项，Nash返回完整性边界。输入Schema与示例共用校验，修复最小费用流的节点类型；协议只协商实际支持版本，表达式入口共用大小／运算边界及外部调用超时，补齐蒙特卡洛截止与所有当前表达式入口的独立覆盖回归。
  Mathematical tools now separate numerical candidates from exact refutations, preserve valid fits with explicit diagnostic states, and qualify Nash enumeration. Shared input validation aligns schemas and examples, flow node labels follow JSON semantics, and protocol negotiation advertises supported versions. External expression calls, including Monte Carlo propagation, run in bounded workers; coverage tests check every current expression consumer across MCP and CLI.

- 本地经验检索采用活动视图：重复记录复用身份，修订可显式替代旧条，退役保留原文但停止召回。外部建议保持候选证据，历史工作流的检索身份不回写；审查建议连接实际区分性检查与处理决定。
  Local lesson retrieval now excludes retired and superseded records without rewriting history. Duplicate additions reuse their identities, external proposals remain candidates, and frozen workflow retrievals stay unchanged. Important critiques lead to a bounded discriminating check and an evidence-based decision.

- 新增可选案例协调入口：初次运行前检索本地经验，以同一接续记录连接预算、最新证据、明确质量判断和报告。失败不覆盖已接受指针，过期证据阻断交付；可交付与值得继续分别判断。
  An optional case coordinator connects local lesson retrieval, bounded execution, current evidence, reviews and reports in one resumable record. Accepted identities survive failed candidates, while stale evidence blocks delivery. A complete draft and a decision to stop are tracked separately.

- 新增可选本地运行反馈：实际来源与阶段事件、未知身份和缺日志、失败与停止状态保持可见；显式文件清单、分享副本、双重哈希及目录／ZIP共层检查。拒绝越界、符号链接、异常压缩、非有限元数据及早于开始的结束时间；不自动上传，不以反馈包代替研究验收。
  Optional run feedback now records sourced metadata, actual events and stopping states, with explicit file selection and separate original/share hashes. The same read-only checks handle folders and ZIPs; unsafe paths, malformed archives, non-finite metadata and inconsistent end times are rejected. Export does not upload files or certify a study.

- 概率与干预解释增加针对性核验：准确率不代替个体概率，重采样区间明确估计对象，预测覆盖检查关键群体；双重差分检查真实对照与变量可区分性，平衡图不替代识别。
  Targeted statistical guidance separates classification accuracy from event probabilities, checks the target of resampling intervals and subgroup coverage, and verifies that treatment and time can be distinguished before a difference-in-differences interpretation.

- 返工与回收建模明确保留持久质量及检测信息，核对完整履约计费、失败终止与可用反馈，避免将拆解旧件反复当作新件抽样。这是带条件的方法改进，不新增必选算法或宣称通用最优。
  Repair and reuse guidance now distinguishes persistent faults from fresh draws and preserves valid inspection information. Fulfillment costs and termination must be checked before comparing recovery policies; the guidance does not prescribe a universal optimum.

- 收费站研究审计在存在多条分流路线时使用与被审计模型相同的策略及有限占用输入，消除不等条件比较造成的假差异；原数值、论文与历史审计回执保留。
  Toll-study audits now match the model’s routing policy and storage inputs. A multiroute regression catches the former comparison mismatch; frozen outputs and historical audit evidence are preserved.

- 修复独立审查发现的数值边界：GM(1,1)近零发展系数使用稳定差分；常量序列的后验比值不再伪造。猜想检查拒绝空采样与非有限结果，蒙特卡洛严格核对样本数，简单图工具拒绝静默覆盖重复边，CVaR保留失败状态。
  Numerical edge cases now fail explicitly: undefined conjecture evaluations, mismatched simulation outputs and duplicate graph edges. Grey-model response differences remain stable near zero, and infeasible portfolio solves retain their solver status.

- 正式论文同时固定 Tectonic 0.17.0 与完整 TeX 资源包，拒绝静默更换编译器；冻结校验同次构建记录、源码和 PDF 哈希。国赛、浴缸与收费站成品同步重排，数值模型不重算；跨系统检查涵盖六份文档并比较逐页文字及渲染。
  Canonical paper builds pin both the compiler and the full TeX bundle. Layout-gated snapshots require a matching build receipt; CI compares six documents across Windows, Linux and macOS.

- 中文论文迁移至固定的 Fandol 0.3 开放字体，移除系统字体依赖；国赛正文与 AI 使用详情同步，新增三系统干净环境编译检查及字体哈希验证。标准中文 CID 字体的提取改用正确映射，避免乱码导致匿名和结构检查漏检。
  Chinese reports now use pinned Fandol fonts from the TeX distribution. The paper and disclosure share the same font choices, with clean-runner compilation checks for Windows, Linux and macOS. Standard CJK CID mappings are handled correctly during intake and PDF inspection.

- 科研绘图不再默认步长抽稀长序列，避免漏掉窄峰；检查全部点的非有限值，明确点数上限超出时拒绝静默删点。图形按论证需要选择，不把配图或子标题设为模板必填项。

- 美赛报告共用单一版式源与摘要页生成器；新增模板漂移检查，收费站终稿与浴缸旗舰统一排版，数学内容不变。冻结入口增加版式门禁与源文件哈希；组件是否选用独立于样式约束，目录两级统一引线。国赛2026正文上限修正为30页（摘要与附录不计）。

- 修复 ODE 容差比较的物理时间对齐，以及反例缩减的最终浮点停滞、异常误判和预算耗尽语义；评审视图保留逐评委证据关联，奖项标签按具体赛事届次校验。同秒运行改按收据时间排序，最新失败不被旧成功掩盖。
  ODE tolerance checks now compare solutions at matching physical times. Counterexample shrinking makes strict floating-point progress and distinguishes evaluation failures from counterexamples. Review evidence stays linked to its reviewer and edition-specific award labels are checked. Timestamp ordering prevents an older success from hiding a later failed run.
- 自主研究沿原任务与证据链推进，运行中的进度与计算定义分开保存。新增收费站汇合研究归档，包含完整英文原稿／修订稿、兼容流量证书、有限占用反例、失败候选与复现入口；它是一次开发研究，不计作隔离盲测或奖项校准。
  The autonomous loop builds on the existing task and evidence workflow, keeping operational progress separate from computational definitions. A new toll-plaza research archive includes complete draft and revised English reports, flow certificates, finite-occupancy counterexamples, a rejected candidate and reproducible checks. It is a development study, not a blind evaluation or award calibration.
- 美赛浴缸案例的摘要、策略和人工操作误差叙述由同一份参考结果生成；误差百分比明确绑定所测试的0.1°C余量方案，不扩展到其他策略。复用既有优化记录，更新论文与预览。
  Key bath-study prose now derives from the archived results. The manual-error percentage is explicitly tied to the tested 0.1°C-buffer policy; existing optimization records are reused and the PDF and previews are refreshed.

- 两份案例按全文审阅修订，复用原优化结果：国赛纠正风险误差方向与缓冲条件；美赛补有限储热／替代流路对照、半秒恒流连续包络及具体六段流量，修订后的PDF、预览、双语页数与证据同步。论文修订指导明确局部修复后的全文一致性检查与按影响复用证据。
  Both case studies now incorporate full-report review while retaining their original optimization runs. Portfolio risk statements are conditional; the bath case adds fixed-policy structural replay, an unrelaxed constant-flow envelope and explicit schedule rates. PDFs, previews and case metadata are synchronized. Revision guidance requires a final consistency pass and reruns only affected calculations.

- 发布检查在独立临时副本运行两个提交包，允许重复检查且保留已有复现结果；失败时输出诊断。
  Release checks run the submission packages in temporary copies, preserve existing reproduction output, and show failure diagnostics.

- 参考固定版本openai/math的工件组织与辅助结果说明，在原证据主线补上证明陈述、前提和覆盖范围检查；辅助引理不能冒充主结论，不新增Lean依赖或强制形式化步骤。
  Proof review now checks statement alignment, assumptions and coverage, informed by a pinned openai/math snapshot. Supporting results cannot stand in for a main claim; no Lean dependency or mandatory formalization stage is added.

- 语言修改锁定事实、条件与结论强度，中英文分别写作；对话技能将日常质疑交给模型检查，持续协作可追加来源可追溯的本地贡献事件，贡献日志与数值快照分离。
  Language edits preserve facts and claim strength while addressing each language on its own terms. Dialogue connects objections to checks; local contribution events retain provenance without invalidating numerical runs merely because a note was appended.
- 赛事评审默认使用奖项导向视图，缺少届次／版本／检查范围时暂不判断；保留内部诊断与旧评审。新增按赛事—赛项—届次查询的覆盖档案，规则、完整流程及奖项校准分别标记，不从旧届次继承合规结论。
  Contest reviews now lead with scoped award estimates and actionable gaps, or abstain when evidence is insufficient. Internal diagnostics remain available. An edition-specific registry separates rule coverage, workflow validation and award calibration without treating candidate contests as supported.

- 明确公开源码与插件交付边界，保留测试/CI等维护文件，忽略本地笔记与构建产物，增加导出排除回归及贡献说明。
  Contribution guidance separates maintained source, local work and installable packages. Export checks keep private and development-only files out of distributions.

- 增加 Codex、Claude Code、Gemini CLI、Copilot CLI 与 Cursor 的宿主导出目标，适配各自清单和 MCP 路径；首页按插件安装组织，提供中英文完整指南。各包共用七技能与核心工具，部分宿主的可选 arXiv 存储需另配。
  Host-targeted exports now cover Codex, Claude Code, Gemini CLI, Copilot CLI and Cursor. Bilingual setup guides explain native installation while keeping the skills and mathematical engine shared.

- 插件导出增加由统一元数据生成的 Codex 原生入口与 MCP 兼容配置，所有入口纳入哈希收据；保留可移植包与七个技能。
  The portable bundle now also exports native Codex entry points from the same metadata, with manifest hashes recorded in the build receipt.
- 合成题评分升级为 planted-v2：排队答案独立计算，LP 核验向量且接受多重最优解，结构标签使用有限族解析条件，SIR 最终规模考虑初始感染；拒绝非法数值与字段类型，订货量改用绝对误差。明确工具回归与真实 Agent 对照的区别。
  Synthetic regression scoring now verifies LP certificates, uses independent queue and analytic structure references, and accounts for finite initial infections. Typed finite answers and absolute inventory tolerances tighten acceptance; oracle contracts distinguish tool checks from Agent comparisons.

- 补强模型比较与计算契约：按推广对象划分数据、跨折汇总选型并重训完整处理链，区分递推预测、平滑、聚类编号与概率；增加指标和逆变换的独立反例演示，以及插值、信号和隐状态方法的条件说明。没有增加工具、依赖或固定步骤。
  Model guidance now follows the intended use of a prediction through data splitting, cross-validation, refitting and output interpretation. A runnable set of counterexamples exposes misleading metrics, unavailable future information and transformation errors; task-specific notes cover interpolation, signals and hidden states without adding tools or mandatory stages.

- 修复插件导出后的双向技能与参考链接；整包链接检查覆盖核心、专项与案例，导出 MCP 实测握手、独立答案与失败恢复。规则按职责归并，完整研究、多人评审与网格检查按实际缺口启用。
  Plugin exports now relocate links across the entire package. Checks cover core and focused skills, references, an MCP handshake, a known-answer computation and recovery after a failed call. Shared guidance is consolidated by responsibility and applied to the task's actual scope.
- 评审 schema v2 区分不适用、尚未核验和反例，关键主张与诊断分并列；保留旧记录兼容，不改赛事权重或设奖项分数线。
  Review schema v2 distinguishes inapplicable checks, missing verification and refuted claims. Claim validity is reported alongside diagnostics; legacy inputs remain supported without changing contest weights or inventing award thresholds.
- 美赛案例拒绝最细网格越界的 19.35 L 候选，改用通过独立三网格连续包络的六段 21.48 L 方案；论文、复现验收与双语展示同步，并保留失败证据。
  The MCM case rejects the 19.35 L candidate that violates the finest-grid spread limit. The selected six-stage policy uses 21.48 L and passes independent continuous-time bounds on three meshes; the paper, reproduction checks and bilingual presentation retain the failed candidate explicitly.

- 明确教程与算法包的最小核验：确认实际算法、指标方向、候选边界、预测参数及留出指标；组合方法与单一基线比较。写作指南不再以引文数量衡量依据，摘要证据可标为临时情景输入；经验模板与官方要求区分。评分可给出未校准的奖项范围，并将 COMAP 通用评审指引与自定量表区分。
  Tutorial code is checked for its actual algorithm, criterion direction, feasibility, fitted parameters and held-out metrics. Combined methods must earn their extra complexity against a single-method baseline. Citation counts are not quality targets; abstract-only evidence may support explicitly provisional scenarios. Award estimates remain uncalibrated, and COMAP guidance is distinguished from the project’s numerical rubric.

- 两个完整案例为图表补入正文解释和自动交叉引用；美赛使用者说明保持独立单页，论文共 24 页（23 页解答加 1 页 AI 报告）；国赛支撑包排除 LaTeX 编译中间文件。修复图表引用检查误判段首引用的问题，并加入成稿回归检查。
  Both cases now connect figures and tables to their arguments through automatic references. The MCM user guide stays on one page; the report has 24 pages (23 solution pages plus the AI report). The CUMCM archive excludes TeX intermediates. Float checks accept paragraph-initial references, with regressions against the final documents.

- 评委评分表改为条目核对为主：每个维度由可对照的条目换算，印象只能在 ±1 内微调且须写理由，并标明分数来自复算还是判断；新增限时阅读评委模式和注入错误的校准；`evals/aggregate.py` 接受条目清单。
  The judging sheet now works from checkable items per dimension, with at most a documented ±1 adjustment and a record of whether a score is computed or judged; a time-boxed reading-judge mode and error-injection calibration are added; `evals/aggregate.py` accepts checklists.
- 修复（外部复核发现）：教训检索支持中文查询（字二元组与中文标签，种子教训补了中文标签，并把尚未在另一道题上验证过的两条降为“观察到一次”）；任何嵌套的乘方都被拒绝；相对路径一律相对工作区；国赛附录标题检测排除带句读的行。
  Fixes from an external review: lesson search works for Chinese queries (character bigrams and Chinese tags; two seed lessons not yet checked on another problem are downgraded); any nested power is rejected; relative paths always mean the workspace; appendix detection ignores lines with sentence punctuation.
- 证据索引新增可选的 `claims`：每条结论声明强度（computed／checked／independent），报告没有结论支撑的问题要求和强度超过证据的结论；路线记录里细化另一条路线时必须写明“简单一层解释不了什么”；教训新增失败做法、发现方式和信号三个字段，附带 5 条种子教训（`templates/lessons-seed.jsonl`），`route_graph` 启动新记录时用 `lessons_path` 返回相关教训。
  The evidence index accepts optional `claims` with a declared strength and reports uncovered requirements and overclaims; a refining route must say what the simpler route cannot explain; lessons gain failure-pattern, detection and signal fields with five seed lessons, returned by `route_graph` when a new record starts.
- 修复：环境快照覆盖全部声明的依赖；相对案例路径先按工作区解析；国赛附录标题检测不再被正文行误触发；表达式中失控的乘方被拒绝；工具说明写明 `proved`。
  Fixes: the environment snapshot covers every declared dependency; relative case paths resolve against the workspace; appendix detection ignores body lines; runaway powers are rejected; `proved` is explained in the tool descriptions.
- 案例展示图去掉“多少页报告”的链接行，两个案例的页脚统一；三个案例页的结尾邀请语统一；新增中文与英文论文各自的写作习惯和语言评审角色。
  Case overview images lose the page-count link line and share one footer; the three case pages close with the same invitation; Chinese and English writing habits and a language reviewer role are added.
- 版式：没有官方要求时按数学期刊连续排版，只有摘要页和不计页的 AI 使用报告另起一页；浮动体页顶端对齐。美赛案例据此重排，共 23 页（正文 22 页加 AI 使用报告）。
  Layout: continuous journal-style flow unless the contest requires otherwise; only the summary sheet and the uncounted AI report start new pages; float pages align to the top. The MCM case was reflowed to 23 pages.
- 新增 `scripts/contest_rules.py`：按美赛（COMAP 2026）与国赛（格式规范 2019/2021/2023）的硬性规则检查 PDF；两个论文模板按各自规则收紧并有测试；美赛 AI 使用报告标题与官方一致；国赛案例的代码页与参考文献不再侵入 2.5 厘米页边距。
  `scripts/contest_rules.py` checks a PDF against the published hard rules of MCM/ICM and CUMCM; both paper templates follow their rules and are tested; the MCM case's AI report carries the official title and the CUMCM case keeps its code and references out of the 2.5 cm margin.

（发布前把这一节改成新版本号。版本号只增不改：已发布的版本不再修改，修复发下一个小版本。小改动只提交，不发版；新增或改名技能与工具、结果格式变化才升次版本号。）

## 0.3.0 · 2026-10-08

由三次封存模拟比赛和两轮盲比较驱动：补齐工具覆盖，加入覆盖地图、评审协议与“先做透再收敛”的工作方式。
Driven by three sealed simulated contests and two blind comparisons: wider tool coverage, a coverage map, a review protocol, and a deep-work-then-converge way of working.

- `ols_report`、`compare_models`（回归诊断与对基线的交叉验证比较）；`check_pdf --margins`（渲染后检查每页左右空白与溢出，新增依赖 pypdfium2）。
  `ols_report` and `compare_models` for regression diagnostics and baseline-honest comparison; `check_pdf --margins` renders pages and flags uneven margins and overflow (new dependency pypdfium2).
- 第一次封存模拟比赛暴露的缺口：分层热传导 `solve_layered_diffusion` 与独立的拉普拉斯解 `layered_diffusion_laplace`、参数标定 `calibrate_curve`（可辨识性与留出点）、`sobol_convergence`、路线记录落盘 `graph_file`、工具索引（自动生成）、图的负值条形与标签转义、`check_pdf --margins` 增加大块空白检测；MCP 服务按需加载重的库，启动更快。
  Gaps found by the first sealed simulation: layered conduction with an independent Laplace solution, parameter calibration with identifiability and hold-out, Sobol convergence, persistent route records, a generated tool index, signed bars and label escaping in figures, white-gap detection in `check_pdf --margins`, and lazy imports that speed up the tool server.
- 第二、三次模拟比赛暴露的缺口：`bimatrix_nash`（非零和博弈全部纳什均衡）、LP/MILP 接受稀疏矩阵、`mcp_server --list --filter`、案例运行只打印摘要；序贯决策（信息结构、松弛上界与遍历证书、规则变体表）、Word 附件、并行预算等指南。
  Gaps from the second and third simulations: Nash equilibria of bimatrix games, sparse LP/MILP input, a tool filter, a compact `run` summary; guidance on sequential decisions, Word attachments and parallel budgets.

## 0.2.0 · 2026-10-08

在 0.1.0 之上，让 Praxis 能面对陌生问题：先找结构、比较路线、没有答案时也能产出带把握等级的结论。
On top of 0.1.0, Praxis can now face an unfamiliar problem: find the structure first, compare routes, and produce conclusions labelled by confidence even when there is no answer key.

- 新技能 `praxis-explore`（结构发现、路径搜索、实验数学、经验沉淀）与 `praxis-dialogue`（向不懂数学的用户讲清模型、结果出来后共同复盘）；新参考：结构发现、路径搜索、研究模式、学习回路、科研基础（不确定性、数值收敛、统计检验）、竞赛题型与丢分点、领域机制速查。
  New skills `praxis-explore` and `praxis-dialogue`, and new references on structure discovery, route search, research mode, the learning loop, scientific foundations, contest playbook and domain mechanisms.
- 新工具共 20 余个：结构探测（凸、单调、对称、幂律、守恒量、量纲分析、全单模）、路线记录 `route_graph`、实验数学（反例搜索、猜想检验、递推猜测与有限核对证明、整数关系）、经验记忆、一维热扩散（附收敛阶与网格收敛指数）、马尔可夫链、矩阵博弈、库存、CVaR 组合、Pareto 前沿、平衡点稳定性、卡尔曼滤波；线性规划支持 ≥ 约束与影子价格；每个工具带可运行示例，字段缺失时报错会列出必填字段。
  More than twenty new tools: structure probes, the route record, experimental mathematics, lesson memory, finite-volume diffusion with convergence indices, Markov chains, games, inventory, CVaR portfolios, Pareto fronts, equilibria and Kalman filtering; LP gains >= rows and shadow prices; every tool carries a runnable example.
- 证据分七层并要求写证伪陈述；`evals.planted` 提供九类已知答案的合成题与盲测规程；新增研究模式案例（3×2n 多米诺铺法数）。
  Evidence has seven layers with a falsification statement; `evals.planted` offers nine kinds of known-answer problems with a blind-evaluation protocol; a research-mode case (domino tilings) is added.
- 国赛案例补三张图并按独立审计修正；美赛案例按独立审计重算：被约束的温度改为在入口射流区之外施加并在三套网格上收敛，分段方案 19.35 L，论文 24 页。
  Both cases were corrected after independent audits; the MCM case was recomputed with mesh-converged constraints (schedule 19.35 L, 24-page paper).
- 修复：`sir_fit` 给出终态规模并说明假设；`mcp_server` 版本号取自 `pyproject.toml`。
  Fixes: `sir_fit` reports the final size and its assumptions; the server reads its version from `pyproject.toml`.

## 0.1.0 · 2026-10-07

首个公开版本 · First public release

- 六个技能：整题入口 `praxis`，以及 `praxis-model`、`praxis-compute`、`praxis-verify`、`praxis-dialogue`、`praxis-report`；按 Agent Plugins 1.0 导出，附 `praxis-tools` 数学工具服务。
  Six skills (the whole-problem entry plus five focused ones) exported as an Agent Plugins 1.0 plugin, with the `praxis-tools` math tool server.
- 两个完整案例：1998 年国赛 A 题（17 页中文论文与支撑材料）和 2016 年美赛 A 题（23 页英文论文），均用 XeLaTeX 与 pgfplots 排版，附复现代码与验收记录。
  Two complete cases: 1998 CUMCM A (17-page Chinese paper plus supporting archive) and 2016 MCM A (23-page English paper), typeset with XeLaTeX and pgfplots, with reproduction code and acceptance records.
- 方法库覆盖优化、微分方程、排队、敏感性、预测与学习类方法，每种附适用条件与必做检查；图表规范与 LaTeX 论文模板（`templates/`）。
  A model library covering optimization, differential equations, queueing, sensitivity, forecasting and learning methods, each with conditions and required checks; figure guidelines and LaTeX paper templates.
- 持续集成：每次推送自动运行测试。
  Continuous integration runs the tests on every push.
- 新增 12 个工具（共 62 个）：`minimize_nlp`、`knapsack`、`min_cost_flow`、`robust_lp`、`solve_mdp`、`hypothesis_test`、`bootstrap_ci`、`monte_carlo`、`solve_ode`、`arima_forecast`、`pca_report`、`cluster_report`，均有已知答案或暴力枚举的测试；新增能力覆盖地图（哪类结构有现成路线、没有时怎么办）、论文评审协议（独立评审角色与反方）、赛前规则清单。
  Twelve new tools (62 in all) with known-answer or brute-force tests; a capability coverage map, a paper review protocol with independent reviewer roles, and a pre-contest rule checklist.
- 新增《深度工作与竞赛收敛》：开始时确认交付目标，先按科研标准做透并设停止规则，再用收敛账本把证据池分流到正文、附录、池或删除；写明评委阅读方式与收敛检查。
  New guide on deep work and contest convergence: declare the delivery target first, work to research standard with a stopping rule, then route the evidence pool into main text, appendix, pool or deletion with a convergence ledger.
