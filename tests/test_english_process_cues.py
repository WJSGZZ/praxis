"""Reader review cues, not a ban on scientific methods or English keywords."""
import pytest

from scripts.check_prose import inspect


def scan(body, title='Discussion'):
    source = r'\section{' + title + '}' + body
    page = title + '\n' + body
    return inspect(source, [page], profile='contest'), page


@pytest.mark.parametrize('body', [
    'No observed holdout data or published numerical plant benchmark was supplied, '
    'and outside retrieval is excluded.',
    'For this exercise, external retrieval was forbidden.',
])
def test_author_access_restriction_prompts_review_without_rejecting(body):
    result, _ = scan(body)
    cues = [w for w in result['warnings'] if w['code'] == 'prose_process_leak']
    assert len(cues) == 1
    assert result['diagnostic_only'] is True
    assert len(result['metrics']['process_leak_candidates']) == 1


def test_pdf_line_hyphenation_keeps_real_page_location():
    body = ('No observed holdout data or published numerical plant benchmark was '
            'supplied, and out-\nside retrieval is excluded.')
    result, page = scan(body, 'Verification, limitations and the resulting recommendation')
    candidates = result['metrics']['process_leak_candidates']
    assert len(candidates) == 1
    item = candidates[0]
    assert item['text'] == 'out-\nside retrieval is excluded'
    assert page[item['offset']:item['offset'] + len(item['text'])] == item['text']
    assert item['page'] == 1
    assert 'No observed holdout data' not in item['text']


@pytest.mark.parametrize('body', [
    'We compare candidate models using the same observations.',
    'Freezing of the physical system changes its latent heat.',
    'The validator checks conservation and units with an independent algebraic method.',
    'The saved validator contains ten checks of the conservation law.',
    'The validator rejects malformed input and detects schema violations.',
    'External retrieval is excluded from the controlled retrieval experiment.',
    'In this controlled retrieval study, outside retrieval is excluded.',
    'No data were suppliedoutside retrieval is excluded.',
    'The code is published at https://example.org/validator/frozen/candidate.py.',
])
def test_scientific_methods_and_isolated_words_are_not_process_cues(body):
    result, _ = scan(body)
    assert not result['metrics']['process_leak_candidates']


@pytest.mark.parametrize('title', ['References', 'Report on Use of AI', 'Appendix', 'Reproducibility'])
def test_existing_disclosure_and_reference_exemptions_are_preserved(title):
    result, _ = scan('For this exercise, external retrieval was forbidden.', title)
    assert not result['metrics']['process_leak_candidates']


def test_uncertain_heading_mapping_does_not_invent_pdf_process_locations():
    source = r'\section{Discussion}For this exercise, external retrieval was forbidden.'
    page = 'Discussion\nFor this exercise, external retrieval was forbidden.'
    result = inspect(source, [page, page], profile='contest')
    assert result['metrics']['mapping_status'] == 'uncertain'
    assert not result['metrics']['process_leak_candidates']
