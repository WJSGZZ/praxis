import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_relative_links_in_documentation_resolve():
    pages = [*ROOT.glob('*.md'), *ROOT.glob('references/*.md'), *ROOT.glob('skills/*/SKILL.md'), *ROOT.glob('demos/*/*.md'), *ROOT.glob('evals/*.md')]
    broken = []
    for page in pages:
        for target in re.findall(r'\]\(([^)#\s]+?)(?:#[^)]*)?\)', page.read_text()):
            if not target.startswith(('http', 'mailto')) and not (page.parent / target).exists():
                broken.append((str(page.relative_to(ROOT)), target))
    assert not broken, broken


def test_the_route_example_in_the_guide_is_valid():
    import json
    from modeling import routes
    text = (ROOT / 'references/path-search.md').read_text()
    block = re.search(r'```json\n(.*?)\n```', text, re.S).group(1)
    result = routes.apply(None, json.loads(block), question='example')
    assert result['issues'] == [] and result['graph']['paths']['lp']['status'] == 'chosen'


def test_tool_index_is_current():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, '-m', 'scripts.gen_tool_index', '--check'], cwd=ROOT)
    assert result.returncode == 0, 'run: uv run --locked python -m scripts.gen_tool_index'


def test_every_tool_is_in_both_readme_tool_tables():
    """The README tool tables list every tool and nothing that no longer exists."""
    import re
    from scripts import mcp_server
    root = Path(__file__).resolve().parents[1]
    for name, header in (('README.md', '| 类别 |'), ('README.en.md', '| Group |')):
        text = (root / name).read_text()
        start = text.index(header)
        table = text[start:text.index('\n\n', start)]
        listed = set(re.findall(r'`([a-z_0-9]+)`', table))
        assert not [t for t in mcp_server.TOOLS if t not in listed], (name, 'missing')
        assert not [t for t in listed if t not in mcp_server.TOOLS], (name, 'unknown')
