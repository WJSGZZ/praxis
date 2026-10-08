# 自动执行与证据契约

执行计算时，解析技能真实位置为 BUNDLE，当前用户工作项目为 WORKSPACE。宿主能力未知或调用失败时按 [agent-compatibility.md](agent-compatibility.md) 核对；能力缺失只做可完成的分析，不能编造运行。环境未准备时执行 `uv sync --project "$BUNDLE" --locked`；需要开发测试时增加 `--group dev`。用 `"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE"` 调用工具，不要依赖技能安装目录作为当前工作目录。下列命令的 BUNDLE 与 WORKSPACE 均应替换为实际绝对路径。

## 先判断要不要走案例系统

案例脚本（`init`、`run`、`status`、`evidence`）适合要保留运行快照与机器证据索引的任务。已有可复现执行链时可以沿用：报告数字能回指脚本与输出文件，检查有名字、结果与证据，最终材料有版本／哈希清单。选择不使用案例系统不等于放弃追溯，也不能声称具有 pipeline 的自动过期检测。需要 `check_pdf.py --checks` 核对检查数时，将真实检查保存成下文契约的 checks.json。

## 接收 Word 和 Excel 附件

`init` 直接接收 PDF、文本、Markdown 与 Excel。题面或附件是 .docx 时：先用 python-docx 读文字与表格；如果文中公式、地图、示意图是对象（MathType、VML 绘图组、嵌入图片），文本抽取会缺内容，要把 .docx 转成 PDF（LibreOffice 的 `soffice --headless --convert-to pdf`）后渲染查看，必要时解压 .docx 读 `word/document.xml` 与 `word/media/`。公式对象数量与抽取到的公式数不符时，逐个核对，不要凭印象补。从图中提取的结构（地图相邻关系、表格）要写明是怎样提取的，并至少抽样人工核对。

## 并行计算的预算

同时开多个进程前先估计核数与内存：并行任务的总数不超过核数的一半，长任务先在小样本上计时。机器过载会使每项慢数倍，得不偿失。

## 建立案例

```bash
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" init \
  --name training-example --problem /绝对路径/problem.pdf \
  --data /绝对路径/data.csv --phase preparation
```

题目原文可先保存为本项目文件再传入；CLI 支持 PDF、TXT、Markdown。多个数据文件重复 `--data`。默认建在 `cases/<name>/`；名称自行根据任务取，不必为取名问用户。已有目录拒绝覆盖，接续时读取 `case.json` 与 `planning/tasks.md`。`--phase contest` 只记录比赛阶段，不能据此判断比赛时限或取得提交授权。

案例保存：`raw/` 原件只读副本、`planning/` 题意与任务记录、`audits/` 数据质量报告、`code/` 可复现处理与模型、`runs/` 每次独立运行结果。副本保留来源路径、哈希和字节数。CSV 使用显式编码（默认 UTF-8；可 `--encoding gb18030`），Excel 逐表检查；其他格式或大于 50 MB 的数据明确标记延后审计，选择流式或针对性处理。延后审计不等于已核验可用。PDF 即使提取到文字仍须查看原页。

## 内容理解不是脚本替代的

题意、路线、假设和推进条件统一按 [methods.md](methods.md) 写入对应任务记录。脚本不自动理解题目、选择模型或确认检查的独立性；本文件只规定如何接收、执行与追溯已经明确的工作。

## 模型与验证器

助手写并检查案例 `code/model.py` 与 `code/validate.py`；两者使用 argparse 接收以下接口：

```text
model.py --output <本次运行的输出目录>
validate.py --results <输出目录/results.json> --output <本次运行/checks.json>
```

- 模型在 `--output` 下生成非空对象 `results.json`，另可生成 CSV、图片和参数记录。结果需包含真实指标与适用范围；数据来自案例原始副本，处理参数保存于案例代码／配置中。
- 验证器对结果做独立计算或检查，生成非空 JSON 列表。每条为 `{"name":"检查名称", "passed":true/false, "evidence":"具体计算或对照结果"}`。不能用“运行成功”或 `assert True` 代替独立检查。失败也如实写入证据并退出非零。
- 预测：和朴素基线比较，选择正确的数据分割；多步预测还要核对目标集合，开发／调参目标不得跨入最终留出集，仅检查训练前缀并不充分；优化：检查约束、整数性与基准；连续模型：解析解、守恒、边界或步长；评价与敏感性：使用适合实际问题的检查。随机种子固定，避免只报告最佳一次运行。
- 可以导入技能包 `modeling/` 与 `scripts/`。运行器把技能包路径加入 PYTHONPATH。不要把模型生成的其他文件放进原始数据区，或用脚本联网调用不相关外部服务。

## 运行与接续

```bash
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" run \
  --case "$WORKSPACE/cases/training-example" --timeout 120
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" status \
  --case "$WORKSPACE/cases/training-example"
```

每次生成新的运行目录，包含两个阶段的 stdout/stderr、命令、时间、代码与输入哈希、源码／参数快照、依赖源码快照、实际 Python／包版本、检查报告、输出哈希和状态。运行顺序以收据 started_utc／ended_utc 为准，避免同秒目录随机后缀倒置；精确时间平局时失败／未完成优先阻断，旧收据缺时间兼容目录时间，坏时间戳拒绝取证。命令用固定 Python argv，不通过 shell 执行题目或数据里的命令。超时或失败记录保留，先查看根因再调整；不覆盖已跑出的结果。

`automatic-checks-passed` 只表示已记录的自动检查通过。`status` 可发现原始输入、代码、依赖或结果变化，标记过期证据；只用 `usable_automatic_evidence: true` 的结果准备论文，并继续评估现实机制与稳健性。检查本身是否有意义仍需 助手审核，不把脚本状态当成科学结论或用户已核验。`paper_ready` 默认 false，不自动授予论文完成状态。

`source_snapshot` 整体哈希 planning/tasks.md、requirements.json 与 code 下文件。纯操作接续放 planning/progress.md，纯贡献放 contributions.jsonl；这些文件不是计算参数入口，不可用来隐藏实际输入变更。有效成果与候选的接受／恢复决定按 [methods.md](methods.md) 维护；这不是 `status` 自动择优的功能。候选失败不覆盖已接受文件，但当前证据是否可用仍以实际快照为准；最新运行失败时 `evidence` 不会偷偷返回旧成功。要恢复旧快照，明确记录恢复理由、核对输入／代码／环境，并重新执行当前状态要求的检查；不能只在任务表把旧结果改成“有效”。

自动化的边界：程序日志不是完整 AI 对话；哈希不是官方提交回执；本地只读不是不可篡改存证；输入副本不是备份策略。原始大数据与生成输出默认不纳入 Git，实际比赛须安排本地备份。

## 写作连接

按实际任务组织报告，将有效运行编号、指标与来源记到工作项目记录。数据或代码变化就重跑并同步文稿。论文沿用用户当前源文件，按实际期刊、课程或比赛的规定检查格式；不硬编码某比赛的页数与字体规则。scripts/check_pdf.py 检查可提取文字、元数据、页数、实际提取文本对应的字体名称与嵌入结构，并按显式配置检查；`--forbidden-font` 使用不含子集前缀的PDF 中提取的 PostScript 字面名或带引号的通配模式（如 `'Example-Black*'`，兼容编排器追加编号），不能仅凭字体文件名或把 Black 当 Regular。`--require-embedded-fonts` 为按场景启用的检查，不默认将未嵌入字体判为违规。轮廓公式、图片文字、文本提取未识别的字形与实际版面仍须逐页渲染查看；有字体程序不证明程序有效或视觉正确。

写论文或交付摘要时，传 `--checks /实际运行/checks.json` 获取真实 total/passed/failed；已有稿件声称的项数可用 `--claimed-check-count` 比对，存在失败或数量不一致时返回非零。报告正文和状态的数量从这份证据派生，不手工凭记忆填写；检查通过不等于检查独立或覆盖充分。

```bash
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/check_pdf.py" /绝对路径/paper.pdf \
  --checks /实际运行/checks.json --claimed-check-count 12
```

字体禁用与是否要求嵌入由本稿规格配置，不内置赛事的某一种字体名单。逐页视觉检查仍需 PDF 查看工具。scripts/freeze_pdf.py 创建字节一致的新副本与哈希回执，不是正式提交回执。

scripts/check_references.py 读取每行一条的参考文献文本，用 Crossref 免费接口核对其中的 DOI 是否存在、题名与年份是否与引文相符，输出 verified / mismatch / not_found / network_error / no_doi。需要联网；没有 DOI 的书、标准和网页只报告 no_doi，必须手工核对。通过只说明记录存在，不说明该文献支持所引论断。


## 数值任务的证据索引

模型运行前，由助手对照原题创建案例 planning/requirements.json，例如：

```json
{
  "requirements": [
    {
      "id": "Q1",
      "question": "在 x=4 时预测 y，并说明验证依据",
      "unit": "dimensionless",
      "result_pointer": "/prediction",
      "checks": ["independent arithmetic"]
    }
  ]
}
```

可选的 `claims` 列表把结论与证据强度对上：每条 `{"id", "requirement", "text", "strength", "result_pointer", "checks"}`，strength 取 computed（结果指针能取到值）、checked（链接的检查至少一项通过）、independent（至少一项通过的检查在 checks.json 里标 `"independent": true`，由作者声明用了不同的方法）。`independent` 由检查记录的作者自己声明：索引只核对声明与证据是否一致，抓得住“说得比证据强”，抓不住“假装独立”，所以仍要有人看这项检查的方法是否真的不同。证据索引会报告两类问题：没有任何结论得到证据支持的问题要求，以及声明强度高于所链接证据的结论。

清单应覆盖实际数值任务，每项 id 唯一，unit 必须写明（无量纲可用 dimensionless），result_pointer 使用 JSON Pointer 访问 results.json，例如 /forecast/0/value。检查名必须对应验证器实际生成的独立检查；名称唯一，不要关联到不相干的检查。单位是否正确及验证是否独立仍需助手审核。

```bash
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" evidence --case "$WORKSPACE/cases/example"
```

返回结果字段值、验证证据、运行回执与清单哈希，以及已链接数量。缺字段或缺检查返回 evidence-incomplete 并退出非零；最新运行失败或过期时拒绝，不能偷偷改用以前成功的运行。空清单拒绝，修改清单使旧运行失效，须重跑后再建索引。旧案例未提供清单时仍可 run/status，但不可声称已通过任务覆盖检查。

evidence-linked 只表示清单中的连接存在；不能证明所有任务已列入，也不能证明检查有意义、单位正确或论文已完成。论证、图表和格式等非数值要求仍在 tasks.md 中跟踪。该命令输出 JSON，不覆盖运行原件；如需保存，将标准输出写到工作项目的报告目录。
