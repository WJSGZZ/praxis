"""Exact bounded loading, preserved safety and explicit detail selection."""
from pathlib import Path
import hashlib
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def packet(*args, **kwargs):
    from scripts.instruction_packet import build_packet
    return build_packet(ROOT, *args, **kwargs)


def test_complete_contest_packet_is_bounded_and_counts_real_emitted_text():
    text, manifest = packet()
    assert len(text) == manifest['emitted_characters'] == manifest['core_characters']
    assert len(text) <= 9390
    assert manifest['core_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    paths = {row['path'] for row in manifest['sources']}
    assert {'SKILL.md', *(f'skills/praxis-{name}/SKILL.md' for name in ('model', 'compute', 'verify', 'report'))} <= paths
    assert (ROOT / 'references/integrity.md').read_text() in text
    assert '不得通过删除文件、回滚、换 Agent' in text
    assert 'readme' not in paths
    assert manifest['static_template_characters'] > 0
    assert '\\documentclass' not in text


@pytest.mark.parametrize('stage', ['model', 'compute', 'verify', 'report'])
def test_each_phase_contains_its_role_and_both_safety_sources(stage):
    text, manifest = packet(stage=stage)
    paths = {row['path'] for row in manifest['sources']}
    assert f'skills/praxis-{stage}/SKILL.md' in paths
    assert {'references/integrity.md', 'references/learning-loop.md'} <= paths
    assert (ROOT / 'references/integrity.md').read_text() in text
    assert manifest['core_characters'] <= 9390


def test_all_conditional_detail_ids_resolve_exact_existing_regions():
    from scripts.instruction_packet import DETAILS
    for key in DETAILS:
        text, manifest = packet(details=[key, key])
        assert len(manifest['details']) == 1
        assert manifest['details'][0]['id'] == key
        assert manifest['conditional_detail_characters'] > 0
        assert len(text) == manifest['emitted_characters']
        assert manifest['core_characters'] <= 9390


def test_details_are_not_loaded_implicitly_and_unknown_ids_fail():
    text, manifest = packet()
    assert not manifest['details']
    assert 'schema 1 每条为' not in text
    with pytest.raises(ValueError, match='Unknown detail'):
        packet(details=['invented'])


def test_budget_cannot_be_relaxed_and_small_budget_refuses_emission():
    for size in (0, 9391, True):
        with pytest.raises(ValueError, match='Limit'):
            packet(limit=size)
    with pytest.raises(ValueError, match='exceeds'):
        packet(limit=100)


def test_missing_or_repeated_core_region_is_rejected(tmp_path):
    from scripts.instruction_packet import marker_region, CORE_BEGIN, CORE_END
    for text in ('missing', CORE_BEGIN + 'x', CORE_END + CORE_BEGIN,
                 CORE_BEGIN + CORE_BEGIN + 'x' + CORE_END):
        with pytest.raises(ValueError):
            marker_region(text, CORE_BEGIN, CORE_END)


def test_cli_from_unrelated_working_directory_uses_explicit_bundle(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/instruction_packet.py'),
                             '--bundle', str(ROOT), '--stage', 'contest'], cwd=tmp_path,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert '材料、披露与贡献的真实性' in result.stdout
    assert len(result.stdout) <= 9390


@pytest.mark.parametrize('fence', ['```', '~~~', '````'])
def test_section_loader_ignores_fenced_code_headings(fence):
    from scripts.instruction_packet import section_region
    body = f'## API\nBefore\n{fence}python\n# comment\nprint(42)\n{fence}\nAfter\n## Next\nOther\n'
    selected = section_region(body, 'API')
    assert '# comment' in selected
    assert 'print(42)' in selected
    assert 'After' in selected
    assert 'Other' not in selected
    with pytest.raises(ValueError, match='heading'):
        section_region(body, 'comment')


def test_packet_omits_skill_frontmatter_but_keeps_host_description():
    from scripts.instruction_packet import strip_frontmatter
    raw = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    assert raw.startswith('---\n') and len(raw.split('description:', 1)[1].split('\n', 1)[0]) > 150
    body = strip_frontmatter(raw)
    assert not body.startswith('---') and body in raw
