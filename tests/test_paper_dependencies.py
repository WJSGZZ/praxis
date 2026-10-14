"""Actual compiler-resolved imports remain bound through final freezing."""
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from PIL import Image
from scripts.paper_template import (
    compiler_dependencies, compile_paper, preamble, verify_compiler_dependencies,
)
from scripts.freeze_pdf import freeze


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
