"""2026 AI declaration boundary, separately from old unspecified-edition checks."""
import pytest
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, TextStringObject, DecodedStreamObject

from scripts.contest_rules import evaluate, extract


USED = '本参赛队在竞赛过程中使用了AI工具，主要用于代码调试，详细使用情况见支撑材料。'
UNUSED = '本参赛队在竞赛过程中未使用任何AI工具。'


def page(text):
    return dict(text=text, lines=text.splitlines(), body_size=12.0)


def pages(declaration='AI工具使用声明\n' + UNUSED):
    return [
        page('题目\n摘 要\n内容。\n关键词：甲；乙\n1'),
        page('正文\n模型说明。\n' + declaration + '\n参考文献\n[1] 实际来源。\n2'),
        page('附录 A 支撑材料文件列表\n本论文没有用到程序\n本论文没有支撑材料\n3'),
    ]


def write_cjk_pdf(path, records):
    """A real standard-CJK PDF, with distinct physical text lines.

    This fixture tests extraction, not house-style or embedded-font compliance.
    UniGB-UCS2-H deliberately exercises the shipped standard CJK mapping path.
    """
    writer = PdfWriter()
    descendant = DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/CIDFontType0'),
        NameObject('/BaseFont'): NameObject('/STSong-Light'),
        NameObject('/CIDSystemInfo'): DictionaryObject({
            NameObject('/Registry'): TextStringObject('Adobe'),
            NameObject('/Ordering'): TextStringObject('GB1'),
            NameObject('/Supplement'): NumberObject(4),
        }),
        NameObject('/DW'): NumberObject(1000),
    })
    font = writer._add_object(DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type0'),
        NameObject('/BaseFont'): NameObject('/STSong-Light'),
        NameObject('/Encoding'): NameObject('/UniGB-UCS2-H'),
        NameObject('/DescendantFonts'): ArrayObject([writer._add_object(descendant)]),
    }))
    for record in records:
        pdf_page = writer.add_blank_page(width=595.27559, height=841.88976)
        pdf_page[NameObject('/Resources')] = DictionaryObject({
            NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})
        })
        commands = []
        physical_lines = [part for line in record['lines']
                          for part in ([line[i:i + 24] for i in range(0, len(line), 24)] or [''])]
        for index, line in enumerate(physical_lines):
            y = 45 if index == len(physical_lines) - 1 else 760 - index * 20
            commands.append(f'BT /F1 12 Tf 1 0 0 1 80 {y} Tm <{line.encode("utf-16-be").hex()}> Tj ET')
        stream = DecodedStreamObject()
        stream.set_data('\n'.join(commands).encode('ascii'))
        pdf_page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as handle:
        writer.write(handle)


@pytest.mark.parametrize('claim', [USED, UNUSED])
def test_used_and_unused_declarations_before_references_are_valid(claim):
    result = evaluate(pages('AI工具使用声明\n' + claim), 'cumcm', edition='2026')
    assert result['passed'], result
    assert result['facts']['ai_declaration_count'] == 1
    assert not result['facts']['ai_use_truth_verified']
    assert not result['facts']['ai_details_attachment_checked']


@pytest.mark.parametrize('declaration', ['', '正文提到AI工具使用声明，但没有设置该节。'])
def test_missing_body_declaration_is_rejected(declaration):
    result = evaluate(pages(declaration), 'cumcm', edition=2026)
    assert not result['passed']
    assert result['facts']['ai_declaration_count'] == 0


def test_duplicate_declarations_are_rejected():
    result = evaluate(pages('AI工具使用声明\n' + UNUSED + '\nAI工具使用声明\n' + UNUSED),
                      'cumcm', edition='2026')
    assert result['facts']['ai_declaration_count'] == 2
    assert any('exactly one' in error for error in result['errors'])


def test_declaration_after_references_is_rejected():
    records = pages('')
    records[1] = page('正文\n参考文献\n[1] 实际来源。\nAI工具使用声明\n' + UNUSED + '\n2')
    assert any('precede' in e for e in evaluate(records, 'cumcm', edition='2026')['errors'])


def test_appendix_and_abstract_mentions_cannot_supply_the_body_declaration():
    records = pages('')
    records[0] = page('题目\n摘 要\nAI工具使用声明\n关键词：甲；乙\n1')
    records[2] = page('附录 A 支撑材料文件列表\nAI工具使用声明\n' + UNUSED +
                      '\n本论文没有用到程序\n本论文没有支撑材料\n3')
    result = evaluate(records, 'cumcm', edition='2026')
    assert not result['passed']
    assert result['facts']['ai_declaration_count'] == 0


@pytest.mark.parametrize('entry', ['AI工具使用声明', 'AI工具使用声明........2'])
def test_contents_mentions_cannot_supply_the_body_declaration(entry):
    records = pages('')
    records.insert(1, page('目 录\n' + entry + '\n2'))
    result = evaluate(records, 'cumcm', edition='2026')
    assert not result['passed']
    assert result['facts']['ai_declaration_count'] == 0


@pytest.mark.parametrize('heading', ['A I 工 具 使 用 声 明', 'AI\n工具使用\n声明', '六、AI工具使用声明', '6\nAI工具使用声明'])
def test_spaced_split_and_numbered_headings_are_one_declaration(heading):
    result = evaluate(pages(heading + '\n' + UNUSED), 'cumcm', edition='2026')
    assert result['passed'], result
    assert result['facts']['ai_declaration_count'] == 1


def test_unspecified_edition_preserves_only_the_legacy_subset():
    result = evaluate(pages(''), 'cumcm')
    assert result['passed']
    assert result['facts']['format_edition'] is None
    assert result['facts']['format_rules_source_edition'] == '2026'
    assert result['facts']['ai_declaration_policy_edition'] is None
    assert any('does not certify' in w for w in result['warnings'])


@pytest.mark.parametrize('edition', ['1998', '2027', 1998, True, False, 2026.0, [], '2026 '])
def test_unsupported_and_non_year_editions_are_refused(edition):
    with pytest.raises(ValueError, match='edition 2026'):
        evaluate(pages(), 'cumcm', edition=edition)


def test_graduate_submission_kind_is_not_inherited_by_cumcm():
    with pytest.raises(ValueError, match='only for graduate'):
        evaluate(pages(), 'cumcm', edition='2026', document_kind='submission')


@pytest.mark.parametrize('claim', [USED, UNUSED])
def test_actual_pdf_extraction_accepts_a_split_chinese_declaration(tmp_path, claim):
    pdf = tmp_path/'split-declaration.pdf'
    write_cjk_pdf(pdf, pages('AI\n工具使用\n声明\n' + claim))
    records = extract(pdf)
    assert '工具使用' in records[1]['text']
    result = evaluate(records, 'cumcm', edition='2026')
    assert result['passed'], result
    assert result['facts']['ai_declaration_count'] == 1


@pytest.mark.parametrize('body,error', [
    ('正文\n参考文献\n[1] 来源。\n2', 'requires one'),
    ('正文\nAI工具使用声明\n' + UNUSED + '\nAI工具使用声明\n' + UNUSED +
     '\n参考文献\n[1] 来源。\n2', 'exactly one'),
    ('正文\n参考文献\n[1] 来源。\nAI工具使用声明\n' + UNUSED + '\n2', 'precede'),
])
def test_actual_pdf_extraction_rejects_bad_declaration_boundaries(tmp_path, body, error):
    pdf = tmp_path/'bad-declaration.pdf'
    records = pages('')
    records[1] = page(body)
    write_cjk_pdf(pdf, records)
    result = evaluate(extract(pdf), 'cumcm', edition='2026')
    assert not result['passed']
    assert any(error in e for e in result['errors'])
