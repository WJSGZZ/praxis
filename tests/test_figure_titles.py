"""Project short-title profile; scientific interpretation stays an editorial check."""
import pytest

from scripts.paper_template import (check, preamble, review_figure_titles,
                                   summary_header, summary_heading)


def paper(caption):
    return (preamble(title='A supported answer') + summary_header('A', edition=2016)
            + summary_heading() + r'An adjacent explanation.\begin{figure}'
            + r'\caption{' + caption + r'}\end{figure}\end{document}')


def test_previous_repeated_short_plus_explanation_case_is_refused():
    caption = 'Final cell-average temperatures. The three layers share a color scale; distances are in metres.'
    with pytest.raises(ValueError, match='adjacent prose'):
        check(paper(caption), layout_mode='current')
    # Historical recorded sources remain reproducible under deliberate archive.
    check(paper(caption), layout_mode='archive')


def test_short_title_and_adjacent_required_interpretation_are_accepted():
    text = paper('Final cell-average temperatures').replace(
        'An adjacent explanation.', 'The panels share a color scale. Axes give the measured distances in metres.')
    check(text, layout_mode='current')
    assert review_figure_titles(text)['titles'][0]['english_words'] == 3


@pytest.mark.parametrize('title', [
    ' '.join(['object'] * 16),
    'A short title! The interval represents uncertainty.',
    'A short title? Here are the methods.',
    '',
])
def test_current_title_rejects_prose_or_empty_and_overlong_shapes(title):
    assert review_figure_titles(paper(title))['errors']


@pytest.mark.parametrize('caption', [
    r'\caption*{\normalsize\textbf{Figure \thefigure.} Richness and drought insurance}',
    r'\caption[Short listing title]{Temperature at $t=0.5$ hours}',
    r'\caption{U.S. medal forecasts}',
    r'\caption{Temperature vs. flow}',
    r'\caption{\emph{Nominal} temperature range}',
])
def test_star_optional_listing_math_acronym_and_nested_title_are_supported(caption):
    result = review_figure_titles(r'\begin{figure}' + caption + r'\end{figure}')
    assert len(result['titles']) == 1 and result['errors'] == []


def test_captionof_figure_is_checked_and_table_caption_is_excluded():
    result = review_figure_titles(r'\captionof{figure}{Temperature. Long explanation.}'
                                 + r'\captionof{table}{Inputs. Unrelated table notes.}')
    assert len(result['titles']) == 1 and result['errors']


def test_definitions_and_literal_source_quotes_do_not_create_figures():
    quoted = (r'\newcommand{\quoted}{\begin{figure}\caption{Title. Explanation.}\end{figure}}'
              + r'\begin{Verbatim}\begin{figure}\caption{Title. Explanation.}\end{figure}\end{Verbatim}')
    assert review_figure_titles(quoted)['titles'] == []


def test_two_figures_cannot_hide_a_bad_caption_behind_one_good_title():
    text = (r'\begin{figure}\caption{First short title}\end{figure}'
            + r'\begin{figure}\caption{Second title. Extra sentence.}\end{figure}')
    result = review_figure_titles(text)
    assert len(result['titles']) == 2 and len(result['errors']) == 1


@pytest.mark.parametrize('tail', [
    r'\par\noindent Curves within one group merge at a nominated point.',
    r'\medskip\begin{minipage}{0.9\linewidth}All three categories use complete denominators.\end{minipage}',
])
def test_short_caption_cannot_hide_a_centered_explanation_inside_figure(tail):
    result = review_figure_titles(r'\begin{figure}\caption{A short title}\label{fig:one}' + tail + r'\end{figure}')
    assert any('post-caption explanation' in error for error in result['errors'])


def test_caption_label_and_environment_closings_are_allowed():
    text = r'\begin{figure}\begin{center}\caption{A short title}\label{fig:one}\end{center}\end{figure}'
    assert review_figure_titles(text)['errors'] == []


def test_explanation_cannot_be_moved_before_caption_inside_a_minipage():
    text = (r'\begin{figure}\centering\begin{minipage}{\linewidth}'
            r'All three categories use complete denominators.\end{minipage}'
            r'\caption{Category star-rating profiles}\end{figure}')
    assert any('ordinary prose inside figure' in error for error in review_figure_titles(text)['errors'])


def test_graphic_axis_labels_and_image_files_are_not_body_prose():
    text = (r'\begin{figure}\begin{tikzpicture}\begin{axis}[xlabel={Time (h)}]'
            r'\addplot coordinates {(0,1) (1,2)};\end{axis}\end{tikzpicture}'
            r'\includegraphics{graph-name.pdf}\caption{Temperature vs. flow}\end{figure}')
    assert review_figure_titles(text)['errors'] == []


@pytest.mark.parametrize('counter', [r'\refstepcounter{figure}', r'\stepcounter{figure}',
                                     r'\addtocounter{figure}{1}', r'\setcounter{figure}{2}'])
def test_manual_figure_counter_arguments_are_metadata_not_prose(counter):
    text = (r'\begin{figure}[H]' + counter + r'\centering'
            + r'\includegraphics[width=\linewidth]{figures/richness.pdf}'
            + r'\caption*{\normalsize\textbf{Figure \thefigure.} Richness and drought insurance}\end{figure}')
    assert review_figure_titles(text)['errors'] == []


@pytest.mark.parametrize('graphic', [r'\rule{2cm}{1pt}', r'\rule[1pt]{2cm}{1pt}'])
def test_rule_dimensions_are_graphical_parameters_not_prose(graphic):
    text = r'\begin{figure}\centering' + graphic + r'\caption{A short title}\end{figure}'
    assert review_figure_titles(text)['errors'] == []
