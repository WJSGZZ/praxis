"""Single-source MCM layout, embedded into standalone TeX with a drift check.

House style is not a certification of any contest edition's submission rules.
"""
import argparse
import hashlib
from pathlib import Path
import re

from scripts import texplot

ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / 'templates/mcm-style.tex'
VERSIONS = {'mcm': 1, 'cumcm': 2}
BEGIN = '% BEGIN PRAXIS MCM STYLE v1\n'
END = '% END PRAXIS MCM STYLE\n'


def style_block(contest='mcm'):
    if contest not in {'mcm', 'cumcm'}:
        raise ValueError('Unknown layout profile')
    name = contest.upper()
    source = ROOT / f'templates/{contest}-style.tex'
    return (f'% BEGIN PRAXIS {name} STYLE v{VERSIONS[contest]}\n' +
            source.read_text().replace('@@PLOTS@@', texplot.PREAMBLE) +
            f'% END PRAXIS {name} STYLE\n')


def escape(text):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%',
                    '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{',
                    '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(c, c) for c in text)


def preamble(team, title, contest='mcm'):
    if contest == 'mcm' and not re.fullmatch(r'[0-9]{1,12}', team):
        raise ValueError('Team number must contain digits only; use the assigned number for a real entry')
    return ((r'\newcommand{\PraxisTeam}{' + team + '}\n' if contest == 'mcm' else '') +
            r'\newcommand{\PraxisTitle}{' + escape(title) + '}\n' +
            style_block(contest) + r'\begin{document}' + '\n')


def summary_header(problem):
    if problem not in 'ABCDEF' or len(problem) != 1:
        raise ValueError('Choose an MCM/ICM problem letter A–F')
    return (r'\thispagestyle{fancy}\begin{center}\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}ccc}' + '\n' +
            r'\textbf{Problem Chosen}&\textbf{MCM/ICM}&\textbf{Team Control Number}\\' + '\n' +
            r'{\Large\textbf{' + problem + r'}}&\textbf{Summary Sheet}&{\Large\textbf{\PraxisTeam}}\end{tabular*}\end{center}\vspace{-4pt}\hrule\vspace{10pt}' + '\n')


def check(text, contest='mcm'):
    """Reject missing/modified styles and direct layout overrides, not scientific content."""
    block = style_block(contest)
    begin = f'% BEGIN PRAXIS {contest.upper()} STYLE v{VERSIONS[contest]}\n'
    end = f'% END PRAXIS {contest.upper()} STYLE\n'
    if text.count(begin) != 1 or text.count(end) != 1 or block not in text:
        raise ValueError('Paper layout differs from the shared source; regenerate with scripts.paper_template')
    rest = text.replace(block, '')
    rest = re.sub(r'(?<!\\)%[^\n]*', '', rest)
    # Hanging references locally disable paragraph indentation; this does not
    # replace the document paragraph style.
    rest = re.sub(r'(\\begingroup\\small(?:\\sloppy)?(?:\\raggedright)?)\\setlength\{\\parindent\}\{0pt\}', r'\1', rest)
    # Covers the ways the two generators originally drifted. Local table widths,
    # mathematical environments and bibliographic formatting remain content choices.
    prohibited = (r'\\(?:documentclass|geometry|newgeometry|restoregeometry|linespread|'
                  r'pagestyle|fancyhf|fancyhead|fancyfoot|captionsetup|titleformat|titlespacing|titlecontents|ctexset|setCJKmainfont|setmainfont|setsansfont|setmonofont|setCJKsansfont|setCJKmonofont|fontfamily|fontencoding)\b|'
                  r'\\(?:setcounter|addtocounter)\s*\{tocdepth\}|'
                  r'\\(?:renewcommand|def)\s*\{?\\(?:normalsize|familydefault|rmdefault|sfdefault|baselinestretch)\b|'
                  r'\\thispagestyle\s*\{(?:empty|plain)\}|'
                  r'\\setlength\s*\{\\(?:parindent|parskip|textwidth|textheight|headheight|oddsidemargin)\}|'
                  r'\\usepackage(?:\[[^\]]*\])?\{[^}]*\b(?:geometry|fontspec|newtxtext|newtxmath|times|mathptmx)[^}]*\}')
    if re.search(prohibited, rest):
        raise ValueError('Direct layout override outside the shared style')
    if contest == 'mcm' and (r'\thispagestyle{fancy}' not in rest or 'Summary Sheet' not in rest):
        raise ValueError('Missing shared summary-page header')
    if contest == 'cumcm' and r'\tableofcontents' in rest:
        raise ValueError('CUMCM papers must not have a table of contents')
    return {'profile': f'praxis-{contest}-v{VERSIONS[contest]}', 'style_sha256': hashlib.sha256(block.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tex', type=Path, help='Standalone TeX generated with the MCM style')
    parser.add_argument('--contest', choices=['mcm', 'cumcm'], default='mcm')
    args = parser.parse_args()
    try:
        result = check(args.tex.read_text(), args.contest)
    except ValueError as exc:
        parser.exit(1, str(exc) + '\n')
    print(f"PASS {result['profile']} {result['style_sha256']}")


if __name__ == '__main__':
    main()
