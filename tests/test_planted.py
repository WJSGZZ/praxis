import json
import subprocess
import sys

import pytest

from evals import planted


@pytest.mark.parametrize('kind', sorted(planted.GENERATORS))
def test_tools_recover_planted_truth_on_fixed_development_seeds(kind):
    for seed in range(1, 9):
        task, truth = planted.GENERATORS[kind](seed)
        answer = planted.solve_with_tools(task)
        result = planted.score(kind, seed, answer)
        assert result['correct'], (kind, seed, answer, truth)


def test_task_does_not_print_answer_fields_and_wrong_answers_fail():
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


@pytest.mark.parametrize('bad', [True, '0.5', float('nan'), float('inf'), 10**1000, {}, []])
def test_numeric_submission_types_are_strict(bad):
    assert not planted.score('queue', 3, {'mean_wait': bad})['correct']


@pytest.mark.parametrize('bad', ['convex', {}, ['convex', 'convex'], [True]])
def test_property_submission_types_are_strict(bad):
    assert not planted.score('structure', 3, {'properties': bad})['correct']


def test_queue_oracle_does_not_call_the_production_solver(monkeypatch):
    assert planted._queue_wait_oracle(1, 2, 1) == pytest.approx(.5)
    assert planted._queue_wait_oracle(2, 2, 2) == pytest.approx(1 / 6)
    monkeypatch.setattr(planted.queueing, 'mmc', lambda *a: {'mean_wait': -100})
    task, _ = planted.gen_queue(3)
    assert not planted.score('queue', 3, planted.solve_with_tools(task))['correct']


def test_lp_vector_is_required_and_other_optimal_vectors_are_accepted(monkeypatch):
    task, truth = planted.gen_lp(3)
    assert not planted.score('lp', 3, truth)['correct']
    assert not planted.score('lp', 3, dict(value=truth['value'], x=[0] * 6))['correct']
    # Two different optima on x1+x2=1. Scoring must check the certificate, not exact vector equality.
    custom = planted.Task('lp', 0, '', {'c': [1, 1], 'A': [[1, 1]], 'b': [1]}, ['value', 'x'])
    monkeypatch.setitem(planted.GENERATORS, 'lp', lambda seed: (custom, {'value': 1.}))
    for x in ([1, 0], [0, 1], [.25, .75]):
        assert planted.score('lp', 0, {'value': 1., 'x': x})['correct']
    for x in ([1], [True, 0], [float('nan'), 0], [2, 0], [-1, 2]):
        assert not planted.score('lp', 0, {'value': 1., 'x': x})['correct']


def test_sir_oracle_respects_finite_initial_conditions():
    import math
    for r0 in (.5, 1., 2., 5.):
        attack = planted._sir_attack_oracle(r0)
        susceptible = 1 - attack
        assert math.log(susceptible / .99999) + r0 * attack == pytest.approx(0, abs=1e-12)
        assert attack >= .00001 - 1e-12


def test_exact_structure_labels_include_degenerate_boundaries():
    assert 'convex' in planted._family_properties(7, 1, 2)  # eigenvalues 0 and 4
    assert 'convex' not in planted._family_properties(7, 1, 3)
    assert 'convex' in planted._family_properties(2, 1, 2)  # Hessian determinant zero
    assert 'convex' not in planted._family_properties(2, 2, 2)
    assert 'symmetric' in planted._family_properties(4, 3, 3)
    assert 'increasing_in_x' not in planted._family_properties(3, 1, 1)
    with pytest.raises(ValueError):
        planted._family_properties(9, 1, 1)
