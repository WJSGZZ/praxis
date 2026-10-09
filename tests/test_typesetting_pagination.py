"""CI must distinguish a solution-page cap from historical PDF length."""
import importlib.util
from pathlib import Path
import pytest

SPEC = importlib.util.spec_from_file_location(
    "typesetting_ci", Path(__file__).resolve().parents[1] / ".github/scripts/typesetting.py")
ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ci)


def pages(solution, ai=1):
    result = []
    for i in range(solution + ai):
        heading = ('Summary' if i == 0 else
                   'Report on Use of AI' if i == solution else 'Text')
        lines = [f'Team # 7391856 Page {i + 1} of {solution + ai}', heading]
        result.append(dict(text='\n'.join(lines), lines=lines, body_size=12.0))
    return result


@pytest.mark.parametrize('solution,ai', [(24, 1), (25, 1), (16, 1), (25, 3)])
def test_current_solution_limit_accepts_varied_total_length(solution, ai):
    rules = ci.check_mcm_pagination(pages(solution, ai))
    assert rules['facts']['counted_pages'] == solution
    assert rules['facts']['total_pages'] == solution + ai


def test_solution_overflow_is_not_excused_by_ai_appendix():
    with pytest.raises(ValueError, match='25-page limit'):
        ci.check_mcm_pagination(pages(26))


def test_ai_report_is_required_for_these_ai_assisted_demos():
    with pytest.raises(ValueError, match='missing its AI-use report'):
        ci.check_mcm_pagination(pages(25, 0))
