"""Check the complete synthetic task and independent validator's discrimination."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'demos/data-vintages'


def module_from(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_complete_vintage_case_retains_population_and_rejects_wrong_answers(tmp_path):
    runner = module_from(DEMO / 'run.py', 'vintage_runner')
    previous_workspace = runner.pipeline.PROJECT
    receipt = runner.reproduce(tmp_path / 'vintage-task')
    assert runner.pipeline.PROJECT == previous_workspace
    case, run = Path(receipt['case']), Path(receipt['run'])
    results = json.loads((run / 'output/results.json').read_text(encoding='utf-8'))
    assert receipt['covered_requirements'] == 4
    assert results['mapping']['counts'] == dict(matched=17, not_available=1,
                                              unknown_availability=1, ambiguous_latest=1)
    assert results['daily_actionable_days'] == 8 and results['daily_decision_days'] == 10
    assert results['comparison']['asof']['mae'] == 87 / 16
    assert results['comparison']['baseline']['realized_cost'] == 157
    assert results['comparison']['final_snapshot']['mae'] == 0
    assert results['comparison']['final_snapshot']['eligible_at_cutoff_under_declared_metadata'] is False
    validator = module_from(case / 'code/validate.py', 'vintage_validator')
    assert all(c['passed'] for c in validator.validate(results))
    mutations = []
    future = copy.deepcopy(results)
    future['mapping']['mappings'][0]['matched_version_index'] = 36
    mutations.append(future)
    omitted = copy.deepcopy(results)
    omitted['daily_actions'] = omitted['daily_actions'][:8]
    mutations.append(omitted)
    wrong_order = copy.deepcopy(results)
    wrong_order['daily_actions'][0]['orders']['A'] += 1
    mutations.append(wrong_order)
    wrong_score = copy.deepcopy(results)
    wrong_score['comparison']['asof']['realized_cost'] = 0
    mutations.append(wrong_score)
    false_time_claim = copy.deepcopy(results)
    false_time_claim['comparison']['final_snapshot']['eligible_at_cutoff_under_declared_metadata'] = True
    mutations.append(false_time_claim)
    false_coverage = copy.deepcopy(results)
    false_coverage['query_coverage']['matched'] = 20
    mutations.append(false_coverage)
    for changed in mutations:
        assert any(not c['passed'] for c in validator.validate(changed))
    with pytest.raises(FileExistsError):
        runner.reproduce(case)
    assert runner.pipeline.PROJECT == previous_workspace


def test_selected_artifacts_match_their_publication_manifest():
    metadata = json.loads((DEMO / 'demo.json').read_text(encoding='utf-8'))
    for relative, expected in metadata['files'].items():
        assert hashlib.sha256((DEMO / relative).read_bytes()).hexdigest() == expected, relative
