"""Extract text with explicit support for standard CJK CID collections.

xdvipdfmx deliberately omits ToUnicode for Adobe character collections.
Those PDFs are valid; consumers need the collection's Unicode mapping.
Use PDFium's built-in mapping instead of interpreting CIDs as Unicode.
https://github.com/TeX-Live/texlive-source/blob/trunk/texk/dvipdfm-x/type0.c
"""
import collections

from pypdf import PdfReader


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
