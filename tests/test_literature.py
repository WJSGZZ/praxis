import pytest

from scripts.literature import open_access_for, search_works


def test_search_works_maps_openalex_fields_and_validates_input():
    sample = {'results': [{'title': 'A paper', 'publication_year': 2020, 'doi': 'https://doi.org/10.1/x', 'cited_by_count': 7,
                           'authorships': [{'author': {'display_name': 'Ada'}}], 'open_access': {'is_oa': True, 'oa_url': 'https://free/x.pdf'},
                           'primary_location': {'source': {'display_name': 'Journal'}}},
                          {'title': 'Closed', 'open_access': {'is_oa': False, 'oa_url': None}, 'authorships': []}]}
    urls = []
    result = search_works('hot bath cooling', 2, get=lambda url, mailto: urls.append(url) or sample)
    assert 'search=hot+bath+cooling' in urls[0]
    first, second = result['results']
    assert first['free_full_text'] == 'https://free/x.pdf' and first['venue'] == 'Journal' and first['authors'] == ['Ada']
    assert second['free_full_text'] is None and second['is_open_access'] is False
    with pytest.raises(ValueError):
        search_works('  ', 3)


def test_open_access_lookup_requires_a_real_email_and_reports_closed_papers():
    with pytest.raises(ValueError):
        open_access_for('10.1/x', 'unknown@example.org')
    closed = open_access_for('https://doi.org/10.1/x', 'me@school.edu', get=lambda url, mailto: {'is_oa': False, 'title': 'T'})
    assert closed['doi'] == '10.1/x' and closed['is_open_access'] is False and 'library' in closed['note']
    free = open_access_for('10.1/y', 'me@school.edu', get=lambda url, mailto: {'is_oa': True, 'best_oa_location': {'url_for_pdf': 'https://p.pdf', 'version': 'publishedVersion'}})
    assert free['pdf_url'] == 'https://p.pdf' and free['note'] is None
