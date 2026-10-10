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
    pdf=demo/'deliverables/7391856.pdf'
    meta=json.loads((demo/'verification.json').read_text())
    assert meta['pdf']['sha256']==hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert meta['current_award_assessment']['version_sha256']==meta['pdf']['sha256']
    pages=PdfReader(pdf).pages
    assert len(pages)==26
    text=' '.join(' '.join(p.extract_text().split()) for p in pages)
    assert 'Challenge the transport mechanism' in text
    assert '-31.51' in text.replace('−', '-') and '-26.28' in text.replace('−', '-')
    assert 'a permitted short circuit does not establish the cause' in text
    assert 'over the remaining bath' in text
    # PDF word-spacing may be emitted as glyph placement rather than spaces.
    assert 'followedbythebackup' in ''.join(text.replace('- ', '').split())
    assert 'retainthequalifiedbackup' in ''.join(text.split())
    revision=meta['transport_revision']
    assert revision['checks']==24 and revision['replays']==36
    # Historical revisions retain their own sources; only the active PDF binding
    # follows later report revisions.
    assert meta['pdf']['generator_sha256']==hashlib.sha256((HERE/'build_report.py').read_bytes()).hexdigest()


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
