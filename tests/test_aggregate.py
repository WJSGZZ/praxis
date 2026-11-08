import json
from pathlib import Path

import pytest

from evals import aggregate as ag


def judge(paper, **scores):
    base = dict.fromkeys(ag.WEIGHTS, 2)
    base.update(scores)
    return dict(paper=paper, scores=base)


def research_item():
    return dict(schema_version=2, paper='research-note', reviewer='reviewer-1',
        critical_claims=[dict(id='theorem', claim='2 + 2 = 4', status='supported',
                             evidence='direct integer arithmetic')],
        issues=[], research_assessment=dict(problem='arithmetic', version='sha256:example',
            scope='one theorem and literature context', target_standard='original mathematics research',
            work_type='expository_note', overall_assessment='Correct exposition of a known fact.',
            criteria={k: dict(status='unverified' if k == 'novelty' else 'supported',
                              evidence='No originality search.' if k == 'novelty' else 'Scoped review p1.')
                      for k in ag.RESEARCH_CRITERIA},
            major_gaps=['No new theorem.'], actions=['Identify a distinct new mathematical question.'],
            novelty_search=dict(completed=False, scope='not performed', sources=[])))


def test_research_view_keeps_evidence_and_does_not_convert_to_awards(tmp_path):
    item = research_item()
    path = tmp_path / 'review.json'
    path.write_text(json.dumps([item]))
    internal = ag.aggregate([path])
    assert 'percent_mean' not in internal['research-note']
    user = ag.user_view(internal)['research-note']
    assert user['status'] == 'research_reviewer_assessments'
    assert user['assessments'][0]['version'] == 'sha256:example'
    assert user['assessments'][0]['review_id'] == user['reviews'][0]['review_id']
    assert user['reviews'][0]['critical_claims'][0]['status'] == 'supported'
    assert user['assessments'][0]['criteria']['novelty']['status'] == 'unverified'
    assert user['assessments'][0]['verification_checks'] is None
    assert user['assessments'][0]['closest_work_comparisons'] is None
    assert 'award_estimates' not in internal['research-note']


@pytest.mark.parametrize('mutation', [
    lambda x: x.update(award_estimate={}),
    lambda x: x.update(scores=dict.fromkeys(ag.WEIGHTS, 4)),
    lambda x: x.update(schema_version=True),
    lambda x: x['research_assessment']['criteria'].pop('significance'),
    lambda x: x['research_assessment']['criteria']['novelty'].update(status='supported'),
    lambda x: x['research_assessment']['criteria']['correctness'].update(evidence=''),
    lambda x: x['research_assessment']['criteria']['correctness'].update(issue_ids=['missing']),
    lambda x: x['research_assessment'].update(work_type='top_journal_accepted'),
    lambda x: x['research_assessment']['novelty_search'].update(completed='true'),
])
def test_research_rejects_unsupported_declarations(mutation, tmp_path):
    item = research_item()
    mutation(item)
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps([item]))
    with pytest.raises(ValueError):
        ag.aggregate([path])


def test_research_literature_and_root_issue_associations_are_preserved(tmp_path):
    item = research_item()
    item['issues'] = [dict(id='prior', description='Known result', evidence='prior theorem p2')]
    assessment = item['research_assessment']
    assessment['criteria']['novelty'].update(status='refuted', evidence='prior theorem p2', issue_ids=['prior'])
    assessment['novelty_search'].update(completed=True, scope='specific theorem search', sources=['primary paper p2'])
    path = tmp_path / 'known.json'
    path.write_text(json.dumps([item]))
    user = ag.user_view(ag.aggregate([path]))['research-note']
    assert user['assessments'][0]['criteria']['novelty']['issue_ids'] == ['prior']
    assert user['reviews'][0]['validity_status'] == 'supported'  # Known does not mean mathematically false.


def closest_comparison():
    return dict(claim_id='theorem', source='Test prior on addition', location='identity (1)',
                prior_result='Adding two to n gives n + 2.', scope='For integers; here n = 2.',
                derivation='Substitute 2 into (1).', relation='implied',
                increment_kind='mathematical_result', increment='The claimed new identity.',
                status='refuted')


def test_distinguish_known_claim_from_added_application_without_certifying_novelty(tmp_path):
    item = research_item()
    known = closest_comparison()
    application = dict(known, increment_kind='application', status='supported',
                       increment='Converts the identity into a check on a device count.',
                       application_implication='Two working units from each rack meet a target of four.')
    unresolved = dict(known, source='A second source', location='Abstract only',
                      scope='Full statement and assumptions unavailable.', relation='unresolved',
                      derivation='The abstract omits the hypotheses.', increment_kind='undetermined',
                      increment='Insufficient information for comparison.', status='unverified')
    rows = [known, application, unresolved]
    item['research_assessment']['closest_work_comparisons'] = rows
    path = tmp_path / 'review.json'
    path.write_text(json.dumps([item]))
    view = ag.user_view(ag.aggregate([path]))['research-note']
    assert view['assessments'][0]['closest_work_comparisons'] == rows
    assert view['assessments'][0]['criteria']['novelty']['status'] == 'unverified'
    assert view['validity'] == ['supported']

    assessment = item['research_assessment']
    assessment['novelty_search'].update(completed=True, scope='Fixture application comparison.',
                                        sources=[application['source']])
    assessment['criteria']['novelty'].update(status='supported', evidence=application['increment'])
    path.write_text(json.dumps([item]))
    updated = ag.user_view(ag.aggregate([path]))['research-note']['assessments'][0]
    assert updated['closest_work_comparisons'][-1]['status'] == 'unverified'
    assert updated['criteria']['novelty']['status'] == 'supported'


@pytest.mark.parametrize('updates', [
    {'claim_id': 'absent'}, {'location': ''}, {'derivation': ''}, {'status': 'supported'},
    {'relation': 'unresolved'}, {'increment_kind': 'application'}, {'relation': 'certified'},
    {'increment_kind': 'undetermined', 'status': 'supported'},
])
def test_reject_contradictory_or_unbound_prior_comparisons(updates):
    item = research_item()
    item['research_assessment']['closest_work_comparisons'] = [dict(closest_comparison(), **updates)]
    with pytest.raises(ValueError):
        ag.review_record(item)


def empirical_comparison():
    return dict(claim_id='theorem', kind='same_data_reproduction', status='consistent',
                actor='reviewer-1', basis='examined', evidence='test fixture, table 1',
                original_data='sample A v1', check_data='sample A v1', same_procedure=True,
                procedure='Mean using both original observations 1 and 3.',
                comparison_rule='Exact equality to 2.', observed='(1+3)/2=2')


def test_empirical_checks_separate_access_recalculation_and_new_samples(tmp_path):
    item = research_item()
    item['critical_claims'][0].update(claim='The original sample mean is 2.',
                                      evidence='Original observations are 1 and 3.')
    rerun = empirical_comparison()
    rows = [dict(claim_id='theorem', kind='artifact_access', status='restricted', basis='reported',
                 actor='data custodian', evidence='Reviewer granted controlled access.'),
            rerun, dict(rerun, kind='new_data_replication', status='inconsistent',
                        check_data='sample B', collection='New sampling visit for this fixture.',
                        procedure='Same instrument and estimand as in the original study.',
                        comparison_rule='Difference in means within 0.25.',
                        observed='Sample B mean 3; difference 1.')]
    item['research_assessment']['verification_checks'] = rows
    path = tmp_path / 'reviews.json'
    path.write_text(json.dumps([item]))
    view = ag.user_view(ag.aggregate([path]))['research-note']
    assert view['assessments'][0]['verification_checks'] == rows
    assert view['validity'] == ['supported']  # A new sample does not change the original arithmetic.


@pytest.mark.parametrize('updates', [
    {'kind': 'new_data_replication', 'collection': 'Original data copied again.'},
    {'check_data': 'new sample'}, {'same_procedure': False},
    {'kind': 'new_data_replication', 'check_data': 'sample B'},  # no collection provenance
    {'kind': 'artifact_access'},  # access is not a completed result comparison
    {'status': 'not_checked'},  # still carries an observed outcome
    {'claim_id': 'absent'}, {'basis': 'certified'}, {'comparison_rule': ''},
])
def test_contradictory_or_unbound_empirical_check_does_not_pass(updates):
    item = research_item()
    item['research_assessment']['verification_checks'] = [dict(empirical_comparison(), **updates)]
    with pytest.raises(ValueError):
        ag.review_record(item)


def test_one_paper_cannot_mix_competition_and_research_judgments(tmp_path):
    path = tmp_path / 'mixed.json'
    path.write_text(json.dumps([research_item(), judge('research-note')]))
    with pytest.raises(ValueError, match='Cannot combine'):
        ag.aggregate([path])


def test_percent_and_spread(tmp_path):
    assert ag.percent(dict.fromkeys(ag.WEIGHTS, 4)) == 100 and ag.percent(dict.fromkeys(ag.WEIGHTS, 0)) == 0
    assert abs(ag.percent(dict.fromkeys(ag.WEIGHTS, 2)) - 50) < 1e-9
    (tmp_path / 'a.json').write_text(json.dumps([judge('P', correctness=4), judge('Q')]))
    (tmp_path / 'b.json').write_text(json.dumps([judge('P', correctness=2), judge('Q')]))
    out = ag.aggregate([tmp_path / 'a.json', tmp_path / 'b.json'])
    assert out['P']['judges'] == 2 and out['P']['unstable_dimensions'] == ['correctness'] and out['P']['percent_range'] == 12.5
    assert out['Q']['percent_mean'] == 50 and out['Q']['unstable_dimensions'] == []
    with pytest.raises(ValueError):
        ag.percent({'coverage': 5, **{k: 2 for k in ag.WEIGHTS if k != 'coverage'}})
    with pytest.raises(ValueError):
        ag.percent({'coverage': 2})


def test_checklist_scores_and_adjust_rules(tmp_path):
    import json
    from evals import aggregate as ag
    dims = list(ag.WEIGHTS)
    def full(met_share):
        return {d: {f'{d}{i}': {'met': i < met_share, 'evidence': 'p1'} for i in range(4)} for d in dims}
    item = {'paper': 'A', 'checklist': full(3)}
    assert set(ag.dimension_scores(item).values()) == {3.0}
    item['adjust'] = {'model': {'value': 1, 'reason': 'insight beyond the routine route'}}
    assert ag.dimension_scores(item)['model'] == 4.0
    item['adjust'] = {'model': {'value': 1, 'reason': ''}}
    import pytest
    with pytest.raises(ValueError):
        ag.dimension_scores(item)
    item['adjust'] = {'model': {'value': 2, 'reason': 'too much'}}
    with pytest.raises(ValueError):
        ag.dimension_scores(item)
    (tmp_path / 'j.json').write_text(json.dumps([{'paper': 'A', 'checklist': full(4)}, {'paper': 'B', 'scores': {d: 2 for d in dims}}]))
    out = ag.aggregate([tmp_path / 'j.json'])
    assert out['A']['percent_mean'] == 100.0 and out['B']['percent_mean'] == 50.0


def test_contest_weights_sum_to_100_and_change_the_score():
    from evals import aggregate as ag
    for w in ag.CONTEST_WEIGHTS.values():
        assert sum(w.values()) == 100 and set(w) == set(ag.WEIGHTS)
    scores = {d: 2 for d in ag.WEIGHTS}
    scores['writing'] = 4
    assert ag.percent(scores, ag.CONTEST_WEIGHTS['mcm']) > ag.percent(scores, ag.CONTEST_WEIGHTS['cumcm'])


def test_every_profile_is_complete_and_unknown_contests_are_refused():
    import pytest
    from evals import aggregate as ag
    for name, profile in ag.PROFILES.items():
        assert sum(profile['weights'].values()) == 100 and set(profile['weights']) == set(ag.WEIGHTS), name
        assert profile['source'] and profile['checked'], name
    assert ag.PROFILES['general']['weights'] == ag.WEIGHTS
    with pytest.raises(ValueError, match='No profile'):
        ag.aggregate([], 'imc')


def test_award_estimates_are_passed_through(tmp_path):
    import json
    from evals import aggregate as ag
    est = {'most_likely': '省一', 'range': ['省二', '国二'], 'basis': 'x', 'calibrated': False}
    (tmp_path / 'j.json').write_text(json.dumps([{'paper': 'A', 'scores': {d: 3 for d in ag.WEIGHTS}, 'award_estimate': est}]))
    assert ag.aggregate([tmp_path / 'j.json'])['A']['award_estimates'] == [est]


def audited_item():
    return {
        'schema_version': 2, 'paper': 'audited',
        'checklist': {dim: {key: {'met': True, 'reviewed': True, 'evidence': 'independent record p1'}
                            for key in keys} for dim, keys in ag.CHECKLIST_IDS.items()},
        'critical_claims': [{'id': 'answer', 'claim': 'x = 2 solves x + 1 = 3',
                             'status': 'supported', 'evidence': 'substitution: 2 + 1 = 3'}],
    }


def test_na_and_unreviewed_have_different_denominators(tmp_path):
    item = audited_item()
    # Hand calculation: robustness 2/3 -> 8/3 -> 2.5; writing 4/5 -> 3.2 -> 3.
    item['checklist']['robustness']['R2'] = {
        'met': None, 'reviewed': True, 'reason': 'no fitted parameters', 'evidence': 'p2 fixed-input table'}
    item['checklist']['robustness']['R3']['met'] = False
    item['checklist']['writing']['W5'] = {
        'met': False, 'reviewed': False, 'reason': 'language review not performed', 'evidence': 'only numerical audit available'}
    scores = ag.dimension_scores(item)
    assert scores['robustness'] == 2.5 and scores['writing'] == 3
    # Remaining weights 80 at 4/4; R contributes 6.25, W contributes 7.5.
    assert ag.percent(scores) == 93.75
    path = tmp_path / 'review.json'
    path.write_text(json.dumps([item]))
    report = ag.aggregate([path])['audited']
    assert report['percent_mean'] == 93.8
    assert report['reviews'][0]['not_applicable_items'] == ['robustness/R2']
    assert report['reviews'][0]['unreviewed_items'] == ['writing/W5']


@pytest.mark.parametrize('mutation', [
    lambda x: x['checklist']['coverage'].pop('C4'),
    lambda x: x['checklist']['coverage']['C1'].pop('met'),
    lambda x: x['checklist']['coverage']['C1'].pop('reviewed'),
    lambda x: x['checklist']['coverage']['C1'].update(met='false'),
    lambda x: x['checklist']['coverage']['C1'].update(met=1),
    lambda x: x['checklist']['coverage']['C1'].update(evidence=' '),
    lambda x: x['checklist']['coverage']['C1'].update(reviewed=False, reason='not checked'),
    lambda x: x['checklist']['robustness']['R2'].update(met=None),
    lambda x: x['checklist']['robustness']['R2'].update(met=None, reviewed=False, reason='unknown'),
    lambda x: x['checklist']['coverage']['C1'].update(met=False, reviewed=False),
    lambda x: x.update(adjust={'model': {'value': True, 'reason': 'not a number'}}),
    lambda x: x.update(adjust={'model': {'value': float('nan'), 'reason': 'invalid'}}),
])
def test_malformed_or_unsubstantiated_checklist_is_refused(mutation):
    item = audited_item()
    mutation(item)
    with pytest.raises(ValueError):
        ag.dimension_scores(item)


def test_whole_dimension_na_does_not_reweight_and_checklist_cannot_be_bypassed():
    item = audited_item()
    for entry in item['checklist']['robustness'].values():
        entry.update(met=None, reason='claimed out of scope')
    item['scores'] = dict.fromkeys(ag.WEIGHTS, 4)
    with pytest.raises(ValueError, match='no applicable'):
        ag.dimension_scores(item)


def test_explicit_half_up_rounding():
    # Nine of sixteen = 2.25/4, exactly between 2 and 2.5.
    legacy = {'checklist': {dim: {str(i): {'met': i < 9, 'evidence': 'p1'}
                                 for i in range(16)} for dim in ag.WEIGHTS}}
    assert set(ag.dimension_scores(legacy).values()) == {2.5}


@pytest.mark.parametrize('value', [True, '4', float('nan'), float('inf'), None, -0.1, 4.1])
def test_direct_legacy_scores_reject_invalid_numeric_values(value):
    with pytest.raises(ValueError):
        ag.dimension_scores(judge('legacy', correctness=value))


def test_counterexample_is_retained_separately_from_high_diagnostic_score(tmp_path):
    item = audited_item()
    # Independent arithmetic witness: 1.523595 > 1.5 + 0.002.
    assert 1.523595 - (1.5 + 0.002) == pytest.approx(0.021595)
    item['critical_claims'] = [{'id': 'feasible', 'claim': 'recommended schedule satisfies spread bound',
        'status': 'refuted', 'evidence': 'replay: 1.523595 > 1.502', 'issue_ids': ['mesh']}]
    item['issues'] = [{'id': 'mesh', 'description': 'fine-grid replay violates bound',
                       'evidence': '1.523595 > 1.502'}]
    for dim, key in [('correctness', 'K3'), ('correctness', 'K4'), ('robustness', 'R3'), ('verifiability', 'V4')]:
        item['checklist'][dim][key].update(met=False, evidence='same mesh counterexample', issue_ids=['mesh'])
    item['award_estimate'] = {'most_likely': 'H', 'range': ['SP', 'M'], 'calibrated': False}
    path = tmp_path / 'counterexample.json'
    path.write_text(json.dumps([item]))
    report = ag.aggregate([path])['audited']
    # K=2.5, R=3, V=3. 25*2.5/4 + 10*3/4 + 15*3/4 + 50 = 84.375.
    assert report['percent_mean'] == 84.4
    assert report['reviews'][0]['validity_status'] == 'refuted'
    assert len(report['reviews'][0]['issues']) == 1
    assert report['award_estimates'] == [item['award_estimate']]


@pytest.mark.parametrize('mutation', [
    lambda x: x.pop('critical_claims'),
    lambda x: x.update(critical_claims='missing'),
    lambda x: x.update(issues={'id': 'wrong shape'}),
    lambda x: x.update(issues=[{'id': 'a', 'description': 'x', 'evidence': 'p1'},
                               {'id': 'a', 'description': 'y', 'evidence': 'p2'}]),
    lambda x: x['critical_claims'][0].update(evidence=''),
    lambda x: x['critical_claims'][0].update(status='correct'),
    lambda x: x['critical_claims'][0].update(issue_ids=['undeclared']),
    lambda x: x['checklist']['correctness']['K4'].update(issue_ids=['undeclared']),
])
def test_invalid_claim_evidence_and_dangling_issue_ids_are_refused(mutation):
    item = audited_item()
    mutation(item)
    with pytest.raises(ValueError):
        ag.review_record(item)


def test_unknown_claim_does_not_become_supported_and_legacy_is_not_certified(tmp_path):
    item = audited_item()
    item['critical_claims'][0].update(status='unverified', evidence='replay missing for this claim')
    path = tmp_path / 'mixed.json'
    path.write_text(json.dumps([item, judge('old')]))
    report = ag.aggregate([path])
    assert report['audited']['percent_mean'] == 100
    assert report['audited']['reviews'][0]['validity_status'] == 'unverified'
    assert report['old']['percent_mean'] == 50
    assert report['old']['reviews'][0]['validity_status'] == 'not_assessed'
    assert report['old']['reviews'][0]['score_source'] == 'legacy_direct'


def test_public_research_reviews_bind_actual_papers_and_keep_nonblind_status():
    import hashlib
    root = Path(__file__).resolve().parents[1]
    files = [root / 'demos' / slug / 'evaluation.json'
             for slug in ('collatz-research', 'domino-research')]
    view = ag.user_view(ag.aggregate(files))
    for path in files:
        record = json.loads(path.read_text())[0]
        assert record['research_assessment']['version'] == hashlib.sha256(
            (root / record['paper']).read_bytes()).hexdigest()
        assert 'non-blind' in record['reviewer']
        assert view[record['paper']]['status'] == 'research_reviewer_assessments'
        assert record['review_evidence']['independent_checks']
        # A classic note does not assert novelty; lack of originality is not a false theorem.
        assert view[record['paper']]['validity'] == ['supported']
