<div align="center">

# Praxis

### 让 AI Agent 成为你的数学建模伙伴。

读懂题目，建好模型，把结果写成一份有依据的报告。

[![Agent Skills](https://img.shields.io/badge/Agent_Skills-portable-334155?style=flat-square)](https://agentskills.io/specification)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-526B55?style=flat-square)](LICENSE)

**简体中文** · [English](README.en.md)

[国赛 Demo](demos/cumcm-1998-a/README.md) · [美赛 Demo](demos/mcm-2016-a/README.md) · [快速开始](#快速开始) · [能力概览](#能力概览) · [Agent 兼容](#agent-兼容) · [验证与边界](#验证与边界)

</div>

[![Praxis：从问题分析、模型求解到验证与完整报告；点击进入国赛 Demo](demos/cumcm-1998-a/assets/overview-zh.png)](demos/cumcm-1998-a/README.md)

**[查看完整国赛 Demo →](demos/cumcm-1998-a/README.md)** · [直接阅读论文](demos/cumcm-1998-a/deliverables/paper.pdf)

---

拿到一道题，先分析什么、用什么模型、怎样判断结果可靠，往往比调用算法更难。Praxis 把这些工作连接起来，帮助个人或团队完成**模型、核验和报告**。你可以从题目和数据开始，也可以只让它审查模型、验证结果或改进论文。

题目要求、计算结果、验证记录和论文中的结论彼此对应。方法按题目选择，先做可解释的基线，再决定是否增加复杂度。研究、课程、实际应用和比赛都可以使用这套工作方式。

<table>
<tr>
<td width="33%"><strong>完成优先</strong><br>先形成基线和完整稿，再按剩余预算改善。</td>
<td width="33%"><strong>证据贯穿</strong><br>任务、结果、独立检查和论文位置相互对应。</td>
<td width="33%"><strong>按团队适配</strong><br>根据实际人数、能力和可用时间安排责任与交接。</td>
</tr>
</table>

## 一个完整案例，先看 Praxis 做出了什么

**1998 国赛 A 题《投资的收益和风险》：从费用门槛与风险约束，走到最优方案、独立核验和完整论文。**

[![国赛完整案例：风险收益曲线、代表结果与最优性论证](demos/cumcm-1998-a/assets/risk-return-zh.png)](demos/cumcm-1998-a/README.md)

<table>
<tr>
<td width="33%"><strong>16 页完整报告</strong><br>模型、结果、证明、图表与完整代码附录。</td>
<td width="33%"><strong>12 项模型检查</strong><br>费用分区穷举、解析上界及边界检查。</td>
<td width="33%"><strong>下载后可以复现</strong><br>两份交付文件，计算入口与证据一起开放。</td>
</tr>
</table>

资金 100 万元时，四资产在风险上限 1% 下得到净收益率 **21.90%**，十五资产在风险上限 10% 下得到 **33.53%**。这些是题目参数与所述风险定义下的模型结果；案例页解释条件、核验和资金规模论证。

**[看完整案例与报告预览 →](demos/cumcm-1998-a/README.md)** · [阅读论文](demos/cumcm-1998-a/deliverables/paper.pdf) · [下载支撑材料](demos/cumcm-1998-a/deliverables/supporting_materials.zip)

<details>
<summary><strong>展开看看报告：摘要与最优性证明</strong></summary>

<table>
<tr>
<td width="50%"><a href="demos/cumcm-1998-a/deliverables/paper.pdf"><img src="demos/cumcm-1998-a/assets/report-abstract.png" alt="摘要：定义、方法与量化结果" width="100%"></a></td>
<td width="50%"><a href="demos/cumcm-1998-a/deliverables/paper.pdf"><img src="demos/cumcm-1998-a/assets/report-proof.png" alt="证明：解析上界与资金规模条件" width="100%"></a></td>
</tr>
<tr><td>摘要：定义、方法与量化结果</td><td>证明：解析上界与资金规模条件</td></tr>
</table>

</details>

## 再看一个不同类型的问题：美赛的空间热模型

**2016 MCM A《A Hot Bath》：平均水温够高，远处的水就一定够暖吗？**

[![美赛案例：三维水温、策略与能量证据](demos/mcm-2016-a/assets/overview-zh.png)](demos/mcm-2016-a/README.md)

这次从可证明的理想模型出发，用三维热网络检查策略是否仍成立。19 页英文报告包含 17 项检查、16 个变化情景、网格诊断及一页使用者说明；最终提交目录只保留一份 PDF。热损与混合参数明确作为情景，结果不冒充实测。

**[查看完整美赛案例 →](demos/mcm-2016-a/README.md)** · [阅读英文论文](demos/mcm-2016-a/deliverables/7391856.pdf)

如果你也希望把建模推进到一份可核查的完整作品，欢迎 **Star Praxis**，或先用下面的方式试一次。

## 快速开始

### 1. 安装技能

以下示例适用于支持共享个人技能目录的本地 Agent，目标目录须尚不存在：

```bash
git clone https://github.com/WJSGZZ/praxis.git ~/.agents/skills/praxis
```

Claude Code 使用 `~/.claude/skills/praxis`。其他位置见 [Agent 兼容](#agent-兼容)；同一宿主只启用一个同名版本，已有安装不自动迁移。

### 2. 准备计算环境

执行脚本需要 **Python 3.12**、[uv](https://docs.astral.sh/uv/) 和宿主的本地文件／终端能力：

```bash
uv sync --project ~/.agents/skills/praxis --locked
```

仅使用分析方法，无需先准备 Python 环境。若安装位置不同，替换命令中的技能路径。

### 3. 在你的项目中使用

重载技能或重新开始会话，确认宿主加载了 Praxis，然后提出任务：

> 使用 Praxis 分析这道题和这些数据，选择合适的路线，推进模型实现、独立验证与报告。

也可以从一个明确的小任务开始：

> 审查我的模型：哪些假设没有依据，哪些结论还缺验证？

> 我们有三个人，请根据成员能力和可用时间安排任务，先完成一份完整报告。

**技能目录保存可复用能力，你的工作区保存题目、数据、案例和论文。** 程序负责执行与追溯，助手负责题意、选择和科学判断。

## 能力概览

| 能力 | 你能得到什么 | 入口 |
|---|---|---|
| 问题分析 | 原始要求、变量、约束、成功条件与任务依赖 | [统一方法](references/methods.md) |
| 模型与数学思想 | 基线、必要扩展、量纲、不变性、可辨识性与优化结构等条件指导 | [数学推理](references/mathematical-reasoning.md) |
| 数据与计算 | CSV／Excel 审计、原件保全、可复现运行；Sobol 与 TOPSIS 工具 | [数据计算](references/data-computing.md) |
| 独立验证 | 相称的对照与检查、失败记录、过期检测和数值任务证据索引 | [执行契约](references/automation.md) |
| 图表与写作 | 从有效结果形成图表、论证和报告，保持数字、单位与来源一致 | [图表](references/visualization.md) · [写作](references/writing.md) |
| 协调与交付 | 一／二／三人分工起点、责任与交接、限时简化路线和交付余量 | [团队适配](references/context-and-team.md) · [单人策略](references/solo-delivery.md) |

这些能力沿同一条主线调用，不要求每次走完全部环节。专业分工与共享交接内容见 [能力分工](references/capabilities.md)。

### 比赛是一个使用场景

国赛、美赛、课程和研究共用建模能力。参赛时，再分别核验该届赛事与学校／赛区要求，配置人数、交付语言、格式、附件、AI 披露和截止时间。

单人限时任务默认只给用户一个当前事项，边取得结果边写报告；多人任务按能力和依赖安排主责与复核。通用项目不套用赛事规则。

## Agent 兼容

同一份 `SKILL.md`、参考与 Python 工具，按宿主选择发现目录：

| Agent | 项目内目录 | 本地个人目录 |
|---|---|---|
| Codex | `.agents/skills/praxis` | `~/.agents/skills/praxis` |
| Claude Code | `.claude/skills/praxis` | `~/.claude/skills/praxis` |
| Gemini CLI | `.agents/skills/praxis` 或 `.gemini/skills/praxis` | `~/.agents/skills/praxis` 或 `~/.gemini/skills/praxis` |
| GitHub Copilot | `.github/skills/praxis` 或 `.agents/skills/praxis` | CLI：`~/.copilot/skills/praxis` 或 `~/.agents/skills/praxis` |
| Cursor | `.agents/skills/praxis` 或 `.cursor/skills/praxis` | `~/.agents/skills/praxis` 或 `~/.cursor/skills/praxis` |

**兼容证据：** 当前已有 Codex 协作与本地 Python 验证记录；五家官方格式与路径已核对，其他四家宿主、新发现路径、Windows 和远程环境仍待实际验证。自然语言调用是否加载技能，取决于宿主。

官方依据、专用调用方式和能力条件见 [跨 Agent 兼容说明](references/agent-compatibility.md)。

## 工具与插件

<details>
<summary><strong>命令行：在独立工作区建立案例</strong></summary>

以下命令以 POSIX shell 为例，路径需替换为实际位置：

```bash
BUNDLE="$HOME/.agents/skills/praxis"
WORKSPACE="/absolute/path/to/your/project"

"$BUNDLE/.venv/bin/python" "$BUNDLE/scripts/pipeline.py" \
  --workspace "$WORKSPACE" init \
  --name example \
  --problem "$WORKSPACE/problem.pdf" \
  --data "$WORKSPACE/data.csv"
```

助手写并审核案例中的 `model.py` 和 `validate.py` 后，才执行 `run`。脚本不自行理解任意题目或生成模型。数据、案例与输出默认不进入 Git，项目规则由工作区提供。

完整接口见 [执行契约](references/automation.md)。

</details>

<details>
<summary><strong>插件：从同一维护源导出能力包</strong></summary>

在仓库根目录运行，输出目录须尚不存在：

```bash
uv run --locked python -m scripts.build_plugin --output outputs/praxis-plugin
```

导出包含 Skill、脚本、参考、锁定依赖和来源许可。环境需要显式准备，用户材料继续保存在工作区。

通用 Skill 是跨宿主入口；当前插件导出按 OpenAI 插件格式组织，不能等同于所有宿主的插件安装方式。目录导出已实现，宿主插件安装／发现尚未验证，也未在官方插件目录上架。

结构与扩展条件见 [架构说明](ARCHITECTURE.md)。

</details>

## 验证与边界

| 状态 | 当前证据 |
|---|---|
| **已验证** | 本地工具累计 45 项测试通过，涵盖解析答案、输入保护、失败与过期证据、PDF 辅助及自包含插件导出；有合成演练与完整国赛历史题目案例 |
| **已实现，待实战验证** | 场景与团队适配、单人限时协调、专业能力交接与写作指导 |
| **尚未完成** | 其他 Agent 完整案例实测、真实多人赛程、完整三天限时演练及宿主插件安装验证 |

自动检查通过不证明模型适用于现实；权重情景份额不是客观概率；日志不是完整 AI 对话。任务清单的完整性须对照原题审查，PDF 的公式、图表与版面仍需视觉核验。大文件或不支持格式会明确延后审计。

Praxis 不承诺任意题目都能自动完成、获奖或无人审核提交。

<details>
<summary><strong>开发与演练命令</strong></summary>

```bash
uv sync --locked --group dev
uv run --locked python -m pytest -q
uv run --locked python -m examples.decision_sensitivity_demo
uv run --locked python -m examples.structural_reasoning_demo
```

测试通过记录与跨宿主／真实任务的行为验证分别表述。

</details>

## 来源与许可

本地原创代码与文档采用 [MIT](LICENSE)。工作流参考 MathModelHub，Sobol 与 TOPSIS 分别使用 SALib 和 pyMCDM；实际复用范围、上游许可与取舍见 [第三方声明](THIRD_PARTY_NOTICES.md) 和 [审查记录](references/upstream-review.md)。报告中实际使用的方法、数据与工具仍需在使用处引用原始来源。

首页与案例图片使用同一套 [Praxis 展示语言](design/README.md)，颜色、字体层级和版式由共享配置维护。
