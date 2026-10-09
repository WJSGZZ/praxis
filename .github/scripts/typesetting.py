"""Clean-runner checks of both house styles and the complete Chinese submission."""
import hashlib
import json
import platform
import os
import sys
from pathlib import Path
import shutil
import subprocess
import tarfile
from urllib.request import urlopen
import zipfile

from scripts.check_pdf import inspect_pdf
from scripts.contest_rules import evaluate, extract
from scripts.paper_template import check, compile_paper
from scripts.freeze_pdf import freeze

ROOT = Path.cwd()
OUT = ROOT / '.session/typesetting'
ASSETS = {
    ('Linux', 'x86_64'): ('x86_64-unknown-linux-gnu.tar.gz', '1a715688baf591e650c8aeb160ae934e181685eecbb38b317de30b269ac5d606'),
    ('Windows', 'AMD64'): ('x86_64-pc-windows-msvc.zip', 'f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f'),
    ('Darwin', 'arm64'): ('aarch64-apple-darwin.tar.gz', 'a3f1cac7c5678f01661a92212f58480ae3b0634115d880dbc59e2953ded45667'),
    ('Darwin', 'x86_64'): ('x86_64-apple-darwin.tar.gz', '7c90ef5b6ddb1eb1937e4337add5237b79338e4b9676459fa91187d24d6cdf80'),
}


def install():
    suffix, expected = ASSETS[(platform.system(), platform.machine())]
    name = 'tectonic-0.17.0-' + suffix
    url = 'https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.17.0/' + name
    data = urlopen(url, timeout=120).read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Official Tectonic archive hash differs')
    archive = OUT / name
    archive.write_bytes(data)
    executable = 'tectonic.exe' if platform.system() == 'Windows' else 'tectonic'
    target = OUT / executable
    # Extract only the executable, never arbitrary paths from an archive.
    if name.endswith('.zip'):
        with zipfile.ZipFile(archive) as z:
            members = [p for p in z.namelist() if Path(p).name == executable]
            if len(members) != 1: raise ValueError('Unexpected archive executable')
            target.write_bytes(z.read(members[0]))
    else:
        with tarfile.open(archive) as z:
            members = [p for p in z.getmembers() if Path(p.name).name == executable and p.isfile()]
            if len(members) != 1: raise ValueError('Unexpected archive executable')
            target.write_bytes(z.extractfile(members[0]).read())
        target.chmod(0o755)
    return target


def check_mcm_pagination(records):
    """Check the current contest boundary, not a historic demo's total length.

    Cross-platform comparison below still detects layout differences. The AI
    report must be present in these AI-assisted demos and stays outside the
    solution-page limit, whose sole authority is contest_rules.evaluate.
    """
    rules = evaluate(records, 'mcm')
    if rules['errors']:
        raise ValueError(rules['errors'])
    if rules['facts']['ai_report_from_page'] is None:
        raise ValueError('AI-assisted demo is missing its AI-use report')
    return rules


def main(compiler=None):
    OUT.mkdir(parents=True, exist_ok=False)
    executable = Path(compiler).resolve() if compiler else install()
    version = subprocess.run([str(executable), "--version"], check=True, capture_output=True, text=True).stdout.strip()
    if version != "Tectonic 0.17.0": raise ValueError("Unexpected compiler version: " + version)
    for contest in ('cumcm', 'mcm', 'research'):
        shutil.copyfile(ROOT / f'templates/{contest}-paper.tex', OUT / f'{contest}-template.tex')
    with zipfile.ZipFile(ROOT / 'demos/cumcm-1998-a/deliverables/supporting_materials.zip') as archive:
        for name in ('main', 'ai-use'):
            (OUT / f'{name}.tex').write_bytes(archive.read(f'paper/{name}.tex'))
    os.environ['PATH'] = str(executable.parent) + os.pathsep + os.environ.get('PATH', '')
    bath = ROOT/'demos/mcm-2016-a/reproduce'
    generated = subprocess.run([sys.executable, str(bath/'build_report.py'), '--run', str(bath/'reference')], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (OUT/'bath-generator.txt').write_text(generated.stdout+generated.stderr, encoding='utf-8')
    if generated.returncode: raise RuntimeError(generated.stdout+generated.stderr)
    shutil.copyfile(bath/'paper/paper.tex', OUT/'bath.tex')
    shutil.copyfile(ROOT/'research/merge-after-toll/paper/paper.tex', OUT/'toll.tex')
    domino = ROOT/'demos/domino-research/reproduce'
    generated = subprocess.run([sys.executable, str(domino/'build_note.py')], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (OUT/'domino-generator.txt').write_text(generated.stdout+generated.stderr, encoding='utf-8')
    if generated.returncode: raise RuntimeError(generated.stdout+generated.stderr)
    shutil.copyfile(domino/'paper/paper.tex', OUT/'domino.tex')
    shutil.copyfile(ROOT/'demos/collatz-research/reproduce/paper/paper.tex', OUT/'collatz.tex')
    checks = {}
    for name, contest in [('cumcm-template', 'cumcm'), ('mcm-template', 'mcm'), ('main', 'cumcm'), ('ai-use', None), ('bath', 'mcm'), ('toll', 'mcm'), ('research-template', 'research'), ('domino', 'research'), ('collatz', 'research')]:
        tex = OUT / f'{name}.tex'
        if contest: check(tex.read_text(encoding='utf-8'), contest)
        built = OUT/(name+'-build')
        compile_paper(tex, contest, built, executable)
        pdf = built/(name+'.pdf')
        if contest:
            freeze(pdf, built/'frozen.pdf', tex=tex, contest=contest,
                   build_receipt=built/(name+'.build.json'))
        for suffix in ('.pdf', '.compile.txt', '.log', '.build.json'):
            source = built/(name+suffix)
            if source.exists(): shutil.copyfile(source, OUT/(name+suffix))
        report = inspect_pdf(pdf, require_embedded_fonts=True)
        if report['errors']: raise ValueError(report['errors'])
        if name in {'cumcm-template', 'main', 'ai-use'}:
            text = '\n'.join(r['text'] for r in extract(pdf))
            if '参考文献' not in text and name != 'ai-use': raise ValueError('Chinese text extraction failed')
            faces = {f['face'] for f in report['fonts']}
            if not any('FandolSong' in f for f in faces): raise ValueError('Unexpected Chinese face')
            if any('Songti' in f or 'Heiti' in f for f in faces): raise ValueError('Platform font substituted')
        if name == 'main':
            rules = evaluate(extract(pdf), 'cumcm')
            if rules['errors']: raise ValueError(rules['errors'])
            if report['total_pages'] != 23 or rules['facts']['body_pages'] != 12:
                raise ValueError('Unexpected pagination')
            report['contest_rules'] = rules
        if name in {'bath', 'toll'}:
            rules = check_mcm_pagination(extract(pdf))
            report['contest_rules'] = rules
        if contest == 'research':
            if not any('LMRoman' in f['face'] for f in report['fonts']):
                raise ValueError('Research font substituted')
            if name in {'domino', 'collatz'} and report['total_pages'] != (4 if name == 'domino' else 7):
                raise ValueError('Unexpected research pagination')
        checks[name] = report
    (OUT / 'verification.json').write_text(json.dumps({'platform': platform.platform(), 'compiler': 'Tectonic 0.17.0', 'checks': checks}, ensure_ascii=False, indent=2), encoding='utf-8')


def compare_artifacts(directory):
    import re
    import pypdfium2 as pdfium
    folders = sorted(Path(directory).glob('typesetting-*'))
    if len(folders) != 3:
        raise ValueError('Expected actual artifacts from all three operating systems')
    results = {}
    reference = None
    for folder in folders:
        manifest = json.loads((folder / 'verification.json').read_text(encoding='utf-8'))
        fingerprints = {}
        for name in ('main', 'ai-use', 'cumcm-template', 'mcm-template', 'bath', 'toll', 'research-template', 'domino', 'collatz'):
            path = folder / (name + '.pdf')
            if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['checks'][name]['sha256']:
                raise ValueError('Artifact differs from runner verification: ' + str(path))
            pages = []
            with pdfium.PdfDocument(str(path)) as document:
                for page in document:
                    textpage = page.get_textpage()
                    try:
                        text = re.sub(r'\s+', '', textpage.get_text_range())
                        image = page.render(scale=1).to_pil()
                        pages.append({'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                                      'render_sha256_72dpi': hashlib.sha256(image.tobytes()).hexdigest(),
                                      'image_size': list(image.size), 'image_mode': image.mode})
                    finally:
                        textpage.close()
                        page.close()
            fingerprints[name] = pages
        results[folder.name] = {'platform': manifest['platform'], 'pages': fingerprints}
        if reference is None:
            reference = fingerprints
        elif fingerprints != reference:
            raise ValueError('Text or rendered layout differs across platforms: ' + folder.name)
    output = Path(directory) / 'cross-platform-verification.json'
    output.write_text(json.dumps({'all_three_match': True, 'scope': 'Page text (whitespace normalized) and PDFium rasters at 72 dpi; not mathematical or host-installation certification', 'results': results}, indent=2), encoding='utf-8')
    print('PASS: three-platform text and page rasters agree')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', help='Use an existing Tectonic 0.17.0 executable')
    parser.add_argument('--compare', type=Path, help='Compare artifacts from the three actual CI jobs')
    args = parser.parse_args()
    if args.compare:
        compare_artifacts(args.compare)
    else:
        main(args.compiler)
