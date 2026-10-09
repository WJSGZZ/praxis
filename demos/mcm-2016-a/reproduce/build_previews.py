"""Render case-page excerpts from an explicitly selected, reviewed manuscript."""
import argparse
import hashlib
import json
from pathlib import Path

import pypdfium2 as pdfium
from pypdf import PdfReader


def build(pdf: Path, output: Path) -> dict:
    pages = PdfReader(pdf).pages
    # Locate the actual proof, rather than retaining a page number from an old edition.
    proof = next(i for i, p in enumerate(pages)
                 if 'Step 1, an identity' in p.extract_text())
    output.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf))
    record = {'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(), 'scale': 1.6, 'previews': {}}
    try:
        for name, index in [('report-summary.png', 0), ('report-proof.png', proof)]:
            page = doc[index]
            bitmap = page.render(scale=1.6)
            try:
                bitmap.to_pil().save(output / name, optimize=True)
            finally:
                bitmap.close()
                page.close()
            record['previews'][name] = {'page': index + 1,
                'sha256': hashlib.sha256((output / name).read_bytes()).hexdigest()}
    finally:
        doc.close()
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.pdf, args.output), indent=2))
