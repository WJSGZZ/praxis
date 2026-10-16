"""Warning-only consistency checks for explicit Arabic quantities in key prose.

Compares Summary/conclusion/Memo quantities to finite JSON numbers and literal
body table cells. Value agreement is evidence of consistency, not of provenance,
correct units, scientific truth or adequate support for the surrounding claim.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_UP
import json
from pathlib import Path
import re

from scripts.manuscript import (
    NUMBER, diagnostic, document, load_json, numeric_results, plain_text,
    quantities, sections, significant_digits, strip_comments, warning,
)


def _matches(claim: Decimal, literal: str, candidate: Decimal) -> str | None:
    with localcontext() as context:
        context.prec = max(50, len(claim.as_tuple().digits), len(candidate.as_tuple().digits)) + 10
        if claim == candidate:
            return 'exact'
        scale = max(abs(claim), abs(candidate))
        if scale and abs(claim - candidate) <= Decimal('0.001') * scale:
            return 'relative_1e-3'
        # Round the evidence to the displayed significant digits, never the
        # other way around. Decimal avoids binary artefacts at display ties.
        digits = significant_digits(literal)
        exponent = claim.adjusted() - digits + 1 if claim else Decimal(literal.replace(',', '')).as_tuple().exponent
        try:
            rounded = candidate.quantize(Decimal(1).scaleb(exponent), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            return None
        return 'display_rounding' if rounded == claim else None


def inspect(tex_text, results=None) -> dict:
    parsed = document(tex_text)
    parts = sections(tex_text)
    masked = strip_comments(tex_text)
    output = diagnostic('claims')
    evidence = [{'value': value, 'source': 'results', 'location': path}
                for value, path in numeric_results(results)]
    tables = 0
    for node in parsed['tables']:
        part = next((part for part in parts if part['start'] <= node.pos < part['end']), None)
        if part is None or part['kind'] not in ('body', 'conclusion'):
            continue
        # A conclusion table does not independently support that conclusion.
        if part['kind'] == 'conclusion':
            continue
        tables += 1
        text = plain_text(masked[node.pos:node.pos + node.len])
        for match in re.finditer(r'(?<![\w.])' + NUMBER + r'(?![\w.])', text):
            evidence.append({'value': Decimal(match.group().replace(',', '')),
                             'source': 'body_table',
                             'location': {'line': tex_text.count('\n', 0, node.pos) + 1}})
    claims = []
    target_parts = [part for part in parts if part['kind'] in ('summary', 'conclusion', 'memo')]
    for part in target_parts:
        raw = masked[part['content_start']:part['end']]
        text = plain_text(raw)
        for quantity in quantities(text):
            value, literal = quantity['value'], quantity['literal']
            interpretations = [(Decimal(1), 'as_displayed')]
            unit = quantity['unit'].lower()
            if '%' in unit or re.search(r'percent|per\s*cent', unit):
                interpretations.append((Decimal(100), 'percent_as_fraction'))
            for name, factor in (('thousand', 1000), ('million', 1000000), ('billion', 1000000000)):
                if name in unit:
                    interpretations.append((Decimal(1) / factor, name + '_as_base_units'))
            match = None
            for reference in evidence:
                for multiplier, interpretation in interpretations:
                    method = _matches(value, literal, reference['value'] * multiplier)
                    if method:
                        match = {'source': reference['source'], 'location': reference['location'],
                                 'value': str(reference['value']), 'comparison': method,
                                 'interpretation': interpretation}
                        break
                if match:
                    break
            claim = {'text': quantity['text'], 'literal': literal, 'unit': quantity['unit'],
                     'section': part['title'], 'kind': part['kind'],
                     'location': {'line': tex_text.count('\n', 0, part['content_start']) + 1,
                                  'section_text_offset': quantity['start']}, 'support': match}
            claims.append(claim)
            if match is None:
                output['warnings'].append(warning('claim_value_unmatched',
                    f'{quantity["text"]} has no numerically consistent JSON value or literal body-table cell.',
                    section=part['title'], **claim['location']))
    output['metrics'].update(claims=claims, claim_count=len(claims),
        supported_count=sum(claim['support'] is not None for claim in claims),
        unmatched_count=sum(claim['support'] is None for claim in claims),
        target_sections=[{'title': p['title'], 'kind': p['kind']} for p in target_parts],
        body_tables=tables, evidence_numbers=len(evidence), results_supplied=results is not None,
        relative_tolerance='1e-3', rounding='evidence rounded to displayed significant digits, ROUND_HALF_UP')
    if not target_parts:
        output['warnings'].append(warning('claims_no_target_sections',
            'No literal Summary, conclusion or Memo region was found; coverage is empty.'))
    if parsed['unexpanded']:
        output['warnings'].append(warning('claims_unexpanded_source',
            'Macro definitions, conditions or external inputs may hide quantities or evidence; literal coverage only.'))
        output['metrics']['unexpanded_constructs'] = parsed['unexpanded']
    output['limitations'] += [
        'Covers ASCII Arabic numbers with recognized unit words, currency prefixes or percent signs, including literal SI/qty/num forms.',
        'Bare numbers, written-out numbers, figure/section labels, years without units, arbitrary TeX macros and implicit equation/table-header units are not claims.',
        'JSON support is numerical only: no unit/semantic identity is inferred from matching values; percentage fractions and named thousand/million/billion scales are tried explicitly.',
        'Table support covers literal tabular/tabular*/tabularx/longtable cells in body sections, not figure captions, appendix or key-section tables.',
    ]
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tex', type=Path)
    parser.add_argument('--results', type=Path)
    args = parser.parse_args(argv)
    try:
        output = inspect(args.tex.read_text(encoding='utf-8'), load_json(args.results) if args.results else None)
    except (OSError, UnicodeError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(output, indent=2, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
