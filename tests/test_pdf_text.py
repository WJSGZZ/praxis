from pathlib import Path

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
