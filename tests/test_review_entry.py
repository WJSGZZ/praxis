"""Verify discoverable contracts and authority relocation, not judge reliability."""
import json
import re
from pathlib import Path

import pytest

from evals.aggregate import aggregate, PROFILES
from evals.competitions import lookup
from scripts.build_plugin import BUNDLE, build_plugin


def test_review_is_a_new_discoverable_skill_without_removing_old_entries(tmp_path):
    output = tmp_path / 'plugin'
    build_plugin(output, host='codex')
    expected = {'praxis', 'praxis-model', 'praxis-assumptions', 'praxis-compute', 'praxis-verify',
                'praxis-review', 'praxis-explore', 'praxis-dialogue', 'praxis-report'}
    paths = list((output / 'skills').glob('*/SKILL.md'))
    assert {p.parent.name for p in paths} == expected
    for path in paths:
        header = path.read_text().split('---')[1]
        assert f'name: {path.parent.name}\n' in header
    review = (output / 'skills/praxis-review/SKILL.md').read_text()
    assert '../../praxis-verify/' not in review
    assert '](../praxis-verify/SKILL.md)' in review
    assert '](../praxis-report/SKILL.md)' in review
    assert '](../praxis/evals/contest-judging.md)' in review
    assert '](../praxis/evals/research-judging.md)' in review
    assert '](../praxis-review/SKILL.md)' in (output / 'skills/praxis/SKILL.md').read_text()


def test_new_authorities_relocate_in_both_directions(tmp_path):
    output = tmp_path / 'plugin'
    build_plugin(output)
    for relative in ('evals/judging.md', 'evals/contest-judging.md',
                     'evals/research-judging.md', 'references/contest-delivery.md'):
        path = output / 'skills/praxis' / relative
        assert path.is_file()
        for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', path.read_text()):
            if '://' not in link:
                assert (path.parent / link).resolve().exists(), (relative, link)
    contest = (BUNDLE / 'evals/contest-judging.md').read_text()
    writing = (BUNDLE / 'references/writing.md').read_text()
    delivery = (BUNDLE / 'references/contest-delivery.md').read_text()
    assert '与参考论文比较时只比较内容' not in contest
    assert '国赛可按其章程四标准' in contest
    assert '美赛按 COMAP' in contest
    # Detailed edition/template rules have one owner, while writing retains navigation.
    assert 'MCM v3 | CUMCM v2' not in writing
    assert 'MCM v3 | CUMCM v2' in delivery
    assert '[contest-delivery.md](contest-delivery.md)' in writing


def test_partial_requests_keep_their_focused_contracts():
    verify = (BUNDLE / 'skills/praxis-verify/SKILL.md').read_text()
    report = (BUNDLE / 'skills/praxis-report/SKILL.md').read_text()
    core = (BUNDLE / 'SKILL.md').read_text()
    assert '局部证明或一个数值结果不启动整稿评奖' in verify
    assert '[praxis-review](../praxis-review/SKILL.md)' in verify
    assert '纯语言修改只读“语言专项”' in report
    assert '不新增科学主张' in report
    assert '不建案例、不写 tasks.md' in core
    assert '未知届次或期刊不继承其它要求' in core


def test_graduate_registry_does_not_create_an_implicit_numerical_profile(tmp_path):
    assert lookup('graduate', 'main', '2026')['status']['rules'] == 'partial'
    assert lookup('graduate', 'main', '2027')['status']['rules'] == 'unconfirmed'
    assert 'graduate' not in PROFILES
    with pytest.raises(ValueError, match='No profile'):
        aggregate([], contest='graduate')
    # Do not turn a known rule registry entry into CUMCM weights.
    contest = (BUNDLE / 'evals/contest-judging.md').read_text()
    assert '没有数值 profile' in contest
    assert '不默套 `cumcm`、`mcm` 或 `general`' in contest
    assert '具名定性竞赛评议' in contest


def test_research_contract_remains_distinct_and_old_weights_are_unchanged():
    research = (BUNDLE / 'evals/research-judging.md').read_text()
    assert '`research_assessment`' in research
    assert '不填竞赛七维表、奖项或百分制' in research
    assert '| 问题理解与题意覆盖（10）' not in research
    assert 'schema_version:2' in research
    assert PROFILES['cumcm']['weights'] == dict(coverage=10, assumptions=20, model=20,
        correctness=25, robustness=5, writing=15, verifiability=5)
    assert PROFILES['mcm']['weights'] == dict(coverage=10, assumptions=10, model=15,
        correctness=20, robustness=15, writing=20, verifiability=10)
    protocol = (BUNDLE / 'evals/PROTOCOL.md').read_text()
    assert '只有竞赛数值诊断填写七维条目' in protocol
    assert '但只作相对比较，不对应奖项' not in protocol
    research_mode = (BUNDLE / 'references/research-mode.md').read_text()
    assert '探索难度，不是用途路由' in research_mode
    assert '研究生竞赛仍按竞赛题意' in research_mode
