"""Locate declared paper answers and diagnose missing contest components.

This checks authored source locations, not whether an answer is correct or
whether a figure is useful. Missing metadata is reported rather than guessed.
"""
import argparse
import json
from pathlib import Path
import re

from scripts.manuscript import plain_text, sections, strip_comments


def _norm(text):
    return re.sub(r'\s+', ' ', plain_text(text)).strip().casefold()


def _locate(anchor, candidates):
    if not isinstance(anchor, str) or not anchor.strip():
        return None
    for part in candidates:
        if anchor.startswith('label:'):
            found = re.search(r'\\label\s*\{\s*' + re.escape(anchor[6:].strip()) + r'\s*\}',
                              strip_comments(part['text']))
            if found:
                return {'section': part['title'], 'source_offset': part['start'] + found.start(),
                        'anchor': anchor}
        elif _norm(anchor) and _norm(anchor) in _norm(part['text']):
            return {'section': part['title'], 'source_offset': part['start'], 'quote': anchor}
    return None


def inspect(requirements, tex_text, model_contract, figure_plan, *, pdf_pages=None):
    warnings = []

    def warn(code, message, location):
        warnings.append(dict(code=code, message=message, location=location))

    for value, name in ((requirements, 'requirements'), (model_contract, 'model_contract'),
                        (figure_plan, 'figure_plan')):
        if not isinstance(value, dict):
            raise ValueError(f'{name} must be an object')
    parts = sections(tex_text)
    clean = strip_comments(tex_text)
    groups = {kind: [part for part in parts if part['kind'] == kind]
              for kind in ('summary', 'body', 'conclusion', 'memo')}
    items = requirements.get('problem_items', [])
    locations = requirements.get('paper_locations', {})
    if not isinstance(items, list) or not isinstance(locations, dict):
        raise ValueError('problem_items must be a list and paper_locations an object')
    table = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str):
            raise ValueError('Each problem item needs a string id')
        identity = item['id']
        declared = locations.get(identity, {})
        if not isinstance(declared, dict):
            raise ValueError(f'paper_locations.{identity} must be an object')
        row = {'id': identity}
        for kind in ('summary', 'body', 'conclusion'):
            # The main body excludes summary, conclusions and audience reports.
            row[kind] = _locate(declared.get(kind), groups[kind])
            if row[kind] is None:
                warn('coverage.answer_location',
                     f'No verified {kind} source anchor for problem item {identity}', identity)
        table.append(row)
    if not items:
        warn('coverage.problem_items', 'No problem_items supplied; completeness is unknown', 'requirements')
    assumptions = requirements.get('assumptions', model_contract.get('assumptions', []))
    if not isinstance(assumptions, list):
        raise ValueError('assumptions must be a list')
    assumption_parts = [part for part in parts if re.search(r'assumptions?|假设', part['title'], re.I)]
    has_table = any(re.search(r'\\begin\s*\{(?:tabular\*?|tabularx|longtable)\}', part['text'])
                    for part in assumption_parts)
    if not has_table:
        warn('coverage.assumption_table', 'No assumption table identified in an assumptions section', 'paper')
    assumption_locations = []
    for index, assumption in enumerate(assumptions):
        if not isinstance(assumption, dict):
            raise ValueError('Each assumption must be an object')
        location = _locate(assumption.get('test_location'), parts)
        identity = assumption.get('id', str(index + 1))
        assumption_locations.append({'id': identity, 'test_location': location})
        if location is None:
            warn('coverage.assumption_test', 'No actual source location for assumption check', str(identity))
    if not assumptions:
        warn('coverage.assumption_metadata', 'Assumption-by-assumption test coverage is unknown', 'requirements')
    sensitivity = requirements.get('sensitivity', {})
    if not isinstance(sensitivity, dict):
        raise ValueError('sensitivity must be an object')
    parameters = sensitivity.get('parameters', [])
    conclusion_parameters = sensitivity.get('conclusion_parameters', [])
    if any(not isinstance(values, list) or any(not isinstance(value, str) for value in values)
           for values in (parameters, conclusion_parameters)):
        raise ValueError('Sensitivity parameter names must be lists of strings')
    intersection = sorted(set(parameters) & set(conclusion_parameters))
    if not intersection:
        warn('coverage.sensitivity_intersection',
             'Declared sensitivity parameters do not intersect declared conclusion dependencies', 'sensitivity')
    sensitivity_location = _locate(sensitivity.get('location'), parts)
    if sensitivity_location is None:
        warn('coverage.sensitivity_location', 'No source anchor for sensitivity results', 'sensitivity')
    symbols = [row['symbol'] for row in model_contract.get('symbols', [])
               if isinstance(row, dict) and isinstance(row.get('symbol'), str) and row['symbol'].strip()]
    memo_rows = []
    for part in groups['memo']:
        before = clean[:part['start']]
        beginning = strip_comments(part['text'])[:200]
        separate = bool(re.search(r'\\(?:clearpage|newpage)\s*$', before.rstrip())
                        or re.match(r'\s*\\begin\s*\{memo\}', beginning))
        if not separate:
            warn('coverage.memo_page', 'Memo page boundary not established by source', part['title'])
        content = strip_comments(part['text'])
        math = bool(re.search(r'(?<!\\)\$|\\[\[(]|\\begin\s*\{(?:equation\*?|align\*?|gather\*?)\}', content))
        if math:
            warn('coverage.memo_math', 'Audience report contains a mathematical environment', part['title'])
        prose = plain_text(content)
        found = [symbol for symbol in symbols if re.search(
            r'(?<!\w)' + re.escape(symbol) + r'(?!\w)', prose)]
        if found:
            warn('coverage.memo_symbols', 'Audience report contains contract symbols: ' + ', '.join(found),
                 part['title'])
        memo_rows.append({'title': part['title'], 'separate_page_source': separate,
                          'mathematical_environment': math, 'contract_symbols': found})
    if not groups['memo']:
        warn('coverage.memo_missing', 'No Memo/Letter/Committee section recognized; verify applicability', 'paper')
    strengths = any(re.search(r'strengths?|优点|优势', part['title'], re.I) for part in parts)
    weaknesses = any(re.search(r'weakness|limitations?|缺点|局限|不足', part['title'], re.I) for part in parts)
    if not strengths or not weaknesses:
        warn('coverage.strengths_weaknesses', 'Strengths and weaknesses sections are not both identified', 'paper')
    actual = len(re.findall(r'\\begin\s*\{figure\*?\}', clean))
    figures = figure_plan.get('figures', [])
    omissions = figure_plan.get('omissions', [])
    if (not isinstance(figures, list) or not isinstance(omissions, list)
            or any(not isinstance(row, dict) for row in figures + omissions)):
        raise ValueError('Figure plan figures and omissions must be lists of objects')
    if len(figures) != actual:
        warn('coverage.figure_count', f'Plan declares {len(figures)} figures; source has {actual}', 'figure_plan')
    for index, figure in enumerate(figures):
        for field in ('id', 'reader_question', 'data_source', 'section'):
            if not isinstance(figure.get(field), str) or not figure[field].strip():
                warn('coverage.figure_plan_field', f'Missing {field}', f'figure_plan.figures[{index}]')
        if isinstance(figure.get('id'), str) and not re.search(
                r'\\label\s*\{\s*' + re.escape(figure['id']) + r'\s*\}', clean):
            warn('coverage.figure_label', 'Planned figure label not found in source', figure['id'])
    kinds = {row.get('kind') for row in figures if isinstance(row.get('kind'), str)}
    justified_omissions = {row.get('kind') for row in omissions
                          if isinstance(row.get('reason'), str) and row['reason'].strip()}
    needed = ['structure'] + (['map'] if model_contract.get('spatial') is True else [])
    for kind in needed:
        if kind not in kinds and kind not in justified_omissions:
            warn('coverage.figure_omission', f'Explain why text/table serves better than a {kind} figure', 'figure_plan')
    if actual < 8 and not str(figure_plan.get('few_figures_reason', '')).strip():
        warn('coverage.figure_number_reason', 'Fewer than 8 figures needs a specific reader-based reason', 'figure_plan')
    return dict(schema_version=1, type='contest_coverage', diagnostic_only=True, warnings=warnings,
                locations=table, assumptions=assumption_locations, memo=memo_rows,
                metrics={'problem_items': len(items), 'sensitivity_parameter_intersection': intersection,
                         'sensitivity_location': sensitivity_location, 'assumption_table': has_table,
                         'strengths_section': strengths, 'weaknesses_section': weaknesses,
                         'source_figures': actual, 'planned_figures': len(figures)},
                limitations=['Declared source locations are verified literally, not evaluated as scientific answers.',
                             'Sensitivity intersection is declared metadata, not evidence of a computed effect.',
                             'Page boundaries are inferred from source; inspect the actual PDF as well.',
                             'Only literal figure environments and non-expanded labels are counted.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tex', type=Path)
    parser.add_argument('--requirements', required=True, type=Path)
    parser.add_argument('--model-contract', required=True, type=Path)
    parser.add_argument('--figure-plan', required=True, type=Path)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding='utf-8'))
    print(json.dumps(inspect(load(args.requirements), args.tex.read_text(encoding='utf-8'),
                             load(args.model_contract), load(args.figure_plan)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
