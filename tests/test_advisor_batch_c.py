"""Small independent counterexamples for advisor batch C's conclusion exits."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest
from scipy.optimize import linprog

from evals import aggregate as ag
from scripts import texplot
from modeling import experiment, structure

ROOT = Path(__file__).resolve().parents[1]


def audited():
    return {'schema_version': 2, 'paper': 'P',
            'checklist': {d: {k: {'met': True, 'reviewed': True, 'evidence': 'explicit audit'}
                              for k in keys} for d, keys in ag.CHECKLIST_IDS.items()},
            'critical_claims': [{'id': 'answer', 'claim': '2+1=3', 'status': 'supported', 'evidence': 'substitution'}]}


def test_user_view_keeps_unreviewed_na_reasons_and_supported_claim(tmp_path):
    item = audited()
    item['checklist']['writing']['W5'].update(met=False, reviewed=False, reason='language review not performed')
    item['checklist']['robustness']['R2'].update(met=None, reason='no fitted parameters')
    path = tmp_path / 'review.json'; path.write_text(json.dumps([item]))
    view = ag.user_view(ag.aggregate([path]))['P']['reviews'][0]
    assert view['validity_status'] == 'supported'
    assert view['unreviewed_items'] == ['writing/W5']
    assert view['not_applicable_items'] == ['robustness/R2']
    summary = view['coverage_summary']
    assert summary['status'] == 'partial'
    assert summary['unreviewed_items'][0]['reason'] == 'language review not performed'
    assert summary['not_applicable_items'][0]['reason'] == 'no fitted parameters'
    assert 'percent_mean' not in view


def test_legacy_review_coverage_unknown_not_inferred():
    record = ag.review_record({'scores': dict.fromkeys(ag.WEIGHTS, 4)})
    assert record['coverage_summary']['status'] == 'unknown'
    assert record['coverage_summary']['reviewed_item_count'] is None
    old_record = {'validity_status': 'supported', 'unreviewed_items': ['writing/W5']}
    view = ag.user_view({'P': {'reviews': [old_record]}})['P']['reviews'][0]
    assert view['coverage_summary']['status'] == 'unknown'
    assert view['coverage_summary']['unreviewed_items'][0]['item'] == 'writing/W5'
    v1 = ag.review_record({'checklist': {'writing': {'W5': {'met': True, 'evidence': 'old entry'}}}})
    assert v1['coverage_summary']['unknown_items'][0]['item'] == 'writing/W5'


@pytest.mark.parametrize('labels,values,colors', [([], [], []), (['A','B'], [1,999], ['main']),
    (['A'], [1,999], ['main','accent']), (['A','B'], [1], ['main','accent']),
    (['A','B'], [1,float('inf')], ['main','accent'])])
def test_hbar_never_silently_drops_values(labels, values, colors):
    with pytest.raises(ValueError):
        texplot.hbar_chart(labels, values, colors, 'value', unit='')


@pytest.mark.parametrize('cubes,titles', [([], []), ([[[]]], ['A']),
    ([[[1]], [[2],[999]]], ['A','B']), ([[[1,2],[3]]], ['A']),
    ([[[1]], [[2]]], ['A']), ([[[1,float('nan')]]], ['A'])])
def test_heatmap_rejects_mismatched_or_nonfinite_cells(cubes, titles):
    with pytest.raises(ValueError):
        texplot.heatmap_panels(cubes, titles, 'x', 'y', (1,1), 0,1000)


def test_valid_charts_keep_every_point_and_orientation():
    bar = texplot.hbar_chart(['A','B'], [1,999], ['main','accent'], 'value', unit='')
    assert bar.count(r'\addplot') == 2 and '(999,1)' in bar
    heat = texplot.heatmap_panels([[[1,2],[3,999]], [[5,6],[7,8]]], ['A','B'], 'x','y',(2,2),0,1000)
    assert '1.5 1.5 999' in heat
    assert '0.5 1.5 2' in heat and '1.5 0.5 3' in heat


def domino_module():
    spec = importlib.util.spec_from_file_location('advisor_domino', ROOT/'demos/domino-research/reproduce/build_note.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_domino_summary_uses_recorded_overlap_and_checks_mismatch():
    note = domino_module()
    assert note.verification_ranges(note.R) == (5,16)
    assert '$0\\le n\\le 5$' in note.count_summary(note.R)
    assert 'Counts from three independent methods agree up to $n=16$' not in note.TEX
    small = {'counts': {'backtracking_n0_to_1':[1,3], 'transfer_matrix_n0_to_2':[1,3,11],
                        'coupled_recurrences_n0_to_2':[1,3,11]}}
    assert note.verification_ranges(small) == (1,2)
    assert '$0\\le n\\le 1$' in note.count_summary(small)
    bad = copy.deepcopy(small); bad['counts']['coupled_recurrences_n0_to_2'][1] = 999
    with pytest.raises(ValueError, match='comparison fails'):
        note.verification_ranges(bad)
    bad = copy.deepcopy(small); bad['counts']['transfer_matrix_n0_to_2'].pop()
    with pytest.raises(ValueError, match='length disagree'):
        note.verification_ranges(bad)


def test_mathematical_shortcuts_retain_needed_conditions():
    probe = structure.check_convexity(lambda x: x[0]**2, [[-1,1]], trials=4)
    assert not probe['proved']
    # A=[1] is TU, but fractional RHS has fractional optimal vertex.
    assert structure.is_network_matrix([[1]])['totally_unimodular']
    assert linprog([-1], A_ub=[[1]], b_ub=[.5], bounds=[(0,None)]).x[0] == .5
    assert linprog([-1], A_ub=[[1]], b_ub=[2], bounds=[(0,None)]).x[0] == 2
    # Sampling cannot certify the unvisited integer domain, even for a true claim.
    sampled = experiment.find_counterexample(lambda n: n >= 0, [('int',0,100)], trials=2, exhaustive_limit=1)
    assert not sampled['found'] and not sampled['proved_for_domain']
    exhaustive = experiment.find_counterexample(lambda n: n >= 0, [('int',0,2)])
    assert exhaustive['proved_for_domain']
    docs = {name:(ROOT/'references'/name).read_text() for name in ['coverage-map.md','structure-discovery.md','research-mode.md','writing.md']}
    assert '数值未发现反例不证明凸性' in docs['coverage-map.md']
    assert '整数右端项' in docs['structure-discovery.md'] and '0.5' in docs['structure-discovery.md']
    assert '已检查的样本中未发现反例' in docs['research-mode.md']
    assert '简单解析结果可以不画图' in docs['writing.md']
    assert '复杂数值场可沿用成熟科学绘图库' in docs['writing.md']
    assert '开头放一张“本文工作”结构图' not in docs['writing.md']
