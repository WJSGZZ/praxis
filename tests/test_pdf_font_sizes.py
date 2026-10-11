"""Independent PDF operators expose shrinking hidden by a dominant-body statistic."""
import hashlib
import json

import pytest
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject

from scripts.check_pdf import inspect_font_sizes, inspect_pdf
from scripts.pdf_text import _unicode_chars, effective_font_runs
from scripts.freeze_pdf import freeze


def font_pdf(path, body_size=11.95517, *, nested=False, small_script=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=595.28, height=841.89)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    resources = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    page[NameObject('/Resources')] = resources
    data = f'BT /F1 {body_size} Tf 72 760 Td (Ordinary body paragraph dominates the page.) Tj ET'.encode()
    if nested:
        # .5 page scale * 2 Form scale * .8 rotated text scale = .8;
        # vertical em is exactly 12*.8=9.6 PDF bp. Diagonal multiplication
        # would miss the rotated label (a=d=0).
        form = DecodedStreamObject()
        form.set_data(b'BT /F1 12 Tf 0 .8 -.8 0 0 0 Tm (Axis label) Tj ET')
        form.update({NameObject('/Type'): NameObject('/XObject'), NameObject('/Subtype'): NameObject('/Form'),
                     NameObject('/BBox'): ArrayObject([FloatObject(v) for v in [-100, -100, 100, 100]]),
                     NameObject('/Matrix'): ArrayObject([FloatObject(v) for v in [2, 0, 0, 2, 0, 0]]),
                     NameObject('/Resources'): resources})
        # Keep Form resources independent of the page's XObject dictionary.
        page_resources = DictionaryObject(resources)
        page_resources[NameObject('/XObject')] = DictionaryObject({NameObject('/Plot'): writer._add_object(form)})
        page[NameObject('/Resources')] = page_resources
        data += b' q .5 0 0 .5 250 400 cm /Plot Do Q'
    if small_script:
        data += b' BT /F1 11.95517 Tf 72 650 Td (x) Tj /F1 8 Tf 6 5 Td (2) Tj ET'
    stream = DecodedStreamObject()
    stream.set_data(data)
    page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as output:
        writer.write(output)


def test_final_rotated_nested_figure_size_is_measured(tmp_path):
    pdf = tmp_path/'nested.pdf'
    font_pdf(pdf, nested=True)
    runs = effective_font_runs(pdf)[0]['runs']
    label = next(r for r in runs if 'Axis' in r['text'])
    assert label['size_pdf_bp'] == pytest.approx(9.6, abs=1e-5)
    report = inspect_pdf(pdf, minimum_font_tex_pt=12)
    assert report['errors']
    assert any('Axis' in r['text'] for r in report['font_size_review']['unresolved_runs'])
    assert report['visual_review_required']


def test_twelve_tex_points_pass_but_eleven_point_six_does_not(tmp_path):
    pdf = tmp_path/'body.pdf'
    font_pdf(pdf)
    assert inspect_font_sizes(pdf, 12)['passed']
    font_pdf(pdf, body_size=11.6)
    report = inspect_font_sizes(pdf, 12)
    assert not report['passed']
    assert report['smaller_runs'][0]['size_tex_pt'] == pytest.approx(11.6435, abs=1e-5)


def test_scripts_need_exact_pdf_bound_review_and_cannot_exempt_prose(tmp_path):
    pdf = tmp_path/'script.pdf'
    font_pdf(pdf, small_script=True)
    before = pdf.read_bytes()
    report = inspect_font_sizes(pdf, 12)
    assert [r['text'] for r in report['smaller_runs']] == ['2']
    run = report['smaller_runs'][0]
    review = tmp_path/'review.json'
    entry = {'id': run['id'], 'role': 'math_script', 'reason': 'Superscript exponent in x squared, checked in the rendered formula.'}
    record = {'pdf_sha256': hashlib.sha256(before).hexdigest(), 'minimum_font_tex_pt': 12,
              'approved_math_runs': [entry]}
    review.write_text(json.dumps(record))
    assert inspect_font_sizes(pdf, 12, review)['passed']
    assert pdf.read_bytes() == before
    entry['role'] = 'ordinary_text'
    review.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='mathematical run'):
        inspect_font_sizes(pdf, 12, review)
    entry['role'] = 'math_script'
    record['pdf_sha256'] = '0'*64
    review.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='does not match'):
        inspect_font_sizes(pdf, 12, review)


@pytest.mark.parametrize('value', [True, 0, -1, float('nan'), float('inf')])
def test_invalid_minimum_is_rejected_before_reading(value, tmp_path):
    with pytest.raises(ValueError, match='positive finite'):
        inspect_font_sizes(tmp_path/'missing.pdf', value)


def test_blank_page_cannot_certify_font_size(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=595.28, height=841.89)
    pdf = tmp_path/'blank.pdf'
    with pdf.open('wb') as output:
        writer.write(output)
    assert not inspect_font_sizes(pdf, 12)['passed']


def test_font_gate_rejects_snapshot_before_writing_and_preserves_source(tmp_path):
    pdf = tmp_path/'source.pdf'
    font_pdf(pdf, nested=True)
    raw = pdf.read_bytes()
    destination = tmp_path/'final.pdf'
    with pytest.raises(ValueError, match='font-size review failed'):
        freeze(pdf, destination, minimum_font_tex_pt=12)
    assert not destination.exists()
    assert pdf.read_bytes() == raw
    font_pdf(pdf)
    result = freeze(pdf, destination, minimum_font_tex_pt=12)
    assert result['font_size_review']['passed']
    assert destination.read_bytes() == pdf.read_bytes()


def test_pdfium_surrogates_keep_glyph_indices_and_serialize_safely():
    chars, malformed = _unicode_chars([ord('T'), 0xd835, 0xdc49, ord('2'), 0xd835])
    assert chars == ['T', '\U0001d449', '', '2', '\ufffd']
    assert malformed == 1
    json.dumps(chars, ensure_ascii=False).encode('utf-8')
