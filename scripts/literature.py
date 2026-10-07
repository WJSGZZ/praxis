"""Free literature lookup: OpenAlex search and Unpaywall open-access locations. No keys, no paid sources.

These find legal open copies and metadata. Paywalled papers stay paywalled: a user with a school
library should fetch them there. Seeing an abstract or a title is not evidence that a paper supports a claim."""
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def get_json(url, mailto='unknown@example.org', timeout=20):
    request = urllib.request.Request(url, headers={'User-Agent': f'praxis-literature (mailto:{mailto})'})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.URLError as error:
        bundle = next((Path(c) for c in ('/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.crt') if Path(c).exists()), None)
        if not isinstance(error.reason, ssl.SSLCertVerificationError) or bundle is None:
            raise
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context(cafile=str(bundle))) as response:
            return json.load(response)


def search_works(query, limit=5, mailto='unknown@example.org', get=get_json):
    """Top OpenAlex works for a query with year, DOI, citations and a free full-text link when one exists."""
    if not query.strip() or not 1 <= limit <= 25:
        raise ValueError('Need a query and a limit between 1 and 25')
    url = 'https://api.openalex.org/works?' + urllib.parse.urlencode(
        {'search': query, 'per-page': limit, 'mailto': mailto,
         'select': 'id,doi,title,publication_year,cited_by_count,authorships,open_access,primary_location'})
    out = []
    for work in get(url, mailto).get('results', []):
        out.append(dict(title=work.get('title'), year=work.get('publication_year'), doi=work.get('doi'),
                        cited_by=work.get('cited_by_count'),
                        authors=[a['author']['display_name'] for a in work.get('authorships', [])[:4]],
                        venue=((work.get('primary_location') or {}).get('source') or {}).get('display_name'),
                        free_full_text=(work.get('open_access') or {}).get('oa_url'),
                        is_open_access=bool((work.get('open_access') or {}).get('is_oa'))))
    return dict(query=query, results=out)


def open_access_for(doi, mailto, get=get_json):
    """Unpaywall's best legal open copy of a DOI, if any. Unpaywall asks callers to send a real email address."""
    if '@' not in mailto or mailto.endswith('example.org'):
        raise ValueError('Unpaywall needs a real contact email in `mailto`')
    doi = doi.strip().removeprefix('https://doi.org/')
    record = get(f'https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={urllib.parse.quote(mailto)}', mailto)
    best = record.get('best_oa_location') or {}
    return dict(doi=doi, title=record.get('title'), is_open_access=bool(record.get('is_oa')),
                pdf_url=best.get('url_for_pdf'), landing_page=best.get('url_for_landing_page'),
                version=best.get('version'), license=best.get('license'),
                note=None if record.get('is_oa') else 'No open copy found; ask your library for the full text.')
