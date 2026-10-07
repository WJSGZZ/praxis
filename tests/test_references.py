import urllib.error

from scripts.check_references import check

RECORD = {'title': ['Vascular, inflammatory and perceptual responses to hot water immersion'],
          'issued': {'date-parts': [[2025, 7, 29]]}}


def fake(doi, mailto):
    if doi == '10.1113/EP092761':
        return RECORD
    if doi == '10.0000/missing':
        raise urllib.error.HTTPError('u', 404, 'nf', {}, None)
    raise urllib.error.URLError('offline')


def test_verified_mismatch_missing_offline_and_no_doi():
    lines = ['Menzies C. et al. Vascular, inflammatory and perceptual responses to hot water immersion. Exp Physiol, 2025. doi:10.1113/EP092761.',
             'Wrong C. A paper about bridges, 2019. doi:10.1113/EP092761',
             'Ghost A. Nothing. 2020. 10.0000/missing',
             'Offline B. Anything. 2021. 10.1111/x',
             'Bergman T. Fundamentals of Heat and Mass Transfer, 7th ed. Wiley, 2011.']
    status = [r['status'] for r in check(lines, get=fake)]
    assert status == ['verified', 'mismatch', 'not_found', 'network_error', 'no_doi']
