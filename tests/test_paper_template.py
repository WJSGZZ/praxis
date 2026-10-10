from pathlib import Path

import pytest

from scripts.paper_template import check, preamble, summary_header, table_of_contents


ROOT = Path(__file__).resolve().parents[1]


def paper():
    return preamble('7391857', 'A title & a result') + summary_header('B') + r'Body.\end{document}'


def test_shared_layout_accepts_content_and_local_reference_format():
    text = paper().replace('Body.', r'\begingroup\small\setlength{\parindent}{0pt}Reference.\endgroup')
    assert check(text)['profile'] == 'praxis-mcm-v1'
    assert r'Team \# \PraxisTeam' in text
    assert r'Page \thepage{} of \pageref{LastPage}' in text
    assert r'A title \& a result' in text


@pytest.mark.parametrize('override', [
    r'\geometry{margin=2in}', r'\fancyfoot[C]{\thepage}',
    r'\thispagestyle{empty}', r'\linespread{1.0}',
    r'\setlength{\parindent}{1.2em}', r'\usepackage{fontspec}',
    r'\setmainfont{Arial}', r'\fontfamily{phv}\selectfont',
])
def test_rejects_layout_overrides(override):
    with pytest.raises(ValueError, match='override'):
        check(paper().replace('Body.', override + 'Body.'))


def test_rejects_drift_inside_shared_block():
    with pytest.raises(ValueError, match='differs'):
        check(paper().replace('top=0.95in', 'top=1in'))


def test_skeleton_and_active_mcm_reports_use_current_profile():
    for path in ['templates/mcm-paper.tex', 'research/merge-after-toll/paper/paper.tex']:
        check((ROOT / path).read_text())
    for path in ['demos/mcm-2016-a/reproduce/build_report.py',
                 'research/merge-after-toll/paper/build_report.py']:
        text = (ROOT / path).read_text()
        assert 'from scripts.paper_template import preamble, summary_header, check as check_layout' in text
        assert 'check_layout(source)' in text
        assert '\\documentclass' not in text


def test_export_contains_style_and_checker():
    from scripts.build_plugin import public_files
    paths = {str(p.relative_to(ROOT)) for p in public_files(ROOT)}
    assert {'templates/mcm-style.tex', 'templates/cumcm-style.tex', 'scripts/paper_template.py'} <= paths


def test_chinese_profile_keeps_its_own_layout_and_rejects_contents():
    text = preamble(None, '中文题目', 'cumcm') + r'\section*{摘要}内容\end{document}'
    assert check(text, 'cumcm')['profile'] == 'praxis-cumcm-v2'
    assert 'Team' not in text
    check((ROOT / 'templates/cumcm-paper.tex').read_text(), 'cumcm')
    with pytest.raises(ValueError, match='contents'):
        check(text.replace('内容', r'\tableofcontents'), 'cumcm')


def test_both_mcm_contents_levels_have_explicit_dot_leaders():
    style = (ROOT / 'templates/mcm-style.tex').read_text()
    assert r'\titlecontents{section}' in style
    assert r'\titlecontents{subsection}' in style
    assert style.count(r'\titlerule*[.6pc]{.}\contentspage') == 2


def test_layout_gate_rejects_before_creating_final_snapshot(tmp_path):
    from scripts.freeze_pdf import freeze
    source = tmp_path / 'source.tex'
    source.write_text(paper().replace('Body.', r'\linespread{1.0}'))
    destination = tmp_path / 'final.pdf'
    with pytest.raises(ValueError, match='override'):
        freeze(tmp_path / 'not-read.pdf', destination, tex=source, contest='mcm')
    assert not destination.exists()


def test_layout_gate_records_source_and_style(tmp_path):
    import hashlib
    from pypdf import PdfWriter
    from scripts.freeze_pdf import freeze
    source = tmp_path / 'source.tex'
    source.write_text(paper())
    pdf = tmp_path / 'source.pdf'
    writer = PdfWriter(); writer.add_blank_page(width=612, height=792)
    with pdf.open('wb') as f: writer.write(f)
    import json
    from scripts.paper_template import ROOT as template_root
    runtime = json.loads((template_root/'templates/typesetting-runtime.json').read_text())
    build = tmp_path/'synthetic-build.json'
    # Synthetic provenance tests binding only; real compilation is tested in CI.
    build.write_text(json.dumps({'runtime':runtime, 'layout':check(source.read_text()),
        'tex_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()}))
    with pytest.raises(ValueError, match='build-receipt'):
        freeze(pdf, tmp_path/'missing.pdf', tex=source, contest='mcm')
    assert not (tmp_path/'missing.pdf').exists()
    receipt = freeze(pdf, tmp_path / 'final.pdf', tex=source, contest='mcm', build_receipt=build)
    pdf.write_bytes(pdf.read_bytes()+b'\n% changed after compilation')
    with pytest.raises(ValueError, match='does not match'):
        freeze(pdf, tmp_path/'stale.pdf', tex=source, contest='mcm', build_receipt=build)
    assert not (tmp_path/'stale.pdf').exists()
    assert receipt['layout']['tex_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt['layout']['profile'] == 'praxis-mcm-v1'


def test_optional_components_and_archived_chinese_source():
    import zipfile
    # A short paper need not have subsections, a TOC, symbols or algorithm boxes.
    check(paper())
    with zipfile.ZipFile(ROOT / 'demos/cumcm-1998-a/deliverables/supporting_materials.zip') as archive:
        check(archive.read('paper/main.tex').decode(), 'cumcm')


def test_optional_contents_separates_summary_and_body():
    check(paper().replace('Body.', table_of_contents() + r'\section{One argument}Body.'))
    check(paper())  # Neither contents nor subsections are compulsory.
    for bad in (r'\clearpage\tableofcontents\section{Body}',
                r'\tableofcontents\clearpage',
                '\\clearpage\\tableofcontents% \\clearpage\nBody.'):
        with pytest.raises(ValueError, match='Contents must'):
            check(paper().replace('Body.', bad))
    check(paper().replace('Body.', r'\clearpage\renewcommand{\contentsname}{Contents}\tableofcontents\clearpage'))


@pytest.mark.parametrize('override', [r'\setcounter{tocdepth}{3}', r'\renewcommand{\familydefault}{\sfdefault}'])
def test_rejects_hierarchy_and_font_default_changes(override):
    with pytest.raises(ValueError, match='override'):
        check(paper().replace('Body.', override))


def test_portable_chinese_profile_and_disclosure_match():
    import json
    import zipfile
    style = (ROOT / 'templates/cumcm-style.tex').read_text()
    profile = json.loads((ROOT / 'templates/cumcm-fonts.json').read_text())
    assert profile['profile'] == 'praxis-cumcm-v2'
    for name in profile['files']:
        assert name in style
    assert 'Songti SC' not in style and 'Heiti SC' not in style
    with zipfile.ZipFile(ROOT / 'demos/cumcm-1998-a/deliverables/supporting_materials.zip') as z:
        ai = z.read('paper/ai-use.tex').decode()
        for line in style.splitlines():
            if line.startswith('\\setCJK'):
                assert line in ai
        assert 'fontset=none' in ai
    from scripts.build_plugin import public_files
    assert ROOT / 'templates/cumcm-fonts.json' in public_files(ROOT)


def test_canonical_build_rejects_wrong_runtime_before_output(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import subprocess
    from scripts.paper_template import compile_paper
    source = tmp_path/'main.tex'; source.write_text(paper(), encoding='utf-8')
    output = tmp_path/'build'
    # These are refusal-path unit tests, not claims of an actual compiler run.
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout='Tectonic 0.16.0'))
    with pytest.raises(ValueError, match='requires Tectonic'):
        compile_paper(source, 'mcm', output, 'test-compiler')
    assert not output.exists()
    def wrong_bundle(command, **kwargs):
        return SimpleNamespace(stdout='Tectonic 0.17.0' if '--version' in command else b'wrong-bundle')
    monkeypatch.setattr(subprocess, 'run', wrong_bundle)
    with pytest.raises(ValueError, match='resource bundle'):
        compile_paper(source, 'mcm', output, 'test-compiler')
    assert not output.exists()


def test_build_receipt_cannot_silently_be_ignored(tmp_path):
    from scripts.freeze_pdf import freeze
    with pytest.raises(ValueError, match='require TeX'):
        freeze(tmp_path/'missing.pdf', tmp_path/'final.pdf', build_receipt=tmp_path/'receipt.json')
    assert not (tmp_path/'final.pdf').exists()


@pytest.mark.parametrize('contest', ['mcm', 'cumcm'])
@pytest.mark.parametrize('override', [
    r'\pagenumbering{roman}', r'\pagenumbering { arabic }',
    r'\setcounter{page}{0}', r'\setcounter { page } { 7 }',
    r'\addtocounter {page}{-1}', r'\renewcommand{\thepage}{\Roman{page}}',
    r'\renewcommand * { \thepage } {hidden}', r'\def \thepage {hidden}',
    r'\let\thepage\relax',
])
def test_page_numbering_cannot_be_overridden_outside_shared_block(contest, override):
    source = paper() if contest == 'mcm' else preamble(None, '中文', 'cumcm') + r'内容\end{document}'
    with pytest.raises(ValueError, match='page numbering'):
        check(source.replace(r'\end{document}', override + r'\end{document}'), contest)


def test_existing_mcm_generated_sources_and_chinese_skeleton_pass_new_frontmatter_gate():
    check((ROOT/'templates/mcm-paper.tex').read_text())
    check((ROOT/'research/merge-after-toll/paper/paper.tex').read_text())
    check((ROOT/'templates/cumcm-paper.tex').read_text(), 'cumcm')
    # Bath has a source generator rather than a checked-in generated paper.
    generator = (ROOT/'demos/mcm-2016-a/reproduce/build_report.py').read_text()
    assert "tex.append(summary_header('A'))" in generator
    assert 'tex.append(table_of_contents())' in generator


def test_summary_integrates_metadata_without_duplicate_running_header():
    header = summary_header('C')
    assert header.startswith(r'\thispagestyle{empty}')
    assert r'Page \thepage{} of \pageref{LastPage}' in header
    assert 'Team Control Number' in header
    check(paper())
    # Historical papers retain the former component; it does not reset pages.
    check(paper().replace(summary_header('B'), summary_header('B', legacy=True)))
    for altered in [paper().replace('Summary Sheet', 'Summary'),
                    paper().replace('Body.', summary_header('A') + 'Body.'),
                    paper().replace('Body.', r'\thispagestyle{empty}Body.'),
                    paper().replace(summary_header('B'), r'\clearpage' + summary_header('B'))]:
        with pytest.raises(ValueError):
            check(altered)


def test_contents_precedes_body_and_is_not_duplicated():
    for body in [r'\section{Introduction}Text.' + table_of_contents(),
                 table_of_contents() + table_of_contents()]:
        with pytest.raises(ValueError, match='Contents'):
            check(paper().replace('Body.', body))
    hook = r'\pretocmd{\section}{\Needspace{5\baselineskip}}{}{}'
    check(paper().replace(r'\begin{document}', r'\begin{document}' + hook))



def test_research_style_accepts_optional_structure_and_refuses_font_drift():
    from scripts.paper_template import style_block
    text = (r'\newcommand{\PraxisTitle}{A result}' + '\n' + style_block('research') +
            r'\title[A result]{A result}\begin{document}\begin{abstract}A claim.\end{abstract}'
            r'\maketitle\begin{theorem}A conditional result.\end{theorem}'
            r'\begin{proof}An argument.\end{proof}\end{document}')
    assert check(text, 'research')['profile'] == 'praxis-research-v1'
    check((ROOT/'templates/research-paper.tex').read_text(), 'research')
    check((ROOT/'demos/collatz-research/reproduce/paper/paper.tex').read_text(), 'research')
    for command in [r'\usepackage{newtxtext}', r'\usepackage{lmodern}',
                    r'\geometry{margin=20mm}', r'\linespread{1.3}']:
        with pytest.raises(ValueError, match='override'):
            check(text.replace(r'\maketitle', command+r'\maketitle'), 'research')
    with pytest.raises(ValueError, match='differs'):
        check(text.replace('margin=30mm', 'margin=25mm'), 'research')
    from scripts.build_plugin import public_files
    assert ROOT/'templates/research-style.tex' in public_files(ROOT)
    assert ROOT/'templates/research-paper.tex' in public_files(ROOT)


def test_cumcm_figure_data_and_proofs_follow_archived_records():
    import ast
    import json
    import re
    import zipfile
    with zipfile.ZipFile(ROOT/'demos/cumcm-1998-a/deliverables/supporting_materials.zip') as z:
        source = z.read('build_paper.py').decode()
        paper = z.read('paper/main.tex').decode()
        env = {'re': re, 'out': []}
        nodes = [n for n in ast.parse(source).body
                 if (isinstance(n, ast.FunctionDef) and n.name in
                     {'esc','T','fig_caption','fig_wrap','fig_margin_error','fig_baselines','fig_dropone'})
                 or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in
                     {'UNI','SYM','URL','GOPT'} for t in n.targets))]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<formatting>', 'exec'), env)
        for number, function, record in [(3,'fig_margin_error','robustness'),
                                         (4,'fig_baselines','alternatives'),
                                         (5,'fig_dropone','alternatives')]:
            groups = json.loads(z.read('reference/'+record+'.json'))['groups']
            env['out'].clear()
            env[function](groups['four'], groups['fifteen'], number)
            assert '\n'.join(env['out']).strip() in paper
        # Independent subtraction, not a second call of the chart implementation.
        assert '(1.322,2)' in paper  # (20.1907639778 - 18.8683846154) percentage points
        assert '(0.971,3)' in paper  # (32.2899959934 - 31.3188019073) percentage points
        assert 'axis cs:20.191,-1' not in paper
        assert paper.count(r'\begin{proof}') == paper.count(r'\end{proof}') == 3
        assert r'$\blacksquare$ 将' not in paper
        assert '∎' not in source


def test_research_running_title_is_explicit():
    text = (ROOT/'templates/research-paper.tex').read_text()
    with pytest.raises(ValueError, match='running title'):
        check(text.replace('[Mathematical research title]', ''), 'research')


def test_removed_table_is_rejected_but_forward_and_package_references_are_valid():
    from scripts.paper_template import check_explicit_references
    check_explicit_references(r"Table \ref{remaining}. Page \pageref{LastPage}. \label{remaining}")
    with pytest.raises(ValueError, match='removed'):
        check_explicit_references(r"Table \ref{remaining} and Table \ref{removed}. \label{remaining}")
    check_explicit_references("% \\ref{commented-out}\n" + r"\label{remaining} \eqref{remaining}")
def test_caption_review_distinguishes_short_titles_and_necessary_explanations():
    from scripts.paper_template import review_captions
    text = r'''% \caption{This comment is not a figure.}
\caption[Short list entry]{Rates $\frac{x}{y}$ and \{bounds\}.}
\captionof{table}{''' + 'condition ' * 41 + r'''}
\caption{''' + '比较' * 41 + r'''}'''
    result = review_captions(text)
    assert len(result['captions']) == 3
    assert result['captions'][0]['text'].endswith(r'\{bounds\}.')
    assert not result['captions'][0]['review_length']
    assert result['captions'][1]['kind'] == 'table'
    assert result['review_candidates'] == 2
    # Flags locate review targets; necessary long descriptions remain intact.
    assert result['captions'][1]['english_words'] == 41
    assert result['captions'][2]['chinese_characters'] == 82


def test_caption_review_does_not_claim_macro_or_malformed_coverage():
    from scripts.paper_template import review_captions
    result = review_captions(r'\mycaption{Unexpanded text}\caption{Unclosed')
    assert result['captions'] == []
    assert 'no rendered-line or semantic' in result['scope']
