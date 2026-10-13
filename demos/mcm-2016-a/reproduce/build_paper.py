"""Recompile the selected manuscript; numerical baseline replay has its own entry."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
for parent in ROOT.parents:
    if (parent/'scripts/paper_template.py').is_file():
        sys.path.insert(0, str(parent)); break
from scripts.paper_template import check, compile_in_place, mcm_identity, MCM_SIMULATION_TEAM
from scripts.freeze_pdf import freeze


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, help='Retained CLI compatibility: only the fixed baseline archive is accepted')
    parser.add_argument('--candidate', action='store_true', help='Compile an unsealed preview for actual page review')
    parser.add_argument('--font-review', type=Path)
    parser.add_argument('--page-review', type=Path)
    args = parser.parse_args()
    if args.run is not None and args.run.resolve() != (ROOT/'reference').resolve():
        parser.error('Selected manuscript uses fixed evidence; use build_report.py for a changed numerical baseline')
    source = ROOT.parent/'report/paper.tex'
    record = json.loads((ROOT.parent/'verification.json').read_text(encoding='utf-8'))
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record['pdf']['tex_sha256']:
        raise ValueError('Selected manuscript source changed; update actual science/format review before delivery')
    check(raw.decode('utf-8'), 'mcm', layout_mode='current')
    if mcm_identity(raw.decode('utf-8'))['team'] != MCM_SIMULATION_TEAM:
        raise ValueError('Current demo must use the fixed simulation team identity')
    output = ROOT/'paper'; output.mkdir(exist_ok=True)
    tex = output/'paper.tex'; tex.write_bytes(raw)
    compile_in_place(tex, 'mcm')
    pdf = tex.with_suffix('.pdf')
    if args.candidate:
        print(json.dumps({'candidate':str(pdf),'review_required':True,'selected_pages':record['pdf']['pages_total']})); return
    target = ROOT/'submission/paper.pdf'
    receipt = freeze(pdf,target,tex=tex,contest='mcm',build_receipt=tex.with_suffix('.build.json'),
                     font_review=args.font_review or ROOT.parent/'current-font-review.json',
                     page_review=args.page_review or ROOT.parent/'current-page-review.json')
    target.with_suffix('.pdf.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'pdf':str(target),'sealed':True}))


if __name__ == '__main__':
    main()
