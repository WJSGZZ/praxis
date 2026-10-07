"""Export the maintained skill as a self-contained portable plugin directory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

BUNDLE = Path(__file__).resolve().parents[1]
FILES = ('SKILL.md', 'README.md', 'README.en.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
         'pyproject.toml', 'uv.lock', 'ARCHITECTURE.md')
# Explicit public resources, never the repository, environment or user cases.
TREES = {
    'agents': {'.yaml'},
    'references': {'.md'},
    'scripts': {'.py'},
    'modeling': {'.py'},
    'examples': {'.py'},
    'third_party': {'.json'},
    'third_party/licenses': None,
    'packaging': {'.json'},
    'design': {'.py', '.md', '.json'},
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
}
# Focused skills ship next to the core skill; links to the core are rewritten.
FOCUSED = ('praxis-model', 'praxis-compute', 'praxis-verify', 'praxis-report')
LINK_TO_CORE = ('](../../', '](../praxis/')


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


def build_plugin(output: Path, source: Path = BUNDLE) -> dict:
    source = source.resolve()
    # Resolve parent aliases, while mkdir(exist_ok=False) protects the target.
    output = output.parent.resolve() / output.name
    if output.exists() or output.is_symlink():
        raise FileExistsError(f'Refusing to replace {output}')
    files = public_files(source)
    manifest = json.loads((source / 'packaging/plugin.json').read_text())
    if manifest['name'] != 'praxis':
        raise ValueError('Expected the Praxis manifest')
    if any(output.is_relative_to(source / tree) for tree in TREES):
        raise ValueError('Output must not be inside a packaged resource directory')
    output.mkdir(parents=True, exist_ok=False)
    skill = output / 'skills/praxis'
    hashes = {}
    for path in files:
        relative = path.relative_to(source)
        if relative.parts[0] == 'skills':
            # Focused skill: sibling of the core skill, links point at ../praxis/.
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(path.read_text().replace(*LINK_TO_CORE))
        else:
            target = skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        hashes[target.relative_to(output).as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / 'plugin.json').write_text(json.dumps(manifest, indent=2) + '\n')
    mcp = json.loads((source / 'packaging/mcp.json').read_text())
    (output / 'mcp.json').write_text(json.dumps(mcp, indent=2) + '\n')
    hashes['mcp.json'] = hashlib.sha256((output / 'mcp.json').read_bytes()).hexdigest()
    (output / 'LICENSE').write_bytes((source / 'LICENSE').read_bytes())
    (output / 'README.md').write_text('''# Praxis plugin

This directory is generated from the maintained Praxis skill repository.
The portable entry point is plugin.json; mcp.json starts the praxis-tools MCP server
(computation tools, run with uv). skills/praxis/ is the core skill with
all references and scripts; skills/praxis-model, -compute, -verify and -report
are focused skills that read the core's references through ../praxis/.

Before running Python helpers, explicitly prepare their environment:

```bash
uv sync --locked --project /absolute/path/to/praxis-plugin/skills/praxis
```

Run helpers with that environment and pass --workspace to the user project.
Installation does not install Python dependencies. Keep cases, data, reports
and run outputs in the user project. See skills/praxis/README.md for usage
and third-party licensing. Desktop installation and discovery must be tested
separately; this export is not a plugin-directory publication.
''')
    receipt = {'format': 'praxis-plugin-export-v1', 'name': manifest['name'],
               'version': manifest['version'], 'files_sha256': hashes}
    (output / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return {'plugin': str(output), 'skill': str(skill), 'public_files': len(files)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New output directory; never replaces an existing directory')
    args = parser.parse_args()
    print(json.dumps(build_plugin(args.output), indent=2))


if __name__ == '__main__':
    main()
