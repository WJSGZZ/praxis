"""Reproduce the original synthetic vintage task through Praxis's case pipeline."""
import argparse
import json
from pathlib import Path
import shutil
import sys

BUNDLE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BUNDLE))
from scripts import pipeline


def reproduce(output):
    previous_workspace = pipeline.PROJECT
    try:
        return _reproduce(output)
    finally:
        pipeline.PROJECT = previous_workspace


def _reproduce(output):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Refuse to overwrite an existing run: {output}')
    demo = Path(__file__).resolve().parent
    pipeline.PROJECT = output.parent
    intake = pipeline.init_case(output.parent, output.name, demo / 'data/problem.md',
                                [demo / 'data' / n for n in
                                 ['queries.json', 'versions.json', 'outcomes.json', 'plan.json']],
                                phase='preparation', encoding='utf-8')
    case = Path(intake['case'])
    for name in ['model.py', 'validate.py']:
        shutil.copyfile(demo / name, case / 'code' / name)
    shutil.copyfile(demo / 'requirements.json', case / 'planning/requirements.json')
    (case / 'planning/tasks.md').write_text(
        (demo / 'data/problem.md').read_text(encoding='utf-8') +
        '\nImplementation: declared-availability Pandas mapping and HiGHS MILP. '
        'Independent checks: UTC scan and all feasible integer orders. '
        'All original targets and unresolved days remain.\n', encoding='utf-8')
    receipt = pipeline.run_case(case, timeout=120)
    if receipt['status'] != 'automatic-checks-passed':
        raise RuntimeError(f'Reproduction failed; retained receipt: {receipt["run"]}')
    evidence = pipeline.evidence_index(case)
    pipeline.save(case / 'evidence.json', evidence)
    if evidence['status'] != 'evidence-linked':
        raise RuntimeError('Recorded task evidence is incomplete')
    return {'case': str(case), 'run': receipt['run'], 'status': receipt['status'],
            'covered_requirements': evidence['covered'], 'paper_ready': False,
            'scope': 'Original synthetic exercise; not a deployment or award certificate'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reproduce(args.output), ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
