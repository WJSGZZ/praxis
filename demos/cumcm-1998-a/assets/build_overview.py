"""Build bilingual README graphics from the actual demo report preview.

Uses Matplotlib and a locally available CJK font; fonts are not distributed.
Set PRAXIS_CJK_FONT when the default macOS font is unavailable.
"""
from pathlib import Path
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch

root = Path(__file__).resolve().parent
paper, ink, teal, muted = '#F7F5F0', '#182C38', '#177A75', '#53656F'
font = Path(os.environ.get('PRAXIS_CJK_FONT',
                           '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
if not font.is_file():
    raise FileNotFoundError('Set PRAXIS_CJK_FONT to a locally installed CJK font.')
cjk = FontProperties(fname=str(font))
for lang in ['zh', 'en']:
    fig = plt.figure(figsize=(14, 7.3), facecolor=paper)
    canvas = fig.add_axes([0, 0, 1, 1]); canvas.axis('off')
    canvas.set_xlim(0, 1); canvas.set_ylim(0, 1)
    fp = {'fontproperties': cjk} if lang == 'zh' else {'fontfamily': 'DejaVu Sans'}
    def label(x, y, text, size, color=ink, **kw):
        canvas.text(x, y, text, fontsize=size, color=color, va='top', **fp, **kw)
    label(.06, .93, 'P R A X I S', 15, teal)
    title = '把一个问题，推进成完整作品。' if lang == 'zh' else 'Turn a problem into\na complete piece of work.'
    label(.06, .81, title, 26 if lang == 'zh' else 25, linespacing=1.4)
    subtitle = '数学建模 · 独立验证 · 可复现报告' if lang == 'zh' else 'Modeling. Independent checks. Reproducible reports.'
    label(.06, .64 if lang == 'zh' else .60, subtitle, 14, muted)
    label(.06, .52, '国赛 1998 A：投资的收益和风险' if lang == 'zh' else 'CUMCM 1998 A: Investment returns and risk', 13, teal)
    steps = [('01', '分析问题', '定义与约束'), ('02', '建立模型', '实现与求解'),
             ('03', '检验结果', '对照与证明'), ('04', '交付报告', '论文与代码')]
    if lang == 'en':
        steps = [('01', 'Frame', 'Definitions'), ('02', 'Model', 'Solve'),
                 ('03', 'Validate', 'Check & prove'), ('04', 'Deliver', 'Report & code')]
    for i, (n, heading, detail) in enumerate(steps):
        x = .06 + i * .14
        canvas.add_patch(FancyBboxPatch((x, .235), .12, .16,
                        boxstyle='round,pad=0.008,rounding_size=0.009',
                        facecolor='#FFFFFF', edgecolor='#D6DEDA', linewidth=1))
        label(x+.014, .374, n, 9, teal)
        label(x+.014, .338, heading, 13)
        label(x+.014, .288, detail, 9, muted)
        if i < 3:
            canvas.annotate('', xy=(x+.139, .31), xytext=(x+.122, .31),
                            arrowprops={'arrowstyle': '->', 'color': teal, 'lw': 1.2})
    label(.06, .15, '16 页报告  /  12 项模型检查  /  完整复现代码' if lang == 'zh'
          else '16-page report  /  12 model checks  /  Runnable source', 12)
    label(.06, .075, '点击图片，查看完整 Demo →' if lang == 'zh'
          else 'Open the full case, report, and source →', 11, teal)
    # Render the actual abstract page, rather than inventing a paper mockup.
    canvas.add_patch(FancyBboxPatch((.705, .132), .244, .695,
                    boxstyle='square,pad=0', facecolor='#E3E7E1', edgecolor='none'))
    page = fig.add_axes([.69, .145, .244, .695])
    page.imshow(plt.imread(root / 'report-abstract.png'))
    page.axis('off')
    label(.695, .89, '真实报告 · 摘要页' if lang == 'zh' else 'Actual report · abstract', 10, muted)
    fig.savefig(root / f'overview-{lang}.png', dpi=160, facecolor=paper)
    plt.close(fig)
