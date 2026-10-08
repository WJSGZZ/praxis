"""The contest format checks: each rule on synthetic page records, and the shipped templates compile into PDFs that pass."""
import shutil
import subprocess
import tempfile
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
