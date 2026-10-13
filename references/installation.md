# 安装 Praxis

[English](installation.en.md)

可以直接下载已发布的宿主安装包，或从源码导出，再使用宿主的安装入口。每种包共用全部专业技能、数学工具和证据工作流；差异只在清单、路径变量和安装方式，不依赖官方商店收录。

## 下载已发布的安装包

[0.8.1 Release](https://github.com/WJSGZZ/praxis/releases/tag/v0.8.1) 提供 [Codex](https://github.com/WJSGZZ/praxis/releases/download/v0.8.1/praxis-0.8.1-codex.zip)、[Claude](https://github.com/WJSGZZ/praxis/releases/download/v0.8.1/praxis-0.8.1-claude.zip)、[Gemini](https://github.com/WJSGZZ/praxis/releases/download/v0.8.1/praxis-0.8.1-gemini.zip)、[Copilot](https://github.com/WJSGZZ/praxis/releases/download/v0.8.1/praxis-0.8.1-copilot.zip)、[Cursor](https://github.com/WJSGZZ/praxis/releases/download/v0.8.1/praxis-0.8.1-cursor.zip) 和 [portable](https://github.com/WJSGZZ/praxis/releases/download/v0.8.1/praxis-0.8.1-portable.zip) ZIP；用同页 [SHA256SUMS.txt](https://github.com/WJSGZZ/praxis/releases/download/v0.8.1/SHA256SUMS.txt) 核对所选文件。PowerShell 可用 `Get-FileHash 文件名.zip -Algorithm SHA256`，macOS 可用 `shasum -a 256 文件名.zip`，Linux 可用 `sha256sum 文件名.zip`，逐字比较该文件的64位摘要。

解压到新目录后，使用下方宿主对应的安装命令，跳过 clone 与 build_plugin。安装路径是含宿主清单的包根目录，计算环境位于其中的 `skills/praxis`。包不携带Python环境；运行工具仍需uv与锁定依赖。固定Release与后续main改动分别保留，下载0.8.1不会自动带入未发布修复。

## 从源码导出

先安装 Git、[uv](https://docs.astral.sh/uv/)，再获取仓库：

```bash
git clone https://github.com/WJSGZZ/praxis.git
cd praxis
```

以下导出命令均在这个仓库中执行，输出目录须尚不存在。uv 按锁文件准备 Python 3.12 与依赖。宿主启动工具时也要能找到 uv。

## Codex

```bash
uv run --locked python -m scripts.build_plugin --host codex --output ../praxis-dist/codex/praxis
codex plugin marketplace add /absolute/path/to/praxis-dist/codex/praxis --json
codex plugin add praxis@praxis-local --json
```

将 `/absolute/path/to` 替换为实际绝对路径。导出包自带 `.agents/plugins/marketplace.json`，不必手写或覆盖个人 marketplace。CLI 不提供这些命令时，使用该版本支持的本地 marketplace 安装界面。重载后确认 `praxis@praxis-local` 及所有 `praxis:*` 技能；此前通过个人 marketplace 安装的同一插件可能显示为 `praxis@personal`。

依据：[OpenAI 插件打包](https://developers.openai.com/plugins/build/plugins)。

## Claude Code

```bash
uv run --locked python -m scripts.build_plugin --host claude --output ../praxis-dist/claude/praxis
claude plugin marketplace add /absolute/path/to/praxis-dist/claude/praxis
claude plugin install praxis@praxis-local
```

可先用 `claude plugin validate /absolute/path/to/praxis-dist/claude/praxis` 检查包；临时试用可用 `claude --plugin-dir /absolute/path/to/praxis-dist/claude/praxis`。清单位于 `.claude-plugin/`，工具使用 Claude 的根目录和数据目录变量。插件技能的调用名称由宿主加命名空间，与直接安装技能的 `/praxis` 不同，以会话列出的名称为准。

依据：[Claude 插件清单](https://code.claude.com/docs/en/plugins-reference)、[marketplace](https://code.claude.com/docs/en/plugin-marketplaces)。

## Gemini CLI

```bash
uv run --locked python -m scripts.build_plugin --host gemini --output ../praxis-dist/gemini/praxis
gemini extensions install /absolute/path/to/praxis-dist/gemini/praxis
gemini extensions list
```

使用原生 `gemini-extension.json`，由扩展加载全部专业技能及 `praxis-tools`，路径使用 `${extensionPath}`。安装后重启 CLI 会话。

依据：[Gemini 扩展参考](https://geminicli.com/docs/extensions/reference/)。

## GitHub Copilot CLI

```bash
uv run --locked python -m scripts.build_plugin --host copilot --output ../praxis-dist/copilot/praxis
copilot plugin install /absolute/path/to/praxis-dist/copilot/praxis
copilot plugin list
```

使用 Copilot CLI 支持的通用 Agent Plugins 根清单与 MCP 格式。这里指 CLI 插件，不等于所有 Copilot 编辑器和云端功能都自动接入。

依据：[Copilot CLI 插件参考](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference)。

## Cursor

```bash
uv run --locked python -m scripts.build_plugin --host cursor --output ~/.cursor/plugins/local/praxis
```

重启 Cursor 或执行 **Developer: Reload Window**，在 **Customize** 检查技能和 MCP。使用真实目录，不能用指向该本地插件目录外的软链接。组织管理的环境需允许 Local Plugin Imports。适配包使用 `${CURSOR_PLUGIN_ROOT}`，解决通用变量未展开的问题。

依据：[Cursor 本地插件](https://cursor.com/docs/plugins)、[MCP 路径变量](https://cursor.com/docs/reference/plugins)。

## 工具、更新与排查

所有包都包含全部专业技能和 `praxis-tools`。通用、Codex、Claude 和 Copilot 包另带固定版本的 arXiv 服务；Gemini、Cursor 包不自动配置它，因为其存储目录变量不同。核心工具中的 OpenAlex、Unpaywall、Crossref 检索不受此影响；需要额外 arXiv 服务时按宿主配置外部存储路径，勿写入安装目录。

更新时先更新源码，再导出到新的目录，通过宿主更新或重新安装。直接修改源码不保证安装缓存同步；不要手改缓存，不覆盖旧导出目录或用户配置。需要退回旧版时，保留旧源码 ref 和原导出包。

重载后检查三件事：Praxis 出现在插件／扩展列表；全部专业技能可发现；`praxis-tools` 能响应。遇到问题先看宿主 MCP 日志中的 uv、Python 和路径错误。可从任意目录检查底层服务（替换路径）：

```bash
uv run --locked --directory /absolute/path/to/plugin/skills/praxis python -m scripts.mcp_server --list
```

这只验证工具服务，不代表宿主加载成功。完整计算和写入权限由宿主控制，题目、数据、论文与运行输出放在用户工作区。

## Windows PowerShell

使用已解压包中的实际路径；题目、数据与产物保存在独立工作区。以下uv入口无需直接调用Windows的 `.venv/Scripts/python.exe`，从无关目录也可运行：

```powershell
$Bundle = "C:/Tools/praxis/skills/praxis"
$Workspace = "C:/Modeling/my project"
uv sync --locked --project "$Bundle"
uv run --locked --directory "$Bundle" python -m scripts.mcp_server --list
uv run --locked --project "$Bundle" python "$Bundle/scripts/pipeline.py" --workspace "$Workspace" status --case "$Workspace/cases/example"
```

先用 `init` 建立案例再查询实际case路径；全部子命令见[数值工作流](automation.md)。POSIX终端也可使用相同uv参数。`--project`选择依赖环境，不改变Python模块搜索的当前目录；绝对脚本路径可从任意目录调用，使用 `python -m scripts...` 时应传 `--directory`。宿主MCP清单通过自己的根目录变量设置工作目录，不能把只指定 `--project` 的裸module命令当作安装失败。

## 仅安装技能

不需要 MCP 的宿主可以保留轻量入口：

```bash
git clone https://github.com/WJSGZZ/praxis.git ~/.agents/skills/praxis
```

Claude Code 可改为 `~/.claude/skills/praxis`；其他发现目录见 [兼容说明](agent-compatibility.md)。这是一种技能安装方式，需要计算时通过终端执行同一套脚本。同一宿主不要同时启用同名插件与技能副本。

## 新电脑上的论文排版

数学计算与 MCP 不要求安装 TeX。需要生成正式 PDF 时，安装 [Tectonic 0.17.0 官方二进制](https://github.com/tectonic-typesetting/tectonic/releases/tag/tectonic%400.17.0)，选择与系统和架构匹配的版本；Windows 使用 `tectonic.exe`，macOS／Linux 使用 `tectonic`。将它加入 PATH，或给编译命令传入 `--compiler "实际可执行文件路径"`。先用 `tectonic --version` 确认版本，不能用另一版本成功运行替代核验。

在仓库根目录编译；从安装包使用时进入其 `skills/praxis` 目录，论文与输出仍放在用户工作区。以下相对路径按实际位置替换，输出目录必须尚不存在：

```bash
uv run --locked python -m scripts.paper_template main.tex --contest cumcm --compile --output-directory outputs/build-001
```

美赛改为 `--contest mcm`。Windows 可追加 `--compiler "C:/Tools/tectonic/tectonic.exe"`，其他系统同样支持显式路径。首次运行需联网获取固定 TeX 资源；中文字体随资源提供，无需复制 Mac 系统字体。版本、资源包与字体哈希不符时停止，不自动更换排版环境。输出包含 PDF、日志和 `.build.json`；逐页检查后，按[写作流程](writing.md)携带构建记录冻结最终文件。

`portable-typesetting` 在 Windows、Linux、macOS 的干净 CI 环境编译文档并比较版面，可用于没有相应电脑时核查排版链。它不代表每一种 Agent 宿主都已完成桌面安装实测。
