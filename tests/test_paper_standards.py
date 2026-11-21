"""The venue-standards knowledge base stays sourced, queryable and consistent with the plotting defaults."""
import re
from pathlib import Path

from scripts import paper_standards, texplot
from scripts.build_plugin import public_files

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / 'references/paper-standards.md'


def rules():
    return paper_standards.parse(GUIDE.read_text(encoding='utf-8'))


def test_every_rule_names_status_source_date_and_condition():
    assert paper_standards.validate(rules()) == []


def test_every_paper_type_has_its_own_confirmed_rules():
    found = {rule['类型'] for rule in rules() if rule['状态'] == '已证实'}
    assert {'siam', 'elsevier', 'ieee', 'nature', 'science', 'statistics', 'mcm', 'cumcm', 'zh'} <= found


def test_validation_rejects_unsourced_or_undated_rules():
    bad = [{'ID': 'siam-x', '类型': 'siam', '主题': '配色', '规范': 'r', '适用条件': 'c',
            '状态': '已证实', '来源': '记忆', '查阅': '最近'}]
    errors = paper_standards.validate(bad)
    assert any('URL' in e for e in errors) and any('ISO date' in e for e in errors)


def test_names_resolve_to_their_own_venue_type():
    assert paper_standards.resolve('SIAM Journal on Applied Mathematics (SIAP)') == ['siam']
    assert paper_standards.resolve('IEEE Transactions on Automatic Control') == ['ieee']
    assert paper_standards.resolve('Physical Review E') == ['aps']
    assert paper_standards.resolve('Nature Communications') == ['nature']
    assert paper_standards.resolve('全国大学生数学建模竞赛') == ['cumcm']
    assert paper_standards.resolve('硕士学位论文') == ['zh']
    assert paper_standards.resolve('JASA') == ['statistics']
    # Short aliases match whole words only, and unknown venues get no borrowed rules.
    assert paper_standards.resolve('Journal of Hydrology claims') == []


def test_query_returns_core_plus_venue_rules_and_open_topics():
    result = paper_standards.query(rules(), 'SIAP')
    types = {rule['类型'] for rule in result['rules']}
    assert types == {'core', 'siam'}
    assert result['unconfirmed_topics']  # what the author guide still has to answer
    unknown = paper_standards.query(rules(), 'Journal of Unlisted Things')
    assert {rule['类型'] for rule in unknown['rules']} == {'core'} and 'Unknown venue' in unknown['note']


def test_venue_figure_conventions_differ_where_sources_differ():
    # Nature labels panels with lower-case a, Science with capital A: neither is a universal rule.
    text = {rule['ID'].strip('`'): rule['规范'] for rule in rules()}
    assert '小写 a' in text['nature-panel'] and '大写 A' in text['science-panel']


def test_command_line_check_and_query_run(capsys):
    assert paper_standards.main(['--check']) == 0
    assert paper_standards.main(['--venue', '国赛', '--topic', '图注']) == 0
    assert 'cumcm' in capsys.readouterr().out


def test_writing_visualization_and_review_skills_retrieve_standards_first():
    for skill in ('praxis-visualization', 'praxis-scientific-writing', 'praxis-review', 'praxis-report'):
        assert 'paper-standards.md' in (ROOT / f'skills/{skill}/SKILL.md').read_text(encoding='utf-8'), skill
    assert 'paper-standards.md' in (ROOT / 'references/visualization.md').read_text(encoding='utf-8')


def test_guide_and_script_are_exported():
    paths = {p.relative_to(ROOT).as_posix() for p in public_files(ROOT)}
    assert {'references/paper-standards.md', 'scripts/paper_standards.py'} <= paths


def test_paper_palette_is_one_scientific_palette_across_tools():
    preamble = dict(re.findall(r'\\definecolor\{(\w+)\}\{HTML\}\{(\w{6})\}', texplot.PREAMBLE))
    style = (ROOT / 'templates/praxis.mplstyle').read_text(encoding='utf-8')
    cycle = re.search(r"axes.prop_cycle: cycler\('color', \[(.*)\]\)", style).group(1)
    first, second = [c.strip(" '") for c in cycle.split(',')[:2]]
    assert (preamble['main'], preamble['accent']) == (first, second) == ('0072B2', 'D55E00')
    for template in ('mcm-style.tex', 'cumcm-style.tex'):
        tex = (ROOT / 'templates' / template).read_text(encoding='utf-8')
        if 'definecolor{main}' in tex:
            assert '{main}{HTML}{0072B2}' in tex and '{accent}{HTML}{D55E00}' in tex


def test_new_flow_diagrams_do_not_use_identity_colours():
    tex = texplot.flow_diagram(['Data', 'Model'])
    assert not re.search(r'\b(teal|clay|slate|sand)\b', tex)
    archived = texplot.flow_diagram(['Data', 'Model'], border='teal', arrow='clay')
    assert 'draw=teal' in archived and ',clay,' in archived


def test_grayscale_claim_matches_palette_luminance():
    # main, accent and muted have close luminance, so grayscale reading needs line style or markers.
    def luminance(code):
        channels = [int(code[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    values = [luminance(code) for code in ('0072B2', 'D55E00', '7A7F85')]
    assert max(values) - min(values) < 0.1
    assert '灰度' in GUIDE.read_text(encoding='utf-8') and '线型' in GUIDE.read_text(encoding='utf-8')


def test_mcm_rules_cover_official_rules_judge_advice_and_reference_papers():
    mcm = {rule['ID'].strip('`'): rule for rule in rules() if rule['类型'] == 'mcm'}
    for rid in ('mcm-pages', 'mcm-summary', 'mcm-font', 'mcm-file', 'mcm-identity', 'mcm-deliverables',
                'mcm-ai-report', 'mcm-credit', 'mcm-advice-figures'):
        assert mcm[rid]['状态'] == '已证实' and 'comap.com' in mcm[rid]['来源'], rid
    # COMAP says nothing on colour or grayscale; the guide must not invent an official rule.
    assert mcm['mcm-color']['状态'] == '未查到'
    reference = [r for r in mcm.values() if r['状态'] == '往届参考']
    assert reference and all(re.search(r'20\d\d', r['适用条件']) for r in reference)


def test_award_paper_observations_need_year_and_location():
    bad = [{'ID': 'mcm-x', '类型': 'mcm', '主题': '版面', '规范': 'O 奖论文都有总览图', '适用条件': '往届',
            '状态': '往届参考', '来源': '印象', '查阅': '2026-11-20'}]
    assert any('往届参考' in e for e in paper_standards.validate(bad))
