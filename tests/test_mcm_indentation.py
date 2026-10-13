"""Rendered independent-answer checks of current and archived paragraph roles."""
import shutil

import pytest

from scripts.paper_template import compile_paper, preamble, summary_header, summary_heading


BODY = r"""MSummaryFirst identifies the opening paragraph after the summary heading.\par
MSummaryLater identifies a subsequent ordinary summary paragraph.\par
\section{First-level heading}
MSectionFirst identifies the paragraph following a section.\par
MSectionLater identifies a later ordinary section paragraph.\par
\subsection{Second-level heading}
MSubsectionFirst identifies the paragraph following a subsection.\par
MSubsectionLater identifies a later ordinary subsection paragraph.\par
\subsubsection{Third-level heading}
MSubsubsectionFirst identifies the paragraph following a subsubsection.\par
MSubsubsectionLater identifies a later ordinary subsubsection paragraph.\par
\noindent MBaseMargin identifies the unindented text boundary.\par
\begin{itemize}\item MListItem role remains a list.\end{itemize}
\begin{figure}[h]\centering\rule{2cm}{1pt}\caption{MCaption role remains centered.}\end{figure}
\begingroup\normalsize\setlength{\parindent}{0pt}\hangindent=1.5em
MReference role retains its local hanging formatting.\linebreak
MReferenceContinuation retains the hanging continuation-line offset.\par\endgroup
\noindent MDearDirector,\par
\noindent MSincerely,\par
\end{document}
"""
FIRST = ['MSummaryFirst', 'MSectionFirst', 'MSubsectionFirst', 'MSubsubsectionFirst']
LATER = ['MSummaryLater', 'MSectionLater', 'MSubsectionLater', 'MSubsubsectionLater']
FLUSH_ROLES = ['MReference', 'MDearDirector', 'MSincerely']
OTHER_ROLES = ['MListItem', 'MCaption']
HANGING_ROLES = ['MReferenceContinuation']


def fixture_source(version):
    return (preamble('1234567', 'Indentation regression fixture', layout_version=version)
            + summary_header('C', edition=2020, layout_version=version)
            + summary_heading(layout_version=version) + BODY)


def marker_left_edges(pdf):
    """Measure matching leading M glyphs, eliminating glyph-sidebearing effects."""
    import pypdfium2 as pdfium
    from pypdfium2 import raw
    edges = {}
    with pdfium.PdfDocument(str(pdf)) as document:
        for page in document:
            textpage = page.get_textpage()
            try:
                text = ''.join(chr(raw.FPDFText_GetUnicode(textpage, i))
                               for i in range(textpage.count_chars()))
                for marker in FIRST + LATER + FLUSH_ROLES + OTHER_ROLES + HANGING_ROLES + ['MBaseMargin']:
                    position = text.find(marker)
                    if position >= 0:
                        assert marker not in edges, 'fixture marker duplicated'
                        edges[marker] = textpage.get_charbox(position)[0]
            finally:
                textpage.close()
                page.close()
    assert set(edges) == set(FIRST + LATER + FLUSH_ROLES + OTHER_ROLES + HANGING_ROLES + ['MBaseMargin'])
    return {marker: x - edges['MBaseMargin'] for marker, x in edges.items()}


@pytest.mark.skipif(shutil.which('tectonic') is None, reason='Canonical Tectonic compiler is unavailable')
@pytest.mark.parametrize('version, first_em, later_em', [(3, 0, 1.5), (4, 2, 2)])
def test_compiled_heading_and_summary_indentation(tmp_path, version, first_em, later_em):
    tex = tmp_path / f'indentation-v{version}.tex'
    tex.write_text(fixture_source(version))
    receipt = compile_paper(tex, 'mcm', tmp_path / 'compiled',
                            layout_mode='archive' if version == 3 else 'current')
    assert receipt['layout']['profile'] == f'praxis-mcm-v{version}'
    measured = marker_left_edges(tmp_path / f'compiled/indentation-v{version}.pdf')
    # newtx 12pt regular body: one em is 12 TeX pt; PDF uses 72/72.27 units.
    em_pdf = 12 * 72 / 72.27
    for marker in FIRST:
        assert measured[marker] == pytest.approx(first_em * em_pdf, abs=.15)
    for marker in LATER:
        assert measured[marker] == pytest.approx(later_em * em_pdf, abs=.15)
    for marker in FLUSH_ROLES:
        assert measured[marker] == pytest.approx(0, abs=.15)
    for marker in HANGING_ROLES:
        assert measured[marker] == pytest.approx(1.5 * em_pdf, abs=.15)
