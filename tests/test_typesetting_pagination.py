"""CI must distinguish a solution-page cap from historical PDF length."""
import importlib.util
import json
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


def current_cumcm_pages():
    root = Path(__file__).resolve().parents[1]
    return ci.extract(root / 'demos/cumcm-1998-a/deliverables/paper.pdf')


def test_cumcm_ci_uses_current_accepted_pagination():
    root = Path(__file__).resolve().parents[1]
    accepted = json.loads((root / 'demos/cumcm-1998-a/verification.json').read_text())
    rules = ci.check_cumcm_pagination(
        current_cumcm_pages(), expected_total=accepted['report_pages'],
        expected_body=accepted['target_inverse_revision']['answer_pages_excluding_abstract'])
    assert (rules['facts']['total_pages'], rules['facts']['body_pages']) == (35, 14)


@pytest.mark.parametrize('total,body', [(23, 12), (34, 14), (35, 13), (35, 15)])
def test_cumcm_ci_rejects_stale_or_wrong_pagination(total, body):
    with pytest.raises(ValueError, match='Unexpected pagination'):
        ci.check_cumcm_pagination(current_cumcm_pages(), expected_total=total, expected_body=body)


def historical_profile():
    root = Path(__file__).resolve().parents[1]
    return json.loads((root/'demos/mcm-2016-a/verification.json').read_text())


def test_historical_selected_work_keeps_current_page_failure_visible():
    result = ci.check_historical_mcm_layout(pages(27), historical_profile())
    assert result['layout_comparison_passed']
    assert result['historical_contest_eligibility'] == 'unverified'
    assert not result['passed'] and '25-page limit' in result['errors'][0]


def test_historical_layout_refuses_wrong_pagination_or_mixed_ai_page():
    with pytest.raises(ValueError, match='Unexpected pagination'):
        ci.check_historical_mcm_layout(pages(26), historical_profile())
    mixed = pages(27); mixed[-1]['lines'].insert(1, 'References')
    mixed[-1]['text'] = '\n'.join(mixed[-1]['lines'])
    with pytest.raises(ValueError):
        ci.check_historical_mcm_layout(mixed, historical_profile())


def test_current_or_claimed_verified_year_cannot_use_historical_gate():
    current = historical_profile(); current['selection']['edition'] = 2026
    with pytest.raises(ValueError, match='explicit unverified 2016'):
        ci.check_historical_mcm_layout(pages(27), current)
    certified = historical_profile(); certified['format']['formal_2016_page_limit_verified'] = True
    with pytest.raises(ValueError, match='explicit unverified 2016'):
        ci.check_historical_mcm_layout(pages(27), certified)
