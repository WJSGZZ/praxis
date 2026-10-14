"""Actual compiler-resolved imports remain bound through final freezing."""
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
from PIL import Image
from scripts.paper_template import (
    _system_null_input, _windows_null_name, compiler_dependencies,
    compile_paper, preamble, verify_compiler_dependencies,
)
from scripts.freeze_pdf import freeze


def test_actual_host_null_is_typed_and_source_still_bound(tmp_path):
    source = tmp_path/'main.tex'; source.write_text('Source remains bound')
    rules = tmp_path/'dependencies.mk'
    rules.write_text(f'main.pdf : main.tex \\\n  {os.devnull}\n')
    record = compiler_dependencies(rules, source)
    assert set(record['files']) == {'main.tex'}
    assert record['system_inputs'] == [_system_null_input(
        Path(os.devnull) if os.name != 'nt' else source.parent/os.devnull)]
    assert record['system_inputs'][0]['read_semantics'] == 'immediate-eof'
    assert verify_compiler_dependencies(record, source)['passed']
    if os.name == 'nt':
        # The actual pinned LaTeX platform probe uses this colon spelling.
        rules.write_text('main.pdf : main.tex \\\n  nul:\n')
        colon = compiler_dependencies(rules, source)
        assert set(colon['files']) == {'main.tex'}
        assert len(colon['system_inputs']) == 1
        assert colon['system_inputs'][0]['read_semantics'] == 'immediate-eof'
        assert verify_compiler_dependencies(colon, source)['passed']
    source.write_text('Changed source')
    with pytest.raises(ValueError, match='current source'):
        verify_compiler_dependencies(record, source)


@pytest.mark.skipif(os.name != 'posix', reason='POSIX filenames and null character device')
def test_null_exception_does_not_hide_regular_files_or_symlink_alias(tmp_path):
    source = tmp_path/'main.tex'; source.write_text('Source')
    ordinary = tmp_path/'NUL'; ordinary.write_text('A real local file')
    directory = tmp_path/'dev'; directory.mkdir()
    local_null = directory/'null'; local_null.write_text('Another real file')
    rules = tmp_path/'dependencies.mk'
    rules.write_text('main.pdf : main.tex \\\n  NUL \\\n  dev/null\n')
    record = compiler_dependencies(rules, source)
    assert set(record['files']) == {'main.tex', 'NUL', 'dev/null'}
    assert record['system_inputs'] == []
    ordinary.write_text('Changed')
    with pytest.raises(ValueError, match='changed or was deleted: NUL'):
        verify_compiler_dependencies(record, source)
    alias = tmp_path/'null-alias'; alias.symlink_to(os.devnull)
    rules.write_text('main.pdf : main.tex \\\n  null-alias\n')
    with pytest.raises(ValueError, match='missing'):
        compiler_dependencies(rules, source)


@pytest.mark.skipif(os.name != 'posix', reason='POSIX nonempty character device')
def test_other_device_is_rejected_without_reading_it(tmp_path, monkeypatch):
    source = tmp_path/'main.tex'; source.write_text('Source')
    rules = tmp_path/'dependencies.mk'
    rules.write_text('main.pdf : main.tex \\\n  /dev/zero\n')
    import builtins
    actual_open = builtins.open
    def guarded_open(name, *args, **kwargs):
        assert str(name) != '/dev/zero', 'Never read an unrelated device'
        return actual_open(name, *args, **kwargs)
    monkeypatch.setattr(builtins, 'open', guarded_open)
    with pytest.raises(ValueError, match='missing'):
        compiler_dependencies(rules, source)


@pytest.mark.parametrize('name', ['NUL', 'nul', 'NUL:', 'nul:', r'C:\dir\NUL', r'C:\dir\NUL:', r'\\.\NUL', r'\\.\NUL:'])
def test_windows_null_lexical_supported_spellings(name):
    assert _windows_null_name(name)


@pytest.mark.parametrize('name', [
    'NUL.txt', 'CON', '/dev/null', r'\\server\share\NUL',
    r'\\?\C:\dir\NUL', '', 'NUL\x00',
])
def test_windows_null_lexical_rejects_other_inputs(name):
    assert not _windows_null_name(name)


def test_forged_or_changed_system_input_is_refused(tmp_path):
    import copy
    source = tmp_path/'main.tex'; source.write_text('Source')
    rules = tmp_path/'dependencies.mk'
    rules.write_text(f'main.pdf : main.tex \\\n  {os.devnull}\n')
    record = compiler_dependencies(rules, source)
    for field, value in [('opened_name', str(source)), ('kind', 'system-device'),
                         ('platform', 'unsupported'), ('read_semantics', 'arbitrary-bytes'),
                         ('device_type', 'ordinary-file')]:
        forged = copy.deepcopy(record)
        forged['system_inputs'][0][field] = value
        with pytest.raises(ValueError, match='system-input|system null input'):
            verify_compiler_dependencies(forged, source)
    duplicated = copy.deepcopy(record)
    duplicated['system_inputs'] *= 2
    with pytest.raises(ValueError, match='system null input'):
        verify_compiler_dependencies(duplicated, source)


@pytest.mark.skipif(os.name != 'posix', reason='POSIX character-device probe')
def test_empty_regular_file_cannot_impersonate_posix_null(tmp_path, monkeypatch):
    impostor = tmp_path/'empty'; impostor.write_bytes(b'')
    monkeypatch.setattr(os, 'devnull', str(impostor))
    with pytest.raises(ValueError, match='expected character device'):
        _system_null_input(impostor)


@pytest.mark.skipif(shutil.which('tectonic') is None, reason='Canonical Tectonic compiler unavailable')
def test_actual_null_build_freezes_but_changed_device_record_is_refused(tmp_path):
    source = tmp_path/'main.tex'
    source.write_text(preamble(None, 'Empty input', 'research') +
        r'\title[Empty input]{Empty input}\maketitle' +
        r'\newread\emptyinput\openin\emptyinput=' + os.devnull +
        r'\relax\closein\emptyinput ' +
        r'An empty system input supplies no manuscript content.\end{document}')
    output = tmp_path/'compiled'
    receipt = compile_paper(source, 'research', output)
    assert len(receipt['compiler_dependencies']['system_inputs']) == 1
    pdf, build = output/'main.pdf', output/'main.build.json'
    result = freeze(pdf, tmp_path/'accepted.pdf', tex=source,
                    contest='research', build_receipt=build)
    assert result['compiler_dependency_review']['system_inputs'] == \
        receipt['compiler_dependencies']['system_inputs']
    receipt['compiler_dependencies']['system_inputs'][0]['read_semantics'] = 'nonempty-input'
    build.write_text(json.dumps(receipt))
    rejected = tmp_path/'refused.pdf'
    with pytest.raises(ValueError, match='system null input'):
        freeze(pdf, rejected, tex=source, contest='research', build_receipt=build)
    assert not rejected.exists()


def test_dependency_parser_preserves_spaced_names_and_rejects_missing(tmp_path):
    source = tmp_path/'main.tex'; source.write_text('Top-level source')
    child = tmp_path/'body with space.tex'; child.write_text('External source')
    rules = tmp_path/'dependencies.mk'
    rules.write_text('main.pdf : main.tex \\\n  body with space.tex\n')
    record = compiler_dependencies(rules, source)
    assert set(record['files']) == {'main.tex', 'body with space.tex'}
    assert verify_compiler_dependencies(record, source)['passed']
    child.unlink()
    with pytest.raises(ValueError, match='changed or was deleted'):
        verify_compiler_dependencies(record, source)
    with pytest.raises(ValueError, match='missing'):
        compiler_dependencies(rules, source)


@pytest.mark.skipif(shutil.which('tectonic') is None, reason='Canonical Tectonic compiler unavailable')
def test_actual_macro_inputs_and_binary_figure_are_bound_then_refused(tmp_path):
    source = tmp_path/'main.tex'
    child = tmp_path/'body with space.tex'
    grandchild = tmp_path/'conclusion.tex'
    figure = tmp_path/'plot.png'
    Image.new('RGB', (32, 32), 'blue').save(figure)
    child.write_text(r'An imported argument. \input{conclusion}')
    grandchild.write_text('Its conclusion is conditional.')
    source.write_text(preamble(None, 'Imported resources', 'research') +
        r'\title[Imported resources]{Imported resources}\maketitle'
        r'\def\bodyfile{body with space}\input{\bodyfile}'
        r'\def\figurefile{plot.png}\includegraphics[width=1cm]{\figurefile}'
        r'\end{document}')
    output = tmp_path/'compiled'
    receipt = compile_paper(source, 'research', output)
    assert set(receipt['compiler_dependencies']['files']) == {
        'main.tex', 'body with space.tex', 'conclusion.tex', 'plot.png'}
    source_bytes = source.read_bytes()
    pdf = output/'main.pdf'; build = output/'main.build.json'
    accepted = freeze(pdf, tmp_path/'accepted.pdf', tex=source, contest='research', build_receipt=build)
    assert accepted['compiler_dependency_review']['passed']
    for resource in (child, grandchild, figure):
        original = resource.read_bytes()
        resource.write_bytes(original+b'changed')
        destination = tmp_path/(resource.stem+'-changed.pdf')
        with pytest.raises(ValueError, match='dependency changed'):
            freeze(pdf, destination, tex=source, contest='research', build_receipt=build)
        assert not destination.exists()
        resource.write_bytes(original)
    figure.unlink()
    with pytest.raises(ValueError, match='dependency changed'):
        freeze(pdf, tmp_path/'deleted.pdf', tex=source, contest='research', build_receipt=build)
    assert source.read_bytes() == source_bytes


def test_historical_receipt_is_unknown_not_retroactively_certified(tmp_path):
    from pypdf import PdfWriter
    from scripts.paper_template import ROOT, check
    source = tmp_path/'main.tex'
    source.write_text(preamble(None, 'Archive', 'research')+
                     r'\title[Archive]{Archive}\end{document}')
    pdf = tmp_path/'main.pdf'
    writer=PdfWriter(); writer.add_blank_page(width=595, height=842); writer.write(pdf)
    build=tmp_path/'main.build.json'
    build.write_text(json.dumps({'runtime':json.loads((ROOT/'templates/typesetting-runtime.json').read_text()),
        'layout':check(source.read_text(),'research'),
        'tex_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()}))
    with pytest.raises(ValueError, match='compiler-opened dependency'):
        freeze(pdf,tmp_path/'current.pdf',tex=source,contest='research',build_receipt=build)
    result=freeze(pdf,tmp_path/'archive.pdf',tex=source,contest='research',build_receipt=build,layout_mode='archive')
    assert result['compiler_dependency_review']['passed'] is None
