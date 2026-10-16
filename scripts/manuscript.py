"""Small, literal-TeX helpers shared by diagnostic manuscript checks.

Uses the existing LatexWalker context, never executes TeX or opens input/include
files. Source positions refer to the original UTF-8 Python string. This is not
a general TeX expansion engine; callers must retain the coverage limitations.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

from pylatexenc.latex2text import LatexNodes2Text
from pylatexenc.latexwalker import (
    LatexCharsNode, LatexCommentNode, LatexEnvironmentNode, LatexGroupNode,
    LatexMacroNode, LatexMathNode, LatexWalker, LatexWalkerError,
)
from pylatexenc.macrospec import EnvironmentSpec, MacroSpec
from scripts.paper_structure import (
    _context, DEFINITIONS, LEVELS, PRIMITIVE_DEFINITIONS, RAW_ENVIRONMENTS,
)

LIMITATIONS = [
    'Literal TeX only: no macro expansion, conditional evaluation or external input files.',
    'Heuristic language and Arabic-number diagnostics are review candidates, not scientific validation.',
]


def strip_comments(tex: str) -> str:
    """Mask unescaped percent comments while preserving offsets and newlines."""
    if not isinstance(tex, str):
        raise TypeError('TeX source must be a string')
    # Raw text needs the mature parser: a percent in verbatim is not a comment.
    chars = list(tex)
    for node in document(tex)['comments']:
        for index in range(node.pos, node.pos + node.len):
            if chars[index] not in '\r\n':
                chars[index] = ' '
    return ''.join(chars)


def document(tex: str) -> dict:
    if not isinstance(tex, str):
        raise TypeError('TeX source must be a string')
    context = _context()
    context.add_context_category('praxis-manuscript', prepend=True,
        macros=[MacroSpec('PraxisSummaryHeading', '{'), MacroSpec('SI', '[{{'),
                MacroSpec('qty', '[{{'), MacroSpec('num', '[{'),
                MacroSpec('url', '{'), MacroSpec('href', '{{')],
        environments=[EnvironmentSpec('summary'), EnvironmentSpec('memo', '{{{'),
                      EnvironmentSpec('strengths'), EnvironmentSpec('weaknesses')])
    try:
        nodes, _, _ = LatexWalker(tex, latex_context=context,
                                  tolerant_parsing=False).get_latex_nodes()
    except LatexWalkerError as error:
        raise ValueError('Cannot parse literal TeX: ' + str(error)) from error
    result = {'nodes': nodes, 'headings': [], 'math': [], 'comments': [],
              'ignored': [], 'tables': [], 'references': [], 'unexpanded': [],
              'start': 0, 'end': len(tex), 'shared_literal_titles': []}

    def visit(items):
        for node in items:
            if isinstance(node, LatexCommentNode):
                result['comments'].append(node)
            elif isinstance(node, LatexMathNode) or node.parsing_state.in_math_mode:
                result['math'].append(node)
            elif isinstance(node, LatexMacroNode):
                name = node.macroname
                if name in DEFINITIONS or name in PRIMITIVE_DEFINITIONS:
                    result['ignored'].append(node)
                    result['unexpanded'].append({'kind': 'macro_definition', 'position': node.pos})
                    # The shared MCM header uses this one literal metadata field.
                    # Read its declared text, without evaluating arbitrary macros.
                    args = getattr(node.nodeargd, 'argnlist', [])
                    if (name == 'newcommand' and len(args) == 5 and args[1] is not None
                            and args[1].latex_verbatim() == r'{\PraxisTitle}'
                            and args[2] is None and args[3] is None and args[4] is not None):
                        result['shared_literal_titles'].append(plain_text(args[4].latex_verbatim()))
                elif name in ('input', 'include', 'includeonly') or name.startswith('if') or name in ('else', 'fi'):
                    result['unexpanded'].append({'kind': name, 'position': node.pos})
                elif name in LEVELS or name == 'PraxisSummaryHeading':
                    args = node.nodeargd.argnlist
                    title = args[-1]
                    title_text = plain_text(title.latex_verbatim())
                    if (name == 'PraxisSummaryHeading' and title.latex_verbatim() == r'{\PraxisTitle}'
                            and len(result['shared_literal_titles']) == 1):
                        title_text = result['shared_literal_titles'][0]
                    if name == 'PraxisSummaryHeading' and not title_text.strip():
                        title_text = 'Summary'
                    result['headings'].append({'title': title_text,
                        'start': node.pos, 'content_start': node.pos + node.len,
                        'level': LEVELS.get(name, 1),
                        **({'kind': 'summary'} if name == 'PraxisSummaryHeading' else {})})
                elif name == 'appendix':
                    # This switches counters; it prints no heading of its own.
                    result['headings'].append({'title': '', 'start': node.pos,
                        'content_start': node.pos + node.len, 'level': 0, 'kind': 'appendix'})
                elif name in ('url', 'href', 'label', 'ref', 'eqref', 'pageref', 'cite', 'citep', 'citet'):
                    result['ignored'].append(node)
                elif name == 'bibitem':
                    result['references'].append(node)
            elif isinstance(node, LatexGroupNode):
                visit(node.nodelist)
            elif isinstance(node, LatexEnvironmentNode):
                name = node.environmentname
                if name in RAW_ENVIRONMENTS:
                    result['ignored'].append(node)
                    continue
                if name == 'document':
                    result['start'] = node.nodelist[0].pos if node.nodelist else node.pos
                    result['end'] = tex.rfind('\\end{document}', node.pos, node.pos + node.len)
                if name in ('abstract', 'summary', 'memo', 'letter', 'thebibliography', 'strengths', 'weaknesses'):
                    kind = {'abstract': 'summary', 'summary': 'summary', 'memo': 'memo',
                            'letter': 'memo', 'thebibliography': 'references',
                            'strengths': 'limitations', 'weaknesses': 'limitations'}[name]
                    result['headings'].append({'title': {'thebibliography': 'References',
                        'abstract': 'Abstract'}.get(name, name.title()), 'start': node.pos,
                        'content_start': node.nodelist[0].pos if node.nodelist else node.pos + node.len,
                        'level': 0, 'kind': kind, 'environment_end': node.pos + node.len})
                if name in ('tabular', 'tabular*', 'tabularx', 'longtable'):
                    result['tables'].append(node)
                visit(node.nodelist)
    visit(nodes)
    # Comments inside mathematical nodes, headings and ordinary macro arguments
    # also retain their original offsets; do not reinterpret verbatim contents.
    def comments(items):
        for node in items:
            if isinstance(node, LatexCommentNode):
                if node not in result['comments']:
                    result['comments'].append(node)
                continue
            if isinstance(node, LatexEnvironmentNode) and node.environmentname in RAW_ENVIRONMENTS:
                continue
            comments(getattr(node, 'nodelist', None) or [])
            for arg in (getattr(getattr(node, 'nodeargd', None), 'argnlist', None) or []):
                if arg is not None:
                    comments([arg])
    comments(nodes)
    result['headings'].sort(key=lambda h: h['start'])
    return result


def plain_text(tex: str) -> str:
    """Finite text conversion; preserves useful SI/qty/num literals and URLs."""
    if not isinstance(tex, str):
        raise TypeError('TeX source must be a string')
    # These simple literal signatures are used by generated scientific reports.
    tex = re.sub(r'\\(?:SI|qty)(?:\[[^\]]*\])?\{([^{}]*)\}\{([^{}]*)\}', r'\1 \2', tex)
    tex = re.sub(r'\\num(?:\[[^\]]*\])?\{([^{}]*)\}', r'\1', tex)
    tex = re.sub(r'\\(?:label|ref|eqref|pageref|cite|citep|citet)(?:\[[^\]]*\])?\{[^{}]*\}', ' ', tex)
    return LatexNodes2Text().latex_to_text(tex).replace('\u2212', '-')


def heading_kind(title: str) -> str:
    title = title.strip().lower()
    rules = (
        ('summary', r'\b(?:summary|abstract)\b|摘要'),
        ('conclusion', r'\bconclusions?\b|结论|结语'),
        ('memo', r'\b(?:memo(?:randum)?|letter|committee report|report\s+to\b[^\n]*committee|executive summary)\b|委员会报告|备忘录|致.*信'),
        ('limitations', r'\b(?:strengths?|weaknesses?|limitations?|advantages?|disadvantages?)\b|优缺点|局限|不足|优点|缺点'),
        ('references', r'\b(?:references|bibliography)\b|参考文献'),
        ('appendix', r'\bappendi(?:x|ces)\b|附录'),
        ('ai', r'\b(?:ai (?:use|usage|report)|use of ai|artificial intelligence)\b|AI\s*使用|人工智能使用'),
        ('reproducibility', r'\b(?:reproducibility|reproduction|replication)\b|复现'),
    )
    # Executive summary is a client document, not the scientific Summary Sheet.
    if re.search(r'\bexecutive summary\b', title):
        return 'memo'
    return next((kind for kind, pattern in rules if re.search(pattern, title, re.I)), 'body')


def sections(tex: str) -> list[dict]:
    """Return non-overlapping literal source sections, retaining excluded parents.

    Each dict has title/start/end/text/kind/content_start/level. A heading is
    bounded by the next literal heading; children inherit an excluded parent.
    """
    parsed = document(tex)
    headings = [h for h in parsed['headings'] if parsed['start'] <= h['start'] < parsed['end']]
    entries, stack, appendix = [], [], False
    if not headings or headings[0]['start'] > parsed['start']:
        entries.append({'title': '', 'start': parsed['start'], 'content_start': parsed['start'],
                        'level': -1, 'kind': 'body'})
    for heading in headings:
        item = dict(heading)
        while stack and stack[-1]['level'] >= item['level']:
            stack.pop()
        kind = item.get('kind', heading_kind(item['title']))
        inherited = stack[-1]['kind'] if stack else None
        if kind == 'appendix':
            appendix = True
        if kind == 'body' and inherited in {'limitations', 'references', 'appendix', 'ai', 'reproducibility'}:
            kind = inherited
        if appendix and kind == 'body':
            kind = 'appendix'
        item['kind'] = kind
        stack.append(item)
        entries.append(item)
    for index, item in enumerate(entries):
        item['end'] = entries[index + 1]['start'] if index + 1 < len(entries) else parsed['end']
        if 'environment_end' in item:
            item['end'] = min(item['end'], item['environment_end'])
        if item['kind'] == 'summary':
            # The shared Summary transition is delimited by the actual page break.
            boundary = re.search(r'\\(?:clearpage|newpage|tableofcontents)\b', tex[item['content_start']:item['end']])
            if boundary:
                item['end'] = item['content_start'] + boundary.start()
        item['text'] = tex[item['start']:item['end']]
    return entries


def warning(code: str, message: str, *, position: int | None = None,
            tex: str | None = None, **location) -> dict:
    if position is not None:
        location['offset'] = position
        if tex is not None:
            location['line'] = tex.count('\n', 0, position) + 1
    return {'code': code, 'message': message, 'location': location or {'scope': 'document'}}


def diagnostic(kind: str) -> dict:
    return {'schema_version': 1, 'type': kind, 'diagnostic_only': True,
            'warnings': [], 'metrics': {}, 'limitations': list(LIMITATIONS)}


def load_json(path: str | Path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON: ' + value)))


# Deliberately explicit unit vocabulary: no bare figure numbers, years or labels.
UNIT = (r'(?:%|percent(?:age points?)?|per\s*cent|percentage\s+points?|'
        r'USD|EUR|GBP|CNY|RMB|KES|US\$|dollars?|euros?|pounds?|yuan|'
        r'million|billion|thousand|km(?:\s*[²³23])?|m(?:\s*[²³23])?|cm|mm|ha|'
        r'kg|mg|tonnes?|tons?|lit(?:er|re)s?|mL|L|MW|kW|W|kWh|MWh|'
        r'years?|months?|weeks?|days?|hours?|minutes?|seconds?|s|h|'
        r'counties|countries|people|persons?|households?|bomas?|units?|cases?|'
        r'paths?|samples?|observations?|trials?|runs?|policies|scenarios?|'
        r'元|万元|亿元|人|户|个|年|月|天|小时|分钟|秒|公里|千米|米|公顷|吨|千克|升)')
NUMBER = r'[+-]?(?:(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
QUANTITY = re.compile(r'(?<![\w.])(?P<currency>[$€£¥])?\s*(?P<number>' + NUMBER +
    r')\s*(?P<unit>' + UNIT + r')?(?![\w])', re.I)


def quantities(text: str) -> list[dict]:
    """Arabic quantities with a known suffix unit or currency prefix only.

    Range endpoints without their own unit, arbitrary prose, written-out numbers,
    generic scientific notation macros and implicit units in equations are
    deliberately outside this lexical coverage.
    """
    found = []
    for match in QUANTITY.finditer(text):
        if not (match['currency'] or match['unit']):
            continue
        value = Decimal(match['number'].replace(',', ''))
        found.append({'literal': match['number'], 'value': value,
                      'unit': (match['currency'] or '') + (match['unit'] or ''),
                      'start': match.start(), 'end': match.end(), 'text': match.group().strip()})
    return found


def significant_digits(literal: str) -> int:
    digits = literal.lower().split('e')[0].lstrip('+-').replace(',', '').replace('.', '').lstrip('0')
    return len(digits) or 1


def numeric_results(results) -> list[tuple[Decimal, str]]:
    """Flatten finite JSON numbers; never treat IDs in strings as numeric truth."""
    output = []
    def visit(value, path):
        if value is None or isinstance(value, (str, bool)):
            return
        if type(value) in (int, float) or isinstance(value, Decimal):
            try:
                numeric = Decimal(str(value))
            except InvalidOperation as error:
                raise ValueError('Invalid numeric result at ' + path) from error
            if not numeric.is_finite():
                raise ValueError('Non-finite numeric result at ' + path)
            output.append((numeric, path))
        elif isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError('Result keys must be strings')
                visit(item, path + '.' + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, path + f'[{index}]')
        else:
            raise TypeError('Results must contain JSON values')
    if results is not None and not isinstance(results, (dict, list)):
        raise TypeError('Results must be a JSON object or array')
    visit(results, '$')
    return output
