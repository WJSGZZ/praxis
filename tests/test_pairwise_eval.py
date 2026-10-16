"""Synthetic-only protocol tests; never open the private corpus."""
import copy
from collections import Counter
import json
import math
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from scripts import pairwise_eval as pe


def pdf(path, text):
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    stream = DecodedStreamObject()
    escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    stream.set_data(('BT /F1 11 Tf 20 760 Td ' + ' 0 -14 Td '.join(f'({line}) Tj' for line in escaped.splitlines()) + ' ET').encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.write(path)


def build_corpus(tmp_path, count=8, awards=('O', 'O', 'M', 'H')):
    papers, contexts = [], []
    names = [f"MCM-{2010 + i}-{('ABC'[i % 3])}" for i in range(count)]
    for i, problem in enumerate(names):
        year = int(problem.split('-')[1])
        context = {'problem': problem, 'year': year}
        for kind in ('statement', 'rules', 'anchor'):
            path = tmp_path / f'{problem}-{kind}.txt'
            path.write_text(f'Synthetic {problem} {kind}. Find a feasible allocation and justify the result.')
            item = {'path': str(path), 'sha256': pe.sha256(path), 'year': year,
                    'completeness': 'complete', 'limitations': [],
                    'source_url': f'https://example.invalid/synthetic/{problem}/{kind}',
                    'source_sha256': pe.sha256(path)}
            if kind == 'rules':
                item['contest'] = 'MCM'
            else:
                item['problem'] = problem
            if kind == 'anchor':
                item['anchor_level'] = 'generic' if i % 2 else 'official'
            context[kind] = item
        contexts.append(context)
        for j, award in enumerate(awards):
            team = str(900000 + i * 10 + j)
            path = tmp_path / f'{problem}-{team}.pdf'
            text = (f'Team Control Number: {team}\nExample University\nSynthetic allocation analysis\n'
                    f'Our capacity is {j + 2} and the feasible plan uses two units.\n'
                    'We compare a baseline with an improved allocation under the same budget.\n'
                    'Acknowledgments\nWe thank Example University for the prize.\nReferences\nA synthetic source.')
            pdf(path, text)
            papers.append({'problem': problem, 'year': year, 'team': team, 'award': award,
                'local_path': str(path), 'sha256': pe.sha256(path), 'version': 'unknown',
                'use': 'evaluation_candidate', 'school': 'Example University'})
    papers += [{'use': 'excluded_reused', 'award': 'O', 'local_path': '/must-not-open-old.pdf'},
               {'use': 'evaluation_candidate', 'award': 'F', 'local_path': '/must-not-open-F.pdf'},
               {'use': 'evaluation_candidate', 'award': 'S', 'local_path': '/must-not-open-S.pdf'}]
    index, ctx = tmp_path / 'index.json', tmp_path / 'contexts.json'
    pe.write_json(index, {'schema': 1, 'papers': papers})
    pe.write_json(ctx, {'schema': 1, 'problems': contexts})
    return tmp_path, index, ctx


@pytest.fixture
def corpus(tmp_path):
    return build_corpus(tmp_path)


@pytest.fixture
def packet(corpus):
    root, index, ctx = corpus
    source, key = root / 'packet', root / 'private' / 'key.json'
    receipt = pe.make_pairs(index, ctx, source, key, root)
    return root, source, key, receipt


def returned(packet, destination, judge=None, swap=False, behavior='O', abstain=False):
    root, source, key_path, _ = packet
    judge = judge or {'id': 'judge-a', 'family': 'GPT', 'instance': 'one'}
    key = pe.read_json(key_path)
    first = next(iter(key['pairs']))
    pe.judge_packet(source, destination, judge['id'], judge['family'], judge['instance'], swap, {first})
    data = pe.read_json(destination / 'judgments-template.json')
    data['judgments'] = []
    for pid, pair in key['pairs'].items():
        left, right = ('B', 'A') if swap else ('A', 'B')
        high = next((p for p in pair['aliases'].values() if key['papers'][p]['award'] == 'O'), pair['aliases'][left])
        chosen = high if behavior in {'O', 'alternating'} else pair['aliases'][left]
        if behavior == 'alternating' and pair['kind'] == 'O_vs_MH' and pair['problem'].split('-')[1] in {'2010', '2011'}:
            chosen = pair['aliases'][right] if chosen == pair['aliases'][left] else pair['aliases'][left]
        data['judgments'].append({'pair_id': pid, 'presentation_id': pair['presentations']['swapped' if swap else 'normal'],
            'left': left, 'right': right, 'fresh_instance': judge['instance'] + '-' + pid,
            'preferred': 'abstain' if abstain else 'left' if chosen == pair['aliases'][left] else 'right', 'confidence': .75,
            'reasons': [{'left_location': 'page 001 L00003', 'right_location': 'page 001 L00003', 'reason': f'Synthetic comparison {n}'} for n in range(3)],
            'mechanical_findings': [{'finding': 'Synthetic possible error', 'status': 'unconfirmed'}]})
    # Merged coordinator outputs are kept outside every judge input directory.
    result = destination.parent / (destination.name + '-judgments.json')
    pe.write_json(result, data)
    return result


def test_pairs_complete_controls_randomized_and_no_label_metadata(packet):
    root, source, key_path, receipt = packet
    assert receipt['pair_kinds'] == {'O_vs_MH': 32, 'O_vs_O': 8, 'MH_vs_MH': 8}
    assert receipt['pairs'] == 48
    key, safe = pe.read_json(key_path), pe.read_json(source / 'pairs.json')
    assert receipt['text_extraction']['actual_backend_papers'] == {'pdfium': 32}
    assert key['text_extraction'] == receipt['text_extraction']
    assert all(p['text_extraction']['requested_backend'] == 'pdfium' and
               p['text_extraction']['actual_backends'] == ['pdfium'] for p in key['papers'].values())
    assert safe['key_sha256'] == pe.sha256(key_path)
    assert not key_path.is_relative_to(source)
    assert {p['award'] for p in key['papers'].values()} == {'O', 'M', 'H'}
    assert {key['papers'][p['left']]['award'] == 'O' for p in safe['pairs'] if key['pairs'][p['pair_id']]['kind'] == 'O_vs_MH'} == {True, False}
    for path in source.rglob('*'):
        if path.is_file():
            text = path.read_text()
            assert not any(token in text for token in ('Example University', '900000', '"award"', '"team"', '"source"'))
    second = root / 'packet-second'
    pe.make_pairs(root / 'index.json', root / 'contexts.json', second, root / 'secret2.json', root)
    # Security decision: the public seed must not reproduce blinding; private sealed decisions do.
    assert (source / 'pairs.json').read_bytes() != (second / 'pairs.json').read_bytes()
    assert set(pe.read_json(second / 'pairs.json')['papers']).isdisjoint(safe['papers'])
    assert pe.read_json(key_path)['pairs'] == key['pairs']


def test_audit_seed_replay_and_degree_attack_have_no_judge_graph(tmp_path):
    root, index, ctx = build_corpus(tmp_path, 10, ('O', 'O', 'M', 'H', 'M'))
    source, key_path = root / 'coordinator', root / 'key.json'
    pe.make_pairs(index, ctx, source, key_path, root, seed=pe.SEED)
    key, coordinator = pe.read_json(key_path), pe.read_json(source / 'pairs.json')
    assert coordinator['coordinator_only'] is True
    degree = Counter(pid for p in key['pairs'].values() for pid in (p['left'], p['right']))
    # Preserve the audit's structural decision: the full graph really does leak
    # all 50 roles, so removing a label field cannot make it a judge input.
    assert all((degree[pid] == 4) == (paper['award'] == 'O') for pid, paper in key['papers'].items())
    assert len(degree) == 50
    chosen = next(iter(key['pairs']))
    for swap, name in ((False, 'judge-one'), (True, 'judge-two')):
        dest = root / name
        pe.judge_packet(source, dest, name, 'GPT', name, swap, {chosen})
        manifest = pe.read_json(dest / 'pair.json')
        assert set(manifest) == {'schema', 'key_sha256', 'pair_id', 'presentation_id', 'problem', 'left', 'right', 'readiness', 'files'}
        assert set(manifest['files']) == {'A.txt', 'B.txt', 'context.json'}
        for alias, pid in key['pairs'][chosen]['aliases'].items():
            assert pe.sha256(dest / f'{alias}.txt') == key['papers'][pid]['anonymous_sha256']
        exported = '\n'.join(p.read_text() for p in dest.iterdir())
        assert not any(token in exported for token in ('statistical_seed', 'planned_judgments', 'pair_kinds', 'coordinator_only', 'O_vs_', 'MH_vs_', 'selected_problems'))
        assert not any(pid in exported for pid in key['papers'])
        assert not any(pid in exported for pid in key['pairs'] if pid != chosen)
    pe.make_pairs(index, ctx, root / 'second', root / 'second-key.json', root, seed=pe.SEED)
    second = pe.read_json(root / 'second-key.json')
    assert set(key['pairs']).isdisjoint(second['pairs'])
    assert set(key['papers']).isdisjoint(second['papers'])
    with pytest.raises(ValueError, match='exactly one'):
        pe.judge_packet(source, root / 'full-graph-judge', 'a', 'GPT', 'a')
    with pytest.raises(ValueError, match='exactly one'):
        pe.judge_packet(source, root / 'two-pair-judge', 'a', 'GPT', 'a', selected=set(list(key['pairs'])[:2]))


def test_anonymization_variants_headers_school_ack_and_sparse():
    pages = [{'text': 'Team # 1 2 3 4 5\nRepeated Header\nThe selected team is １２-３４-５.\nExample University\nAcknowledgements\nSecret name\nReferences\nReal source\nPage 1 of 2'},
             {'text': 'Repeated Header\nIndependent body and valid allocation\nPage 2 of 2'}]
    text, report = pe.anonymize_pages(pages, '12345', ['Example University'])
    for token in ('12345', '12-34-5', 'Repeated Header', 'Example University', 'Secret name', 'Acknowledgements'):
        assert token not in text
    assert 'References' in text and 'Real source' in text
    assert report['redactions']['team_variants'] == 1
    assert report['sparse_pages'] == [2]
    with pytest.raises(ValueError, match='No manuscript text'):
        pe.anonymize_pages([{'text': 'Team Control Number: 12345'}], '12345')


@pytest.mark.parametrize('marker', ['校苑数模', '微信公众号', '获取更多资讯'])
def test_anonymization_removes_exact_publisher_markers(marker):
    text, report = pe.anonymize_pages([{'text': marker + '\nA valid scientific result remains.'}], '12345')
    assert marker not in text
    assert text == '[page 001]\nL00002: A valid scientific result remains.\n'
    assert report['redactions']['publisher_markers'] == 1


def test_anonymization_preserves_science_and_urls_beside_publisher_markers():
    scientific = 'Considering water storage, we derive an approximation to sim\ufffe'
    reference = 'Reference https://example.org/data?q=water&year=2022'
    chinese = '扩散系数满足守恒方程，中文科学内容与正常参考文献保留。'
    normalized_chinese = '扩散系数满足守恒方程,中文科学内容与正常参考文献保留。'
    pages = [{'text': scientific + '校苑数模\n微信公众号' + reference + '\n' + chinese + '获取更多资讯'}]
    text, report = pe.anonymize_pages(pages, '12345')
    assert text == f'[page 001]\nL00002: {scientific}\nL00003: {reference}\nL00004: {normalized_chinese}\n'
    assert report['redactions']['publisher_markers'] == 3
    assert not any(marker in text for marker in ('校苑数模', '微信公众号', '获取更多资讯'))


def test_pairwise_requests_pdfium_for_every_candidate(corpus, monkeypatch):
    from scripts.pdf_text import extract_pages
    root, index, ctx = corpus
    calls = []
    def tracked(path, *, text_backend='auto'):
        calls.append(text_backend)
        return extract_pages(path, text_backend=text_backend)
    monkeypatch.setattr('scripts.pdf_text.extract_pages', tracked)
    receipt = pe.make_pairs(index, ctx, root / 'coordinator', root / 'key.json', root)
    assert calls == ['pdfium'] * 32
    assert receipt['text_extraction']['requested_backend'] == 'pdfium'


def test_pairwise_rejects_mixed_extraction_backend_instead_of_silent_fallback(corpus, monkeypatch):
    root, index, ctx = corpus
    monkeypatch.setattr('scripts.pdf_text.extract_pages', lambda *a, **kw:
        [{'text': 'Synthetic body', 'body_size': 12, 'text_backend': 'pypdf'}])
    with pytest.raises(ValueError, match='Uniform PDFium extraction required'):
        pe.make_pairs(index, ctx, root / 'coordinator', root / 'key.json', root)
    assert not (root / 'key.json').exists()


def test_key_inside_packet_rejected_before_manuscript_read(corpus, monkeypatch):
    root, index, ctx = corpus
    monkeypatch.setattr('scripts.pdf_text.extract_pages', lambda p: pytest.fail('must not extract'))
    with pytest.raises(ValueError, match='outside'):
        pe.make_pairs(index, ctx, root / 'packet', root / 'packet' / 'key.json', root)


@pytest.mark.parametrize('damage', ['missing_context', 'year', 'problem', 'sha', 'empty', 'missing_rules', 'anchor_level', 'completeness'])
def test_context_fail_closed_before_manuscript_read(corpus, monkeypatch, damage):
    root, index, ctx = corpus
    data = pe.read_json(ctx)
    if damage == 'missing_context':
        data['problems'].pop()
    elif damage == 'year':
        data['problems'][0]['rules']['year'] = 2027
    elif damage == 'problem':
        data['problems'][0]['anchor']['problem'] = 'MCM-2027-A'
    elif damage == 'sha':
        data['problems'][0]['rules']['sha256'] = '0' * 64
    elif damage == 'empty':
        path = Path(data['problems'][0]['rules']['path'])
        path.write_text('')
        data['problems'][0]['rules']['sha256'] = pe.sha256(path)
    elif damage == 'missing_rules':
        del data['problems'][0]['rules']
    elif damage == 'anchor_level':
        del data['problems'][0]['anchor']['anchor_level']
    else:
        del data['problems'][0]['rules']['completeness']
    pe.write_json(ctx, data)
    monkeypatch.setattr('scripts.pdf_text.extract_pages', lambda p: pytest.fail('must not extract'))
    with pytest.raises(ValueError):
        pe.make_pairs(index, ctx, root / 'packet', root / 'key.json', root)
    assert not (root / 'packet').exists()


def test_minimum_no_silent_threshold_reduction(corpus):
    root, index, ctx = corpus
    data = pe.read_json(index)
    data['papers'] = data['papers'][:4]
    pe.write_json(index, data)
    with pytest.raises(ValueError, match='minimum'):
        pe.make_pairs(index, ctx, root / 'packet', root / 'key.json', root)


def test_external16_is_stratified_from_all_pairs_and_self_contained(packet):
    root, source, key, _ = packet
    receipt = pe.export_packet(source, root / 'external', 'external')
    folders = [p for p in (root / 'external').iterdir() if p.is_dir()]
    manifests = [pe.read_json(p / 'pair.json') for p in folders]
    assert len(receipt['selection']) == len(set(receipt['selection'])) == len(folders) == 16
    assert len({p['problem'] for p in manifests}) == 8
    assert set(Counter(p['problem'] for p in manifests).values()) == {2}
    assert not list((root / 'external').rglob('key.json'))
    for folder, manifest in zip(folders, manifests):
        assert set(manifest['files']) == {'A.txt', 'B.txt', 'context.json'}
        assert not (folder / 'pairs.json').exists()
        for path in folder.iterdir():
            text = path.read_text()
            assert not any(token in text for token in ('"award"', '"source"', '"team"', '"seed"', '"statistical_seed"', str(key)))
            assert not any(pid in text for pid in pe.read_json(key)['papers'])
    assert not (root / 'external' / 'selection.json').exists()
    assert pe.stratified_sample(pe.read_json(source / 'pairs.json')['pairs']) == receipt['selection']
    with pytest.raises(ValueError, match='do not pad'):
        pe.stratified_sample(pe.read_json(source / 'pairs.json')['pairs'][:15])


def test_packet_extra_labels_and_path_escape_rejected(packet):
    root, source, _, _ = packet
    data = pe.read_json(source / 'pairs.json')
    data['award'] = 'O'
    pe.write_json(source / 'pairs.json', data)
    with pytest.raises(ValueError, match='metadata'):
        pe.export_packet(source, root / 'external')
    del data['award']
    next(iter(data['papers'].values()))['path'] = '../index.json'
    pe.write_json(source / 'pairs.json', data)
    with pytest.raises(ValueError, match='escapes'):
        pe.export_packet(source, root / 'external')


def test_packet_tamper_is_detected_and_key_symlink_is_rejected(packet, corpus):
    root, source, _, _ = packet
    path = next((source / 'papers').glob('*.txt'))
    path.write_text(path.read_text() + '\nModified manuscript\n')
    with pytest.raises(ValueError, match='SHA256 mismatch'):
        pe.export_packet(source, root / 'bad-export')
    other, index, ctx = corpus
    target = other / 'judge-symlink'
    target.mkdir()
    link = other / 'key-link'
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='outside'):
        pe.make_pairs(index, ctx, target, link / 'key.json', other)


def test_award_and_author_banner_variants_are_redacted():
    text, report = pe.anonymize_pages([{'text': 'O-Award\nAward Level: H\nMCM M award\nAuthors: Identifiable Name\nScientific allocation under fixed resources.'}], '12345')
    assert report['redactions']['award_lines'] == 3
    assert 'Identifiable' not in text
    assert 'Scientific allocation' in text


def test_partial_generic_anchor_limits_and_provenance_are_visible(corpus):
    root, index, ctx = corpus
    data = pe.read_json(ctx)
    data['problems'][0]['anchor'].update(anchor_level='generic', completeness='partial',
        limitations=['Generic task guidance; no original-year judges commentary.'])
    pe.write_json(ctx, data)
    source, key = root / 'packet', root / 'private-key.json'
    pe.make_pairs(index, ctx, source, key, root)
    selected = {next(p['pair_id'] for p in pe.read_json(source / 'pairs.json')['pairs'] if p['problem'] == 'MCM-2010-A')}
    pe.judge_packet(source, root / 'judge', 'test', 'synthetic', 'one', selected=selected)
    request = root / 'judge' / 'request.md'
    assert 'Generic task guidance' in request.read_text()
    metadata = pe.read_json(root / 'judge' / 'context.json')['resource_metadata']
    assert metadata['rules']['source_url'].startswith('https://example.invalid/')
    assert metadata['anchor']['completeness'] == 'partial'


def test_partial_rules_prepare_reviewable_packet_without_claiming_formal_readiness(corpus):
    root, index, ctx = corpus
    data = pe.read_json(ctx)
    data['problems'][0]['rules'].update(completeness='partial',
        limitations=['Only original submission instructions; complete historical rules unavailable.'])
    pe.write_json(ctx, data)
    source, key = root / 'packet', root / 'private-key.json'
    receipt = pe.make_pairs(index, ctx, source, key, root)
    assert receipt['readiness']['ready_for_formal_eval'] is False
    assert receipt['readiness']['complete_context_problems'] == 7
    assert receipt['readiness']['blockers'][0]['problem'] == 'MCM-2010-A'
    assert receipt['anonymous_word_count'] > 0
    assert receipt['pair_manuscript_words_one_pass'] > receipt['anonymous_word_count']
    assert pe.read_json(key)['readiness'] == pe.read_json(source / 'pairs.json')['readiness']
    selected = {next(p['pair_id'] for p in pe.read_json(source / 'pairs.json')['pairs'] if p['problem'] == 'MCM-2010-A')}
    pe.judge_packet(source, root / 'judge', 'test', 'synthetic', 'one', selected=selected)
    requests = [(root / 'judge' / 'request.md').read_text()]
    assert all('Formal evaluation context ready: false' in r for r in requests)
    assert any('complete historical rules unavailable' in r for r in requests)


def test_original_single_problem_pdf_supplements_figures_without_upgrading_rules(corpus):
    root, index, ctx = corpus
    original = root / 'original-problem-only.pdf'
    pdf(original, 'Synthetic original problem A. The map has three regions. Figure one is a triangle.')
    data = pe.read_json(ctx)
    statement = data['problems'][0]['statement']
    statement.update(source_file=str(original), source_sha256=pe.sha256(original), source_scope='single_problem',
                     completeness='partial', limitations=['Maps are absent from extracted text; data appendix not supplied.'])
    data['problems'][0]['rules'].update(completeness='partial', limitations=['Only original submission instructions available.'])
    pe.write_json(ctx, data)
    source, key = root / 'coordinator', root / 'key.json'
    receipt = pe.make_pairs(index, ctx, source, key, root)
    chosen = next(p['pair_id'] for p in pe.read_json(source / 'pairs.json')['pairs'] if p['problem'] == 'MCM-2010-A')
    pe.judge_packet(source, root / 'judge', 'one', 'GPT', 'fresh-one', selected={chosen})
    manifest = pe.read_json(root / 'judge' / 'pair.json')
    assert set(manifest['files']) == {'A.txt', 'B.txt', 'context.json', 'problem-original.pdf'}
    assert (root / 'judge' / 'problem-original.pdf').read_bytes() == original.read_bytes()
    assert manifest['files']['problem-original.pdf'] == pe.sha256(original)
    assert 'Read problem-original.pdf' in (root / 'judge' / 'request.md').read_text()
    assert 'does not mark the historical rules or data attachments complete' in (root / 'judge' / 'request.md').read_text()
    assert receipt['readiness']['ready_for_formal_eval'] is False
    metadata = pe.read_json(root / 'judge' / 'context.json')['resource_metadata']
    assert metadata['statement']['completeness'] == metadata['rules']['completeness'] == 'partial'
    assert metadata['statement']['source_sha256'] == pe.sha256(original)
    assert 'source_file' not in json.dumps(metadata)
    attachment = source / pe.read_json(source / 'pairs.json')['statement_attachments']['MCM-2010-A']['path']
    attachment.write_bytes(b'tampered original problem')
    with pytest.raises(ValueError, match='SHA256 mismatch'):
        pe.judge_packet(source, root / 'tampered', 'one', 'GPT', 'fresh-two', selected={chosen})


def test_wrong_original_statement_pdf_hash_rejected_before_manuscript_read(corpus, monkeypatch):
    root, index, ctx = corpus
    original = root / 'original.pdf'
    pdf(original, 'Synthetic original single problem statement with a map.')
    data = pe.read_json(ctx)
    data['problems'][0]['statement'].update(source_file=str(original), source_sha256='0' * 64, source_scope='single_problem')
    pe.write_json(ctx, data)
    monkeypatch.setattr('scripts.pdf_text.extract_pages', lambda p: pytest.fail('candidate body must remain unopened'))
    with pytest.raises(ValueError, match='original statement PDF.*SHA256 mismatch'):
        pe.make_pairs(index, ctx, root / 'coordinator', root / 'key.json', root)


@pytest.mark.parametrize('kind,scope', [('html', 'single_problem'), ('pdf', 'multiple_problems'), ('pdf', None)])
def test_html_multi_problem_and_unknown_scope_sources_are_not_copied(corpus, kind, scope):
    root, index, ctx = corpus
    original = root / ('original.' + kind)
    if kind == 'pdf':
        pdf(original, 'Synthetic multiple or unknown problem statement source.')
    else:
        original.write_text('<html>Problem A and problem B together</html>')
    data = pe.read_json(ctx)
    data['problems'][0]['statement'].update(source_file=str(original), source_sha256=pe.sha256(original), source_scope=scope)
    pe.write_json(ctx, data)
    source, key = root / 'coordinator', root / 'key.json'
    pe.make_pairs(index, ctx, source, key, root)
    chosen = next(p['pair_id'] for p in pe.read_json(source / 'pairs.json')['pairs'] if p['problem'] == 'MCM-2010-A')
    pe.judge_packet(source, root / 'judge', 'one', 'GPT', 'fresh-one', selected={chosen})
    assert not list((root / 'judge').glob('*.pdf'))
    metadata = pe.read_json(root / 'judge' / 'context.json')['resource_metadata']['statement']
    assert metadata['original_pdf']['available'] is False
    assert 'not copied' in metadata['original_pdf']['reason'] or kind == 'html'


def test_accuracy_cluster_bootstrap_strata_and_penalized_separation(packet):
    root, _, key, _ = packet
    result = returned(packet, root / 'judge-a', behavior='alternating')
    report = pe.fit(key, [result])
    assert report['accuracy']['accuracy'] == .75
    assert report['accuracy']['n'] == 32
    assert report['accuracy']['cluster_bootstrap_95']['interval'] == [.375, 1.0]
    assert report['bootstrap']['replicates'] == 1000
    assert report['BT']['method'] == 'penalized_BT'
    assert report['BT']['ridge'] == 1
    assert len(report['stratified_accuracy']['problem']) == 8
    assert set(report['stratified_accuracy']['anchor_level']) == {'generic', 'official'}
    assert list(report['stratified_accuracy']['version']) == ['unknown']
    assert all(abs(sum(b['scores'].values())) < 1e-8 for b in report['BT']['problems'].values())
    assert any(b['separated_or_disconnected'] for b in report['BT']['problems'].values())
    assert pe.fit(key, [result]) == report
    mle = pe.fit(key, [result], ridge=0)
    assert all(b['status'] == 'no_finite_identifiable_MLE' for b in mle['BT']['problems'].values())
    assert mle['BT']['O_minus_MH_mean'] is None


def test_no_samples_abstention_and_findings_do_not_set_preference(packet):
    root, _, key, _ = packet
    result = returned(packet, root / 'abstain', abstain=True)
    report = pe.fit(key, [result])
    assert report['accuracy']['accuracy'] == 0
    assert report['accuracy']['decided_accuracy'] is None
    assert all(p['status'] == 'no_decided_observations' for p in report['BT']['problems'].values())
    assert report['length_preference']['pearson'] is None
    data = pe.read_json(result)
    data['judgments'] = []
    pe.write_json(result, data)
    empty = pe.fit(key, [result])
    assert empty['status'] == 'no_observations'
    assert empty['accuracy']['accuracy'] is None
    assert empty['accuracy']['cluster_bootstrap_95']['interval'] is None


def test_small_cluster_and_degenerate_outputs_are_explicit(packet):
    root, _, key, _ = packet
    result = returned(packet, root / 'small')
    data = pe.read_json(result)
    secret = pe.read_json(key)
    data['judgments'] = [row for row in data['judgments'] if secret['pairs'][row['pair_id']]['problem'] == 'MCM-2010-A']
    pe.write_json(result, data)
    report = pe.fit(key, [result])
    assert report['accuracy']['n'] == 4
    assert report['accuracy']['cluster_bootstrap_95']['interval'] is None
    assert report['BT']['cluster_bootstrap_95']['interval'] is None
    assert pe._ci([1.] * 1000, 8)['status'] == 'degenerate_point_interval'
    assert pe._ci([.5, 1.], 2)['status'] == 'small_cluster_exploratory'


def test_audit_ten_of_160_cannot_pass_preregistered_checks(tmp_path):
    root, index, ctx = build_corpus(tmp_path, 10, ('O', 'O', 'M', 'H', 'M'))
    source, key = root / 'coordinator', root / 'key.json'
    receipt = pe.make_pairs(index, ctx, source, key, root)
    assert receipt['pairs'] == 80
    packet = root, source, key, receipt
    first = returned(packet, root / 'first')
    data, secret = pe.read_json(first), pe.read_json(key)
    one_per_problem = {}
    for row in data['judgments']:
        pair = secret['pairs'][row['pair_id']]
        if pair['kind'] == 'O_vs_MH':
            one_per_problem.setdefault(pair['problem'], row)
    data['judgments'] = list(one_per_problem.values())
    pe.write_json(first, data)
    report = pe.fit(key, [first])
    assert report['accuracy']['accuracy'] == 1
    assert report['accuracy']['cluster_bootstrap_95']['interval'] == [1., 1.]
    assert report['status'] == 'incomplete_observed_subset'
    assert report['coverage']['planned_judgments'] == 160
    assert report['coverage']['observed_judgments'] == report['coverage']['effective_judgments'] == 10
    assert report['coverage']['missing_judgments'] == 150
    assert report['coverage']['completion_fraction'] == 10 / 160
    assert report['coverage']['by_kind']['O_vs_MH']['planned'] == 120
    assert report['coverage']['by_kind']['O_vs_O']['missing'] == 20
    assert report['coverage']['by_kind']['MH_vs_MH']['missing'] == 20
    assert report['predeclared_checks']['accuracy_at_least_0_70'] is None
    assert report['predeclared_checks']['cluster_CI_lower_above_0_5'] is None


def test_two_fresh_opposite_orders_complete_plan_and_repeats_do_not(packet):
    root, _, key, _ = packet
    first = returned(packet, root / 'first')
    second = returned(packet, root / 'second', {'id': 'judge-b', 'family': 'GPT', 'instance': 'two'}, swap=True)
    report = pe.fit(key, [first, second])
    assert report['coverage']['complete'] is True
    assert report['coverage']['planned_judgments'] == report['coverage']['effective_judgments'] == 96
    assert report['coverage']['missing_judgments'] == 0
    assert set(report['coverage']['by_judge_id']) == {'judge-a', 'judge-b'}
    assert report['predeclared_checks']['accuracy_at_least_0_70'] is True
    assert report['predeclared_checks']['cluster_CI_lower_above_0_5'] is True
    assert report['status'] == 'analysed_complete_plan'
    repeated = returned(packet, root / 'same-instance-swap', swap=True)
    partial = pe.fit(key, [first, repeated])
    assert partial['coverage']['effective_judgments'] == 48
    assert partial['coverage']['pairs_with_repeated_ids_or_instances'] == 48
    assert partial['coverage']['complete'] is False
    assert partial['predeclared_checks']['accuracy_at_least_0_70'] is None
    same_order = returned(packet, root / 'same-order', {'id': 'judge-c', 'family': 'GPT', 'instance': 'three'})
    assert pe.fit(key, [first, same_order])['coverage']['complete'] is False
    reused_data = pe.read_json(second)
    for row in reused_data['judgments']:
        row['fresh_instance'] = 'one-context-reused-across-all-pairs'
    pe.write_json(second, reused_data)
    reused = pe.fit(key, [first, second])
    assert reused['coverage']['reused_fresh_instances_across_pairs'][0]['pairs'] == 48
    assert reused['coverage']['complete'] is False


def test_external_family_cannot_fill_planned_gpt_slots(packet):
    root, _, key, _ = packet
    first = returned(packet, root / 'first')
    external = returned(packet, root / 'claude', {'id': 'claude', 'family': 'Claude', 'instance': 'claude-one'}, swap=True)
    report = pe.fit(key, [first, external])
    assert report['input_judgments'] == 96
    assert report['judgments'] == 48
    assert report['coverage']['effective_judgments'] == 48
    assert report['coverage']['complete'] is False
    assert report['predeclared_checks']['cluster_CI_lower_above_0_5'] is None


def test_bt_known_balanced_answer_and_length_bias():
    obs = [{'left': 'A', 'right': 'B', 'winner': p} for p in ('A', 'A', 'A', 'B')]
    b = pe._bt_problem(['A', 'B'], obs, 0)
    assert b['converged']
    assert b['scores']['A'] - b['scores']['B'] == pytest.approx(math.log(3), abs=1e-5)
    key = {'papers': {'A': {'word_count': 100}, 'B': {'word_count': 50}}}
    rows = [{'left': 'A', 'right': 'B', 'winner': 'A'}, {'left': 'B', 'right': 'A', 'winner': 'A'}] * 3
    assert pe._length_bias(key, rows)['pearson'] == pytest.approx(1)
    assert pe._ci([1.] * 1000, 1)['interval'] is None


def test_family_and_identity_based_swapped_agreement(packet):
    root, _, _, _ = packet
    first = returned(packet, root / 'a')
    swapped = returned(packet, root / 'b', swap=True)
    stable = pe.agreement(first, swapped)
    assert stable['swap_stability']['n'] == 48
    assert stable['swap_stability']['agreement'] >= 32 / 48
    assert stable['cohens_kappa'] is None
    same = returned(packet, root / 'fresh-two', {'id': 'judge-b', 'family': 'GPT', 'instance': 'two'})
    assert pe.agreement(first, same)['comparison'] == 'same_family_two_instance_agreement'
    external = returned(packet, root / 'claude', {'id': 'claude', 'family': 'Claude', 'instance': 'one'})
    cross = pe.agreement(first, external)
    assert cross['comparison'] == 'different_family_agreement'
    assert cross['cohens_kappa'] == pytest.approx(1)
    assert cross['external_16_check']['kappa_above_0_4'] is None
    data = pe.read_json(external)
    row = data['judgments'][0]
    row['preferred'] = 'right' if row['preferred'] == 'left' else 'left'
    pe.write_json(external, data)
    assert pe.agreement(first, external)['agreement'] == pytest.approx(47 / 48)


def test_external_exact16_and_degenerate_kappa(packet):
    root, _, _, _ = packet
    first = returned(packet, root / 'gpt')
    second = returned(packet, root / 'claude16', {'id': 'claude', 'family': 'Claude', 'instance': 'one'})
    left, right = pe.read_json(first), pe.read_json(second)
    left['judgments'] = left['judgments'][:16]
    right['judgments'] = right['judgments'][:16]
    pe.write_json(first, left)
    pe.write_json(second, right)
    assert pe.agreement(first, second)['external_16_check'] == {'exactly_16_shared': True, 'kappa_above_0_4': True}
    for data, path in ((left, first), (right, second)):
        for row in data['judgments']:
            row['preferred'] = 'left' if row['left'] < row['right'] else 'right'
        pe.write_json(path, data)
    result = pe.agreement(first, second)
    assert result['agreement'] == 1
    assert result['cohens_kappa'] is None
    assert result['kappa_status'] == 'degenerate_or_no_samples'


def agreement_inputs(tmp_path, count=8):
    """Synthetic judgments only; actual context IDs may override batch headers."""
    header = {'id': 'gpt-comparison-batch', 'family': 'GPT', 'instance': 'coordinator-merged'}
    one = {'schema': 1, 'key_sha256': '1' * 64, 'judge': dict(header), 'judgments': []}
    two = copy.deepcopy(one)
    for i in range(count):
        row = {'pair_id': f'synthetic-pair-{i}', 'left': 'A', 'right': 'B', 'preferred': 'left', 'confidence': .75,
               'reasons': [{'left_location': 'page 1 L1', 'right_location': 'page 1 L2', 'reason': 'Synthetic comparison'} for _ in range(3)],
               'mechanical_findings': [], 'fresh_instance': f'actual-first-{i}'}
        one['judgments'].append(row)
        reversed_row = copy.deepcopy(row)
        reversed_row.update(left='B', right='A', preferred='right', fresh_instance=f'actual-second-{i}')
        two['judgments'].append(reversed_row)
    first, second = tmp_path / 'first.json', tmp_path / 'second.json'
    return one, two, first, second


def test_agreement_same_headers_different_row_instances_are_cross_instance(tmp_path):
    one, two, first, second = agreement_inputs(tmp_path)
    assert one['judge'] == two['judge']
    pe.write_json(first, one)
    pe.write_json(second, two)
    report = pe.agreement(first, second)
    assert report['agreement'] == 1
    assert report['comparison'] == 'same_family_two_instance_agreement'
    assert report['instance_comparisons']['same_instance'] == 0
    assert report['swap_stability']['same_instance'] == {'n': 0, 'agreement': None}
    assert report['swap_stability']['cross_instance'] == {'n': 8, 'agreement': 1}
    assert report['swap_stability']['scope'] == 'reversed order across instances; not isolated same-judge order stability'


def test_agreement_mixed_row_instances_split_reversed_order_statistics(tmp_path):
    one, two, first, second = agreement_inputs(tmp_path)
    for i in range(4):
        two['judgments'][i]['fresh_instance'] = one['judgments'][i]['fresh_instance']
    for i in (0, 4, 5):
        two['judgments'][i]['preferred'] = 'left'
    pe.write_json(first, one)
    pe.write_json(second, two)
    report = pe.agreement(first, second)
    assert report['comparison'] == 'same_family_mixed_instance_agreement'
    assert report['instance_comparisons']['same_instance'] == report['instance_comparisons']['cross_instance'] == 4
    assert report['agreement'] == report['swap_stability']['agreement'] == 5 / 8
    assert report['swap_stability']['same_instance'] == {'n': 4, 'agreement': .75}
    assert report['swap_stability']['cross_instance'] == {'n': 4, 'agreement': .5}
    assert report['swap_stability']['scope'].startswith('mixed actual instances;')


@pytest.mark.parametrize('change_header', [False, True])
def test_agreement_without_row_instances_retains_header_fallback(tmp_path, change_header):
    one, two, first, second = agreement_inputs(tmp_path)
    for data in (one, two):
        for row in data['judgments']:
            del row['fresh_instance']
    if change_header:
        two['judge']['instance'] = 'other-actual-context'
    pe.write_json(first, one)
    pe.write_json(second, two)
    report = pe.agreement(first, second)
    assert report['comparison'] == ('same_family_two_instance_agreement' if change_header else 'same_judge_repeated')
    assert report['swap_stability']['cross_instance' if change_header else 'same_instance'] == {'n': 8, 'agreement': 1}


def test_agreement_resolves_judge_id_and_row_fallback_per_pair(tmp_path):
    one, two, first, second = agreement_inputs(tmp_path, 2)
    # First pair has a row override matching the other file's header fallback.
    one['judgments'][0]['fresh_instance'] = one['judge']['instance']
    del two['judgments'][0]['fresh_instance']
    # Second pair resolves to the same context string but a different judge ID
    # still cannot claim repeated execution of that judge.
    two['judgments'][1]['fresh_instance'] = one['judgments'][1]['fresh_instance']
    pe.write_json(first, one)
    pe.write_json(second, two)
    report = pe.agreement(first, second)
    assert report['comparison'] == 'same_judge_repeated'
    two['judge']['id'] = 'different-judge'
    pe.write_json(second, two)
    report = pe.agreement(first, second)
    assert report['comparison'] == 'same_family_two_instance_agreement'
    assert report['swap_stability']['same_instance']['n'] == 0


@pytest.mark.parametrize('damage', ['confidence', 'reasons', 'finding_shape', 'identity', 'hash', 'duplicate'])
def test_judgment_bad_inputs_are_rejected(packet, damage):
    root, _, key, _ = packet
    result = returned(packet, root / 'a')
    data = pe.read_json(result)
    if damage == 'confidence':
        data['judgments'][0]['confidence'] = .49
    elif damage == 'reasons':
        data['judgments'][0]['reasons'][0]['right_location'] = ''
    elif damage == 'finding_shape':
        data['judgments'][0]['mechanical_findings'] = 'must be list'
    elif damage == 'identity':
        data['judgments'][0]['right'] = 'OTHER'
    elif damage == 'hash':
        data['key_sha256'] = '0' * 64
    else:
        data['judgments'].append(copy.deepcopy(data['judgments'][0]))
    pe.write_json(result, data)
    with pytest.raises(ValueError):
        pe.fit(key, [result])


def test_cli_json_failure_and_no_model_call(tmp_path, capsys):
    missing = tmp_path / 'missing.json'
    assert pe.main(['make-pairs', '--index', str(missing), '--contexts', str(missing),
                    '--packet', str(tmp_path / 'packet'), '--key', str(tmp_path / 'key.json'),
                    '--workspace', str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().err)['review_run'] is False


def test_cli_five_commands_complete_synthetic_round(corpus, capsys):
    root, index, ctx = corpus
    source, key = root / 'packet', root / 'private-key.json'
    assert pe.main(['make-pairs', '--index', str(index), '--contexts', str(ctx),
        '--packet', str(source), '--key', str(key), '--workspace', str(root)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt['pair_total_words_two_judges'] > receipt['pair_manuscript_words_one_pass'] * 2
    assert pe.main(['judge-packet', '--packet', str(source), '--output', str(root / 'one-pair'),
        '--judge-id', 'one', '--family', 'synthetic', '--instance', 'one', '--pair-id', pe.read_json(source / 'pairs.json')['pairs'][0]['pair_id'], '--swap']) == 0
    assert json.loads(capsys.readouterr().out)['pairs'] == 1
    assert pe.main(['export-packet', '--packet', str(source), '--output', str(root / 'external'), '--judge', 'external']) == 0
    assert json.loads(capsys.readouterr().out)['pairs'] == 16
    packet = root, source, key, receipt
    first = returned(packet, root / 'gpt')
    second = returned(packet, root / 'claude', {'id': 'claude', 'family': 'Claude', 'instance': 'one'})
    assert pe.main(['fit', '--key', str(key), '--results', str(first), str(second), '--output', str(root / 'fit.json')]) == 0
    assert json.loads(capsys.readouterr().out)['accuracy']['accuracy'] == 1
    assert pe.main(['agreement', '--first', str(first), '--second', str(second), '--output', str(root / 'agreement.json')]) == 0
    assert json.loads(capsys.readouterr().out)['cohens_kappa'] == 1
