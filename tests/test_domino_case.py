import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'demos/domino-research'


def load_explore():
    spec = importlib.util.spec_from_file_location('domino_explore', CASE / 'reproduce/explore.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_case_recomputes_its_archived_numbers_and_proofs_hold():
    out = load_explore().main()
    archived = json.loads((CASE / 'reproduce/reference/results.json').read_text())
    assert out['counts'] == archived['counts']
    assert out['guess']['coefficients'] == ['4', '-1'] and out['guess']['holdout_ok']
    assert out['finite_check']['proof_by_finite_check'] and out['finite_check']['equations_needed'] == 8
    assert out['counterexample_search_n2_to_60']['proved_for_domain'] and out['closed_form_matches_n0_to_60']
    assert out['route_issues'] == []


def test_case_pages_state_the_archived_terms():
    archived = json.loads((CASE / 'reproduce/reference/results.json').read_text())
    last = str(archived['counts']['transfer_matrix_n0_to_16'][-1])
    for page in ('README.md', 'README.en.md'):
        assert last in (CASE / page).read_text()
    assert (CASE / 'deliverables/note.pdf').stat().st_size > 10_000
