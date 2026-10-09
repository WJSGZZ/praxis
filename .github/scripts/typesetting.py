"""Clean-runner checks of both house styles and the complete Chinese submission."""
import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import tarfile
from urllib.request import urlopen
import zipfile

from scripts.check_pdf import inspect_pdf
from scripts.contest_rules import evaluate, extract
from scripts.paper_template import check

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


def main(compiler=None):
    OUT.mkdir(parents=True, exist_ok=False)
    executable = Path(compiler).resolve() if compiler else install()
    version = subprocess.run([str(executable), "--version"], check=True, capture_output=True, text=True).stdout.strip()
    if version != "Tectonic 0.17.0": raise ValueError("Unexpected compiler version: " + version)
    fonts = json.loads((ROOT / 'templates/cumcm-fonts.json').read_text())
    for name, record in fonts['files'].items():
        data = subprocess.run([str(executable), '-X', 'bundle', 'cat', name], check=True, capture_output=True).stdout
        if hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError('TeX bundle font differs from pinned profile: ' + name)
    for contest in ('cumcm', 'mcm'):
        shutil.copyfile(ROOT / f'templates/{contest}-paper.tex', OUT / f'{contest}-template.tex')
    with zipfile.ZipFile(ROOT / 'demos/cumcm-1998-a/deliverables/supporting_materials.zip') as archive:
        for name in ('main', 'ai-use'):
            (OUT / f'{name}.tex').write_bytes(archive.read(f'paper/{name}.tex'))
    checks = {}
    for name, contest in [('cumcm-template', 'cumcm'), ('mcm-template', 'mcm'), ('main', 'cumcm'), ('ai-use', None)]:
        tex = OUT / f'{name}.tex'
        if contest: check(tex.read_text(encoding='utf-8'), contest)
        run = subprocess.run([str(executable), '--keep-logs', str(tex)], cwd=OUT, capture_output=True, text=True, encoding='utf-8', errors='replace')
        (OUT / f'{name}.compile.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        if run.returncode: raise RuntimeError(run.stdout + run.stderr)
        pdf = OUT / f'{name}.pdf'
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
        checks[name] = report
    (OUT / 'verification.json').write_text(json.dumps({'platform': platform.platform(), 'compiler': 'Tectonic 0.17.0', 'checks': checks}, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', help='Use an existing Tectonic 0.17.0 executable')
    main(parser.parse_args().compiler)
