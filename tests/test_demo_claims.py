"""The numbers printed on the case pages and homepage must come from the archived records."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMOS = ROOT / 'demos'


def read(path):
    return (ROOT / path).read_text()


def records(demo, name):
    return json.loads((DEMOS / demo / 'reproduce/reference' / name).read_text())


def selected(group, cap):
    rows = records('cumcm-1998-a', 'results.json')['groups'][group]['selected']
    return next(r for r in rows if abs(r['risk_cap'] - cap) < 1e-9)


def test_cumcm_case_page_numbers_match_records():
    expected = [f"{100 * selected('four', .01)['net_return']:.2f}%", f"{100 * selected('fifteen', .10)['net_return']:.2f}%"]
    rec = records('cumcm-1998-a', 'recommendation.json')['groups']
    expected += [f"{100 * rec['four']['knee_net_return']:.2f}%", f"{100 * rec['fifteen']['knee_net_return']:.2f}%"]
    thresholds = {row['group']: math.ceil(row['sufficient_threshold_yuan']) for row in records('cumcm-1998-a', 'capital-threshold-check.json')}
    for page in ('demos/cumcm-1998-a/README.md', 'demos/cumcm-1998-a/README.en.md'):
        text = read(page)
        for value in expected:
            assert value in text, (page, value)
        for value in thresholds.values():
            assert f'{value:,}' in text or str(value) in text, (page, value)


def test_mcm_case_page_numbers_match_records():
    results = records('mcm-2016-a', 'results.json')
    extended = records('mcm-2016-a', 'extended.json')
    schedule = next(r for r in extended['control']['runs'] if r['segments'] == 12)
    expected = [f"{results['policy']['water_l']:.2f}", f"{schedule['water_l']:.2f}",
                f"{results['analytic']['mixed_optimum_l']:.2f}", f"{results['analytic']['energy_lower_bound_l']:.2f}"]
    for page in ('demos/mcm-2016-a/README.md', 'demos/mcm-2016-a/README.en.md'):
        text = read(page)
        for value in expected:
            assert value in text, (page, value)


def page_count(demo):
    record = json.loads((DEMOS / demo / 'verification.json').read_text())
    return record['report_pages'] if 'report_pages' in record else record['pdf']['pages_total']


def test_page_counts_agree_everywhere():
    phrase = re.compile(r'(?:完整 |英文，|# )(\d+) 页|complete (\d+)-page|English, (\d+) pages|# (\d+) pages')
    for demo in ('cumcm-1998-a', 'mcm-2016-a'):
        count = page_count(demo)
        for page in (f'demos/{demo}/README.md', f'demos/{demo}/README.en.md'):
            numbers = {int(n) for groups in phrase.findall(read(page)) for n in groups if n}
            assert numbers == {count}, (page, numbers, count)
    for page, pattern in (('README.md', r'(\d+) 页(?:中文|英文)报告'), ('README.en.md', r'(\d+)-page (?:Chinese|English) report')):
        found = sorted(int(n) for n in re.findall(pattern, read(page)))
        assert found == sorted([page_count('cumcm-1998-a'), page_count('mcm-2016-a')]), (page, found)


def test_case_pages_only_link_to_existing_files():
    for page in DEMOS.glob('*/README*.md'):
        for target in re.findall(r'\]\(([^)#]+?)(?:#[^)]*)?\)', page.read_text()):
            if target.startswith(('http', 'mailto')):
                continue
            assert (page.parent / target).exists(), (page, target)
