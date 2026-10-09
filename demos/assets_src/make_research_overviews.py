"""Research case covers, using the same Canvas and palette as the contest cases.

Run from the repository root with uv run --locked python
  demos/assets_src/make_research_overviews.py
Font faces are selected by name from local collections; font files are not shipped.
"""
from __future__ import annotations

import json
import tempfile
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from fontTools.ttLib import TTCollection
from pypdf import PdfReader
from make_overviews import Canvas, ROOT, TEAL, CLAY, INK, GREY, RULE, STYLE

PROFILE = STYLE["profiles"]["research"]
TYPE = PROFILE["typography"]
LAYOUT = PROFILE["layout"]


class ResearchCanvas(Canvas):
    def __init__(self, lang, faces):
        super().__init__(lang)
        self.faces = faces[lang]

    def text(self, x, y, s, px, color=INK, kind='sans', ha='left', weight='normal', rotation=0):
        self.ax.text(x,y,s,fontsize=px*.72,color=color,fontproperties=self.faces[kind],
                     ha=ha,va='center',rotation=rotation)

    def style_ticks(self, a):
        for lab in a.get_xticklabels()+a.get_yticklabels():
            lab.set_fontproperties(self.faces['sans'])
            lab.set_fontsize(TYPE['axis'])

    def save(self, path):
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            self.fig.canvas.draw()
        missing = [str(w.message) for w in recorded if 'Glyph' in str(w.message) and 'missing' in str(w.message)]
        if missing:
            raise ValueError('Font coverage failure: ' + '; '.join(missing))
        renderer=self.fig.canvas.get_renderer()
        boxes=[]
        for a in self.fig.axes:
            texts=list(a.texts)+(a.get_xticklabels()+a.get_yticklabels() if a.axison else [])
            for t in texts:
                if not t.get_visible() or not t.get_text(): continue
                b=t.get_window_extent(renderer)
                if b.x0 < 0 or b.x1 > 1920 or b.y0 < 0 or b.y1 > 1080:
                    raise ValueError(f'Text outside canvas: {t.get_text()}')
                boxes.append((t,b))
                if a is self.ax:
                    x,y=t.get_position()
                    if x >= LAYOUT['facts_x'] and 374 <= y <= 833:
                        if b.x0 < LAYOUT['facts_x']-2 or b.x1 > 1795:
                            raise ValueError('Fact exceeds its column: ' + t.get_text())
        for i,(left,b) in enumerate(boxes):
            for right,c in boxes[i+1:]:
                if min(b.x1,c.x1)>max(b.x0,c.x0)+1 and min(b.y1,c.y1)>max(b.y0,c.y0)+1:
                    raise ValueError(f'Text overlap: {left.get_text()} / {right.get_text()}')
        super().save(path)


def local_faces(temporary):
    """Read exact local faces from the shared profile; no guessed TTC indices."""
    faces={}
    for lang, roles in PROFILE['fonts'].items():
        faces[lang]={}
        for kind, spec in roles.items():
            path=Path(font_manager.findfont(spec['family'],fallback_to_default=False))
            if path.suffix.lower() not in ('.ttc','.otc'):
                faces[lang][kind]=font_manager.FontProperties(fname=path)
                continue
            collection=TTCollection(path)
            matches=[f for f in collection.fonts if spec['postscript'] in
                     [n.toUnicode() for n in f['name'].names if n.nameID==6]]
            if len(matches)!=1:raise ValueError(f"Exact font face not found: {spec['postscript']}")
            target=temporary/f"{spec['postscript']}.ttf";matches[0].save(target)
            faces[lang][kind]=font_manager.FontProperties(fname=target)
            collection.close()
    return faces


def frame(c, code, pages, title, subtitle):
    c.text(125,LAYOUT['header_y'],'P R A X I S',18,TEAL)
    c.text(1795,LAYOUT['header_y'],f'{code}   /   {pages:02d} PP',TYPE['folio'],GREY,ha='right')
    c.ax.plot([125,1795],[LAYOUT['rule_y']]*2,color=RULE,lw=.8)
    c.text(125,LAYOUT['title_y'],title,TYPE['title'],kind='serif')
    c.text(125,LAYOUT['subtitle_y'],subtitle,TYPE['subtitle'],GREY)
    c.ax.plot([LAYOUT['divider_x']]*2,[374,833],color=RULE,lw=.8)
    c.ax.plot([125,1795],[LAYOUT['footer_rule_y']]*2,color=RULE,lw=.8)


def fact(c,y,label,value,explanation,colour=INK):
    x=LAYOUT['facts_x']
    c.text(x,y,label,TYPE['label'],GREY)
    c.text(x,y+58,value,TYPE['value'],colour)
    c.text(x,y+114,explanation,TYPE['explanation'],GREY)


def plot(c):
    a=c.plot_axes(*LAYOUT['chart'])
    a.grid(axis='y',color=RULE,lw=.6)
    a.tick_params(length=0,pad=10)
    for spine in a.spines.values():spine.set_visible(False)
    return a


def collatz(lang,faces):
    case=ROOT/'demos/collatz-research'
    cert=json.loads((case/'reproduce/runs/certificate.json').read_text())
    rows=cert['checkpoints'];cap=cert['cap'];H=cert['finite_scan']['domain'][1]
    pages=len(PdfReader(case/'deliverables/note.pdf').pages)
    zh=lang=='zh'
    c=ResearchCanvas(lang,faces)
    frame(c,'COLLATZ',pages,
          '收缩，何时意味着下降' if zh else 'When contraction implies descent',
          'Collatz 迭代的有限深度认证' if zh else 'An exact certificate for the shortcut Collatz map')
    a=plot(c)
    a.semilogy([r['k'] for r in rows],[r['unresolved_density_float'] for r in rows],
               color=TEAL,marker='o',lw=1.35,markersize=5,linestyle=(0,(2,3)))
    a.set_xlim(0,1050);a.set_ylim(1e-20,1)
    a.set_xticks([0,256,512,768,1024]);a.set_yticks([1e-2,1e-6,1e-10,1e-14,1e-18])
    a.set_yticklabels([r'$10^{-2}$',r'$10^{-6}$',r'$10^{-10}$',r'$10^{-14}$',r'$10^{-18}$']);a.minorticks_off()
    c.style_ticks(a)
    c.text(182,365,'未覆盖自然密度' if zh else 'Unclassified natural density',TYPE['label'],GREY)
    c.text(638,LAYOUT['axis_label_y'],'首次系数收缩深度 K' if zh else 'First-contraction depth K',TYPE['label'],GREY,ha='center')
    fact(c,413,'已认证的收缩深度' if zh else 'Certified first-contraction depth',str(cap),
         '对起始整数不设大小上限' if zh else 'No upper bound on the starting integer',TEAL)
    fact(c,631,'潜在例外的扫描上限' if zh else 'Potential-exception scan bound',f'{H:,}',
         '精确整数运算 · 独立递推核验' if zh else 'Exact integers; independently checked recurrences')
    c.text(125,LAYOUT['claim_y'],f'对所有 n > 1，若 τ(n) ≤ {cap}，则 σ(n) = τ(n)' if zh else
           f'For every n > 1: τ(n) ≤ {cap} implies σ(n) = τ(n)',TYPE['footer'])
    c.text(125,LAYOUT['condition_y'],'七个核验深度的密度；虚线仅引导阅读，未覆盖部分仍大于零' if zh else
           'Seven certified-depth checkpoints; dotted guides do not interpolate the remaining density',TYPE['explanation'],GREY)
    c.save(case/'assets'/f'overview-{lang}.png')


def domino(lang,faces):
    case=ROOT/'demos/domino-research'
    data=json.loads((case/'reproduce/reference/results.json').read_text())
    values=data['counts']['transfer_matrix_n0_to_16'];zh=lang=='zh'
    pages=len(PdfReader(case/'deliverables/note.pdf').pages)
    c=ResearchCanvas(lang,faces)
    frame(c,'DOMINO TILINGS',pages,
          '发现规律，还要证明为何成立' if zh else 'From a pattern to a proof',
          '经典组合计数的重建 · 3 × 2n 棋盘' if zh else 'A classical enumeration reconstructed for 3 × 2n boards')
    a=plot(c)
    a.semilogy(range(len(values)),values,color=TEAL,lw=1.7)
    a.scatter(range(13),values[:13],s=23,color=TEAL,zorder=3)
    a.scatter(range(13,17),values[13:],s=35,color=CLAY,zorder=3)
    a.set_xlim(-.2,16.2);a.set_xticks([0,4,8,12,16]);a.set_ylim(.6,3e9)
    a.set_yticks([1,1e3,1e6,1e9]);a.set_yticklabels(['1',r'$10^3$',r'$10^6$',r'$10^9$']);a.minorticks_off();c.style_ticks(a)
    c.text(182,365,'精确铺法数 a(n)' if zh else 'Exact tiling count a(n)',TYPE['label'],GREY)
    c.text(638,LAYOUT['axis_label_y'],'棋盘宽度 2n，横轴为 n' if zh else 'n, for a board of width 2n',TYPE['label'],GREY,ha='center')
    fact(c,413,'相互核对的证明路线' if zh else 'Distinct proof strategies','2',
         '棋盘拆分 · 状态转移与有限核对' if zh else 'Decomposition and a finite transfer-matrix check',TEAL)
    fact(c,631,'发现项与留出项' if zh else 'Discovery and held-out terms','13 + 4',
         '青绿用于发现，棕色用于留出检验' if zh else 'Teal for discovery; clay for held-out checks')
    c.text(125,LAYOUT['claim_y'],'a(n) = 4a(n−1) − a(n−2)，n ≥ 2' if zh else
           'a(n) = 4a(n−1) − a(n−2), for n ≥ 2',TYPE['footer'])
    c.text(125,LAYOUT['condition_y'],'计算提供线索；严格证明把有限观察推广到全部棋盘尺寸' if zh else
           'The computation suggests a recurrence; structural proofs establish it at every board size',TYPE['explanation'],GREY)
    c.save(case/'assets'/f'overview-{lang}.png')


def main():
    for name in ('collatz-research','domino-research'):
        (ROOT/'demos'/name/'assets').mkdir(parents=True,exist_ok=True)
    temporary_root=ROOT/'.session';temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='research-covers-',dir=temporary_root) as temporary:
        faces=local_faces(Path(temporary))
        for lang in ('zh','en'):
            collatz(lang,faces);domino(lang,faces)
    print('Four research covers rebuilt from archived numbers; temporary font faces removed.')


if __name__=='__main__':main()
