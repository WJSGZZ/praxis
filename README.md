# Praxis

**一个面向支持 Agent Skills 的 AI Agent 的数学建模能力包：把问题和数据推进到可解释的模型、独立验证和可追溯报告。** 支持通用建模、课程项目与比赛准备，不限定某个赛事。

Praxis 围绕同一任务组织五个环节：明确问题、形成路线、取得结果、判断证据、完成回答。模型与验证一起选择，失败按原因返回对应环节；方法按任务条件调用，多个模型只有输入输出关系明确且确有用途时才组合。工具负责原始输入、审计、运行与证据追溯，助手负责含义、选择与科学判断。工作流参考 MathModelHub，Sobol 和 TOPSIS 分别使用 SALib 与 pyMCDM；复用范围见 [来源与许可](THIRD_PARTY_NOTICES.md)，新增工作流对照与改进见 [审查记录](references/upstream-review.md)。

## 安装与使用

Praxis 使用开放的 `SKILL.md` 格式，建模主线、参考和 Python 工具不依赖某一家模型。脚本执行需要 Python 3.12、[uv](https://docs.astral.sh/uv/) 以及宿主的本地文件／终端能力；仅使用分析方法不必先准备 Python 环境。

按宿主选择安装位置（`praxis` 是技能目录）：

| 宿主 | 项目内目录 | 本地个人目录 | 当前证据 |
|---|---|---|---|
| Codex | `.agents/skills/praxis` | `~/.agents/skills/praxis` | 当前 Codex 会话已使用；新发现路径依据官方文档，未重新安装验证 |
| Claude Code | `.claude/skills/praxis` | `~/.claude/skills/praxis` | 官方格式／路径已核对，宿主实测待完成 |
| Gemini CLI | `.agents/skills/praxis` 或 `.gemini/skills/praxis` | `~/.agents/skills/praxis` 或 `~/.gemini/skills/praxis` | 官方格式／路径已核对，宿主实测待完成 |
| GitHub Copilot | `.github/skills/praxis` 或 `.agents/skills/praxis` | CLI 可用 `~/.copilot/skills/praxis` 或 `~/.agents/skills/praxis` | 官方格式／路径已核对，不同运行表面仍需实测 |
| Cursor | `.agents/skills/praxis` 或 `.cursor/skills/praxis` | `~/.agents/skills/praxis` 或 `~/.cursor/skills/praxis` | 官方格式／路径已核对，宿主实测待完成 |

例如安装到共享个人目录（目标目录必须尚不存在）：

```bash
git clone https://github.com/WJSGZZ/praxis.git ~/.agents/skills/praxis
uv sync --project ~/.agents/skills/praxis --locked
```

Claude Code 使用表中的 `.claude` 路径。同一宿主只启用一个同名版本；已有 Codex 旧安装不自动迁移。重载技能或重新开始会话后，在工作项目中说：

> 使用 Praxis 分析这道题和这些数据，选择合适的路线，推进模型实现、独立验证与报告。

也可以只要求读题、比较路线或审查已有模型。自然语言请求不保证宿主必定加载技能，应核对实际加载；专用调用入口随宿主而异。技能目录保存工具，案例保存到当前工作项目。官方来源、能力条件、调用差异和验证边界见 [跨 Agent 兼容说明](references/agent-compatibility.md)。

命令行建立案例的例子：

```bash
BUNDLE="$HOME/.agents/skills/praxis"
WORKSPACE="/absolute/path/to/your/project"
"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" --workspace "$WORKSPACE" init   --name example --problem "$WORKSPACE/problem.pdf" --data "$WORKSPACE/data.csv"
```

助手按 [执行契约](references/automation.md) 写并审核案例内的 model.py 与 validate.py 后，才运行 `run`；命令行脚本本身不会自动理解问题或生成模型。数据、案例与输出默认不进入 Git。项目规则与比赛规则由工作项目提供。

## 工作区与插件

同一份维护源既支持通用 Skill 安装，也能导出含 Skill、脚本、锁定依赖和许可的 portable 插件包：

```bash
uv run --locked python -m scripts.build_plugin --output outputs/praxis-plugin
```

导出目录必须尚不存在。题目、数据、案例与论文继续保存在用户工作区；环境需要显式准备。通用 Skill 是跨宿主入口，当前插件导出按 OpenAI 插件格式组织，各宿主插件安装不能直接等同。当前已支持目录导出，尚未验证宿主插件安装／发现，也未在官方插件目录上架。架构、职责和后续扩展条件见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 方法与工具的分工

统一推理主线在 [methods.md](references/methods.md)，各环节更新同一份任务记录。定义歧义的例子按需读取；算法封装按输入条件调用；运行与证据脚本服务于主线，不决定题意或结论。用户只要求分析就完成分析，完整建模才推进至实际结果与报告。

能力按实际需求分为问题分析、文献来源、模型设计、数据计算、独立验证、图表表达、论文写作。各领域有对应专业参考，统一交接任务 ID、有效结果与结论边界；见 [能力分工](references/capabilities.md)。当前是技能内部的按需指导，并非自动多代理系统。

## 场景与团队适配

Praxis 面向数学建模本身，比赛是应用场景之一。先了解实际赛事／届次、人数、成员能力和可用时间，再安排任务主责、复核与交接；一、二、三人均有起始策略，通用项目不套赛事规则。全国规则与学校要求分别核验，交付语言、格式、附件、AI 披露和截止也按实际规范配置。见 [context-and-team.md](references/context-and-team.md)。当前是协调指导，尚未经过真实多人完整赛程验证。

## 单人限时完成

当你独自推进、时间紧且首先要求完成时，Praxis 负责协调优先级、依赖和下一步，默认只给一个当前用户事项。先做必需任务的基线，边产生结果边写报告，尽早形成完整版本；复杂扩展按剩余预算决定，末段留给核对与交付。具体策略见 [solo-delivery.md](references/solo-delivery.md)。这是按需执行的指导，尚未经过完整三天演练验证，也不是后台倒计时或自动排程。

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

## 商业使用与服务

本地原创部分的 MIT 许可允许商业使用与销售副本，分发时保留版权和许可；依赖及第三方材料继续遵守各自许可。依据见 [MIT 原文](https://opensource.org/license/mit) 和 THIRD_PARTY_NOTICES.md。

公开仓库可供他人获取和合法复用。可收费的服务可以是安装配置、原创教学材料、赛前或非竞赛完整演练、持续维护与使用支持；应明确具体交付，不把公开地址本身描述成独占源码权益。当前没有收费产品、定价或经验证的服务效果。
