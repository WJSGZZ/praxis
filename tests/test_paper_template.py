from pathlib import Path

import pytest

from scripts.paper_template import check, preamble, summary_header


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
    assert check(text, 'cumcm')['profile'] == 'praxis-cumcm-v1'
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
    receipt = freeze(pdf, tmp_path / 'final.pdf', tex=source, contest='mcm')
    assert receipt['layout']['tex_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt['layout']['profile'] == 'praxis-mcm-v1'


def test_optional_components_and_archived_chinese_source():
    import zipfile
    # A short paper need not have subsections, a TOC, symbols or algorithm boxes.
    check(paper())
    with zipfile.ZipFile(ROOT / 'demos/cumcm-1998-a/deliverables/supporting_materials.zip') as archive:
        check(archive.read('paper/main.tex').decode(), 'cumcm')


@pytest.mark.parametrize('override', [r'\setcounter{tocdepth}{3}', r'\renewcommand{\familydefault}{\sfdefault}'])
def test_rejects_hierarchy_and_font_default_changes(override):
    with pytest.raises(ValueError, match='override'):
        check(paper().replace('Body.', override))
