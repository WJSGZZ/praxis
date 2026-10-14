"""Current final-delivery refusals, independent of historical reproduction.

The PDF operators below are real readable files. Their synthetic build receipts
exercise the final binding boundary and do not claim an actual compiler run.
Canonical TeX compilation is covered separately by compiler-available tests.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from scripts.check_pdf import MCM_PAGE_REVIEW_CHECKS, inspect_font_sizes, inspect_mcm_delivery_format
from scripts.freeze_pdf import freeze
from scripts.paper_template import (ROOT, check, compile_paper, inspect_typesetting_log,
                                   preamble, summary_header, summary_heading)


def source(version=4, body='Ordinary summary evidence.'):
    return (preamble('1234567', 'A conditional answer', layout_version=version)
            + summary_header('C', edition=2020, layout_version=version)
            + summary_heading(layout_version=version) + body + r'\end{document}')


def actual_pdf(path, *, letter=False, small_math=False, small_prose=False, unmapped_math=False,
               team='1234567', edition='2020', running_header=None):
    writer = PdfWriter()
    width, height = (612, 792) if letter else (210 / 25.4 * 72, 297 / 25.4 * 72)
    page = writer.add_blank_page(width=width, height=height)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Times-Roman')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    lines = ['Problem Chosen', 'C', edition, 'MCM/ICM', 'Summary Sheet',
             'Team Control Number', team, 'Summary', 'Ordinary summary evidence.']
    data = b'BT /F1 11.95517 Tf 72 770 Td '
    data += b' 0 -22 Td '.join(('(' + line + ') Tj').encode() for line in lines)
    if small_math:
        data += b' 0 -25 Td (x) Tj /F1 8 Tf 6 5 Td (2) Tj'
    if small_prose:
        data += b' /F1 9 Tf 0 -25 Td (Axis label) Tj'
    if unmapped_math:
        cmap = DecodedStreamObject()
        cmap.set_data(b'/CIDInit /ProcSet findresource begin 12 dict begin begincmap '
                      b'/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def '
                      b'/CMapName /UnmappedMathFixture def /CMapType 2 def '
                      b'1 begincodespacerange <00> <FF> endcodespacerange '
                      b'1 beginbfchar <21> <FFFD> endbfchar endcmap '
                      b'CMapName currentdict /CMap defineresource pop end end')
        math_font = DictionaryObject(font)
        math_font[NameObject('/ToUnicode')] = writer._add_object(cmap)
        page[NameObject('/Resources')][NameObject('/Font')][NameObject('/F2')] = writer._add_object(math_font)
        data += b' /F2 11.95517 Tf 0 -25 Td (!) Tj'
    data += b' ET'
    stream = DecodedStreamObject(); stream.set_data(data)
    page[NameObject('/Contents')] = writer._add_object(stream)
    if running_header is not None:
        following = writer.add_blank_page(width=width, height=height)
        following[NameObject('/Resources')] = page[NameObject('/Resources')]
        header = DecodedStreamObject()
        header.set_data(('BT /F1 11.95517 Tf 72 770 Td (' + running_header
                         + ') Tj 0 -40 Td (Ordinary following-page text.) Tj ET').encode())
        following[NameObject('/Contents')] = writer._add_object(header)
    with path.open('wb') as output:
        writer.write(output)


@pytest.mark.parametrize('statement,valid', [
    ('Template team number 0000000 is an unassigned exercise identifier.', False),
    ('The current team control number is 0000000.', False),
    ('The earlier template team number 0000000 was replaced.', True),
    ('The simulation team number is 1234567; seed 0000000 remains scientific data.', True),
])
def test_actual_pdf_ai_narrative_identity_has_the_same_guard(tmp_path, statement, valid):
    from pypdf import PdfReader
    original = tmp_path/'summary.pdf'; actual_pdf(original)
    writer = PdfWriter()
    first = writer.add_page(PdfReader(original).pages[0])
    page = writer.add_blank_page(width=float(first.mediabox.width), height=float(first.mediabox.height))
    page[NameObject('/Resources')] = first[NameObject('/Resources')]
    lines = ['Team #1234567 Page 2 of 2', 'Report on Use of AI', statement]
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 11.95517 Tf 72 770 Td '+
                    b' 0 -40 Td '.join(('('+line+') Tj').encode() for line in lines)+b' ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    pdf=tmp_path/'current.pdf'; writer.write(pdf)
    result=inspect_mcm_delivery_format(pdf, {'team':'1234567','edition':'2020','problem':'C'}, ai_report_expected=True)
    assert result['passed'] is valid, result['errors']
    if not valid:
        assert any('identity statement' in error for error in result['errors'])


def candidate(tmp_path, *, version=4, mode='current', **pdf_options):
    tex = tmp_path / 'main.tex'; tex.write_text(source(version))
    pdf = tmp_path / 'main.pdf'; actual_pdf(pdf, **pdf_options)
    # Explicit synthetic log: only the log/receipt/freshness gate is exercised.
    pdf.with_suffix('.log').write_text('Synthetic test log; no compiler run claimed.\n'
                                      'Output written on main.xdv (1 page).\n')
    build = tmp_path / 'main.build.json'
    build.write_text(json.dumps({
        'runtime': json.loads((ROOT / 'templates/typesetting-runtime.json').read_text()),
        'layout': check(tex.read_text()), 'layout_mode': mode,
        'tex_sha256': hashlib.sha256(tex.read_bytes()).hexdigest(),
        'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
        # Synthetic binding fixture, not an actual compiler-opened receipt.
        'compiler_dependencies': {'schema_version': 1,
            'method': 'tectonic-0.17-opened-local-files',
            'files': {tex.name: hashlib.sha256(tex.read_bytes()).hexdigest()}},
    }))
    review = tmp_path / 'main.pdf.page-review.json'
    review.write_text(json.dumps({
        'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
        'actor': 'Test fixture; synthetic rendering-record binding only', 'pages': [1],
        'format_checks': {name: True for name in MCM_PAGE_REVIEW_CHECKS},
    }))
    return tex, pdf, build, review


@pytest.mark.parametrize('version', [1, 2, 3])
def test_current_requires_current_version_while_archive_retains_identity(tmp_path, version):
    text = source(version)
    assert check(text, layout_mode='archive')['profile'] == f'praxis-mcm-v{version}'
    with pytest.raises(ValueError, match='requires the current shared style'):
        check(text, layout_mode='current')
    tex = tmp_path / 'old.tex'; tex.write_text(text)
    with pytest.raises(ValueError, match='requires the current shared style'):
        compile_paper(tex, 'mcm', tmp_path / 'compiled', 'unused-compiler')
    with pytest.raises(ValueError, match='requires the current shared style'):
        freeze(tmp_path / 'unread.pdf', tmp_path / 'final.pdf', tex=tex, contest='mcm')
    assert not (tmp_path / 'final.pdf').exists()


def test_actual_letter_cannot_pass_with_current_source_and_binding_receipt(tmp_path):
    tex, pdf, build, _ = candidate(tmp_path, letter=True)
    with pytest.raises(ValueError, match='A4 page box'):
        freeze(pdf, tmp_path / 'final.pdf', tex=tex, contest='mcm', build_receipt=build)
    assert not (tmp_path / 'final.pdf').exists()


def test_archive_mode_explicitly_keeps_old_letter_snapshot(tmp_path):
    tex, pdf, build, _ = candidate(tmp_path, version=2, mode='archive', letter=True)
    result = freeze(pdf, tmp_path / 'archive.pdf', tex=tex, contest='mcm', build_receipt=build,
                    layout_mode='archive')
    assert result['layout_mode'] == 'archive' and result['layout']['profile'] == 'praxis-mcm-v2'
    assert 'current_mcm_format' not in result and 'font_size_review' not in result


@pytest.mark.parametrize('body', [
    r'\noindent Ordinary summary evidence.',
    r'Ordinary evidence.\clearpage\section{Method}\noindent Ordinary first paragraph.',
    r'\@afterindentfalse Ordinary summary evidence.',
])
def test_current_literal_first_paragraph_suppression_is_refused(body):
    with pytest.raises(ValueError, match='indentation'):
        check(source(body=body), layout_mode='current')


def test_letter_roles_and_list_caption_roles_are_still_legal():
    text = source(body=(r'Ordinary summary.\clearpage\section{Letter to the director}'
                        r'\noindent Dear Director,\par A recommendation.\par\noindent Sincerely,'
                        r'\begin{itemize}\item A list role.\end{itemize}'
                        r'\begin{figure}\centering\rule{1cm}{1pt}\caption{A caption.}\end{figure}'))
    assert check(text, layout_mode='current')['profile'] == 'praxis-mcm-v4'


def test_shared_summary_macro_accepts_a_nested_real_title():
    # The 2025 A generated title includes both a line break and a sized subtitle.
    # Its balanced macro argument is one real heading, not a macro replacement.
    text = source().replace(summary_heading(),
                            r'\PraxisSummaryHeading{What follows from the model\\[5pt]{\large Subtitle}}' + '\n')
    assert check(text, layout_mode='current')['profile'] == 'praxis-mcm-v4'
    override = text.replace(r'\begin{document}',
                            r'\renewcommand{\PraxisSummaryHeading}[1]{#1}\begin{document}')
    with pytest.raises(ValueError, match='overrides the shared summary heading'):
        check(override, layout_mode='current')


def test_current_freeze_automatically_measures_ordinary_figure_text(tmp_path):
    tex, pdf, build, _ = candidate(tmp_path, small_prose=True)
    with pytest.raises(ValueError, match='font-size review failed'):
        freeze(pdf, tmp_path / 'final.pdf', tex=tex, contest='mcm', build_receipt=build)
    with pytest.raises(ValueError, match='fixed 12'):
        freeze(pdf, tmp_path / 'lowered.pdf', tex=tex, contest='mcm', build_receipt=build,
               minimum_font_tex_pt=9)
    assert not (tmp_path / 'final.pdf').exists() and not (tmp_path / 'lowered.pdf').exists()


def test_current_math_review_is_required_bound_and_saved(tmp_path):
    tex, pdf, build, _ = candidate(tmp_path, small_math=True)
    with pytest.raises(ValueError, match='font-size review failed'):
        freeze(pdf, tmp_path / 'missing.pdf', tex=tex, contest='mcm', build_receipt=build)
    sizes = inspect_font_sizes(pdf, 12)
    review = tmp_path / 'font-review.json'
    review.write_text(json.dumps({
        'pdf_sha256': sizes['pdf_sha256'], 'minimum_font_tex_pt': 12,
        'approved_math_runs': [{'id': sizes['smaller_runs'][0]['id'], 'role': 'math_script',
                                'reason': 'Fixture exponent 2 in x squared; bound-review validation only.'}],
    }))
    result = freeze(pdf, tmp_path / 'final.pdf', tex=tex, contest='mcm', build_receipt=build,
                    font_review=review)
    assert result['font_size_review']['passed'] and result['current_mcm_format']['passed']
    stale = json.loads(review.read_text()); stale['pdf_sha256'] = '0' * 64
    review.write_text(json.dumps(stale))
    with pytest.raises(ValueError, match='does not match this PDF'):
        freeze(pdf, tmp_path / 'stale.pdf', tex=tex, contest='mcm', build_receipt=build,
               font_review=review)
    assert not (tmp_path / 'stale.pdf').exists()


def test_current_unmapped_mathematical_glyph_requires_its_own_bound_review(tmp_path):
    tex, pdf, build, _ = candidate(tmp_path, unmapped_math=True)
    sizes = inspect_font_sizes(pdf, 12)
    assert sizes['unmapped_runs'] and not sizes['passed']
    with pytest.raises(ValueError, match='font-size review failed'):
        freeze(pdf, tmp_path / 'missing-glyph-review.pdf', tex=tex, contest='mcm', build_receipt=build)
    review = tmp_path / 'glyph-review.json'
    review.write_text(json.dumps({
        'pdf_sha256': sizes['pdf_sha256'], 'minimum_font_tex_pt': 12,
        'approved_math_runs': [],
        'approved_unmapped_math_glyphs': [{'id': run['id'], 'role': 'math_notation',
                                          'reason': 'Synthetic factorial glyph with deliberately broken Unicode map; binding test only.'}
                                         for run in sizes['unmapped_runs']],
    }))
    result = freeze(pdf, tmp_path / 'reviewed-glyph.pdf', tex=tex, contest='mcm', build_receipt=build,
                    font_review=review)
    assert result['font_size_review']['unmapped_glyphs'] > 0
    assert not result['font_size_review']['unresolved_unmapped_runs']


def test_inspection_cannot_copy_earlier_pdf_bytes_after_source_changes(tmp_path, monkeypatch):
    import scripts.check_pdf as inspection
    _, pdf, _, _ = candidate(tmp_path)
    original = inspection.inspect_font_sizes
    def change_after_font_read(path, threshold, review=None):
        result = original(path, threshold, review)
        path.write_bytes(path.read_bytes() + b'\n% changed during inspection')
        return result
    monkeypatch.setattr(inspection, 'inspect_font_sizes', change_after_font_read)
    with pytest.raises(ValueError, match='changed during final delivery inspection'):
        freeze(pdf, tmp_path / 'stale-raw.pdf', minimum_font_tex_pt=12)
    assert not (tmp_path / 'stale-raw.pdf').exists()


@pytest.mark.parametrize('bad', ['missing', 'stale', 'pages', 'failed', 'absent_check'])
def test_current_page_rendering_review_is_mandatory_before_writing(tmp_path, bad):
    tex, pdf, build, review = candidate(tmp_path)
    data = json.loads(review.read_text())
    if bad == 'missing':
        review.unlink()
    else:
        if bad == 'stale': data['pdf_sha256'] = '0' * 64
        if bad == 'pages': data['pages'] = []
        if bad == 'failed': data['format_checks']['clipping_overlap'] = False
        if bad == 'absent_check': del data['format_checks']['paragraph_indentation']
        review.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='review'):
        freeze(pdf, tmp_path / 'final.pdf', tex=tex, contest='mcm', build_receipt=build)
    assert not (tmp_path / 'final.pdf').exists()


def test_current_valid_review_saves_actual_gate_results(tmp_path):
    tex, pdf, build, _ = candidate(tmp_path)
    result = freeze(pdf, tmp_path / 'final.pdf', tex=tex, contest='mcm', build_receipt=build)
    assert result['layout_mode'] == 'current'
    assert result['font_size_review']['minimum_font_tex_pt'] == 12
    assert result['page_format_review']['pages'] == [1]
    assert result['current_mcm_format']['identity'] == {'team': '1234567', 'problem': 'C', 'edition': '2020'}
    assert result['typesetting_diagnostics']['passed']
    assert result['typesetting_diagnostics']['legacy_build_without_diagnostics']
    assert result['typesetting_diagnostics']['log_sha256'] == hashlib.sha256(pdf.with_suffix('.log').read_bytes()).hexdigest()


@pytest.mark.parametrize('bad', ['missing', 'incomplete', 'hbox', 'vbox', 'float', 'binding'])
def test_current_freeze_requires_fresh_bound_overflow_free_log(tmp_path, bad):
    tex, pdf, build, _ = candidate(tmp_path)
    log = pdf.with_suffix('.log')
    if bad == 'missing':
        log.unlink()
    elif bad == 'incomplete':
        log.write_text('Synthetic incomplete log.\n')
    elif bad == 'binding':
        data = json.loads(build.read_text()); data['typesetting_diagnostics'] = {'log_sha256': '0' * 64}
        build.write_text(json.dumps(data))
    else:
        warning = {'hbox': r'Overfull \hbox (1.0pt too wide) in paragraph',
                   'vbox': r'Overfull \vbox (2.0pt too high) detected at line 1',
                   'float': 'LaTeX Warning: Float too large for page by 12.0pt on input line 1.'}[bad]
        log.write_text(warning + '\nOutput written on main.xdv (1 page).\n')
    with pytest.raises(ValueError, match='typesetting (?:log|overflow)|match the current typesetting log'):
        freeze(pdf, tmp_path / 'refused.pdf', tex=tex, contest='mcm', build_receipt=build)
    assert not (tmp_path / 'refused.pdf').exists()


def test_current_freeze_records_build_bound_log_without_mutating_receipt(tmp_path):
    tex, pdf, build, _ = candidate(tmp_path)
    data = json.loads(build.read_text())
    data['typesetting_diagnostics'] = inspect_typesetting_log(pdf.with_suffix('.log'), pdf=pdf)
    build.write_text(json.dumps(data)); original = build.read_bytes()
    result = freeze(pdf, tmp_path / 'final.pdf', tex=tex, contest='mcm', build_receipt=build)
    assert not result['typesetting_diagnostics']['legacy_build_without_diagnostics']
    assert build.read_bytes() == original


@pytest.mark.parametrize('option', [{'team': '7654321'}, {'edition': '2021'}])
def test_actual_summary_identity_is_bound_to_current_tex(tmp_path, option):
    tex, pdf, build, _ = candidate(tmp_path, **option)
    with pytest.raises(ValueError, match='differs from the current TeX identity'):
        freeze(pdf, tmp_path / 'final.pdf', tex=tex, contest='mcm', build_receipt=build)


@pytest.mark.parametrize('header, passed', [
    ('Team # 1234567 Page 2 of2', True),
    ('Team # 1234567 Page2of2', True),
    ('Team # 1234567 Page 2 of21', False),
    ('Team # 1234567 Page 3 of2', False),
    ('Team # 7654321 Page 2 of2', False),
])
def test_pdf_joined_running_header_tokens_keep_exact_numeric_identity(tmp_path, header, passed):
    pdf = tmp_path / 'running.pdf'; actual_pdf(pdf, running_header=header)
    result = inspect_mcm_delivery_format(pdf, {'team': '1234567', 'edition': '2020', 'problem': 'C'})
    assert result['passed'] is passed


def test_current_cli_default_refuses_old_source_but_explicit_archive_accepts(tmp_path):
    tex = tmp_path / 'old.tex'; tex.write_text(source(3))
    command = [sys.executable, '-m', 'scripts.paper_template', str(tex)]
    current = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    archive = subprocess.run(command + ['--layout-mode', 'archive'], cwd=ROOT, capture_output=True, text=True)
    assert current.returncode == 1 and 'current shared style' in current.stderr
    assert archive.returncode == 0 and 'praxis-mcm-v3' in archive.stdout


@pytest.mark.skipif(shutil.which('tectonic') is None, reason='Canonical Tectonic compiler is unavailable')
def test_actual_compiler_overflow_is_refused_but_archive_can_reproduce_it(tmp_path):
    body = r'Ordinary summary evidence.\par\makebox[2\linewidth][l]{Unbreakable wide evidence.}'
    tex = tmp_path / 'main.tex'; tex.write_text(source(body=body))
    output = tmp_path / 'current'
    with pytest.raises(ValueError, match='typesetting overflow'):
        compile_paper(tex, 'mcm', output)
    assert (output / 'main.pdf').is_file()
    assert r'Overfull \hbox' in (output / 'main.log').read_text()
    assert not (output / 'main.build.json').exists()
    old = tmp_path / 'historical.tex'; old.write_text(source(version=2, body=body))
    archive = compile_paper(old, 'mcm', tmp_path / 'archive', layout_mode='archive')
    assert archive['layout_mode'] == 'archive'
    assert archive['layout']['profile'] == 'praxis-mcm-v2'
    assert 'typesetting_diagnostics' not in archive


@pytest.mark.skipif(shutil.which('tectonic') is None, reason='Canonical Tectonic compiler is unavailable')
def test_expanded_geometry_override_is_caught_in_actual_pdf(tmp_path):
    tex = tmp_path / 'main.tex'
    # A literal-command-only static check cannot expand csname; the canonical
    # build must reject the resulting real Letter page before a success receipt.
    tex.write_text(source().replace(r'\begin{document}',
                                   r'\csname geometry\endcsname{paperwidth=8.5in,paperheight=11in}\begin{document}'))
    assert check(tex.read_text(), layout_mode='current')['profile'] == 'praxis-mcm-v4'
    with pytest.raises(ValueError, match='A4 page box'):
        compile_paper(tex, 'mcm', tmp_path / 'compiled')
    assert (tmp_path / 'compiled/main.pdf').is_file()
    assert not (tmp_path / 'compiled/main.build.json').exists()



def test_completed_log_can_precede_pdf_serialization(tmp_path):
    tex, pdf, build, _ = candidate(tmp_path)
    log = pdf.with_suffix('.log')
    old = pdf.stat().st_mtime_ns - 1000000000
    os.utime(log, ns=(old, old))
    assert freeze(pdf, tmp_path / 'final.pdf', tex=tex, contest='mcm',
                  build_receipt=build)['typesetting_diagnostics']['passed']


def test_crlf_style_inspection_preserves_actual_source_binding(tmp_path):
    tex = tmp_path / 'windows-lines.tex'
    raw = source().replace('\n', '\r\n').encode('utf-8')
    tex.write_bytes(raw)
    assert check(raw.decode('utf-8'), 'mcm', layout_mode='current')['profile'] == 'praxis-mcm-v4'
    altered = raw.decode('utf-8').replace('a4paper', 'letterpaper', 1)
    with pytest.raises(ValueError, match='differs from the shared source'):
        check(altered, 'mcm', layout_mode='current')
    if shutil.which('tectonic') is None:
        pytest.skip('Canonical Tectonic compiler is unavailable')
    record = compile_paper(tex, 'mcm', tmp_path / 'compiled')
    assert tex.read_bytes() == raw
    assert record['tex_sha256'] == hashlib.sha256(raw).hexdigest()
    assert record['current_mcm_format']['passed']
