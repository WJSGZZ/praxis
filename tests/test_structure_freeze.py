"""Integration at the final output boundary, not another heading-parser test."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pypdf import PdfWriter

from scripts.freeze_pdf import freeze
from scripts.paper_structure import inspect_structure
from scripts.paper_template import ROOT, check, preamble, summary_header


def artifact(tmp_path, body):
    tex = tmp_path / 'source.tex'
    tex.write_text(preamble('7391857', 'A conditional answer')
                   + summary_header('A', edition=2023)
                   + body + r'\end{document}', encoding='utf-8')
    pdf = tmp_path / 'source.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with pdf.open('wb') as stream:
        writer.write(stream)
    build = tmp_path / 'synthetic-build.json'
    # Synthetic provenance tests binding and refusal only. Real current-paper
    # compilation and negative old-paper replay are separate development evidence.
    build.write_text(json.dumps({
        'runtime': json.loads((ROOT / 'templates/typesetting-runtime.json').read_text()),
        'layout': check(tex.read_text()),
        'tex_sha256': hashlib.sha256(tex.read_bytes()).hexdigest(),
        'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
    }))
    return tex, pdf, build


def approval(tmp_path, tex, reason='This externally required subsection is the stable reference target.'):
    report = inspect_structure(tex.read_bytes().decode('utf-8'))
    assert len(report['candidates']) == 1
    review = tmp_path / 'structure-review.json'
    review.write_text(json.dumps({
        'tex_sha256': report['tex_sha256'],
        'approved_single_child_nodes': [
            {'id': report['candidates'][0]['id'], 'reason': reason}],
    }))
    return review


def test_sole_child_refuses_creation_without_changing_source(tmp_path):
    tex, pdf, build = artifact(tmp_path, r'\section{Model}\subsection{Construction}Evidence.')
    original = (tex.read_bytes(), pdf.read_bytes(), build.read_bytes())
    destination = tmp_path / 'delivery' / 'paper.pdf'
    with pytest.raises(ValueError, match='Heading structure review failed'):
        freeze(pdf, destination, tex=tex, contest='mcm', build_receipt=build)
    assert not destination.parent.exists()
    assert original == (tex.read_bytes(), pdf.read_bytes(), build.read_bytes())


def test_source_bound_reason_allows_real_navigation_exception(tmp_path):
    tex, pdf, build = artifact(tmp_path, r'\section{Model}\subsection{Required anchor}\label{anchor}Evidence.')
    review = approval(tmp_path, tex)
    destination = tmp_path / 'paper.pdf'
    receipt = freeze(pdf, destination, tex=tex, contest='mcm', build_receipt=build,
                     structure_review=review)
    assert destination.read_bytes() == pdf.read_bytes()
    structure = receipt['heading_structure_review']
    assert structure['passed'] and len(structure['candidates']) == 1
    assert structure['candidates'][0]['approval_reason'].startswith('This externally required')
    assert structure['tex_sha256'] == hashlib.sha256(tex.read_bytes()).hexdigest()


@pytest.mark.parametrize('bad', ['stale', 'unknown', 'empty', 'duplicate'])
def test_invalid_reason_cannot_create_snapshot(tmp_path, bad):
    tex, pdf, build = artifact(tmp_path, r'\section{Model}\subsection{Construction}Evidence.')
    review = approval(tmp_path, tex)
    data = json.loads(review.read_text())
    if bad == 'stale':
        data['tex_sha256'] = '0' * 64
    elif bad == 'unknown':
        data['approved_single_child_nodes'][0]['id'] = 'absent'
    elif bad == 'empty':
        data['approved_single_child_nodes'][0]['reason'] = ' '
    else:
        data['approved_single_child_nodes'] *= 2
    review.write_text(json.dumps(data))
    destination = tmp_path / 'paper.pdf'
    with pytest.raises(ValueError, match='Heading structure review failed'):
        freeze(pdf, destination, tex=tex, contest='mcm', build_receipt=build,
               structure_review=review)
    assert not destination.exists()


@pytest.mark.parametrize('body', [
    r'\section{Model}One complete argument.',
    r'\section{Model}\subsection{Construction}Evidence.\subsection{Independent check}Check.',
])
def test_no_forced_subsections_or_reasons(tmp_path, body):
    tex, pdf, build = artifact(tmp_path, body)
    receipt = freeze(pdf, tmp_path / 'paper.pdf', tex=tex, contest='mcm', build_receipt=build)
    assert receipt['heading_structure_review']['candidates'] == []


def test_reason_requires_a_source_not_just_a_pdf(tmp_path):
    with pytest.raises(ValueError, match='requires TeX'):
        freeze(tmp_path / 'unread.pdf', tmp_path / 'paper.pdf', structure_review=tmp_path / 'review.json')
    assert not (tmp_path / 'paper.pdf').exists()


def test_template_review_cli_propagates_failure_and_source_bound_approval(tmp_path):
    tex, _, _ = artifact(tmp_path, r'\section{Model}\subsection{Construction}Evidence.')
    command = [sys.executable, '-m', 'scripts.paper_template', str(tex), '--review-structure']
    failed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert failed.returncode == 1
    assert len(json.loads(failed.stdout)['unresolved']) == 1
    review = approval(tmp_path, tex)
    accepted = subprocess.run(command + ['--structure-review', str(review)],
                              cwd=ROOT, capture_output=True, text=True)
    assert accepted.returncode == 0 and json.loads(accepted.stdout)['passed']


def test_template_cli_does_not_silently_ignore_review_options(tmp_path):
    tex, _, _ = artifact(tmp_path, r'\section{Model}Evidence.')
    for arguments in [
        ['--structure-review', str(tmp_path / 'review.json')],
        ['--review-structure', '--compile', '--output-directory', str(tmp_path / 'build')],
        ['--review-structure', '--review-captions'],
    ]:
        result = subprocess.run([sys.executable, '-m', 'scripts.paper_template', str(tex)] + arguments,
                                cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 2
        assert not (tmp_path / 'build').exists()
