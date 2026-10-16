from pathlib import Path

import pytest

from scripts.check_pdf import inspect_pdf
from scripts.contest_rules import extract
from scripts.pdf_text import extract_pages
from scripts.pipeline import init_case

FIXTURE = Path(__file__).parent / 'fixtures/fandol-cjk.pdf'


def test_standard_cjk_mapping_is_readable_and_used_for_anonymity():
    records = extract_pages(FIXTURE)
    assert records[0]['text_backend'] == 'pdfium-standard-cjk-mapping'
    assert '数学建模与独立验证' in records[0]['text']
    assert records[0]['body_size'] == 12.0
    report = inspect_pdf(FIXTURE, forbidden=['数学建模与独立验证'], require_embedded_fonts=True)
    assert report['errors'] == ['Configured forbidden term found: 数学建模与独立验证']
    assert all(f['embedding_present'] for f in report['fonts'])
    assert '投资的收益和风险' in extract(FIXTURE)[0]['text']


def test_problem_intake_preserves_chinese_from_standard_collection(tmp_path):
    case = Path(init_case(tmp_path, 'cjk', FIXTURE)['case'])
    assert '数学建模与独立验证' in (case / 'planning/problem-extracted.txt').read_text()


def test_chinese_identifying_metadata_is_not_hidden_by_json_escaping(tmp_path):
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.add_metadata({'/Author': '测试大学'})
    path = tmp_path / 'metadata.pdf'
    with path.open('wb') as stream:
        writer.write(stream)
    report = inspect_pdf(path, forbidden=['测试大学'])
    assert report['errors'] == ['Configured forbidden term found: 测试大学']


def test_rotated_body_size_uses_effective_vertical_em(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    from scripts.contest_rules import evaluate
    writer = PdfWriter()
    page = writer.add_blank_page(width=500, height=700)
    font = writer._add_object(DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica'),
    }))
    page[NameObject('/Resources')] = DictionaryObject({
        NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 0 .5 -.5 0 150 150 Tm '
                    b'(Rotated body with six-point effective letters) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    path = tmp_path/'rotated.pdf'
    writer.write(path)
    records = extract(path)
    assert records[0]['body_size'] == 6.0
    assert not evaluate(records, 'mcm')['passed']
    explicit = extract_pages(path, text_backend='pdfium')[0]
    assert explicit['body_size'] == records[0]['body_size']
    assert explicit['text_backend'] == 'pdfium'
    assert 'six-point effective letters' in explicit['text']


def test_scaled_standard_cjk_size_does_not_keep_nominal_twelve(tmp_path):
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    page = writer.add_page(PdfReader(FIXTURE).pages[0])
    page.scale_by(.5)
    path = tmp_path/'scaled-cjk.pdf'
    writer.write(path)
    record = extract_pages(path)[0]
    assert '数学建模与独立验证' in record['text']
    assert record['body_size'] == 6.0
    explicit = extract_pages(path, text_backend='pdfium')[0]
    assert explicit['body_size'] == record['body_size']
    assert explicit['text'] == record['text']


def test_explicit_pdfium_preserves_cjk_text_and_auto_result_contract():
    default = extract_pages(FIXTURE)
    assert extract_pages(FIXTURE, text_backend='auto') == default
    explicit = extract_pages(FIXTURE, text_backend='pdfium')
    assert len(explicit) == len(default)
    assert all(page['text_backend'] == 'pdfium' for page in explicit)
    assert [(p['text'], p['body_size']) for p in explicit] == [(p['text'], p['body_size']) for p in default]


def test_explicit_pdfium_bypasses_pypdf_text_and_preserves_numbers(tmp_path, monkeypatch):
    from pypdf import PageObject, PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=500, height=700)
    font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    stream = DecodedStreamObject()
    text = 'Revenue = 1,234.50; ratio = 25%; n = 101.'
    stream.set_data(f'BT /F1 12 Tf 20 650 Td ({text}) Tj ET'.encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    path = tmp_path / 'numbers.pdf'
    writer.write(path)
    before = extract_pages(path)
    assert before[0]['text_backend'] == 'pypdf'
    assert before == extract_pages(path, text_backend='auto')
    # A controlled backend fault proves that the explicit route does not use
    # pypdf text. This is synthetic, not a claim to reproduce a real font defect.
    monkeypatch.setattr(PageObject, 'extract_text', lambda *args, **kwargs: 'NQ synthetic corrupted numbers')
    assert extract_pages(path)[0]['text'] == 'NQ synthetic corrupted numbers'
    explicit = extract_pages(path, text_backend='pdfium')[0]
    assert text in explicit['text']
    assert explicit['body_size'] == before[0]['body_size'] == 12
    assert explicit['text_backend'] == 'pdfium'


@pytest.mark.parametrize('backend', ['pypdf', '', None, {}])
def test_bad_text_backend_is_rejected_before_opening_pdf(tmp_path, monkeypatch, backend):
    monkeypatch.setattr('scripts.pdf_text.PdfReader', lambda *a, **kw: pytest.fail('must reject backend before opening PDF'))
    with pytest.raises(ValueError, match='text_backend must be auto or pdfium'):
        extract_pages(tmp_path / 'must-not-open.pdf', text_backend=backend)
