"""Independent fee/risk answers for the demo's comparison helpers."""
import ast
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]/'demos/cumcm-1998-a/reproduce'


def helpers(filename, budget):
    # These scripts run a complete demo at import time; test only their helpers.
    tree = ast.parse((ROOT/filename).read_text())
    tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    namespace = {'np': np, 'M': budget}
    exec(compile(tree, filename, 'exec'), namespace)
    return namespace


def test_budget_reduction_uses_minimum_fee_below_threshold():
    h = helpers('check_robustness.py', 100.)
    data = np.array([[20., 5., 10., 100.]])
    # A positive purchase below 100 still costs 10; the maximum principal is 90.
    x, scaled = h['within_budget'](data, np.array([99.]))
    assert scaled and x[0] == pytest.approx(90.)
    assert h['spent'](data, x) == pytest.approx(100.)


def test_independent_risk_closed_form_and_regime_rejection():
    h = helpers('check_alternatives.py', 1000.)
    data = np.array([[25., 10., 0., 1.], [25., 10., 0., 1.]])
    # Equal returns/risk: Cauchy-Schwarz has equal investments, ||.1*x||2=10.
    x = h['std_risk'](data, .01)
    assert x == pytest.approx([100/np.sqrt(2)]*2)
    assert np.linalg.norm(.1*x)/1000 == pytest.approx(.01)
    data[:, 3] = 10000.
    with pytest.raises(ValueError, match='fee/budget regime'):
        h['std_risk'](data, .01)


def test_current_shortfall_is_against_executable_plan_and_zip_matches():
    from zipfile import ZipFile
    records = json.loads((ROOT/'reference/robustness.json').read_text())
    for group, count, cap in [('four', 106, .006), ('fifteen', 95, .08)]:
        execution = records['groups'][group]['parameter_error_10pct']['kept_plan_execution']
        assert execution['raw_over_budget_count'] == count
        assert execution['maximum_spent_yuan'] <= 1e6 + 1e-6
        assert execution['maximum_risk'] <= cap + 1e-12
        assert execution['minimum_return_shortfall'] >= -1e-7
    with ZipFile(ROOT.parent/'deliverables/supporting_materials.zip') as z:
        for filename in ('check_alternatives.py', 'check_robustness.py',
                         'reference/alternatives.json', 'reference/robustness.json'):
            assert z.read(filename) == (ROOT/filename).read_bytes()


def test_support_readme_matches_archived_generator_and_pinned_runtime():
    from zipfile import ZipFile
    with ZipFile(ROOT.parent/'deliverables/supporting_materials.zip') as z:
        tree = ast.parse(z.read('build_paper.py').decode())
        strings = [node.value for node in ast.walk(tree)
                   if isinstance(node, ast.Constant) and isinstance(node.value, str)
                   and node.value.startswith('# 《投资的收益和风险》支撑材料')]
        assert len(strings) == 1
        assert z.read('README.md').decode() == strings[0]
        assert 'Tectonic 0.17.0' in strings[0] and 'Fandol 0.3' in strings[0]
