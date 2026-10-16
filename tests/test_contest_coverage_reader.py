import json
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from scripts import contest_coverage as coverage
from scripts import reader_packet


def source():
    return r'''\documentclass{article}\begin{document}
\section*{Summary}\label{sum:p1}We store 5 litres safely.
\clearpage\section{Model}\label{body:p1}We store 5 litres safely.
\begin{figure}A diagram.\caption{Flow}\label{fig:flow}\end{figure}
\section{Assumptions}\begin{tabular}{ll}Closed vessel&No leak\end{tabular}
\section{Sensitivity}\label{check:a1}Vary capacity and keep the conclusion.
\section{Strengths}Conservation.
\section{Weaknesses}Unknown future supply.
\section{Conclusions}\label{end:p1}We store 5 litres safely.
\clearpage\section*{Memo}Store 5 litres this afternoon.
\end{document}'''


def inputs():
    return ({'problem_items': [{'id': 'P1', 'quote': 'Find water.'}],
             'paper_locations': {'P1': {'summary': 'label:sum:p1', 'body': 'label:body:p1',
                                         'conclusion': 'label:end:p1'}},
             'assumptions': [{'id': 'A1', 'test_location': 'label:check:a1'}],
             'sensitivity': {'parameters': ['capacity'], 'conclusion_parameters': ['capacity'],
                             'location': 'label:check:a1'}},
            {'symbols': [{'symbol': 'X'}], 'spatial': True},
            {'figures': [{'id': 'fig:flow', 'kind': 'structure', 'reader_question': 'Where does water go?',
                          'data_source': 'The mass balance', 'section': 'Model'}],
             'omissions': [{'kind': 'map', 'reason': 'A synthetic one-vessel example has no spatial locations.'}],
             'few_figures_reason': 'This one-balance example is conveyed fully by its diagram and scalar table.'})


def test_declared_locations_are_checked_in_their_actual_sections():
    requirements, contract, plan = inputs()
    result = coverage.inspect(requirements, source(), contract, plan)
    assert result['diagnostic_only'] is True
    assert result['warnings'] == []
    assert result['locations'][0]['summary']['section'] == 'Summary'
    requirements['paper_locations']['P1']['summary'] = 'label:body:p1'
    result = coverage.inspect(requirements, source(), contract, plan)
    assert any(w['code'] == 'coverage.answer_location' for w in result['warnings'])
    assert result['locations'][0]['summary'] is None


def test_bad_components_warn_instead_of_claiming_a_scientific_verdict():
    requirements, contract, plan = inputs()
    requirements['assumptions'][0]['test_location'] = 'label:missing'
    requirements['sensitivity']['parameters'] = ['rain']
    plan['figures'] = []
    plan['omissions'] = []
    plan.pop('few_figures_reason')
    tex = source().replace(r'\clearpage\section*{Memo}', r'\section*{Memo}')
    tex = tex.replace('Store 5 litres this afternoon.', r'Use $X=5$ litres this afternoon.')
    result = coverage.inspect(requirements, tex, contract, plan)
    codes = {warning['code'] for warning in result['warnings']}
    assert {'coverage.assumption_test', 'coverage.sensitivity_intersection', 'coverage.memo_page',
            'coverage.memo_math', 'coverage.memo_symbols', 'coverage.figure_count',
            'coverage.figure_omission', 'coverage.figure_number_reason'} <= codes
    assert 'passed' not in result


def test_comment_does_not_supply_a_missing_answer_or_figure_label():
    requirements, contract, plan = inputs()
    tex = source().replace(r'\label{sum:p1}', '% \\label{sum:p1}\n')
    tex = tex.replace(r'\label{fig:flow}', '% \\label{fig:flow}\n')
    result = coverage.inspect(requirements, tex, contract, plan)
    assert any(w['code'] == 'coverage.answer_location' for w in result['warnings'])
    assert any(w['code'] == 'coverage.figure_label' for w in result['warnings'])


def test_reader_selection_retains_continuations_and_explicit_unlabelled_pages():
    pages = ['Summary\nOur answer.', 'Contents\nConclusions 5\nMemo 7',
             'Figure 1. A measured curve.', 'Unlabelled map.',
             'Team # 7391856\nPage 5 of 8\n6 Conclusions\nA result.',
             'Team # 7391856\nPage 6 of 8\nMore concluding evidence.',
             'Memo\nTo: committee\nA recommendation.', 'References\nA citation.']
    records = reader_packet.select_pages(pages, extra_pages=[4])
    assert [row['original_page'] for row in records] == [1, 3, 4, 5, 6, 7]
    assert records[4]['reasons'] == ['conclusion_continuation_candidate']
    with pytest.raises(ValueError, match='inside the PDF'):
        reader_packet.select_pages(pages, extra_pages=[True])


def pdf_with_text(path, pages):
    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({
            NameObject('/F1'): writer._add_object(font)})})
        content = DecodedStreamObject()
        escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        content.set_data(f'BT /F1 12 Tf 72 700 Td ({escaped}) Tj ET'.encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(content)
    with path.open('wb') as stream:
        writer.write(stream)


def test_reader_packet_writes_real_selected_pdf_and_nonprefilled_review(tmp_path):
    pdf = tmp_path / 'paper.pdf'
    pdf_with_text(pdf, ['Summary', 'Unselected body', 'Figure 1. Result', 'Conclusions', 'References'])
    original = pdf.read_bytes()
    destination = tmp_path / 'reader'
    receipt = reader_packet.build(pdf, destination,
                                  {'problem_items': [{'id': 'P1', 'quote': 'Give a policy.'}]})
    packet = PdfReader(destination / 'packet.pdf')
    assert [page.extract_text() for page in packet.pages] == ['Summary', 'Figure 1. Result', 'Conclusions']
    assert receipt['packet_pages'] == 3 and receipt['source_pages'] == 5
    assert pdf.read_bytes() == original
    template = json.loads((destination / 'reader-review-template.json').read_text())
    assert template['type'] == 'reader' and template['problem_items'][0]['answer_found'] is None
    with pytest.raises(FileExistsError):
        reader_packet.build(pdf, destination, {'problem_items': [{'id': 'P1', 'quote': 'Give a policy.'}]})


def test_reader_missing_answers_warn_and_all_item_ids_are_required():
    items = [{'id': 'P1'}, {'id': 'P2'}]
    review = {'type': 'reader', 'problem_items': [
        {'id': 'P1', 'answer_found': 'no', 'answer_one_line': 'Unknown',
         'why_credible': 'No answer found', 'top_question': 'What is the actual decision?'}]}
    warnings = reader_packet.review_warnings(review, items)
    assert {w['code'] for w in warnings} == {'reader.answer_missing', 'reader.item_missing'}
    review['problem_items'][0]['answer_found'] = 'yes'
    review['problem_items'].append(dict(review['problem_items'][0], id='P2'))
    assert reader_packet.review_warnings(review, items) == []


def test_shared_v5_memo_and_strength_environments_are_real_components():
    from scripts.manuscript import sections
    requirements, contract, plan = inputs()
    tex = source().replace(r'\section{Strengths}Conservation.', r'\begin{strengths}\item Conservation.\end{strengths}')
    tex = tex.replace(r'\section{Weaknesses}Unknown future supply.', r'\begin{weaknesses}\item Unknown supply.\end{weaknesses}')
    tex = tex.replace(r'\clearpage\section*{Memo}Store 5 litres this afternoon.',
                      r'\begin{memo}{Committee}{May 2020}{Store water}Store 5 litres this afternoon.\end{memo}')
    result = coverage.inspect(requirements, tex, contract, plan)
    assert result['warnings'] == []
    memo = next(part for part in sections(tex) if part['kind'] == 'memo')
    assert 'Store 5 litres' in tex[memo['content_start']:memo['end']]
    assert 'Committee' not in tex[memo['content_start']:memo['end']]


def test_empty_shared_summary_title_and_named_committee_report_are_recognized():
    from scripts.manuscript import sections
    tex = (r'\begin{document}\PraxisSummaryHeading{}A result.\clearpage'
           r'\section*{Report to the Kenyan Tourism and Wildlife Committee}An action.\end{document}')
    parts = sections(tex)
    assert [(part['title'], part['kind']) for part in parts] == [
        ('Summary', 'summary'), ('Report to the Kenyan Tourism and Wildlife Committee', 'memo')]
    pages = ['Summary\nA result.', 'Report to the Kenyan Tourism and Wildlife Committee\nAn action.',
             'Committee report: page 2 of 2\nCosts.', 'References\nA citation.']
    assert [row['original_page'] for row in reader_packet.select_pages(pages)] == [1, 2, 3]


def test_shared_literal_paper_title_does_not_disable_pdf_body_leak_scan():
    from scripts import check_prose
    tex = (r'\newcommand{\PraxisTitle}{Where Conservation Works}'
           r'\begin{document}\PraxisSummaryHeading{\PraxisTitle}A summary.\clearpage'
           r'\section{Model}This estimate used run 20261016T052000-abcdef12.\end{document}')
    result = check_prose.inspect(tex, ['Where Conservation Works\nA summary.',
                                      '1 Model\nThis estimate used run 20261016T052000-abcdef12.'],
                                 problem_year=2023)
    assert result['metrics']['mapping_status'] == 'mapped_literal_headings'
    assert result['metrics']['process_leak_candidates'][0]['kind'] == 'run_identifier'


def test_argument_led_final_section_is_included_before_a_named_committee_report():
    pages = ['Summary', 'Model', 'Verification and the decision to implement',
             'Final decision continued', 'Report to the Kenyan Tourism and Wildlife Committee',
             'Committee report: page 2 of 2', 'References']
    records = reader_packet.select_pages(pages)
    assert [row['original_page'] for row in records] == [1, 3, 4, 5, 6]
    assert 'last_body_conclusion_candidate' in records[1]['reasons']
