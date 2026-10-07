"""Render bilingual risk-return previews from recorded data and shared tokens."""
from pathlib import Path
import csv
import json
import sys
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root.parents[1]))
from design.style import showcase_style, TOKENS
results = json.loads((root/'reproduce/reference/results.json').read_text())

with showcase_style() as s:
    for lang in ['zh', 'en']:
        fig, canvas = s.canvas()
        s.header(canvas, 'CASE 01  /  RESULTS')
        s.text(canvas, .065, .825, '风险的边界，收益的选择。' if lang == 'zh' else
               'Risk limits. Return choices.', lang=lang, role='display', size=30)
        s.text(canvas, .065, .745, '费用、风险与预算进入同一个模型；代表结果另有解析上界核验。' if lang == 'zh' else
               'Fees, risk, and budget in one model. Representative solutions checked against analytical bounds.',
               lang=lang, role='body', color='muted', size=12)
        for i, key in enumerate(['four', 'fifteen']):
            left = .085 + i*.465
            ax = fig.add_axes([left, .245, .36, .365], facecolor=s.c['paper'])
            color = s.c['accent' if key == 'four' else 'comparison']
            with (root/f'reproduce/reference/{key}-frontier.csv').open() as f:
                rows = list(csv.DictReader(f))
            x = [float(r['risk_cap']) for r in rows]; y = [float(r['net_return']) for r in rows]
            selected = results['groups'][key]['selected'][1]
            title = ('四资产' if key == 'four' else '十五资产') if lang == 'zh' else ('4 assets' if key == 'four' else '15 assets')
            s.text(canvas, left, .675, title, lang=lang, role='section', size=19)
            s.text(canvas, left+.36, .688, f"{selected['net_return']:.2%}", role='metric', color='accent' if key == 'four' else 'comparison', ha='right')
            s.text(canvas, left+.36, .64, ('风险上限 ' if lang == 'zh' else 'Risk limit: ')+f"{selected['risk_cap']:.0%}",
                   lang=lang, role='note', color='muted', ha='right')
            ax.plot(x, y, color=color, lw=TOKENS['chart']['line_width'])
            ax.fill_between(x, .05, y, color=color, alpha=TOKENS['chart']['fill_alpha'])
            ax.axhline(.05, color=s.c['muted'], alpha=.6, lw=.8, ls=(0,(4,4)))
            ax.scatter(selected['risk_cap'], selected['net_return'], s=55, color=color, edgecolors=s.c['paper'], linewidth=1.5, zorder=3)
            ax.set_xlim(0, max(x)); ax.set_ylim(.025, max(y)+.025)
            ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=1 if key == 'four' else 0))
            ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
            ax.set_xlabel('风险上限' if lang == 'zh' else 'Risk limit', fontproperties=s.font(lang), fontsize=12, color=s.c['muted'], labelpad=10)
            ax.set_ylabel('最优净收益率' if lang == 'zh' else 'Optimal net return', fontproperties=s.font(lang), fontsize=12, color=s.c['muted'], labelpad=10)
            ax.spines[['top','right']].set_visible(False)
            for side in ['left','bottom']: ax.spines[side].set_color(s.c['rule'])
            ax.tick_params(colors=s.c['muted'], length=0, pad=8, labelsize=11)
            ax.grid(axis='y', color=s.c['ink'], alpha=TOKENS['chart']['grid_alpha'])
        canvas.plot([.065,.935], [.145,.145], color=s.c['rule'], lw=.8)
        s.text(canvas, .065, .12, '资金 100 万元 · 虚线为 5% 银行收益率 · 两组采用不同风险上限' if lang == 'zh' else
               'Budget: CNY 1,000,000 · Dashed line: 5% bank return · Different risk limits across groups', lang=lang, role='note')
        s.text(canvas, .065, .075, '风险口径：最大单项风险损失额 ÷ 总资金。模型结果不代表实际投资收益预测。' if lang == 'zh' else
               'Risk = maximum single-asset loss / budget. Conditional model results, not investment forecasts.',
               lang=lang, role='note', color='muted')
        s.save(fig, root/'assets'/('risk-return-zh.png' if lang == 'zh' else 'risk-return.png'))
