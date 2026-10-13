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
