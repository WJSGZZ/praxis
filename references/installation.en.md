# Install Praxis

[简体中文](installation.md)

Choose your agent, build its package from the public repository, and install it using that agent's own plugin system. Every target carries the same seven skills and mathematical engine. Host adapters change metadata and path handling, not the modeling methodology. These instructions use source distribution; no marketplace listing is required.

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

The export includes its local marketplace catalog, so existing personal configuration need not be edited. If your CLI lacks these commands, use its supported local marketplace interface. Reload and look for `praxis@praxis-local` and seven `praxis:*` skills. An earlier personal-marketplace install may instead be identified as `praxis@personal`.

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

Every target includes all seven skills and `praxis-tools`. Portable, Codex, Claude and Copilot packages additionally declare the pinned arXiv server. Gemini and Cursor leave that optional integration out because their storage variables differ; configure an external storage location separately if needed. OpenAlex, Unpaywall and Crossref remain available through the core service.

To update, fetch the source, export to a fresh destination and update or reinstall through your host. Do not patch an installation cache or overwrite user configuration. Keep the old source ref and export if you need a rollback.

After reloading, check the plugin list, skill discovery and MCP connection separately. Startup failures usually show up in the host's MCP logs as missing uv, Python or resource paths. A direct service diagnostic is:

```bash
uv run --locked --directory /absolute/path/to/plugin/skills/praxis python -m scripts.mcp_server --list
```

This checks the service rather than host loading. Host permissions still apply. Store problems, data, papers and run outputs in your project workspace.

## Skills-only option

If MCP is unnecessary, install the entry skill and its resources:

```bash
git clone https://github.com/WJSGZZ/praxis.git ~/.agents/skills/praxis
```

For Claude Code, use `~/.claude/skills/praxis`. Other discovery paths are in [host compatibility](agent-compatibility.md). Computation remains available through terminal scripts. Avoid enabling a standalone copy alongside the plugin in the same host.
