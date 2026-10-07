"""Run the anonymous support package from a clean work directory."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='model-demo-') as temp:
    work=Path(temp);(work/'raw/data').mkdir(parents=True)
    for path in (root/'data').glob('*.csv'):
        shutil.copyfile(path,work/'raw/data'/path.name)
    out=work/'output';out.mkdir()
    subprocess.run([sys.executable,str(root/'code/model.py'),'--output',str(out)],cwd=work,check=True)
    subprocess.run([sys.executable,str(root/'code/validate.py'),'--results',str(out/'results.json'),
                    '--output',str(work/'checks.json')],cwd=work,check=True)
    actual=json.loads((out/'results.json').read_text())
    expected=json.loads((root/'reference/results.json').read_text())
    for group in ['four','fifteen']:
        for a,b in zip(actual['groups'][group]['selected'],expected['groups'][group]['selected']):
            assert abs(a['net_return']-b['net_return'])<1e-7
    target=root/'reproduced'
    if target.exists():raise FileExistsError('Refusing to replace reproduced/')
    shutil.copytree(out,target);shutil.copyfile(work/'checks.json',target/'checks.json')
    print('Independent checks passed; selected report results reproduced within 1e-7.')
