"""Export Praxis as a self-contained portable Agent plugin."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tomllib
from urllib.parse import unquote, urlsplit

from scripts.plugin_hosts import HOSTS, host_files

BUNDLE = Path(__file__).resolve().parents[1]
FILES = ('SKILL.md', 'README.md', 'README.en.md', 'CHANGELOG.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
         'pyproject.toml', 'uv.lock')
# Explicit public resources, never the repository, environment or user cases.
TREES = {
    'agents': {'.yaml'},
    'references': {'.md'},
    'scripts': {'.py'},
    'modeling': {'.py'},
    'templates': {'.tex', '.jsonl'},
    'examples': {'.py'},
    'evals': {'.py', '.md', '.json'},
    'demos/assets_src': {'.py'},
    'third_party': {'.json'},
    'third_party/licenses': None,
    'packaging': {'.json'},
    # Only explicitly curated public demos; never user cases or generated reruns.
    'demos/cumcm-1998-a': {'.md', '.json'},
    'demos/cumcm-1998-a/assets': {'.png', '.py'},
    'demos/cumcm-1998-a/deliverables': {'.pdf', '.zip'},
    'demos/cumcm-1998-a/reproduce': {'.py', '.txt', '.json'},
    'demos/cumcm-1998-a/reproduce/code': {'.py'},
    'demos/cumcm-1998-a/reproduce/data': {'.csv'},
    'demos/cumcm-1998-a/reproduce/reference': {'.csv', '.json'},
    'demos/mcm-2016-a': {'.md', '.json'},
    'demos/mcm-2016-a/assets': {'.png', '.py'},
    'demos/mcm-2016-a/deliverables': {'.pdf'},
    'demos/mcm-2016-a/reproduce': {'.py', '.md'},
    'demos/mcm-2016-a/reproduce/code': {'.py'},
    'demos/mcm-2016-a/reproduce/reference': {'.npz', '.json'},
    'demos/domino-research': {'.md'},
    'demos/domino-research/assets': {'.png'},
    'demos/domino-research/deliverables': {'.pdf'},
    'demos/domino-research/reproduce': {'.py'},
    'demos/domino-research/reproduce/reference': {'.json', '.md'},
}
# Focused skills ship next to the core; all packaged Markdown links follow relocation.
FOCUSED = ('praxis-model', 'praxis-compute', 'praxis-verify', 'praxis-explore', 'praxis-dialogue', 'praxis-report')


def export_path(relative: Path) -> Path:
    return relative if relative.parts[0] == 'skills' else Path('skills/praxis') / relative


def relocate_links(text: str, path: Path, source: Path, files: list[Path]) -> str:
    """Relocate local Markdown destinations, including core-to-focused links.

    Only selected resources and their directories are mapped. URLs, anchors,
    labels and optional titles retain their original text.
    """
    destinations = {p: export_path(p.relative_to(source)) for p in files}
    directories = {p.parent for p in files}
    target_parent = export_path(path.relative_to(source)).parent

    def replace(match: re.Match) -> str:
        raw = match.group(1)
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match.group(0)
        resolved = (path.parent / unquote(parsed.path)).resolve()
        destination = destinations.get(resolved)
        if destination is None and resolved in directories:
            destination = export_path(resolved.relative_to(source))
        if destination is None:
            return match.group(0)
        relative = Path(os.path.relpath(destination, target_parent)).as_posix()
        # Preserve the original query/fragment spelling and Markdown title.
        suffix = raw[len(parsed.path):]
        return '](' + relative + suffix + match.group(2) + ')'

    return re.sub(r'\]\(([^\s)]+)([^)]*)\)', replace, text)


def public_files(source: Path) -> list[Path]:
    selected = {source / name for name in FILES}
    for directory, extensions in TREES.items():
        root = source / directory
        if root.is_symlink():
            raise ValueError(f'Symlink is not a public resource: {root}')
        for path in root.iterdir():
            if path.is_symlink():
                raise ValueError(f'Symlink is not a public resource: {path}')
            if path.is_file() and (extensions is None or path.suffix in extensions):
                selected.add(path)
    for name in FOCUSED:
        path = source / 'skills' / name / 'SKILL.md'
        selected.add(path)
    for path in selected:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Missing or symlinked public resource: {path}')
    return sorted(selected)


def build_plugin(output: Path, source: Path = BUNDLE, host: str = 'portable') -> dict:
    if host not in HOSTS:
        raise ValueError(f'Unknown plugin host: {host}')
    source = source.resolve()
    # Resolve parent aliases, while mkdir(exist_ok=False) protects the target.
    output = output.parent.resolve() / output.name
    if output.exists() or output.is_symlink():
        raise FileExistsError(f'Refusing to replace {output}')
    files = public_files(source)
    manifest = json.loads((source / 'packaging/plugin.json').read_text())
    version = tomllib.loads((source / 'pyproject.toml').read_text())['project']['version']
    if manifest['version'] != version:
        raise ValueError('Manifest version must match pyproject.toml')
    if manifest['name'] != 'praxis':
        raise ValueError('Expected the Praxis manifest')
    if any(output.is_relative_to(source / tree) for tree in TREES):
        raise ValueError('Output must not be inside a packaged resource directory')
    output.mkdir(parents=True, exist_ok=False)
    skill = output / 'skills/praxis'
    hashes = {}
    for path in files:
        relative = path.relative_to(source)
        target = output / export_path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == '.md':
            target.write_text(relocate_links(path.read_text(), path, source, files))
        else:
            shutil.copyfile(path, target)
        hashes[target.relative_to(output).as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / 'plugin.json').write_text(json.dumps(manifest, indent=2) + '\n')
    mcp = json.loads((source / 'packaging/mcp.json').read_text())
    (output / 'mcp.json').write_text(json.dumps(mcp, indent=2) + '\n')
    # Derive native Codex metadata from the portable manifest: one identity,
    # two host entry points, no independently maintained compatibility copy.
    native = {k: manifest[k] for k in ('name', 'version', 'description', 'author', 'repository', 'license')}
    native.update(manifest.get('extensions', {}).get('com.openai', {}))
    native.update(skills='./skills/', mcpServers='./.mcp.json')
    (output / '.codex-plugin').mkdir()
    (output / '.codex-plugin/plugin.json').write_text(json.dumps(native, indent=2, ensure_ascii=False) + '\n')
    legacy_mcp = {'mcpServers': {name: {k: v for k, v in server.items() if k != 'type'}
                              for name, server in mcp['mcpServers'].items()}}
    (output / '.mcp.json').write_text(json.dumps(legacy_mcp, indent=2) + '\n')
    for name, data in host_files(host, manifest, mcp).items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    # A host adapter can replace an entry point; receipt always hashes final bytes.
    for name in ('plugin.json', 'mcp.json', '.codex-plugin/plugin.json', '.mcp.json'):
        hashes[name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    (output / 'LICENSE').write_bytes((source / 'LICENSE').read_bytes())
    (output / 'README.md').write_text('''# Praxis plugin

This directory is generated from the maintained Praxis Agent plugin repository.
The portable entry point is plugin.json; mcp.json starts the praxis-tools MCP server
(computation tools, run with uv). skills/praxis/ is the core skill with
all references and scripts; six sibling skills cover modeling, computation,
verification, exploration, dialogue and reporting. All local Markdown links
are relocated with their resources.

Before running Python helpers, explicitly prepare their environment:

```bash
uv sync --locked --project /absolute/path/to/praxis-plugin/skills/praxis
```

Run helpers with that environment and pass --workspace to the user project.
Installation does not install Python dependencies. Keep cases, data, reports
and run outputs in the user project. See skills/praxis/README.md for usage
and third-party licensing. Install this host-specific export using the instructions in
skills/praxis/references/installation.md. Installation and discovery checks
are distinct from plugin-directory publication.
''')
    receipt = {'format': 'praxis-plugin-export-v1', 'name': manifest['name'],
               'version': manifest['version'], 'host': host, 'files_sha256': hashes}
    (output / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return {'plugin': str(output), 'skill': str(skill), 'host': host, 'public_files': len(files)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New output directory; never replaces an existing directory')
    parser.add_argument('--host', choices=HOSTS, default='portable', help='Target host adapter; core skills and code are unchanged')
    args = parser.parse_args()
    print(json.dumps(build_plugin(args.output, host=args.host), indent=2))


if __name__ == '__main__':
    main()
