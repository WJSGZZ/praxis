"""The contest format checks: each rule on synthetic page records, and the shipped templates compile into PDFs that pass."""
import shutil
import subprocess
import tempfile
from zipfile import ZipFile
from pathlib import Path

import pytest

from scripts import contest_rules

ROOT = Path(__file__).resolve().parents[1]


def page(text, size=12.0):
    return dict(text=text, lines=[x for x in text.splitlines() if x.strip()], body_size=size)


def mcm_pages(n, ai_from=None, size=12.0):
    out = []
    for i in range(n):
        body = 'Report on Use of AI\nwords' if ai_from is not None and i == ai_from else 'Summary\nwords' if i == 0 else 'text'
        out.append(page(f'Team # 1234567 Page {i + 1} of {n}\n{body}', size))
    return out


def cumcm_pages(body=10, appendix=2):
    pages = [page('摘 要\n内容\n关键词：甲；乙\n1')]
    pages += [page(f'正文\n内容\n{i + 2}') for i in range(body - 1)]
    pages += [page(f'附录 A 支撑材料文件列表\n源程序\n{body + i + 1}') for i in range(appendix)]
    return pages


def test_mcm_page_limit_counts_everything_before_the_ai_report():
    assert contest_rules.evaluate(mcm_pages(25), 'mcm')['passed']
    assert contest_rules.evaluate(mcm_pages(26), 'mcm')['errors']
    assert contest_rules.evaluate(mcm_pages(30, ai_from=25), 'mcm')['passed']        # 25 counted pages plus an AI report
    assert contest_rules.evaluate(mcm_pages(30, ai_from=26), 'mcm')['errors']


def test_mcm_font_and_team_number():
    assert contest_rules.evaluate(mcm_pages(5, size=10.0), 'mcm')['errors']
    pages = mcm_pages(5)
    pages[2] = page('Team # 7654321 Page 3 of 5\ntext')
    assert any('team numbers' in e for e in contest_rules.evaluate(pages, 'mcm')['errors'])
    assert contest_rules.evaluate(mcm_pages(3), 'mcm')['facts']['team_number'] == '1234567'


def test_mcm_contents_entry_is_not_the_ai_heading():
    pages = mcm_pages(4)
    pages[1] = page('Team # 1234567 Page 2 of 4\nContents\nReport on Use of AI 4')
    r = contest_rules.evaluate(pages, 'mcm')
    assert r['facts']['has_table_of_contents'] and r['facts']['ai_report_from_page'] is None


def test_cumcm_rules():
    assert contest_rules.evaluate(cumcm_pages(), 'cumcm')['passed']
    toc = cumcm_pages()
    toc[1] = page('目 录\n1 问题重述\n2')
    assert any('table of contents' in e for e in contest_rules.evaluate(toc, 'cumcm')['errors'])
    assert contest_rules.evaluate(cumcm_pages(body=21), 'cumcm')['warnings']
    no_abstract = cumcm_pages()
    no_abstract[0] = page('问题重述\n1')
    assert contest_rules.evaluate(no_abstract, 'cumcm')['errors']
    no_code = cumcm_pages(appendix=1)
    no_code[-1] = page('附录\n仅说明\n11')
    assert contest_rules.evaluate(no_code, 'cumcm')['errors']
    wrong_number = cumcm_pages()
    wrong_number[3] = page('正文\n内容\n9')
    assert contest_rules.evaluate(wrong_number, 'cumcm')['warnings']


def test_forbidden_text_is_an_error():
    pages = cumcm_pages()
    pages[1] = page('正文 某某大学\n2')
    assert any('identifying' in e for e in contest_rules.evaluate(pages, 'cumcm', forbidden=['某某大学'])['errors'])


def test_margin_rule():
    margins = dict(pages=[dict(page=1, left_pt=80, right_pt=80), dict(page=2, left_pt=60, right_pt=80)])
    assert any('2.5 cm' in e for e in contest_rules.evaluate(cumcm_pages(), 'cumcm', margins=margins)['errors'])


@pytest.mark.skipif(not (shutil.which('xelatex') or shutil.which('tectonic')), reason='no TeX engine')
@pytest.mark.parametrize('template,contest', [('mcm-paper.tex', 'mcm'), ('cumcm-paper.tex', 'cumcm')])
def test_shipped_templates_satisfy_their_own_contest_rules(template, contest):
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(ROOT / 'templates' / template, Path(tmp) / 'main.tex')
        engine = ['xelatex', '-interaction=nonstopmode'] if shutil.which('xelatex') else ['tectonic']
        for _ in range(2):
            done = subprocess.run(engine + ['main.tex'], cwd=tmp, capture_output=True, text=True)
        if not (Path(tmp) / 'main.pdf').exists():
            pytest.skip('template did not compile here (missing fonts or packages): ' + done.stdout[-200:])
        margins = None
        if contest == 'cumcm':
            from scripts.check_pdf import margin_report
            margins = margin_report(Path(tmp) / 'main.pdf')
        report = contest_rules.evaluate(contest_rules.extract(Path(tmp) / 'main.pdf'), contest, margins=margins)
        assert report['passed'], report['errors']


def test_demo_papers_satisfy_their_contest_rules():
    mcm = ROOT / 'demos/mcm-2016-a/deliverables/7391856.pdf'
    cumcm = ROOT / 'demos/cumcm-1998-a/deliverables/paper.pdf'
    from scripts.check_pdf import margin_report
    assert contest_rules.evaluate(contest_rules.extract(mcm), 'mcm')['passed']
    assert contest_rules.evaluate(contest_rules.extract(cumcm), 'cumcm', margins=margin_report(cumcm))['passed']


def test_a_body_line_that_starts_with_appendix_is_not_the_appendix_heading():
    pages = cumcm_pages(body=10, appendix=2)
    pages[4] = page('正文\n附录 B 中的程序按第 3 节的步骤逐项实现，相关说明见表 2，不再重复。\n6')
    r = contest_rules.evaluate(pages, 'cumcm')
    assert r['facts']['body_pages'] == 10


def test_a_short_body_line_with_punctuation_is_not_an_appendix_heading():
    pages = cumcm_pages(body=10, appendix=2)
    pages[4] = page('正文\n附录 B。\n6')
    assert contest_rules.evaluate(pages, 'cumcm')['facts']['body_pages'] == 10


def test_figures_and_tables_that_the_text_never_mentions_are_flagged():
    pages = cumcm_pages(body=4, appendix=1)
    pages[1] = page('正文，见图 1 的结果。\n图 1 风险收益曲线\n表 2 参数\n图 3 孤立的图\n2')
    r = contest_rules.evaluate(pages, 'cumcm')
    warning = next(w for w in r['warnings'] if 'never referred' in w)
    assert '表 2' in warning and '图 3' in warning and '图 1' not in warning
    en = [page('Summary\nTeam # 1234567 Page 1 of 3'), page('Team # 1234567 Page 2 of 3\nSee Figure 1.\nFigure 1. Curve\nTable 2. Parameters'), page('Team # 1234567 Page 3 of 3\ntext')]
    w = [x for x in contest_rules.evaluate(en, 'mcm')['warnings'] if 'never referred' in x][0]
    assert 'table 2' in w.lower() and 'figure 1' not in w.lower()


def test_float_references_can_start_a_paragraph_and_cross_a_line_break():
    pages = [page('图 1 显示收益的边际变化。\n图 1 风险收益曲线\n'
                  'Table\n2 gives the inputs.\nTable 2. Inputs\n'
                  'Figure 3 shows the bound.\nFigure 3. Bound\n'
                  '表 4 未引用的参数表')]
    assert contest_rules.unreferenced_floats(pages) == ['表 4']


def test_demo_figures_and_tables_have_reader_callouts():
    for relative in ['demos/mcm-2016-a/deliverables/7391856.pdf',
                     'demos/cumcm-1998-a/deliverables/paper.pdf']:
        assert contest_rules.unreferenced_floats(contest_rules.extract(ROOT / relative)) == []
    mcm = contest_rules.extract(ROOT / 'demos/mcm-2016-a/deliverables/7391856.pdf')
    guide = [r for r in mcm if 'A guide for the person in the bathtub' in r['text']]
    assert len(guide) == 1 and 'The practical rule:' in guide[0]['text']
    assert 'References and reproducible algorithm' not in guide[0]['text']
    with ZipFile(ROOT / 'demos/cumcm-1998-a/deliverables/supporting_materials.zip') as archive:
        assert not any(Path(name).suffix in {'.aux', '.out', '.log'} for name in archive.namelist())
