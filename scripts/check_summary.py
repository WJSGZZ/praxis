"""Warning-only literal-TeX Summary diagnostics; no quality or correctness score."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from scripts.manuscript import (
    diagnostic, document, load_json, numeric_results, plain_text, quantities,
    sections, strip_comments, warning,
)

METHOD_TERMS = Path(__file__).resolve().parents[1] / 'evals' / 'method-terms.json'
LIMITING = re.compile(r"\b(?:not|cannot|can't|neither|without|unless|only|limitation|limited|"
                      r'caution|uncertain|however|but)\b|不能|仅|只|局限|不足|但是|然而', re.I)


def sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r'(?<=[.!?])\s+|(?<=[。！？])\s*', re.sub(r'\s+', ' ', text)) if part.strip()]


def _terms(terms):
    if terms is None:
        terms = load_json(METHOD_TERMS)
    if isinstance(terms, dict):
        terms = terms.get('terms')
    if not isinstance(terms, list) or not terms or any(not isinstance(t, str) or not t.strip() for t in terms):
        raise ValueError('method_terms must be a nonempty list of literal method names')
    return terms


def _symbols(math_text):
    math_text = re.sub(r'\\(?:text|mathrm|operatorname)\{[^{}]*\}', ' ', math_text)
    greek = re.findall(r'\\(?:alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|'
                       r'vartheta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)\b', math_text)
    bare = re.sub(r'\\[A-Za-z]+', ' ', math_text)
    # One letter, optionally followed by one literal subscript; not prose names.
    bare_symbols = re.findall(r'(?<![A-Za-z])([A-Za-z](?:_\{?[A-Za-z0-9]+\}?)?)(?![A-Za-z])', bare)
    return set(greek + [symbol.replace('{', '').replace('}', '') for symbol in bare_symbols])


def inspect(tex_text, results=None, *, method_terms=None, reader_quality=False,
            pdf_pages=None, paragraph_boundaries_known=True, profile='contest') -> dict:
    parsed = document(tex_text)
    numeric_results(results)  # Validate optional JSON; numerical consistency is check_claims' job.
    terms = _terms(method_terms)
    output = diagnostic('summary')
    summaries = [part for part in sections(tex_text) if part['kind'] == 'summary']
    if not summaries and '\\begin{document}' not in tex_text and not parsed['headings']:
        summaries = [{'start': 0, 'content_start': 0, 'end': len(tex_text), 'text': tex_text,
                      'title': 'Summary fragment'}]
        output['metrics']['input_mode'] = 'summary_fragment'
    else:
        output['metrics']['input_mode'] = 'document'
    if len(summaries) != 1:
        output['warnings'].append(warning('summary_not_unique',
            f'Expected one literal Summary/abstract region; found {len(summaries)}.'))
        output['metrics']['summary_regions'] = len(summaries)
        return output
    part = summaries[0]
    raw = strip_comments(tex_text)[part['content_start']:part['end']]
    # An environment's closing marker does not belong to its prose.
    raw = re.sub(r'\\end\{(?:abstract|summary)\}\s*$', '', raw)
    raw = re.split(r'\\(?:textbf|textit)\{(?:Key\s*words?|关键词)\}', raw, flags=re.I)[0]
    text = plain_text(raw).strip()
    paragraphs = [plain_text(p).strip() for p in re.split(r'\n\s*\n|\\par\b', raw) if plain_text(p).strip()]
    all_sentences = sentences(text)
    first_sentences = sentences(paragraphs[0]) if paragraphs else []
    methods = sorted({term for term in terms if (term in text if re.search(r'[\u3400-\u9fff]',term)
                     else re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I))})
    numbers = quantities(text)
    output['metrics'].update(summary_regions=1,
        first_paragraph_sentences=len(first_sentences) if paragraph_boundaries_known else None,
        paragraph_boundaries_known=paragraph_boundaries_known,
        sentences=len(all_sentences), method_terms_found=methods,
        quantities=[{'literal': q['literal'], 'unit': q['unit'], 'text': q['text']} for q in numbers],
        quantity_count=len(numbers), quantity_range=[1, 8], quantity_range_status='experimental',
        results_supplied=results is not None)
    loc = {'position': part['start'], 'tex': tex_text, 'section': part['title']}
    if not text:
        output['warnings'].append(warning('summary_empty', 'Summary has no extracted literal text.', **loc))
    if len(first_sentences) > 3 and paragraph_boundaries_known and profile == 'contest':
        output['warnings'].append(warning('summary_first_paragraph_long',
            f'First paragraph has {len(first_sentences)} sentences; experimental maximum is 3.', **loc))
    if not methods and profile == 'contest':
        output['warnings'].append(warning('summary_method_missing', 'No method name from the explicit vocabulary was found.', **loc))
    if not 1 <= len(numbers) <= 8 and profile == 'contest':
        output['warnings'].append(warning('summary_quantity_count',
            f'Found {len(numbers)} Arabic quantities with recognized units; experimental range is 1–8.', **loc))
    if all_sentences and LIMITING.search(all_sentences[-1]):
        output['warnings'].append(warning('summary_limiting_last_sentence',
            'Last Summary sentence contains a limiting/negative cue; review its reader-facing role.', **loc))
    if reader_quality:
        quality_text = text
        output['metrics']['reader_quality_text_source'] = 'literal_tex_abstract'
        if pdf_pages:
            # Actual rendered numbers may be produced by macros absent from literal TeX.
            # Summary Sheet metadata is not the scientific Summary paragraph.
            first = pdf_pages[0]
            anchor = re.search(r'(?:^|\n)\s*(?:摘要|Abstract|Summary)(?![ \t]*Sheet\b)(?=[.。:：\s]|$)[.。:：]?', first, re.I)
            if anchor:
                quality_text = first[anchor.end():]
                stop = re.search(r'(?:^|\n)\s*(?:Keywords?\s*:|关键词|关键字|\d+(?:\.\d+)*[.)]?\s+[^\d])', quality_text, re.I)
                if stop: quality_text = quality_text[:stop.start()]
                output['metrics']['reader_quality_text_source'] = 'actual_pdf_abstract'
            else:
                output['metrics']['reader_quality_pdf_mapping'] = 'uncertain; literal source fallback'
        quality_sentences = sentences(quality_text)
        result_cue = re.compile(r'发现|结果|提高|降低|升至|降至|由.+至|分别需|净额为|最优|'
                                r'得到|得出|求得|表明|'
                                r'\b(?:find|found|estimate|achieve|reduce|increase|gives?|yields?|coverage|gets?|gains?|predicts?|reaches?)\b', re.I)
        result_numbers = [q for sentence in quality_sentences if result_cue.search(sentence)
                          for q in quantities(sentence)]
        output['metrics']['result_quantity_count'] = len(result_numbers)
        output['metrics']['result_number_scope'] = 'unit-bearing numbers in lexical result sentences; targets and years alone do not count; semantic binding requires reader review'
        if not result_numbers:
            output['warnings'].append(warning('summary_result_numbers_missing',
                'No unit-bearing number in a recognizable result sentence; review whether the abstract states a key finding.', **loc))
        boundary = re.compile(r'^(?:(?:本文|本研究|我们|研究|we|this (?:paper|study))\s*)?'
                              r'(?:尚未|不能|未识别|未能|无法|不足|cannot|have not|does not)', re.I)
        for side, sentence in [('opening', quality_sentences[0] if quality_sentences else ''),
                               ('closing', quality_sentences[-1] if quality_sentences else '')]:
            if boundary.search(sentence):
                output['warnings'].append(warning('summary_limitation_boundary',
                    f'Abstract {side} starts with a limitation; review findings-first organization.', **loc))
    summary_symbols = set()
    definitions = {}
    for node in parsed['math']:
        symbols = _symbols(tex_text[node.pos:node.pos + node.len])
        if part['content_start'] <= node.pos < part['end']:
            summary_symbols |= symbols
        context_before = plain_text(tex_text[max(0, node.pos - 80):node.pos])
        context_after = plain_text(tex_text[node.pos + node.len:node.pos + node.len + 100])
        defined = re.search(r'\b(?:let|define|denote|where|represents?|stands for)\s*$', context_before, re.I)
        defined = defined or re.match(r'\s*(?:(?:denotes?|represents?|is defined|is the|means)\b|:)', context_after, re.I)
        if any(table.pos <= node.pos < table.pos + table.len for table in parsed['tables']):
            defined = defined or re.match(r'\s*&', tex_text[node.pos + node.len:])
        if defined:
            for symbol in symbols:
                definitions.setdefault(symbol, node.pos)
    late = []
    for symbol in sorted(summary_symbols):
        position = definitions.get(symbol)
        if position is not None and position >= part['end']:
            late.append(symbol)
            output['warnings'].append(warning('summary_symbol_defined_later',
                f'Summary uses {symbol}, with a literal definition cue later in the body.',
                position=position, tex=tex_text, symbol=symbol, summary_line=tex_text.count('\n', 0, part['start']) + 1))
    output['metrics'].update(math_symbols=sorted(summary_symbols), symbols_defined_later=late,
                             symbol_definition_scope='literal math plus nearby English definition cues')
    if parsed['unexpanded']:
        output['metrics']['unexpanded_constructs'] = parsed['unexpanded']
    output['limitations'].append('Sentence splitting and definition cues are lexical; not all abbreviations or symbolic definitions are recognized.')
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tex', type=Path)
    parser.add_argument('--results', type=Path)
    parser.add_argument('--method-terms', type=Path)
    args = parser.parse_args(argv)
    try:
        output = inspect(args.tex.read_text(encoding='utf-8'), load_json(args.results) if args.results else None,
                         method_terms=load_json(args.method_terms) if args.method_terms else None)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(output, indent=2, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
