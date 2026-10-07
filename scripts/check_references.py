"""Check that each DOI in a reference list exists in Crossref and matches the cited title and year.

Reads one reference per line. Lines without a DOI (books, standards, web pages) are reported as
'no_doi' and must be checked by hand; a match here shows the record exists, not that the source
supports the claim it is cited for."""
import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOI = re.compile(r'10\.\d{4,9}/[^\s"<>]+')
WORD = re.compile(r'[a-z0-9]+')


def fetch(doi, mailto):
    request = urllib.request.Request('https://api.crossref.org/works/' + urllib.parse.quote(doi),
                                     headers={'User-Agent': f'praxis-check-references (mailto:{mailto})'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)['message']
    except urllib.error.URLError as error:
        # Some Python builds ship without a CA bundle; retry with the system one before giving up.
        bundle = next((Path(c) for c in ('/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.crt') if Path(c).exists()), None)
        if not isinstance(error.reason, ssl.SSLCertVerificationError) or bundle is None:
            raise
        context = ssl.create_default_context(cafile=str(bundle))
        with urllib.request.urlopen(request, timeout=20, context=context) as response:
            return json.load(response)['message']


def words(text):
    return [w for w in WORD.findall(text.lower()) if len(w) > 2]


def compare(line, record):
    title = ' '.join(record.get('title') or [''])
    wanted = set(words(title))
    overlap = len(wanted & set(words(line))) / len(wanted) if wanted else 0.0
    issued = (record.get('issued') or {}).get('date-parts', [[None]])[0][0]
    year_ok = issued is not None and str(issued) in line
    return dict(crossref_title=title, crossref_year=issued, title_overlap=round(overlap, 2),
                year_in_citation=year_ok,
                status='verified' if overlap >= 0.6 and year_ok else 'mismatch')


def check(lines, mailto='unknown@example.org', get=fetch):
    results = []
    for number, line in enumerate((l.strip() for l in lines), 1):
        if not line:
            continue
        found = DOI.search(line)
        if not found:
            results.append(dict(line=number, status='no_doi', citation=line))
            continue
        doi = found.group(0).rstrip('.,;)')
        try:
            record = get(doi, mailto)
        except urllib.error.HTTPError as error:
            status = 'not_found' if error.code == 404 else 'network_error'
            results.append(dict(line=number, doi=doi, status=status, citation=line))
            continue
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            results.append(dict(line=number, doi=doi, status='network_error', error=str(error), citation=line))
            continue
        results.append(dict(line=number, doi=doi, citation=line, **compare(line, record)))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('references', type=Path, help='Text file, one reference per line')
    parser.add_argument('--mailto', default='unknown@example.org', help='Contact address Crossref asks clients to send')
    args = parser.parse_args()
    results = check(args.references.read_text().splitlines(), args.mailto)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    sys.exit(0 if all(r['status'] in {'verified', 'no_doi'} for r in results) else 1)


if __name__ == '__main__':
    main()
