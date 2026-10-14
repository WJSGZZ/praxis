"""A valid selected log must survive the package's own archive boundary."""
import json
import zipfile

import pytest

from scripts import feedback


def test_highly_compressible_selected_file_roundtrips_without_relaxing_reader(tmp_path):
    case = tmp_path/'case'
    case.mkdir()
    data = b'0\n' * 50000
    (case/'run.log').write_bytes(data)
    feedback.init(case, mode='autonomous', goal='Recorded finite log')
    staged = feedback.stage(case, tmp_path/'shared', includes=['run.log'])
    result = feedback.pack(tmp_path/'shared', tmp_path/'shared.zip',
                           confirm_manifest_sha256=staged['manifest_sha256'])
    with zipfile.ZipFile(tmp_path/'shared.zip') as archive:
        assert archive.read('files/run.log') == data
    assert result['inspection'] == staged['inspection']
    assert json.loads((tmp_path/'shared/manifest.json').read_text())['files'][0]['bytes'] == len(data)


def test_rejected_zip_closes_its_handle_before_propagating_error(tmp_path, monkeypatch):
    path = tmp_path/'invalid.zip'
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('../outside.txt',b'untrusted data')
    factory = zipfile.ZipFile
    opened = []

    def tracked(*args, **kwargs):
        archive = factory(*args, **kwargs)
        opened.append(archive)
        return archive

    monkeypatch.setattr(feedback.zipfile,'ZipFile',tracked)
    with pytest.raises(ValueError,match='Unsafe relative path'):
        feedback.inspect(path)
    assert len(opened)==1 and opened[0].fp is None
