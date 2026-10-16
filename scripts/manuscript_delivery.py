"""Combine current-delivery manuscript diagnostics; every new rule is a warning."""
import hashlib
from pathlib import Path

from scripts import check_claims, check_prose, check_summary, contest_coverage, reader_packet
from scripts.manuscript import load_json


def inspect(tex_text, pdf_pages, *, pdf_sha256, results=None, requirements=None,
            model_contract=None, figure_plan=None, reader_review=None,
            problem_year=None, allow_anachronism=False):
    paths = dict(results=results, requirements=requirements, model_contract=model_contract,
                 figure_plan=figure_plan, reader_review=reader_review)
    values, bindings = {}, {}
    for name, path in paths.items():
        if path is None:
            values[name] = None
        else:
            path = Path(path)
            raw = path.read_bytes()
            values[name] = load_json(path)
            bindings[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    reports = {'summary': check_summary.inspect(tex_text, values['results']),
               'prose': check_prose.inspect(tex_text, pdf_pages, problem_year=problem_year,
                                            allow_anachronism=allow_anachronism),
               'claims': check_claims.inspect(tex_text, values['results'])}
    warnings = []
    for name, report in reports.items():
        warnings.extend(dict(warning, check=name) for warning in report['warnings'])
    needed = ('requirements', 'model_contract', 'figure_plan')
    missing = [name for name in needed if values[name] is None]
    if missing:
        warnings.append(dict(code='delivery.coverage_inputs', message='Coverage not checked; supply ' + ', '.join(missing),
                             location='inputs', check='contest_coverage'))
    else:
        coverage = contest_coverage.inspect(values['requirements'], tex_text, values['model_contract'],
                                            values['figure_plan'], pdf_pages=pdf_pages)
        reports['contest_coverage'] = coverage
        warnings.extend(dict(warning, check='contest_coverage') for warning in coverage['warnings'])
    if values['reader_review'] is None:
        warnings.append(dict(code='delivery.reader_pending', message='Fresh packet-reader review not supplied',
                             location='reader_review', check='reader'))
    elif values['requirements'] is None:
        warnings.append(dict(code='delivery.reader_requirements', message='Reader coverage needs problem_items',
                             location='requirements', check='reader'))
    else:
        review = values['reader_review']
        reader_warnings = reader_packet.review_warnings(review, values['requirements'].get('problem_items', []))
        if not isinstance(review, dict) or review.get('source_pdf_sha256') != pdf_sha256:
            reader_warnings.append(dict(code='reader.pdf_binding', message='Reader review is not bound to this PDF',
                                        location='reader_review'))
        reports['reader'] = dict(schema_version=1, type='reader_diagnostic', diagnostic_only=True,
                                 warnings=reader_warnings)
        warnings.extend(dict(warning, check='reader') for warning in reader_warnings)
    # Match parsed metadata to the bytes whose hashes will be saved in receipt.
    for name, path in paths.items():
        if path is not None and hashlib.sha256(Path(path).read_bytes()).hexdigest() != bindings[name]['sha256']:
            raise ValueError(f'Manuscript diagnostic input changed while being read: {name}')
    return dict(schema_version=1, diagnostic_only=True, warnings=warnings, reports=reports,
                inputs=bindings, problem_year=problem_year, allow_anachronism=allow_anachronism,
                note='New manuscript diagnostics are warnings; no calibrated rejection rule has been authorized.')
