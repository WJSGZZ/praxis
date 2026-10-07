import json
import subprocess
import sys

import pytest

from evals import planted


@pytest.mark.parametrize('kind', sorted(planted.GENERATORS))
def test_tools_recover_planted_truth_on_unseen_seeds(kind):
    for seed in range(1, 9):
        task, truth = planted.GENERATORS[kind](seed)
        answer = planted.solve_with_tools(task)
        result = planted.score(kind, seed, answer)
        assert result['correct'], (kind, seed, answer, truth)


def test_statement_never_contains_the_truth_and_wrong_answers_fail():
    for kind in planted.GENERATORS:
        task, truth = planted.GENERATORS[kind](3)
        shown = json.dumps(dict(statement=task.statement, data=task.data))
        for value in truth.values():
            assert str(value) not in shown
    task, truth = planted.GENERATORS['queue'](3)
    assert not planted.score('queue', 3, dict(mean_wait=truth['mean_wait'] * 1.01))['correct']
    assert not planted.score('queue', 3, {})['correct']
    assert not planted.score('structure', 3, dict(properties=['nonsense']))['correct']


def test_command_line_round_trip():
    out = subprocess.run([sys.executable, '-m', 'evals.planted', 'new', 'assignment', '5'], capture_output=True, text=True, check=True).stdout
    task = json.loads(out)
    assert 'total' in task['report'] and 'cost' in task['data']
    truth = planted.GENERATORS['assignment'](5)[1]['total']
    ok = subprocess.run([sys.executable, '-m', 'evals.planted', 'check', 'assignment', '5', json.dumps(dict(total=truth))], capture_output=True, text=True, check=True).stdout
    assert json.loads(ok)['correct']


def test_non_object_answers_get_a_helpful_error_and_the_task_carries_a_template():
    with pytest.raises(ValueError, match='JSON object with the keys'):
        planted.score('structure', 3, ['convex'])
    out = subprocess.run([sys.executable, '-m', 'evals.planted', 'new', 'structure', '3'], capture_output=True, text=True, check=True).stdout
    assert json.loads(out)['answer_template'] == {'properties': []}
