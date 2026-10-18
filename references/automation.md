# 自动执行与证据契约

执行计算时，解析技能真实位置为 BUNDLE，当前用户工作项目为 WORKSPACE。宿主能力未知或调用失败时按 [agent-compatibility.md](agent-compatibility.md) 核对；能力缺失只做可完成的分析，不能编造运行。环境未准备时执行 `uv sync --project "$BUNDLE" --locked`；需要开发测试时增加 `--group dev`。通过 `uv run --locked --project "$BUNDLE" python "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE"` 调用，不依赖虚拟环境的系统目录结构，也不依赖技能安装目录作为当前工作目录。下列命令的 BUNDLE 与 WORKSPACE 均应替换为实际绝对路径；Windows PowerShell 示例见[安装指南](installation.md#windows-powershell)。已有准备好的 POSIX 环境仍可直接使用其 `.venv/bin/python`，不要解析符号链接后改用基础解释器。

外部材料访问与披露按 [integrity.md](integrity.md)；运行前检查模型和验证器代码。普通 Python 以宿主账户权限执行，参数校验与超时的真实隔离范围见 [SECURITY.md](../SECURITY.md)。

工具名称与 Python 模块／函数名不保证相同。先用 `python -m scripts.mcp_server --describe 工具名` 核实际输入，再通过 MCP 或 `--call` 调用；需要直接 Python 时读实际注册适配与锁定库接口，不按类别猜 import。一次属性不存在可能只是定位错误，不能据此宣布能力缺失并重写已存在算法。先核已有实现与第一手 API 的条件，确有缺口才形成新的计算实现。

环境故障先用 `runtime_info` 核当前进程的解释器、实际资源位置、依赖和导出收据；无工具服务时可直接运行 `python /实际包目录/skills/praxis/scripts/runtime_info.py`。CLI 使用标准库，未加载工具注册表时明确报告未知；MCP 调用传入该服务的真实注册名称。诊断不联网、不装依赖、不读取用户案例、不执行模型或编译器。磁盘文件匹配不证明在运行的旧进程已重载；找到 Tectonic 路径不代表其版本、资源或论文已验证，仍要真实调用及成品门禁。

## 先判断要不要走案例系统

案例脚本（`init`、`run`、`status`、`evidence`）适合要保留运行快照与机器证据索引的任务。已有可复现执行链时可以沿用：报告数字能回指脚本与输出文件，检查有名字、结果与证据，最终材料有版本／哈希清单。选择不使用案例系统不等于放弃追溯，也不能声称具有 pipeline 的自动过期检测。需要 `check_pdf.py --checks` 核对检查数时，将真实检查保存成下文契约的 checks.json。

## 接收 Word 和 Excel 附件

`init` 直接接收 PDF、文本、Markdown 与 Excel。题面或附件是 .docx 时：先用 python-docx 读文字与表格；如果文中公式、地图、示意图是对象（MathType、VML 绘图组、嵌入图片），文本抽取会缺内容，要把 .docx 转成 PDF（LibreOffice 的 `soffice --headless --convert-to pdf`）后渲染查看，必要时解压 .docx 读 `word/document.xml` 与 `word/media/`。公式对象数量与抽取到的公式数不符时，逐个核对，不要凭印象补。从图中提取的结构（地图相邻关系、表格）要写明是怎样提取的，并至少抽样人工核对。

## 并行计算的预算

同时开多个进程前先估计核数与内存：并行任务的总数不超过核数的一半，长任务先在小样本上计时。机器过载会使每项慢数倍，得不偿失。

## 建立案例

```bash
uv run --locked --project "$BUNDLE" python "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" init \
  --name training-example --problem /绝对路径/problem.pdf \
  --data /绝对路径/data.csv --phase preparation
```

题目原文可先保存为本项目文件再传入；CLI 支持 PDF、TXT、Markdown。多个数据文件重复 `--data`。默认建在 `cases/<name>/`；名称自行根据任务取，不必为取名问用户。`init` 默认创建 `case.json.schema: 2`，显式 `--schema 1` 保留旧契约；缺 schema 的历史案例按1解释，接续不改原件。已有目录拒绝覆盖，接续时读取 `case.json` 与 `planning/tasks.md`。`--phase contest` 只记录比赛阶段，不能据此判断比赛时限或取得提交授权。

案例保存：`raw/` 原件只读副本、`planning/` 题意与任务记录、`audits/` 数据质量报告、`code/` 可复现处理与模型、`runs/` 每次独立运行结果。副本保留来源路径、哈希和字节数。CSV 使用显式编码（默认 UTF-8；可 `--encoding gb18030`），Excel 逐表检查；其他格式或大于 50 MB 的数据明确标记延后审计，选择流式或针对性处理。延后审计不等于已核验可用。PDF 即使提取到文字仍须查看原页。 插件自己的 JSON、Markdown、TOML 元数据与中文记录用 UTF-8 显式读写；CSV 的编码仍按数据契约指定，原始模型子进程日志保留原始字节，不由系统代码页转换。

## 内容理解不是脚本替代的

题意、路线、假设和推进条件统一按 [methods.md](methods.md) 写入对应任务记录。脚本不自动理解题目、选择模型或确认检查的独立性；本文件只规定如何接收、执行与追溯已经明确的工作。

## 模型与验证器

schema 2 先由 model 产出 `planning/model-contract.json`，每次 run 前用 `modeling.schema_contracts.check_model_contract(contract) -> list[str]` 检查；非空问题列表拒绝启动模型。`MODEL_CONTRACT_V2` 为对应结构schema，任务产出与人工复算见 [modeling-gate.md](modeling-gate.md)。字段接口：

| 字段 | 结构与机器约束 |
|---|---|
| `symbols` | `[{symbol,unit,object,uses:[{equation,object}],same_object_justification?}]`；用法非空，描述字段必填；对象描述不同且未说明理由只告警，供独立审查定位，不代表语义已核。真正比较对象身份需另设短标识。 |
| `parameters` | `[{symbol,value,unit,source_level,source,real_world_quantity,reference_magnitude?,magnitude_justification?}]`；来源级别 measured/literature/fitted/declared/unknown；`value:null` 只能配 `unknown`，记告警不拒绝，并跳过量级检查。其余真实量必有 `{value,unit,source,ratio_ok?}` 参照，单位一致且参照非零；默认比值 `[0.1,10]`，越界或把 `ratio_ok` 放宽到默认之外都须写 `magnitude_justification`，下界须大于0。参数和 effect_variable 必须是已声明符号，符号比较时忽略空格、花括号和反斜杠。检查器一次返回全部问题。 |
| `mechanisms` | `[{id,cause,effect_variable,sign,equation}]`，sign 为 `+/-/±`。 |
| `conserved_quantities` | `[{name,check_name:"balance:<name>"}]`；验证阶段须实际产生同名通过检查。 |
| `probability_combinations` | `[{expression,independence,justification}]`，independence 为 assumed/derived/not_assumed；assumed 理由非空。 |
| `logical_claims` | `[{claim,type,proof_ref}]`，type 为 sufficient/necessary/both。 |
| `limiting_cases` | `[{case,expected}]`。 |
| `cheapest_refutation` | `{method,result}`，method 为 hand_calc/small_example/unit_check。 |
| `information_time`、`spatial` | 非空信息时点文本、布尔值。 |

这些是作者声明的一致性门；实际方程是否列齐、量纲与物理解释是否正确，仍核代码、原题和独立答案。超过七成参数 `source_level:declared` 在收据 `model_contract_warnings` 告警，不拒绝；比值范围和七成均是本版实验参数，保留其适用范围。

助手写并检查案例 `code/model.py` 与 `code/validate.py`；两者使用 argparse 接收以下接口：

```text
model.py --output <本次运行的输出目录>
validate.py --results <输出目录/results.json> --output <本次运行/checks.json>
```

- 模型在 `--output` 下生成非空对象 `results.json`，另可生成 CSV、图片和参数记录。结果需包含真实指标与适用范围；数据来自案例原始副本，处理参数保存于案例代码／配置中。
- 验证器生成非空 JSON 列表。schema 1 每条为 `{"name":"检查名称","passed":true/false,"evidence":"具体计算或对照结果"}`；schema 2 另必填 `method`，取 analytic/enumeration/bound/conservation/hand_calc/naive_baseline/replay/external_value。独立方法另标 `independent:true`，并给实际计算／比较证据；运行成功检查单独标自身范围。失败写入并退出非零。
- 预测：和朴素基线比较，选择正确的数据分割；多步预测还要核对目标集合，开发／调参目标不得跨入最终留出集，仅检查训练前缀并不充分；优化：检查约束、整数性与基准；连续模型：解析解、守恒、边界或步长；评价与敏感性：使用适合实际问题的检查。随机种子固定，避免只报告最佳一次运行。
- 可以导入技能包 `modeling/` 与 `scripts/`。运行器把技能包路径加入 PYTHONPATH。不要把模型生成的其他文件放进原始数据区，或用脚本联网调用不相关外部服务。

昂贵运行前用最小输入走一遍真实的固定参数列表和消费入口，不能只做语法检查或让生产者自报self-check成功。检查实际文件名、参数路径、`results.json`非空对象及上述非空检查列表；`name`须为非空字符串，`passed`须为原生JSON布尔，`evidence`须为非空字符串，成功收据还要求每项为true。小例也覆盖有缺失值的整数日历列：CSV中的整数年份不能因空值升成`2012.0`后再交给要求整数文本的消费者，缺年仍保留真实时间间隔。沿用已有执行器、schema与独立验证路径，不为预检另写一套宽松解析器；记录预检实际预算和结果，不能把小例通过冒称完整模型已验。

独立检查器内部可保留结构化诊断；若外部`evidence`字段要求字符串，在最终写出边界按稳定键序和明确编码序列化为JSON字符串，内部增补证据完成前不要提前转字符串。接口错误与数学失败分别记录，但即使数学检查成立，不合格执行收据仍是失败；保留原失败，修接口后另产真实验证收据，不回填旧成功或重建案例清零预算。

## 按信息截点映射版本

`asof_join` 接收 `queries`、`versions`、键 `on`、查询时间列 `decision_time` 和版本可用时间列 `available_time`。最多 20000 查询、200000 版本，每张表列名一致且值为有限 JSON；键类型一致且非空。时间为带 Z 或 ±HH:MM 时区的 ISO8601，时间数字使用 ASCII、最多九位小数；拒绝仅日期、无时区及范围外值。返回 `schema_version: 1` 与原顺序的索引映射，不复制 payload、不改原件。

```python
from modeling.data_analysis import asof_join
queries = [{"id": "A", "cutoff": "2026-01-02T08:00:00Z"}]
versions = [
    {"id": "A", "released": "2026-01-02T07:50:00Z", "value": 12},
    {"id": "A", "released": "2026-01-03T12:00:00Z", "value": 19},
]
mapping = asof_join(queries, versions, "id", "cutoff", "released")
# matched_version_index 为 0，不能选翌日才公布的 19。
```

默认严格早于截点；确知同刻可用时显式 `allow_exact_matches=True`。未发布、同键缺可用时点或最新可用时刻冲突分别返回 `not_available`、`unknown_availability`、`ambiguous_latest`，索引为 null。计数覆盖全查询，空查询的匹配比例为 null。它不能认证账本真实／完整、因果或部署性能；科学含义归 [data-analysis.md](data-analysis.md#按决策时刻选择数据版本)，原记录 payload 由调用者按有效索引取值，未决项显式处理。

## 数学工具的结果契约

- `probe_structure` 的违例是浮点或有限差分候选，始终 `proved: false`。`test_conjecture` 的 `holds`／`numerical_holds` 描述采样计算；普遍命题状态另读 `claim_status`，候选核验另读 `verification`。只有支持的有理算术在箱内一个精确点严格违例，才给 `exact_rational_witness` 和 `claim_status: refuted`；候选被精确核验否定或含未支持函数时仍未决。mpmath高精度本身不升级证据。`find_counterexample` 只有忠实精确的整数谓词才保留有限域证明；浮点常量、实变量、真正除法及未认证的负／变量幂不因穷举而成为严格保证。精确组合判据、条件性递推证明等原保证继续按自身前提使用。
- 拟合／回归保留有限的参数、拟合误差及真实收敛状态。未定义、无穷、不适用和不可识别的诊断以 `null` 加对应状态与原因表达；秩亏拟合的一组系数不代表唯一识别，局部区间不得抹去秩亏或失败。严格JSON继续拒绝NaN／Infinity，不对所有结果自动清洗。
- LP 的 `certified` 与 MILP 的 `proved_optimal` 是数值门禁结果，不是精确数学证明。LP 检查缩放后的原始可行性、对偶可行性与差距；MILP 另核实际整数性和求解器界／差距。先读 `success` 再读对应认证字段，不可把求解器返回成功或限时可行解当成认证最优。极端尺度可能被拒绝；影子价格按原问题单位返回；无法表示为有限浮点值时为 null，`diagnostics.rhs_shadow_prices` 保存 `not_representable`。严格结论需要独立界或精确答案。
- `knapsack` 对提供的整数与二进制浮点值做精确有理运算，`value_exact` 保存最优总值；它不追认未提供的理想十进制值。权重、数量和容量为非负整数，容量最多1000000，动态规划最多5000000表格单元。微小正收益不因数值容差被丢弃。
- `solve_mdp` 的有限期分支对整数及实际二进制浮点值做精确有理 DP，`value_exact` 保存值，浮点 `value` 可有显示舍入。通过随机矩阵前提后，转移行按实际行和精确归一，`transition_rows_normalized` 记录是否发生改变；保证只归这个明确的模型。最多2000000次非零转移／奖励运算，值的有理数位数最多32768。折现无穷期仍用数值迭代，误差界从返回值的精确 Bellman 残差计算；`error_bound_exact` 保留精确界，浮点界向上取整，不可表示时为 null 加原因。这不认证状态、奖励或信息结构符合现实。
- `matrix_game` 保留原收益的整数／二进制身份，以精确差值居中缩放，再求数值 LP 策略并核原单位 exploitability。`value_exact` 是策略下界和上界中点的精确有理账目，不普遍等于精确均衡值；读 `certificate_scope` 的数值容差。`has_saddle` 比较原收益的纯策略极小极大；吸收链指定状态必须是真正无出边的自吸收行，极小正转移也不能当作零。
- `hypothesis_test` 的未定义检验保留本检验字段名，以 null 和原因记录；t 检验用 `p`，相关检验用 `pearson_p`／`spearman_p`，`significant` 同为 null；配对样本必须长度一致。`bootstrap_ci` 的退化 BCa 区间以 `ci: null` 保留状态，估计值或标准误不能代替有效区间。检验、区间及折间误差的解释仍依实际抽样设计。
- `bimatrix_nash.count` 只数返回候选。`completeness` 明确浮点等支撑枚举未认证完整性；退化连续均衡族和奇异支撑可能遗漏，不把有限列表当全部均衡。策略建议另核最优反应及适用条件。
- 输入由同一 `TOOLS` 注册描述和校验；校验器仅实现当前使用的JSON Schema 2020-12关键词子集，未知约束词拒绝。最小费用流边为异构四元组；JSON demand键为字符串，整数端点（包括数学整数 `1.0`）规范化为整数字符串，拒绝整数与相同文本字符串混用。
- MCP stdio 每帧至多8 MiB UTF-8字节（包括换行）；超限帧只排空、不解析、不执行工具。无效UTF-8、重复JSON键及解析深度溢出拒绝，下一帧仍可处理。CLI JSON参数同样拒绝重复键。注册表达式子进程最多保留4 MiB stdout与64 KiB stderr；超限终止并回收直接子进程、不接受结果。上述边界不限制工作进程的内存、CPU、子孙进程、文件或网络权限；普通数值工具及案例脚本另按实际预算和宿主隔离执行。
- MCP请求整体还核有限JSON值与Unicode标量，拒绝NaN／无穷和未配对代理字符（键和值均核）；合法中文和非BMP字符保留。外层MCP回复和JSON CLI用ASCII安全的JSON转义，解码后字符串不变，不依赖Windows stdout代码页。MCP CLI与Python表达式工作进程使用UTF-8文本协议；工作进程自己的PYTHONIOENCODING固定为UTF-8，覆盖继承的流编码而不改变其它环境。接受结果前再次核墙钟截止，父进程晚醒也不能接受超时输出。
- stdio当前声明支持 `2025-06-18`，未知请求版本协商回实际支持版本，客户端不兼容时可断开；依 [MCP版本协商规范](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle#version-negotiation) 处理，不因版本名新就声称支持。
- 受限表达式支持 `where(cond, a, b)`；比较（<、<=、>、>=、==、!=）只能作 where 的第一个参数且只含一个比较，拒绝裸比较、数值条件、链式比较、属性调用和嵌套幂。log、sqrt、exp、sin、cos、tan、除法和幂在每个求值点都必须得到有限实数，否则报错并指明运算；where 两分支都会求值，上述运算在未选分支中也必须有限。加、减、乘的溢出不在表达式里单独拦截，各工具会拒收非有限的最终输出。需要分段定义时先把参数换成安全值，如 `where(x>0, log(where(x>0, x, 1)), 0)`。LP ε 扫描在每个网格点先优化主目标，再在各目标都不变差的条件下改进其余目标；第二阶段经核验的点不是仅弱有效，未核验时保留第一阶段点并标 `weakly_efficient_possible: true`。NLP 不做第二阶段，所有点都这样标注。前沿合并目标值相同的点并列出全部产生它的 ε 行。有限网格不认证完整前沿，表达式 NLP 同受下述截止保护。
- 受限表达式共用字符4096、AST节点512／深度64、常量整数4096位及绝对指数200的上限；等价常量写法和运行时变量指数都核查，isprime参数至多64位。猜想采样至多100000点，表达式标定至多10000观测。MCP／CLI的注册表达式工具（包括 `monte_carlo`）在30秒子进程截止内运行，超时终止并回收、不接受结果；调用后可继续服务。截止覆盖回归从当前注册函数的编译器／求值器调用路径独立识别入口，逐项验证MCP与CLI，不只测试保护名单中的工具；新增外部求值器需同时核对这一有限路径检查。内部Python `call` 和任意用户回调不因此获得硬计时或内存隔离，单次运算守卫也不能替代进程截止。

兼容说明：这些更正保留工具名和正常计算结果，新增证据、诊断与完整性字段，部分原诊断数值在未定义时改为 `null`。调用方必须按状态解释，不能只读取旧 `proved` 或 `count`。历史收据保留原源码与原字段，不自动重标成新版认证；依赖此次更正的结论应另建核验记录。既有冻结案例按真实调用影响检查，不批量重算。

## 运行与接续

```bash
uv run --locked --project "$BUNDLE" python "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" run \
  --case "$WORKSPACE/cases/training-example" --timeout 120
uv run --locked --project "$BUNDLE" python "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" status \
  --case "$WORKSPACE/cases/training-example"
```

每次生成新的运行目录，包含两阶段 stdout/stderr、命令、时间、代码与输入哈希、案例源码／参数快照、实际 Python／包版本、检查、输出哈希与状态。案例 `source-snapshot` 总是保留。schema 2 仅当公开bundle为干净Git工作树时省略 `dependency-snapshot` 并写 `bundle_git_commit`；原 `dependencies` 哈希字典仍保留供过期检测。脏Git、非Git安装副本及schema 1继续保存实际依赖源码快照。运行顺序以收据 started_utc／ended_utc 为准，避免同秒目录随机后缀倒置；精确时间平局时失败／未完成优先阻断，旧收据缺时间兼容目录时间，坏时间戳拒绝取证。命令用固定 Python argv，不通过 shell 执行题目或数据里的命令。超时或失败记录保留，先查看根因再调整；不覆盖已跑出的结果。候选计算的协作式截止检查须覆盖开始前与接受前，保留超时状态，不因计算终于返回可行结果就接受；它不能中断正在运行的求解器。需要限制实际计算历时时，另用进程超时及求解器迭代／求值上限，不把接受截止当成硬实时执行保证。

`automatic-checks-passed` 只表示已记录的自动检查通过。`status` 可发现原始输入、代码、依赖或结果变化，标记过期证据；只用 `usable_automatic_evidence: true` 的结果准备论文，并继续评估现实机制与稳健性。检查本身是否有意义仍需 助手审核，不把脚本状态当成科学结论或用户已核验。`paper_ready` 默认 false，不自动授予论文完成状态。

`source_snapshot` 整体哈希 planning/tasks.md、requirements.json 与 code 下文件；schema 2另绑定 planning/model-contract.json 和 planning/problem-extracted.txt，契约或题面抽文本变更使旧运行过期。纯操作接续放 planning/progress.md，纯贡献放 contributions.jsonl；这些文件不是计算参数入口，不可用来隐藏实际输入变更。有效成果与候选的接受／恢复决定按 [methods.md](methods.md) 维护；这不是 `status` 自动择优的功能。候选失败不覆盖已接受文件，但当前证据是否可用仍以实际快照为准；最新运行失败时 `evidence` 不会偷偷返回旧成功。要恢复旧快照，明确记录恢复理由、核对输入／代码／环境，并重新执行当前状态要求的检查；不能只在任务表把旧结果改成“有效”。

自动化的边界：程序日志不是完整 AI 对话；哈希不是官方提交回执；本地只读不是不可篡改存证；输入副本不是备份策略。原始大数据与生成输出默认不纳入 Git，实际比赛须安排本地备份。

## 写作连接

### 竞赛模板与组件 API

以下模块命令在 **BUNDLE目录** 的锁定环境执行，所有论文／输出路径使用工作项目的绝对路径。`paper_template --contest` 实际支持 mcm/cumcm/research；研究生赛按原官方封面及匿名稿选择真实工具链，再用下方 graduate 提交检查，记录实际支持范围。

```bash
uv run --locked python -m scripts.paper_template "$WORKSPACE/paper/paper.tex" \
  --contest mcm --review-structure
uv run --locked python -m scripts.paper_template "$WORKSPACE/paper/paper.tex" \
  --contest mcm --compile --output-directory "$WORKSPACE/paper/build-001"
uv run --locked python -m scripts.freeze_pdf "$WORKSPACE/paper/build-001/paper.pdf" \
  "$WORKSPACE/paper/final.pdf" --tex "$WORKSPACE/paper/paper.tex" --contest mcm \
  --build-receipt "$WORKSPACE/paper/build-001/paper.build.json" \
  --page-review "$WORKSPACE/paper/build-001/paper.pdf.page-review.json"
```

国赛选 `--contest cumcm`；未知或不匹配版式的通用PDF快照保留自身用途。美赛当前编译默认 `--layout-mode current`；历史按原 `layout_version` 选择 v1/v2/v3/v4，并在编译与冻结显式 `--layout-mode archive`。资源由 `templates/typesetting-runtime.json` 固定 Tectonic 0.17.0 及包URL／SHA256。共享样式嵌入独立TeX，字面全局字体、页边距、段距／行距、标题与页眉覆盖由检查器拒绝；变更从唯一模板源重建。

组件从 `scripts.paper_template` 调用：

| 目的 | API与身份 |
|---|---|
| 模拟美赛稿 | `preamble(title='...', identity_mode='simulation')`；队号由唯一 `MCM_SIMULATION_TEAM='7391856'` 提供，实际声明simulation。 |
| 正式美赛稿 | `preamble(actual_team, '...', identity_mode='contest')`；actual_team须来自用户／任务的实际分配，保留来源。非零只通过机械形状检查，注册身份另核。 |
| 历史美赛稿 | `preamble(old_team, '...', identity_mode='archive', layout_version=...)`；原身份与版本保留，随后archive编译／冻结。 |
| 摘要三栏 | `summary_header('A', edition=2025)` 显式原题年份；`summary_heading()`／共享 `\PraxisSummaryHeading{Summary}` 接回普通段落。 |
| 目录 | `table_of_contents(depth=1|2|3)`，默认2；组件前后 `\clearpage`，静态门核重复目录、正文后插入和直接重置页码。 |
| 连续／独立组件 | `section_component(title, body, separate_page=False, in_contents=False)`；独立组件设True，前后清出浮动体。 |
| 面向决策者的独页报告 | `memo(recipient, date, subject, body)`；v5 的 `memo` 环境前后清页，元数据必填。 |
| 可选论证组件 | v5 提供 `strengths`／`weaknesses` 列表、`algorithm`＋`algorithmic` 伪码、`subfigure` 子图及 theorem/lemma/proposition/corollary/definition/remark；按实际内容选择。 |
| 完整美赛AI尾部 | `ai_report(body, title='Report on Use of AI', in_contents=True)`；前后独立边界，静态门核重复及尾部后再插正文／文献。 |

国赛2026“AI工具使用声明”在参考文献前，用连续section_component，使用AI另交详情PDF；首个附录独立起页形成计页边界。研究稿声明与附录按期刊选择，通用骨架按实际用途组装。现有正确手写边界可检查，历史冻结保留原件。current MCM拒绝全0以及身份、年份、题号、页眉与声明的直接冲突；任意宏改写与真实注册来源继续人工核。

当届交付机械检查示例：

```bash
uv run --locked python -m scripts.contest_rules "$WORKSPACE/paper/final.pdf" --contest cumcm --edition 2026
uv run --locked python -m scripts.contest_rules "$WORKSPACE/paper/final.pdf" --contest graduate --edition 2026 --document-kind submission
```

不传edition只做兼容检查；graduate默认document-kind=report只核匿名报告部分，完整submission另核官方封面。机械子集、真实披露、原届次合规与正式提交分别验收，官方条款和已核日期见 [contest-delivery.md](contest-delivery.md)。


按实际任务组织报告，将有效运行编号、指标与来源记到工作项目记录。数据或代码变化就重跑并同步文稿。论文沿用用户当前源文件，按实际期刊、课程或比赛的规定检查格式；不硬编码某比赛的页数与字体规则。scripts/check_pdf.py 检查可提取文字、元数据、页数、实际提取文本对应的字体名称与嵌入结构，并按显式配置检查；`--forbidden-font` 使用不含子集前缀的PDF 中提取的 PostScript 字面名或带引号的通配模式（如 `'Example-Black*'`，兼容编排器追加编号），不能仅凭字体文件名或把 Black 当 Regular。`--require-embedded-fonts` 为按场景启用的检查，不默认将未嵌入字体判为违规。轮廓公式、图片文字、文本提取未识别的字形与实际版面仍须逐页渲染查看；有字体程序不证明程序有效或视觉正确。

写论文或交付摘要时，传 `--checks /实际运行/checks.json` 获取真实 total/passed/failed；已有稿件声称的项数可用 `--claimed-check-count` 比对，存在失败或数量不一致时返回非零。报告正文和状态的数量从这份证据派生，不手工凭记忆填写；检查通过不等于检查独立或覆盖充分。

```bash
uv run --locked --project "$BUNDLE" python "$BUNDLE/scripts/check_pdf.py" /绝对路径/paper.pdf \
  --checks /实际运行/checks.json --claimed-check-count 12
```

美赛当前交付的字号门禁固定为 12 TeX pt，冻结入口自动执行；先用 `--minimum-font-tex-pt 12` 取得字体候选（不套给其他赛事）。测量使用成熟PDFium的字形矩阵，包含图形嵌套与旋转后的有效字号，不能用源码12pt或多数正文字号代替。首次输出列出所有较小文字及未识别字形；逐条看实际页面、上下文和源码，修正普通正文／轴／图例的小字，真实数学上下标和式内标注才可另记 `--font-review /绝对路径/font-review.json`。记录须含 `pdf_sha256`、`minimum_font_tex_pt` 和 `approved_math_runs`，每项用输出的 `id`、`role`（`math_script`或`math_notation`）及具体`reason`；未识别数学字形另用`approved_unmapped_math_glyphs`（`role=math_notation`）。不得按字号或字体批量豁免。记录与PDF或阈值不符、剩余候选未解决时拒绝通过；这保存审阅判断，不能自动证明某字真是数学。轮廓与图片文字仍需视觉核对。

字体禁用与是否要求嵌入由本稿规格配置，不内置赛事的某一种字体名单。逐页视觉检查仍需 PDF 查看工具。交付组件的连续／独立结构按 [contest-delivery.md](contest-delivery.md) 选择，用 scripts.paper_template 的共享函数生成；check 与冻结门禁拒绝直接遗漏的边界，仍需在实际 PDF 核对前后页、浮动体和正文计页。contest_rules 只有确认AI报告独立起页时才排除该尾部，混页或重复标题不能获得美赛页数豁免；国赛首个附录若与正文混页，该页仍计入正文。普通连续章节并不因此违反格式。它们是可提取文本的机械检查，宏展开、图像和真实披露仍需审阅，不认证未知届次。

当前美赛交付必须依次完成：current 编译 → 当前 PDF 字体候选和全部页面实际审阅 → current 冻结 → `workflow.report` 登记当前冻结副本与证据。首次交付任一门禁失败就保留候选和失败，不登记为成品。唯一执行入口为 scripts.paper_template 的 `--compile` 和 scripts.freeze_pdf 的 `--tex`／`--contest mcm`：默认 `--layout-mode current` 要求当前 v5，固定运行时和资源包，并核对实际 A4 页框、摘要年份／题号／队号、完整页眉身份及 AI 报告独立边界。编译和最终冻结共用真实 `.log` 检查，Overfull hbox/vbox 或 Float too large 均拒绝；冻结要求 PDF 同目录同名的完整日志，记录日志与 PDF 修改时间供诊断，并保存日志 SHA256。有诊断的构建收据须匹配该日志哈希；历史 current 收据缺此字段时允许以实际新鲜零溢出日志补验，记录该兼容路径而不改旧收据。编译器可能先落日志后写 PDF，因此不以二者时间先后判定有效性；日志、源码和 PDF 哈希也不代替视觉或科学核验。

current 编译与冻结还共用摘要单页边界检查：从同份已绑定 TeX 的真实 `PraxisSummaryHeading` 到首个 `clearpage`（仅摘要文档可到文档结束），解析最后可见普通文字，要求其末尾锚点在实际 PDF 中唯一出现并位于第 1 页最后。首个 `clearpage` 后须接字面章节／目录组件或文档结束，不能用一次换页隐藏继续的摘要。检查保留源码 SHA256，支持嵌套文字格式、注释、定义与 PDF 连字／行末断词；定义和代码中的文字不能充当摘要锚点。摘要内的浮动体、外部输入、图像、不确定宏展开，或数学等非普通文字结尾，不能凭较早段落自动认证，须修成可核查边界后重编。自然跨页即使没有 Overfull 也会拒绝；此检查不代替全部页面的实际审阅，archive 不追改原验收。

Current MCM compilation and freezing also bind a literal Summary-tail anchor from the checked TeX source to the final extractable text on PDF page 1. The first clearpage must lead to a literal heading, contents or document end, so it cannot hide a continuing Summary. Natural page overflow is refused even without an Overfull warning. Unsupported expansion, external content, floats or a non-prose tail cannot be certified by an earlier paragraph; actual page review remains required, and archived evidence retains its original status.

current 美赛冻结自动执行 12 TeX pt 字号门禁；合法较小数学候选必须逐项以同 PDF 的 `--font-review` 解释，普通小字必须修源重建。逐页实际查看后保存 `--page-review`（默认 `<候选.pdf>.page-review.json`）：含当前 `pdf_sha256`、真实 `actor`、全部一基页码 `pages`，以及 `format_checks` 中 `paragraph_indentation`、`figures_tables_fonts`、`clipping_overlap`、`cross_references`、`summary_headers`、`ai_report_boundary` 六项实际核对的布尔值 true。缺项、false、旧哈希或漏页都拒绝。它记录审阅范围与判断，不能自动认证完整 TeX 宏展开或人的核验。冻结还必须提供同次 `--build-receipt`；收据保存实际格式、结构、字体、日志和页审阅结果，创建字节一致的新副本后才调用 `workflow.report`。

current 编译还通过 Tectonic 的依赖清单记录实际打开的本地输入和图片，再绑定第二次构建。冻结核对这些文件的存在与字节，不能仅主 TeX 不变就接受已经改动的 `input` 或图像。旧 current 收据缺少依赖绑定时须真实重编；archive 保留原证据身份。摘要、页眉及明确的当前／模拟作者身份声明共用队号检查，历史身份和科学数字保留各自角色；静态声明检查不理解任意改写。

编译器若打开本机标准空设备，收据以 `system_inputs` 明确保存其身份和即时 EOF 语义，第二次构建与冻结再次核对；不将字符设备当作普通文件读完整哈希。例外仅适用于本机标准空设备，普通同名文件、符号链接别名和其他设备仍拒绝或按真实文件绑定。这个分类不取消文稿与图像依赖的字节检查，跨系统行为由真实排版 CI 核对。

历史重现必须显式选择保留的 `layout_version`，编译与布局冻结传 `--layout-mode archive`；保留版本、原件和旧哈希，不称当前交付通过。无布局 profile 的通用 PDF 快照、research 和 CUMCM 继续其各自用途与规则；它们不自动成为美赛交付，也不能冒充当前美赛字号／页面门禁成功。构建或冻结记录不是正式提交回执。

章节结构由 `python -m scripts.paper_template main.tex --contest mcm --review-structure` 预检，或单独运行 `python -m scripts.paper_structure main.tex`。采用 pylatexenc 的语法树，检查字面 chapter／section／subsection／subsubsection 的直接父子关系；注释、代码示例、数学内容和宏定义不作为实际标题。带 `--tex`／`--contest` 的最终冻结同样检查，未解决候选或解析失败时在写PDF前停止，另将结果保存在冻结收据；原构建收据的版式身份不变。它是编辑复查入口，不是官方子节数量规则或完整TeX解析认证：不展开宏、不读取 input／include、不执行条件分支；未覆盖的结构仍以实际目录和正文为准。合法的复杂TeX也可能触发解析失败，先查看诊断，不因此判论文错误，也不绕过成品审查。没有源码的通用快照保持原用途，不认证章节结构。

只有一个编号子节时，默认合并无独立作用的层级。确需保留者保存JSON：`tex_sha256` 为当前UTF-8源码字节的SHA256，`approved_single_child_nodes` 为 `[{"id":"预检给出的候选id","reason":"该子节实际承担的独立导航或规定职责"}]`。预检追加 `--structure-review /绝对路径/structure-review.json`，单独脚本用 `--review`，最终冻结也传 `--structure-review`。过期哈希、未知／重复id和空理由拒绝；不能用批量理由或增加无内容标题凑数。记录保存实际判断，不能自动证明理由正确。预检与编译分开调用，最后查看同次编译的目录、正文与交叉引用。

scripts/check_references.py 读取每行一条的参考文献文本，用 Crossref 免费接口核对其中的 DOI 是否存在、题名与年份是否与引文相符，输出 verified / mismatch / not_found / network_error / no_doi。需要联网；没有 DOI 的书、标准和网页只报告 no_doi，必须手工核对。通过只说明记录存在，不说明该文献支持所引论断。


### 当前交付的论文诊断（全部先告警）

`freeze_pdf` 在 current MCM/CUMCM 布局冻结中调用 Summary、正文语言、关键数字与题面覆盖诊断，收据 `manuscript_diagnostics` 含逐项结果和输入 SHA；新项均为 `diagnostic_only:true`，不以词汇代理指标判论文质量。版式、字节绑定和原有拒绝条件照常执行。缺少元数据或文本映射不确定时明确列未检查项，不当作通过。

```bash
uv run --locked python -m scripts.check_summary "$WORKSPACE/paper/paper.tex" --results "$WORKSPACE/results.json"
uv run --locked python -m scripts.check_prose "$WORKSPACE/paper/paper.tex" --pdf "$WORKSPACE/paper/paper.pdf" --problem-year 2023
uv run --locked python -m scripts.check_claims "$WORKSPACE/paper/paper.tex" --results "$WORKSPACE/results.json"
uv run --locked python -m scripts.contest_coverage "$WORKSPACE/paper/paper.tex" \
  --requirements "$WORKSPACE/planning/requirements.json" --model-contract "$WORKSPACE/planning/model-contract.json" \
  --figure-plan "$WORKSPACE/planning/figure-plan.json"
```

正文统计使用实际 PDF 文本及 TeX 节标题映射，排除局限、优缺点、参考、附录、AI 与复现节；标题无法唯一定位时比例为 null。英文否定词占比 >0.16、六位有效数字、运行编号／本机路径、晚于题目年份的引用仅告警；历史学习稿显式 `--allow-anachronism`。公开 URL、数学环境、复现节各按实际用途处理。数值检查只覆盖显式阿拉伯数字加已识别单位／币种／百分号，允许 1e-3 或显示精度舍入；值匹配不证明量纲、出处或主张正确。

覆盖位置由 `requirements.json` 的可选交付元数据提供，脚本核实际源位置，不猜语义：

```json
{
  "paper_locations": {"P1":{"summary":"label:sum:p1","body":"label:answer:p1","conclusion":"label:end:p1"}},
  "assumptions": [{"id":"A1","test_location":"label:test:a1"}],
  "sensitivity": {"parameters":["capacity"],"conclusion_parameters":["capacity"],"location":"label:sensitivity"}
}
```

位置值可为 `label:<实际标签>` 或该区域的原文短句；Summary／正文／结论各自核验。假设表、每条检验位置、声明参数交集、Memo 页边界和符号、优缺点及图计划逐项告警。`planning/figure-plan.json` 用 `{figures:[{id,kind,reader_question,data_source,section}],omissions:[{kind,reason}],few_figures_reason}`；id 对应实际图标签，kind 的 structure/map 供结构图及空间地图核查，数量和省略理由按 [visualization.md](visualization.md#图表计划)。源检查不代替实际 PDF 页审阅。

```bash
uv run --locked python -m scripts.reader_packet "$WORKSPACE/paper/paper.pdf" "$WORKSPACE/reader-packet" \
  --requirements "$WORKSPACE/planning/requirements.json" --minutes 25 --pages 16 17
```

阅读包含首页、可识别图页、结论与 Memo 候选页，保留原页码映射；`--pages` 仅补实际核实的漏选页。标题／图号是文本启发式，先核 packet 覆盖。全新读者只读 packet，最多20–30分钟，按模板逐题写 yes/no、一句话答案、可信依据与首要追问；真实 actor、耗时及原 PDF SHA 一并保存。缺答案或过期 PDF 绑定先告警，不充当全文评审或数学验证。

最终冻结可追加 `--results`、`--requirements`、`--model-contract`、`--figure-plan`、`--reader-review`（均为实际 JSON 路径）、`--problem-year` 与历史研究用 `--allow-anachronism`。这些参数只用于 current MCM/CUMCM；archive 保持原证据，不追套新版诊断。只有经独立 O/MH 校准并获用户采纳的项目才能另升为拒绝，目前没有新增拒绝项。

## 数值任务的证据索引

模型运行前对照原题建立 `planning/requirements.json`。schema 2 的最小字段示例（quote须替换为本案例题面原句）：

```json
{
  "problem_items": [{"id":"P1","quote":"在 x=4 时计算 y，并说明验证依据","page":1}],
  "requirements": [{
    "id":"Q1", "question":"在 x=4 时计算 y", "unit":"dimensionless",
    "result_pointer":"/prediction", "checks":["independent arithmetic"],
    "problem_item_ids":["P1"], "kind":"answer"
  }]
}
```

`problem_items` 每项有唯一id、原文quote及正整数页码；quote须在 `planning/problem-extracted.txt` 中逐字出现（折叠空白，跨行连字符可去掉），至少4个英文词或15个字母、数字、汉字，且各项互不相同；init 记录抽取文本哈希，事后改动须在 `problem_text_corrections` 逐条说明。每个 requirement 给非空 `problem_item_ids`，schema 2 下 kind 必填，取 answer/forecast/decision/proof；所挂原句含预测类词而 kind 不是 forecast 时须写 `kind_justification`。每个原题项须映射到requirement，或在该item写有实际内容的 `conditional_answer`／`not_addressed_reason`；遗漏、假引用或未知id使 evidence-incomplete。提取文本是接收时证据，实际要求与页码仍核原页。

schema 2 每个 requirement 至少链接一项 `independent:true` 且 method 非replay的通过check。预测项另链接 `method:naive_baseline`，带 `baseline_score/model_score/metric/lower_is_better`；模型更差须 `disclosed:true`，否则 `claim_problems` 报错。披露只保留诚实状态，预测是否满足题意仍按实际指标与基线审查。

可选的 `claims` 列表把结论与证据强度对上：每条 `{"id", "requirement", "text", "strength", "result_pointer", "checks"}`，strength 取 computed（结果指针能取到值）、checked（链接的检查至少一项通过）、independent（至少一项通过的检查在 checks.json 里标 `"independent": true`，由作者声明用了不同的方法）。`independent` 由检查记录的作者自己声明：索引只核对声明与证据是否一致，抓得住“说得比证据强”，抓不住“假装独立”，所以仍要有人看这项检查的方法是否真的不同。证据索引会报告两类问题：没有任何结论得到证据支持的问题要求，以及声明强度高于所链接证据的结论。

清单与声明的 `checks` 必须是检查名称的字符串列表，不能用一个字符串冒充列表。案例、数值结果、检查及清单的JSON读取均拒绝重复键与非有限数值；例如同一检查重复写 `"passed": false`、`"passed": true` 会被拒绝，不能靠最后一个值升级证据。`case.json.schema` 支持整数1或2；没有字段的历史案例沿原v1解释，不改写原件，显式未知版本或错误类型拒绝。模型输出中的业务字段仍由任务定义，不给任意结果对象强行套一份通用结构。

独立检查说明其依据、共用的数据／常量、检查范围和未覆盖内容；必要时记录方法族帮助审读。机械禁止导入模型常量或要求方法族名字不同不能证明独立性，也会误拒同一方法族下的独立实现和解析界。共用单位定义可以合理，直接引用作者答案当期望值或重用同一关键错误则不能算独立答案。

清单应覆盖实际数值任务，每项 id 唯一，unit 必须写明（无量纲可用 dimensionless），result_pointer 使用 JSON Pointer 访问 results.json，例如 /forecast/0/value。检查名必须对应验证器实际生成的独立检查；名称唯一，不要关联到不相干的检查。单位是否正确及验证是否独立仍需助手审核。

```bash
uv run --locked --project "$BUNDLE" python "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" evidence --case "$WORKSPACE/cases/example"
```

返回结果字段值、验证证据、运行回执与清单哈希，以及已链接数量。缺字段或缺检查返回 evidence-incomplete 并退出非零；最新运行失败或过期时拒绝，不能偷偷改用以前成功的运行。空清单拒绝，修改清单使旧运行失效，须重跑后再建索引。旧案例未提供清单时仍可 run/status，但不可声称已通过任务覆盖检查。

evidence-linked 只表示清单中的连接存在；不能证明所有任务已列入，也不能证明检查有意义、单位正确或论文已完成。论证、图表和格式等非数值要求仍在 tasks.md 中跟踪。该命令输出 JSON，不覆盖运行原件；如需保存，将标准输出写到工作项目的报告目录。

## 可选任务协调

多轮案例可调用 [workflow.md](workflow.md)，在同一份 progress 连接初始化经验检索、预算、运行、审阅和报告，复用本文件契约。

schema 2 的 `workflow.accept` 在原 actor/scope/run_id/receipt_sha256/quality_decision 之外核：

- `problem_items_ticked:[{id,location}]` 恰好逐一覆盖全部原题项，位置非空。
- `attacks` 至少3项 `{type,target,result}`；type取 units/limit_case/sign_flip/small_example/independent_recompute/magnitude，result取 survived/refuted/inconclusive；有 refuted 时拒绝pass。
- `mechanism_audit:{symbols_checked:n,double_meaning_found:[]}`，n不少于契约声明的符号数且至少为1；有未解决多义时拒绝pass。
- 契约不通过时 `workflow.run` 不消耗尝试次数，`next` 返回 prepare 并列出契约问题；workflow 状态记录案例 schema，之后每个命令核对。
- 初始化检索遇空／generic／prior lessons时，从题面启发式取最高频15个英文内容词或中文双字；状态保存 `lesson_retrieval.query_source/query_tokenization`。首次运行前 tasks.md 对每个hit写同一行的 `applied: ID 行动` 或 `not_applied: ID 理由`；accept核首次实际run快照与哈希，事后补写不追认。检索与新条目格式见 [learning-loop.md](learning-loop.md)。

schema 1沿原行为。字段门保存作者／评审者声明，实际覆盖、攻击是否有力和机制是否正确继续由作品及独立检查判断。

## 可选运行反馈

正常任务可同步用 `scripts/feedback.py init/record` 记录实际模型／宿主来源、工作模式、材料接触、阶段、评审／候选、介入与停止事件；不可取得的信息保留 `unknown`，不会自动捕获聊天。记录放用户案例的 `feedback/`，不纳入计算定义，不改变数值证据有效性规则。已有非 pipeline 目录也可适配。

交付或实际停止后，可用 `stage` 按显式文件清单生成独立分享副本与摘要，查看删减／缺失和原件／分享哈希；确认实际清单后才 `pack`。同一只读 `inspect` 接受目录和 ZIP，不执行包内代码、不上传。完整字段、事件样例、分享边界和限制见 [运行反馈](feedback.md)。反馈记录完整、ZIP 字节完好与整题研究完成分别验收。

分享包写入器对压缩比过高的合法重复日志使用无压缩条目，保持读取器的膨胀比限制。拒绝的 ZIP 同样关闭资源；此措施不取消总字节、路径、符号链接和文件数检查。插件导出收据绑定实际交付文件，包括包根 README 与 LICENSE；收据自身不递归绑定，哈希也不等于信任或功能验证。


## 活案例：字段绑定、依赖与局部更新

这些是本地 CLI，不是新增 MCP 数学工具。历史冻结、作者判断和科学验证保持独立。

- `paper_facts.py resolve/expand --case ... --manifest ... --workspace ...` 用非根 RFC6901 路径、来源 SHA、单位和格式绑定 `\fact{key}`；数组位置可加语义 guard。展示算术仅接受有来源链的有限操作，不运行文档代码。补充证据保留原作用范围，不能冒充某次运行字段。所有出现生成句子映射；查到同值不算绑定。
- 默认只选最新且可用的运行，不跳过失败。显式 `--run-id ... --historical` 只复现历史显示，不能恢复科学有效性。展开目标必须是新目录；旧 TeX/PDF/收据不覆盖，编译及实际页面审阅另做。
- 新运行保留原 `code/dependencies` 广库存，并额外记录 `actual_dependencies`。缺省仍保守失效；案例显式 `dependency_mode: "python-reviewed"` 表示调用者已审阅其 Python I/O 适用性。两阶段观察完整时，按实际读取/导入、条件路径、目录枚举、环境及执行不变量判断失效；未用脚本不因此失效。旧收据不补写追踪。
- 追踪是 Python 观察，不能观察全部原生库内部 I/O，不能当作系统沙箱。用户显式 ctypes 加载、子进程、网络或不完整观察退回保守模式。唯一运行时例外是按标准库实际源码/栈定位的顶层 `pythonapi = PyDLL(None)` 初始化，保留事件与 SHA；不豁免用户 `CDLL(None)`。失败/超时也留部分观察，瞬时修改后复原不保证检出。
- `pipeline.py --workspace ... refresh --cases ... --dry-run` 只报告已有影响/差异；没有新运行时数字变化写未知。清单是用户工作区里的 `schema:1,cases:[...]`，每项显式指定 `id/case/baseline_run`，另一个不可变案例基线用 `baseline_case`；可指定 `tolerances:{absolute,relative,ignore_paths}`、`conclusions:[{id,pointer,operator,threshold?}]`、fact manifest、句子映射及版式/指导文件的旧 SHA。容差判断为 `|a-b| <= absolute + relative*max(|a|,|b|)`；按数组原位置比较，不用同值搜索重配。
- `--execute` 只消耗已有工作流的一次合法尝试，不建立或重置时钟。失败保留，不换旧成功。报告可同时含 unaffected/numbers/conclusions/layout/guidance/unknown；列出已声明结论谓词的翻转，无法据此声称全部自然语言结论已核。
- `--execute --rebuild` 仅在已绑定数字、结论谓词未翻转时生成独立候选和变化页清单；作者仍须复查比较措辞、条件和页面，不能自动冻结。结论翻转交作者改论证；指导改变给定点建议，不整篇重写。像素相同仅证明该尺寸显示复现，不证明科学正确。

有分段人写源和数值图生成器的案例，清单用 `facts.driver:{path,sha256,timeout_seconds?}` 绑定已审阅的本地适配脚本；refresh只传固定的case/run-id/output参数，不走shell，重建段落与图到新目录。脚本字节变化须重新审阅并更新清单，不直接在文档或数据中执行命令。静态源展开不能保证未绑定图的数值自动同步，涉及这类图应使用适配器或转人工复查。
