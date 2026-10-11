"""The MCM 12-point floor follows the extractor's 0.1 PDF-bp precision."""
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from scripts.contest_rules import evaluate, extract


def records(size):
    text = 'Team # 1234567 Page 1 of 1\nSummary\nBody text.'
    return [dict(text=text, lines=text.splitlines(), body_size=size)]


def test_mcm_body_11_6_does_not_meet_the_12_point_floor():
    result = evaluate(records(11.6), 'mcm')
    assert not result['passed']
    assert any('minimum is 12' in e for e in result['errors'])


def test_actual_12_tex_point_pdf_rounds_to_12_pdf_bp_and_passes(tmp_path):
    pdf = tmp_path/'twelve-tex-point.pdf'
    writer = PdfWriter()
    page = writer.add_blank_page(width=595.27559, height=841.88976)
    font = writer._add_object(DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica'),
    }))
    page[NameObject('/Resources')] = DictionaryObject({
        NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})
    })
    stream = DecodedStreamObject()
    tex_pt_in_pdf_bp = 12 * 72 / 72.27
    stream.set_data(('\n'.join(
        f'BT /F1 {tex_pt_in_pdf_bp:.8f} Tf 1 0 0 1 80 {760-i*20} Tm ({text}) Tj ET'
        for i, text in enumerate(records(12)[0]['lines'])
    )).encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    with pdf.open('wb') as handle:
        writer.write(handle)
    actual = extract(pdf)
    assert actual[0]['body_size'] == 12.0
    assert evaluate(actual, 'mcm')['passed']
