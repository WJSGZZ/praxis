import pytest

from scripts.check_presentation import check, readme_errors
from scripts.release_notes import render


def test_public_capabilities_and_version_agree_in_both_languages():
    assert check()['errors'] == []


def test_stale_download_version_and_missing_capability_are_reported():
    text = ('[latest](https://github.com/WJSGZZ/praxis/releases/latest) '
            '[old](https://github.com/WJSGZZ/praxis/releases/tag/v0.7.0)\n'
            '| [`praxis`](SKILL.md) | core |\n## Math tools\n| `solve_lp` | LP |')
    errors = readme_errors(text, 'en', '0.8.0', {'praxis', 'praxis-image-analysis'}, {'solve_lp', 'binary_components'})
    assert len(errors) == 3
    assert any('0.7.0' in error for error in errors)
    assert any('praxis-image-analysis' in error for error in errors)
    assert any('binary_components' in error for error in errors)


def test_release_notes_use_the_selected_version_and_actual_assets():
    changelog = ('## 0.8.0 · 2026-10-13\n- 新版变化。\n  New changes.\n\n'
                 '## 0.7.1 · 2026-10-13\n- 原版本变化，[说明](SECURITY.md)。\n  Original changes.\n')
    notes = render('0.7.1', changelog, ['praxis-0.7.1-codex.zip', 'SHA256SUMS.txt'])
    assert 'New changes.' not in notes and 'Original changes.' in notes
    assert '/blob/v0.7.1/SECURITY.md' in notes
    assert '/download/v0.7.1/praxis-0.7.1-codex.zip' in notes
    assert 'claude.zip' not in notes
    assert '中文说明' in notes and 'English guide' in notes


def test_release_without_attachments_does_not_invent_downloads():
    notes = render('0.3.0', '## 0.3.0 · day\n- 中文。\n  English.\n', [])
    assert '/releases/download/' not in notes


@pytest.mark.parametrize('version', ['0.7', '../0.7.1', '0.7.2'])
def test_unknown_or_malformed_release_is_rejected(version):
    with pytest.raises(ValueError):
        render(version, '## 0.7.1 · day\n- 中文。\n  English.\n', [])


def test_release_rejects_untranslated_changes_and_unsafe_asset_names():
    with pytest.raises(ValueError):
        render('0.7.1', '## 0.7.1 · day\nOnly English changes.\n', [])
    with pytest.raises(ValueError):
        render('0.7.1', '## 0.7.1 · day\n中文。 English.\n', ['../bad.zip'])


def _gallery_copy(tmp_path):
    import shutil
    from pathlib import Path
    from scripts.check_presentation import ROOT

    target = tmp_path / 'demos' / 'mcm-studies'
    shutil.copytree(ROOT / 'demos' / 'mcm-studies', target)
    primary = target.parent / 'mcm-2016-a'
    primary.mkdir(parents=True)
    shutil.copy2(ROOT / 'demos' / 'mcm-2016-a' / 'paper.pdf', primary / 'paper.pdf')
    return target


def test_single_best_gallery_has_unique_problem_identity_and_bound_papers():
    from scripts.check_presentation import check_gallery

    result = check_gallery()
    assert result['entries'] == 10
    assert result['errors'] == []


def test_gallery_rejects_duplicate_problem_identity(tmp_path):
    import json
    from scripts.check_presentation import check_gallery

    gallery = _gallery_copy(tmp_path)
    path = gallery / 'catalog.json'
    catalog = json.loads(path.read_text())
    catalog['entries'][1]['edition'] = catalog['entries'][0]['edition']
    catalog['entries'][1]['problem'] = catalog['entries'][0]['problem']
    path.write_text(json.dumps(catalog))
    assert any('appears more than once' in error for error in check_gallery(tmp_path)['errors'])


def test_gallery_rejects_orphaned_pdf_and_metadata_records(tmp_path):
    from scripts.check_presentation import check_gallery

    gallery = _gallery_copy(tmp_path)
    (gallery / 'papers' / 'old-version.pdf').write_bytes((gallery / 'papers' / 'mcm-2017-b.pdf').read_bytes())
    (gallery / 'metadata' / 'old-version.json').write_text('{}')
    errors = check_gallery(tmp_path)['errors']
    assert any('metadata files differ' in error for error in errors)
    assert any('PDF files differ' in error for error in errors)


def test_gallery_rejects_page_count_and_hash_mismatches(tmp_path):
    import json
    from scripts.check_presentation import check_gallery

    gallery = _gallery_copy(tmp_path)
    path = gallery / 'catalog.json'
    catalog = json.loads(path.read_text())
    catalog['entries'][1]['pages'] += 1
    catalog['entries'][2]['pdf_sha256'] = '0' * 64
    path.write_text(json.dumps(catalog))
    errors = check_gallery(tmp_path)['errors']
    assert any('PDF has' in error for error in errors)
    assert any('PDF SHA-256 differs' in error for error in errors)


def test_gallery_checker_reports_missing_directory(tmp_path):
    from scripts.check_presentation import check_gallery

    result = check_gallery(tmp_path)
    assert result['errors'] and 'Gallery directory is missing' in result['errors'][0]


def test_gallery_rejects_missing_bilingual_table_entry(tmp_path):
    from scripts.check_presentation import check_gallery

    gallery = _gallery_copy(tmp_path)
    english = gallery / 'README.en.md'
    lines = english.read_text().splitlines()
    english.write_text('\n'.join(line for line in lines if 'metadata/mcm-2025-c.json' not in line) + '\n')
    assert any('list each catalog paper exactly once' in error
               for error in check_gallery(tmp_path)['errors'])


def test_gallery_catalog_can_grow_without_hard_coded_problem_count(tmp_path):
    import json
    import shutil
    from scripts.check_presentation import check_gallery

    gallery = _gallery_copy(tmp_path)
    catalog_path = gallery / 'catalog.json'
    catalog = json.loads(catalog_path.read_text())
    template = next(entry for entry in catalog['entries'] if entry['slug'] == 'mcm-2017-b')
    added = dict(template, edition=2018, problem='A', slug='mcm-2018-a',
                  pdf_path='papers/mcm-2018-a.pdf', metadata='metadata/mcm-2018-a.json')
    catalog['entries'].append(added)
    catalog_path.write_text(json.dumps(catalog))
    shutil.copy2(gallery / template['pdf_path'], gallery / added['pdf_path'])
    metadata = json.loads((gallery / template['metadata']).read_text())
    metadata.update(id='MCM-2018-A', case_identity='MCM-2018-A', edition=2018,
                    problem='A', pdf_path='../papers/mcm-2018-a.pdf')
    (gallery / added['metadata']).write_text(json.dumps(metadata))
    for filename, row in [
        ('README.md', '| 2018 MCM A · 示例 | [论文·17页](papers/mcm-2018-a.pdf) · [说明](metadata/mcm-2018-a.json) | 示例方法与边界。 |'),
        ('README.en.md', '| 2018 MCM A · Example | [Paper · 17 pages](papers/mcm-2018-a.pdf) · [Record](metadata/mcm-2018-a.json) | Example method and boundary. |'),
    ]:
        path = gallery / filename
        text = path.read_text()
        next_heading = '\n## '
        start = text.index(next_heading, text.index('\n## ', text.index('\n## ') + 1))
        path.write_text(text[:start] + '\n' + row + text[start:])
    assert check_gallery(tmp_path)['errors'] == []


def test_gallery_rejects_duplicate_paper_row_under_unknown_heading(tmp_path):
    from scripts.check_presentation import check_gallery
    gallery = _gallery_copy(tmp_path)
    path = gallery/'README.md'
    text = path.read_text(); row = next(line for line in text.splitlines()
                                       if 'metadata/mcm-2016-a.json' in line)
    path.write_text(text+'\n## 旧版本\n\n'+row+'\n')
    assert any('all displayed paper rows' in error for error in check_gallery(tmp_path)['errors'])


def test_gallery_rejects_wrong_visible_problem_label(tmp_path):
    from scripts.check_presentation import check_gallery
    gallery = _gallery_copy(tmp_path)
    path = gallery/'README.en.md'
    path.write_text(path.read_text().replace('2017 MCM B · Toll-plaza',
                                            '2016 MCM A · Toll-plaza'))
    assert any('displayed problem label differs' in error for error in check_gallery(tmp_path)['errors'])
