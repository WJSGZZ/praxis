"""Render bilingual release notes from the version's maintained changelog.

Pass the actual release asset metadata, not a guessed list of host files.
Rendering does not publish or alter a release.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/WJSGZZ/praxis'


def render(version, changelog, asset_names):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('version must contain three numeric components')
    match = re.search(r'^## ' + re.escape(version) + r' · ([^\n]+)\n(.*?)(?=^## |\Z)',
                      changelog, re.MULTILINE | re.DOTALL)
    if match is None:
        raise ValueError('The requested version has no changelog entry')
    entry = match.group(2).strip()
    if not re.search(r'[\u4e00-\u9fff]', entry) or not re.search(r'[A-Za-z]{4}', entry):
        raise ValueError('Release changes must include Chinese and English')
    # Changelog links become stable links into this version, never current main.
    def link(m):
        target = m.group(2)
        if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
            return m.group(0)
        return f'[{m.group(1)}]({REPOSITORY}/blob/v{version}/{target})'
    entry = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, entry)
    assets = sorted(set(asset_names))
    if any(not re.fullmatch(r'[A-Za-z0-9._-]+', name) for name in assets):
        raise ValueError('Asset names must be simple published filenames')
    lines = [f'## 更新 · Changes', '', entry, '', '## 下载 · Downloads', '']
    if assets:
        lines += ['从下方选择对应宿主的安装包；如提供 `SHA256SUMS.txt`，请核对校验和。',
                  'Choose the package for your host and verify its checksum when a checksum file is provided.', '',
                  '| 文件 · File | 下载 · Download |', '|---|---|']
        for name in assets:
            lines.append(f'| `{name}` | [下载 · Download]({REPOSITORY}/releases/download/v{version}/{name}) |')
    else:
        lines += ['本版本未发布预构建附件；源码保留在版本标签。',
                  'This release has no prebuilt attachments. Its source is preserved at the version tag.']
    lines += ['', '## 使用 · Usage', '',
              f'[中文说明]({REPOSITORY}/blob/v{version}/README.md) · '
              f'[English guide]({REPOSITORY}/blob/v{version}/README.en.md) · '
              f'[版本源码 · Versioned source]({REPOSITORY}/tree/v{version})', '',
              '以上更新对应本版本；后续主分支修改不回填安装包。案例结论以各自论文和证据范围为准。',
              'These changes describe this version. Later main-branch changes do not alter its packages. '
              'Case conclusions retain their manuscript-specific evidence and scope.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--assets-json', type=Path, required=True,
                        help='Saved gh release view JSON, with its actual assets')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    names = [asset['name'] for asset in json.loads(args.assets_json.read_text())['assets']]
    text = render(args.version, (ROOT / 'CHANGELOG.md').read_text(), names)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
