# 自动执行与证据契约

先按 agent-compatibility.md 核对宿主能读取本地文件并执行终端；能力缺失时仅做相应分析，不能编造运行。解析技能真实位置为 BUNDLE，当前用户工作项目为 WORKSPACE。先执行 `uv sync --project "$BUNDLE" --locked`；需要开发测试时增加 `--group dev`。用 `"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE"` 调用工具，不要依赖技能安装目录作为当前工作目录。下列命令的 BUNDLE 与 WORKSPACE 均应替换为实际绝对路径。

## 先判断要不要走案例系统

案例脚本（`init`、`run`、`status`、`evidence`）适合要保留追溯索引的任务。一道题、一个人、自己写一串互相读取结果的阶段脚本时可以不走它，但至少做到：每个出现在论文里的数字都能追到某个脚本和输出文件（一个 `run_all.sh` 或 README 逐条列出）；检查记录成带名字、结果和证据的 `checks.json`，用 `check_pdf.py --checks` 核对论文声称的检查数；最终材料的哈希写进清单。

## 建立案例

```bash
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" init \
  --name training-example --problem /绝对路径/problem.pdf \
  --data /绝对路径/data.csv --phase preparation
```

题目原文可先保存为本项目文件再传入；CLI 支持 PDF、TXT、Markdown。多个数据文件重复 `--data`。默认建在 `cases/<name>/`；名称自行根据任务取，不必为取名问用户。已有目录拒绝覆盖，接续时读取 `case.json` 与 `planning/tasks.md`。`--phase contest` 只记录比赛阶段，不能据此判断比赛时限或取得提交授权。

案例保存：`raw/` 原件只读副本、`planning/` 题意与任务记录、`audits/` 数据质量报告、`code/` 可复现处理与模型、`runs/` 每次独立运行结果。副本保留来源路径、哈希和字节数。CSV 使用显式编码（默认 UTF-8；可 `--encoding gb18030`），Excel 逐表检查；其他格式或大于 50 MB 的数据明确标记延后审计，选择流式或针对性处理。延后审计不等于已核验可用。PDF 即使提取到文字仍须查看原页。

## 内容理解不是脚本替代的

从原文识别子任务、变量、单位与交付物，写入 `planning/tasks.md`。对每个主要假设说明依据、失效现象及影响。脚本不自动读懂任意赛题，也不会替 助手写出真实模型；技能负责引导 助手选择、实现并设计独立检查。

读题后有合理基线就自主推进。保留选择理由和备选，不等待用户逐项确认。实际偏好或关键事实缺失才问，同时做可独立推进的工作。

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

每次生成新的运行目录，包含两个阶段的 stdout/stderr、命令、时间、代码与输入哈希、源码／参数快照、依赖源码快照、实际 Python／包版本、检查报告、输出哈希和状态。命令用固定 Python argv，不通过 shell 执行题目或数据里的命令。超时或失败记录保留，先查看根因再调整；不覆盖已跑出的结果。

`automatic-checks-passed` 只表示已记录的自动检查通过。`status` 可发现原始输入、代码、依赖或结果变化，标记过期证据；只用 `usable_automatic_evidence: true` 的结果准备论文，并继续评估现实机制与稳健性。检查本身是否有意义仍需 助手审核，不把脚本状态当成科学结论或用户已核验。`paper_ready` 默认 false，不自动授予论文完成状态。

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

清单应覆盖实际数值任务，每项 id 唯一，unit 必须写明（无量纲可用 dimensionless），result_pointer 使用 JSON Pointer 访问 results.json，例如 /forecast/0/value。检查名必须对应验证器实际生成的独立检查；名称唯一，不要关联到不相干的检查。单位是否正确及验证是否独立仍需助手审核。

```bash
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" evidence --case "$WORKSPACE/cases/example"
```

返回结果字段值、验证证据、运行回执与清单哈希，以及已链接数量。缺字段或缺检查返回 evidence-incomplete 并退出非零；最新运行失败或过期时拒绝，不能偷偷改用以前成功的运行。空清单拒绝，修改清单使旧运行失效，须重跑后再建索引。旧案例未提供清单时仍可 run/status，但不可声称已通过任务覆盖检查。

evidence-linked 只表示清单中的连接存在；不能证明所有任务已列入，也不能证明检查有意义、单位正确或论文已完成。论证、图表和格式等非数值要求仍在 tasks.md 中跟踪。该命令输出 JSON，不覆盖运行原件；如需保存，将标准输出写到工作项目的报告目录。
