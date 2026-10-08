"""Small host adapters; all skills and mathematical code remain shared."""
from __future__ import annotations
import copy

HOSTS = ('portable', 'codex', 'claude', 'copilot', 'gemini', 'cursor')


def host_files(host: str, manifest: dict, mcp: dict) -> dict[str, dict]:
    if host not in HOSTS:
        raise ValueError(f'Unknown plugin host: {host}')
    identity = {k: manifest[k] for k in ('name', 'version', 'description', 'author', 'repository', 'license')}
    files = {}
    if host in ('portable', 'codex'):
        files['.agents/plugins/marketplace.json'] = {
            'name': 'praxis-local', 'interface': {'displayName': 'Praxis'},
            'plugins': [{'name': 'praxis', 'source': {'source': 'local', 'path': './'},
                         'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
                         'category': 'Productivity'}]}
    elif host == 'claude':
        config = copy.deepcopy(mcp)
        config.pop('$schema', None)
        for server in config['mcpServers'].values():
            server.pop('type', None)
            # Claude documents substitution in args/env, not cwd. uv changes
            # directory explicitly so Python -m finds the bundled scripts.
            cwd = server.pop('cwd', None)
            if cwd:
                server['args'] = ['--directory', cwd, *server['args']]
            server['args'] = [v.replace('${PLUGIN_ROOT}', '${CLAUDE_PLUGIN_ROOT}')
                              .replace('${PLUGIN_DATA}', '${CLAUDE_PLUGIN_DATA}') for v in server['args']]
        files['.mcp.json'] = config
        files['.claude-plugin/plugin.json'] = identity
        files['.claude-plugin/marketplace.json'] = {
            'name': 'praxis-local', 'owner': manifest['author'], 'description': manifest['description'],
            'plugins': [{'name': 'praxis', 'source': './', 'description': manifest['description']}]}
    elif host in ('gemini', 'cursor'):
        # These hosts have no documented equivalent of the standard data-dir
        # variable. Keep the core service; optional arXiv storage is configured
        # separately rather than writing to the plugin installation directory.
        server = copy.deepcopy(mcp['mcpServers']['praxis-tools'])
        root = '${extensionPath}' if host == 'gemini' else '${CURSOR_PLUGIN_ROOT}'
        server['args'] = [v.replace('${PLUGIN_ROOT}', root) for v in server['args']]
        server['cwd'] = server['cwd'].replace('${PLUGIN_ROOT}', root)
        if host == 'gemini':
            server.pop('type', None)
            files['gemini-extension.json'] = {k: identity[k] for k in ('name', 'version', 'description')}
            files['gemini-extension.json']['mcpServers'] = {'praxis-tools': server}
        else:
            files['mcp.json'] = {'$schema': mcp['$schema'], 'mcpServers': {'praxis-tools': server}}
    # Copilot CLI supports the portable root manifest and mcp.json directly.
    return files
