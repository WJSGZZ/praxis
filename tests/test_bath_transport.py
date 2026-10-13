"""Distinct closure, stale evidence, failed searches and overflow identity."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

HERE=Path(__file__).resolve().parents[1]/'demos/mcm-2016-a/reproduce'
spec=importlib.util.spec_from_file_location('bath_transport',HERE/'transport_values.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_frozen_study_separates_failure_selection_and_energy():
    r=module.transport_values(HERE)
    assert len(r['run']['rows'])==36
    assert len(r['checks']['records'])==24
    assert r['groups'][('uniform',.0003)]['selected'] is None
    assert r['groups'][('localized_body',.0003)]['selected'] is None
    assert r['groups'][('uniform',.001)]['selected']['delay_s']==0
    assert r['groups'][('uniform',.003)]['selected']['delay_s']==600
    assert r['original_overflow']['excess_j']==pytest.approx(-31510.8168277805)
    assert all(row['excess_overflow_energy_j']<0 for row in r['independent'])


def test_delivered_paper_keeps_corrected_mechanism_and_version_identity():
    from pypdf import PdfReader
    demo=HERE.parent
    pdf=demo/'deliverables/paper.pdf'
    meta=json.loads((demo/'verification.json').read_text())
    assert meta['pdf']['sha256']==hashlib.sha256(pdf.read_bytes()).hexdigest()
    revision=meta['frontmatter_revision']
    inheritance=revision['scientific_review_inheritance']
    assert inheritance['review_version_sha256']==meta['current_award_assessment']['version_sha256']==revision['previous_current_pdf']['sha256']
    assert inheritance['current_pdf_sha256']==revision['current_pdf_sha256']
    font_revision=meta['font_layout_revision']
    assert font_revision['previous_current_pdf']['sha256']==revision['current_pdf_sha256']
    font_inheritance=font_revision['scientific_review_inheritance']
    assert font_inheritance['review_version_sha256']==meta['current_award_assessment']['version_sha256']
    assert font_inheritance['current_pdf_sha256']==font_revision['current_pdf_sha256']
    assert font_inheritance['new_scientific_review'] is False and font_inheritance['new_award_assessment'] is False
    assert inheritance['new_scientific_review'] is False and inheritance['new_award_assessment'] is False
    heading_revision=meta['heading_layout_revision']
    assert heading_revision['previous_current_pdf']['sha256']==font_revision['current_pdf_sha256']
    heading_inheritance=heading_revision['scientific_review_inheritance']
    assert heading_inheritance['review_version_sha256']==meta['current_award_assessment']['version_sha256']
    assert heading_inheritance['current_pdf_sha256']==heading_revision['current_pdf_sha256']
    assert heading_inheritance['new_scientific_review'] is False and heading_inheritance['new_award_assessment'] is False
    indentation=meta['indentation_revision']
    assert indentation['previous_current_pdf']['sha256']==heading_revision['current_pdf_sha256']
    indentation_inheritance=indentation['scientific_review_inheritance']
    assert indentation_inheritance['review_version_sha256']==meta['current_award_assessment']['version_sha256']
    assert indentation_inheritance['current_pdf_sha256']==indentation['current_pdf_sha256']==meta['format_gate_revision']['previous_current_pdf']['sha256']
    assert meta['format_gate_revision']['current_pdf_sha256']==meta['pdf']['sha256']
    assert meta['format_gate_revision']['scientific_review_inheritance']['new_scientific_review'] is False
    assert indentation_inheritance['new_scientific_review'] is False and indentation_inheritance['new_award_assessment'] is False
    pages=PdfReader(pdf).pages
    assert len(pages)==26
    text=' '.join(' '.join(p.extract_text().split()) for p in pages)
    assert 'Transport comparison and network infeasibility' in text
    assert '-31.51' in text.replace('−', '-') and '-26.28' in text.replace('−', '-')
    assert 'a permitted short circuit does not establish the cause' in text
    assert 'for every compatible model' in text or 'Over every compatible model' in text
    # PDF word-spacing may be emitted as glyph placement rather than spaces.
    assert 'remainingbackuppassforeverycompatiblemodel' in ''.join(text.replace('- ', '').split())
    assert 'otherwisekeep thecheckedbackup'.replace(' ', '') in ''.join(text.replace('- ', '').split())
    revision=meta['transport_revision']
    assert revision['checks']==24 and revision['replays']==36
    # Historical revisions retain their own sources; only the active PDF binding
    # follows later report revisions.
    source=demo/meta['pdf']['generator_source']
    assert source.is_file()
    assert meta['pdf']['generator_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
    previous=meta['frontmatter_revision']['previous_current_pdf']
    old_source=demo/previous['generator_source']
    assert hashlib.sha256(old_source.read_bytes()).hexdigest()==previous['generator_sha256']=='7b271509cff03e48856f9cfc6aa2a929d036ed64d3d8ee3f1ba836c2a0dc07ef'


def test_four_layout_edges_keep_actual_archived_generator_sources():
    """Compare whole sources after reversing only the recorded layout edits."""
    demo=HERE.parent
    meta=json.loads((demo/'verification.json').read_text())
    revisions=[meta[name] for name in ['frontmatter_revision','font_layout_revision','heading_layout_revision','indentation_revision']]
    old=[]
    for revision in revisions:
        binding=revision['previous_current_pdf']
        raw=(demo/binding['generator_source']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==binding['generator_sha256']
        old.append(raw.decode())
    current=(demo/meta['format_gate_revision']['previous_current_pdf']['generator_source']).read_text()

    def replace(text,before,after,count=1):
        assert text.count(before)==count
        return text.replace(before,after)

    # Original reviewed report -> edition-aware shared summary sheet.
    assert replace(old[1],"summary_header('A', edition=2016)","summary_header('A')")==old[0]

    # Shared v2 -> v3: exact typography/pagination edits, without removing
    # arbitrary paragraphs, numerical expressions, or model calls.
    v3=old[2]
    v3=replace(v3,r'\begingroup\normalsize\setlength',r'\begingroup\small\setlength')
    v3=replace(v3,r'\centering\normalsize\caption',r'\centering\small\caption')
    v3=replace(v3,r'fontsize=\\normalsize',r'fontsize=\\small')
    v3=replace(v3,", font_profile='mcm-v3'",'',10)
    helper='\ndef mcm_spatial_layout(axes):\n    """Keep twelve-point plot text while fitting the full three-panel figure."""\n    return axes.replace(\'width=4.1cm,height=2.6cm\', \'width=3.8cm,height=2.6cm\').replace(\'horizontal sep=0.9cm\', \'horizontal sep=0.65cm\').replace(\'yshift=-1.0cm\', \'yshift=-1.25cm\')\n'
    v3=replace(v3,helper,'')
    v3=replace(v3,"FIG['spatial.png']=mcm_spatial_layout(FIG['spatial.png'])\n",'')
    v3=replace(v3,"page('Appendix A. Scenario definitions')","page('Appendix A. Scenario definitions',True)")
    disclosure=("# Disclosure paragraphs use a local list's natural paragraph separation, without changing body font or page margins.\n"
        +r"tex.append('\\begin{list}{}{\\setlength{\\leftmargin}{0pt}\\setlength{\\rightmargin}{0pt}\\setlength{\\parsep}{2.5pt}\\setlength{\\topsep}{0pt}\\setlength{\\itemsep}{0pt}}\\item[]\n')"+'\n')
    v3=replace(v3,disclosure,'')
    for title in ['Tool, task and scope','Outputs, corrections and verification','Record limitations']:
        before=r"tex.append('\\textbf{"+title+r"}\\par\n')"
        v3=replace(v3,before,"para('"+title+"','heading')")
    v3=replace(v3,r"tex.append('\\end{list}\n')"+'\n','')
    assert v3==old[1]

    # v3 -> clarified headings: four exact literals, no prose/data exclusions.
    heading=old[3]
    for before,after in [
        ('4. Optimality and energy bounds','4. Mixed-model optimum and spatial energy bound'),
        ('7.4 Observation-conditioned decisions','7.4 Supply decisions from temperature probes'),
        ('11.3 Continuous-parameter transfer bounds','11.3 Parameter changes and fixed-policy bounds'),
        ('11.4 Transport comparison and infeasibility','11.4 Transport comparison and network infeasibility'),
    ]:
        heading=replace(heading,"page('"+after+"')","page('"+before+"')")
    assert heading==old[2]

    # Clarified v3 -> v4: only the exact shared Summary component import/call.
    current=replace(current,'from scripts.paper_template import table_of_contents, summary_heading',
                    'from scripts.paper_template import table_of_contents')
    current=replace(current,"if s=='Summary':tex.append(summary_heading())",
                    "if s=='Summary':tex.append(r'\\begin{center}{\\Large\\bfseries Summary}\\end{center}'+'\\n')")
    assert current==old[3]


def test_public_reading_copy_matches_delivery_and_links():
    demo=HERE.parent
    reading=demo/'paper.pdf'
    delivery=demo/'deliverables/paper.pdf'
    assert reading.read_bytes()==delivery.read_bytes()
    meta=json.loads((demo/'verification.json').read_text())
    assert meta['public_paper']['sha256']==hashlib.sha256(reading.read_bytes()).hexdigest()
    assert meta['public_paper']['byte_identical_to']=='deliverables/paper.pdf'
    assert meta['submission_files']==['paper.pdf']
    for language in ['README.md','README.en.md']:
        text=(demo/language).read_text()
        assert '(paper.pdf)' in text and 'href="paper.pdf"' in text
    assert sorted(p.name for p in (demo/'deliverables').iterdir())==['paper.pdf']


@pytest.mark.parametrize('defect',['stale','coverage','failed','water','refinement','outlet'])
def test_consumer_rejects_corrupt_evidence_even_after_outer_rebinding(tmp_path,defect):
    folder=tmp_path/'reference/transport'
    shutil.copytree(HERE/'reference/transport',folder)
    for name in ['results.json','mesh_check.json','trajectory.npz']:
        shutil.copyfile(HERE/'reference'/name,tmp_path/'reference'/name)
    (tmp_path/'code').mkdir()
    shutil.copyfile(HERE/'code/model.py',tmp_path/'code/model.py')
    if defect=='stale':
        (folder/'model.py').write_text((folder/'model.py').read_text()+'\n# changed\n')
    elif defect=='outlet':
        p=folder/'original-overflow.json';r=json.loads(p.read_text());r['outlet_index']=89;p.write_text(json.dumps(r))
    else:
        p=folder/'results.json';r=json.loads(p.read_text())
        if defect=='coverage':r['rows'].pop()
        elif defect=='failed':r['search'][0]['selected']=r['search'][1]['selected']
        elif defect=='water':r['search'][1]['selected']['command_l']+=1
        else:r['search'][1]['refinement'][0]['sampled_physical_passed']=False
        p.write_text(json.dumps(r))
        check=folder/'checks.json';c=json.loads(check.read_text())
        c['source_sha256']['results.json']=hashlib.sha256(p.read_bytes()).hexdigest();check.write_text(json.dumps(c))
    manifest=folder/'manifest.json';m=json.loads(manifest.read_text())
    m['members']={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in m['members']}
    manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError):module.transport_values(tmp_path)
