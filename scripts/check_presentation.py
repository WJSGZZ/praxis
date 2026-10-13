"""Check public version, skill and tool facts in both README languages."""
import json
import re
import tomllib
from pathlib import Path

from scripts import build_plugin, mcp_server

ROOT = Path(__file__).resolve().parents[1]


def readme_errors(text, language, version, skill_names, tool_names):
    errors = []
    for advertised in re.findall(r'(?:Version-|/releases/tag/v)(\d+\.\d+\.\d+)', text):
        if advertised != version:
            errors.append(f'{language}: advertised version {advertised} differs from {version}')
    if '/releases/latest' not in text:
        errors.append(f'{language}: latest published release link is missing')
    listed_skills = set(re.findall(r'\[`(praxis(?:-[a-z-]+)?)`\]', text))
    if listed_skills != set(skill_names):
        errors.append(f'{language}: skill table differs: {sorted(listed_skills ^ set(skill_names))}')
    heading = '## 数学工具' if language == 'zh' else '## Math tools'
    if heading not in text:
        return errors + [f'{language}: tool section is missing']
    section = text.split(heading, 1)[1].split('\n## ', 1)[0]
    listed_tools = set(re.findall(r'`([a-z][a-z_0-9]*)`', section))
    if listed_tools != set(tool_names):
        errors.append(f'{language}: tool table differs: {sorted(listed_tools ^ set(tool_names))}')
    return errors


def check(root=ROOT):
    project = tomllib.loads((root / 'pyproject.toml').read_text())['project']
    version = project['version']
    manifest = json.loads((root / 'packaging/plugin.json').read_text())
    errors = [] if manifest['version'] == version else ['Plugin and project versions differ']
    skills = {'praxis', *build_plugin.FOCUSED}
    for language, file in [('zh', 'README.md'), ('en', 'README.en.md')]:
        errors += readme_errors((root / file).read_text(), language, version, skills, mcp_server.TOOLS)
    if not re.search(r'^## ' + re.escape(version) + r' · ',
                     (root / 'CHANGELOG.md').read_text(), re.MULTILINE):
        errors.append('Current version has no changelog entry')
    for language, file in [('zh', 'installation.md'), ('en', 'installation.en.md')]:
        text = (root / 'references' / file).read_text()
        versions = set(re.findall(r'/releases/(?:tag|download)/v(\d+\.\d+\.\d+)', text))
        if versions != {version}:
            errors.append(f'{language}: installation release versions {sorted(versions)} differ from {version}')
    return {'version': version, 'skills': len(skills), 'tools': len(mcp_server.TOOLS), 'errors': errors}


def main():
    result = check()
    print(json.dumps(result, ensure_ascii=False))
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
