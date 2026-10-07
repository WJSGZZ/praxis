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
