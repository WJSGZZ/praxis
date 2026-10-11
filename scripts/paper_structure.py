"""Static review requests for sole numbered child headings, using LatexWalker.

This checks literal LaTeX structure, not writing quality or mathematical truth.
It does not execute TeX, expand macros, evaluate conditions, or read input files.
The optional review binds every approval to the exact UTF-8 source hash.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pylatexenc
from pylatexenc.latex2text import LatexNodes2Text
from pylatexenc.latexwalker import (
    LatexCharsNode, LatexEnvironmentNode, LatexGroupNode, LatexMacroNode,
    LatexMathNode, LatexWalker, LatexWalkerEndOfStream, LatexWalkerError, LatexWalkerParseError,
    get_default_latex_context_db,
)
from pylatexenc.macrospec import (
    EnvironmentSpec, MacroSpec, MacroStandardArgsParser, ParsedMacroArgs,
    VerbatimArgsParser,
)


LEVELS = {'chapter': 0, 'section': 1, 'subsection': 2, 'subsubsection': 3}
RAW_ENVIRONMENTS = {
    'verbatim': '', 'verbatim*': '', 'Verbatim': '[', 'Verbatim*': '[',
    'lstlisting': '[', 'lstlisting*': '[', 'minted': '[{', 'minted*': '[{',
}
DEFINITIONS = {
    'newcommand': '*{[[{', 'renewcommand': '*{[[{', 'providecommand': '*{[[{',
    'DeclareRobustCommand': '*{[[{',
    'newenvironment': '*{[[{{', 'renewenvironment': '*{[[{{',
    **{name: '{{{' for name in (
        'NewDocumentCommand', 'RenewDocumentCommand', 'ProvideDocumentCommand',
        'DeclareDocumentCommand', 'NewExpandableDocumentCommand',
        'RenewExpandableDocumentCommand', 'ProvideExpandableDocumentCommand',
        'DeclareExpandableDocumentCommand',
    )},
    **{name: '{{{{' for name in (
        'NewDocumentEnvironment', 'RenewDocumentEnvironment',
        'ProvideDocumentEnvironment', 'DeclareDocumentEnvironment',
    )},
}
PRIMITIVE_DEFINITIONS = {'def', 'gdef', 'edef', 'xdef'}
LIMITS = [
    'Only literal chapter/section/subsection/subsubsection commands in parsed '
    'groups and environments are inspected; macro arguments are not document body.',
    'An unstarred command is treated as numbered; numbering counters, secnumdepth, '
    'custom heading commands and class/package behavior are not simulated.',
    'Macros are not expanded and conditions are not evaluated; conditional branches '
    'may contain headings that do not appear in the compiled document.',
    'External input/include files are not read. Unknown macro signatures and '
    'catcode changes can affect static coverage. This is not a TeX compiler.',
    'passed means the current static candidates have been handled with a valid '
    'source-bound review, or none were found; it does not certify article quality.',
]


class _CommentAwareArgs(MacroStandardArgsParser):
    """Use the official argument parser after skipping inter-argument comments."""

    def parse_args(self, w, pos, parsing_state=None):
        cursor, arguments = pos, []
        for kind in self.argspec:
            while True:
                try:
                    token = w.get_token(cursor, parsing_state=parsing_state)
                except LatexWalkerEndOfStream:
                    break
                if token.tok != 'comment':
                    break
                cursor = token.pos + token.len
            parsed, start, length = MacroStandardArgsParser(kind).parse_args(
                w, cursor, parsing_state)
            arguments.extend(parsed.argnlist)
            cursor = start + length
        return ParsedMacroArgs(argspec=self.argspec, argnlist=arguments), pos, cursor - pos


class _TitleFormatArgs:
    """titlesec has distinct documented signatures for titleformat and its star."""

    def parse_args(self, w, pos, parsing_state=None):
        star, start, length = _CommentAwareArgs('*').parse_args(w, pos, parsing_state)
        spec = '{{' if star.argnlist[0] is not None else '{[{{{{['
        args, rest_start, rest_length = _CommentAwareArgs(spec).parse_args(
            w, start + length, parsing_state)
        return (ParsedMacroArgs(argspec='*' + spec, argnlist=star.argnlist + args.argnlist),
                pos, rest_start + rest_length - pos)


class _RawEnvironmentArgs(_CommentAwareArgs):
    """Adapt the documented verbatim parser pattern to fixed environment names."""

    def __init__(self, name, prefix):
        super().__init__(prefix)
        self.end_marker = '\\end{' + name + '}'

    def parse_args(self, w, pos, parsing_state=None):
        args, start, length = super().parse_args(w, pos, parsing_state)
        body_start = start + length
        end = w.s.find(self.end_marker, body_start)
        if end < 0:
            raise LatexWalkerParseError(
                s=w.s, pos=body_start, msg='Missing literal ' + self.end_marker)
        raw = w.make_node(LatexCharsNode, pos=body_start, len=end - body_start,
                          chars=w.s[body_start:end], parsing_state=parsing_state)
        return (ParsedMacroArgs(argspec=self.argspec + '{',
                                argnlist=args.argnlist + [raw]), pos, end - pos)


class _InlineVerbatimArgs(_CommentAwareArgs):
    def parse_args(self, w, pos, parsing_state=None):
        prefix, start, length = super().parse_args(w, pos, parsing_state)
        body_start = start + length
        if body_start >= len(w.s):
            raise LatexWalkerParseError(s=w.s, pos=body_start,
                                        msg='Missing inline verbatim argument')
        raw, raw_start, raw_length = VerbatimArgsParser('verb-macro').parse_args(
            w, body_start, parsing_state)
        return (ParsedMacroArgs(argspec=self.argspec + '{',
                                argnlist=prefix.argnlist + raw.argnlist),
                pos, raw_start + raw_length - pos)


class _PrimitiveDefinitionArgs:
    """Consume a primitive definition with the existing token/group parser."""

    def parse_args(self, w, pos, parsing_state=None):
        name, start, length = w.get_latex_expression(pos, parsing_state=parsing_state)
        cursor = start + length
        while True:
            token = w.get_token(cursor, environments=False, parsing_state=parsing_state)
            if token.tok == 'brace_open' and token.arg == '{':
                body, body_start, body_length = w.get_latex_braced_group(
                    token.pos, parsing_state=parsing_state)
                return (ParsedMacroArgs(argspec='{{', argnlist=[name, body]),
                        pos, body_start + body_length - pos)
            cursor = token.pos + token.len


def _context():
    context = get_default_latex_context_db()
    context.add_context_category(
        'praxis-paper-structure', prepend=True,
        macros=[MacroSpec(name, _CommentAwareArgs('*[{')) for name in LEVELS]
        + [MacroSpec(name, _CommentAwareArgs(args)) for name, args in DEFINITIONS.items()]
        + [MacroSpec(name, _PrimitiveDefinitionArgs()) for name in PRIMITIVE_DEFINITIONS]
        + [MacroSpec('verb', _InlineVerbatimArgs('*')),
           MacroSpec('lstinline', _InlineVerbatimArgs('*[')),
           MacroSpec('let', '{{'), MacroSpec('titleformat', _TitleFormatArgs()),
           MacroSpec('titlespacing', _CommentAwareArgs('*{{{{['))],
        environments=[EnvironmentSpec(name, _RawEnvironmentArgs(name, prefix))
                      for name, prefix in RAW_ENVIRONMENTS.items()],
    )
    return context


def _argument_tex(node, text):
    if isinstance(node, LatexGroupNode):
        return text[node.pos + 1:node.pos + node.len - 1]
    return node.latex_verbatim()


def _headings(nodes, walker, text):
    headings, unexpanded, stack, occurrences = [], [], [], {}
    # Without a configured input directory, the official text converter does
    # not access the filesystem, even for input/include inside a title.
    converter = LatexNodes2Text()

    def visit(items):
        for node in items:
            if isinstance(node, LatexMathNode) or node.parsing_state.in_math_mode:
                continue
            if isinstance(node, LatexMacroNode):
                name = node.macroname
                line, column = walker.pos_to_lineno_colno(node.pos)
                if name in DEFINITIONS or name in PRIMITIVE_DEFINITIONS:
                    unexpanded.append({'kind': 'macro_definition', 'macro': name, 'line': line})
                elif name in {'input', 'include', 'includeonly'}:
                    unexpanded.append({'kind': 'external_input', 'macro': name, 'line': line})
                elif name.startswith('if') or name in {'else', 'fi'}:
                    unexpanded.append({'kind': 'conditional', 'macro': name, 'line': line})
                if name not in LEVELS:
                    continue
                star, short, title = node.nodeargd.argnlist
                if title.len == 0:
                    raise LatexWalkerParseError(s=text, pos=node.pos,
                                                msg='Heading has no title in inspected document body')
                level = LEVELS[name]
                while stack and stack[-1]['level'] >= level:
                    stack.pop()
                parent = stack[-1] if stack else None
                title_tex = _argument_tex(title, text)
                key = (parent['id'] if parent else None, name, star is None, title_tex)
                occurrences[key] = occurrences.get(key, 0) + 1
                identity = json.dumps([*key, occurrences[key]], ensure_ascii=False)
                heading = {
                    'id': 'heading-' + hashlib.sha256(identity.encode()).hexdigest()[:24],
                    'name': name, 'level': level, 'numbered': star is None,
                    'title': ' '.join(converter.node_to_text(title).split()),
                    'title_tex': title_tex,
                    'short_title_tex': _argument_tex(short, text) if short else None,
                    'line': line, 'column': column, 'position': node.pos,
                    'parent_id': parent['id'] if parent else None, 'children': [],
                }
                if parent:
                    parent['children'].append(heading['id'])
                headings.append(heading)
                stack.append(heading)
            elif isinstance(node, LatexGroupNode):
                visit(node.nodelist)
            elif isinstance(node, LatexEnvironmentNode):
                if node.environmentname not in RAW_ENVIRONMENTS:
                    visit(node.nodelist)

    visit(nodes)
    return headings, unexpanded


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def _review(candidates, tex_sha256, review_path):
    status = {'provided': review_path is not None, 'valid': None, 'approved_ids': []}
    if review_path is None:
        return status, []
    status['path'] = str(review_path)
    status['valid'] = False
    try:
        review = json.loads(Path(review_path).read_bytes().decode('utf-8'),
                            object_pairs_hook=_no_duplicate_keys)
        if not isinstance(review, dict):
            raise ValueError('Review must be a JSON object')
        if review.get('tex_sha256') != tex_sha256:
            raise ValueError('Review tex_sha256 does not match the current UTF-8 source')
        approvals = review.get('approved_single_child_nodes')
        if not isinstance(approvals, list):
            raise ValueError('approved_single_child_nodes must be a list')
        known = {candidate['id'] for candidate in candidates}
        reasons = {}
        for approval in approvals:
            if not isinstance(approval, dict) or not isinstance(approval.get('id'), str):
                raise ValueError('Every approval requires an id string and a reason')
            node_id = approval['id']
            if node_id not in known:
                raise ValueError('Unknown single-child candidate id: ' + node_id)
            if node_id in reasons:
                raise ValueError('Duplicate single-child candidate id: ' + node_id)
            reason = approval.get('reason')
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError('Approval reason must be a nonempty string: ' + node_id)
            reasons[node_id] = reason.strip()
    except (OSError, UnicodeError, ValueError) as error:
        return status, [{'kind': 'review_error', 'message': str(error)}]
    # Apply none of the approvals until the entire review has been validated.
    for candidate in candidates:
        if candidate['id'] in reasons:
            candidate['approved'] = True
            candidate['approval_reason'] = reasons[candidate['id']]
    status.update(valid=True, approved_ids=list(reasons))
    return status, []


def inspect_structure(text: str, review_path=None) -> dict:
    """Return JSON-compatible headings, review candidates and explicit limits.

    A candidate is a heading with exactly one unstarred direct child. Starred
    headings delimit ancestry but do not count as numbered children. Candidate
    IDs are stable under prose/line changes; every review still requires the
    exact current source hash. Parse/review errors always prevent ``passed``.
    """
    if not isinstance(text, str):
        raise TypeError('text must be a string')
    result = {
        'schema_version': 1, 'tex_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        'parser': {'name': 'pylatexenc.latexwalker.LatexWalker',
                   'version': pylatexenc.__version__, 'tolerant_parsing': False},
        'scope': 'literal-heading-static-review', 'limitations': list(LIMITS),
        'parsed': False, 'headings': [], 'unexpanded_constructs': [],
        'candidates': [], 'unresolved': [], 'errors': [],
        'review': {'provided': review_path is not None, 'valid': None, 'approved_ids': []},
        'passed': False,
    }
    walker = LatexWalker(text, latex_context=_context(), tolerant_parsing=False)
    try:
        nodes, _, _ = walker.get_latex_nodes()
        headings, unexpanded = _headings(nodes, walker, text)
    except LatexWalkerError as error:
        result['errors'].append({'kind': 'parse_error', 'message': str(error),
                                 'line': getattr(error, 'lineno', None),
                                 'column': getattr(error, 'colno', None)})
        return result
    result.update(parsed=True, headings=headings, unexpanded_constructs=unexpanded)
    by_id = {heading['id']: heading for heading in headings}
    for parent in headings:
        numbered_children = [by_id[node_id] for node_id in parent['children']
                             if by_id[node_id]['numbered']]
        if len(numbered_children) != 1:
            continue
        child = numbered_children[0]
        result['candidates'].append({
            'id': 'single-child-' + parent['id'],
            'parent_id': parent['id'], 'child_id': child['id'],
            'parent_title': parent['title'], 'child_title': child['title'],
            'parent_line': parent['line'], 'child_line': child['line'],
            'parent_level': parent['level'], 'child_level': child['level'],
            'message': 'Review whether this sole numbered child needs a distinct role '
                       'or should be merged into its parent; this is not a mathematical error.',
            'approved': False, 'approval_reason': None,
        })
    result['review'], result['errors'] = _review(
        result['candidates'], result['tex_sha256'], review_path)
    result['unresolved'] = [candidate for candidate in result['candidates']
                            if not candidate['approved']]
    result['passed'] = not result['errors'] and not result['unresolved']
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tex', type=Path, help='UTF-8 TeX source; external input files are not read')
    parser.add_argument('--review', type=Path, help='Source-bound JSON approval of justified sole children')
    args = parser.parse_args(argv)
    try:
        result = inspect_structure(args.tex.read_bytes().decode('utf-8'), args.review)
    except (OSError, UnicodeError) as error:
        result = {'passed': False, 'tex_sha256': None, 'headings': [], 'candidates': [],
                  'unresolved': [], 'errors': [{'kind': 'input_error', 'message': str(error)}],
                  'scope': 'literal-heading-static-review', 'limitations': list(LIMITS)}
    result['source'] = str(args.tex)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
