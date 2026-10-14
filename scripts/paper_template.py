"""Single-source contest and mathematical-research layouts, embedded into standalone TeX with a drift check.

House style is not a certification of any contest edition's submission rules.
"""
import argparse
import hashlib
from pathlib import Path
import re

from scripts import texplot

ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / 'templates/mcm-style.tex'
VERSIONS = {'mcm': 4, 'cumcm': 2, 'research': 1}
# A house identity for simulations only; it is not an assigned contest team.
MCM_SIMULATION_TEAM = '7391856'
BEGIN = '% BEGIN PRAXIS MCM STYLE v4\n'
END = '% END PRAXIS MCM STYLE\n'


def style_block(contest='mcm', *, layout_version=None):
    if contest not in VERSIONS:
        raise ValueError('Unknown layout profile')
    name = contest.upper()
    version = VERSIONS[contest] if layout_version is None else layout_version
    supported = (1, 2, 3, 4) if contest == 'mcm' else (VERSIONS[contest],)
    if type(version) is not int or version not in supported:
        raise ValueError('Unsupported archived layout version')
    suffix = f'-v{version}' if contest == 'mcm' and version != VERSIONS[contest] else ''
    source = ROOT / f'templates/{contest}-style{suffix}.tex'
    return (f'% BEGIN PRAXIS {name} STYLE v{version}\n' +
            source.read_text(encoding='utf-8').replace('@@PLOTS@@', texplot.PREAMBLE) +
            f'% END PRAXIS {name} STYLE\n')


def escape(text):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%',
                    '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{',
                    '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(c, c) for c in text)


def preamble(team=None, title='', contest='mcm', *, layout_version=None, identity_mode=None):
    """Fixed simulation identity, explicit contest identity, or deliberate archive.

    Existing nonzero positional team callers retain their exact preamble bytes.
    A supplied contest number is a caller declaration, not verified registration.
    """
    identity = ''
    if contest == 'mcm':
        if identity_mode not in (None, 'simulation', 'contest', 'archive'):
            raise ValueError('Identity mode must be simulation, contest or archive')
        if identity_mode is None and team is None:
            identity_mode = 'simulation'
        if identity_mode == 'simulation':
            if team not in (None, MCM_SIMULATION_TEAM):
                raise ValueError('Simulation team must use the fixed MCM simulation identity')
            team = MCM_SIMULATION_TEAM
        if not isinstance(team, str) or not re.fullmatch(r'[0-9]{1,12}', team):
            raise ValueError('Team number must contain ASCII digits; real entries require an explicitly supplied assigned number')
        if identity_mode == 'archive':
            if layout_version is None:
                raise ValueError('Archive identity requires an explicit layout version')
        elif not team.strip('0'):
            raise ValueError('All-zero team placeholders cannot be used for current delivery')
        identity = r'\newcommand{\PraxisTeam}{' + team + '}\n'
        if identity_mode in ('simulation', 'contest'):
            identity += r'\newcommand{\PraxisIdentityMode}{' + identity_mode + '}\n'
    elif identity_mode is not None:
        raise ValueError('MCM identity mode is only applicable to MCM/ICM papers')
    return (identity +
            r'\newcommand{\PraxisTitle}{' + escape(title) + '}\n' +
            style_block(contest, layout_version=layout_version) + r'\begin{document}' + '\n')


def summary_header(problem, *, edition=None, layout_version=None, legacy=False):
    """Year-specific three-column summary metadata; running headers start later.

    Edition is explicit for new papers. Sizes are house style, not COMAP rules.
    Versions 1, 2 and 3 are available for deliberate frozen-archive reproduction.
    Versions 2 through 4 share the same year-specific summary metadata.
    """
    if problem not in 'ABCDEF' or len(problem) != 1:
        raise ValueError('Choose an MCM/ICM problem letter A–F')
    version = VERSIONS['mcm'] if layout_version is None else layout_version
    if version == 1:
        style = 'fancy' if legacy else 'empty'
        middle = (r'\textbf{Summary Sheet}' if legacy else
                  r'\shortstack{\textbf{Summary Sheet}\\Page \thepage{} of \pageref{LastPage}}')
        return (r'\thispagestyle{' + style + r'}\begin{center}\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}ccc}' + '\n' +
                r'\textbf{Problem Chosen}&\textbf{MCM/ICM}&\textbf{Team Control Number}\\' + '\n' +
                r'{\Large\textbf{' + problem + r'}}&' + middle + r'&{\Large\textbf{\PraxisTeam}}\end{tabular*}\end{center}\vspace{-4pt}\hrule\vspace{10pt}' + '\n')
    if version not in (2, 3, 4) or legacy:
        raise ValueError('Legacy summary metadata requires explicit layout_version=1')
    if not re.fullmatch(r'(?:19|20)[0-9]{2}', str(edition)):
        raise ValueError('Supply the original contest edition (YYYY), not the current date')
    return (r'\thispagestyle{empty}\begin{center}\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}ccc}' + '\n' +
            r'\parbox[t]{.30\linewidth}{\centering\textbf{Problem Chosen}\\[5pt]{\fontsize{26}{30}\selectfont\bfseries ' + problem + r'}}&' + '\n' +
            r'\parbox[t]{.30\linewidth}{\centering\textbf{' + str(edition) + r'\\MCM/ICM\\Summary Sheet}}&' + '\n' +
            r'\parbox[t]{.30\linewidth}{\centering\textbf{Team Control Number}\\[5pt]{\fontsize{26}{30}\selectfont\bfseries\PraxisTeam}}' + '\n' +
            r'\end{tabular*}\end{center}\vspace{-4pt}\hrule\vspace{10pt}' + '\n')


def summary_heading(title='Summary', *, layout_version=None):
    """Centered summary title followed by ordinary, indented body paragraphs.

    MCM v4 uses the shared heading macro and LaTeX's heading transition.
    Historical versions keep their exact former center-environment behavior.
    Metadata, titles, lists, captions and letter salutations are separate roles.
    """
    version = VERSIONS['mcm'] if layout_version is None else layout_version
    if type(version) is not int or version not in (1, 2, 3, 4):
        raise ValueError('Unsupported archived layout version')
    if version < 4:
        return r'\begin{center}{\Large\bfseries ' + escape(title) + r'}\end{center}' + '\n'
    return r'\PraxisSummaryHeading{' + escape(title) + '}\n'


def table_of_contents(*, depth=2):
    """Optional isolated contents with a selected useful navigation depth."""
    if type(depth) is not int or depth not in (1, 2, 3):
        raise ValueError('Contents depth must be 1, 2 or 3')
    prefix = '' if depth == 2 else r'\setcounter{tocdepth}{' + str(depth) + r'}' + '\n'
    return prefix + r'\clearpage\tableofcontents\clearpage' + '\n'


SECTION_BEGIN = '% BEGIN PRAXIS SEPARATE SECTION v1\n'
SECTION_END = '% END PRAXIS SEPARATE SECTION\n'


def section_component(title, body, *, separate_page=False, in_contents=False):
    """An optional unnumbered section, with explicit boundaries when selected.

    The caller supplies truthful TeX content and chooses placement from the
    applicable contest/journal policy. clearpage also flushes pending floats.
    Ordinary declarations, references and later appendices can stay continuous.
    """
    heading = r'\section*{' + escape(title) + '}\n'
    if in_contents:
        heading += r'\addcontentsline{toc}{section}{' + escape(title) + '}\n'
    content = heading + body.rstrip() + '\n'
    if separate_page:
        return SECTION_BEGIN + '\\clearpage\n' + content + '\\clearpage\n' + SECTION_END
    return content


def ai_report(body, *, title='Report on Use of AI', in_contents=True):
    """Full, isolated disclosure report; not an inline CUMCM declaration."""
    return section_component(title, body, separate_page=True, in_contents=in_contents)


def _check_section_boundaries(text):
    # Check markers before removing comments. Bare, already-correct historical
    # sections remain supported; marked components must retain both boundaries.
    tokens = list(re.finditer(re.escape(SECTION_BEGIN) + '|' + re.escape(SECTION_END), text))
    if len(tokens) % 2:
        raise ValueError('Incomplete separate-section component')
    for start, end in zip(tokens[::2], tokens[1::2]):
        if start.group() != SECTION_BEGIN or end.group() != SECTION_END:
            raise ValueError('Nested or misplaced separate-section component')
        body = re.sub(r'(?<!\\)%[^\n]*', '', text[start.end():end.start()])
        if not re.match(r'\s*\\clearpage\b', body) or not re.search(r'\\clearpage\s*$', body):
            raise ValueError('Separate-section component requires clearpage before and after its content')


def check(text, contest='mcm', *, layout_mode='archive'):
    """Reject missing/modified styles and explicit layout/page-counter overrides.

    This static gate detects direct commands, not arbitrary TeX macro expansion.
    Local font commands in content (including captions) are not macro-expanded.
    Actual rendered pagination and role-specific font sizes require PDF inspection.
    """
    # Inspect TeX line endings semantically; receipts still bind untouched bytes.
    # Windows Path.write_text emits CRLF even with LF Git checkout attributes.
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    if layout_mode not in {'current', 'archive'}:
        raise ValueError('Layout mode must be current or archive')
    version = VERSIONS[contest]
    if contest == 'mcm':
        markers = re.findall(r'% BEGIN PRAXIS MCM STYLE v([0-9]+)\n', text)
        if len(markers) != 1:
            raise ValueError('Require exactly one shared MCM style version')
        version = int(markers[0])
        if layout_mode == 'current' and version != VERSIONS['mcm']:
            raise ValueError('Current MCM delivery requires the current shared style v'
                             + str(VERSIONS['mcm']) + '; use explicit archive mode for historical reproduction')
    block = style_block(contest, layout_version=version)
    begin = f'% BEGIN PRAXIS {contest.upper()} STYLE v{version}\n'
    end = f'% END PRAXIS {contest.upper()} STYLE\n'
    if text.count(begin) != 1 or text.count(end) != 1 or block not in text:
        raise ValueError('Paper layout differs from the shared source; regenerate with scripts.paper_template')
    _check_section_boundaries(text)
    rest = text.replace(block, '')
    rest = re.sub(r'(?<!\\)%[^\n]*', '', rest)
    numbering_override = (
        r'\\pagenumbering\b|'
        r'\\(?:setcounter|addtocounter)\s*\{\s*page\s*\}|'
        r'\\(?:renewcommand|newcommand|providecommand)\s*\*?\s*'
        r'(?:\{\s*\\thepage\s*\}|\\thepage\b)|'
        r'\\(?:def|gdef|edef|xdef|let)\s*\\thepage\b')
    if re.search(numbering_override, rest):
        raise ValueError('Direct page numbering override outside the shared style')
    if contest == 'mcm':
        # Only this exact shared component may suppress the running header.
        # Accept the former component so historical papers remain reproducible.
        if version == 1:
            headers = [summary_header(letter, layout_version=1, legacy=legacy)
                       for letter in 'ABCDEF' for legacy in (False, True)]
        else:
            years = set(re.findall(r'\\textbf\{((?:19|20)[0-9]{2})\\\\MCM/ICM', rest))
            headers = [summary_header(letter, edition=year, layout_version=version)
                       for letter in 'ABCDEF' for year in years]
        occurrences = sum(rest.count(header) for header in headers)
        if occurrences != 1:
            raise ValueError('Require exactly one shared summary-page header')
        used = next(header for header in headers if header in rest)
        document_start = rest.find(r'\begin{document}')
        prefix = rest[document_start + len(r'\begin{document}'):rest.index(used)]
        if document_start < 0 or re.search(r'\\(?:clearpage|newpage|pagebreak|tableofcontents)\b', prefix):
            raise ValueError('Summary metadata must start on the first document page')
        for header in headers:
            rest = rest.replace(header, '')
    if contest == 'mcm':
        components = [table_of_contents(depth=d) for d in (1, 2, 3)]
        for component in components:
            rest = rest.replace(component, r'\clearpage\tableofcontents\clearpage' + '\n')
    # Hanging references locally disable paragraph indentation; this does not
    # replace the document paragraph style.
    rest = re.sub(r'(\\begingroup\\(?:small|normalsize)(?:\\sloppy)?(?:\\raggedright)?)\\setlength\{\\parindent\}\{0pt\}', r'\1', rest)
    # Covers the ways the two generators originally drifted. Local table widths,
    # mathematical environments and bibliographic formatting remain content choices.
    prohibited = (r'\\(?:documentclass|geometry|newgeometry|restoregeometry|linespread|'
                  r'pagestyle|fancyhf|fancyhead|fancyfoot|captionsetup|titleformat|titlespacing|titlecontents|ctexset|setCJKmainfont|setmainfont|setsansfont|setmonofont|setCJKsansfont|setCJKmonofont|fontfamily|fontencoding)\b|'
                  r'\\(?:setcounter|addtocounter)\s*\{(?:tocdepth|secnumdepth)\}|'
                  r'\\(?:renewcommand|def)\s*\{?\\(?:normalsize|familydefault|rmdefault|sfdefault|baselinestretch)\b|'
                  r'\\thispagestyle\s*\{(?:empty|plain)\}|'
                  r'\\setlength\s*\{\\(?:parindent|parskip|textwidth|textheight|headheight|oddsidemargin)\}|'
                  r'\\usepackage(?:\[[^\]]*\])?\{[^}]*\b(?:geometry|fontspec|fontenc|lmodern|newtxtext|newtxmath|times|mathptmx)[^}]*\}')
    if re.search(prohibited, rest):
        raise ValueError('Direct layout override outside the shared style')
    if contest == 'mcm' and layout_mode == 'current':
        identity = mcm_identity(text)
        if not identity['team'].strip('0'):
            raise ValueError('All-zero team placeholders cannot be used for current delivery')
        preamble_text = rest.split(r'\begin{document}', 1)[0]
        modes = re.findall(r'\\newcommand\s*\{\\PraxisIdentityMode\}\s*\{([^{}]*)\}', preamble_text)
        if len(modes) > 1 or (modes and modes[0] not in ('simulation', 'contest')):
            raise ValueError('Current identity mode must be simulation or contest')
        if modes == ['simulation'] and identity['team'] != MCM_SIMULATION_TEAM:
            raise ValueError('Simulation team must use the fixed MCM simulation identity')
        if re.search(r'\\(?:renewcommand|providecommand)\s*\{\\PraxisTeam\}|\\(?:def|gdef|edef|xdef|let)\s*\\PraxisTeam\b', rest):
            raise ValueError('Team identity must have one literal declaration without overrides')
        # Current author identities in letters/disclosures share the macro.
        # Cited teams and actual random seeds remain their own truthful data.
        identity_content = re.sub(r'\\begin\s*\{(Verbatim|verbatim|lstlisting|minted)\}.*?\\end\s*\{\1\}',
                                  '', rest, flags=re.S)
        literal_field = (r'\\textbf\{From:\}\s*Team\s*[0-9]+\b|'
                         r'(?:Respectfully|Sincerely),[\s\\]*Team\s*[0-9]+\b|'
                         r'internal control identifier\s+[0-9]+\b')
        if re.search(literal_field, identity_content):
            raise ValueError('Current team signatures and disclosure identity must use the shared PraxisTeam macro')
        disclosure = review_mcm_identity_statements(identity_content, identity['team'])
        if disclosure['errors']:
            raise ValueError('Current MCM author identity: ' + '; '.join(disclosure['errors']))
        titles = review_figure_titles(rest)
        if titles['errors']:
            raise ValueError('Current MCM figure titles: ' + '; '.join(titles['errors']))
        _check_current_indentation(rest)
    if contest == 'research' and not re.search(r'\\title\s*\[[^\]\n]+\]', rest):
        raise ValueError('Research manuscripts need an explicit short running title')
    # Literal source/code in disclosure records is content, not an executed
    # section or bibliography. Mask conventional verbatim blocks for this scan.
    structure = re.sub(r'\\begin\s*\{(Verbatim|verbatim|lstlisting|minted)\}.*?\\end\s*\{\1\}',
                       lambda m: ' ' * len(m.group()), rest, flags=re.S)
    sections = list(re.finditer(r'\\section\s*\*?\s*(?:\[[^\]]*\]\s*)?\{([^{}]*)\}', structure))
    if contest == 'cumcm':
        if r'\tableofcontents' in structure:
            raise ValueError('CUMCM papers must not have a table of contents')
        declarations = [s for s in sections if s.group(1).strip() == 'AI工具使用声明']
        references = [s.start() for s in sections if s.group(1).strip() == '参考文献']
        references += [m.start() for m in re.finditer(r'\\begin\s*\{thebibliography\}', structure)]
        if len(declarations) > 1:
            raise ValueError('CUMCM AI declaration may appear at most once')
        if declarations and references and declarations[0].start() > min(references):
            raise ValueError('CUMCM AI declaration must precede the references')
    if contest == 'mcm':
        reports = [s for s in sections if re.fullmatch(r'Report on Use of AI(?: Tools)?', s.group(1).strip(), re.I)]
        if len(reports) > 1:
            raise ValueError('AI report may appear at most once')
        if reports:
            report = reports[0]
            if not re.search(r'\\clearpage\s*$', rest[:report.start()]):
                raise ValueError('AI report must begin on a separate page with clearpage')
            if any(s.start() > report.start() for s in sections):
                raise ValueError('MCM AI report must follow all solution sections, references and appendices')
            if re.search(r'\\begin\s*\{thebibliography\}|\\(?:bibliography|printbibliography|appendix|tableofcontents)\b',
                         structure[report.end():]):
                raise ValueError('MCM AI report must follow the bibliography, appendices and contents')
        if len(re.findall(r'\\tableofcontents\b', structure)) > 1:
            raise ValueError('Contents may appear at most once')
        for toc in re.finditer(r'\\tableofcontents\b', structure):
            if not re.match(r'\s*\\clearpage\b', structure[toc.end():]):
                raise ValueError('Contents must end with an explicit clearpage before the body')
            before = structure[:toc.start()]
            body_prefix = before[before.find(r'\begin{document}') + len(r'\begin{document}'):]
            if re.search(r'\\section\s*(?:\[[^\]]*\]\s*)?\{', body_prefix):
                raise ValueError('Contents must precede the numbered scientific sections')
            if not re.search(r'\\clearpage\s*(?:\\renewcommand\{\\contentsname\}\{[^{}]*\}\s*)?$', before):
                raise ValueError('Contents must begin on a separate page with clearpage')
    return {'profile': f'praxis-{contest}-v{version}', 'style_sha256': hashlib.sha256(block.encode()).hexdigest()}


def _check_current_indentation(text):
    """Inspect literal heading transitions with the existing LatexWalker context.

    Shared v4 supplies the indentation. This check catches direct suppression at
    ordinary first paragraphs; it does not expand user macros or inspect images.
    Letter and memorandum salutations retain their separate paragraph role.
    """
    from pylatexenc.latexwalker import (
        LatexCharsNode, LatexCommentNode, LatexEnvironmentNode, LatexGroupNode,
        LatexMacroNode, LatexMathNode, LatexWalker, LatexWalkerError,
    )
    from pylatexenc.macrospec import MacroSpec
    from scripts.paper_structure import _context, DEFINITIONS, PRIMITIVE_DEFINITIONS, RAW_ENVIRONMENTS
    context = _context()
    context.add_context_category('praxis-current-summary', prepend=True,
                                 macros=[MacroSpec('PraxisSummaryHeading', '{')])
    try:
        nodes, _, _ = LatexWalker(text, latex_context=context,
                                 tolerant_parsing=False).get_latex_nodes()
    except LatexWalkerError as exc:
        raise ValueError('Current MCM indentation inspection could not parse the source: ' + str(exc)) from exc
    summaries = []

    def inspect(items):
        pending = None
        for node in items:
            if isinstance(node, LatexCommentNode):
                continue
            if isinstance(node, LatexCharsNode):
                if node.chars.strip():
                    pending = None
                continue
            if isinstance(node, LatexMathNode):
                pending = None
                continue
            if isinstance(node, LatexMacroNode):
                name = node.macroname
                if re.match(r'\\(?:@afterindentfalse|@afterheading)\b', text[node.pos:]):
                    raise ValueError('Current MCM first-paragraph indentation overrides the shared heading transition')
                if name in DEFINITIONS or name in PRIMITIVE_DEFINITIONS:
                    # The mature parser consumes balanced declaration arguments;
                    # only their literal target is inspected, never their body as
                    # an executed heading or ordinary paragraph.
                    arguments = node.nodeargd.argnlist
                    target = arguments[0] if name in PRIMITIVE_DEFINITIONS else next(
                        (argument for argument in arguments if isinstance(argument, (LatexMacroNode, LatexGroupNode))), None)
                    if target is not None and re.search(r'\\PraxisSummaryHeading\b', target.latex_verbatim()):
                        raise ValueError('Current MCM first-paragraph indentation overrides the shared summary heading')
                    continue
                if name == 'PraxisSummaryHeading':
                    summaries.append(node)
                    pending = 'summary'
                    continue
                if name in {'section', 'subsection', 'subsubsection'}:
                    title = node.nodeargd.argnlist[-1].latex_verbatim()
                    pending = None if re.search(r'\b(?:letter|memo|memorandum)\b', title, re.I) else name
                    continue
                if name == 'noindent' and pending is not None:
                    raise ValueError('Current MCM first-paragraph indentation is suppressed after ' + pending)
                if name in {'label', 'addcontentsline', 'vspace', 'hspace', 'par', 'relax'}:
                    continue
                pending = None
            elif isinstance(node, LatexEnvironmentNode):
                if node.environmentname not in RAW_ENVIRONMENTS:
                    inspect(node.nodelist)
                pending = None
            elif isinstance(node, LatexGroupNode):
                inspect(node.nodelist)
                pending = None
    inspect(nodes)
    if len(summaries) != 1:
        raise ValueError('Current MCM requires exactly one shared summary_heading() transition')


def mcm_identity(text):
    """Literal identity supplied by a checked standalone MCM source."""
    preamble_text = text.split(r'\begin{document}', 1)[0]
    preamble_text = re.sub(r'(?<!\\)%[^\n]*', '', preamble_text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    team = re.findall(r'\\newcommand\s*\{\\PraxisTeam\}\s*\{([0-9]{1,12})\}', preamble_text)
    headers = [(letter, year) for year in set(re.findall(r'\\textbf\{((?:19|20)[0-9]{2})\\\\MCM/ICM', text))
               for letter in 'ABCDEF' if summary_header(letter, edition=year) in text]
    if len(team) != 1 or len(headers) != 1:
        raise ValueError('Current MCM requires one literal team number and original-year summary identity')
    return {'team': team[0], 'problem': headers[0][0], 'edition': headers[0][1]}


def mcm_ai_report_expected(text):
    """Literal AI heading, with comments and conventional code quotes excluded."""
    text = re.sub(r'(?<!\\)%[^\n]*', '', text)
    text = re.sub(r'\\begin\s*\{(Verbatim|verbatim|lstlisting|minted)\}.*?\\end\s*\{\1\}',
                  '', text, flags=re.S)
    return bool(re.search(r'\\section\s*\*?\s*(?:\[[^\]]*\]\s*)?\{Report on Use of AI(?: Tools)?\}', text, re.I))


def review_mcm_identity_statements(text, team):
    """Catch literal current author-identity declarations outside header fields.

    Scientific zeros, seeds, cited teams and explicitly previous identities are
    different roles. This bounded prose check does not infer every paraphrase.
    The TeX caller removes comments/code; the PDF caller checks the AI tail.
    """
    pattern = re.compile(
        r'\b(?:template\s+team\s+number|(?:simulation|simulated|exercise)\s+team\s+(?:number|identifier)|'
        r'internal\s+control\s+identifier|current\s+team\s+(?:control\s+)?number)'
        r'\s*(?:is\s+)?[:#=]?\s*([0-9]{4,12})(?![0-9])', re.I)
    statements, errors = [], []
    for match in pattern.finditer(text):
        prefix = text[max(0, match.start()-80):match.start()]
        prefix = re.split(r'[.!?]\s+', prefix)[-1]
        previous = bool(re.search(r'\b(?:old|older|previous|earlier|historical|archived|original)\s+(?:\w+\s+){0,2}$', prefix, re.I))
        record = {'declaration': match.group(), 'team': match.group(1),
                  'explicitly_previous_identity': previous}
        statements.append(record)
        if not previous and match.group(1) != team:
            errors.append('author identity statement differs from current team: ' + match.group())
    return {'statements': statements, 'errors': errors,
            'scope': 'Literal template/simulation/current author-identity statements; historical attribution and numeric science retain their own roles.'}


def check_explicit_references(text):
    """Check literal references in our standalone generated documents.

    Macro-generated keys and external documents are outside this static check;
    rendering remains necessary. LastPage is provided by the shared package.
    """
    text = re.sub(r'(?<!\\)%[^\n]*', '', text)
    labels = set(re.findall(r'\\label\s*\{([^{}]+)\}', text))
    references = set(re.findall(r'\\(?:ref|pageref|eqref)\*?\s*\{([^{}]+)\}', text))
    missing = {key for key in references-labels-{'LastPage'} if '\\' not in key}
    if missing:
        raise ValueError('Unresolved explicit cross-reference: ' + ', '.join(sorted(missing)))


def review_figure_titles(text):
    """Inspect literal figure captions as short titles in the MCM house profile.

    This is a project style, not a COMAP or universal journal requirement.
    It does not certify semantics, visible line length or expanded user macros.
    Essential explanation belongs in adjacent prose; journal legends keep their
    target journal's rules. Tables, definitions and quoted code are excluded.
    """
    from pylatexenc.latexwalker import (LatexCharsNode, LatexEnvironmentNode, LatexGroupNode,
                                       LatexMacroNode, LatexWalker, LatexWalkerError)
    from pylatexenc.macrospec import MacroSpec
    from pylatexenc.latex2text import LatexNodes2Text
    from scripts.paper_structure import _context, DEFINITIONS, PRIMITIVE_DEFINITIONS, RAW_ENVIRONMENTS
    context = _context()
    context.add_context_category('praxis-figure-titles', prepend=True, macros=[
        MacroSpec('caption', '*[{'), MacroSpec('captionof', '*{[{'),
        MacroSpec('refstepcounter', '{'), MacroSpec('stepcounter', '{'),
        MacroSpec('addtocounter', '{{'), MacroSpec('setcounter', '{{'),
        MacroSpec('rule', '[{{')])
    try:
        nodes, _, _ = LatexWalker(text, latex_context=context,
                                 tolerant_parsing=False).get_latex_nodes()
    except LatexWalkerError as exc:
        raise ValueError('Figure-title inspection could not parse the source: ' + str(exc)) from exc
    titles, errors = [], []
    figure_ends = []

    def figure_prose(items):
        """Literal prose outside graphical data/labels and the caption itself."""
        found = []
        graphics = {'tikzpicture', 'axis', 'groupplot', 'picture', 'pgfpicture',
                    'pspicture', 'circuitikz', 'forest', 'tabular', 'tabular*'}
        text_macros = {'textbf', 'textit', 'emph', 'textrm', 'textsf', 'texttt',
                       'mbox', 'makebox', 'parbox'}
        for node in items:
            if isinstance(node, LatexCharsNode):
                if re.search(r'[A-Za-z\u3400-\u9fff]', node.chars):
                    found.append(node.chars.strip())
            elif isinstance(node, LatexGroupNode):
                found.extend(figure_prose(node.nodelist))
            elif isinstance(node, LatexEnvironmentNode):
                if node.environmentname not in graphics and node.environmentname not in RAW_ENVIRONMENTS:
                    found.extend(figure_prose(node.nodelist))
            elif isinstance(node, LatexMacroNode) and node.macroname in text_macros:
                args = node.nodeargd.argnlist if node.nodeargd else []
                if args and isinstance(args[-1], LatexGroupNode):
                    found.extend(figure_prose(args[-1].nodelist))
        return found

    def walk(items, environment=None):
        for node in items:
            if isinstance(node, LatexEnvironmentNode):
                if node.environmentname not in RAW_ENVIRONMENTS:
                    kind = node.environmentname.rstrip('*')
                    if kind == 'figure':
                        if figure_prose(node.nodelist):
                            line = text.count('\n', 0, node.pos) + 1
                            errors.append(f'line {line}: ordinary prose inside figure belongs in adjacent prose')
                        figure_ends.append(node.pos + node.len - len(r'\end{' + node.environmentname + '}'))
                    walk(node.nodelist, kind if kind in ('figure', 'table') else environment)
                    if kind == 'figure':
                        figure_ends.pop()
            elif isinstance(node, LatexGroupNode):
                walk(node.nodelist, environment)
            elif isinstance(node, LatexMacroNode):
                if node.macroname in DEFINITIONS or node.macroname in PRIMITIVE_DEFINITIONS:
                    continue
                arguments = node.nodeargd.argnlist if node.nodeargd else []
                is_figure = node.macroname == 'caption' and environment == 'figure'
                if node.macroname == 'captionof' and len(arguments) == 4:
                    kind = arguments[1]
                    is_figure = isinstance(kind, LatexGroupNode) and kind.latex_verbatim()[1:-1].strip() == 'figure'
                if is_figure and arguments and isinstance(arguments[-1], LatexGroupNode):
                    raw = arguments[-1].latex_verbatim()[1:-1]
                    # Retain the exact legacy manual label/counter convention.
                    raw = re.sub(r'^\s*\\normalsize\s*\\textbf\{Figure\s+\\thefigure\.\}\s*', '', raw)
                    title = LatexNodes2Text(math_mode='text').latex_to_text(raw).strip()
                    words = len(re.findall(r"[A-Za-z]+(?:[-’'][A-Za-z]+)*", title))
                    chinese = len(re.findall(r'[\u3400-\u9fff]', title))
                    sentence_text = re.sub(r'(?:\b[A-Z]\.){2,}', 'ACRONYM', title)
                    sentence_text = re.sub(r'\b(?:vs|e\.g|i\.e|s\.d|s\.e|No)\.(?=\s)', 'ABBREVIATION', sentence_text)
                    issues = []
                    if not title:
                        issues.append('empty title')
                    if re.search(r'[.!?]\s+\S', sentence_text):
                        issues.append('explanatory sentences belong in adjacent prose')
                    if words > 15 or chinese > 30:
                        issues.append('title exceeds the project short-title limit (15 English words / 30 Chinese characters)')
                    if node.macroname == 'caption' and figure_ends:
                        # A label or closing center/group is not another title.
                        # Narrative hidden in a post-caption minipage/paragraph
                        # still reads as an extended caption on the real page.
                        tail = text[node.pos + node.len:figure_ends[-1]]
                        tail = re.sub(r'(?<!\\)%[^\n]*', '', tail)
                        tail = re.sub(r'\\label\s*\{[^{}]*\}', '', tail)
                        tail = re.sub(r'\\end\s*\{[^{}]*\}', '', tail)
                        # Strip opening minipage dimensions (they are layout,
                        # never scientific content), then inspect its prose.
                        tail = re.sub(r'\\begin\s*\{minipage\}(?:\[[^\]]*\])?\s*\{[^{}]*\}', '', tail)
                        tail_visible = LatexNodes2Text(math_mode='text').latex_to_text(tail).strip(' \n\t{}')
                        if re.search(r'[A-Za-z\u3400-\u9fff]', tail_visible):
                            issues.append('post-caption explanation inside figure belongs in adjacent prose')
                    line = text.count('\n', 0, node.pos) + 1
                    titles.append({'line': line, 'title': title, 'english_words': words,
                                   'chinese_characters': chinese, 'issues': issues})
                    errors.extend(f'line {line}: {issue}' for issue in issues)
                else:
                    for argument in arguments:
                        if isinstance(argument, LatexGroupNode):
                            walk(argument.nodelist, environment)
    walk(nodes)
    return {'profile': 'praxis-short-figure-title-v1', 'titles': titles, 'errors': errors,
            'scope': 'Literal figure title shape only; semantics and final PDF need actual review'}


def review_captions(text):
    """Locate literal long captions for human review, never a quality gate.

    Counts cannot determine rendered lines, necessity or semantic correctness.
    Macro-produced captions are outside this static reading aid.
    """
    text = re.sub(r'(?<!\\)%[^\n]*', lambda m: ' ' * len(m.group()), text)
    captions = []
    pattern = r'\\caption(?:of\s*\{(figure|table)\})?\*?\s*(?:\[[^\]]*\]\s*)?\{'
    for match in re.finditer(pattern, text):
        start = pos = match.end()
        depth = 1
        while pos < len(text) and depth:
            if text[pos] == '\\':
                pos += 2
                continue
            depth += (text[pos] == '{') - (text[pos] == '}')
            pos += 1
        if depth:
            continue  # Compilation handles malformed TeX; do not invent content.
        body = text[start:pos-1]
        words = len(re.findall(r'[A-Za-z]+(?:[-\u2019\x27][A-Za-z]+)*', body))
        chinese = len(re.findall(r'[\u3400-\u9fff]', body))
        captions.append({'line': text.count('\n', 0, match.start()) + 1,
                         'kind': match.group(1) or 'caption', 'text': body,
                         'english_words': words, 'chinese_characters': chinese,
                         'review_length': words > 40 or chinese > 80})
    return {'scope': 'literal TeX captions; no rendered-line or semantic judgment',
            'captions': captions,
            'review_candidates': sum(c['review_length'] for c in captions)}


def inspect_typesetting_log(log_file, *, pdf=None):
    """Inspect the retained TeX log; timestamps are freshness evidence, not provenance.

    Current receipts bind its bytes. Older current receipts can still be closed
    with the actual adjacent completed log, whose hash is saved by freezing.
    """
    log_file = Path(log_file)
    if not log_file.is_file():
        raise ValueError('Current MCM requires the retained co-located typesetting log')
    raw = log_file.read_bytes()
    text = raw.decode('utf-8', errors='replace')
    if not raw or not re.search(r'^Output written on .+\.(?:pdf|xdv)\b', text, flags=re.M):
        raise ValueError('Current MCM typesetting log is empty or incomplete')
    log_mtime = log_file.stat().st_mtime_ns
    pdf_mtime = Path(pdf).stat().st_mtime_ns if pdf is not None else None
    # Tectonic may flush its log before serializing the PDF; mtime order is
    # recorded for diagnosis only. The canonical receipt binds log bytes.
    overfull = re.findall(r'^Overfull \\(?:hbox|vbox) \([^\n]*', text, flags=re.M)
    oversized = re.findall(r'^LaTeX Warning: Float too large for page[^\n]*', text, flags=re.M)
    result = {'overfull_boxes': overfull, 'oversized_floats': oversized,
              'log_name': log_file.name, 'log_sha256': hashlib.sha256(raw).hexdigest(),
              'log_mtime_ns': log_mtime, 'pdf_mtime_ns': pdf_mtime, 'passed': not (overfull or oversized)}
    if not result['passed']:
        raise ValueError('Current MCM candidate has unresolved typesetting overflow: '
                         + '; '.join(overfull + oversized))
    return result


def compiler_dependencies(rules_path, source, *, output_directory=None):
    """Read Tectonic's opened-local-file list, preserving spaces in filenames.

    Tectonic 0.17 writes one dependency per physical line and does not make-
    escape internal spaces. This deliberately is not a generic Make parser or
    a guess from literal TeX commands; macro-resolved inputs are included.
    The 0.17 driver prefixes relative filesystem names with its output path,
    although they were read from the input directory. Remove that documented
    writer prefix before resolving; never pick whichever file happens to exist.
    Bundle resources are covered separately by the pinned runtime profile.
    """
    source, rules_path = Path(source).resolve(), Path(rules_path)
    lines = rules_path.read_text(encoding='utf-8').splitlines()
    if not lines or ' : ' not in lines[0]:
        raise ValueError('Missing or unsupported compiler dependency record')
    first = lines[0].split(' : ', 1)[1]
    names = [first] + [line[2:] if line.startswith('  ') else '' for line in lines[1:]]
    dependencies = {}
    for index, name in enumerate(names):
        name = name.removesuffix(' \\')
        if not name or '\x00' in name:
            raise ValueError('Invalid compiler dependency record')
        path = Path(name)
        if index and output_directory is not None and path.is_absolute():
            try:
                relative = path.relative_to(Path(output_directory).absolute())
            except ValueError:
                pass  # An explicitly absolute import retains its actual path.
            else:
                path = source.parent/relative
        if not path.is_absolute():
            path = source.parent/path
        path = path.resolve()
        if not path.is_file():
            raise ValueError('Compiler dependency is missing: ' + str(path))
        # Relative identities survive moving a complete document resource tree.
        import os
        key = Path(os.path.relpath(path, source.parent)).as_posix()
        if key in dependencies:
            raise ValueError('Duplicate compiler dependency: ' + key)
        dependencies[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    if dependencies.get(source.name) != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError('Compiler dependency record does not include the current source')
    return {'schema_version': 1, 'method': 'tectonic-0.17-opened-local-files',
            'files': dependencies,
            'scope': 'Local files actually opened by the compiler; pinned bundle resources are bound separately. Two builds verify the observed file set and bytes remain stable.'}


def verify_compiler_dependencies(record, source):
    """Reject missing/changed resources without replacing an old receipt."""
    if (not isinstance(record, dict) or record.get('schema_version') != 1
            or record.get('method') != 'tectonic-0.17-opened-local-files'
            or not isinstance(record.get('files'), dict) or not record['files']):
        raise ValueError('Current delivery requires compiler-opened dependency bindings; rebuild the candidate')
    source = Path(source).resolve()
    files = record['files']
    if files.get(source.name) != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError('Compiler dependencies do not bind the current source')
    for name, digest in files.items():
        if (not isinstance(name, str) or not name or Path(name).is_absolute()
                or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
            raise ValueError('Invalid compiler dependency identity')
        path = source.parent/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Compiler dependency changed or was deleted: ' + name)
    return {'passed': True, 'files': dict(files), 'method': record['method']}


def compile_paper(tex, contest, output, compiler=None, *, layout_mode='current'):
    """Canonical compiler + bundle; a receipt binds this actual source and PDF."""
    import json
    import shutil
    import subprocess
    import tempfile
    tex, output = Path(tex).resolve(), Path(output).resolve()
    source = tex.read_bytes()
    check_explicit_references(source.decode('utf-8'))
    if layout_mode not in {'current', 'archive'}:
        raise ValueError('Layout mode must be current or archive')
    text = source.decode('utf-8')
    layout = check(text, contest, layout_mode=layout_mode) if contest else None
    runtime = json.loads((ROOT / 'templates/typesetting-runtime.json').read_text(encoding='utf-8'))
    executable = compiler or shutil.which('tectonic') or str(Path.home()/'.local/bin/tectonic')
    version = subprocess.run([str(executable), '--version'], check=True, capture_output=True, text=True).stdout.strip()
    if version != runtime['compiler']:
        raise ValueError('Canonical output requires ' + runtime['compiler'] + '; found ' + version)
    if output.exists():
        raise FileExistsError(output)
    # Bundle inspection must use this profile, not a surrounding Tectonic.toml.
    session = output.parent / '.session'; session.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='typesetting-', dir=session) as directory:
        probe = Path(directory)
        (probe/'Tectonic.toml').write_text('[doc]\nname = "praxis-probe"\nbundle = ' + json.dumps(runtime['bundle_url']) + '\n[[output]]\nname = "default"\ntype = "pdf"\n', encoding='utf-8')
        def bundle_file(name):
            return subprocess.run([str(executable), '-X', 'bundle', 'cat', name], cwd=probe, check=True, capture_output=True).stdout
        if bundle_file('SHA256SUM').decode().strip() != runtime['bundle_sha256']:
            raise ValueError('TeX resource bundle differs from the pinned profile')
        if contest == 'cumcm':
            fonts = json.loads((ROOT/'templates/cumcm-fonts.json').read_text(encoding='utf-8'))
            for name, record in fonts['files'].items():
                if hashlib.sha256(bundle_file(name)).hexdigest() != record['sha256']:
                    raise ValueError('Font differs from the pinned profile: ' + name)
    output.mkdir(parents=True)
    rules = output/(tex.stem+'.dependencies.mk')
    command = [str(executable), '--bundle', runtime['bundle_url'], '--keep-logs',
               '--makefile-rules', str(rules), '--outdir', str(output), str(tex)]
    transcripts = []
    # First discover actual opened local resources, including macro-resolved
    # imports. The second build is the accepted candidate, with observed bytes
    # captured before and compared after; a changed file set is refused too.
    dependencies = None
    for phase in ('dependency discovery', 'bound candidate'):
        if dependencies is not None:
            verify_compiler_dependencies(dependencies, tex)
        run = subprocess.run(command, cwd=tex.parent, capture_output=True, text=True,
                             encoding='utf-8', errors='replace')
        transcripts.append('=== ' + phase + ' ===\n' + run.stdout + run.stderr)
        (output/(tex.stem+'.compile.txt')).write_text('\n'.join(transcripts), encoding='utf-8')
        if run.returncode:
            raise RuntimeError(run.stdout+run.stderr)
        observed = compiler_dependencies(rules, tex, output_directory=output)
        if dependencies is not None and observed['files'] != dependencies['files']:
            raise ValueError('Compiler dependencies changed during compilation; rebuild the candidate')
        dependencies = observed
    diagnostics = None
    if contest == 'mcm' and layout_mode == 'current':
        log_file = output/(tex.stem+'.log')
        diagnostics = inspect_typesetting_log(log_file, pdf=output/(tex.stem+'.pdf'))
    if tex.read_bytes() != source:
        raise ValueError('TeX source changed during compilation')
    pdf = output/(tex.stem+'.pdf')
    final_format = None
    if contest == 'mcm' and layout_mode == 'current':
        from scripts.check_pdf import inspect_mcm_delivery_format
        final_format = inspect_mcm_delivery_format(pdf, mcm_identity(text),
                                                  ai_report_expected=mcm_ai_report_expected(text))
        if not final_format['passed']:
            raise ValueError('Current MCM PDF format failed: ' + '; '.join(final_format['errors']))
    receipt = {'runtime': runtime, 'layout': layout, 'source_name': tex.name,
               'layout_mode': layout_mode,
               'tex_sha256': hashlib.sha256(source).hexdigest(),
               'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
               'compiler_dependencies': dependencies,
               'visual_review_required': True}
    if final_format is not None:
        receipt['current_mcm_format'] = final_format
        receipt['typesetting_diagnostics'] = diagnostics
    (output/(tex.stem+'.build.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


def compile_in_place(tex, contest, compiler=None, *, layout_mode='current'):
    """Used by generators that already replace their own generated artifacts."""
    import shutil
    import tempfile
    session = Path(tex).parent/'.session'; session.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='paper-build-', dir=session) as directory:
        output = Path(directory)/'compiled'
        receipt = compile_paper(tex, contest, output, compiler, layout_mode=layout_mode)
        for suffix in ('.pdf', '.build.json', '.compile.txt', '.log', '.dependencies.mk'):
            path = output/(Path(tex).stem+suffix)
            if path.exists():
                shutil.copyfile(path, Path(tex).with_suffix(suffix))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tex', type=Path, help='Standalone TeX generated with a shared style')
    parser.add_argument('--contest', choices=list(VERSIONS), default='mcm')
    parser.add_argument('--compile', action='store_true', help='Compile with the pinned canonical runtime')
    parser.add_argument('--output-directory', type=Path, help='New output directory for canonical build artifacts')
    parser.add_argument('--compiler', help='Path to Tectonic 0.17.0')
    parser.add_argument('--layout-mode', choices=['current', 'archive'], default='current',
                        help='Current delivery by default; archive explicitly reproduces a retained historical style')
    reviews = parser.add_mutually_exclusive_group()
    reviews.add_argument('--review-captions', action='store_true',
                         help='List literal captions and advisory length candidates; not a quality certification')
    reviews.add_argument('--review-structure', action='store_true',
                         help='Inspect literal heading hierarchy and require reasons for sole numbered children')
    parser.add_argument('--structure-review', type=Path,
                        help='Exact-source-bound JSON reasons, used with --review-structure')
    args = parser.parse_args()
    if args.structure_review is not None and not args.review_structure:
        parser.error('--structure-review requires --review-structure')
    if args.compile and (args.review_structure or args.review_captions):
        parser.error('Compile and review are separate actions; review the resulting source before freezing')
    try:
        if args.compile:
            if args.output_directory is None:
                parser.error('--compile requires --output-directory')
            import json
            print(json.dumps(compile_paper(args.tex, args.contest, args.output_directory, args.compiler,
                                          layout_mode=args.layout_mode), indent=2))
            return
        result = check(args.tex.read_text(encoding='utf-8'), args.contest, layout_mode=args.layout_mode)
    except ValueError as exc:
        parser.exit(1, str(exc) + '\n')
    if args.review_structure:
        import json
        from scripts.paper_structure import inspect_structure
        structure = inspect_structure(args.tex.read_bytes().decode('utf-8'), args.structure_review)
        print(json.dumps(structure, ensure_ascii=False, indent=2))
        if not structure['passed']:
            parser.exit(1)
    elif args.review_captions:
        import json
        print(json.dumps(review_captions(args.tex.read_text(encoding='utf-8')), ensure_ascii=False, indent=2))
    else:
        print(f"PASS {result['profile']} {result['style_sha256']}")


if __name__ == '__main__':
    main()
