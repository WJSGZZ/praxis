"""Simulation identity and explicit real-entry boundaries; no registration claim."""
import json
from pathlib import Path

import pytest

from scripts.paper_template import (MCM_SIMULATION_TEAM, ROOT, check,
                                   compile_paper, preamble, summary_header,
                                   summary_heading)
from scripts.freeze_pdf import freeze


def paper(prefix):
    return prefix + summary_header('C', edition=2020) + summary_heading() + r'Evidence.\end{document}'


def test_default_simulation_and_skeleton_share_one_identity():
    prefix = preamble(title='Simulation')
    assert r'\newcommand{\PraxisTeam}{7391856}' in prefix
    assert r'\newcommand{\PraxisIdentityMode}{simulation}' in prefix
    check(paper(prefix), layout_mode='current')
    skeleton = (ROOT / 'templates/mcm-paper.tex').read_text()
    assert prefix.splitlines()[0] in skeleton
    assert prefix.splitlines()[1] in skeleton
    check(skeleton, layout_mode='current')


@pytest.mark.parametrize('team', ['0000000', '0', '7391857'])
def test_simulation_rejects_arbitrary_or_placeholder_team(team):
    with pytest.raises(ValueError, match='fixed'):
        preamble(team, 'Simulation', identity_mode='simulation')


@pytest.mark.parametrize('team', [None, '0000000', '0', '７３９１８５６', 7391856])
def test_real_entry_requires_explicit_nonzero_ascii_number(team):
    with pytest.raises(ValueError):
        preamble(team, 'Actual entry', identity_mode='contest')


def test_real_identity_is_preserved_and_not_replaced_by_demo_number():
    prefix = preamble('1234567', 'Actual entry', identity_mode='contest')
    assert r'\newcommand{\PraxisTeam}{1234567}' in prefix
    assert r'\newcommand{\PraxisIdentityMode}{contest}' in prefix
    check(paper(prefix), layout_mode='current')
    # Legacy callers supplied their own nonzero number before modes existed.
    assert preamble('1234567', 'Legacy').splitlines()[0] == r'\newcommand{\PraxisTeam}{1234567}'
    assert 'PraxisIdentityMode' not in preamble('1234567', 'Legacy')


@pytest.mark.parametrize('team', ['0000000', '0'])
def test_current_check_compile_and_freeze_refuse_zero_before_output(tmp_path, team):
    raw = paper(preamble(MCM_SIMULATION_TEAM, 'Simulation')).replace(
        r'\newcommand{\PraxisTeam}{7391856}', r'\newcommand{\PraxisTeam}{' + team + '}')
    tex = tmp_path / 'paper.tex'; tex.write_text(raw)
    pdf = tmp_path / 'missing.pdf'; target = tmp_path / 'final.pdf'
    with pytest.raises(ValueError, match='All-zero'):
        check(raw, layout_mode='current')
    with pytest.raises(ValueError, match='All-zero'):
        compile_paper(tex, 'mcm', tmp_path / 'build')
    with pytest.raises(ValueError, match='All-zero'):
        freeze(pdf, target, tex=tex, contest='mcm')
    assert not target.exists() and not (tmp_path / 'build').exists()


def test_deliberate_archive_keeps_old_zero_without_recertification():
    prefix = preamble('0000000', 'Archive', layout_version=4, identity_mode='archive')
    assert 'PraxisIdentityMode' not in prefix
    check(paper(prefix), layout_mode='archive')
    with pytest.raises(ValueError, match='explicit layout'):
        preamble('0000000', 'Archive', identity_mode='archive')


@pytest.mark.parametrize('mutation', [
    ('{7391856}', '{7391857}'),
    ('{simulation}', '{unknown}'),
    ('{simulation}', '{simulation}\n\\newcommand{\\PraxisIdentityMode}{contest}'),
])
def test_current_simulation_declaration_is_checked(mutation):
    raw = paper(preamble(title='Simulation')).replace(*mutation)
    with pytest.raises(ValueError, match='identity|Identity|Simulation'):
        check(raw, layout_mode='current')


def test_current_identity_cannot_be_overridden():
    raw = paper(preamble(title='Simulation')).replace(r'\begin{document}', r'\renewcommand{\PraxisTeam}{1234567}\begin{document}')
    with pytest.raises(ValueError, match='overrides'):
        check(raw, layout_mode='current')


@pytest.mark.parametrize('field', [r'\textbf{From:} Team 7391861\\',
                                  r'\noindent Respectfully,\\Team 7391857',
                                  'The internal control identifier 2024022 is not officially assigned.'])
def test_current_identity_fields_cannot_drift_in_body(field):
    raw = paper(preamble(title='Simulation')).replace('Evidence.', field)
    with pytest.raises(ValueError, match='signatures and disclosure'):
        check(raw, layout_mode='current')


def test_other_team_citations_and_actual_seed_remain_truthful():
    body = (r'Resources: seed 7391861.\par\textbf{From:} Team \PraxisTeam\\'
            + r'\begin{thebibliography}{1}\bibitem{other} Team 2510862. A different paper.\end{thebibliography}')
    raw = paper(preamble(title='Simulation')).replace('Evidence.', body)
    check(raw, layout_mode='current')


def test_public_gallery_declares_simulation_not_actual_registration():
    catalog = json.loads((ROOT / 'demos/mcm-studies/catalog.json').read_text())
    for row in catalog['entries']:
        assert row['identity'] == {'mode': 'simulation', 'team': MCM_SIMULATION_TEAM}


def test_primary_demo_builder_rejects_a_real_identity_with_fresh_source_hash(tmp_path):
    import hashlib
    import os
    import shutil
    import subprocess
    import sys

    reproduce = tmp_path / 'reproduce'; reproduce.mkdir()
    script = reproduce / 'build_paper.py'
    shutil.copy2(ROOT / 'demos/mcm-2016-a/reproduce/build_paper.py', script)
    source = tmp_path / 'report/paper.tex'; source.parent.mkdir()
    source.write_text(paper(preamble('1234567', 'Actual entry', identity_mode='contest')))
    (tmp_path / 'verification.json').write_text(json.dumps({'pdf': {
        'tex_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'pages_total': 1}}))
    environment = dict(os.environ, PYTHONPATH=str(ROOT))
    result = subprocess.run([sys.executable, str(script), '--candidate'], cwd=ROOT,
                            env=environment, capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert 'fixed simulation team identity' in result.stderr
    assert not (reproduce / 'paper').exists()
