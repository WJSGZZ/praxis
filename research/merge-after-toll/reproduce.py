"""Reproduce this frozen research study without replacing its archived files."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def compare(actual,expected,path=''):
    if isinstance(expected,dict):
        assert set(actual)==set(expected),f'{path}: fields differ'
        for key,value in expected.items():
            if key not in {'compute_seconds','computed_utc'}:compare(actual[key],value,path+'/'+key)
    elif isinstance(expected,list):
        assert len(actual)==len(expected),f'{path}: length differs'
        for i,(a,b) in enumerate(zip(actual,expected)):compare(a,b,f'{path}/{i}')
    elif isinstance(expected,(int,float)) and not isinstance(expected,bool):
        assert math.isclose(actual,expected,rel_tol=1e-8,abs_tol=1e-6),f'{path}: {actual} != {expected}'
    else: assert actual==expected,f'{path}: {actual!r} != {expected!r}'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidate',action='store_true');parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args()
    if args.candidate and args.baseline:parser.error('Choose one phase')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    phase='baseline' if args.baseline else 'rejected-routing' if args.candidate else 'accepted'
    code=HERE/'baseline/code' if args.baseline else HERE/'code'
    command=[sys.executable,str(code/('balanced.py' if args.candidate else 'model.py')),'--output',str(out)]
    if args.baseline:command+=['--phase','baseline']
    subprocess.run(command,check=True,stdout=(out/'model.stdout.log').open('w'),stderr=(out/'model.stderr.log').open('w'))
    subprocess.run([sys.executable,str(code/'validate.py'),'--results',str(out/'results.json'),'--output',str(out/'checks.json')],check=True)
    actual=json.loads((out/'results.json').read_text());expected=json.loads((HERE/f'reference/{phase}.json').read_text())
    compare(actual,expected)
    if not args.baseline:
        subprocess.run([sys.executable,str(HERE/'audit.py'),'--results',str(out/'results.json'),'--code-dir',str(code),'--output',str(out/'independent-checks.json')],check=True)
    # Source integrity is separate from numerical equivalence and never edits reference outputs.
    manifest=json.loads((HERE/'manifest.json').read_text())
    changed=[name for name,sha in manifest['files_sha256'].items() if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=sha]
    assert not changed,f'Frozen archive changed: {changed}'
    (out/'reproduction.json').write_text(json.dumps(dict(phase=phase,numerical_match=True,reference_unchanged=True,scope='Local development reproduction; not field calibration or blind assessment'),indent=2))
    print('PASS: checks, frozen numerical reference, and archive hashes')


if __name__=='__main__':main()
