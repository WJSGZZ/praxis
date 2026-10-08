import copy
import json
from pathlib import Path
import pytest
from scripts import contributions
from test_pipeline import make_case, pipeline


def event():
    return dict(source={'excerpt': '高峰期也能这样排队吗？'}, proposer='user', matter='检查稳态假设',
                task='Q1', executor='assistant', kind='challenge', status='proposed',
                impact='待核', evidence=[], mode='collaboration', origin='contemporaneous')


def test_contribution_append_does_not_expire_run_but_accepted_code_change_does(tmp_path):
    case, _, _ = make_case(tmp_path)
    pipeline.run_case(case)
    first = contributions.append_event(case, event())
    assert pipeline.status(case)['runs'][0]['usable_automatic_evidence']
    revised = {**event(), 'supersedes': first['id'], 'status': 'implemented',
               'impact': '增加高峰时段检查', 'evidence': ['code/model.py']}
    (case / 'code/model.py').write_text((case / 'code/model.py').read_text() + '\n# changed model assumptions\n')
    second = contributions.append_event(case, revised)
    assert not pipeline.status(case)['runs'][0]['usable_automatic_evidence']
    summary = contributions.summarize(case)
    assert summary['historical_events'] == 2 and summary['events'][0]['id'] == second['id']
    assert len(contributions.read_events(case)) == 2


@pytest.mark.parametrize('change', [
    {'source': {}}, {'status': 'implemented'}, {'contribution_percent': 80}, {'human_verified': True},
    {'kind': 'method-innovation'}, {'origin': 'inferred'}, {'supersedes': 'made-up'},
    {'evidence': ['../private.txt']}, {'evidence': ['/etc/hosts']}, {'evidence': ['missing.txt']},
])
def test_records_require_real_trace_and_workspace_evidence(tmp_path, change):
    data = event()
    data.update(change)
    with pytest.raises(ValueError):
        contributions.append_event(tmp_path, data)
    assert not (tmp_path / 'planning/contributions.jsonl').exists()


def test_log_symlink_cannot_write_outside_workspace(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    root = tmp_path / 'workspace'
    root.mkdir()
    (root / 'planning').symlink_to(outside)
    with pytest.raises(ValueError, match='remain'):
        contributions.append_event(root, event())


def test_record_evidence_is_locatable_without_claiming_verification(tmp_path):
    file = tmp_path / 'notes.md'
    file.write_text('Observed a failed assumption; not an independent mathematical verification.')
    record = contributions.append_event(tmp_path, {**event(), 'status': 'checked', 'evidence': ['notes.md']})
    assert len(record['evidence_sha256']['notes.md']) == 64
    assert record['kind'] == 'challenge'
    assert record['proposer'] == 'user' and record['executor'] == 'assistant'
    assert 'percentage' in contributions.summarize(tmp_path)['scope']
