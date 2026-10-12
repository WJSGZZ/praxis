# Install Praxis

[简体中文](installation.md)

Download a released package for your host or build one from source, then use that host's plugin installer. Each target includes the same fifteen skills and mathematical engine. The adapter supplies the host metadata and paths; no marketplace listing is required.

## Released packages

The [0.6.0 release](https://github.com/WJSGZZ/praxis/releases/tag/v0.6.0) contains ZIPs for [Codex](https://github.com/WJSGZZ/praxis/releases/download/v0.6.0/praxis-0.6.0-codex.zip), [Claude](https://github.com/WJSGZZ/praxis/releases/download/v0.6.0/praxis-0.6.0-claude.zip), [Gemini](https://github.com/WJSGZZ/praxis/releases/download/v0.6.0/praxis-0.6.0-gemini.zip), [Copilot](https://github.com/WJSGZZ/praxis/releases/download/v0.6.0/praxis-0.6.0-copilot.zip), [Cursor](https://github.com/WJSGZZ/praxis/releases/download/v0.6.0/praxis-0.6.0-cursor.zip), and [portable use](https://github.com/WJSGZZ/praxis/releases/download/v0.6.0/praxis-0.6.0-portable.zip). Compare your chosen ZIP's SHA-256 with its entry in [SHA256SUMS.txt](https://github.com/WJSGZZ/praxis/releases/download/v0.6.0/SHA256SUMS.txt): use `Get-FileHash filename.zip -Algorithm SHA256` in PowerShell, `shasum -a 256 filename.zip` on macOS, or `sha256sum filename.zip` on Linux.

Extract into a fresh directory. Skip cloning and building, and use the matching installation command below with the extracted bundle root. The computational resource is its `skills/praxis` directory. These packages include the locked Python project, not a Python environment; tools still need uv and its prepared dependencies. A fixed release remains separate from subsequent changes on main.

## Build from source

Install Git and [uv](https://docs.astral.sh/uv/), then clone the repository:

```bash
git clone https://github.com/WJSGZZ/praxis.git
cd praxis
```

Run the build commands below from this checkout. Each destination must be new. uv prepares Python 3.12 and the locked dependencies; it must also be available to the agent when the MCP server starts. Replace `/absolute/path/to` with your actual location.

## Codex

```bash
uv run --locked python -m scripts.build_plugin --host codex --output ../praxis-dist/codex/praxis
codex plugin marketplace add /absolute/path/to/praxis-dist/codex/praxis --json
codex plugin add praxis@praxis-local --json
```

The export includes its local marketplace catalog, so existing personal configuration need not be edited. If your CLI lacks these commands, use its supported local marketplace interface. Reload and look for `praxis@praxis-local` and fifteen `praxis:*` skills. An earlier personal-marketplace install may instead be identified as `praxis@personal`.

Reference: [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins).

## Claude Code

```bash
uv run --locked python -m scripts.build_plugin --host claude --output ../praxis-dist/claude/praxis
claude plugin marketplace add /absolute/path/to/praxis-dist/claude/praxis
claude plugin install praxis@praxis-local
```

Run `claude plugin validate /absolute/path/to/praxis-dist/claude/praxis` to check the package. For a session-only trial, use `claude --plugin-dir /absolute/path/to/praxis-dist/claude/praxis`. This target supplies the Claude manifest and root/data variables. Plugin skills are namespaced; use the names shown by the session rather than assuming the standalone `/praxis` name.

References: [manifest](https://code.claude.com/docs/en/plugins-reference), [marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).

## Gemini CLI

```bash
uv run --locked python -m scripts.build_plugin --host gemini --output ../praxis-dist/gemini/praxis
gemini extensions install /absolute/path/to/praxis-dist/gemini/praxis
gemini extensions list
```

Gemini loads the skills and core MCP service through `gemini-extension.json`. Resource paths use `${extensionPath}`. Restart the CLI session after installation.

Reference: [extension reference](https://geminicli.com/docs/extensions/reference/).

## GitHub Copilot CLI

```bash
uv run --locked python -m scripts.build_plugin --host copilot --output ../praxis-dist/copilot/praxis
copilot plugin install /absolute/path/to/praxis-dist/copilot/praxis
copilot plugin list
```

This target uses Copilot CLI's Agent Plugins support. It does not automatically configure every Copilot editor integration or cloud environment.

Reference: [CLI plugin reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference).

## Cursor

```bash
uv run --locked python -m scripts.build_plugin --host cursor --output ~/.cursor/plugins/local/praxis
```

Restart Cursor or run **Developer: Reload Window**, then inspect skills and MCP in **Customize**. Build into a real directory; Cursor skips local-plugin symlinks pointing outside that directory tree. Managed environments must permit Local Plugin Imports. The adapter substitutes `${CURSOR_PLUGIN_ROOT}` because Cursor does not expand the portable root variable.

References: [local plugins](https://cursor.com/docs/plugins), [MCP variables](https://cursor.com/docs/reference/plugins).

## Runtime and maintenance

Every target includes all fifteen skills and `praxis-tools`. Portable, Codex, Claude and Copilot packages additionally declare the pinned arXiv server. Gemini and Cursor leave that optional integration out because their storage variables differ; configure an external storage location separately if needed. OpenAlex, Unpaywall and Crossref remain available through the core service.

To update, fetch the source, export to a fresh destination and update or reinstall through your host. Do not patch an installation cache or overwrite user configuration. Keep the old source ref and export if you need a rollback.

After reloading, check the plugin list, skill discovery and MCP connection separately. Startup failures usually show up in the host's MCP logs as missing uv, Python or resource paths. A direct service diagnostic is:

```bash
uv run --locked --directory /absolute/path/to/plugin/skills/praxis python -m scripts.mcp_server --list
```

This checks the service rather than host loading. Host permissions still apply. Store problems, data, papers and run outputs in your project workspace.

## Windows PowerShell

Point these variables at your extracted computational resource and a separate user workspace. uv selects the environment without requiring a platform-specific virtualenv executable path, including when your current directory is elsewhere:

```powershell
$Bundle = "C:/Tools/praxis/skills/praxis"
$Workspace = "C:/Modeling/my project"
uv sync --locked --project "$Bundle"
uv run --locked --directory "$Bundle" python -m scripts.mcp_server --list
uv run --locked --project "$Bundle" python "$Bundle/scripts/pipeline.py" --workspace "$Workspace" status --case "$Workspace/cases/example"
```

Create a case with `init` before requesting its status; see the [runtime contract](automation.md) for subcommands. The uv arguments also work in POSIX shells. `--project` selects dependencies but leaves Python's module-search working directory unchanged: use an absolute script path, or use `--directory` with `python -m scripts...`. Host manifests already select the bundle's working directory.

## Skills-only option

If MCP is unnecessary, install the entry skill and its resources:

```bash
git clone https://github.com/WJSGZZ/praxis.git ~/.agents/skills/praxis
```

For Claude Code, use `~/.claude/skills/praxis`. Other discovery paths are in [host compatibility](agent-compatibility.md). Computation remains available through terminal scripts. Avoid enabling a standalone copy alongside the plugin in the same host.

## Typesetting on a new machine

The mathematical tools and MCP server run without TeX. For a final paper build, obtain the binary for your OS and architecture from the [official Tectonic 0.17.0 release](https://github.com/tectonic-typesetting/tectonic/releases/tag/tectonic%400.17.0). Put `tectonic` on PATH (`tectonic.exe` on Windows), or supply its location with `--compiler`. Check `tectonic --version` before building.

Run the following from the repository root, or from `skills/praxis` in an exported plugin. Adjust the source and output paths to your own workspace; the destination must be new:

```bash
uv run --locked python -m scripts.paper_template main.tex --contest cumcm --compile --output-directory outputs/build-001
```

Use `--contest mcm` for an MCM paper. An explicit Windows path can be passed as `--compiler "C:/Tools/tectonic/tectonic.exe"`; the same option accepts macOS and Linux paths. The first build needs network access to fetch the pinned TeX resources, including Chinese fonts. Compiler, bundle or font mismatches stop the build rather than selecting a substitute. Keep the PDF, log and `.build.json` together, inspect every page, then follow the [writing workflow](writing.md) to freeze a final copy.

The `portable-typesetting` workflow runs on clean Windows, Linux and macOS hosts and compares page layouts. This checks the typesetting pipeline even without owning all three systems; it does not certify installation inside every agent application.
