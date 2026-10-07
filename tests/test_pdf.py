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
