"""Research case covers, using the same Canvas and palette as the contest cases.

Run from the repository root with uv run --locked python
  demos/assets_src/make_research_overviews.py
Font faces are selected by name from local collections; font files are not shipped.
"""
from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader
from showcase import ACCENT, COMPARISON, LAYOUT, STROKES, Canvas, FontSession, L

ROOT = Path(__file__).resolve().parents[2]
CHART = LAYOUT['chart']


def plot(c):
    a = c.axes(*CHART)
    a.spines['bottom'].set_visible(False)
    a.tick_params(axis='x', length=0)
    return a


def collatz(lang):
    case=ROOT/'demos/collatz-research'
    cert=json.loads((case/'reproduce/runs/certificate.json').read_text())
    rows=cert['checkpoints'];cap=cert['cap'];H=cert['finite_scan']['domain'][1]
    pages=len(PdfReader(case/'deliverables/paper.pdf').pages)
    zh=lang=='zh'
    c=Canvas(lang)
    c.frame(f'RESEARCH  ·  COLLATZ  ·  {pages} PAGES',
          '收缩，何时意味着下降' if zh else 'When contraction is descent',
          'Collatz 迭代的有限深度认证' if zh else 'An exact certificate for the shortcut Collatz map')
    a=plot(c)
    a.semilogy([r['k'] for r in rows],[r['unresolved_density_float'] for r in rows],
               color=ACCENT,marker='o',lw=STROKES['guide'],markersize=STROKES['marker'],linestyle=(0,(2,3)))
    a.set_xlim(0,1050);a.set_ylim(1e-20,1)
    a.set_xticks([0,256,512,768,1024]);a.set_yticks([1e-2,1e-6,1e-10,1e-14,1e-18])
    a.set_yticklabels([r'$10^{-2}$',r'$10^{-6}$',r'$10^{-10}$',r'$10^{-14}$',r'$10^{-18}$']);a.minorticks_off()
    c.ticks(a)
    c.text(L,LAYOUT['caption_y'],'未覆盖自然密度' if zh else 'Unclassified natural density','caption')
    c.text((CHART[0]+CHART[1])/2,LAYOUT['axis_label_y'],'首次系数收缩深度 K' if zh else 'First-contraction depth K','key',ha='center')
    c.facts([('已认证的收缩深度' if zh else 'Certified first-contraction depth',str(cap),
              '对起始整数不设大小上限' if zh else 'No upper bound on the starting integer','lead'),
             ('潜在例外的扫描上限' if zh else 'Potential-exception scan bound',f'{H:,}',
              '精确整数运算 · 独立递推核验' if zh else 'Exact integers; independent recurrence checks','lead')])
    c.footer(f'对所有 n > 1，若 τ(n) ≤ {cap}，则 σ(n) = τ(n)' if zh else
             f'For every n > 1: τ(n) ≤ {cap} implies σ(n) = τ(n)',
             '七个核验深度的密度；虚线仅引导阅读，未覆盖部分仍大于零' if zh else
             'Seven certified-depth checkpoints; dotted guides do not interpolate the remaining density')
    c.save(case/'assets'/f'overview-{lang}.png')


def domino(lang):
    case=ROOT/'demos/domino-research'
    data=json.loads((case/'reproduce/reference/results.json').read_text())
    values=data['counts']['transfer_matrix_n0_to_16'];zh=lang=='zh'
    pages=len(PdfReader(case/'deliverables/paper.pdf').pages)
    c=Canvas(lang)
    c.frame(f'RESEARCH  ·  DOMINO TILINGS  ·  {pages} PAGES',
          '发现规律，还要证明为何成立' if zh else 'From a pattern to a proof',
          '经典组合计数的重建 · 3 × 2n 棋盘' if zh else 'A classical enumeration reconstructed for 3 × 2n boards')
    a=plot(c)
    a.semilogy(range(len(values)),values,color=ACCENT,lw=STROKES['secondary'])
    a.scatter(range(13),values[:13],s=STROKES['marker']**2,color=ACCENT,zorder=3)
    a.scatter(range(13,17),values[13:],s=(STROKES['marker']+2)**2,color=COMPARISON,zorder=3)
    a.set_xlim(-.2,16.2);a.set_xticks([0,4,8,12,16]);a.set_ylim(.6,3e9)
    a.set_yticks([1,1e3,1e6,1e9]);a.set_yticklabels(['1',r'$10^3$',r'$10^6$',r'$10^9$']);a.minorticks_off();c.ticks(a)
    c.text(L,LAYOUT['caption_y'],'精确铺法数 a(n)' if zh else 'Exact tiling count a(n)','caption')
    c.text((CHART[0]+CHART[1])/2,LAYOUT['axis_label_y'],'棋盘宽度 2n，横轴为 n' if zh else 'n, for a board of width 2n','key',ha='center')
    c.facts([('相互核对的证明路线' if zh else 'Distinct proof strategies','2',
              '棋盘拆分 · 状态转移与有限核对' if zh else 'Decomposition; finite transfer-matrix checks','lead'),
             ('发现项与留出项' if zh else 'Discovery and held-out terms','13 + 4',
              '群青用于发现，朱红用于留出检验' if zh else 'Blue for discovery; vermilion for held-out checks','lead')])
    c.footer('a(n) = 4a(n−1) − a(n−2)，n ≥ 2' if zh else 'a(n) = 4a(n−1) − a(n−2), for n ≥ 2',
             '计算提供线索；严格证明把有限观察推广到全部棋盘尺寸' if zh else
             'The computation suggests a recurrence; structural proofs establish it at every board size')
    c.save(case/'assets'/f'overview-{lang}.png')


def main():
    for name in ('collatz-research','domino-research'):
        (ROOT/'demos'/name/'assets').mkdir(parents=True,exist_ok=True)
    with FontSession():
        for lang in ('zh','en'):
            collatz(lang);domino(lang)
    print('Four research covers rebuilt from archived numbers; temporary font faces removed.')


if __name__=='__main__':main()
