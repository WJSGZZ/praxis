"""Aggregate reviewer diagnostics, not paper correctness or award predictions.

    uv run --locked python -m evals.aggregate [--contest=cumcm|mcm] judge1.json ...
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

WEIGHTS = {'coverage': 10, 'assumptions': 15, 'model': 15, 'correctness': 25, 'robustness': 10, 'writing': 10, 'verifiability': 15}
CHECKLIST_IDS = {dim: [f'{prefix}{i}' for i in range(1, count + 1)] for dim, prefix, count in (
    ('coverage', 'C', 4), ('assumptions', 'A', 5), ('model', 'M', 5),
    ('correctness', 'K', 5), ('robustness', 'R', 4), ('writing', 'W', 5), ('verifiability', 'V', 5))}
PROFILES = json.loads(Path(__file__).with_name('profiles.json').read_text(encoding='utf-8'))
CONTEST_WEIGHTS = {k: v['weights'] for k, v in PROFILES.items() if k != 'general'}
RESEARCH_CRITERIA = ('correctness', 'novelty', 'significance', 'method_depth',
                     'exposition', 'reproducibility')


def _number(value, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be a finite number in {low}-{high}')
    return value


def _text(value, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} needs nonempty text')


def _review_blocks(item: dict) -> dict:
    """Retain optional reading/comparison declarations, without grading them.

    Only recorded shapes and enum/range values are checked. Missing answers,
    references or reasons are not filled in or certified as a completed review;
    reader coverage belongs to reader_packet and pairwise judgments to its own
    protocol. Unknown metadata remains attached to the declaring reviewer.
    """
    out = {}
    if 'reader' in item:
        reader = item['reader']
        if not isinstance(reader, dict):
            raise ValueError('reader must be an object')
        if 'problem_items' in reader:
            rows = reader['problem_items']
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError('reader.problem_items must be a list of objects')
            for row in rows:
                if 'answer_found' in row and row['answer_found'] not in ('yes', 'no'):
                    raise ValueError('reader answer_found must be yes or no')
        out['reader'] = reader
    if 'comparison' in item:
        comparison = item['comparison']
        rows = [comparison] if isinstance(comparison, dict) else comparison
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError('comparison must be an object or list of objects')
        for row in rows:
            if 'preferred' in row and row['preferred'] not in ('self', 'reference', 'tie'):
                raise ValueError('comparison preferred must be self, reference or tie')
            if 'confidence' in row:
                _number(row['confidence'], 'comparison confidence', 0.5, 1)
            if 'reasons' in row:
                if not isinstance(row['reasons'], list):
                    raise ValueError('comparison reasons must be a list')
                for reason in row['reasons']:
                    _text(reason, 'comparison reason')
        out['comparison'] = comparison
    return out


def percent(scores: dict, weights: dict | None = None) -> float:
    weights = WEIGHTS if weights is None else weights
    missing = set(weights) - set(scores)
    if missing:
        raise ValueError(f'Missing dimensions: {sorted(missing)}')
    for k in weights:
        _number(scores[k], f'score for {k}', 0, 4)
    return 100 * sum(weights[k] * scores[k] / 4 for k in weights) / sum(weights.values())


def dimension_scores(item: dict) -> dict:
    """NA is excluded; unreviewed applicable items stay in the denominator."""
    version = item.get('schema_version', 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError('schema_version must be 1 or 2')
    if 'checklist' not in item and version == 1 and 'scores' in item:
        percent(item['scores'])  # Validate direct legacy scores too.
        return {dim: item['scores'][dim] for dim in WEIGHTS}
    checklist = item.get('checklist', {})
    if set(checklist) != set(WEIGHTS):
        raise ValueError('Checklist must contain all seven dimensions')
    if set(item.get('adjust', {})) - set(WEIGHTS):
        raise ValueError('Unknown adjust dimension')
    out = {}
    for dim in WEIGHTS:
        items = checklist[dim]
        if not isinstance(items, dict) or not items:
            raise ValueError(f'No checklist for {dim}')
        if version == 2 and set(items) != set(CHECKLIST_IDS[dim]):
            raise ValueError(f'Checklist IDs for {dim} must be {CHECKLIST_IDS[dim]}')
        met_count = applicable = 0
        for key, entry in items.items():
            if not isinstance(entry, dict) or 'met' not in entry:
                raise ValueError(f'{dim}/{key} needs met')
            met = entry['met']
            if met is not None and type(met) is not bool:
                raise ValueError(f'{dim}/{key}: met must be true, false or null')
            _text(entry.get('evidence'), f'evidence for {dim}/{key}')
            if version == 2 and 'reviewed' not in entry:
                raise ValueError(f'{dim}/{key}: schema_version 2 needs reviewed')
            reviewed = entry.get('reviewed', True)
            if type(reviewed) is not bool:
                raise ValueError(f'{dim}/{key}: reviewed must be boolean')
            if met is None:
                _text(entry.get('reason'), f'NA reason for {dim}/{key}')
                if not reviewed:
                    raise ValueError('NA applicability must be reviewed')
                continue
            applicable += 1
            if not reviewed:
                _text(entry.get('reason'), f'unreviewed reason for {dim}/{key}')
                if met:
                    raise ValueError('An unreviewed item cannot be met')
            met_count += met
        if not applicable:
            raise ValueError(f'{dim} has no applicable items; do not silently reweight dimensions')
        # Explicit round-half-up, rather than Python's round-to-even at ties.
        base = math.floor(8 * met_count / applicable + 0.5) / 2
        if dim in item.get('adjust', {}):
            adjust = item['adjust'][dim]
            _text(adjust.get('reason'), f'adjust reason for {dim}')
            base += _number(adjust.get('value'), f'adjust for {dim}', -1, 1)
        out[dim] = min(4.0, max(0.0, base))
    return out


def review_coverage(item: dict) -> dict:
    """Keep explicit review scope separate from legacy scoring defaults."""
    checklist = item.get('checklist', {})
    unreviewed, not_applicable, unknown = [], [], []
    reviewed = 0
    for dim, items in checklist.items():
        for key, entry in items.items():
            detail = {'item': f'{dim}/{key}', 'reason': entry.get('reason'),
                      'evidence': entry.get('evidence')}
            if 'reviewed' not in entry:
                unknown.append({**detail, 'reason': 'Review status not recorded in legacy checklist'})
            elif entry['reviewed'] is False:
                unreviewed.append(detail)
            else:
                reviewed += 1
            if entry['met'] is None:
                not_applicable.append(detail)
    return {'status': 'unknown' if not checklist or unknown else 'partial' if unreviewed else 'recorded',
            'reviewed_item_count': reviewed if checklist else None,
            'unreviewed_items': unreviewed, 'not_applicable_items': not_applicable,
            'unknown_items': unknown,
            'note': 'Checklist review coverage; supported critical claims do not imply other items were reviewed.'
                    if checklist else 'Item-level review coverage was not recorded; do not infer completeness.'}


def review_record(item: dict) -> dict:
    """Validate declarations and retain their scope; never infer mathematical truth."""
    blocks = _review_blocks(item)
    issues = item.get('issues', [])
    if not isinstance(issues, list) or any(not isinstance(issue, dict) for issue in issues):
        raise ValueError('issues must be a list of objects')
    issue_ids = set()
    for issue in issues:
        for field in ('id', 'description', 'evidence'):
            _text(issue.get(field), f'issue {field}')
        # The three grades belong to competition review. Archived research
        # judgments have their own labels (e.g. nonblocking); retain those.
        if ('research_assessment' not in item and 'severity' in issue
                and issue['severity'] not in ('decisive', 'substantive', 'local')):
            raise ValueError('issue severity must be decisive, substantive or local')
        if issue['id'] in issue_ids:
            raise ValueError(f'Duplicate issue id: {issue["id"]}')
        issue_ids.add(issue['id'])
    claims = item.get('critical_claims', [])
    if not isinstance(claims, list) or any(not isinstance(claim, dict) for claim in claims):
        raise ValueError('critical_claims must be a list of objects')
    if item.get('schema_version', 1) == 2 and not claims:
        raise ValueError('schema_version 2 needs explicit critical_claims')
    claim_ids = set()
    for claim in claims:
        for field in ('id', 'claim', 'evidence'):
            _text(claim.get(field), f'critical claim {field}')
        if claim['id'] in claim_ids:
            raise ValueError(f'Duplicate claim id: {claim["id"]}')
        claim_ids.add(claim['id'])
        if claim.get('status') not in ('supported', 'refuted', 'unverified'):
            raise ValueError('Critical claim status must be supported, refuted or unverified')
    entries = [entry for dim in item.get('checklist', {}).values() for entry in dim.values()]
    research = research_assessment(item) if 'research_assessment' in item else None
    if research:
        entries += list(research['criteria'].values())
    for entry in entries + claims:
        refs = entry.get('issue_ids', [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in issue_ids for ref in refs):
            raise ValueError('issue_ids must reference declared issues in this review')
    status = 'not_assessed'
    if claims:
        status = ('refuted' if any(c['status'] == 'refuted' for c in claims)
                  else 'unverified' if any(c['status'] == 'unverified' for c in claims) else 'supported')
    return dict(schema_version=item.get('schema_version', 1),
                score_source='qualitative_research' if research else
                             ('checklist' if item.get('schema_version', 1) == 2 else 'legacy_checklist')
                             if 'checklist' in item else 'legacy_direct',
                validity_status=status, critical_claims=claims, issues=issues,
                coverage_summary=review_coverage(item),
                overall_note=item.get('overall_note'),
                unreviewed_items=[f'{dim}/{key}' for dim, items in item.get('checklist', {}).items()
                                  for key, entry in items.items() if entry.get('reviewed', True) is False],
                not_applicable_items=[f'{dim}/{key}' for dim, items in item.get('checklist', {}).items()
                                      for key, entry in items.items() if entry['met'] is None],
                **blocks)


def _verification_checks(rows, claim_ids):
    """Check the internal consistency of optional, claim-specific declarations."""
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('research verification_checks must be a list of records')
    for row in rows:
        claim_id = row.get('claim_id')
        if not isinstance(claim_id, str) or claim_id not in claim_ids:
            raise ValueError('verification check must identify a declared critical claim')
        for field in ('actor', 'evidence'):
            _text(row.get(field), f'verification {field}')
        if row.get('basis') not in ('reported', 'examined'):
            raise ValueError('verification basis must distinguish reported from examined')
        kind, status = row.get('kind'), row.get('status')
        if kind == 'artifact_access':
            if status not in ('available', 'restricted', 'unavailable'):
                raise ValueError('artifact_access requires an access status')
            continue
        if kind not in ('same_data_reproduction', 'new_data_replication'):
            raise ValueError('Unknown research verification kind')
        if status == 'not_checked':
            if row.get('observed') is not None:
                raise ValueError('An unperformed comparison cannot report an observed result')
            continue
        if status not in ('consistent', 'inconsistent', 'inconclusive'):
            raise ValueError('verification comparison needs an explicit outcome')
        for field in ('original_data', 'check_data', 'procedure', 'comparison_rule', 'observed'):
            _text(row.get(field), f'verification {field}')
        same_inputs = row['original_data'].strip() == row['check_data'].strip()
        if kind == 'same_data_reproduction':
            if not same_inputs or row.get('same_procedure') is not True:
                raise ValueError('Same-data reproduction requires the original inputs and procedure')
        if kind == 'new_data_replication':
            if same_inputs:
                raise ValueError('New-data replication cannot use the original sample again')
            _text(row.get('collection'), 'new-data collection evidence')


def _closest_work_comparisons(rows, claim_ids):
    """Validate what a reviewer declares about one claim relative to one prior result."""
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('research closest_work_comparisons must be a list of records')
    for row in rows:
        claim_id = row.get('claim_id')
        if not isinstance(claim_id, str) or claim_id not in claim_ids:
            raise ValueError('closest-work comparison must identify a declared critical claim')
        for field in ('source', 'location', 'prior_result', 'scope', 'derivation', 'increment'):
            _text(row.get(field), f'closest-work {field}')
        relation = row.get('relation')
        if relation not in ('implied', 'additional_step', 'conflicts', 'unresolved'):
            raise ValueError('Unknown closest-work relation')
        kind, status = row.get('increment_kind'), row.get('status')
        if kind not in ('none', 'mathematical_result', 'proof', 'method', 'mechanism',
                        'empirical_finding', 'application', 'undetermined'):
            raise ValueError('Unknown closest-work increment kind')
        if status not in ('supported', 'refuted', 'unverified'):
            raise ValueError('Unknown closest-work increment status')
        if (relation == 'unresolved' or kind == 'undetermined') and status != 'unverified':
            raise ValueError('An unresolved comparison or undetermined increment must remain unverified')
        if relation == 'implied' and kind == 'mathematical_result' and status == 'supported':
            raise ValueError('A directly implied claim cannot itself be a supported new mathematical result')
        if kind == 'application' or row.get('application_implication') is not None:
            _text(row.get('application_implication'), 'closest-work application_implication')


def research_assessment(item: dict) -> dict:
    """Validate scoped research judgments, without a score or journal certification."""
    if type(item.get('schema_version')) is not int or item['schema_version'] != 2:
        raise ValueError('Research assessment requires schema_version 2')
    if any(key in item for key in ('award_estimate', 'scores', 'checklist', 'adjust')):
        raise ValueError('Research assessment cannot mix competition awards or diagnostics')
    assessment = item['research_assessment']
    if not isinstance(assessment, dict):
        raise ValueError('research_assessment must be an object')
    for field in ('problem', 'version', 'scope', 'target_standard', 'overall_assessment'):
        _text(assessment.get(field), f'research {field}')
    if assessment.get('work_type') not in ('reproduction', 'expository_note',
                                           'original_research', 'development_study'):
        raise ValueError('Unknown research work_type')
    criteria = assessment.get('criteria')
    if not isinstance(criteria, dict) or set(criteria) != set(RESEARCH_CRITERIA):
        raise ValueError(f'Research criteria must be {RESEARCH_CRITERIA}')
    for name, entry in criteria.items():
        if not isinstance(entry, dict) or entry.get('status') not in ('supported', 'refuted', 'unverified'):
            raise ValueError(f'Invalid research criterion status: {name}')
        _text(entry.get('evidence'), f'research {name} evidence')
    for field in ('major_gaps', 'actions'):
        if not isinstance(assessment.get(field), list):
            raise ValueError(f'research {field} needs a list')
        for value in assessment[field]:
            _text(value, f'research {field} item')
    search = assessment.get('novelty_search')
    if not isinstance(search, dict) or type(search.get('completed')) is not bool:
        raise ValueError('research novelty_search needs explicit completed boolean')
    _text(search.get('scope'), 'research novelty search scope')
    if not isinstance(search.get('sources'), list):
        raise ValueError('research novelty search sources needs a list')
    for source in search['sources']:
        _text(source, 'research novelty search source')
    if criteria['novelty']['status'] == 'supported' and not (search['completed'] and search['sources']):
        raise ValueError('Supported novelty requires a completed scoped literature search with sources')
    if assessment.get('verification_checks') is not None:
        _verification_checks(assessment['verification_checks'], {c['id'] for c in item['critical_claims']})
    if assessment.get('closest_work_comparisons') is not None:
        _closest_work_comparisons(assessment['closest_work_comparisons'], {c['id'] for c in item['critical_claims']})
    return assessment


def aggregate(files: list[Path], contest: str | None = None) -> dict:
    if contest and contest not in PROFILES:
        raise ValueError(f'No profile for {contest!r}; known: {sorted(PROFILES)}')
    weights = PROFILES[contest]['weights'] if contest else WEIGHTS
    per_paper: dict[str, list[float]] = {}
    awards: dict[str, list[dict]] = {}
    dims: dict[str, dict[str, list[float]]] = {}
    basis: dict[str, dict[str, set]] = {}
    reviews: dict[str, list[dict]] = {}
    kinds: dict[str, str] = {}
    for path in files:
        for source_index, item in enumerate(json.loads(Path(path).read_text(encoding='utf-8'))):
            is_research = 'research_assessment' in item
            kind = 'research' if is_research else 'competition_diagnostic'
            if item['paper'] in kinds and kinds[item['paper']] != kind:
                raise ValueError('Cannot combine research and competition reviews for one paper')
            kinds[item['paper']] = kind
            scores = None if is_research else dimension_scores(item)
            record = review_record(item)
            record['source'] = str(path)
            record['source_record_index'] = source_index
            record['review_id'] = f'review-{len(reviews.get(item["paper"], [])) + 1}'
            record['reviewer'] = item.get('reviewer', item.get('judge'))
            record['scope'] = item.get('scope')
            if 'award_estimate' in item:
                record['award_estimate'] = item['award_estimate']
            if is_research:
                record['research_assessment'] = research_assessment(item)
            reviews.setdefault(item['paper'], []).append(record)
            if 'award_estimate' in item:
                awards.setdefault(item['paper'], []).append(item['award_estimate'])
            if is_research:
                continue
            for k, b in item.get('basis', {}).items():
                basis.setdefault(item['paper'], {}).setdefault(b, set()).add(k)
            per_paper.setdefault(item['paper'], []).append(percent(scores, weights))
            for k, v in scores.items():
                dims.setdefault(item['paper'], {}).setdefault(k, []).append(v)
    out = {}
    for paper, values in per_paper.items():
        spread = {k: max(v) - min(v) for k, v in dims[paper].items()}
        out[paper] = dict(judges=len(values), percent_each=[round(v, 1) for v in values], percent_mean=round(sum(values) / len(values), 1),
                          percent_range=round(max(values) - min(values), 1), unstable_dimensions=sorted(k for k, d in spread.items() if d > 1),
                          basis={b: sorted(v) for b, v in basis.get(paper, {}).items()},
                          award_estimates=awards.get(paper, []), reviews=reviews[paper],
                          score_kind='uncalibrated_diagnostic', diagnostic_only=True, weights=weights)
    for paper, records in reviews.items():
        if kinds[paper] == 'research':
            out[paper] = dict(judges=len(records), score_kind='qualitative_research',
                              reviews=records,
                              note='Scoped reviewer judgments; no numerical grade or journal acceptance estimate.')
    return out


def _award_view(award: dict, contest: str | None) -> dict | None:
    """Validate one scoped declaration; an unknown award system forces abstention."""
    required = {'contest', 'event', 'edition', 'problem', 'version', 'scope', 'target', 'basis',
                'gaps', 'actions', 'most_likely', 'range', 'calibrated'}
    if not isinstance(award, dict) or not required <= set(award):
        return None  # Preserve legacy awards internally, without inventing their scope.
    for field in ('contest', 'event', 'edition', 'problem', 'version', 'scope', 'basis'):
        _text(award[field], f'award {field}')
    if contest and contest != 'general' and award['contest'] != contest:
        raise ValueError('Award contest does not match the selected profile')
    if award['contest'] == 'mcm' and award['event'] not in ('MCM', 'ICM'):
        raise ValueError('Specify MCM or ICM as the event')
    target = award['target']
    if target is not None:
        _text(target, 'award target')
    # Explicit null is canonical; retain the previous documented Chinese sentinel.
    target = None if target in (None, '未设定', 'unset') else target
    if award['most_likely'] is not None:
        _text(award['most_likely'], 'award most_likely')
    for field in ('range', 'gaps', 'actions'):
        if not isinstance(award[field], list):
            raise ValueError(f'award {field} needs a list')
        for value in award[field]:
            _text(value, f'award {field} item')
    from evals.competitions import lookup
    edition_record = lookup(award['contest'], award['event'], award['edition'])
    levels = edition_record.get('award_system')
    labels = award['range'] + ([award['most_likely']] if award['most_likely'] is not None else [])
    if target is not None:
        labels.append(target)
    if levels and any(label not in levels for label in labels):
        raise ValueError('Award label (including target) does not belong to the exact contest edition record')
    if type(award['calibrated']) is not bool:
        raise ValueError('award calibrated must be boolean')
    if award['calibrated']:
        _text(award.get('calibration_evidence'), 'award calibration_evidence')
        if not levels:
            raise ValueError('Cannot declare calibrated awards without a verified edition award system')
    assessment = {key: award[key] for key in (
        'most_likely', 'range', 'basis', 'gaps', 'actions',
        'contest', 'event', 'edition', 'problem', 'version', 'scope', 'calibrated')}
    assessment.update(target=target, target_status='unset' if target is None else 'set',
                      award_system_status='verified' if levels else 'unverified',
                      assessment_status='reviewer_estimate' if award['most_likely'] is not None or award['range'] else 'abstained')
    if edition_record.get('award_system_scope'):
        assessment['award_system_scope'] = edition_record['award_system_scope']
    if award['calibrated']:
        assessment['calibration_evidence'] = award['calibration_evidence']
    if not levels:
        # Keep the proposal for audit, but never present unchecked labels as an estimate.
        assessment['unverified_proposal'] = {
            'target': target, 'most_likely': award['most_likely'], 'range': award['range']}
        assessment.update(target=None, target_status='unset' if target is None else 'unverified',
                          most_likely=None, range=[], assessment_status='abstained_unverified_award_system')
    return assessment


def user_view(report: dict, contest: str | None = None) -> dict:
    """Award-first view, with each review's mathematical evidence kept associated."""
    out = {}
    for paper, result in report.items():
        if result.get('score_kind') == 'qualitative_research':
            records = result['reviews']
            out[paper] = dict(status='research_reviewer_assessments',
                assessments=[dict(r['research_assessment'], review_id=r['review_id'],
                                  source=r.get('source'), reviewer=r.get('reviewer'),
                                  verification_checks=r['research_assessment'].get('verification_checks'),
                                  closest_work_comparisons=r['research_assessment'].get('closest_work_comparisons'))
                             for r in records],
                reviews=records, validity=[r['validity_status'] for r in records],
                note='研究意见按稿件版本、主张和审读范围呈现。verification_checks 或 closest_work_comparisons 为 null 表示该类检查未记录。')
            continue
        assessments, reviews = [], []
        has_attached_awards = any('award_estimate' in r for r in result['reviews'])
        for index, record in enumerate(result['reviews'], 1):
            review_id = record.get('review_id', f'review-{index}')
            assessment = _award_view(record['award_estimate'], contest) if 'award_estimate' in record else None
            if assessment is not None:
                assessment.update(review_id=review_id, source=record.get('source'), reviewer=record.get('reviewer'))
                assessments.append(assessment)
            reviews.append({
                'review_id': review_id, 'source': record.get('source'),
                'source_record_index': record.get('source_record_index'), 'reviewer': record.get('reviewer'),
                'scope': record.get('scope') or (assessment['scope'] if assessment else None),
                'validity_status': record['validity_status'],
                'critical_claims': record.get('critical_claims', []), 'issues': record.get('issues', []),
                'award_assessment': assessment, 'overall_note': record.get('overall_note'),
                'unreviewed_items': record.get('unreviewed_items', []),
                'not_applicable_items': record.get('not_applicable_items', []),
                'coverage_summary': record.get('coverage_summary') or {
                    'status': 'unknown', 'reviewed_item_count': None,
                    'unreviewed_items': [{'item': key, 'reason': 'Reason unavailable in legacy report'}
                                         for key in record.get('unreviewed_items', [])],
                    'not_applicable_items': [{'item': key, 'reason': 'Reason unavailable in legacy report'}
                                             for key in record.get('not_applicable_items', [])],
                    'unknown_items': [], 'note': 'Full item-level coverage unavailable in legacy report.'},
                **{field: record[field] for field in ('reader', 'comparison') if field in record},
            })
        if not has_attached_awards:
            # Old aggregate reports lack the association: do not guess by array position.
            for award in result.get('award_estimates', []):
                assessment = _award_view(award, contest)
                if assessment is not None:
                    assessment.update(review_id=None, association_status='unavailable_in_legacy_report')
                    assessments.append(assessment)
        unknown_system = any(a['award_system_status'] == 'unverified' for a in assessments)
        status = ('award_system_unverified' if assessments and all(
                    a['award_system_status'] == 'unverified' for a in assessments)
                  else 'reviewer_estimates' if assessments else 'insufficient_scoped_award_evidence')
        out[paper] = {'contest': contest or 'general', 'assessments': assessments,
                      'status': status, 'reviews': reviews,
                      'validity': [r['validity_status'] for r in reviews],
                      'note': ('部分或全部届次的奖项体系未核实，相关意见暂不判断档次；保留原提议供核查。' if unknown_system
                               else '各评委估计与主张证据分别保留；未建立诊断分与奖项的固定换算。' if assessments
                               else '暂不判断奖项：缺少具体届次、题目、版本、范围或评审依据。')}
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--contest', choices=sorted(PROFILES), help='diagnostic weight profile')
    parser.add_argument('--view', choices=('user', 'internal'),
                        help='default: user for a non-general contest, internal otherwise')
    parser.add_argument('files', nargs='+', type=Path, help='one or more reviewer JSON files')
    # Preserve --view between file names as well as the original equals forms.
    args = parser.parse_intermixed_args(argv)
    view = args.view or ('user' if args.contest and args.contest != 'general' else 'internal')
    result = aggregate(args.files, args.contest)
    print(json.dumps(user_view(result, args.contest) if view == 'user' else result, ensure_ascii=True, indent=1))


if __name__ == '__main__':
    main()
