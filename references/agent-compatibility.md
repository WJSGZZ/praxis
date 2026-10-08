# 跨 Agent 使用与能力边界

Praxis 作为 Agent 插件维护：技能负责建模判断与协作，MCP／Python 脚本负责确定性执行，证据工作流连接任务、运行、独立检查与报告。可移植核心仍采用 Agent Skills 格式；不同宿主复用同一份方法和工具，不另造一套建模逻辑。仅需技能时可单独接入。

## 实际能力优先于品牌

- **读取与编辑文件**：能读取技能相对路径和用户工作区，接续已有规则；BUNDLE 根据实际 SKILL.md 所在目录解析，不写死 ~/.codex。若无法读取本地资源，让用户提供任务必要内容，并明确缺失。
- **终端与 Python**：运行工具需 Python 3.12、uv 与依赖环境。遵守宿主实际权限；无终端时可分析／设计，不声称模型已运行、检查通过或证据已保存。
- **研究与图像**：按任务用宿主可用搜索、PDF／图像查看工具。只能提取文本时，图、公式与版面仍未视觉核验。
- **文档**：有编辑器／编译器则沿用；没有则使用已可用的文件与编译方式，缺失就说明未验证。Codex 内置 LaTeX 编译接口只是可选实现，不是通用技能要求。
- **协作**：职责与交接不依赖子代理。当前宿主没有并行代理时，同一助手顺序推进。不能把分工建议冒充已联系真人成员。

scripts/pipeline.py 使用标准 Python 与文件接口，不调用某家 Agent 的 SDK。references/automation.md 中命令以 POSIX shell 为例；Windows 可用 `uv run --locked --project <BUNDLE> python <BUNDLE>/scripts/pipeline.py --workspace <WORKSPACE> ...` 避免依赖 .venv/bin 路径。本项目尚未做 Windows 实测。

## 发现与调用

安装目录见 README 表格；目标文件夹名应为 praxis。确认宿主实际加载了这份 SKILL.md，再执行。Codex 可用 `$praxis`，Claude Code 的直接技能可用 `/praxis`；自然语言“使用 Praxis …”可作跨宿主请求，但自动选择与交互入口仍取决于宿主。

agents/openai.yaml 仅提供 Codex 的展示与调用元数据。通用规则放在 SKILL.md 与 references，不依赖该文件被其他宿主理解，不加入专有动态插值或固定工具授权。packaging/plugin.json 与 packaging/mcp.json 是 Agent Plugins 1.0 导出的来源；各宿主自己的插件目录与清单格式可能不同，宿主不读取该格式时，用技能目录加命令行工具（`python -m scripts.mcp_server --call`）。

共享个人目录适用于本地宿主，不能据此声称云端会话或远程机器自动拥有本地文件。远程环境需在那里安装技能并准备执行依赖；仍以实际文件／终端能力判断可执行范围。

## 依据与验证状态

2026-10-07 已核对以下第一手文档；路径与功能可能随宿主版本变化：

- [Agent Skills 规范](https://agentskills.io/specification)：SKILL.md、名称与描述、相对资源和脚本结构。
- [Codex 技能文档](https://developers.openai.com/codex/skills)：.agents/skills 的项目和用户入口；现有环境的旧入口不强制迁移。
- [Claude Code 技能文档](https://code.claude.com/docs/en/skills)：.claude/skills 的项目／个人入口和直接技能调用。
- [Gemini CLI 技能文档](https://geminicli.com/docs/cli/skills/)：.gemini/skills 与 .agents/skills 别名。
- [GitHub Copilot 技能文档](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)：项目 .github/.claude/.agents 技能目录及个人入口；支持范围以具体表面为准。
- [Cursor 技能文档](https://cursor.com/docs/skills)：.cursor/skills 与 .agents/skills；本地个人技能不会自动复制到所有远程环境。

已存在 Codex 协作与本地 Python 验证记录；其他宿主目前为文档与格式支持待实测，不能称五种 Agent 都已跑通。后续实测记录宿主版本、真实加载路径、技能是否触发、独立案例运行与交付结果；发现差异修宿主适配，不复制整套核心方法。
