"""Professional single-file MCM report; numerical evidence is supplied, never invented."""
import argparse,hashlib,json,math,re,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
import model,control
TEAM_CONTROL_NUMBER='7391856'
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);args=parser.parse_args()
r=json.loads((args.run/'results.json').read_text(encoding='utf-8'));checks=json.loads((args.run/'checks.json').read_text(encoding='utf-8'))
assert all(c['passed'] for c in checks)
p=r['parameters'];b=r['policy'];a=r['analytic'];sc=r['scenarios'];z=np.load(args.run/'trajectory.npz')
ST=json.loads((args.run/'structure.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in ST['input_sha256'].items()), 'Structural evidence is stale'
E=json.loads((args.run/'extended.json').read_text(encoding='utf-8'));wf=lambda floor:next(f_['constant_l'] for f_ in E['frontier'] if f_['floor']==floor);raw_ctl=E['control']['best'];prov=E['provenance'];lr=E['literature_ranges'];ctl_checks=E['checks']
assert all(c['passed'] for c in ctl_checks)
MC=json.loads((args.run/'mesh_check.json').read_text(encoding='utf-8'))
assert MC.get('input_sha256') == hashlib.sha256((args.run/'extended.json').read_bytes()).hexdigest(), 'Schedule evidence is stale'
assert E['parameters'] == p, 'Baseline and schedule parameters differ'
def schedule_source_matches(name, digest):
    current = ROOT/name
    if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest() == digest:
        return True
    # Historical accepted evidence retains its actual validator, not the repaired
    # validator's hash. Other physical/validation sources must still match.
    archived = ROOT/'reference/mesh-validator-335052c.py'
    return name == 'run_mesh_check.py' and archived.is_file() and hashlib.sha256(archived.read_bytes()).hexdigest() == digest

assert set(MC.get('source_sha256', {})) == {'run_mesh_check.py', 'code/model.py', 'code/policy_validation.py'} and all(schedule_source_matches(name, digest) for name,digest in MC['source_sha256'].items()), 'Schedule source evidence is stale'
assert MC.get('accepted_schedule') is not None, 'No independently accepted schedule; run run_mesh_check.py'
assert MC.get('checks') and all(c['passed'] for c in MC['checks']), 'Schedule acceptance failed'
ctl=MC['accepted_schedule']
CS=json.loads((ROOT/'reference/control-study.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in CS['source_sha256'].items()), 'Control-study evidence is stale'
assert CS['baseline_flow_lpm'] == ctl['flow_lpm'], 'Control-study baseline differs from accepted schedule'
assert all(row['accepted'] and all(m['continuous_passed'] for m in row['independent']) for row in CS['conditional_schedules']), 'Conditional schedules failed independent acceptance'
CAL=json.loads((ROOT/'reference/calibration-study.json').read_text(encoding='utf-8'))
assert CAL['status']=='completed' and CAL['accepted'], 'Calibration candidate not accepted'
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in CAL['source_sha256'].items()), 'Calibration evidence is stale'
assert CAL['baseline_flow_lpm']==ctl['flow_lpm'], 'Calibration baseline differs'
expected={(i,grid) for i in range(CAL['compatible_models']) for grid in ((8,4,3),(12,6,4),(16,8,6))}
keys=[(row['model_index'],tuple(row['grid'])) for row in CAL['independent']]
assert len(keys)==len(set(keys)) and set(keys)==expected and all(row['continuous_passed'] for row in CAL['independent']), 'Calibration replay coverage failed'
cal_flow=CAL['rounds'][-1]['flow_lpm']
assert abs(CAL['commanded_water_l']-5*sum(cal_flow))<1e-9, 'Calibration water arithmetic differs'
assert len(CAL['rows'])==CAL['compatible_models'], 'Calibration bank count differs'
for row in CAL['independent']:
    multiplier=CAL['rows'][row['model_index']]['parameters']['flow_multiplier']
    assert abs(row['water_l']-CAL['commanded_water_l']*multiplier)<1e-9, 'Delivered water differs'
    assert row['lower_temperature_bound_c']>=39 and row['upper_temperature_bound_c']<=41 and row['span_upper_bound_c']<=1.5, 'Calibration envelope violates physical limits'
cal_span=max(row['span_upper_bound_c'] for row in CAL['independent'])
cal_actual=[min(row['water_l'] for row in CAL['independent']),max(row['water_l'] for row in CAL['independent'])]
TR=json.loads((ROOT/'reference/calibration-transfer.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in TR['source_sha256'].items()), 'Calibration transfer evidence is stale'
assert TR['new_policy_flow_lpm']==cal_flow and TR['selected_model_indices']==CAL['rounds'][-1]['selected_indices'], 'Transfer policy differs'
assert [row['model_index'] for row in TR['constant_rows']]==list(range(CAL['compatible_models'])), 'Constant replay coverage differs'
assert abs(TR['constant_command_l']-b['water_l'])<1e-8, 'Constant replay water differs'
transfer_keys=[(row['model_index'],row['route'],row['body_capacity_j_per_k']) for row in TR['structure_rows']]
assert len(transfer_keys)==len(set(transfer_keys)) and set(transfer_keys)=={(i,route,cap) for i in TR['selected_model_indices'] for route in ('surface','deep') for cap in (None,253310.)}, 'Transfer coverage differs'
assert all(row['sampled_passed'] and row['step_check_delta_c']<2e-4 and row['instantaneous_balance_residual_w']<1e-6 and row['integrated_balance_residual_j']<.1 for row in TR['structure_rows']), 'Transfer checks failed'
IV=json.loads((ROOT/'reference/information-value.json').read_text())
FV=json.loads((ROOT/'reference/finite-volume-verification.json').read_text())
def information_source_matches(path,digest):
    file=ROOT/path
    if file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==digest:
        return True
    archive=ROOT/'reference/information-study-27f9e95.py'
    return path=='study_information_value.py' and archive.is_file() and hashlib.sha256(archive.read_bytes()).hexdigest()==digest
for name,receipt in [('Information',IV),('Finite-volume',FV)]:
    assert receipt['status']=='completed' and receipt['accepted'], name+' evidence incomplete'
    assert all(information_source_matches(path,digest) for path,digest in receipt['source_sha256'].items()), name+' evidence stale'
iv_flow=IV['rounds'][-1]['flow_lpm'];iv_water=5*sum(iv_flow)
assert abs(iv_water-IV['control_command_l'])<1e-9 and len(IV['rows'])==IV['compatible_models'], 'Passive water/bank mismatch'
iv_keys=[(row['model_index'],tuple(row['grid'])) for row in IV['independent']]
assert len(iv_keys)==len(set(iv_keys)) and set(iv_keys)=={(i,g) for i in range(len(IV['rows'])) for g in ((8,4,3),(12,6,4),(16,8,6))}, 'Passive independent coverage incomplete'
for row in IV['independent']:
    assert row['continuous_passed'] and row['lower_temperature_bound_c']>=39 and row['upper_temperature_bound_c']<=41 and row['span_upper_bound_c']<=1.5, 'Passive envelope failed'
    assert abs(row['water_l']-iv_water*IV['rows'][row['model_index']]['parameters']['flow_multiplier'])<1e-9, 'Passive delivered water differs'
assert IV['parameter_grid']==CAL['parameter_grid'] and IV['probes']==CAL['probes'] and IV['reading_bound_c']==CAL['reading_bound_c'] and IV['constant_offset_bound_c']==CAL['constant_offset_bound_c'], 'Information designs not comparable'
iv_delta=iv_water-CAL['commanded_water_l']
iv_parameters=list(IV['parameter_grid'])
iv_intersection=len({tuple(row['parameters'][k] for k in iv_parameters) for row in IV['rows']} & {tuple(row['parameters'][k] for k in iv_parameters) for row in CAL['rows']})
assert iv_delta>0 and IV['observation_command_l']==0., 'Unexpected cost order; revise interpretation'
from observation_values import observation_values
OBS=observation_values(ROOT)
obs_rows=OBS['rows']
strong_delta=obs_rows[('strong_mixing_low_loss','passive')]['selected']['command_l']-obs_rows[('strong_mixing_low_loss','pulse')]['selected']['command_l']
from report_values import report_values
rv=report_values(r,E,MC,ST)
save=100*(1-ctl['water_l']/b['water_l']);qq=lr['water_quantiles_l'];sp=lr['spearman_with_water']
ct=E['control']['runs']
ROOT.joinpath('submission').mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT.parents[2]))
import subprocess,shutil
from scripts import texplot
from scripts.paper_template import preamble, summary_header, check as check_layout
from scripts.paper_template import table_of_contents
escape=lambda s:s
tex=[];eqcount=0;tabcount=0;table_total=0;SEC=[0]
CAPS=['Where each requirement is answered','Modeling options compared','Baseline inputs','Coefficient anchors and the values used','Symbols',
 'Baseline result under the best constant rate','Constant rate, scheduled flow and the bounds','Geometry, size and body scenarios',
 'Mixing, surface, comfort and supply scenarios','Mesh replay: constrained temperatures','Fixed-policy structural replay','Scenario definitions','Scenario definitions (continued)']
UNI={'′':r"$'$",'Ṫ':r'$\dot T$','∫':r'$\int$','≥':r'$\geq$','≤':r'$\leq$','≈':r'$\approx$','→':r'$\rightarrow$','≠':r'$\neq$','⁻':r'$^{-}$','¹':r'$^{1}$','⁰':r'$^{0}$','∂':r'$\partial$','ρ':r'$\rho$','Δ':r'$\Delta$','∑':r'$\sum$','−':'-','µ':r'$\mu$','∞':r'$\infty$'}
def esc(s):
    s=s.replace('\\',r'\textbackslash{}')
    for a,b in [('&',r'\&'),('%',r'\%'),('$',r'\$'),('#',r'\#'),('_',r'\_'),('{',r'\{'),('}',r'\}'),('~',r'\textasciitilde{}'),('^',r'\textasciicircum{}')]:s=s.replace(a,b)
    return ''.join(UNI.get(c,c) for c in s)
URL=re.compile(r'((?:https?://)?[A-Za-z0-9.-]+\.(?:com|org|gov|net|edu)/[^\s,;]*[^\s,;.])')
TOK={'Tmin':r'T_{\min}','Tmax':r'T_{\max}','Tout':r'T_{\mathrm{out}}','Tin':r'T_{\mathrm{in}}','Vcell':r'V_{\mathrm{cell}}','Aij':'A_{ij}','dij':'d_{ij}','gij':'g_{ij}',
 'φi':r'\phi_i','Ti':'T_i','Tc':'T_c','Te':'T_e','Ta':'T_a','Tb':'T_b','T0':'T_0','Tf':'T_f','Ha':'H_a','Hb':'H_b','Ci':'C_i','Vi':'V_i','tc':'t_c','tf':'t_f','wi':'w_i',
 'ℓ':r'\ell','φ':r'\phi','Ṫ':r'\dot T','Ri':r'\mathrm{Ri}','ΔT':r'\Delta T','q':'q','D':'D','T':'T'}
TOKRE=re.compile(r'(?<![\w°$\\])(%s)(?![\w°])'%'|'.join(sorted(map(re.escape,TOK),key=len,reverse=True)))
EXP=re.compile(r'\b(\d+(?:\.\d+)?)e-(\d+)\b')
def plain_nomath(s):
    parts=URL.split(s)
    return ''.join((r'\url{'+x+'}') if i%2 else esc(x) for i,x in enumerate(parts))
def plain(s):
    hold=[]
    def keep(raw):hold.append(raw);return '\x00%d\x01'%(len(hold)-1)
    out=[]
    for i,seg in enumerate(re.split(r'(\$[^$]*\$)',s)):
        if i%2:out.append(keep(seg));continue
        seg=EXP.sub(lambda m:keep(r'$%s\times10^{-%s}$'%(m.group(1),m.group(2))),seg)
        seg=TOKRE.sub(lambda m:keep('$'+TOK[m.group(1)]+'$'),seg)
        parts=URL.split(seg)
        out.append(''.join(keep(r'\url{'+x+'}') if j%2 else esc(x) for j,x in enumerate(parts)))
    res=''.join(out)
    return re.sub('\x00(\\d+)\x01',lambda m:hold[int(m.group(1))],res)
def tx(s,math=True):
    s=s.replace('&gt;','>').replace('&lt;','<').replace('&amp;','&')
    out=[];depth=[]
    for tok in re.split(r'(</?b>|</?i>|<br/>|</?font[^>]*>)',s):
        if tok=='<b>':out.append(r'\textbf{');depth.append('b')
        elif tok=='<i>':out.append(r'\emph{');depth.append('i')
        elif tok in('</b>','</i>'):out.append('}');depth.pop()
        elif tok=='<br/>':out.append(r'\\ ')
        elif tok.startswith('<font') or tok=='</font>':pass
        else:out.append(plain(tok) if math else plain_nomath(tok))
    return re.sub(r'@(fig|tab):([\w-]+)@',r'\\ref{\1:\2}',''.join(out))
def para(s,kind='body'):
    if kind=='title':tex.append(r'\begin{center}{\LARGE\bfseries '+tx(s)+r'}\end{center}'+'\n')
    elif kind=='heading':
        if s=='Summary':tex.append(r'\begin{center}{\Large\bfseries Summary}\end{center}'+'\n')
        else:tex.append(r'\subsection*{'+tx(s)+'}\n')
    elif kind=='ref':tex.append(r'\begingroup\small\setlength{\parindent}{0pt}\hangindent=1.5em '+tx(s,False)+r'\par\endgroup'+'\n')
    else:tex.append(tx(s)+'\n\n')
def page(title,hard=False):
    if hard:tex.append(r'\clearpage'+'\n')
    m2=re.match(r'^(\d+)\.(\d+) (.*)$',title);m1=re.match(r'^(\d+)\. (.*)$',title)
    if m2:tex.append(r'\subsection{'+tx(m2.group(3))+'}\n')
    elif m1:
        SEC[0]+=1;assert int(m1.group(1))==SEC[0],title
        tex.append(r'\section{'+tx(m1.group(2))+'}\n')
    else:tex.append(r'\section*{'+tx(title)+'}\n'+r'\addcontentsline{toc}{section}{'+tx(title)+'}\n')
def table(rows,widths=None,caption=None,label=None):
    global tabcount,table_total
    table_total+=1
    # Named additional tables must not shift the established caption/label map.
    # LaTeX supplies the visible sequential number for every table independently.
    if caption is None:
        tabcount+=1
        caption=CAPS[tabcount-1]
        label=str(tabcount)
        established=True
    else:
        if not label or not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*',label):
            raise ValueError('An additional table needs a stable semantic label')
        established=False
    n=len(rows[0]);tot=float(sum(widths)) if widths else 1
    introductions={
      1: 'The coverage map in Table @tab:1@ links each requested outcome to the argument or result that answers it.',
      2: 'The comparison in Table @tab:2@ motivates the modeling choice: a thermal network resolves spatial differences without requiring the unobserved velocity field of a flow solver.',
      3: 'The baseline in Table @tab:3@ separates geometry and comfort assumptions from the coefficients whose physical anchors are examined next.',
      4: 'The relations and ranges in Table @tab:4@ show how each heat-loss coefficient is anchored; the selected values define a scenario rather than a fitted bath.',
      5: 'The notation in Table @tab:5@ distinguishes cell capacities, transport and boundary exchange so the energy balance can be checked term by term.',
      6: 'The results in Table @tab:6@ show that the selected constant rate meets the stated temperature limits while accounting for the total replacement water.',
      7: 'The comparison in Table @tab:7@ separates feasible search results from proved bounds: scheduling saves water relative to the constant rate, but the remaining gap is not an optimality certificate.',
      8: 'The scenarios in Table @tab:8@ distinguish changes in water storage from changes in body displacement and heat exchange; each row uses its own reconstructed geometry.',
      9: 'The outcomes in Table @tab:9@ show why mixing and boundary heat loss must be varied separately: stronger transport can help, while added surface loss can offset the gain.',
      10: 'The three-grid replay in Table @tab:10@ checks the quantities constrained outside the fixed jet zone and separately reports the inlet-cell peak, which is not covered by that ceiling.',
      11: 'Table @tab:11@ compares the unchanged scheduled policy under the baseline and limited structural alternatives.',
      12: 'The inputs in Table @tab:12@ make the scenario comparisons reproducible: only the listed quantities change from the baseline.',
    }
    if established and tabcount in introductions: para(introductions[tabcount])
    if widths:cols='@{}'+''.join(r'>{\raggedright\arraybackslash}p{%.4f\dimexpr\linewidth-%d\tabcolsep\relax}'%(w/tot,2*(n-1)) for w in widths)+'@{}'
    else:cols='l'*n
    lines=[' & '.join(tx(c) for c in row) for row in rows]
    tex.append(r'\begin{table}[htbp]\centering\small\caption{'+tx(caption,False)+'}'+r'\label{tab:'+label+'}'+'\n\\begin{tabular}{'+cols+'}\n\\toprule\n'+lines[0]+r' \\ \midrule'+'\n'+(r' \\ '+'\n').join(lines[1:])+r' \\ \bottomrule'+'\n\\end{tabular}\n\\end{table}\n')
def eq(s):
    global eqcount
    eqcount+=1;tex.append(r'\begin{equation}'+re.sub(r'\{\\rm ',r'{\\mathrm ',s)+r'\end{equation}'+'\n')
figcount=[0]
def figure(name,caption,height=None):
    figcount[0]+=1
    introductions={
      'roadmap.png': 'The roadmap in Figure @fig:roadmap@ shows how the proved mixed benchmark, spatial model and independent checks contribute to the final recommendation.',
      'spatial.png': 'The layers in Figure @fig:spatial@ locate the remaining spatial temperature differences; a single shared scale makes the top-layer inlet path comparable with the deeper water.',
      'temperature.png': 'The trajectory in Figure @fig:temperature@ contrasts the volume-weighted mean with the coldest cell and the full spatial range, showing why the mean alone cannot establish comfort.',
      'control.png': 'The schedule in Figure @fig:control@ concentrates replenishment in the middle of the bath; its temperature trajectory must therefore be checked over the no-flow intervals as well.',
      'frontier.png': 'Figure @fig:frontier@ compares the spatial constant-rate search with the analytical well-mixed optimum and energy lower bound. The spatial curve joins accepted search results; it does not certify an optimum over all controls.',
      'bounds.png': 'The bracket in Figure @fig:bounds@ separates admissible policies from lower bounds; it supports a comparison of water use without claiming that the spatial search proves a global optimum.',
      'ranges.png': 'The draws in Figure @fig:ranges@ show how surface heat loss changes water demand within the tested ranges, while the rejected draws expose conditions where the search finds no acceptable policy.',
    }
    if name in introductions: para(introductions[name])
    m=re.match(r'^Figure (\d+)\. (.*)$',caption,re.S);assert m,caption
    tex.append(texplot.figure_env(FIG[name],tx(m.group(2)),label='fig:'+name.replace('.png','')))
PREAMBLE=preamble(TEAM_CONTROL_NUMBER, 'A Hot Bath: Conserving Water Without Losing Uniformity')

def compile_pdf(stem,title):
    d=ROOT/'paper';d.mkdir(exist_ok=True)
    source=PREAMBLE+''.join(tex)+'\n\\end{document}\n'
    check_layout(source)
    (d/(stem+'.tex')).write_text(source, encoding='utf-8')
    from scripts.paper_template import compile_in_place
    compile_in_place(d/(stem+'.tex'), 'mcm')
    return d/(stem+'.pdf')

# Figures are pgfplots/TikZ source built from the numerical record; fonts match the paper.
FIG={}
# Colour rules: blue = the quantity of interest, vermilion = the contrast (coldest cell, accepted-policy failures, constant-rate search), grey = bounds and context.
t=z['t']/60;T=z['T'];mean=T@z['volume']/z['volume'].sum()
ax=texplot.Axis('Time (min)','Temperature (°C)',height='5.0cm',xmin=0,xmax=30,ymin=38.85,ymax=p['ceiling']+.2)
Vn=model.view(model.network(p),T)
ax.band(t,T.min(1),Vn.max(1),label='Spatial range').line(t,mean,label='Volume-weighted mean').line(t,T.min(1),color='accent',style='dashed',label='Coldest cell').hline(p['floor']).hline(p['ceiling'])
FIG['temperature.png']=ax.tex().replace('°C','$^\\circ$C')
labels=['Constant rate','Constant rate, fine grid','Optimized schedule','Perfect mixing','Energy bound'];values=[b['water_l'],r['mesh']['fine_policy']['water_l'],ctl['water_l'],a['mixed_optimum_l'],a['energy_lower_bound_l']]
FIG['bounds.png']=texplot.hbar_chart(labels,values,['main','main','main','muted','muted'],'Added water over 30 min (L)',height='5.0cm',xmax=max(values)*1.3)
seg_min=ctl['segment_s']/60;edges=list(np.arange(len(ctl['flow_lpm'])+1)*seg_min)
Yc=control.piecewise(p,model.network(p),ctl['flow_lpm'],5.);tc=np.linspace(0,30,len(Yc))
a1=texplot.Axis('','Flow (L/min)',width='0.62\\linewidth',height='2.5cm',xmin=0,xmax=30,ymin=0,legend=None,extra='scale only axis,name=top,xticklabels={}')
a1.stairs(ctl['flow_lpm'],edges).line([0,30],[b['flow_lpm']]*2,color='muted',style='dashed')
a1.label(30,ctl['flow_lpm'][-1]+0.0,'Optimized schedule',color='main').label(30,b['flow_lpm'],'Best constant rate',color='muted',dy='-6pt')
a2=texplot.Axis('Time (min)','Temp. ($^\\circ$C)',width='0.62\\linewidth',height='3.0cm',xmin=0,xmax=30,ymin=38.85,ymax=41.15,legend=None,extra='scale only axis,at={(top.south)},anchor=north,yshift=-0.35cm')
Vc=model.view(model.network(p),Yc)
a2.band(tc,Yc.min(1),Vc.max(1)).line(tc,Yc.min(1),color='accent',style='dashed').line(tc,Vc.max(1)).hline(p['floor']).hline(p['ceiling'])
a2.label(25.5,float(np.interp(25.5,tc,Vc.max(1)))+0.1,'Hottest cell',color='main',anchor='south west',dx='0pt').label(8,float(np.interp(8,tc,Yc.min(1)))-0.03,'Coldest cell',color='accent',anchor='north',dx='0pt')
FIG['control.png']=a1.tex()+'\n'+a2.tex()
boxes=['Assumptions\nand anchors\n§2','Mixed benchmark\nand bound\n§3–4','Spatial network\nand solver\n§5–6','Rate, schedule,\nscenarios\n§7–9','Validation,\nranges, mesh\n§10–11','Conclusion,\nuser guide\n§12–13']
FIG['roadmap.png']=texplot.flow_diagram(boxes,node_width='2.05cm')
rows_=lr['rows'];okr=[r_ for r_ in rows_ if r_['feasible']];bad=[r_ for r_ in rows_ if not r_['feasible']]
top=max(r_['water_l'] for r_ in okr)*1.08
ax=texplot.Axis('Surface coefficient (W/(m$^2$ K))','Added water (L)',height='5.0cm')
ax.scatter([r_['inputs']['h_surface'] for r_ in okr],[r_['water_l'] for r_ in okr],label='Accepted policy')
if bad:ax.scatter([r_['inputs']['h_surface'] for r_ in bad],[top]*len(bad),color='accent',mark='x',size=2.6,label='None accepted')
ax.vline(p['h_surface'])
FIG['ranges.png']=ax.tex()
fr=E['frontier'];okf=[f_ for f_ in fr if f_['constant_l'] is not None]
ax=texplot.Axis('Allowed temperature drop ($^\\circ$C)','Added water (L)',height='5.0cm',legend_columns=2)
ax.line([f_['fall'] for f_ in fr],[f_['mixed_l'] for f_ in fr],label='Mixed optimum').line([f_['fall'] for f_ in fr],[f_['bound_l'] for f_ in fr],color='muted',style='dashed',width=0.9,label='Energy bound')
ax.line([f_['fall'] for f_ in okf],[f_['constant_l'] for f_ in okf],color='accent',marks='*',label='Spatial constant rate')
badf=[f_ for f_ in fr if f_['constant_l'] is None]
if badf:ax.scatter([f_['fall'] for f_ in badf],[0]*len(badf),color='accent',mark='x',size=2.6,label='No candidate found')
ax.vline(p['initial']-p['floor'])
FIG['frontier.png']=ax.tex()
cube=T[-1].reshape(tuple(r['grid']))
FIG['spatial.png']=texplot.heatmap_panels([cube[:,:,k].tolist() for k in range(3)],['Bottom layer','Middle layer','Top layer'],'Length (m)','Width (m)',(p['L'],p['W']),float(T[-1].min()),float(T[-1].max()),cbar_label='Final cell-average temperature ($^\\circ$C)',xticks=[0,.75,1.5],yticks=[0,.325,.65])

tex.append(summary_header('A'))

para('A Hot Bath: Conserving Water Without Losing Uniformity','title')
para('Summary','heading')
para('Maintaining a warm bath is a coupled problem of heat loss, replenishment and transport. A hot inlet can improve the mean temperature while leaving distant water cool and sending useful heat directly to the overflow. We therefore minimize added water subject to a lower limit in every cell and upper-temperature and spread limits outside a 0.15 m inlet zone, rather than optimizing an average alone.')
para('We prove a coast-then-hold policy optimal for a well-mixed bath, then use a three-dimensional finite-volume thermal network with coefficients derived from textbook correlations and tied to a published immersion study where one exists (Section 2). The best constant rate is compared with an optimized piecewise-constant schedule; neither is proved optimal among all controls.')
para(f'In a {rv["water_volume_l"]:.2f} L water-volume scenario lasting {rv["horizon_min"]:g} minutes, with an initial temperature of {p["initial"]:g}°C and a {p["floor"]:g}°C lower limit, the best constant-rate policy adds <b>{b["water_l"]:.2f} L</b> at {b["flow_lpm"]:.3f} L/min from the start, and a {ctl["segments"]}-segment schedule with a {ctl["buffer_c"]:g}°C design margin needs <b>{ctl["water_l"]:.2f} L</b>, {save:.0f}% less. The well-mixed optimum is {a["mixed_optimum_l"]:.2f} L, while an independent energy argument gives a {a["energy_lower_bound_l"]:.2f} L lower bound for the spatial problem. A finer mesh changes the constant-rate result by {100*abs(r["mesh"]["fine_policy"]["water_l"]-b["water_l"])/b["water_l"]:.2f}%, and the selected scheduled policy passes independent continuous-time bounds on all three tested meshes.')
para(f'Across {lr["samples"]} Sobol draws over the stated parameter ranges, {lr["feasible"]} yield an accepted constant-rate candidate, needing {qq["0.05"]:.0f}–{qq["0.95"]:.0f} L (5th–95th percentile). Weak mixing often defeats this finite search. Motion improves transport, but the associated extra surface loss can offset the saving. The assumed foam layer reduces constant-flow demand to {sc["foam"]["policy"]["water_l"]:.1f} L; this is a scenario, not a measured additive effect.')
para(f'At equal volume a deep, narrow tub needs {sc["deep narrow"]["policy"]["water_l"]:.2f} L; larger body displacement and contact area together raise demand to {sc["larger body"]["policy"]["water_l"]:.2f} L. More importantly, mixing changes when water must enter: six-stage candidates need {CS["conditional_schedules"][0]["chosen"]["water_l"]:.2f} L at D = 0.0007 m²/s and {CS["conditional_schedules"][1]["chosen"]["water_l"]:.2f} L at 0.0013 m²/s; the weaker-mixing candidate starts immediately. Similar readings do not guarantee the same decision. A synthetic two-probe pulse leaves 178 compatible models and a {CAL["commanded_water_l"]:.2f} L control candidate. Passive cooling leaves {IV["compatible_models"]} and needs {iv_water:.2f} L, but avoids the 6 L pulse. With equal reset costs, the pulse candidate becomes cheaper only when reused for at least seven unchanged baths. Both pass three-grid conditional envelopes. Alternative synthetic observations change control demand and the equal-reset crossover; weaker mixing also exposes a failed search. The contribution is to connect transport and useful information to supply timing and total water cost. These are conditional model results, not tested prescriptions; AI assistance is disclosed.')
para('<b>Keywords:</b> thermal network; energy balance; lower bound; optimal control; sensitivity analysis')

tex.append(table_of_contents())
page('1. Define the decision before optimizing',True)
para('The task is to preserve both warmth and spatial uniformity in an overflowing, unheated tub, and to examine geometry, the bather and motion, and a bubble-bath layer [1]. The report separates physical requirements from preference assumptions. There is no supplied temperature record or measured heat-transfer coefficient to fit.')
para('The decision variables are an inlet flow rate and the time at which a constant trickle begins. The tub is already full: added water displaces an equal volume through the overflow. The horizon is 1,800 s. Our baseline requires every cell average to stay at or above 39°C, and requires the cell averages outside a 0.15 m jet-mixing zone around the inlet to stay at or below 41°C and within an instantaneous spread of 1.5°C. These choices operationalize comfort; they are not medical limits or numbers specified by the problem, and the jet zone is an assumption justified in Section 2.1.')
eq(r'J=1000\int_0^{t_f}q(t)\,dt')
eq(r'T_i(t)\geq T_{\min}\ \ (\forall i),\qquad T_i(t)\leq T_{\max},\quad \max_{i\in\Omega}T_i(t)-\min_{i\in\Omega}T_i(t)\leq\Delta\ \ (i\in\Omega)')
para('Here $\\Omega$ is the set of cells outside the inlet jet zone, q is in m³/s and J is in litres. We prioritize the least water within the constraints, rather than assigning arbitrary weights to unlike units. Tightening the temperature tolerance is a separate scenario. Zero flow is admitted: if the initial stored heat suffices, using no added water is globally water-minimal.')
table([['Requirement','Where answered'],['Temperature in space and time','Sections 3, 5–7; Figures @fig:spatial@–@fig:temperature@'],['Water-use strategy and its scope','Sections 4, 6–7 and 12'],['Tub/body geometry, size and temperature','Section 8'],['Motion and bubble-bath additive','Section 9'],['Validation and sensitivity','Sections 8–11'],['One-page non-technical explanation','Section 13']],[210,258])
para('Spatial temperature means a control-volume average. It does not bound the unresolved temperature of a faucet jet or a skin-contact film. This distinction determines which practical conclusions the simulation can support.')

para('<b>Modeling options.</b> A lumped model (Newton cooling) keeps one temperature and cannot see a cold corner. A flow solver resolves velocity but needs a turbulence closure and a faucet jet that nothing available here can constrain. A finite-volume thermal network sits between them: it keeps conservation exact, resolves where heat is lost and delivered, and makes mixing an explicit, testable parameter [5]. We use the lumped model as a proved benchmark (Sections 3–4) and the network for the decision (Sections 5–11).')
table([['Option','Resolves','Evidence it needs','Role here'],['Lumped (Newton)','Mean temperature','Two loss coefficients','Proved benchmark'],['Thermal network','Cells, heat paths, overflow','Loss, body and mixing coefficients','Decision model'],['Flow solver','Velocity and buoyancy','Turbulence closure, jet data','Not used']],[100,120,130,118])
page('2. Physical assumptions and scenario inputs')
para('Each assumption below is paired with its reason and, where it matters, the scenario that tests it. Coefficients cannot be identified from the problem statement alone, so they come from the anchors in Section 2.1.')
table([['Quantity','Baseline / units','Status'],['Tub L × W × H',f'{p["L"]:.2f} × {p["W"]:.2f} × {p["H"]:.2f} m','Assumed geometry'],['Displaced body volume / area',f'{p["body_volume"]:.3f} m³ / {p["body_area"]:.2f} m²','Assumed'],['Water density / heat capacity',f'{p["rho"]:g} kg/m³ / {p["cp"]:g} J/(kg K)','Rounded constants'],['Air / skin / inlet temperature',f'{p["air_temp"]:g} / {p["body_temp"]:g} / {p["inlet_temp"]:g}°C','Fixed reservoirs'],['Surface / wall / body coefficient',f'{p["h_surface"]:g} / {p["h_wall"]:g} / {p["h_body"]:g} W/(m² K)','Correlation-based (next page)'],['Mixing diffusivity D',f'{p["D"]:g} m²/s','Uncalibrated closure; range tested'],['Initial / lower / upper limit',f'{p["initial"]:g} / {p["floor"]:g} / {p["ceiling"]:g}°C','Preference scenario'],['Time / allowed spread',f'{p["horizon"]:g} s / {p["span"]:g}°C','Preference scenario']],[182,188,98])
para('<b>A1. Constant density and heat capacity.</b> Water properties change by under 1% between 39 and 41°C, and the constants are rounded values, not an evaluated IAPWS table [3]. <i>Reason:</i> the resulting capacity error is small next to the loss coefficients.')
para('<b>A2. Heat exchange proportional to temperature difference.</b> Surface, shell and body exchange follow Newton’s law with effective coefficients [2]. <i>Reason:</i> the temperature span is narrow, so linearization is acceptable. The surface coefficient aggregates convection, radiation and evaporation, so evaporation is not added twice; evaporative volume change is neglected. The evaporative part is linearized about the room temperature; an independent review estimated that this understates its sensitivity near 40°C by several percent (about 7% on the total), which is small next to the tested range.')
para('<b>A3. Skin held at a fixed temperature.</b> <i>Reason:</i> thermoregulation is outside the problem; skin temperature is varied (32 and 36°C) instead of resolved.')
para('<b>A4. Inlet-to-overflow surface stream.</b> The hot water travels along a prescribed surface path to the overflow, so short circuit is possible. The stream runs along the row of cells nearest the centre line (half a cell off it on meshes with an even number of rows). <i>Reason:</i> a different inlet geometry would need its own transport network and evidence.')
para('<b>A5. Mixing as one effective diffusivity D.</b> Motion enters through D, with a separate surface-loss scenario. <i>Reason:</i> molecular diffusion alone would not represent circulation; D is anchored only by an order-of-magnitude scaling (Section 2.1) and is tested over a range; vertical mixing is tested separately in Section 9.')

page('2.1 Where the coefficients come from')
sf=prov['surface'];wl=prov['wall'];bd=prov['body']
para(f'No temperature record exists to fit, so each coefficient is derived from a textbook relation or tied to a published measurement where one exists, and given a range; where nothing exists (mixing, the exposed fraction, the air and skin temperatures) the value is an assumption and is labelled as one. Surface loss sums natural convection above a hot horizontal surface ($\\mathrm{{Nu}}=0.15\\,\\mathrm{{Ra}}^{{1/3}}$ for $10^{{7}}<\\mathrm{{Ra}}<10^{{11}}$, length $A/P$ [5]; here $\\mathrm{{Ra}}={sf["rayleigh"]/1e7:.1f}\\times10^{{7}}$), linearized radiation (emissivity 0.96) and evaporation by the Lewis analogy. For open water at 40°C in 22°C air at 50% humidity the parts are {sf["parts"]["convection"]:.1f}, {sf["parts"]["radiation"]:.1f} and {sf["parts"]["evaporation"]:.1f} W/(m² K) ({sf["evaporation_kg_m2_h"]:.2f} kg/m² h evaporated), {sf["open_water_total"]:.1f} in total. A bather covers part of the surface; with an assumed exposed fraction of 0.7 the central value is {sf["central"]:.1f}, and we use 25 within the range 17–37, which spans exposed fractions of 0.5 to 1.0. Evaporation correlations differ by tens of percent, so this is a scenario range, not a measured one.')
para(f'The shell coefficient is a series resistance: a 5 mm shell (0.19 W/(m K)) with film coefficients of 300 inside and 8 W/(m² K) outside gives {wl["central"]:.1f}, and {wl["range"][0]:.1f}–{wl["range"][1]:.1f} for other thicknesses. These are typical engineering values, not measurements of a particular tub. The body coefficient is anchored by a measurement: Menzies et al. report a rectal-temperature rise of 0.9 ± 0.3°C after 30 minutes in 40°C water to the shoulders [6]. Taking the mean body mass of the study participants, 73 kg, $c=3470$ J/(kg K) and a mean body rise of 1–2°C, the average heat uptake is {bd["anchor"][0]["average_uptake_w"]:.0f}–{bd["anchor"][1]["average_uptake_w"]:.0f} W, equal to {bd["anchor"][0]["equivalent_h_body"]:.0f}–{bd["anchor"][1]["equivalent_h_body"]:.0f} W/(m² K) with skin held at 34°C. We use 25, because a fixed skin node overstates the driving difference later in the bath. The mean body rise and the driving difference are assumptions, so this is an order-of-magnitude anchor, not a calibration. Holding the skin at a fixed temperature also ignores the heat capacity of the body, about 37% of the water\'s here (73 kg × 3470 J/(kg K) against 687 kJ/K): uptake is anchored only on its 30-minute average. Its decay is omitted in the baseline and tested with a finite effective reservoir in Section 11.1.')
para('Mixing has only a scaling anchor. A mixing-length estimate $D\\approx 0.1\\,u\'\\ell$, with a velocity scale $u\'$ and eddy size $\\ell$, gives about 1e-4 m²/s for buoyancy-driven flow alone ($u\'=0.02$ m/s, $\\ell=0.05$ m), 1e-3 for gentle movement of the bather (0.1 m/s, 0.1 m) and 6e-3 for vigorous movement (0.3 m/s, 0.2 m). We use 0.001 and test 0.0003–0.003. This is a scaling argument, not a measurement, so D stays a scenario.')
cv=r['mesh']['convergence']
para(f'The 39–41°C window is a preference; immersion studies use 40–42°C water [6], which is not a safety standard. The inlet cell is a point source: the same policy gives a maximum inlet-cell average of {cv[0]["inlet_cell_max_temp"]:.2f}, {cv[1]["inlet_cell_max_temp"]:.2f} and {cv[2]["inlet_cell_max_temp"]:.2f}°C on the three meshes of Section 11, because a smaller cell mixes less water with the hot inflow. A limit imposed on that cell would test the mesh, not the bath. The ceiling and the spread limit therefore apply outside a jet-mixing zone of 0.15 m radius around the inlet, on the assumption that a bather does not sit in the jet; the floor applies to every cell, which the energy bound of Section 4 needs. With this definition the constrained temperatures agree across meshes (Section 11).')
table([['Coefficient','Relation or anchor','Derived value','Used (range tested)'],['Surface, W/(m² K)','Convection + radiation + evaporation [5]',f'{sf["open_water_total"]:.1f} open; {sf["central"]:.1f} at 70%','25 (17–37)'],['Shell, W/(m² K)','Series resistance, typical shell values',f'{wl["central"]:.1f} ({wl["range"][0]:.1f}–{wl["range"][1]:.1f})','6.5 (4.5–8.5)'],['Body, W/(m² K)','Uptake implied by core rise [6]',f'{bd["anchor"][0]["equivalent_h_body"]:.0f}–{bd["anchor"][1]["equivalent_h_body"]:.0f} at fixed skin','25 (12–40)'],['Mixing D, m²/s','Mixing-length scaling','1e-4 to 6e-3','0.001 (0.0003–0.003)']],[96,162,110,100])

page('3. A transparent well-mixed benchmark')
table([['Symbol','Meaning'],['C','Heat capacity of the water, J/K'],['Ha, Hb','Air/shell and body conductance, W/K'],['Ta, Tb, Tin','Room, skin and inlet temperature, °C'],['Tmin, Tmax','Lower and upper limit, °C'],['q, J','Inlet flow, m³/s; added water, L'],['D','Effective mixing diffusivity, m²/s']],[110,358])
para('Let $C$ be total water heat capacity, $H_a$ the air/shell conductance and $H_b$ the body conductance. A well-mixed overflow has the same temperature as the bath. Integrating the physical energy balance gives')
eq(r'C\dot T=H_a(T_a-T)+H_b(T_b-T)+\rho c_pq(T_{\rm in}-T)')
eq(r'C=\rho c_p(LWH-V_b),\quad H_b=h_bA_b')
eq(r'H_a=h_s fLW+h_w\{LW+2H(L+W)\}')
para('The foam multiplier $f$ equals one without a layer. Setting $q=0$, define $H=H_a+H_b$ and $T_e=(H_aT_a+H_bT_b)/H$. The cooling solution and first time to reach the lower limit are')
eq(r'T(t)=T_e+(T_0-T_e)e^{-Ht/C}')
eq(r't_c=\frac{C}{H}\log\frac{T_0-T_e}{T_{\min}-T_e}')
para(f'Baseline conductances are Ha = {a["air_conductance"]:.2f} W/K and Hb = {a["body_conductance"]:.2f} W/K, and C = {p["rho"]*p["cp"]*(p["L"]*p["W"]*p["H"]-p["body_volume"]):,.0f} J/K. Thus Te = {a["equilibrium"]:.2f}°C and tc = {a["coast_s"]/60:.2f} min.')
para('A heat-loss model must approach an environmental equilibrium rather than zero Celsius. This analytic boundary also supplies a direct check on signs and units. The benchmark describes mixing perfectly; the spatial model will test the cost of departing from that assumption.')

page('4. What can be proved about water use?')
para('Let $\\ell(T)=H_a(T-T_a)+H_b(T-T_b)$ be the heat loss of the mixed bath, and let the inlet be hotter than every temperature considered. <b>Proposition 1.</b> Coasting to the lower limit and then holding it uses the least water, provided the holding rate is within the faucet bound. The proof has four steps.')
tex.append(r'\begin{proof}'+'\n')
para('<b>Step 1, an identity.</b> Dividing the balance by $T_{\\mathrm{in}}-T$ and integrating over the horizon gives')
eq(r'\int q\,dt=\frac{C}{\rho c_p}\log\frac{T_{\rm in}-T_0}{T_{\rm in}-T_f}+\int\frac{\ell(T)}{\rho c_p(T_{\rm in}-T)}\,dt')
para('<b>Step 2, monotonicity.</b> The integrand $\\ell(T)/(T_{\\mathrm{in}}-T)$ has derivative $[H_a(T_{\\mathrm{in}}-T_a)+H_b(T_{\\mathrm{in}}-T_b)]/(T_{\\mathrm{in}}-T)^2>0$, so it increases with $T$, and the logarithmic term increases with the final temperature. Water use is therefore an increasing functional of the temperature path.')
para('<b>Step 3, the lowest admissible path.</b> Because $q\\ge 0$, comparison with the no-flow solution gives $T(t)\\ge T_c(t)$, the cooling curve of Section 3, and feasibility requires $T(t)\\ge T_{\\min}$. The pointwise lowest admissible path is $\\max(T_c(t),T_{\\min})$: coast until $T_c$ reaches $T_{\\min}$, then hold.')
para('<b>Step 4, attainability.</b> Holding $T=T_{\\min}$ means $\\dot T=0$, which needs the rate')
eq(r'q_{\rm hold}=\frac{\ell(T_{\min})}{\rho c_p(T_{\rm in}-T_{\min})}')
para('When this rate is within the bound, the path is feasible and, by Step 2, optimal.')
tex.append(r'\end{proof}'+'\n')
para(f'For the baseline, the mixed-model optimum adds {a["mixed_optimum_l"]:.2f} L: wait {a["coast_s"]/60:.2f} min, then supply {a["hold_lpm"]:.3f} L/min. Optimality is established for the mixed model; spatial policies are assessed separately.')
para('<b>Proposition 2 (energy lower bound).</b> In the spatial model, suppose every cell satisfies $T_i(t)\\ge T_{\\min}$. Summing the cell balances gives $\\sum_i C_iT_i(t_f)-CT_0=-\\int L\\,dt+\\rho c_p\\int q(T_{\\mathrm{in}}-T_{\\mathrm{out}})\\,dt$, with $L$ the total loss. Each loss term increases with its cell temperature, and $H_a$ and $H_b$ are the sums of the cell conductances, so $L(t)\\ge\\ell(T_{\\min})$. The outlet cell satisfies $T_{\\mathrm{out}}\\ge T_{\\min}$, so $T_{\\mathrm{in}}-T_{\\mathrm{out}}\\le T_{\\mathrm{in}}-T_{\\min}$, and the left side is at least $C(T_{\\min}-T_0)$. Combining these three facts,')
eq(r'J\geq\max\left(0,\frac{1000[\ell(T_{\min})t_f-C(T_0-T_{\min})]}{\rho c_p(T_{\rm in}-T_{\min})}\right)')
para(f'The resulting {a["energy_lower_bound_l"]:.2f} L is a genuine conditional lower bound, valid for any control, but it is not tight: the initial water is hotter than the floor and loses more heat, and limited mixing adds further cost. Section 7.1 shows how much of the gap an optimized schedule recovers.')

page('5. A conservative model in three dimensions')
para('The rectangular water envelope is divided into 8 × 4 × 3 cells. Each has a capacity $C_i$ and exchanges heat only across common faces. The cells whose centres lie within 0.15 m of the inlet cell form the jet zone (2, 9 and 22 cells on the 8 × 4 × 3, 12 × 6 × 4 and 16 × 8 × 6 meshes); $\\Omega$ is the rest. Top cells lose heat to the room; bottom and side faces lose heat through the shell. The bather is represented by a smooth, three-dimensional displacement field and a distributed skin contact term.')
eq(r'C_i\dot T_i=\sum_jg_{ij}(T_j-T_i)+H_{a,i}(T_a-T_i)+H_{b,i}(T_b-T_i)+S_i')
eq(r'g_{ij}=\rho c_pD\frac{A_{ij}}{d_{ij}}\min(\phi_i,\phi_j),\quad C_i=\rho c_pV_i')
para('Here $\\phi$ is fluid fraction, $A_{ij}$ a face area and $d_{ij}$ the center separation. Symmetric $g_{ij}$ guarantees that internal heat exchange cancels when the equations are summed. D is an effective mixing closure; molecular diffusion alone would not represent motion or buoyant circulation.')
eq(r'w_i\propto\exp\left[-\frac{1}{2}\sum_{k=1}^3\left(\frac{x_{ik}-b_k}{s_k}\right)^2\right],\quad \sum_iw_i=1')
eq(r'V_i=V_{\rm cell}-V_bw_i,\quad H_{b,i}=h_bA_bw_i')
para('Baseline $\\mathbf{b}=(0.55L,\\,W/2,\\,0.45H)$, with widths $\\mathbf{s}=(0.40,0.16,0.12)$ m. Fluid fraction is $\\phi_i=V_i/V_{\\mathrm{cell}}$. The center $\\mathbf{b}$ and widths $\\mathbf{s}$ set the spatial distribution of body effects. Body volume and contact area remain independent inputs: shape is varied through $\\mathbf{s}$ at fixed volume and area. This is a homogenized immersed-body representation, not an anatomically resolved obstruction. A cell whose occupied fraction reaches 0.95 is rejected rather than assigned a negative capacity.')
para(f'A fixed envelope volume is preserved by balancing inlet and overflow. In the baseline the exact displaced-water volume is {rv["water_volume_l"]:.2f} L. Shape scenarios preserve envelope volume when isolating aspect-ratio effects. Volume scenarios deliberately change water depth and hence both storage and side-wall area.')

page('5.1 Spatial evidence: the mean is not the whole bath')
figure('spatial.png','Figure 4. Final temperatures in the three horizontal cell layers. All layers use one color scale; the top layer contains the prescribed inlet-to-overflow stream. Geometry is in metres, and values are cell averages.',height=199)
para('The heat map is calculated from the same archived trajectory as Figure @fig:temperature@. It shows where the imposed transport path and environmental/body sinks leave temperature differences. The plots are horizontal slices through a three-dimensional network with exchange between layers, not three independent two-dimensional models.')
para('A temperature range summarizes the spread but cannot show its location. The maps make the physical interpretation inspectable: localized replenishment and distributed losses must be balanced through mixing. Every cell contributes to the comfort test; a high mean cannot compensate for a cold region.')
para('The Gaussian body representation changes both storage and exchange distribution. A map does not prove that this homogenized representation captures anatomy, recirculation or buoyancy. Its role is to reveal the actual implications of the declared model, not to create the appearance of a resolved flow simulation. The refinement table separately checks how cell size affects the result.')

page('6. Inlet transport, solver and strategy search')
para('Inlet and overflow are on opposite ends of a surface stream. Every path edge carries the same q: the first cell receives hot water, interior cells receive upstream water and lose the same volume downstream, and the last cell discharges through the overflow.')
eq(r'S_1=\rho c_pq(T_{\rm in}-T_1),\quad S_i=\rho c_pq(T_{i-1}-T_i)')
eq(r'\sum_i C_i\dot T_i=-\sum_iH_{a,i}(T_i-T_a)-\sum_iH_{b,i}(T_i-T_b)+\rho c_pq(T_{\rm in}-T_{\rm out})')
para('This stream deliberately allows hot-water short circuit. Heat can leave at a locally warm outlet before warming a distant cold region. It is an explicit transport assumption, not an inferred flow field. Section 11.1 changes the internal path while preserving inlet and overflow; alternative inlet placement would still require another network and calibration.')
para('For a fixed flow, the network is affine linear. Augmenting the state by a constant one permits matrix-exponential propagation, avoiding a large forward-Euler step restriction [4]. A delayed-start policy has two exact constant-control segments.')
eq(r'\dot{\mathbf{T}}=A(q)\mathbf{T}+\mathbf{b}(q),\quad \mathbf{z}(t+\tau)=e^{\widetilde{A}(q)\tau}\mathbf{z}(t)')
para('Starts are tested at 0, 120, …, 1200 seconds. For each, rates from 0 to 3 L/min are bracketed on a 0.2 L/min grid; the first crossing of the lower-temperature requirement is refined by Brent’s root method. The search targets $T_{\\min}+0.03$°C as numerical reserve, then checks the upper-temperature and spread limits at 5-second output intervals. Starts that already violate the floor are rejected.')
para('This is a reproducible candidate search. Nonmonotone flow responses, untested delays, pulsed inputs, inlet relocation and feedback are not excluded by the calculation. A failed search means no candidate was accepted, not that every possible action is infeasible. The independent checks further examine the chosen trajectory between samples.')

page('7. The spatial result and the mixing penalty')
figure('temperature.png','Figure 5. Matrix-exponential cell temperatures under the selected policy. The shaded range covers the coldest cell and the hottest cell outside the inlet jet zone; the mean alone would hide cold and hot locations.',height=208)
table([['Result','Baseline'],['Rate / start',f'{b["flow_lpm"]:.3f} L/min / {b["delay_s"]/60:.1f} min'],['Added water',f'{b["water_l"]:.2f} L'],['Minimum / maximum',f'{b["min_temp"]:.3f} / {b["max_temp"]:.3f}°C'],['Maximum simultaneous spread',f'{b["max_span"]:.3f}°C'],['Final volume-weighted mean',f'{b["final_mean"]:.3f}°C']],[300,168])
para('Within the constant-rate family, starting the trickle immediately ranks ahead of delayed starts here, even though waiting is optimal in the ideal mixed model. The distant water needs time to receive heat; larger late rates create a warmer inlet region before they solve the cold-region constraint. This is a concrete consequence of resolving space.')
para(f'Holding a perfectly mixed bath at 40°C throughout would use {a["constant_at_target_l"]:.2f} L. This is a stricter reference service, not a like-for-like optimum. Our accepted 1°C cooling allowance uses less water partly because it provides a different service. The comparable mixed model with the same lower limit uses {a["mixed_optimum_l"]:.2f} L. The gap also reflects our restricted control family and 0.03°C numerical reserve; it cannot be attributed purely to imperfect mixing.')

page('7.1 A time-varying schedule uses less water')
flows=ctl['flow_lpm'];K=len(flows);lead=next((i for i,v in enumerate(flows) if v>1e-3),K);trail=next((i for i,v in enumerate(reversed(flows)) if v>1e-3),K);seg_min=ctl['segment_s']/60
para(f'Constant-rate policies are a narrow family. We therefore optimize piecewise-constant inlet flow in K equal segments (K = 3, 6, 12) by sequential quadratic programming, minimizing added water under the same floor and outside-jet limits (with the 0.03°C floor reserve), sampled every 5 s, from four starting schedules. The problem is non-convex: each result is the best local optimum found, with no global claim.')
rows=[['Policy','Water (L)','Change','Min / max (°C)','Spread (°C)'],['Best constant rate',f'{b["water_l"]:.2f}','—',f'{b["min_temp"]:.2f} / {b["max_temp"]:.2f}',f'{b["max_span"]:.2f}']]
for run in ct:rows.append([f'{run["segments"]} segments, coarse candidate',f'{run["water_l"]:.2f}',f'{100*(run["water_l"]/b["water_l"]-1):+.1f}%',f'{run["min_temp"]:.2f} / {run["max_temp"]:.2f}',f'{run["max_span"]:.2f}'])
rows.append([f'{ctl["segments"]} segments, accepted',f'{ctl["water_l"]:.2f}',f'{-save:.1f}%',f'{ctl["min_temp"]:.2f} / {ctl["max_temp"]:.2f}',f'{ctl["max_span"]:.2f}'])
rows+=[['Perfect-mixing optimum',f'{a["mixed_optimum_l"]:.2f}','','',''],['Energy lower bound',f'{a["energy_lower_bound_l"]:.2f}','','','']]
table(rows,[150,70,70,100,78])
pseudo='''Input: network, limits, K, starting schedules\nfor each starting schedule x0:\n  minimize sum(x)*segment_time  over 0 <= x <= 3 L/min\n  subject to  min_i T_i(t) >= Tmin+reserve,\n              max_{i in Omega} T_i(t) <= Tmax,\n              spread over Omega <= span   (every 5 s)\nretain coarse candidates and buffered alternatives;\nreplay on three meshes with independent integration;\naccept only if continuous bounds meet all limits'''
tex.append('\\noindent\\begin{minipage}{\\linewidth}\\begin{Verbatim}[frame=single,fontsize=\\small,framesep=4pt,xleftmargin=5pt,xrightmargin=5pt]\n'+pseudo+'\n\\end{Verbatim}\n\\end{minipage}\\par\\medskip\n')

figure('control.png',f'Figure 6. Selected buffered {K}-segment schedule against the best constant rate (top) and the range of cell temperatures outside the inlet jet zone (bottom); dotted lines mark the limits. The baseline concentrates inflow in the middle 15 minutes; both no-flow periods enter the independent checks.',height=176)
para(f'The accepted {K}-segment policy is off for the first {lead*seg_min:.1f} minutes and last {trail*seg_min:.1f} minutes, with a peak flow of {max(flows):.2f} L/min. For consecutive {rv["segment_min"]:g}-minute intervals the rates, rounded to nine decimals, are {rv["flow_rates_text"]} L/min; the interval duration times their sum is {ctl["water_l"]:.6f} L. It adds {ctl["water_l"]:.2f} L, {save:.1f}% below the constant rate. Its {ctl["buffer_c"]:g}°C design margin sacrifices some water savings to protect the stated constraints. The remaining {ctl["water_l"]-a["energy_lower_bound_l"]:.2f} L gap to the energy bound is not an optimality certificate.')
mr=MC['accepted_independent']['meshes']
para(f'The unbuffered {raw_ctl["segments"]}-segment candidate uses {raw_ctl["water_l"]:.2f} L but reaches a spread of {rv["rejected_finest_spread_c"]:.3f}°C on the finest mesh, above the 1.5°C limit, so it is rejected. Among the tested buffered alternatives, the accepted {K}-segment policy gives spreads of {mr[0]["max_span"]:.3f}, {mr[1]["max_span"]:.3f} and {mr[2]["max_span"]:.3f}°C on the 8 × 4 × 3, 12 × 6 × 4 and 16 × 8 × 6 meshes. Independently integrated continuous-time bounds also pass on each mesh. This establishes numerical feasibility for these tested networks, not mesh-independent physics or a global minimum.')

page('7.2 What does staying close to the start temperature cost?')
fm={f_['floor']:f_ for f_ in E['frontier']}
w=lambda fl:fm[fl]['constant_l']
para(f'The task asks for a bath close to its initial temperature without wasting much water, which is a trade-off rather than a single optimum. Figure @fig:frontier@ repeats the search while the allowed fall below 40°C changes from 0.25 to 3°C; the 1°C case is the baseline. With a fall of 2.5°C or more the stored heat suffices and no water is added. At 2°C the best constant rate adds {w(38.0):.1f} L, at 1.5°C {w(38.5):.1f} L, at 1°C {w(39.0):.1f} L and at 0.75°C {w(39.25):.1f} L. Between 2°C and 0.75°C each further 0.5°C of tolerance is therefore worth roughly {(w(39.25)-w(38.0))/(2.0-.75)/2:.0f} L, almost linearly. At 0.5°C the best constant rate adds {w(39.5):.1f} L; for a fall of 0.25°C no constant-rate policy was accepted, while the perfectly mixed bath would still need {fm[39.75]["mixed_l"]:.1f} L.')
figure('frontier.png','Figure 7. Water use versus temperature tolerance. Crosses denote unsuccessful searches, not zero water demand; the dotted line marks the baseline. Allowing a larger fall sharply reduces demand in the tested constant-rate family.',height=182)
para(f'The curve is the practical answer to “how close is close enough”: below a 2.5°C fall every degree of tolerance bought back costs about the same, so the tolerance is worth choosing deliberately. The perfectly mixed curve lies below the spatial one at every tolerance, and the gap widens as the tolerance tightens, from {fm[38.0]["constant_l"]-fm[38.0]["mixed_l"]:.1f} L at 2°C to {fm[39.25]["constant_l"]-fm[39.25]["mixed_l"]:.1f} L at 0.75°C: the stricter the comfort requirement, the more uneven mixing costs. Only constant-rate policies are searched here; scheduled flow (Section 7.1) lowers the baseline point by about {save:.0f}% at this one point. Schedules at other tolerances have not been optimized here.')

page('7.3 Can a user follow the schedule?')
tol=E['control']['tolerance'];price=E['control']['buffer_price'];rob=E['control'].get('robust_tolerance')
us=tol['uniform_scale_slack_c'];rnd=tol['random_error'];seg_t=tol['segments']
pw={x['buffer_c']:x['water_l'] for x in price}
worst=min(seg_t,key=lambda x:x['slack_plus20']);calm=[x for x in seg_t if x['slack_plus20']>-1e-3 and x['slack_minus20']>-1e-3]
para(f'We distinguish fixed tap bias from random segment errors. For the unbuffered 12-segment candidate, multiplying every rate by 0.9 or 1.1 crosses a limit by {-us["0.90"]:.3f} and {-us["1.10"]:.3f}°C. Independently drawing each multiplier from a normal distribution of mean 1 and standard deviation 0.1, clipped below zero, gives median and 5th-percentile slacks of {rnd["0.10"]["median_slack_c"]:.3f} and {rnd["0.10"]["p05_slack_c"]:.3f}°C (200 draws, seed 11). Standard deviation 0.1 does not mean an error bounded within ±10%. Negative slack is a violation, however small.')
para(f'The error is not symmetric. The most sensitive segment is segment {worst["segment"]+1} ({raw_ctl["flow_lpm"][worst["segment"]]:.2f} L/min), where raising the flow by 20% breaks the limits by {-worst["slack_plus20"]:.3f}°C and lowering it by 20% by {-worst["slack_minus20"]:.3f}°C: extra hot water overheats the inlet region and widens the spread. Over-delivery in a high-flow segment is the error to guard against.'+(f' {len(calm)} of the {len(seg_t)} active segments '+('tolerates' if len(calm)==1 else 'tolerate')+' a 20% error in either direction.' if calm else ''))
def money_text(b):
    return 'no schedule' if pw.get(b) is None else f'{pw[b]:.2f} L (+{pw[b]/pw[0.]-1:.0%})'
rob_text=''
if rob:
    r10=rob['random_error']['0.10']
    rob_text=f' With the 0.1°C buffer, {r10["share_within_limits"]:.0%} of 200 draws with independent Gaussian multiplier standard deviation 0.1 stay within the limits.'
para(f'The price of a margin is measured on a 6-segment version. Requiring all three limits to hold with a buffer b gives {pw[0.]:.2f} L at b = 0, {money_text(0.1)} at 0.1°C, {money_text(0.2)} at 0.2°C and {money_text(0.3)} at 0.3°C.'+rob_text+f' The {ctl["buffer_c"]:g}°C policy is selected here for its independently checked numerical margin. Its {rv["tap_error_share"]:.0%} acceptance under the stated random error model does not make it a reliable manual prescription; a real bath needs temperature feedback and separate calibration.')
page('7.4 Measurement ambiguity changes the decision')
para('Mixing changes timing: the weaker-mixing candidate starts immediately. Two probes miss violations in two of nine cases. We now propagate observation ambiguity into the supply decision.')
para('A separate synthetic trial applies (0, 0, 1.2, 0, 0, 0) L/min in five-minute stages. Known geometry starts uniformly at 40°C; cells 89 and 6 are read every 30 s. Assumed reading errors and constant probe biases are each bounded by ±0.02°C; these are not instrument specifications.')
para('For parameters $\\theta$ and probe j, let $d_j(t;\\theta)=T_j(t;\\theta)-y_j(t)$. At observed times $\\mathcal{T}=\\{0,30,\\ldots,1800\\}$ s, a model is compatible when a constant correction $a_j$ exists such that')
eq(r'\min_{|a_j|\leq0.02}\max_{t\in\mathcal{T}}|d_j(t;\theta)-a_j|\leq0.02\quad(j=1,2).')
para('The minimax correction is the extreme-discrepancy midpoint clipped to the bias bound; physical bias is $b_j=-a_j$. A trace spanning −0.04 to +0.04°C fails: its offset cannot vary between readings.')
para(f'Our grid has 7 mixing values (0.00085–0.00115 m²/s), 9 surface and 9 body coefficients (20–30 and 15–35 W/(m² K)), and 5 delivery multipliers (0.95–1.05). Of {CAL["candidate_models"]} models, {CAL["compatible_models"]} fit. This finite decision ambiguity set is neither a confidence region nor a probability distribution.')
para(f'Table @tab:measurement-control@ compares archived policies with a replacement optimized on ten extreme/failing models, using a 2 L/min bound, 0.1°C target and 0.03°C extra floor reserve. All {CAL["compatible_models"]} pass three-grid envelopes; the tightest spread bound is {cal_span:.6f}°C. The selected target is not an all-model margin or global optimum.')
cal_rows=[['Policy','Command (L)','Delivered (L)','Sampled pass']]
for label,command,count in [('Constant',TR['constant_command_l'],sum(row['sampled_passed'] for row in TR['constant_rows'])),('Nominal six-stage',ctl['water_l'],CAL['compatible_models']-CAL['baseline_sampled_failures']),('Ambiguity-set six-stage',CAL['commanded_water_l'],sum(v>=0 for v in CAL['rounds'][-1]['sampled_slacks_c']))]:
    cal_rows.append([label,f'{command:.2f}',f'{command*.95:.2f}–{command*1.05:.2f}',f'{count}/{CAL["compatible_models"]}'])
table(cal_rows,[158,86,122,102],caption='Policies on the same measurement-compatible set',label='measurement-control')
para(f'Counts share the same 178 models, network and five-second sampling; archived policies are not re-optimized. Only the replacement has 534 three-grid envelopes. Its rates are '+', '.join(f'{q:.6f}' for q in cal_flow)+f' L/min, five minutes each, as computational settings. Envelope extrema are {min(row["lower_temperature_bound_c"] for row in CAL["independent"]):.4f} and {max(row["upper_temperature_bound_c"] for row in CAL["independent"]):.4f}°C.')
para(f'The replacement costs {(CAL["commanded_water_l"]/ctl["water_l"]-1)*100:.2f}% more than the nominal policy; feasibility repair does not establish information value. With the same prior, probes and errors, a zero-inlet 30-minute cooling trial leaves {IV["compatible_models"]} models. Delivery bias remains unidentified, yet its candidate passes {len(IV["independent"])} three-grid envelopes. These separate nominal-observation sets intersect in {iv_intersection} models; they are not nested, probabilistic or information scores.')
para('Table @tab:information-cost@ separates control and trial water. Both candidates restart at uniform 40°C with the same control family and design targets.')
obs_table=[['Observation / trial','Models','Control (L)','Trial (L)'],['Nominal / passive',str(IV['compatible_models']),f'{iv_water:.2f}','0.00'],['Nominal / pulse',str(CAL['compatible_models']),f'{CAL["commanded_water_l"]:.2f}','6.00']]
for truth,display in [('strong_mixing_low_loss','Strong mixing'),('weak_mixing_high_loss','Weak mixing')]:
    for design in ['passive','pulse']:
        row=obs_rows[(truth,design)]
        water=f'{row["selected"]["command_l"]:.2f}' if row['accepted'] else 'Not accepted'
        if truth=='weak_mixing_high_loss' and design=='pulse':water+='*'
        obs_table.append([display+' / '+design,str(row['models']),water,'0.00' if design=='passive' else '6.00'])
table(obs_table,[180,62,124,102],caption='Observation-conditioned trial and control costs',label='information-cost')
para('Passive rates are '+', '.join(f'{q:.6f}' for q in iv_flow)+f' L/min. Initial filling and reset are not free; these conditional candidates do not establish expected information value or global optimality.')
para(f'Let n unchanged baths share one trial; let $\\alpha\\in[0.95,1.05]$ be the common delivery multiplier and $R_0,R_1$ the actual reset litres for passive and pulse designs. The difference between their total actual-water costs is')
eq(r'C_0-C_1=\alpha\bigl(n\Delta-6\bigr)+R_0-R_1,\qquad \Delta='+f'{iv_delta:.6f}'+r'\ \mathrm{L}.')
para(f'At nominal delivery, passive costs less for one bath if $R_0-R_1<{6-iv_delta:.4f}$ L. Equal reset costs give a crossover at {6/iv_delta:.2f} baths: passive is cheaper through six, pulse from seven. Reuse requires unchanged geometry, heat transfer, probes and delivery bias; otherwise remeasure. This is not online feedback or a real-bath guarantee.')
para(f'Two predeclared alternative mechanisms use triples (D, surface coefficient, body coefficient) of (0.00115, 20, 15) and (0.00085, 30, 35), in m²/s and W/(m² K), with nominal delivery. Each trial is separate and retains the same prior and errors. In the strong-mixing case, the cost gap is {strong_delta:.4f} L: equal reset costs move the crossover to {6/strong_delta:.2f} uses, hence pulse from six. Across the three accepted candidates, {OBS["independent_checks"]} distinct model-grid envelopes pass.')
para('*The weak-mixing pulse candidate passes the physical bounds despite a failed line search and an unmet extra design margin; it is not a successful optimum. No passive candidate was accepted within two starts and three constraint-generation rounds. That failure proves neither infeasibility nor that a pulse is necessary. The observations change decisions, but their outcomes are not known before the trial: this is conditional policy adaptation, not an ex ante optimal experiment or sequential inference.')


page('8. Separate geometry, size and body effects')
rows=[['Change from baseline','Water (L)','Interpretation']]
for key,desc in [('shallow wide','Same envelope volume'),('deep narrow','Same envelope volume'),('small bath','Lower water depth'),('large bath','Higher water depth'),('deep bath','Depth 0.35 m, like a bath filled to the shoulders'),('larger body','More displacement/contact'),('long body','Shape only; fixed volume/area'),('warmer skin','Skin at 36°C'),('cooler skin','Skin at 32°C')]:
 v=sc[key]['policy'];rows.append([key.title(),f'{v["water_l"]:.2f}' if v['feasible'] else 'No candidate',desc])
table(rows,[148,86,234])
fx=lambda k:(f'needs {sc[k]["policy"]["water_l"]:.2f} L' if sc[k]['policy']['feasible'] else 'has no accepted candidate')
para(f'At equal volume, the wide, shallow tub has a larger exposed top area and a changed diffusion length; it {fx("shallow wide")}. The deep, narrow tub needs {sc["deep narrow"]["policy"]["water_l"]:.2f} L against {b["water_l"]:.2f} L, because a deep, narrow envelope reduces top-area heat loss, although a real deep bath may stratify, which Section 9 tests with a separate vertical-mixing scenario. Geometry is therefore more than an interchangeable cooling coefficient.')
para(f'Changing depth at fixed length and width changes thermal storage and shell area. Greater water volume slows cooling, which can lower added water over a short fixed horizon: the large bath needs {sc["large bath"]["policy"]["water_l"]:.2f} L, while the small bath {fx("small bath")}. The 0.23 m baseline depth is shallow, and its surface-to-volume ratio is about 1.7 times that of a bath filled to the shoulders; a 0.35 m depth {fx("deep bath")}, so the baseline overstates the surface-loss share of a deeper bath. That does not mean a larger bath conserves total water: filling it initially uses more. J counts replenishment only, and this distinction prevents a misleading conservation claim.')
para(f'The larger-body scenario simultaneously displaces more water and increases assumed contact area; it is a combined size scenario and {fx("larger body")}. The long-body scenario isolates the spatial distribution by keeping total body volume and contact area fixed. Warmer skin reduces the temperature difference driving body heat loss. These changes quantify conditional dependence; they do not establish measured human heat transfer.')
para('To transfer the model to a real tub, measure water volume after entry, submerged contact geometry, temperatures at several depths and distances, and no-inlet cooling. Shape and temperature should not be inferred from a single mean cooling curve.')

page('9. Motion and a bubble layer can change the policy')
rows=[['Scenario','Added water (L)','Search outcome']]
for key in ['weak mixing','strong mixing','moving with added surface loss','stratified','convective surface layer','foam','tight comfort','loose comfort','low loss','high loss','cool supply']:
 v=sc[key]['policy'];rows.append([key.title(),f'{v["water_l"]:.2f}' if v['feasible'] else '—','Accepted' if v['feasible'] else 'None accepted'])
table(rows,[224,116,128])
para(f'Increasing D reduces the gradient created by the localized inlet. The strong-mixing scenario uses {sc["strong mixing"]["policy"]["water_l"]:.2f} L against {b["water_l"]:.2f} L, but motion may also increase heat loss. When D is increased together with a 20% increase in the surface coefficient (30 instead of 25 W/(m² K)), the need rises to {sc["moving with added surface loss"]["policy"]["water_l"]:.2f} L and most of the benefit disappears. The comparison deliberately separates transport improvement from its possible boundary cost.')
para(f'Stratification is tested separately. A hot inlet layer is lighter than the water below, and the stable density gradient suppresses vertical mixing. With a cell height of 0.077 m, a vertical temperature difference of 1 K, a velocity scale of 0.02 m/s and an expansion coefficient of about 3.8e-4 per K, the gradient Richardson number is $\\mathrm{{Ri}}=g\\beta\\,\\Delta T\\,\\ell/u^2\\approx 0.7$. The Munk–Anderson stability function for scalars, $(1+3.33\\,\\mathrm{{Ri}})^{{-3/2}}$ [8], then reduces vertical diffusivity to about 0.15 of its neutral value. We test a vertical-to-horizontal ratio of 0.2. The best constant rate becomes {sc["stratified"]["policy"]["water_l"]:.2f} L against {b["water_l"]:.2f} L, but the maximum spread rises from {b["max_span"]:.2f} to {sc["stratified"]["policy"]["max_span"]:.2f}°C against the 1.50°C limit. Stratification therefore costs little water here and uses {100*(sc["stratified"]["policy"]["max_span"]-b["max_span"])/(p["span"]-b["max_span"]):.0f}% of the remaining uniformity margin; the ratio is an order-of-magnitude scenario and the Richardson estimate uses assumed velocity and temperature scales. The stable layer is an upper-bound picture: evaporative cooling at the surface can instead drive convection and raise vertical mixing, so a vertical-to-horizontal ratio of 3 is also tested, and it {fx("convective surface layer")}.')
para(f'The foam scenario multiplies only the effective surface coefficient by 0.4. With all other inputs fixed, the best constant rate falls to {sc["foam"]["policy"]["water_l"]:.2f} L. The assumed 60% reduction is a scenario, not an experimentally established property of bubble-bath additive. If the layer breaks up or motion raises evaporation, this result must be recomputed.')
none=[k.title() for k,v in sc.items() if not v['policy']['feasible']]
para('No accepted candidate exists for: '+', '.join(none)+'. They are reported as such, not hidden in a favorable average. In the weak-mixing, high-loss and wide-shallow cases, flows large enough to keep every cell above the floor already push the spread above its 1.5°C limit (checked at constant flows from 0.8 to 2.5 L/min), but these sampled candidates cannot establish that every constant flow fails. No constant-rate policy was accepted by the documented search in those scenarios. Their outcomes identify where the restricted strategy must change. Potential responses include improved circulation, a different inlet path, a shorter bath, or a different comfort tolerance. The paper does not certify which response is safe or optimal without corresponding physical evidence.')

page('10. Validation: independent evidence and remaining error')
num=lambda name:json.loads(next(c['evidence'] for c in checks if c['name']==name))
energy=num('instantaneous_energy_balance_with_overflow');rk=num('independent_RK45_vs_archived_matrix_exponential');env=num('continuous_time_policy_envelope')
para(f'All {len(checks)} recorded checks pass. Independent heat-flow arithmetic sums environmental losses, body exchange and local-temperature overflow; the largest instantaneous residual is {energy["max_residual_w"]:.2e} W. An adaptive RK45 integration with independently assembled right-hand side agrees with the archived matrix-exponential trajectory within {rk["maximum_temperature_difference_c"]:.2e}°C. This tests numerical implementation, not a second physical model.')
para('A constructed uniform-loss problem reproduces its analytic exponential cooling solution. Internal exchange cancels globally, and the stream has exactly one overflow sink. Positive off-diagonal dynamics and nonpositive row sums support physical bounds and a contractive derivative estimate for each constant-flow segment.')
para(f'Half-second replay is supplemented by a derivative bound: if |dTi/dt| ≤ L, a point lies at most 0.25 seconds from a sample, so temperatures differ by at most L/4 and spread by at most L/2. With an integration allowance and no relaxation of the physical limits, the resulting lower envelope is {env["lower_temperature_bound_c"]:.4f}°C, upper {env["upper_temperature_bound_c"]:.4f}°C, and spread upper bound {env["span_upper_bound_c"]:.4f}°C. This is a conditional floating-point envelope, not interval-arithmetic certification.')

ind=MC['accepted_independent']
para(f'The accepted schedule uses an independently assembled right-hand side and adaptive RK45, restarted at every flow switch. Nonnegative off-diagonal transport and nonpositive row sums give an infinity-norm contraction bound for the derivative within each segment. One-second samples alone leave some intervals unresolved; adding RK45 step endpoints and bisecting unresolved intervals once on the finest mesh gives bounds of {ind["lower_temperature_bound_c"]:.4f}°C for the minimum, {ind["upper_temperature_bound_c"]:.4f}°C for the maximum and {ind["span_upper_bound_c"]:.4f}°C for the spread. These pass the physical limits without threshold relaxation. A 2e-6°C integration allowance is included; this floating-point check is conditional on the network, not interval arithmetic or experimental validation. The {len(checks)} baseline checks are separate.')

page('11. Resolution, uncertainty and transfer to a real bath')
f=r['mesh']['fine_policy'];fp=r['mesh']['coarse_policy_on_fine'];cv=r['mesh']['convergence']
table([['Mesh (cells)','Max outside jet zone','Spread outside zone','Inlet-cell max']]+[[f'{c["grid"][0]} × {c["grid"][1]} × {c["grid"][2]} ({c["cells"]})',f'{c["max_temp"]:.3f}°C',f'{c["max_span"]:.3f}°C',f'{c["inlet_cell_max_temp"]:.3f}°C'] for c in cv],[130,115,115,108])
para(f'The same constant-rate policy is replayed on three meshes. The ceiling and spread quantities outside the jet zone agree within {max(c["max_temp"] for c in cv)-min(c["max_temp"] for c in cv):.3f}°C and {max(c["max_span"] for c in cv)-min(c["max_span"] for c in cv):.3f}°C, and the tested constant-rate trajectory stays within the comfort limits on these meshes. The inlet-cell maximum rises from {cv[0]["inlet_cell_max_temp"]:.2f} to {cv[2]["inlet_cell_max_temp"]:.2f}°C with refinement; that is why the cell is excluded rather than constrained. The selected water amounts on the 8 × 4 × 3 and 12 × 6 × 4 meshes are {b["water_l"]:.3f} and {f["water_l"]:.3f} L ({100*abs(f["water_l"]-b["water_l"])/b["water_l"]:.2f}% apart). Three meshes are a diagnostic, not an asymptotic convergence-order study.')
para('Parameter uncertainty concerns heat loss, body exchange and mixing. Structural uncertainty concerns the prescribed surface stream, fixed skin reservoir, homogenized body and constant effective D. These are different errors. The scenario table explores parameter dependence and one coupled motion effect; it is not a probability distribution or confidence interval.')
names_lr={'h_surface':'surface coefficient','h_body':'body coefficient','air_temp':'room temperature','body_temp':'skin temperature','h_wall':'shell coefficient','D':'mixing diffusivity'}
para(f'Range analysis. Section 2 gives ranges for six inputs. {lr["samples"]} scrambled Sobol points cover them (D log-uniform), and the constant-rate search runs at each. {lr["feasible"]} points have an accepted candidate. Among those, the required water is {qq["0.05"]:.1f}, {qq["0.25"]:.1f}, {qq["0.5"]:.1f}, {qq["0.75"]:.1f} and {qq["0.95"]:.1f} L at the 5th, 25th, 50th, 75th and 95th percentiles. The remaining {lr["samples"]-lr["feasible"]} points have none, mostly because of weak mixing (below). The baseline of {b["water_l"]:.1f} L sits in the upper half of this distribution.')
figure('ranges.png','Figure 9. Required water against the surface coefficient for each Sobol draw. Crosses at the top mark draws with no accepted policy; the vertical line is the baseline. Associations among accepted draws do not describe rejected conditions or establish causation.',height=182)
para('Spearman rank correlations with water, over accepted draws: '+', '.join(f'{names_lr[k]} {v:+.2f}' for k,v in sorted(sp.items(),key=lambda kv:-abs(kv[1])))+'.')
from scipy.stats import mannwhitneyu
okd=[r_ for r_ in lr['rows'] if r_['feasible']];nod=[r_ for r_ in lr['rows'] if not r_['feasible']]
pv={k:float(mannwhitneyu([r_['inputs'][k] for r_ in okd],[r_['inputs'][k] for r_ in nod]).pvalue) for k in names_lr}
others=min(v for k,v in pv.items() if k!='D');pdtxt='< 1e-4' if pv['D']<1e-4 else '= %.3f'%pv['D']
para(f'The correlations use accepted draws only, so they say nothing about which draws have an accepted policy at all. In this finite search, acceptance differs most strongly with the mixing diffusivity: its median is {np.median([r_["inputs"]["D"] for r_ in okd]):.1e} m²/s for draws with an accepted policy and {np.median([r_["inputs"]["D"] for r_ in nod]):.1e} for draws without (Mann–Whitney p {pdtxt}), while no association is detected for the other five inputs in this sample (smallest p = {others:.2f}). Weak mixing leaves the far water too cold unless the flow is raised so far that the inlet region breaks the spread limit. The draws are uniform over ranges that we chose; they are not a probability distribution for any real tub. The main message: among accepted candidates, the loss coefficients and room temperature affect the water needed, while the mixing closure strongly affects search acceptance, which is why Section 2 ties the coefficients to outside evidence and Section 9 reports weak mixing separately.')
para('In the nominal example, Section 7.4 motivates inlet-free cooling as a low-cost characterization option, recording water volume and room conditions. Multiple temperature probes distinguish aggregate heat loss from mixing. A separate inlet experiment records flow and inlet/outlet temperatures, allowing overflow energy to be checked. Motion and foam need matched trials because both can alter transfer coefficients. Reserve an entire experiment for prediction checks after fitting. A single mean-temperature series cannot separate the surface, shell and body coefficients, so only calibrated and independently tested parameters would support advice for a particular bath.')

para(f'The finite-volume stencil is also checked against an insulated three-dimensional cosine diffusion mode: four successively refined grids approach second order (finest observed order {FV["observed_orders"][-1]:.2f}). A zero-diffusion inlet path matches the independent stirred-cell cascade step response within {max(x["max_error_c"] for x in FV["advection_rows"]):.1e}°C. These verify implementation in empty-domain limits, not the mixing closure or real baths [9].')

page('11.1 Do the policies survive a different body or flow path?')
para(f'We replay both archived policies on the {math.prod(ST["grid"])}-cell network under two structural alternatives and their combination, without re-optimizing. A finite contact reservoir replaces fixed skin: $C_b \\dot B=\\sum_i H_{{b,i}}(T_i-B)$, with {rv["body_capacity_kj_per_k"]:.2f} kJ/K and initial B = {p["body_temp"]:g}°C. This tests storage, not physiology; thermoregulation is omitted. The alternative face-connected stream descends at the inlet, crosses the bottom, then rises to the unchanged overflow. Geometry, mixing, losses and the jet zone remain fixed.')
rows=[['Scheduled-policy structure','Min (°C)','Max (°C)','Spread (°C)']]
labels={('surface',False):'Baseline',('surface',True):'Finite contact reservoir',('deep',False):'Deep transport path',('deep',True):'Both alternatives'}
for row in ST['rows']:
 if row['policy']=='scheduled':
  rows.append([labels[(row['route'],row['body_capacity_j_per_k'] is not None)],f'{row["min_temp"]:.3f}',f'{row["max_temp"]:.3f}',f'{row["max_span"]:.3f}'])
table(rows,[210,86,86,86])
assert rv['all_structures_sampled_passed'], 'Structural alternatives no longer preserve sampled feasibility'
para(f'Both policies meet the sampled limits in all four structures. Body storage changes the scheduled minimum by {rv["body_minimum_change_c"]:+.3f}°C; the deep route changes its spread by {rv["deep_spread_change_c"]:+.3f}°C. The effective body node ends near {rv["final_body_temp_c"]:.2f}°C. Thus these limited changes preserve sampled feasibility, not optimality or the {save:.0f}% saving after re-optimization.')
para(f'For the original policies, independent heat-flow arithmetic and RK45 restart at every switch; 1/0.5 s sampling differs by at most {rv["structure_max_time_delta_c"]:.2e}°C. Maximum energy residuals are {rv["structure_max_instantaneous_w"]:.2e} W and {rv["structure_max_integrated_j"]:.2e} J. The fixed-skin {a["energy_lower_bound_l"]:.2f} L bound does not transfer to a warming body reservoir.')
para(f'The ambiguity-set policy also passes sampled limits in 40 combinations: ten search-selected parameter models, both routes, and fixed/finite body storage. Its lowest temperature is {min(row["min_temp"] for row in TR["structure_rows"]):.4f}°C and largest spread {max(row["max_span"] for row in TR["structure_rows"]):.4f}°C, with independent RK45, 2/1 s sampling and energy checks. None of these alternatives is calibrated or continuously certified; they do not extend the original three-grid certificate or establish re-optimized savings.')

page('12. Conclusions and a policy with clear scope')
para(f'Tolerating a modest decline lets stored heat replace inlet water. Spatial transport then changes the mixed recommendation: a constant trickle starts at once, while nominal scheduling withholds water at both ends and needs {save:.0f}% less. At equal volume the deep, narrow tub needs {sc["deep narrow"]["policy"]["water_l"]:.2f} L; increased body displacement/contact needs {sc["larger body"]["policy"]["water_l"]:.2f} L. Motion can improve mixing while increasing heat loss, and an assumed foam layer reduces demand. Crucially, poorer mixing changes supply timing: the D = 0.0007 m²/s candidate starts immediately. Two fixed readings can miss spatial violations, so timing needs more than a mean-temperature check.')
para(f'For the stated baseline, the best constant trickle is {b["flow_lpm"]:.3f} L/min for {b["water_l"]:.2f} L over {rv["horizon_min"]:g} minutes; the {K}-segment schedule uses {ctl["water_l"]:.2f} L. The scheduled result includes a {ctl["buffer_c"]:g}°C design margin and three-grid continuous-time checks; the floor covers every cell, while the ceiling and spread exclude the inlet zone. Neither is a universal faucet prescription or a proved global optimum over all time-varying controls.')
para(f'<b>Strengths.</b> Exact network conservation, independent integration, proved benchmark and lower bound connect mechanism with decision. Scheduling reduces the nominal bound gap from {b["water_l"]-a["energy_lower_bound_l"]:.1f} to {ctl["water_l"]-a["energy_lower_bound_l"]:.1f} L; physical accuracy remains untested.')
para('Limitations. Local policy search, assumed mixing and jet zone, omitted shell storage, fixed skin and unmodeled flow physics limit transfer. Section 11.1 tests only selected structural alternatives. Preference limits and cell averages do not establish inlet-jet safety.')

para(f'Unique parameter estimation is unnecessary if the remaining models support a decision. Passive cooling cannot identify delivery bias, yet supports a {iv_water:.2f} L candidate. The pulse reduces control water by {iv_delta:.2f} L but spends 6 L first: equal reset costs favor passive for one to six unchanged baths and pulse from seven. This candidate comparison, not the number of fitted parameters, determines which trial is useful. Different synthetic observations move the crossover to six uses or expose search failure. Reset differences can reverse the choice; finite banks do not certify real baths.')

page('13. A warmer bath, with less replacement water',True)
para('A guide for the person in the bathtub','heading')
para(f'<b>Decide what “warm enough” means.</b> A bath need not stay at exactly its starting temperature to remain acceptable. In our example, allowing a 1°C fall still needs about {b["water_l"]:.0f} L of replacement water, while allowing a 2°C fall needs only {sc["loose comfort"]["policy"]["water_l"]:.1f} L. Your actual comfort and health needs must determine the acceptable range.')
para('<b>Distribute the warmth before turning up the tap.</b> The water near the faucet can warm while the far end remains cool. Gentle movement can help redistribute heat. More vigorous motion is not automatically better: it may also increase heat loss from the surface.')
para(f'<b>Time the inflow for the stated baseline conditions.</b> The verified {K}-stage schedule waits {lead*seg_min:g} minutes, adds hot water during the next {(K-lead-trail)*seg_min:g} minutes, then stops for {trail*seg_min:g} minutes. It uses {ctl["water_l"]:.2f} L against {b["water_l"]:.2f} L for a constant trickle. This timing requires the stated heat-loss and mixing conditions; the weaker-mixing example needs inflow from the start. It is not a rule for an uncharacterized bath. A limited body-storage and flow-path replay preserves the example’s sampled limits, but does not establish transfer to other baths. Other tubs or body positions need a new calculation; if the water is not mixing or the thermometer disagrees, the schedule is not transferable.')
para(f'<b>Leave room for error.</b> The lowest-water candidate failed our refined calculation. Even with a margin, only {rv["tap_error_share"]:.0%} of trials with independent Gaussian tap multipliers of standard deviation 0.1 stayed within the limits. This is a model experiment, not your success probability. More water is not automatically better: a strong burst can overheat the inlet region.')
para('<b>Check more than one location, and do not assume two readings cover the bath.</b> Our fixed-probe study misses spatial violations even without sensor noise. Reconsider timing when cold or hot locations move. Compare passive cooling with a paid hot-water trial: in this example, our passive candidate uses slightly more control water but avoids the 6 L pulse. With equal reset costs, a pulse pays back only after seven unchanged uses. Both trials take 30 minutes and need a fresh uniform starting state; changes to your bath invalidate that comparison. Cell-average temperature does not establish hot-jet safety.')
para('<b>Remember where the added water goes.</b> Once the tub is full, extra water leaves through the overflow. Hot water that runs along the surface to the overflow may escape before its warmth reaches you. Increasing the stream can waste heat without fixing unevenness.')
para('<b>A bubble layer may help, but the amount is uncertain.</b> An intact insulating surface layer can reduce heat loss. Our calculation explores such a layer; it does not measure the effect of a particular additive. If the layer disappears or the bath behaves differently, reassess rather than relying on the example’s saving.')
para('<b>The practical rule:</b> use the bath’s stored warmth, keep temperature distributed, and add only as much water as your actual conditions require. The numerical example explains these tradeoffs; it is not a tested bathing or safety standard.')

page('14. References and reproducible algorithm',True)
refs=[
'[1] COMAP. 2016 MCM Problem A: A Hot Bath. 2016. Official problem PDF: contest.comap.com/undergraduate/contests/mcm/contests/2016/problems/2016_MCM_Problem_A.pdf.',
'[2] U.S. Department of Energy. DOE Fundamentals Handbook: Thermodynamics, Heat Transfer, and Fluid Flow. DOE-HDBK-1012/2-92, June 1992. Convection heat transfer, Eq. (2-9).',
'[3] IAPWS. Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use. R6-95(2018). iapws.org/technical-guidance/release/IAPWS-95.',
'[4] SciPy developers. scipy.sparse.linalg.expm_multiply and scipy.integrate.solve_ivp, API documentation. docs.scipy.org/doc/scipy/reference/. Accessed 7 October 2026.',
'[5] Bergman, T. L., Lavine, A. S., Incropera, F. P., DeWitt, D. P. Fundamentals of Heat and Mass Transfer, 7th ed. Wiley, 2011. Natural convection above a heated horizontal surface (characteristic length A/P); heat and mass transfer analogy.',
'[6] Menzies, C., Clarke, N., Steward, C. J., Thake, C. D., Pugh, C. J. A., Cullen, T. Vascular, inflammatory and perceptual responses to hot water immersion: impacts of water depth and temperature in young healthy adults. Experimental Physiology, 2025. doi:10.1113/EP092761.',
'[7] OpenAI, Codex (GPT-6-based assistant), and Anthropic, Claude Sonnet 5.5 in Claude Code. Used on 7 October 2026 for modeling, code, validation and report composition; exact builds not independently established. See Report on Use of AI.',
'[8] Munk, W. H., Anderson, E. R. Notes on a theory of the thermocline. Journal of Marine Research, 7(3), 276–295, 1948.',
'[9] NASA/NPARC Alliance. Verification Assessment and Validation Assessment, CFD tutorial. www.grc.nasa.gov/WWW/wind/valid/tutorial/. Accessed 9 October 2026.',
]
for ref in refs:para(ref,'ref')
para('Algorithm and computational record','heading')
para('1. Form cell volumes and capacities; reject excessive body occupancy. Assemble symmetric face exchange, environmental/body conductances and the conservative stream. 2. Compute the mixed closed forms and energy lower bound. 3. Evaluate delayed constant-flow candidates with matrix exponentials and refine the first bracketed lower-temperature crossing. Reject ceiling or spread violations outside the jet zone. 4. Rank accepted candidates by added litres. 5. Independently integrate and check balances, analytic limits, parameter arithmetic and constraints; replay a finer mesh and perturb physical scenarios. 6. Optimize piecewise-constant and buffered schedules, then accept only candidates whose independent three-grid continuous bounds pass. 7. Rerun the constant-rate search at Sobol draws over the literature ranges. Independent RK45 checks use relative tolerance 2e-9, absolute 2e-10°C and steps of at most 5 s. AI assistance is acknowledged in [7].')

names={'D':'D (m²/s)','Dz_ratio':'vertical/horizontal D ratio','h_surface':'surface coefficient (W/m²K)','foam':'surface multiplier','floor':'lower limit (°C)','L':'length (m)','W':'width (m)','H':'depth (m)','body_volume':'body displacement (m³)','body_area':'body contact area (m²)','body_shape':'body widths s (m)','body_temp':'skin temperature (°C)','h_wall':'wall coefficient (W/m²K)','h_body':'body coefficient (W/m²K)','inlet_temp':'inlet temperature (°C)'}
items=list(sc.items())
for part in range(1):
 if part==0:
  page('Appendix A. Scenario definitions',True)
  para('Each row changes only the listed baseline inputs. All unspecified inputs remain as stated in Section 2; geometry and conductance are then rebuilt. The equal-volume aspect-ratio cases retain the envelope volume of 0.22425 m³. Widths s describe a smooth displacement distribution, not measured anatomical semiaxes.')
  para('Accepted candidates are independently replayed on their scenario network at intervals of no more than five seconds. These scenario checks are sampled checks; continuous-time envelopes are reported for the baseline constant rate and the selected scheduled policy; the latter uses additional interval refinement when necessary. “None accepted” refers to the documented finite search and is not an infeasibility theorem.')
 rows=[['Scenario','Changed input(s)']]
 for label,item in items:
  text='; '.join(names.get(k,k)+' = '+(str(v) if isinstance(v,list) else f'{v:.6g}') for k,v in item['changes'].items())
  rows.append([label.title(),text])
 table(rows,[144,324])

page('Report on Use of AI',True)
para('Tool and scope','heading')
para('OpenAI Codex, a GPT-6-based assistant, and Anthropic Claude Sonnet 5.5 through Claude Code assisted development on 7–9 October 2026; exact builds were not independently established. They formulated models, wrote code, checked calculations, drew figures and composed the report. A sealed version preceded comparative learning. The revision read both Outstanding papers 44845 and 54164 in full text, with page overviews and selected readable figures, and COMAP’s commentary; it must not be described as an unseen-problem trial. Their data and figures were not copied. An assistant sub-agent wrote the independent-RHS validation routine and another checked fixed probes; this is AI-assisted review, not independent human verification.')
para('Task','heading')
para('The task was to produce a complete historical MCM case; no conversation wording is reproduced.')
para('Outputs, corrections and verification','heading')
para('On 8 October, independent integration rejected the 19.35 L schedule and accepted a buffered alternative; later fixed-policy replays checked limited body storage and flow-path changes. On 9 October, the baseline values were bound to archived results without repeating that optimization. Earlier coefficient and inlet-zone corrections are recorded in the accompanying development history. References [1]–[4] were checked at the linked sources and [6] in its open manuscript; [5] and [8] were not opened, so their relations were checked indirectly. The AI produced the code, derivations, figures and report; all reported numerical results came from actual calculations.')
para('The control study optimized two known-diffusivity schedules and independently checked their three-grid envelopes and nine fixed-probe cases. Synthetic pulse/passive trials retained 178/510 of 2,835 models; their candidates passed 534/1530 three-grid envelopes. Trial water and unknown reset costs remain separate. Frozen-policy comparison covered one ambiguity bank and ten selected models under four structures. Two additional synthetic mechanisms produced four observation banks and 255 further three-grid envelopes; the weak-passive search and weak-pulse optimizer failure remain explicit. Analytic diffusion and inlet-cascade cases checked the discretization. The original baseline optimization was not rerun; source-bound receipts retain failures and finite scope.')
para('Record limitations','heading')
para('A full exported interaction transcript and every intermediate AI output were not available in this artifact. The task description, tool identification, scope, code artifacts and numerical receipts are retained in the accompanying development record; this report does not invent a transcript. No independent human review or physical bath experiment is claimed.')

TOTAL=SEC[0]
pdf=compile_pdf('paper','A Hot Bath')
(ROOT/'submission').mkdir(exist_ok=True)
shutil.copyfile(pdf,ROOT/'submission'/(TEAM_CONTROL_NUMBER+'.pdf'))
print(json.dumps({'pdf':str(ROOT/'submission'/(TEAM_CONTROL_NUMBER+'.pdf')),'sections':TOTAL,'equations':eqcount,'tables':table_total,'figures':figcount[0],'checks':len(checks)}))
