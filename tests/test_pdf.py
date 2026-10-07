from pathlib import Path
import pytest
from pypdf import PdfWriter
from scripts.check_pdf import inspect_pdf
from scripts.freeze_pdf import freeze
from scripts.pipeline import init_case


def make_pdf(path):
    w=PdfWriter()
    w.add_blank_page(width=300,height=400)
    w.add_metadata({'/Author':'Synthetic author'})
    with path.open('wb') as stream:
        w.write(stream)


def test_pdf_limits_metadata_and_snapshot(tmp_path):
    source=tmp_path/'input.pdf'
    make_pdf(source)
    before=source.read_bytes()
    report=inspect_pdf(source,max_pages=1,max_bytes=1,forbidden=['Synthetic author'])
    assert report['total_pages']==1
    assert len(report['errors'])==2
    assert report['visual_review_required']
    assert report['warnings']
    target=tmp_path/'frozen.pdf'
    receipt=freeze(source,target)
    assert source.read_bytes()==before==target.read_bytes()
    assert receipt['sha256']==report['sha256']
    with pytest.raises(FileExistsError):
        freeze(source,target)


def test_pdf_intake_requires_visual_review(tmp_path):
    source=tmp_path/'problem.pdf'
    make_pdf(source)
    case=Path(init_case(tmp_path/'cases','pdf-intake',source,[])['case'])
    import json
    record=json.loads((case/'case.json').read_text())
    assert record['problem_visual_review_required']
    assert not record['problem_text_extracted']


def make_font_pdf(path):
    """Synthetic text uses two faces; a declared third face is deliberately unused."""
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer=PdfWriter();page=writer.add_blank_page(width=300,height=400)
    fonts=DictionaryObject()
    for key,face in [('F1','ABCDEF+Example-Regular'),('F2','ABCDEF+Example-Black-0'),('F3','Unused-Black')]:
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),
                              NameObject('/Subtype'):NameObject('/Type1'),
                              NameObject('/BaseFont'):NameObject('/'+face),
                              NameObject('/Encoding'):NameObject('/WinAnsiEncoding')})
        fonts[NameObject('/'+key)]=writer._add_object(font)
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):fonts})
    content=DecodedStreamObject()
    content.set_data(b'BT /F1 12 Tf 20 300 Td (regular) Tj /F2 12 Tf 0 -20 Td (black) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(content)
    with path.open('wb') as f:writer.write(f)


def test_actual_text_faces_and_optional_embedding_requirement(tmp_path):
    path=tmp_path/'faces.pdf';make_font_pdf(path);before=path.read_bytes()
    report=inspect_pdf(path,forbidden_fonts=['Example-Black*'])
    assert {f['face'] for f in report['fonts']}=={'Example-Regular','Example-Black-0'}
    assert len(report['errors'])==1
    assert 'Example-Black' in report['errors'][0]
    # A face declared in resources but unused in text is not reported as a body font.
    assert not inspect_pdf(path,forbidden_fonts=['Unused-Black'])['errors']
    assert len(inspect_pdf(path,require_embedded_fonts=True)['errors'])==2
    assert path.read_bytes()==before


def test_descendant_font_embedding_structure():
    from scripts.check_pdf import font_record
    from pypdf.generic import DictionaryObject, NameObject, ArrayObject, DecodedStreamObject
    descriptor=DictionaryObject({NameObject('/FontFile2'):DecodedStreamObject()})
    descendant=DictionaryObject({NameObject('/FontDescriptor'):descriptor})
    font=DictionaryObject({NameObject('/BaseFont'):NameObject('/ABCDEF+Example-Regular'),
                           NameObject('/Subtype'):NameObject('/Type0'),
                           NameObject('/DescendantFonts'):ArrayObject([descendant])})
    assert font_record(font)['embedding_present']
    del descriptor['/FontFile2']
    assert not font_record(font)['embedding_present']


def test_report_count_and_failed_evidence_cannot_be_upgraded(tmp_path):
    import json
    path=tmp_path/'input.pdf';make_pdf(path)
    checks=tmp_path/'checks.json'
    entries=[{'name':f'check {i}','passed':True,'evidence':f'independent synthetic value {i}'} for i in range(12)]
    checks.write_text(json.dumps(entries))
    report=inspect_pdf(path,checks_path=checks,claimed_check_count=13)
    assert report['check_summary']['total']==12 and report['check_summary']['passed']==12
    assert len(report['errors'])==1
    assert not inspect_pdf(path,checks_path=checks,claimed_check_count=12)['errors']
    entries[-1]['passed']=False;checks.write_text(json.dumps(entries))
    report=inspect_pdf(path,checks_path=checks,claimed_check_count=12)
    assert report['check_summary']['failed']==1
    assert report['errors']
    assert report['check_summary']['independence_not_assessed']


@pytest.mark.parametrize('entries', [[],[{'name':'x','passed':1,'evidence':'value'}],
    [{'name':'x','passed':True,'evidence':'value'}]*2])
def test_malformed_or_duplicate_evidence_is_rejected(tmp_path,entries):
    import json
    from scripts.check_pdf import summarize_checks
    path=tmp_path/'checks.json';path.write_text(json.dumps(entries))
    with pytest.raises(ValueError):summarize_checks(path)


def test_margin_report_flags_overflow_and_uneven_pages(tmp_path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from scripts.check_pdf import margin_report
    path = tmp_path / 'layout.pdf'
    with PdfPages(path) as pdf:
        for left_edge, right_edge in ((0.2, 0.8), (0.2, 0.97), (0.5, 0.5)):
            fig = plt.figure(figsize=(6, 8))
            fig.add_artist(plt.Line2D([left_edge, right_edge], [0.5, 0.5], color='black', lw=3, transform=fig.transFigure))
            pdf.savefig(fig)
            plt.close(fig)
    report = margin_report(path)
    by_page = {p['page']: p for p in report['pages']}
    assert 'flags' not in by_page[1]
    assert 'margins differ' in by_page[2]['flags'] and 'ink near the page edge' in by_page[2]['flags']
    assert abs(by_page[1]['left_pt'] - by_page[1]['right_pt']) < 4
    assert report['flagged_pages'] == [2]
