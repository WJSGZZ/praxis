"""Read-only generic PDF inspection; visual layout review remains necessary."""
import argparse
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader


def inspect_pdf(path, max_pages=None, max_bytes=None, forbidden=()):
    raw = path.read_bytes()
    errors, warnings = [], []
    with path.open('rb') as stream:
        doc = PdfReader(stream)
        if doc.is_encrypted:
            raise ValueError('Encrypted PDF must be opened by its owner first')
        if not doc.pages:
            errors.append('Empty PDF')
        if max_pages is not None and len(doc.pages) > max_pages:
            errors.append('Page count exceeds configured limit')
        if max_bytes is not None and len(raw) > max_bytes:
            errors.append('File exceeds configured byte limit')
        metadata = {str(k): str(v) for k,v in (doc.metadata or {}).items()}
        pages=[]
        texts=[]
        for number,page in enumerate(doc.pages,1):
            text=page.extract_text() or ''
            texts.append(text)
            if not text.strip():
                warnings.append(f'Page {number}: no extracted text; image review required')
            pages.append({'page':number,'size_points':[float(page.mediabox.width),float(page.mediabox.height)],'text_characters':len(text)})
        searchable='\n'.join(texts)+json.dumps(metadata)
        for term in forbidden:
            if term and term.casefold() in searchable.casefold():
                errors.append(f'Configured forbidden term found: {term}')
        return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'total_pages':len(doc.pages),'metadata':metadata,'pages':pages,'errors':errors,'warnings':warnings,'visual_review_required':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('path',type=Path)
    p.add_argument('--max-pages',type=int)
    p.add_argument('--max-bytes',type=int)
    p.add_argument('--forbidden',action='append',default=[])
    a=p.parse_args()
    if any(v is not None and v<1 for v in [a.max_pages,a.max_bytes]):
        p.error('Limits must be positive')
    r=inspect_pdf(a.path,a.max_pages,a.max_bytes,a.forbidden)
    print(json.dumps(r,ensure_ascii=False,indent=2))
    raise SystemExit(1 if r['errors'] else 0)


if __name__=='__main__':
    main()
