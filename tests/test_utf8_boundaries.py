"""UTF-8 project formats must not depend on the host's legacy default codec."""
import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

from modeling import routes
from scripts import pipeline, workflow

SOURCE = Path(__file__).resolve().parents[1]


@pytest.fixture
def cp1252_default(monkeypatch):
    """Actual file bytes/text under a Windows-style locale default, not a mock result."""
    original = Path.open
    def legacy_open(path, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        if 'b' not in mode and encoding in (None, 'locale'):
            encoding = 'cp1252'
        return original(path, mode, buffering, encoding, errors, newline)
    monkeypatch.setattr(Path, 'open', legacy_open)


def test_route_save_and_load_keep_chinese_bytes(cp1252_default, tmp_path):
    graph = routes.new_graph('中文建模：比较守恒与统计路线')
    routes.add_path(graph, 'baseline', '守恒基线', note='独立验证，不替代真实证据')
    path = tmp_path / '路线.json'
    routes.save(graph, path)
    assert '中文建模'.encode('utf-8') in path.read_bytes()
    assert routes.load(path) == graph


def test_route_load_existing_utf8_does_not_corrupt_text(cp1252_default, tmp_path):
    graph = routes.new_graph('已有中文路线')
    path = tmp_path / 'existing.json'
    path.write_bytes(json.dumps(graph, ensure_ascii=False).encode('utf-8'))
    assert routes.load(path) == graph


def test_workflow_retains_existing_chinese_progress(cp1252_default, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'PROJECT', tmp_path)
    problem = tmp_path / 'problem.md'
    problem.write_bytes('独立合成题：两项资源约束。'.encode('utf-8'))
    case = Path(pipeline.init_case(tmp_path / 'cases', 'utf8-progress', problem)['case'])
    before = '已有中文进度：待核验，禁止追认。\n'
    progress = case / 'planning/progress.md'
    progress.write_bytes(before.encode('utf-8'))
    result = workflow.init(case, '明确本轮中文目标', budget_seconds=60, per_run_timeout=5)
    state, prefix, _ = workflow.read_state(case)
    assert state['goal'] == result['state']['goal'] == '明确本轮中文目标'
    assert prefix == before and progress.read_bytes().startswith(before.encode('utf-8'))


def test_competition_registry_preserves_actual_chinese_labels(cp1252_default):
    from evals.competitions import lookup
    record = lookup('graduate', 'main', '2026')
    assert '三等奖' in record['award_system']


def test_aggregate_import_and_chinese_review_roundtrip(cp1252_default, tmp_path):
    namespace = runpy.run_path(str(SOURCE / 'evals/aggregate.py'), run_name='__utf8_boundary__')
    paper = '中文论文：独立诊断'
    item = {'paper': paper, 'scores': dict.fromkeys(namespace['WEIGHTS'], 2)}
    path = tmp_path / 'review.json'
    path.write_bytes(json.dumps([item], ensure_ascii=False).encode('utf-8'))
    value = namespace['aggregate']([path])
    assert value[paper]['percent_mean'] == 50
    assert value[paper]['score_kind'] == 'uncalibrated_diagnostic'


def test_pipeline_environment_reads_utf8_toml(cp1252_default, tmp_path, monkeypatch):
    (tmp_path / 'pyproject.toml').write_bytes(
        '[project]\nname="praxis"\ndescription="保留中文原文"\ndependencies=[]\n'.encode('utf-8'))
    monkeypatch.setattr(pipeline, 'BUNDLE', tmp_path)
    assert pipeline.environment_snapshot()['packages'] == {}


def test_mcp_project_version_reads_utf8_toml(cp1252_default, tmp_path, monkeypatch):
    from scripts import mcp_server
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    (tmp_path / 'pyproject.toml').write_bytes(
        '[project]\nname="praxis"\nversion="0.8.0"\ndescription="保留中文版本说明"\n'.encode('utf-8'))
    monkeypatch.setattr(mcp_server, '__file__', str(scripts / 'mcp_server.py'))
    assert mcp_server._project_version() == '0.8.0'


def test_known_utf8_route_rejects_invalid_bytes(cp1252_default, tmp_path):
    path = tmp_path / 'invalid.json'
    original = b'{"question":"\xff"}'
    path.write_bytes(original)
    with pytest.raises(UnicodeDecodeError):
        routes.load(path)
    assert path.read_bytes() == original


def test_original_problem_explicit_legacy_encoding_still_works(cp1252_default, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'PROJECT', tmp_path)
    text = 'Résumé : coût = 4; vérifier le résultat.'
    problem = tmp_path / 'problem.md'
    original = text.encode('cp1252')
    problem.write_bytes(original)
    case = Path(pipeline.init_case(tmp_path / 'cases', 'legacy-intake', problem, encoding='cp1252')['case'])
    assert problem.read_bytes() == original
    assert (case / 'planning/problem-extracted.txt').read_bytes().decode('utf-8') == text


def test_pipeline_logs_preserve_actual_raw_child_bytes(cp1252_default, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'PROJECT', tmp_path)
    problem = tmp_path / 'problem.md'
    problem.write_bytes('合成测试：整数二加二等于四。'.encode('utf-8'))
    case = Path(pipeline.init_case(tmp_path / 'cases', 'raw-logs', problem)['case'])
    model = '''import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
sys.stdout.buffer.write(b'\\xffraw\\x00'+"中文日志".encode('utf-8'))
(a.output/'results.json').write_text(json.dumps({'answer':4,'label':'整数答案'},ensure_ascii=False),encoding='utf-8')
'''
    validator = '''import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--results',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
r=json.loads(a.results.read_text(encoding='utf-8'))
sys.stderr.buffer.write(b'\\xfevalidator')
a.output.write_text(json.dumps([{'name':'整数恒等式','passed':r['answer']==2+2,'evidence':'独立整数计算：2+2=4'}],ensure_ascii=False),encoding='utf-8')
'''
    (case / 'code/model.py').write_bytes(model.encode('utf-8'))
    (case / 'code/validate.py').write_bytes(validator.encode('utf-8'))
    result = pipeline.run_case(case, timeout=10)
    assert result['status'] == 'automatic-checks-passed'
    run = Path(result['run'])
    assert (run / 'model.stdout.log').read_bytes() == b'\xffraw\x00' + '中文日志'.encode('utf-8')
    assert (run / 'validation.stderr.log').read_bytes() == b'\xfevalidator'
    assert pipeline.read_json(run / 'output/results.json') == {'answer': 4, 'label': '整数答案'}


def test_bilingual_release_notes_cli_reads_utf8_inputs(cp1252_default, tmp_path, monkeypatch):
    from scripts import release_notes
    (tmp_path / 'CHANGELOG.md').write_bytes('## 0.8.0 · Fixture\n\n中文改进。 English changes.\n'.encode('utf-8'))
    assets = tmp_path / 'assets.json'
    assets.write_bytes(json.dumps({'assets': [{'name': 'praxis.zip'}], 'note': '中文元数据'}, ensure_ascii=False).encode('utf-8'))
    output = tmp_path / 'release.md'
    monkeypatch.setattr(release_notes, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['release_notes', '--version', '0.8.0', '--assets-json', str(assets), '--output', str(output)])
    release_notes.main()
    assert '中文改进。 English changes.' in output.read_bytes().decode('utf-8')


def test_reference_cli_preserves_non_doi_chinese_without_network(cp1252_default, tmp_path, monkeypatch, capsys):
    from scripts import check_references
    source = tmp_path / 'references.txt'
    citation = '中文书目：模型假设与验证，2026。'
    source.write_bytes((citation + '\n').encode('utf-8'))
    monkeypatch.setattr(sys, 'argv', ['check_references', str(source)])
    monkeypatch.setattr(check_references.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('No DOI means no network'))
    with pytest.raises(SystemExit) as exited:
        check_references.main()
    assert exited.value.code == 0
    assert json.loads(capsys.readouterr().out)[0]['citation'] == citation


def test_generated_index_actual_cli_check_under_cp1252_default():
    # New process exercises module import + actual --check without altering the index.
    script = '''from pathlib import Path
import runpy,sys
original=Path.open
def legacy(path, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
    if 'b' not in mode and encoding in (None,'locale'): encoding='cp1252'
    return original(path,mode,buffering,encoding,errors,newline)
Path.open=legacy
sys.argv=['gen_tool_index','--check']
runpy.run_module('scripts.gen_tool_index',run_name='__main__')
'''
    process = subprocess.run([sys.executable, '-B', '-c', script], cwd=SOURCE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    assert process.returncode == 0, process.stderr.decode('utf-8', errors='replace')


def test_generated_index_actual_write_is_utf8(cp1252_default, tmp_path, monkeypatch, capsys):
    # Exact producer source, temporary output root; no public generated file is rewritten.
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    (tmp_path / 'references').mkdir()
    generator = scripts / 'gen_tool_index.py'
    generator.write_bytes((SOURCE / 'scripts/gen_tool_index.py').read_bytes())
    monkeypatch.setattr(sys, 'argv', ['gen_tool_index'])
    runpy.run_path(str(generator), run_name='__main__')
    value = json.loads(capsys.readouterr().out)
    output = tmp_path / 'references/tool-index.md'
    assert value['written'] == str(output)
    assert output.read_bytes().decode('utf-8').startswith('# 工具索引\n')
