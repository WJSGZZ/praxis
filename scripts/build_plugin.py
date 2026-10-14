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
FILES = ('SKILL.md', 'README.md', 'README.en.md', 'CHANGELOG.md', 'LICENSE', 'SECURITY.md', 'THIRD_PARTY_NOTICES.md', 'CITATION.cff',
         'pyproject.toml', 'uv.lock', 'demos/mcm-2016-a/paper.pdf')
# Explicit public resources, never the repository, environment or user cases.
TREES = {
    'agents': {'.yaml'},
    'references': {'.md'},
    'scripts': {'.py'},
    'modeling': {'.py'},
    'templates': {'.tex', '.jsonl', '.json'},
    'examples': {'.py'},
    'evals': {'.py', '.md', '.json'},
    'demos/assets_src': {'.py', '.json', '.md', '.png'},
    'demos': {'.md'},
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
    'demos/mcm-2016-a/report': {'.tex'},
    'demos/mcm-2016-a/reproduce': {'.py', '.md'},
    'demos/mcm-2016-a/reproduce/code': {'.py'},
    'demos/mcm-2016-a/reproduce/reference': {'.npz', '.json', '.py', '.md'},
    'demos/mcm-2016-a/reproduce/reference/transport': {'.json', '.py', '.md'},
    'demos/mcm-2016-a/reproduce/reference/spatial-functional': {'.json', '.py', '.md'},
    'demos/mcm-2016-a/reproduce/reference/delayed-upper': {'.json', '.py', '.md', '.npz'},
    'demos/domino-research': {'.md', '.json'},
    'demos/domino-research/assets': {'.png'},
    'demos/domino-research/deliverables': {'.pdf'},
    'demos/domino-research/reproduce': {'.py'},
    'demos/domino-research/reproduce/reference': {'.json', '.md'},
    'demos/collatz-research': {'.md', '.json'},
    'demos/collatz-research/assets': {'.png'},
    'demos/collatz-research/deliverables': {'.pdf'},
    'demos/collatz-research/reproduce/code': {'.py'},
    'demos/collatz-research/reproduce/paper': {'.tex'},
    'demos/collatz-research/reproduce/runs': {'.json'},
    'demos/data-analysis': {'.md', '.py', '.json'},
    'demos/data-analysis/assets': {'.png', '.pdf'},
    'demos/data-vintages': {'.md', '.py', '.json'},
    'demos/data-vintages/data': {'.md', '.json'},
    'demos/spatial-analysis': {'.md', '.py', '.json'},
    'demos/spatial-analysis/assets': {'.png', '.pdf'},
    'demos/image-analysis': {'.md', '.py', '.json', '.tex'},
    'demos/image-analysis/assets': {'.png', '.pdf'},
}
# Focused skills ship next to the core; all packaged Markdown links follow relocation.
FOCUSED = ('praxis-model', 'praxis-assumptions', 'praxis-compute', 'praxis-verify', 'praxis-review', 'praxis-explore', 'praxis-dialogue', 'praxis-report',
           'praxis-data-analysis', 'praxis-statistics', 'praxis-text-analysis',
           'praxis-visualization', 'praxis-time-series', 'praxis-causal-analysis',
           'praxis-scientific-writing', 'praxis-literature-review', 'praxis-optimization', 'praxis-dynamical-modeling', 'praxis-uncertainty-analysis', 'praxis-machine-learning', 'praxis-experimental-design', 'praxis-spatial-analysis', 'praxis-image-analysis')
# Use the maintained brand asset for native presentation; reports keep their
# scientific typography and do not acquire the plugin logo.
VISUAL_ASSETS = {'assets/praxis-logo.png': 'demos/assets_src/praxis-logo.png'}


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
    for target_name, source_name in VISUAL_ASSETS.items():
        target = output / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source / source_name).read_bytes())
        hashes[target_name] = hashlib.sha256(target.read_bytes()).hexdigest()
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
    (output / 'README.md').write_text('''# Praxis · Agent 插件 / Agent plugin

[简体中文](skills/praxis/README.md) · [English](skills/praxis/README.en.md)

本目录由 Praxis 的同一份源码按宿主导出，包含核心入口、专业技能、数学工具和证据工作流。
宿主安装方式与首次使用见[中文安装指南](skills/praxis/references/installation.md)。

This host-specific package contains the coordinated skills, mathematical tools and evidence workflow.
Start with the [English installation guide](skills/praxis/references/installation.en.md).

## 计算环境 · Computational environment

安装插件后，用实际包路径准备锁定的 Python 环境。此命令适用于终端和 PowerShell。
Prepare the locked environment with the actual package path; the command works in a shell or PowerShell.

```text
uv sync --locked --project /absolute/path/to/praxis-plugin/skills/praxis
```

题目、数据和结果保存到自己的项目；运行脚本时显式传入该工作区。
Keep problems, data and outputs in your project and pass its path to workspace-aware scripts.

[技能与工具](skills/praxis/README.md#技能一览) · [Skills and tools](skills/praxis/README.en.md#skills)
''')
    # The package-root guidance and license are shipped resources too. The
    # receipt binds all final files except the receipt itself (no self-hash).
    for name in ('README.md', 'LICENSE'):
        hashes[name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
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
