"""Bilingual case cards from actual archived temperatures and water-use results."""
from pathlib import Path
import sys,json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from design.style import showcase_style
HERE=Path(__file__).resolve().parent
R=json.loads((HERE.parent/'reproduce/reference/results.json').read_text());Z=np.load(HERE.parent/'reproduce/reference/trajectory.npz');p=R['parameters'];b=R['policy'];a=R['analytic']
with showcase_style() as s:
 for lang in ['zh','en']:
  fig,canvas=s.canvas();s.header(canvas,'CASE 02  /  MCM 2016 A')
  title='水温要均匀，策略就不能只看平均值。' if lang=='zh' else 'A warm average can hide a cold corner.'
  s.text(canvas,.065,.84,title,lang=lang,role='display',size=34 if lang=='zh' else 32)
  sub='三维热网络 · 解析基线 · 独立积分与能量核验' if lang=='zh' else 'Spatial heat balance, a proved benchmark, and independent numerical checks.'
  s.text(canvas,.065,.75,sub,lang=lang,role='body',color='muted',size=17)
  legend='青绿：均值 · 虚线：最冷单元 · 阴影：温度范围' if lang=='zh' else 'Mean (teal) · Coldest cell (dashed) · Spatial range (shade)'
  s.text(canvas,.095,.685,legend,lang=lang,role='note',size=14,color='muted')
  ax=fig.add_axes([.095,.24,.46,.40]);T=Z['T'];t=Z['t']/60
  ax.fill_between(t,T.min(1),T.max(1),color=s.c['accent'],alpha=.12)
  ax.plot(t,T@Z['volume']/Z['volume'].sum(),color=s.c['accent'],lw=2)
  ax.plot(t,T.min(1),color=s.c['comparison'],lw=1.8,ls='--');ax.axhline(39,color=s.c['muted'],lw=.9,ls=':')
  ax.set_xlim(0,30);ax.set_ylim(38.8,40.5);ax.set_xticks([0,10,20,30]);ax.set_yticks([39,39.5,40,40.5]);ax.set_facecolor(s.c['paper']);ax.spines[['top','right']].set_visible(False)
  for edge in ['left','bottom']:ax.spines[edge].set_color(s.c['rule'])
  for tick in ax.get_xticklabels()+ax.get_yticklabels():tick.set_fontproperties(s.font(lang));tick.set_fontsize(14);tick.set_color(s.c['muted'])
  ax.set_xlabel('时间 / min' if lang=='zh' else 'Time / min',fontproperties=s.font(lang),fontsize=15,color=s.c['muted'])
  ax.set_ylabel('水温 / °C' if lang=='zh' else 'Temperature / °C',fontproperties=s.font(lang),fontsize=15,color=s.c['muted'])
  lines=[('三维候选策略' if lang=='zh' else 'Accepted spatial policy',b['water_l'],'accent'),('理想充分混合' if lang=='zh' else 'Ideal well-mixed optimum',a['mixed_optimum_l'],'comparison'),('能量下界' if lang=='zh' else 'Conditional energy lower bound',a['energy_lower_bound_l'],'muted')]
  for j,(label,value,color) in enumerate(lines):
   y=.63-j*.15;s.text(canvas,.64,y,label,lang=lang,role='body',size=17,color='muted');s.text(canvas,.64,y-.043,f'{value:.2f} L',role='metric',size=32,color=color)
  footer='40°C 起始 · 39°C 下限 · 30 分钟 · 情景参数，非实测' if lang=='zh' else '40°C start · 39°C floor · 30 min · Scenario inputs, not measured data'
  s.text(canvas,.065,.145,footer,lang=lang,role='note',size=15,color='muted')
  link='19 页完整报告（含 AI 披露） · 17 项检查 · 查看美赛 Demo →' if lang=='zh' else 'Read the 19-page report with AI disclosure · Inspect 17 recorded checks →'
  s.text(canvas,.065,.08,link,lang=lang,role='body',size=17,color='accent')
  s.save(fig,HERE/f'overview-{lang}.png')
