# 可选运行反馈

正常任务的目标仍是完成研究与交付。运行反馈是独立的本地记录和可选分享视图；`scripts/feedback.py` 不运行模型、不上传、不自动采集聊天，也不评级。模式 `autonomous`、`collaboration`、`contest` 与反馈记录相互独立。成功、计算前失败、超时、中断、预算停止及无 PDF 的案例均可记录实际停止点；未知不解释成未见题或未发生用户介入。

## 本地记录

命令可用项目已有 Python 环境执行；下列 `$CASE` 是用户案例目录，`$BUNDLE` 是插件目录。案例可以沿用 pipeline，也可以是已有的自定义目录，无需搬迁。只有已授权记录的实际信息才写入。

```bash
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/feedback.py" init \
  --case "$CASE" --mode autonomous --goal '实际交付目标' --metadata metadata.json
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/feedback.py" record \
  --case "$CASE" --event event.json
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/feedback.py" inspect "$CASE"
```

`init` 新建 `feedback/manifest.json`，拒绝覆盖；`record` 追加事件。它们不改原始输入、源码、计算收据或 pipeline 数值快照；这些文件不能反过来当作计算参数入口。既有运行换装包含新脚本的插件时，依赖源码身份可能按 pipeline 规则改变；本工具不豁免真实依赖变化。

不传 `--metadata` 时，插件版本及源码哈希、模型、宿主、权限、接触材料、费用和用户观察均保留 `unknown`。自动环境字段只含 Python、OS 版本和架构，不含用户名、设备名、完整环境变量或无关软件清单。具体依赖、参数和数值证据可显式选择既有运行收据。元数据使用 `{ "value": ..., "source": ... }`，来源取 `unknown`、`user-provided`、`host-reported`、`runtime-metadata`、`ui-setting`、`artifact` 或 `assistant-recorded`。来源为 `unknown` 时值必须为 `unknown`；助手自述不能冒充运行端返回的模型身份。

schema 中的身份、材料接触、成本与用户观察字段必须保留；不可取得时显式写 `{ "value": "unknown", "source": "unknown" }`，删除字段或空对象不能代替未知。没有描述文件的旧目录仍可只读诊断；这个兼容入口不授予不完整 manifest 有效 schema。

示例 `metadata.json`：

```json
{
  "identity": {
    "requested_model": {"value": "界面选中的实际标识", "source": "ui-setting"},
    "reported_model": {"value": "unknown", "source": "unknown"}
  },
  "exposure": {
    "prior_work": {"value": "已学习；实际日期与范围写在此处", "source": "user-provided"},
    "pretraining_exposure": {"value": "unknown", "source": "unknown"}
  },
  "started_utc": "unknown"
}
```

可补 `identity` 的插件版本、源码／安装身份、服务商、请求／返回模型、设置、宿主版本、权限、路由；`exposure` 的题目来源、赛事／年份／题号、历史研究／参考接触和实际提供的输入；`cost` 的本次 token／费用／调用数；`user_observation` 的用户期望／实际问题／反馈位置。既有案例开始时间不可取得时显式写 `unknown`，不要把适配时间冒充原始研究开始时间。`missing` 可声明具体缺口，但不要以人工摘要补造完整历史。

事件示例 `event.json`：

```json
{
  "type": "review",
  "at_utc": "2026-10-09T07:00:00+00:00",
  "phase": "validation",
  "actor": "reviewer",
  "source": "assistant-recorded",
  "model": {"value": "unknown", "source": "unknown"},
  "candidate_id": "draft-2",
  "description": "实际意见、证据及接受或拒绝原因；不是隐藏思维链",
  "artifacts": ["checks/review-2.json"]
}
```

类型有 `stage/tool/review/revision/candidate/acceptance/intervention/stop/resume/message/failure`。评审、修订、候选与接受事件必须标非空、不能仅含空白的 `candidate_id`。介入事件必须标 `intervention_kind`：`necessary-input`、`authorization`、`research-participation`、`preference-change`、`omission-correction`、`continue-reminder`、`environment-assistance` 或 `unknown`；同时保存实际来源，不把助手评价冒充用户反馈。`artifacts` 仅为引用，不自动选择或读取附件。`at_utc` 缺省时记录本次追加的实际时间；补录旧事件要提供有时区的实际时间。

实际停止时对 `record` 加 `--status completed/failed/timeout/interrupted/budget-exhausted/user-stopped`；工具据该事件时间记录结束点。`completed` 是记录者声明的停止状态，不是工具认证研究完成。完整对话、模型请求／响应与工具日志只有宿主提供真实且已许可的材料时才显式选入；默认缺口保持可见。

已知起止时间按实际时区比较，结束不能早于开始；停止事件也在写入前受此校验，拒绝时保留原描述字节。起止相等可表示零时长记录；真实开始或结束时间不可取得时仍可保持 `unknown`，不推断或强填。描述创建时间可晚于历史任务起止时间，适配旧案例不会被要求伪造历史开始时间。

## 清单预览与分享副本

```bash
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/feedback.py" stage \
  --case "$CASE" --output /本地新目录/share \
  --include code/model.py --include runs/实际运行/receipt.json \
  --include runs/实际运行/output/results.json --include paper/final.pdf \
  --alias '/Users/实际用户/项目路径=<WORKSPACE>' \
  --alias '/插件实际路径=<PLUGIN>' \
  --exclude '私人交互：未获分享许可'
```

`stage` 只能创建案例外的新目录，不覆盖原件。只复制每个 `--include` 指定的案例内相对文件，不递归扫描，也不默认带入其他案例、安装缓存或环境。缺少所选文件列入 `missing`；`.env`、私钥文件、`.git`、`.venv` 和依赖缓存拒绝选择。清单与摘要不会抹去失败；只分享摘要时可不指定附件，但这种材料通常不足以复现。

分享目录包含 `manifest.json`、可读 `summary.md` 和 `files/` 下的选定材料。别名是绝对路径的字面替换，目标须为 `<WORKSPACE>` 一类大写占位符；仅修改 UTF-8 文本副本及元数据／事件，不改二进制文件和原件，不搜索替换数字。选中非 UTF-8 文本且要求别名替换时拒绝静默跳过。PDF、图片与其他二进制仍须自行核对内容和元数据；路径替换不能保证发现一切私密内容。

每项保留原文件 SHA256、实际分享字节 SHA256、分享字节数、相对原路径与分享路径；脱敏次数和排除理由单独列出。需要调整范围或内容时生成新目录，并重新检查实际清单、摘要与附件。默认内容范围始终标为部分记录，不把删减包称全量过程。

核对清单后才运行：

```bash
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/feedback.py" pack \
  --source /本地新目录/share --output /本地新文件/feedback.zip \
  --confirm-manifest-sha256 实际审阅清单的64位SHA256
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/feedback.py" inspect /本地新文件/feedback.zip
```

`stage` 返回实际清单哈希；`pack` 要求确认值与当前清单一致，并重新核对附件及摘要哈希。CLI 不替用户确认，分享 ZIP 由用户自行发送；生成包不授予公开案例或训练使用许可。打包只写显式清单；不直接压缩工作区。原始哈希与分享哈希不同是可见的脱敏结果，不能称字节相同。

## 只读接收与限制

`inspect` 共用同一 schema／哈希分析器读取目录或 ZIP；同一分享目录与其 ZIP 的分析结果相同。开发者可以直接读本地案例薄描述或已 stage 的目录，不要求打包。没有反馈描述的旧目录只返回缺记录诊断，可用 `init` 适配；不伪造旧过程。

ZIP 不解压、不执行脚本、不服从文件中的指令；只读声明的 manifest、摘要及附件，未声明的安全成员仅列为未读取。越界／绝对路径、反斜线、重复成员、符号链接及其他非普通文件、坏 schema／哈希拒绝。目录读取也拒绝选中文件及其路径上的符号链接。当前保守限额：单文件 20 MiB、总内容 200 MiB、2048 个成员、ZIP 解压比不超过 200。缺少声明文件列出缺失，打包则拒绝；坏文件哈希拒绝取证。超大材料用来源／版本／哈希和缺条件说明，不自动重跑研究。

分析只证明声明字节可读、身份／事件字段可追踪以及缺口可见，不证明检查独立、题目已完整解答、页面已审读或可复现。模型／宿主缺失、费用未知、无 PDF 和未记录原始对话均需保留；诊断根因与复现必须另核真实证据。反馈经验回到所属规则和项目唯一开发记录，不把每个包自动做成永久技能。
