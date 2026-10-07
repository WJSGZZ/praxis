# Praxis

**一个用于 Codex 的数学建模 Skill：把问题和数据推进到可解释的模型、独立验证和可追溯报告。** 支持通用建模、课程项目与比赛准备，不限定某个赛事。

Praxis 围绕同一任务组织五个环节：明确问题、形成路线、取得结果、判断证据、完成回答。模型与验证一起选择，失败按原因返回对应环节；方法按任务条件调用，多个模型只有输入输出关系明确且确有用途时才组合。工具负责原始输入、审计、运行与证据追溯，助手负责含义、选择与科学判断。工作流参考 MathModelHub，Sobol 和 TOPSIS 分别使用 SALib 与 pyMCDM；复用范围见 [来源与许可](THIRD_PARTY_NOTICES.md)，新增工作流对照与改进见 [审查记录](references/upstream-review.md)。

## 安装与使用

需要 Python 3.12、[uv](https://docs.astral.sh/uv/) 与支持本地 skills 的 Codex。将仓库克隆到技能目录（该目录必须尚不存在）：

```bash
git clone https://github.com/WJSGZZ/praxis.git ~/.codex/skills/praxis
uv sync --project ~/.codex/skills/praxis --locked
```

让 Codex 重新发现技能后，在你的工作项目中说：

> 用 $praxis 分析这道题和这些数据，选择合适的路线，推进模型实现、独立验证与报告。

也可以只要求读题、比较路线或审查已有模型，不必每次运行全套。技能目录保存工具，案例保存到当前工作项目；不会把新题目写入技能安装目录。

命令行建立案例的例子：

```bash
BUNDLE="$HOME/.codex/skills/praxis"
WORKSPACE="/absolute/path/to/your/project"
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" init   --name example --problem "$WORKSPACE/problem.pdf" --data "$WORKSPACE/data.csv"
```

助手按 [执行契约](references/automation.md) 写并审核案例内的 model.py 与 validate.py 后，才运行 `run`；命令行脚本本身不会自动理解问题或生成模型。数据、案例与输出默认不进入 Git。项目规则与比赛规则由工作项目提供。

## 方法与工具的分工

统一推理主线在 [methods.md](references/methods.md)，各环节更新同一份任务记录。定义歧义的例子按需读取；算法封装按输入条件调用；运行与证据脚本服务于主线，不决定题意或结论。用户只要求分析就完成分析，完整建模才推进至实际结果与报告。

## 已实现与限制

- 任务拆解、机制与基线选择指导，见 [方法参考](references/methods.md)。
- CSV 与 Excel 全工作表审计；PDF 文本提取，大文件或不支持格式明确延后审计。
- 每次运行保存源码、参数、输入和输出哈希、环境版本、日志及独立检查。过期证据会被标记。
- 数学结构与思想的条件指导：量纲／不变性、参数可辨识性、优化结构与证书、概率生成检查、因果识别。部分已用现有库演练，专门库仅留作备选，见 [数学思想](references/mathematical-reasoning.md)。
- 定义审查与跨任务一致性指导；`pipeline evidence` 将已记录的数值任务链接到结果字段与独立检查，拒绝过期运行，暴露遗漏。清单的完整性仍须对照原题审核。
- 两个数学工具：独立均匀输入的 Sobol 敏感性，以及具有明确权重和成本／收益方向的 TOPSIS 方案评价。
- 通用 PDF 基础检查与字节一致的冻结副本。PDF 字体、图表、公式与布局仍须视觉审核。

自动检查通过不证明模型适用于现实；稳定性情景份额不等于客观概率；程序日志不等于完整 AI 对话。本项目是初版工具，已用合成案例与解析答案测试，尚未证明任意真实任务都能自动完成，也不承诺获奖或无人审核提交。

## 开发验证

```bash
uv sync --locked --group dev
uv run --locked python -m pytest -q
uv run --locked python -m examples.decision_sensitivity_demo
uv run --locked python -m examples.structural_reasoning_demo
```

## 许可

本地编写的代码与文档采用 MIT；上游及依赖保留自己的许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。研究报告中实际使用的方法、数据与工具仍需在使用处引用原始来源。
