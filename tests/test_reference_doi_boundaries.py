"""Legal legacy DOI characters and citation wrappers must survive extraction."""
import pytest

from scripts.check_references import check


@pytest.mark.parametrize('doi,line', [
    ('10.1002/(SICI)1099-0844(199912)17:6<290::AID-CBF849>3.0.CO;2-P',
     'Sample Paper, 1999. doi:10.1002/(SICI)1099-0844(199912)17:6<290::AID-CBF849>3.0.CO;2-P.'),
    ('10.1234/example(2020)', 'Sample Paper, 1999 (doi:10.1234/example(2020)).'),
    ('10.1234/example(2020)', 'Sample Paper, 1999 <https://doi.org/10.1234/example(2020)>'),
])
def test_doi_extraction_preserves_balanced_identifier_delimiters(doi,line):
    requested = []

    def metadata(value, mailto):
        requested.append(value)
        return {'title':['Sample Paper'], 'issued':{'date-parts':[[1999]]}}

    result = check([line], get=metadata)
    assert requested == [doi]
    assert result[0]['doi'] == doi
    assert result[0]['status'] == 'verified'
