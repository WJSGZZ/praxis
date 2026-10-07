"""Render the showcase from the report's recorded numerical results."""
from pathlib import Path
import csv
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

root = Path(__file__).resolve().parents[1]
results = json.loads((root / 'reproduce/reference/results.json').read_text())
ink, teal, gold, paper = '#182C38', '#177A75', '#AC6B24', '#F7F5F0'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})
fig, axes = plt.subplots(1, 2, figsize=(14, 7.6))
fig.patch.set_facecolor(paper)
fig.subplots_adjust(left=.07, right=.965, bottom=.22, top=.64, wspace=.28)
fig.text(.07, .91, 'PRAXIS  /  CUMCM 1998 A', color=teal, fontsize=12, weight='bold')
fig.text(.07, .82, 'A portfolio. A frontier. A proof.', color=ink, fontsize=27,
         fontfamily='DejaVu Serif')
fig.text(.07, .755, 'An end-to-end modeling case, with a complete report and runnable evidence.',
         color=ink, fontsize=12)
for ax, key, color, title in zip(axes, ['four', 'fifteen'], [teal, gold],
                               ['4 assets', '15 assets']):
    with (root / f'reproduce/reference/{key}-frontier.csv').open() as f:
        rows = list(csv.DictReader(f))
    x = [float(r['risk_cap']) for r in rows]
    y = [float(r['net_return']) for r in rows]
    selected = results['groups'][key]['selected'][1]
    ax.set_facecolor(paper)
    ax.plot(x, y, color=color, lw=2.7)
    ax.fill_between(x, .05, y, color=color, alpha=.07)
    ax.axhline(.05, color=ink, alpha=.35, lw=1, ls='--')
    ax.scatter(selected['risk_cap'], selected['net_return'], s=65, color=color,
               edgecolors=paper, linewidth=1.5, zorder=3)
    ax.set_title(title, loc='left', color=ink, fontsize=15, pad=24)
    ax.text(.98, 1.17, f"{selected['net_return']:.2%}", transform=ax.transAxes,
            ha='right', va='top', fontsize=21, color=color, weight='bold')
    ax.text(.98, 1.04, f"at {selected['risk_cap']:.0%} risk limit", transform=ax.transAxes,
            ha='right', va='top', fontsize=10, color=ink)
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=1 if key == 'four' else 0))
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_xlabel('Risk limit', color=ink, labelpad=10)
    ax.set_ylabel('Optimal net return', color=ink, labelpad=8)
    ax.set_xlim(0, max(x))
    ax.set_ylim(.025, max(y) + .025)
    ax.spines[['top', 'right']].set_visible(False)
    for side in ['bottom', 'left']:
        ax.spines[side].set_color('#CBCFCB')
    ax.tick_params(colors=ink, length=0, pad=8)
    ax.grid(axis='y', color=ink, alpha=.08)
fig.text(.07, .10, '16-page report   /   12 model checks   /   analytical optimality certificates',
         fontsize=12, color=ink)
fig.text(.07, .045, 'Budget: CNY 1,000,000. Risk = max(single-asset loss amount) / budget. '
         'Dashed line: 5% bank return.', fontsize=9, color='#52616A')
fig.savefig(root / 'assets/risk-return.png', dpi=160, facecolor=paper)
plt.close(fig)
