"""Independent literal examples: diagnostics are candidates and never reject prose."""
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.check_claims import inspect as claims
from scripts.check_prose import inspect as prose
from scripts.check_summary import inspect as summary
from scripts.manuscript import (
    load_json, plain_text, quantities, sections, significant_digits, strip_comments,
)


def codes(result):
    assert result['schema_version'] == 1
    assert result['diagnostic_only'] is True
    assert all(set(w) == {'code', 'message', 'location'} for w in result['warnings'])
    json.dumps(result, allow_nan=False)
    return {w['code'] for w in result['warnings']}


def paper(summary_text, body='We explain the model and its measured response.', conclusion=''):
    return (r'\begin{document}' + '\n' + r'\PraxisSummaryHeading{Summary}' + '\n' + summary_text
            + '\n\\clearpage\n\\section{Model}\n' + body
            + ('\n\\section{Conclusion}\n' + conclusion if conclusion else '') + '\n\\end{document}')


def test_summary_valid_short_independent_example():
    result = summary(paper('We use regression to estimate 60.2\\% coverage. We recommend a 3 day trial.'),
                     {'coverage': 0.602})
    assert not codes(result)
    assert result['metrics']['quantity_count'] == 2
    assert result['metrics']['first_paragraph_sentences'] == 2


def test_summary_explicit_bad_cases_and_late_symbol_definition():
    text = ('We estimate $x$ over 3 days. We present estimates. We describe outcomes. '
            'We report the response.\n\nHowever, it cannot identify a universal optimum.')
    result = summary(paper(text, 'Let $x$ denote the response.'))
    assert {'summary_first_paragraph_long', 'summary_method_missing',
            'summary_limiting_last_sentence', 'summary_symbol_defined_later'} <= codes(result)
    assert result['metrics']['symbols_defined_later'] == ['x']


def test_summary_local_definition_and_decimal_are_legal():
    result = summary(r'We use an ODE. Let $x$ denote coverage of 60.2\%. We choose 2 days.')
    assert not codes(result)
    assert result['metrics']['first_paragraph_sentences'] == 3
    assert result['metrics']['math_symbols'] == ['x']


def test_summary_abstract_custom_title_and_quantity_boundaries():
    assert summary(r'\begin{abstract}Regression gives 3 km.\end{abstract}')['metrics']['quantity_count'] == 1
    custom = paper('Regression gives 3 km.').replace('{Summary}', '{A practical model}')
    assert summary(custom)['metrics']['summary_regions'] == 1
    result = summary('A model works. See Figure 3 in 2026.')
    assert 'summary_quantity_count' in codes(result)
    result = summary('Regression gives ' + ', '.join(f'{i} days' for i in range(1, 10)) + '.')
    assert result['metrics']['quantity_count'] == 9
    assert 'summary_quantity_count' in codes(result)


def test_summary_word_boundaries_and_missing_document_region():
    assert 'summary_method_missing' in codes(summary('The coding proceeds over 2 days.', method_terms=['ODE']))
    assert 'summary_not_unique' in codes(summary(r'\begin{document}\section{Model}Text.\end{document}'))
    with pytest.raises(ValueError):
        summary('Text', method_terms=[])


def test_summary_subscript_variants_and_notation_table_definition():
    result = summary(paper(r'Regression estimates $x_1$ over 3 days.',
                           r'\begin{tabular}{ll}$x_{1}$ & Measured response\\\end{tabular}'))
    assert result['metrics']['symbols_defined_later'] == ['x_1']
    assert 'summary_symbol_defined_later' in codes(result)


def test_comments_math_verbatim_and_public_url_do_not_create_syntax_claims():
    tex = r'''\begin{document}
\section{Model}
This is $x_i$ and \(y_j\).
\begin{align} z_k &= 1 \\ w_l &= 2 \end{align}
\begin{equation} q_m = 3 \end{equation}
% secret_value /Users/private 20261014T024934-616bd085
Escaped value\_name and \url{https://github.com/a/b/blob/0123456789abcdef/script_name.py}.
\begin{verbatim}raw_name % untouched\end{verbatim}
Actual bad_name is outside math.
\end{document}'''
    result = prose(tex, ['Model\nThe procedure estimates an independently measured effect.'], problem_year=2023)
    assert codes(result) == {'prose_text_subscript'}
    assert len(result['metrics']['text_subscripts']) == 1
    masked = strip_comments(tex)
    assert len(masked) == len(tex)
    assert 'secret_value' not in masked
    assert 'raw_name % untouched' in masked


def test_prose_uses_pdf_not_tex_and_exempts_honest_limitations():
    tex = r'''\begin{document}
\section{Model}
TeX cannot be used to fabricate the measured PDF statistic.
\section{Strengths and Limitations}
We cannot identify everything about this process.
\subsection{Sampling}
We cannot establish unrestricted causal effects here.
\section{Conclusion}
We recommend taking the selected next step.
\section{References}
Source 2020.
\appendix
\section{Derivation}
Appendix materials.
\end{document}'''
    pages = ['1 Model\nThe model estimates a stable independently measured response.\n'
             '2 Strengths and Limitations\nWe cannot identify all possible responses in nature.\n'
             '2.1 Sampling\nWe cannot extrapolate unrestricted claims from these observations.\n'
             '3 Conclusion\nThe selected policy improves the measured local outcome.\n'
             'References\n2020.\nA Derivation\nWe cannot measure the unobserved environmental response.']
    result = prose(tex, pages, problem_year=2023)
    assert not codes(result)
    assert result['metrics']['mapping_status'] == 'mapped_literal_headings'
    assert result['metrics']['body_sentences'] == 2
    assert result['metrics']['negative_sentences'] == 0
    assert result['metrics']['neg_ratio'] == 0


def test_prose_appendix_without_rendered_heading_keeps_boundary_unknown():
    tex = r'\section{Model}Body.\appendix Appendix prose has no literal heading.'
    result = prose(tex, ['Model\nThe body contains a stable measured response.\nAppendix prose has no literal heading.'], problem_year=2023)
    assert 'prose_section_mapping_uncertain' in codes(result)
    assert result['metrics']['neg_ratio'] is None


def test_prose_calibration_formula_and_lexical_scope():
    tex = r'\section{Model}The source prose is separate.'
    pdf = ['Model\nWe cannot estimate the final response from this sample. '
           'The independent model yields a stable measured response. '
           'Short no.']
    result = prose(tex, pdf, problem_year=2023)
    assert result['metrics']['body_sentences'] == 2
    assert result['metrics']['neg_ratio'] == 0.5
    assert 'prose_negation_ratio' in codes(result)


@pytest.mark.parametrize('pdf', [
    ['Model\nFirst body.\nLimitations\nExcluded text.\nModel\nRunning header.'],
    ['A differently named Model title\nThe selected response is stable.'],
])
def test_prose_mapping_uncertainty_is_reported_and_no_false_exact_ratio(pdf):
    tex = r'\section{Model}Body.\section{Limitations}Exempt.'
    result = prose(tex, pdf, problem_year=2023)
    assert 'prose_section_mapping_uncertain' in codes(result)
    assert result['metrics']['neg_ratio'] is None
    assert result['metrics']['body_sentences'] is None


def test_prose_precision_leaks_boundaries_exemptions_and_commit_urls():
    tex = r'\section{Model}Body.\section{Reproducibility}Exempt.\section{Conclusion}Decision.'
    pages = ['Model\nThe cost is $122.649928 million for 1234567 people, with 0.123456% coverage. '
             'The measurement is 0.123456789 km. '
             'Run 20261014T024934-616bd085 uses abcdef1234567890 in /Users/example/private/report and C:\\work\\run. '
             'The public source is https://github.com/a/b/blob/0123456789abcdef/script.py . '
             'Identifier xabcdef1234567890z is a word.\n'
             'Reproducibility\nRun 20261014T024934-616bd085 at /Users/example/reproduce.\n'
             'Conclusion\nThe chosen policy improves the observed response.']
    result = prose(tex, pages, problem_year=2023)
    kinds = [c['kind'] for c in result['metrics']['process_leak_candidates']]
    assert kinds.count('run_identifier') == 1
    assert kinds.count('hex_identifier') == 1
    assert kinds.count('local_path') == 2
    assert len(result['metrics']['precision_candidates']) == 3
    assert 'prose_process_leak' in codes(result)


def test_prose_chronology_is_reference_only_and_explicit_override():
    tex = r'''\section{Model}2026 appears in the body.
\section{References}A reference (2024). Another in 2020.
\url{https://example.org/2026/source}'''
    pages = ['Model\nThe source date has a defined local role.\nReferences\nA 2024 citation.']
    result = prose(tex, pages, problem_year=2023)
    assert [item['year'] for item in result['metrics']['later_reference_years']] == [2024]
    assert 'prose_anachronistic_reference' in codes(result)
    allowed = prose(tex, pages, problem_year=2023, allow_anachronism=True)
    assert 'prose_anachronistic_reference' not in codes(allowed)
    assert allowed['metrics']['later_reference_years']


def test_prose_image_pdf_and_invalid_inputs():
    result = prose(r'\section{Model}Text.', ['', ''], problem_year=2023)
    assert 'prose_pdf_text_missing' in codes(result)
    assert result['metrics']['neg_ratio'] is None
    with pytest.raises(TypeError):
        prose('Text', 'fabricated page')
    with pytest.raises(ValueError):
        prose('Text', ['Page'], problem_year=True)


def test_prose_escaped_underscore_parity_and_summary_precision():
    tex = paper(r'Regression gives \$122.649928 million.', r'Good\_word then bad\\_word.')
    result = prose(tex, ['Summary\nRegression gives $122.649928 million.\nModel\nThe selected local response is stable and measured.'], problem_year=2023)
    assert len(result['metrics']['text_subscripts']) == 1
    assert len(result['metrics']['precision_candidates']) == 1


def test_claims_exact_rounding_fraction_and_named_scale_support():
    tex = paper(r'Regression gives 60.2\% coverage, \SI{12.3}{km}, and a \$1.23 million budget.',
                'Body table is separate.', r'We recommend a 30 day trial.')
    result = claims(tex, {'coverage': 0.602, 'distance': 12.34, 'budget': 1234567, 'trial': 30})
    assert not codes(result)
    assert result['metrics']['claim_count'] == 4
    assert result['metrics']['supported_count'] == 4
    supports = [claim['support'] for claim in result['metrics']['claims']]
    assert any(s['interpretation'] == 'percent_as_fraction' for s in supports)
    assert any(s['comparison'] == 'display_rounding' for s in supports)
    assert any(s['interpretation'] == 'million_as_base_units' for s in supports)


def test_claims_mismatch_caught_and_figures_years_refs_not_claims():
    tex = paper(r'Regression yields 60.2\%. Figure 3 and Section 2 describe the 2023 study.',
                r'Table \ref{tab:one} has evidence. \begin{tabular}{lr}Coverage & 60.2\%\\\end{tabular}',
                r'The result is 70.2\%.')
    result = claims(tex)
    assert 'claim_value_unmatched' in codes(result)
    assert result['metrics']['claim_count'] == 2
    assert result['metrics']['unmatched_count'] == 1
    assert result['metrics']['body_tables'] == 1


def test_claims_body_table_is_evidence_key_section_and_appendix_table_are_not():
    tex = paper(r'Regression gives 12 km.',
        r'\begin{tabular}{lr}Distance & 12.004\\\end{tabular}', r'The plan lasts 3 days.')
    tex = tex.replace(r'\end{document}', r'\appendix\begin{tabular}{lr}Trial & 3\\\end{tabular}\end{document}')
    result = claims(tex)
    assert result['metrics']['supported_count'] == 1
    assert result['metrics']['unmatched_count'] == 1
    assert result['metrics']['body_tables'] == 1


def test_claims_memo_chinese_units_scientific_notation_and_comments():
    tex = (r'\section{Summary}Regression gives 1.2e3 kg and 2.5亿元.'
           '\n% omitted 999 days\n' + r'\section{Model}Body.'
           r'\section{Memo}Use 50 counties.\section{Conclusion}Wait 30 days.')
    result = claims(tex, {'mass': 1200, 'money': 2.5, 'count': 50, 'wait': 30})
    assert not codes(result)
    assert result['metrics']['claim_count'] == 4


def test_claims_zero_sign_and_non_finite_results_are_explicit():
    tex = paper(r'Regression gives 0\% and -3 kg.')
    assert not codes(claims(tex, {'zero': 0, 'negative': -3}))
    with pytest.raises(ValueError):
        claims(tex, {'x': float('nan')})
    assert 'claim_value_unmatched' in codes(claims(paper('Regression gives 3 days.'), {'x': True, 'id': '3'}))


def test_literal_parser_sections_and_quantity_coverage():
    tex = r'\newcommand{\fake}{\section{Limitations}}\section{Model}Body.\section{Limitations}Exempt.\subsection{Details}Still exempt.\section{Next}Body.'
    parts = sections(tex)
    assert [p['title'] for p in parts if p['title']] == ['Model', 'Limitations', 'Details', 'Next']
    assert next(p for p in parts if p['title'] == 'Details')['kind'] == 'limitations'
    assert [q['literal'] for q in quantities('Figure 12 in 2026 has 50 counties and 1.2e3 kg.')] == ['50', '1.2e3']
    assert plain_text(r'\SI{3.5}{km} and 60.2\%').strip() == '3.5 km and 60.2%'
    assert significant_digits('0.000123456') == 6
    assert significant_digits('1.2300e-3') == 5


def test_cli_warning_is_zero_exit_and_illegal_json_is_rejected(tmp_path):
    tex = tmp_path / 'paper.tex'
    tex.write_text(paper('A model gives 99 days.'), encoding='utf-8')
    for module in ('scripts.check_summary', 'scripts.check_claims'):
        process = subprocess.run([sys.executable, '-m', module, str(tex)], capture_output=True, text=True)
        assert process.returncode == 0, process.stderr
        assert json.loads(process.stdout)['warnings']
    malformed = tmp_path / 'results.json'
    malformed.write_text('{"x":1,"x":2}', encoding='utf-8')
    process = subprocess.run([sys.executable, '-m', 'scripts.check_claims', str(tex), '--results', str(malformed)],
                             capture_output=True, text=True)
    assert process.returncode != 0
    assert 'Duplicate JSON key' in process.stderr
    with pytest.raises(ValueError):
        load_json(malformed)


def test_prose_cli_extracts_real_pdf_text(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    tex = tmp_path / 'paper.tex'
    tex.write_text(r'\section{Model}The source says nothing about negative sentences.', encoding='utf-8')
    pdf = tmp_path / 'paper.pdf'
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 50 740 Td (Model) Tj 0 -20 Td (We cannot estimate every possible unobserved process here.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    with pdf.open('wb') as handle:
        writer.write(handle)
    process = subprocess.run([sys.executable, '-m', 'scripts.check_prose', str(tex), str(pdf), '--problem-year', '2023'],
                             capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result['metrics']['negative_sentences'] == 1
    assert result['metrics']['neg_ratio'] == 1
    assert 'prose_negation_ratio' in codes(result)
