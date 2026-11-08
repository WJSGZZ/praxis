"""Exact quantifier checks, scope separation, and compatibility of the normal evidence entry."""
import pytest

from modeling.proof_obligations import review
from scripts import pipeline
from test_gates import make_schema2_case


def obligation(**changes):
    return dict({'method': 'quadratic_extrema', 'quantifier': 'forall', 'domain': 'real_interval',
                 'interval': [0, 1], 'coefficients': [0, -1, 1]}, **changes)


def test_endpoints_of_a_real_interval_are_not_the_interval():
    witness = review(obligation(method='witness', point=0))
    assert witness['status'] == 'open' and witness['agrees_with_assertion'] is None
    finite = review(obligation(method='enumeration', domain='integer_interval'))
    assert finite['status'] == 'formal_support'
    assert finite['checked'] == [{'point': '0', 'value': '0'}, {'point': '1', 'value': '0'}]
    real = review(obligation())
    assert real['status'] == 'formal_refutation'
    assert real['checked'][-1] == {'point': '1/2', 'value': '-1/4'}
    assert review(obligation(method='witness', point='1/2', asserted_truth=False))['agrees_with_assertion']


def test_witness_covers_the_entire_scope_of_a_singleton():
    record = obligation(method='witness', interval=[1, 1], point=1)
    assert review(record)['status'] == 'formal_support'
    assert review(dict(record, quantifier='exists', coefficients=[-1]))['status'] == 'formal_refutation'


def test_existence_may_require_the_interior_stationary_point():
    # -(x-2/3)^2 reaches zero only at x=2/3.
    polynomial = ['-4/9', '4/3', -1]
    result = review(obligation(quantifier='exists', coefficients=polynomial))
    assert result['status'] == 'formal_support'
    assert result['checked'][-1] == {'point': '2/3', 'value': '0'}
    assert review(obligation(quantifier='exists', coefficients=[-1]))['status'] == 'formal_refutation'


@pytest.mark.parametrize('record', [
    None, {'method': 'derivation', 'statement': 'q'}, obligation(method='witness', point=2),
    obligation(method='witness', domain='integer_interval', point='1/2'),
    obligation(method='enumeration'), obligation(method='enumeration', domain='integer_interval', interval=[0,128]),
    obligation(coefficients=[1,0,0,1]), obligation(coefficients=['1e100000000']),
    obligation(interval=[1,0]), obligation(coefficients=[False]), obligation(extra_assumption='x >= 1'),
    obligation(quantifier='almost surely'),
])
def test_unknown_or_inadmissible_formalizations_stay_open(record):
    assert review(record)['status'] == 'open'


def test_textual_deduction_is_assigned_to_review_even_with_fields_present():
    result = review(dict(method='derivation', statement='For any x >= 1, x*x >= x.',
                         domain='real x >= 1', argument='x(x-1) is a product of two nonnegative factors.'))
    assert result['status'] == 'needs_mathematical_review'


@pytest.mark.parametrize('record,status,linked', [
    (None, 'open', True), (obligation(), 'formal_refutation', False),
    (obligation(asserted_truth=False), 'formal_refutation', True),
    (obligation(coefficients=[1,-2,1]), 'formal_support', True),
])
def test_schema2_evidence_exposes_scope_without_upgrading_run_links(tmp_path, monkeypatch, record, status, linked):
    case = make_schema2_case(tmp_path, monkeypatch)
    path = case/'planning/requirements.json'
    definition = pipeline.read_json(path)
    definition['requirements'][0]['kind'] = 'proof'
    claim = {'id': 'K', 'requirement': 'Q1', 'text': 'Scope check', 'strength': 'independent',
             'checks': ['balance:water']}
    if record is not None:
        claim['proof_obligation'] = record
    definition['claims'] = [claim]
    pipeline.save(path, definition)
    assert pipeline.run_case(case)['automatic_checks_passed']
    observed = pipeline.evidence_index(case)
    entry = observed['entries'][0]
    assert entry['linked'] is linked
    assert observed['status'] == ('evidence-linked' if linked else 'evidence-incomplete')
    assert entry['proof_review'][0]['status'] == status
