"""Build bilingual homepage covers with the shared Praxis visual language."""
from pathlib import Path
import sys
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parents[2]))
from design.style import showcase_style

with showcase_style() as s:
    for lang in ['zh', 'en']:
        fig, ax = s.canvas()
        s.header(ax, 'CASE 01  /  CUMCM 1998 A')
        title = '从一道题，\n到一份完整报告。' if lang == 'zh' else 'Mathematical modeling.\nEvidence you can run.'
        s.text(ax, .065, .805, title, lang=lang, role='display', size=38 if lang == 'zh' else 30, linespacing=1.22)
        s.text(ax, .065, .57 if lang == 'zh' else .59,
               '从题目分析到结果核验，再到论文与代码交付。' if lang == 'zh' else
               'An agent workflow for models, checks, and a finished report.',
               lang=lang, role='body', size=12 if lang == 'en' else 13, color='muted')
        s.text(ax, .065, .465, '看一次完整的国赛建模' if lang == 'zh' else 'See the workflow in practice',
               lang=lang, role='section', size=18)
        # A flat numbered sequence belongs to the shared page grid, not floating cards.
        steps = ['读懂题目', '建立模型', '核验结论', '完成论文'] if lang == 'zh' else ['Define', 'Solve', 'Check', 'Report']
        details = ['定义与约束', '实现与求解', '对照与证明', '论文与代码'] if lang == 'zh' else ['Set the scope', 'Run the model', 'Test the claims', 'Show the evidence']
        for i, (heading, detail) in enumerate(zip(steps, details)):
            x = .065 + i * .145
            ax.plot([x, x+.12], [.35, .35], color=s.c['rule'], lw=.8)
            s.text(ax, x, .332, f'0{i+1}', role='note', color='accent')
            s.text(ax, x, .295, heading, lang=lang, role='body', size=14)
            s.text(ax, x, .247, detail, lang=lang, role='note', color='muted')
        # Keep the actual abstract intact and clearly separated from the cover.
        ax.add_patch(Rectangle((.678, .224), .25, .63, facecolor=s.c['surface'], edgecolor=s.c['rule'], linewidth=.8))
        page = fig.add_axes([.680, .226, .246, .626]); page.imshow(plt.imread(root/'report-abstract.png')); page.axis('off')
        s.text(ax, .678, .196, '真实报告 · 摘要页' if lang == 'zh' else 'Actual report · abstract',
               lang=lang, role='note', color='muted')
        ax.plot([.065, .935], [.155, .155], color=s.c['rule'], lw=.8)
        values = [('16', '页完整报告'), ('12', '项模型检查'), ('2', '份提交文件')] if lang == 'zh' else [('16', 'report pages'), ('12', 'model checks'), ('2', 'deliverables')]
        for i, (value, caption) in enumerate(values):
            x = .065 + i*.18
            s.text(ax, x, .13, value, lang=lang, role='metric')
            s.text(ax, x+.057, .113, caption, lang=lang, role='note', color='muted')
        s.text(ax, .935, .113, '查看完整 Demo →' if lang == 'zh' else 'Explore the complete case →',
               lang=lang, role='label', color='accent', ha='right')
        s.save(fig, root/f'overview-{lang}.png')
