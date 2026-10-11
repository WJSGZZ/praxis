"""Extract text with explicit support for standard CJK CID collections.

xdvipdfmx deliberately omits ToUnicode for Adobe character collections.
Those PDFs are valid; consumers need the collection's Unicode mapping.
Use PDFium's built-in mapping instead of interpreting CIDs as Unicode.
https://github.com/TeX-Live/texlive-source/blob/trunk/texk/dvipdfm-x/type0.c
"""
import collections
import ctypes
import math

from pypdf import PdfReader


def _unicode_chars(codes):
    """Keep PDFium glyph indices while joining UTF-16 surrogate pairs."""
    chars = []
    malformed = 0
    for index, code in enumerate(codes):
        if 0xd800 <= code <= 0xdbff and index + 1 < len(codes) and 0xdc00 <= codes[index + 1] <= 0xdfff:
            chars.append(chr(0x10000 + ((code - 0xd800) << 10) + codes[index + 1] - 0xdc00))
        elif 0xdc00 <= code <= 0xdfff and index and 0xd800 <= codes[index - 1] <= 0xdbff:
            chars.append('')  # The preceding index holds the combined scalar.
        elif 0xd800 <= code <= 0xdfff or code > 0x10ffff:
            chars.append('\ufffd')
            malformed += 1
        else:
            chars.append(chr(code) if code else '')
    return chars, malformed


def effective_font_runs(path):
    """Measure extractable glyphs after the PDF's effective transformations.

    PDFium resolves nested Form XObjects and standard CJK mappings. Its font
    size is nominal: multiply by the transformed vertical em vector, including
    rotation. This measures typography, not whether text is prose or a script.
    Outlined/raster text and clipping/visibility still require visual review.
    """
    import pypdfium2 as pdfium
    from pypdfium2 import raw
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError('Encrypted PDF must be opened by its owner first')
    records = []
    with pdfium.PdfDocument(str(path)) as document:
        for number, page in enumerate(document, 1):
            unit = float(reader.pages[number - 1].get('/UserUnit', 1))
            if not math.isfinite(unit) or unit <= 0:
                raise ValueError('PDF page has an invalid UserUnit')
            textpage = page.get_textpage()
            try:
                codes = [raw.FPDFText_GetUnicode(textpage, i)
                         for i in range(textpage.count_chars())]
                chars, _ = _unicode_chars(codes)
                runs, unmapped = [], []
                for index, char in enumerate(chars):
                    if ((not char and codes[index] == 0 and raw.FPDFText_IsGenerated(textpage, index) != 1)
                            or char == '\ufffd'):
                        unmapped.append({'page': number, 'index': index, 'id': f'{number}:{index}',
                                         'unicode_code': codes[index],
                                         'context': ''.join(chars[max(0, index - 35):index + 36])})
                    if not char:
                        continue
                    if char.isspace() or raw.FPDFText_IsGenerated(textpage, index) == 1:
                        continue
                    matrix = raw.FS_MATRIX()
                    if not raw.FPDFText_GetMatrix(textpage, index, ctypes.byref(matrix)):
                        raise ValueError(f'Cannot measure PDF glyph on page {number}, index {index}')
                    size = raw.FPDFText_GetFontSize(textpage, index) * math.hypot(matrix.c, matrix.d) * unit
                    if not math.isfinite(size) or size <= 0:
                        raise ValueError(f'Invalid PDF glyph size on page {number}, index {index}')
                    size = round(size, 5)
                    previous = runs[-1] if runs else None
                    between = ''.join(chars[previous['last_index'] + 1:index]) if previous else ''
                    if previous and previous['size_pdf_bp'] == size and not between.strip():
                        previous['text'] += between + char
                        previous['last_index'] = index
                    else:
                        runs.append({'page': number, 'first_index': index, 'last_index': index,
                                     'text': char, 'size_pdf_bp': size})
                for run in runs:
                    first, last = run['first_index'], run['last_index']
                    run['id'] = f'{number}:{first}:{last}'
                    run['context'] = ''.join(chars[max(0, first - 35):last + 36])
                    run['size_tex_pt'] = round(run['size_pdf_bp'] * 72.27 / 72, 5)
                records.append({'page': number, 'runs': runs, 'unmapped_glyphs': len(unmapped),
                                'unmapped_runs': unmapped})
            finally:
                textpage.close()
                page.close()
    return records


def needs_collection_mapping(reader):
    for page in reader.pages:
        resources = page.get('/Resources')
        resources = resources.get_object() if resources is not None else {}
        fonts = resources.get('/Font')
        fonts = fonts.get_object() if fonts is not None else {}
        for reference in fonts.values():
            font = reference.get_object()
            if font.get('/Subtype') != '/Type0' or '/ToUnicode' in font:
                continue
            for child in font.get('/DescendantFonts', []):
                info = child.get_object().get('/CIDSystemInfo')
                info = info.get_object() if info is not None else {}
                if info.get('/Registry') == 'Adobe' and info.get('/Ordering') in {'GB1', 'CNS1', 'Japan1', 'Korea1', 'KR'}:
                    return True
    return False


def extract_pages(path):
    """Return text and dominant font size; neither certifies visual correctness."""
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError('Encrypted PDF must be opened by its owner first')
    if needs_collection_mapping(reader):
        import pypdfium2 as pdfium
        from pypdfium2 import raw
        records = []
        with pdfium.PdfDocument(str(path)) as document:
            for page in document:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range()
                    sizes = collections.Counter()
                    for index in range(textpage.count_chars()):
                        code = raw.FPDFText_GetUnicode(textpage, index)
                        if code and not chr(code).isspace():
                            sizes[round(raw.FPDFText_GetFontSize(textpage, index), 1)] += 1
                    records.append({'text': text, 'body_size': sizes.most_common(1)[0][0] if sizes else None,
                                    'text_backend': 'pdfium-standard-cjk-mapping'})
                finally:
                    textpage.close()
                    page.close()
        return records
    records = []
    for page in reader.pages:
        sizes = collections.Counter()

        def visitor(text, cm, tm, font, size):
            if text.strip():
                effective = float(size) * abs(float(tm[0]) if tm[0] else 1) * abs(float(cm[0]) if cm[0] else 1)
                sizes[round(effective, 1)] += len(text.strip())
        text = page.extract_text(visitor_text=visitor) or ''
        records.append({'text': text, 'body_size': sizes.most_common(1)[0][0] if sizes else None,
                        'text_backend': 'pypdf'})
    return records
