import importlib.util
import json
from pathlib import Path
import pytest

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('skill_pipeline', PROJECT / 'scripts/pipeline.py')
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def make_case(tmp_path):
    problem = tmp_path / 'problem.md'
    data = tmp_path / 'measurements.csv'
    problem.write_text('Synthetic check: extrapolate y=1+2*x at x=4.')
    data.write_text('x,y\n0,1\n1,3\n2,5\n3,7\n')
    result = pipeline.init_case(tmp_path / 'cases','training',problem,[data])
    case = Path(result['case'])
    (case / 'code/model.py').write_text('''import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
d=pd.read_csv('raw/data/measurements.csv')
slope,intercept=np.polyfit(d.x,d.y,1)
(a.output/'results.json').write_text(json.dumps({'prediction':float(slope*4+intercept)}))
''')
    (case / 'code/validate.py').write_text('''import argparse,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--results',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
r=json.loads(a.results.read_text());expected=1+2*4
ok=math.isclose(r['prediction'],expected)
a.output.write_text(json.dumps([{'name':'independent arithmetic','passed':ok,'evidence':f"1+2*4={expected}; fitted prediction={r['prediction']}"}]))
raise SystemExit(0 if ok else 1)
''')
    return case, problem, data


def test_intake_preserves_originals_and_audits_all_excel_sheets(tmp_path):
    import pandas as pd
    problem = tmp_path / 'problem.txt'; problem.write_text('Synthetic audit')
    data = tmp_path / 'data.xlsx'
    with pd.ExcelWriter(data) as writer:
        pd.DataFrame({'x':[1,2]}).to_excel(writer,sheet_name='first',index=False)
        pd.DataFrame({'x':[3,None,5]}).to_excel(writer,sheet_name='second',index=False)
    before = data.read_bytes()
    case=Path(pipeline.init_case(tmp_path/'cases','audit',problem,[data])['case'])
    report=json.loads((case/'audits/data.xlsx.json').read_text())
    assert set(report['sheets']) == {'first','second'}
    assert report['sheets']['second']['missing']['x'] == 1
    assert data.read_bytes() == before == (case/'raw/data/data.xlsx').read_bytes()
    assert (case/'raw/data/data.xlsx').stat().st_mode & 0o222 == 0
    with pytest.raises(FileExistsError):
        pipeline.init_case(tmp_path/'cases','audit',problem,[data])


def test_run_records_independent_evidence_and_detects_stale_outputs(tmp_path):
    case,problem,data=make_case(tmp_path)
    receipt=pipeline.run_case(case)
    assert receipt['status'] == 'automatic-checks-passed'
    assert len(receipt['steps']) == 2
    assert receipt['human_verification'].startswith('not recorded')
    assert pipeline.status(case)['runs'][0]['usable_automatic_evidence']
    run=Path(receipt['run'])
    (run/'output/results.json').write_text('{"prediction": 999}')
    report=pipeline.status(case)
    assert not report['runs'][0]['usable_automatic_evidence']
    assert 'output/results.json' in report['runs'][0]['stale']


def test_changed_code_and_added_configuration_invalidate_evidence(tmp_path):
    case,_,_=make_case(tmp_path)
    pipeline.run_case(case)
    (case/'code/parameters.json').write_text('{"new_assumption":true}')
    assert not pipeline.status(case)['runs'][0]['usable_automatic_evidence']
    pipeline.run_case(case)
    (case/'code/model.py').write_text((case/'code/model.py').read_text()+'\n# changed source\n')
    assert all(not r['usable_automatic_evidence'] for r in pipeline.status(case)['runs'])


def test_failed_check_never_certifies_model(tmp_path):
    case,_,_=make_case(tmp_path)
    (case/'code/validate.py').write_text('''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--results');p.add_argument('--output',type=Path);a=p.parse_args()
a.output.write_text(json.dumps([{'name':'bad numerical result','passed':False,'evidence':'deliberate rejection'}]))
''')
    result=pipeline.run_case(case)
    assert result['status'] == 'failed'
    assert not result['automatic_checks_passed']
    assert not pipeline.status(case)['runs'][0]['usable_automatic_evidence']
    assert (Path(result['run'])/'validation.stdout.log').exists()


def test_input_mutation_blocks_execution(tmp_path):
    case,_,_=make_case(tmp_path)
    raw=case/'raw/data/measurements.csv';raw.chmod(0o644);raw.write_text('x,y\n0,999\n')
    with pytest.raises(ValueError,match='raw inputs changed'):
        pipeline.run_case(case)
    assert pipeline.status(case)['raw_input_changes'] == ['raw/data/measurements.csv']


def test_unreviewed_code_path_is_rejected(tmp_path):
    case,_,_=make_case(tmp_path)
    outside=tmp_path/'outside.py';outside.write_text('raise Exception("must not run")')
    with pytest.raises(ValueError,match='reviewed'):
        pipeline.run_case(case,model=str(outside))


def test_timeout_retains_failure_log_and_does_not_validate(tmp_path):
    case,_,_=make_case(tmp_path)
    (case/'code/model.py').write_text('import time; time.sleep(3)')
    result=pipeline.run_case(case,timeout=1)
    assert result['status']=='failed'
    assert 'TimeoutExpired' in result['error']
    assert len(result['steps'])==1
    assert (Path(result['run'])/'receipt.json').exists()


def test_nonfinite_results_cannot_be_certified(tmp_path):
    case,_,_=make_case(tmp_path)
    (case/'code/model.py').write_text('''import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
(a.output/'results.json').write_text('{"metric": NaN}')
''')
    result=pipeline.run_case(case)
    assert result['status']=='failed'
    assert 'Non-finite' in result['error']
    assert len(result['steps'])==1


def test_cli_uses_external_workspace_not_skill_install_directory(tmp_path):
    import subprocess
    import sys
    workspace = tmp_path / 'other-project'
    workspace.mkdir()
    problem = workspace / 'problem.txt'
    problem.write_text('Synthetic portability check')
    result = subprocess.run([sys.executable, str(PROJECT/'scripts/pipeline.py'),
                             '--workspace',str(workspace),'init','--name','portable',
                             '--problem',str(problem)], cwd=PROJECT,
                            capture_output=True,text=True,check=True)
    case = Path(json.loads(result.stdout)['case'])
    assert case == workspace/'cases/portable'
    assert (case/'planning/tasks.md').is_file()
    assert not (PROJECT/'cases/portable').exists()


def test_external_workspace_runs_and_detects_stale_evidence(tmp_path, monkeypatch):
    workspace = tmp_path / 'other-project'
    workspace.mkdir()
    monkeypatch.setattr(pipeline,'PROJECT',workspace)
    case,_,_=make_case(workspace)
    result=pipeline.run_case(case)
    assert result['automatic_checks_passed']
    assert pipeline.status(case)['runs'][0]['usable_automatic_evidence']
    assert 'scripts/pipeline.py' in result['dependencies']
    (case/'code/model.py').write_text('# changed')
    assert not pipeline.status(case)['runs'][0]['usable_automatic_evidence']


def test_environment_snapshot_covers_every_declared_dependency():
    import re
    import tomllib
    from scripts import pipeline
    declared = tomllib.loads((Path(pipeline.BUNDLE) / 'pyproject.toml').read_text())['project']['dependencies']
    names = {re.split(r'[<>=!~\[ ]', spec, maxsplit=1)[0] for spec in declared}
    assert names <= set(pipeline.environment_snapshot()['packages'])


def test_relative_case_path_is_read_from_the_workspace(tmp_path, monkeypatch):
    from scripts import pipeline
    workspace = tmp_path / 'ws'
    (workspace / 'cases/demo').mkdir(parents=True)
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    monkeypatch.setattr(pipeline, 'PROJECT', workspace.resolve())
    monkeypatch.chdir(elsewhere)
    assert pipeline.under_project(Path('cases/demo')) == (workspace / 'cases/demo').resolve()
