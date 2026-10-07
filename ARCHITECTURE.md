# Praxis 的工作区与插件

Praxis 的目标是帮助个人或团队完成有证据的建模成果，适用于研究、课程、应用与比赛。赛事规则、实际人数和分工按 references/context-and-team.md 配置，单人策略为条件分支。按职责组织能力，而不是按上游项目、算法数量或目录大小组织。统一推理主线仍是 references/methods.md；插件只改变分发方式，不增加必经步骤。通用 Skill 与宿主插件不同：当前插件导出按 OpenAI 文档实现，不代表各宿主插件清单或安装方式通用。

## 一个入口，四个专项技能

按请求类型的触发条件拆分，而不是按流程阶段或上游项目拆分：`praxis` 管整题、团队与交接；`praxis-model`、`praxis-compute`、`praxis-verify`、`praxis-report` 各管一类单独出现的请求（建模、计算、验证审查、写作交付）。拆分的原因是单个描述无法同时让宿主正确触发“做完整题”与“只审查这份模型”，且专项请求不必加载整条主线。它们共用 references/methods.md 与同一任务记录，不增加必经步骤。

维护源中核心技能在仓库根目录，专项技能在 skills/praxis-*/SKILL.md，只含触发说明与指向核心参考的链接。直接安装根目录得到入口技能，由它按路径读取专项文件；导出插件时专项技能与 skills/praxis 并列，打包器把指向核心的链接从 ../../ 改为 ../praxis/，测试检查两种布局下链接都有效。

## 两个相互配合的部分

**可复用能力包**以 Agent Skills 标准为通用入口，宿主差异见 references/agent-compatibility.md。它保存 Skill、专业参考、脚本、数学封装、锁定依赖和许可。当前仓库是唯一维护源，兼容现有直接 Skill 安装；scripts/build_plugin.py 从明确的公开文件清单生成插件，不维护第二套源码。

**用户工作区**保存项目规则、已有唯一状态记录、题目、数据、案例、结果和报告。一个工作区可以容纳多个案例。pipeline 的 --workspace 指向这里；技能的 BUNDLE 始终从 SKILL.md 的真实位置确定。用户不必把项目迁入插件目录。

| 职责 | 当前实现 | 增加能力的条件 |
|---|---|---|
| 接续与协调 | Skill、任务模板、单人完成策略 | 实践中反复丢失依赖或优先级时，增加明确状态与可测试的协调辅助 |
| 分析与选择 | 同一推理主线、七项按需专业能力 | 新方法能解决已观察到的缺口，并说明输入、输出、适用条件与验收 |
| 执行 | pipeline、数据审计、数学封装、PDF 检查与冻结，以及 `praxis-tools` 提供的规划、网络、权重、排队、传染病、预测基线、敏感性和参考文献核对 | 重复且确定的操作才写成脚本或工具，并配独立答案的测试 |
| 证据 | 输入保全、运行快照、独立检查、过期检测、任务证据索引 | 新交付物无法追溯时扩展已有证据契约 |
| 写作与交付 | 写作指导、现有文档编辑工具、PDF 辅助 | 真实案例暴露重复步骤时自动化，并验证输出 |
| 分发 | 直接 Skill 安装、可导出的插件目录 | 本地插件安装与发现验证后，再考虑目录发布 |

## 插件导出

在仓库根目录运行：

```bash
uv run --locked python -m scripts.build_plugin --output outputs/praxis-plugin
```

输出目录必须尚不存在。导出包含：

```text
praxis-plugin/
  plugin.json
  mcp.json
  LICENSE
  README.md
  build-receipt.json
  skills/praxis-model/SKILL.md
  skills/praxis-compute/SKILL.md
  skills/praxis-verify/SKILL.md
  skills/praxis-report/SKILL.md
  skills/praxis/
    SKILL.md
    agents/
    references/
    scripts/
    modeling/
    examples/
    third_party/
    packaging/
    pyproject.toml
    uv.lock
    README.md
    LICENSE
    THIRD_PARTY_NOTICES.md
```

根 plugin.json 与 mcp.json 使用 Agent Plugins 1.0 格式，这一版规范只定义技能和 MCP 服务两类组件，二者都已提供；hooks、agents 等不在该版本范围内，不使用。skills/praxis 是自包含能力包。packaging/plugin.json 与 packaging/mcp.json 是维护源中的模板，仓库根目录本身仍是直接安装的 Skill，插件导出目录才是插件包。打包器仅复制明确公开资源，不含 .git、Python 环境、案例、原始数据或论文；保留许可与文件哈希收据，拒绝资源符号链接和覆盖已有目标。

在导出的能力包中显式运行 `uv sync --locked --project /absolute/path/to/praxis-plugin/skills/praxis` 准备 Python 环境，再用该环境执行脚本。插件下载不会替你安装这些依赖。插件目录的发现、安装及宿主可写路径兼容性需要单独验证；当前常规 Skill 安装保持可用。不要同时启用两个同名 Praxis 入口。

结构依据：[Agent Plugins 规范](https://agent-plugins.org/specification)与其 JSON Schema。mcp.json 用 `uv run --locked` 启动 `scripts.mcp_server`（工具清单与调用方式见 README），首次启动由 uv 按锁文件准备环境；另一个服务 `arxiv` 是第三方开源项目，固定版本，论文存到插件数据目录，来源与核验见 references/upstream-review.md。导出不是在任何插件目录上架。

## 工作流怎样逐步自动化

现有工作流的判断部分由助手按任务推进；pipeline 自动执行已审核模型和验证器，保留证据。下一层自动化应减少一次真实任务中的重复协调成本，例如从同一任务记录报告阻塞点，或从有效证据生成报告表格。先用一个完整案例验证，再推广。

只有需要稳定、结构化工具调用且现有脚本接口不足时才增加 MCP；只有交互检查明显优于现有记录时才增加界面。没有实际收益，不增加后台服务、流程引擎或固定多代理编排。工具运行成功与科学验证、人工确认分别记录，限时任务继续以基线、完整稿和交付余量为先。

## 开发状态（面向维护者）

| 状态 | 内容 |
|---|---|
| 已验证 | 本地 46 项测试；国赛、美赛两份历史题目案例及独立检查 |
| 已实现，待实战验证 | 团队与单人限时协调、能力交接、写作指导；四个专项技能被宿主单独发现与触发 |
| 未完成 | 其他宿主的完整案例、真实多人赛程、完整三天限时演练、宿主插件安装与发现 |

自动检查不证明模型适用于现实；日志不是完整 AI 对话；PDF 公式与版面须视觉核验。这些限制写在维护文档，不放进面向使用者的 README。
