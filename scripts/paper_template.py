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
            source.read_text(encoding='utf-8').replace('@@PLOTS@@', texplot.PREAMBLE) +
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


def compile_paper(tex, contest, output, compiler=None):
    """Canonical compiler + bundle; a receipt binds this actual source and PDF."""
    import json
    import shutil
    import subprocess
    import tempfile
    tex, output = Path(tex).resolve(), Path(output).resolve()
    source = tex.read_bytes()
    layout = check(tex.read_text(encoding='utf-8'), contest) if contest else None
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
    run = subprocess.run([str(executable), '--bundle', runtime['bundle_url'], '--keep-logs', '--outdir', str(output), str(tex)], cwd=tex.parent, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (output/(tex.stem+'.compile.txt')).write_text(run.stdout+run.stderr, encoding='utf-8')
    if run.returncode:
        raise RuntimeError(run.stdout+run.stderr)
    if tex.read_bytes() != source:
        raise ValueError('TeX source changed during compilation')
    pdf = output/(tex.stem+'.pdf')
    receipt = {'runtime': runtime, 'layout': layout, 'source_name': tex.name,
               'tex_sha256': hashlib.sha256(source).hexdigest(),
               'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
               'visual_review_required': True}
    (output/(tex.stem+'.build.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


def compile_in_place(tex, contest, compiler=None):
    """Used by generators that already replace their own generated artifacts."""
    import shutil
    import tempfile
    session = Path(tex).parent/'.session'; session.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='paper-build-', dir=session) as directory:
        output = Path(directory)/'compiled'
        receipt = compile_paper(tex, contest, output, compiler)
        for suffix in ('.pdf', '.build.json', '.compile.txt', '.log'):
            path = output/(Path(tex).stem+suffix)
            if path.exists():
                shutil.copyfile(path, Path(tex).with_suffix(suffix))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tex', type=Path, help='Standalone TeX generated with the MCM style')
    parser.add_argument('--contest', choices=['mcm', 'cumcm'], default='mcm')
    parser.add_argument('--compile', action='store_true', help='Compile with the pinned canonical runtime')
    parser.add_argument('--output-directory', type=Path, help='New output directory for canonical build artifacts')
    parser.add_argument('--compiler', help='Path to Tectonic 0.17.0')
    args = parser.parse_args()
    try:
        if args.compile:
            if args.output_directory is None:
                parser.error('--compile requires --output-directory')
            import json
            print(json.dumps(compile_paper(args.tex, args.contest, args.output_directory, args.compiler), indent=2))
            return
        result = check(args.tex.read_text(encoding='utf-8'), args.contest)
    except ValueError as exc:
        parser.exit(1, str(exc) + '\n')
    print(f"PASS {result['profile']} {result['style_sha256']}")


if __name__ == '__main__':
    main()
