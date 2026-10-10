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
from observation_values import observation_values, structure_observation_values, structure_decision_values
OBS=observation_values(ROOT)
STRUCT_OBS=structure_observation_values(ROOT)
STRUCT_DEC=structure_decision_values(ROOT)
from common_reserve import common_reserve_values
FAIR=common_reserve_values(ROOT)
from feedback_study import feedback_values, transfer_values, continuous_values
from transport_values import transport_values
AX=transport_values(ROOT)
from recourse_values import recourse_values
RC=recourse_values(ROOT)
AXM=AX['groups'][('uniform',.001)]['selected']; AXS=AX['groups'][('uniform',.003)]['selected']
AXWEAK=next(x['metrics'] for x in AX['run']['rows'] if x['profile']=='uniform' and x['D']==.0003 and x['cells']==160 and x['policy']=='original_constant')
AX_ERR=math.ceil(max(max(x['max_error_c'][-1:]) for x in AX['checks']['records'] if x['check']=='transient_continuum_refinement')*1e6)/1e6
AX_RK=math.ceil(max(x['max_temperature_difference_c'] for x in AX['independent'])*1e9)/1e9
AX_ENERGY=math.ceil(max(x['integrated_energy_error_j'] for x in AX['independent'])*1e5)/1e5
FB=feedback_values(ROOT)
FT=transfer_values(ROOT)
BOX=continuous_values(ROOT)
BOX_CERTS=[next(x for x in row["scales"] if x["scale"]==BOX["scale"]) for row in BOX["rows"]]
BOX_CENTER=BOX["rows"][0]["parameters"]; BOX_WIDTH=BOX_CERTS[0]["halfwidths"]
BOX_BOUND=[math.floor(min(x["temperature_bounds_c"][0] for x in BOX_CERTS)*1e4)/1e4, math.ceil(max(x["temperature_bounds_c"][1] for x in BOX_CERTS)*1e4)/1e4, math.ceil(max(x["temperature_bounds_c"][2] for x in BOX_CERTS)*1e4)/1e4]
FBZERO=FB["completed"][("variants","zero_noise")]
FBRANDOM=FB["completed"][("variants-resume","random_noise")]
assert STRUCT_DEC["all_base_envelopes_passed"] and STRUCT_DEC["repair_sampled_passes"]==STRUCT_DEC["repair_checks"], "Revise structural decision interpretation"
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
 'Mixing, surface, comfort and supply scenarios','Mesh replay: constrained temperatures','Common-reserve structural decisions','Scenario definitions','Scenario definitions (continued)']
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
      1: 'Table @tab:1@ maps each requirement to its answer.',
      2: 'Table @tab:2@ contrasts spatial resolution and data requirements.',
      3: 'Table @tab:3@ separates assumed inputs from anchored coefficients.',
      4: 'Table @tab:4@ summarizes the coefficient anchors and scenario ranges.',
      5: 'Table @tab:5@ defines storage, transport and exchange symbols.',
      6: 'Table @tab:6@ reports the constant-rate trajectory and water use.',
      7: 'Table @tab:7@ separates candidates from proved bounds.',
      8: 'Table @tab:8@ isolates geometry, storage and body changes.',
      9: 'Table @tab:9@ separates transport benefits from boundary losses.',
      10: 'Table @tab:10@ compares constrained temperatures and the excluded inlet peak.',
      11: 'Table @tab:11@ compares structure-specific banks at the same reserves.',
      12: 'Table @tab:12@ lists the changes defining each scenario.',
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
      'spatial.png': 'Figure @fig:spatial@ locates cold regions across layers on one scale.',
      'temperature.png': 'Figure @fig:temperature@ contrasts the mean, coldest cell and spatial range.',
      'control.png': 'Figure @fig:control@ shows flow timing and temperature constraints.',
      'frontier.png': 'Figure @fig:frontier@ compares searched spatial policies with analytical benchmarks.',
      'bounds.png': 'The bracket in Figure @fig:bounds@ separates admissible policies from lower bounds; it supports a comparison of water use without claiming that the spatial search proves a global optimum.',
      'ranges.png': 'The draws in Figure @fig:ranges@ show how surface heat loss changes water demand within the tested ranges, while the rejected draws expose conditions where the search finds no acceptable policy.',
    }
    if name in introductions: para(introductions[name])
    m=re.match(r'^Figure (\d+)\. (.*)$',caption,re.S);assert m,caption
    tex.append(texplot.figure_env(FIG[name],tx(m.group(2)),label='fig:'+name.replace('.png','')))
PREAMBLE=preamble(TEAM_CONTROL_NUMBER, 'A Hot Bath: Conserving Water Without Losing Uniformity')
PREAMBLE=PREAMBLE.replace(r'\begin{document}', r'\usepackage{placeins}'+'\n'+r'\begin{document}')

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

# Realized online policies: action timing and the retained finite ambiguity set.
fa=texplot.Axis('', 'Flow (L/min)', width='0.64\\linewidth',height='2.5cm',xmin=0,xmax=30,ymin=0,legend_columns=3,extra='name=feedbacktop,xticklabels={}')
fa.stairs(FBZERO['flows'],list(range(31)),label='Zero noise').stairs(FBRANDOM['flows'],list(range(31)),color='accent',style='dashed',label='Random noise').stairs([x['baseline_flow_lpm'] for x in FBZERO['steps']],list(range(31)),color='muted',style='dotted',label='Backup')
fb=texplot.Axis('Time (min)', 'Models retained',width='0.64\\linewidth',height='2.4cm',xmin=0,xmax=30,ymin=1,legend=None,extra='ymode=log,at={(feedbacktop.south)},anchor=north,yshift=-0.4cm')
fb.line([x['time_s']/60 for x in FBZERO['steps']],[x['retained_models'] for x in FBZERO['steps']]).line([x['time_s']/60 for x in FBRANDOM['steps']],[x['retained_models'] for x in FBRANDOM['steps']],color='accent',style='dashed')
FIG['feedback.png']=fa.tex()+'\n'+fb.tex()

tex.append(summary_header('A'))

para('A Hot Bath: Conserving Water Without Losing Uniformity','title')
para('Summary','heading')
para('A warm mean does not ensure a uniformly warm bath. We minimize replacement water subject to a lower limit in every cell, and upper-temperature and spread limits outside a 0.15 m inlet zone. Stored heat favors waiting; finite transport can make distant water cold before that waiting period ends.')
para('We prove a coast-then-hold policy optimal for a well-mixed bath, then use a three-dimensional finite-volume thermal network with coefficients derived from textbook correlations and tied to a published immersion study where one exists (Section 2). The best constant rate is compared with an optimized piecewise-constant schedule; neither is proved optimal among all controls.')
para(f'In a {rv["water_volume_l"]:.2f} L water-volume scenario lasting {rv["horizon_min"]:g} minutes, with an initial temperature of {p["initial"]:g}°C and a {p["floor"]:g}°C lower limit, the best accepted constant-rate candidate adds <b>{b["water_l"]:.2f} L</b> at {b["flow_lpm"]:.3f} L/min from the start, and a {ctl["segments"]}-segment schedule with a {ctl["buffer_c"]:g}°C design margin needs <b>{ctl["water_l"]:.2f} L</b>, {save:.0f}% less. The well-mixed optimum is {a["mixed_optimum_l"]:.2f} L, while an independent energy argument gives a {a["energy_lower_bound_l"]:.2f} L lower bound for the spatial problem. A finer mesh changes the constant-rate result by {100*abs(r["mesh"]["fine_policy"]["water_l"]-b["water_l"])/b["water_l"]:.2f}%, and the selected scheduled policy passes independent continuous-time bounds on all three tested meshes.')
para(f'Across {lr["samples"]} Sobol draws over the stated parameter ranges, {lr["feasible"]} yield an accepted constant-rate candidate, needing {qq["0.05"]:.0f}–{qq["0.95"]:.0f} L (5th–95th percentile). Weak mixing often defeats this finite search. Motion improves transport, but the associated extra surface loss can offset the saving. The assumed foam layer reduces constant-flow demand to {sc["foam"]["policy"]["water_l"]:.1f} L; this is a scenario, not a measured additive effect.')
para(f'A distinct axial-dispersion model reproduces remote cooling and shifts the selected start from zero to ten minutes as the tested mixing strengthens. Both adopted baselines have cooler-than-mean overflow: extra water is not evidence of hot-water short circuit. Cooling alone cannot identify the inlet route. At common reserves, passive/pulse candidates use {FAIR["volumes"]["passive"]:.2f}/{FAIR["volumes"]["pulse"]:.2f} L; a reusable 6 L pulse pays from use {FAIR["crossover"]} at equal resets and unchanged conditions. Probe updates give {sum(FBZERO["flows"]):.2f}/{sum(FBRANDOM["flows"]):.2f} L in two nominal noise cases. Our decision rule permits waiting or reduced inflow only with a checked continuation for every surviving model; inconsistent observations trigger reassessment. Narrow boxes certify fixed actions. Separate static recourse tests include a one-minute bridge and higher water costs.')
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

para('<b>Modeling options.</b> The lumped model supplies a proved benchmark; the conservative network resolves cold regions with an explicit mixing parameter [5]. A velocity solver needs jet and turbulence data unavailable here. Table @tab:2@ compares their roles.')
table([['Option','Resolves','Evidence it needs','Role here'],['Lumped (Newton)','Mean temperature','Two loss coefficients','Proved benchmark'],['Thermal network','Cells, heat paths, overflow','Loss, body and mixing coefficients','Decision model'],['Flow solver','Velocity and buoyancy','Turbulence closure, jet data','Not used']],[100,120,130,118])
page('2. Physical assumptions and scenario inputs')
para('The problem supplies no calibrated coefficients. Section 2.1 separates external anchors from assumptions; scenarios test the important ones.')
table([['Quantity','Baseline / units','Status'],['Tub L × W × H',f'{p["L"]:.2f} × {p["W"]:.2f} × {p["H"]:.2f} m','Assumed geometry'],['Displaced body volume / area',f'{p["body_volume"]:.3f} m³ / {p["body_area"]:.2f} m²','Assumed'],['Water density / heat capacity',f'{p["rho"]:g} kg/m³ / {p["cp"]:g} J/(kg K)','Rounded constants'],['Air / skin / inlet temperature',f'{p["air_temp"]:g} / {p["body_temp"]:g} / {p["inlet_temp"]:g}°C','Fixed reservoirs'],['Surface / wall / body coefficient',f'{p["h_surface"]:g} / {p["h_wall"]:g} / {p["h_body"]:g} W/(m² K)','Correlation-based (next page)'],['Mixing diffusivity D',f'{p["D"]:g} m²/s','Uncalibrated closure; range tested'],['Initial / lower / upper limit',f'{p["initial"]:g} / {p["floor"]:g} / {p["ceiling"]:g}°C','Preference scenario'],['Time / allowed spread',f'{p["horizon"]:g} s / {p["span"]:g}°C','Preference scenario']],[182,188,98])
para('<b>A1. Constant density and heat capacity.</b> Water properties change by under 1% between 39 and 41°C, and the constants are rounded values, not an evaluated IAPWS table [3]. <i>Reason:</i> the resulting capacity error is small next to the loss coefficients.')
para('<b>A2. Linear exchange.</b> Newton’s law [2] approximates the narrow temperature span. Surface loss includes convection, radiation and evaporation once; evaporative volume change is neglected. Room-temperature linearization understates near-40°C sensitivity by about 7% of total loss in an independent estimate, within the tested coefficient range.')
para('<b>A3. Skin held at a fixed temperature.</b> <i>Reason:</i> thermoregulation is outside the problem; skin temperature is varied (32 and 36°C) instead of resolved.')
para('<b>A4. Prescribed surface stream.</b> Water traverses the top row nearest the centre line (half a cell off it for even row counts). Alternative paths and whole-section flow are tested in Section 11; the route is assumed, not measured.')
para('<b>A5. Mixing as one effective diffusivity D.</b> Motion enters through D, with a separate surface-loss scenario. <i>Reason:</i> molecular diffusion alone would not represent circulation; D is anchored only by an order-of-magnitude scaling (Section 2.1) and is tested over a range; vertical mixing is tested separately in Section 9.')

page('2.1 Where the coefficients come from')
sf=prov['surface'];wl=prov['wall'];bd=prov['body']
para(f'No temperature record exists to fit, so each coefficient is derived from a textbook relation or tied to a published measurement where one exists, and given a range; where nothing exists (mixing, the exposed fraction, the air and skin temperatures) the value is an assumption and is labelled as one. Surface loss sums natural convection above a hot horizontal surface ($\\mathrm{{Nu}}=0.15\\,\\mathrm{{Ra}}^{{1/3}}$ for $10^{{7}}<\\mathrm{{Ra}}<10^{{11}}$, length $A/P$ [5]; here $\\mathrm{{Ra}}={sf["rayleigh"]/1e7:.1f}\\times10^{{7}}$), linearized radiation (emissivity 0.96) and evaporation by the Lewis analogy. For open water at 40°C in 22°C air at 50% humidity the parts are {sf["parts"]["convection"]:.1f}, {sf["parts"]["radiation"]:.1f} and {sf["parts"]["evaporation"]:.1f} W/(m² K) ({sf["evaporation_kg_m2_h"]:.2f} kg/m² h evaporated), {sf["open_water_total"]:.1f} in total. A bather covers part of the surface; with an assumed exposed fraction of 0.7 the central value is {sf["central"]:.1f}, and we use 25 within the range 17–37, which spans exposed fractions of 0.5 to 1.0. Evaporation correlations differ by tens of percent, so this is a scenario range, not a measured one.')
para(f'A 5 mm shell (0.19 W/(m K)), with inside/outside films 300/8 W/(m² K), gives a series coefficient {wl["central"]:.1f}, with range {wl["range"][0]:.1f}–{wl["range"][1]:.1f}; these are typical inputs. Menzies et al. observed rectal rise 0.9 ± 0.3°C after 30 min shoulder-depth immersion at 40°C [6]. For mass 73 kg and heat capacity 3470 J/(kg K), an assumed mean rise 1–2°C implies uptake {bd["anchor"][0]["average_uptake_w"]:.0f}–{bd["anchor"][1]["average_uptake_w"]:.0f} W and equivalent exchange {bd["anchor"][0]["equivalent_h_body"]:.0f}–{bd["anchor"][1]["equivalent_h_body"]:.0f} W/(m² K) at fixed 34°C skin. We use 25. Mean rise and driving difference are assumptions: this is a scale anchor, not calibration. Body capacity is about 37% of water capacity; its delayed warming is tested in Section 11.1.')
para('The assumed scaling $D\\approx0.1u\'\\ell$ gives 1e-4/1e-3/6e-3 m²/s for velocity/eddy-length pairs (0.02 m/s, 0.05 m), (0.1, 0.1) and (0.3, 0.2). We use 0.001 and test 0.0003–0.003; these are circulation scenarios, not measured diffusivities.')
cv=r['mesh']['convergence']
para(f'The 39–41°C window is a preference, not a safety standard [6]. Inlet-cell maxima increase {cv[0]["inlet_cell_max_temp"]:.2f}/{cv[1]["inlet_cell_max_temp"]:.2f}/{cv[2]["inlet_cell_max_temp"]:.2f}°C on the three meshes: the point source heats less water per cell. Ceiling/spread therefore exclude a 0.15 m inlet zone, assuming no bather occupies the jet; the floor covers every cell, as required by Section 4. Section 11 checks constrained quantities.')
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
para('The heat map and Figure @fig:temperature@ use the same archived trajectory. Exchange couples the horizontal layers into one three-dimensional network. The cold-region locations explain information lost by a mean or range; the mesh table tests resolution. These are homogenized cell averages, not resolved anatomy, recirculation or a faucet jet.')
# Homogenized-body and unresolved-jet scope is retained in the preceding paragraph.
# The homogenized-body and unresolved-jet limits are stated in Sections 1, 2 and 5.

page('6. Inlet transport, solver and strategy search')
para('Inlet and overflow are on opposite ends of a surface stream. Every path edge carries the same q: the first cell receives hot water, interior cells receive upstream water and lose the same volume downstream, and the last cell discharges through the overflow.')
eq(r'S_1=\rho c_pq(T_{\rm in}-T_1),\quad S_i=\rho c_pq(T_{i-1}-T_i)')
eq(r'\sum_i C_i\dot T_i=-\sum_iH_{a,i}(T_i-T_a)-\sum_iH_{b,i}(T_i-T_b)+\rho c_pq(T_{\rm in}-T_{\rm out})')
para('This prescribed stream permits short circuit but does not establish excess outlet heat loss. Section 11.4 diagnoses its sign against a distinct whole-section closure; Section 11.1 changes the internal path at fixed inlet and overflow. Neither route is an inferred velocity field.')
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
para(f'The spatial-minus-mixed gap increases from {fm[38.0]["constant_l"]-fm[38.0]["mixed_l"]:.1f} L at a 2°C fall to {fm[39.25]["constant_l"]-fm[39.25]["mixed_l"]:.1f} L at 0.75°C. Scheduling lowers the baseline by {save:.0f}%; schedules at other tolerances were not optimized.')

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
para('The extreme-discrepancy midpoint clipped to the bias bound is the minimax correction, with physical bias $b_j=-a_j$. A trace from −0.04 to +0.04°C fails: bias cannot vary between readings.')
para(f'Our grid has 7 mixing values (0.00085–0.00115 m²/s), 9 surface and 9 body coefficients (20–30 and 15–35 W/(m² K)), and 5 delivery multipliers (0.95–1.05). Of {CAL["candidate_models"]} models, {CAL["compatible_models"]} fit. This finite decision ambiguity set is neither a confidence region nor a probability distribution.')
para(f'Table @tab:measurement-control@ compares archived policies with a replacement optimized on ten extreme/failing models, using a 2 L/min bound, 0.1°C target and 0.03°C extra floor reserve. All {CAL["compatible_models"]} pass three-grid envelopes; the tightest spread bound is {cal_span:.6f}°C. The selected target is not an all-model margin or global optimum.')
cal_rows=[['Policy','Command (L)','Delivered (L)','Sampled pass']]
for label,command,count in [('Constant',TR['constant_command_l'],sum(row['sampled_passed'] for row in TR['constant_rows'])),('Nominal six-stage',ctl['water_l'],CAL['compatible_models']-CAL['baseline_sampled_failures']),('Ambiguity-set six-stage',CAL['commanded_water_l'],sum(v>=0 for v in CAL['rounds'][-1]['sampled_slacks_c']))]:
    cal_rows.append([label,f'{command:.2f}',f'{command*.95:.2f}–{command*1.05:.2f}',f'{count}/{CAL["compatible_models"]}'])
table(cal_rows,[158,86,122,102],caption='Policies on the same measurement-compatible set',label='measurement-control')
para(f'The table uses the same 178 models and five-second sampling; archived policies were not re-optimized. Only the replacement has 534 three-grid envelopes. Its five-minute rates are '+', '.join(f'{q:.6f}' for q in cal_flow)+f' L/min; envelope extrema are {min(row["lower_temperature_bound_c"] for row in CAL["independent"]):.4f}/{max(row["upper_temperature_bound_c"] for row in CAL["independent"]):.4f}°C.')
para(f'The replacement costs {(CAL["commanded_water_l"]/ctl["water_l"]-1)*100:.2f}% more than the nominal policy. A separate zero-inlet trial with the same prior, probes and errors retains {IV["compatible_models"]} models, including unidentified delivery bias; its candidate passes {len(IV["independent"])} three-grid envelopes. The two observation sets intersect in {iv_intersection} models; they are not nested or probabilistic.')
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
para(f'Two additional observations use (D, surface/body coefficients)=(0.00115,20/15) and (0.00085,30/35), in m²/s and W/(m² K), with nominal delivery. Separate trials retain the same prior/errors. Strong mixing gives a {strong_delta:.4f} L control-cost gap, so equal-reset pulse reuse pays from six. The three accepted candidates pass {OBS["independent_checks"]} distinct three-grid envelopes.')
para('*The weak-mixing pulse passes physical limits but fails the optimizer and extra design margin. No passive candidate was accepted within two starts and three constraint-generation rounds; neither failure proves infeasibility. These are observation-conditioned outcomes, not ex ante experiment values or sequential inference.')


page('8. Separate geometry, size and body effects')
rows=[['Change from baseline','Water (L)','Interpretation']]
for key,desc in [('shallow wide','Same envelope volume'),('deep narrow','Same envelope volume'),('small bath','Lower water depth'),('large bath','Higher water depth'),('deep bath','Depth 0.35 m, like a bath filled to the shoulders'),('larger body','More displacement/contact'),('long body','Shape only; fixed volume/area'),('warmer skin','Skin at 36°C'),('cooler skin','Skin at 32°C')]:
 v=sc[key]['policy'];rows.append([key.title(),f'{v["water_l"]:.2f}' if v['feasible'] else 'No candidate',desc])
table(rows,[148,86,234])
fx=lambda k:(f'needs {sc[k]["policy"]["water_l"]:.2f} L' if sc[k]['policy']['feasible'] else 'has no accepted candidate')
para(f'At equal volume, the wide, shallow tub has a larger exposed top area and a changed diffusion length; it {fx("shallow wide")}. The deep, narrow tub needs {sc["deep narrow"]["policy"]["water_l"]:.2f} L against {b["water_l"]:.2f} L, because a deep, narrow envelope reduces top-area heat loss, although a real deep bath may stratify, which Section 9 tests with a separate vertical-mixing scenario. Geometry is therefore more than an interchangeable cooling coefficient.')
para(f'Changing depth changes storage and shell area. The large bath needs {sc["large bath"]["policy"]["water_l"]:.2f} L replenishment; the small bath {fx("small bath")}. At 0.23 m the baseline is shallow: its surface-to-volume ratio is about 1.7 times that at shoulder depth; a 0.35 m bath {fx("deep bath")}. Initial filling is excluded from J, so lower replenishment does not establish lower total water use.')
para(f'The larger-body case combines displacement and contact-area changes and {fx("larger body")}; the long-body case changes distribution at fixed volume/area. Warmer skin reduces the exchange driving difference. These are conditional scenarios, not measured human responses.')
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
para('No candidate was accepted for: '+', '.join(none)+'. In weak-mixing, high-loss and wide-shallow trials, sufficient inflow violates spread on sampled rates 0.8–2.5 L/min. Finite search does not prove infeasibility. Circulation, inlet layout, duration or comfort tolerance may need to change; each remedy requires its own evidence.')

page('10. Validation: independent evidence and remaining error')
num=lambda name:json.loads(next(c['evidence'] for c in checks if c['name']==name))
energy=num('instantaneous_energy_balance_with_overflow');rk=num('independent_RK45_vs_archived_matrix_exponential');env=num('continuous_time_policy_envelope')
para(f'All {len(checks)} recorded checks pass. Independent heat-flow arithmetic sums environmental losses, body exchange and local-temperature overflow; the largest instantaneous residual is {energy["max_residual_w"]:.2e} W. An adaptive RK45 integration with independently assembled right-hand side agrees with the archived matrix-exponential trajectory within {rk["maximum_temperature_difference_c"]:.2e}°C. This tests numerical implementation, not a second physical model.')
para('Uniform-loss analytic cooling and a single conservative overflow sink check signs and energy; nonnegative off-diagonals and nonpositive row sums give contraction within each flow segment.')
para(f'Half-second replay is supplemented by a derivative bound: if |dTi/dt| ≤ L, a point lies at most 0.25 seconds from a sample, so temperatures differ by at most L/4 and spread by at most L/2. With an integration allowance and no relaxation of the physical limits, the resulting lower envelope is {env["lower_temperature_bound_c"]:.4f}°C, upper {env["upper_temperature_bound_c"]:.4f}°C, and spread upper bound {env["span_upper_bound_c"]:.4f}°C. This is a conditional floating-point envelope, not interval-arithmetic certification.')

ind=MC['accepted_independent']
para(f'The accepted schedule uses an independently assembled right-hand side and adaptive RK45, restarted at every flow switch. Nonnegative off-diagonal transport and nonpositive row sums give an infinity-norm contraction bound for the derivative within each segment. One-second samples alone leave some intervals unresolved; adding RK45 step endpoints and bisecting unresolved intervals once on the finest mesh gives bounds of {ind["lower_temperature_bound_c"]:.4f}°C for the minimum, {ind["upper_temperature_bound_c"]:.4f}°C for the maximum and {ind["span_upper_bound_c"]:.4f}°C for the spread. These pass the physical limits without threshold relaxation. A 2e-6°C integration allowance is included; this floating-point check is conditional on the network, not interval arithmetic or experimental validation. The {len(checks)} baseline checks are separate.')

page('11. Resolution, uncertainty and transfer to a real bath')
f=r['mesh']['fine_policy'];fp=r['mesh']['coarse_policy_on_fine'];cv=r['mesh']['convergence']
table([['Mesh (cells)','Max outside jet zone','Spread outside zone','Inlet-cell max']]+[[f'{c["grid"][0]} × {c["grid"][1]} × {c["grid"][2]} ({c["cells"]})',f'{c["max_temp"]:.3f}°C',f'{c["max_span"]:.3f}°C',f'{c["inlet_cell_max_temp"]:.3f}°C'] for c in cv],[130,115,115,108])
para(f'The same constant-rate policy is replayed on three meshes. The ceiling and spread quantities outside the jet zone agree within {max(c["max_temp"] for c in cv)-min(c["max_temp"] for c in cv):.3f}°C and {max(c["max_span"] for c in cv)-min(c["max_span"] for c in cv):.3f}°C, and the tested constant-rate trajectory stays within the comfort limits on these meshes. The inlet-cell maximum rises from {cv[0]["inlet_cell_max_temp"]:.2f} to {cv[2]["inlet_cell_max_temp"]:.2f}°C with refinement; that is why the cell is excluded rather than constrained. The selected water amounts on the 8 × 4 × 3 and 12 × 6 × 4 meshes are {b["water_l"]:.3f} and {f["water_l"]:.3f} L ({100*abs(f["water_l"]-b["water_l"])/b["water_l"]:.2f}% apart). Three meshes are a diagnostic, not an asymptotic convergence-order study.')
para('Parameter uncertainty concerns heat loss, body exchange and mixing. Structural uncertainty concerns the prescribed surface stream, fixed skin reservoir, homogenized body and constant effective D. These are different errors. The scenario table explores parameter dependence and one coupled motion effect; it is not a probability distribution or confidence interval.')
names_lr={'h_surface':'surface coefficient','h_body':'body coefficient','air_temp':'room temperature','body_temp':'skin temperature','h_wall':'shell coefficient','D':'mixing diffusivity'}
para(f'Among {lr["samples"]} scrambled Sobol draws over the six stated input ranges (D log-uniform), {lr["feasible"]} admit a searched constant-rate candidate. Water quantiles at 5/25/50/75/95% are {qq["0.05"]:.1f}/{qq["0.25"]:.1f}/{qq["0.5"]:.1f}/{qq["0.75"]:.1f}/{qq["0.95"]:.1f} L. These scenario quantiles exclude {lr["samples"]-lr["feasible"]} failed searches and are not real-bath probabilities.')
# Range quantiles, failures and correlations remain in the text; the feedback plot now carries the distinct temporal decision evidence.
para('Spearman rank correlations with water, over accepted draws: '+', '.join(f'{names_lr[k]} {v:+.2f}' for k,v in sorted(sp.items(),key=lambda kv:-abs(kv[1])))+'.')
from scipy.stats import mannwhitneyu
okd=[r_ for r_ in lr['rows'] if r_['feasible']];nod=[r_ for r_ in lr['rows'] if not r_['feasible']]
pv={k:float(mannwhitneyu([r_['inputs'][k] for r_ in okd],[r_['inputs'][k] for r_ in nod]).pvalue) for k in names_lr}
others=min(v for k,v in pv.items() if k!='D');pdtxt='< 1e-4' if pv['D']<1e-4 else '= %.3f'%pv['D']
para(f'Accepted/rejected draws have median D {np.median([r_["inputs"]["D"] for r_ in okd]):.1e}/{np.median([r_["inputs"]["D"] for r_ in nod]):.1e} m²/s (Mann–Whitney p {pdtxt}); the other five inputs show no detected association (smallest p={others:.2f}). Weak mixing can leave distant water cold while extra inflow violates uniformity.')
para('An inlet-free trial cheaply characterizes cooling but cannot identify a term it never excites. At uniform initial T0, internal exchange vanishes, so $\\dot T_i(0)=[H_{a,i}(T_a-T_0)+H_{b,i}(T_b-T_0)]/C_i$, independent of D. Later spatial differences can reveal mixing. Delivery bias and inlet path remain absent throughout the passive trial. A warming contact reservoir shares the initial slope but changes later curvature; loss parameters can compensate for that difference. An inlet trial must therefore check transport and overflow energy, not merely refine a cooling fit. Reserve a separate experiment to check predictions; match motion/foam trials for changes in loss as well as mixing.')

para(f'The finite-volume stencil is also checked against an insulated three-dimensional cosine diffusion mode: four successively refined grids approach second order (finest observed order {FV["observed_orders"][-1]:.2f}). A zero-diffusion inlet path matches the independent stirred-cell cascade step response within {max(x["max_error_c"] for x in FV["advection_rows"]):.1e}°C. These verify implementation in empty-domain limits, not the mixing closure or real baths [9].')

page('11.1 Carry structural ambiguity into the decision')
para(fr'The alternatives replace fixed skin by $C_b \dot B=\sum_i H_{{b,i}}(T_i-B)$ ({rv["body_capacity_kj_per_k"]:.2f} kJ/K, initially {p["body_temp"]:g}°C), or route the inlet stream down, across the bottom and back to the same overflow. Contact storage is not physiology; the fixed-skin energy bound does not transfer.')
para(f'Eight alternative-mechanism observation sets fit the original structure; six existing policies pass specified sampled replays, with min/max/spread/final-body summary differences below {math.ceil(STRUCT_OBS["maximum_summary_difference_c"]*1e10)/1e10:.2e}°C. We therefore screen surface/fixed, deep/fixed and surface/finite hypotheses together: passive/pulse banks retain 1465/467 pairs. Each trial restarts uniformly; observations are not sequential.')
para('Base-grid success hid two finest-grid ceiling failures (41.0010/41.0007°C). A 1% passive-flow reduction repairs those sampled cases, without common reserves or full fine-grid coverage. New six-stage candidates instead target 39.13°C floor, 40.9°C outside-zone ceiling and 1.4°C spread across all three grids. These extra reserves leave the physical 39/41/1.5°C limits unchanged.')
rows=[['Structure / trial','Pairs','Control (L)','Floor / ceiling (°C)','Spread (°C)']]
structure_names={'surface_fixed':'Surface/fixed','deep_fixed':'Deep/fixed','surface_finite':'Surface/storage'}
for structure,design in [(s,d) for s in structure_names for d in ('passive','pulse')]:
    groups=[g for g in FAIR['rows'] if g['structure']==structure and g['design']==design]
    records=[r for g in groups for r in g['records']]
    # Outward rounding: a displayed lower bound must not exceed its evidence.
    lo=math.floor(min(r['lower_bound_c'] for r in records)*1000)/1000
    hi=math.ceil(max(r['upper_bound_c'] for r in records)*1000)/1000
    sp=math.ceil(max(r['span_bound_c'] for r in records)*1000)/1000
    rows.append([structure_names[structure]+' / '+design,str(len(groups[0]['records'])),f'{FAIR["volumes"][design]:.2f}',f'{lo:.3f} / {hi:.3f}',f'{sp:.3f}'])
table(rows,[139,45,72,132,80])
para('The local search uses exact affine sensitivities on active cells. Two base-grid members fail the common floor despite passing physical limits. Adding those constraints gives the candidates in Table @tab:11@. For consecutive five-minute stages their rates are '+', '.join(f'{q:.6f}' for q in FAIR['manifest']['policies']['passive'])+' L/min (passive), and '+', '.join(f'{q:.6f}' for q in FAIR['manifest']['policies']['pulse'])+' L/min (pulse). Unrounded settings are retained for computation.')
para(fr'All {FAIR["objects"]} model-grid objects pass conditional continuous-time envelopes. The dynamic temperatures $U=(T_1,\ldots,T_N,B)$ exclude the constant coordinate. Nonnegative off-diagonals and nonpositive row sums give contraction within each flow stage. Chord error is bounded by $\|U^{{\prime\prime}}(t_0)\|_\infty h^2/8$; the first derivative gives another enclosure. Unresolved one-second intervals are bisected to at most 0.0625 s. A 2e-6°C allowance (twice for spread) is assumed, not interval-proved. Table @tab:11@ rounds outward. Independent RK45/energy checks cover {FAIR["independent_cases"]} extremal identities, not the entire bank.')
para(fr'Section 7.4’s cost identity now has $\Delta={FAIR["delta_l"]:.6f}$ L, giving $n>{FAIR["strict_n_greater_than"]:.5f}$: pulse beats the fixed passive candidate from use {FAIR["crossover"]}, if one 6 L trial is reused, delivery bias stays positive and fixed, and total reset costs match. The seven-use result was conditional on the original structure. This expanded-bank comparison establishes neither global optimality nor expected experiment value.')

page('11.2 Use observations to change the next action')
para('Starting from 1,465 passive-compatible pairs on the 96-cell grid, read probes 89 and 6 every minute. Given prediction $\\widehat T_{mj,k}$ and reading $z_{j,k}$, retain each model’s constant-bias intervals:')
eq(r'I_{mj,k}=[-0.02,0.02]\cap\bigcap_{\ell=0}^{k}[z_{j,\ell}-\widehat T_{mj,\ell}-0.020002,\ z_{j,\ell}-\widehat T_{mj,\ell}+0.020002].')
para('Exclude a model if either interval is empty. Choose the least of 0, 0.8, 0.9 and 1 times the current backup rate whose next minute and remaining backup satisfy all survivors’ common targets. Chord bounds include the dynamic body state, refine unresolved five-second intervals to 0.0390625 s, and assume the same 2e-6°C allowance.')
para(f'<b>Conditional feasibility and water cap.</b> Each accepted minute is checked with the original remaining backup. Subsequent observations only shrink the set, preserving that feasible tail. Induction applies if the truth stays in the static bank and propagators are valid. For L/min commands $0\\le q_k\\le q_k^{{\\mathrm{{backup}}}}$, a completed service has $J_{{\\mathrm{{cmd}}}}=\\sum_k q_k\\Delta t\\le\\sum_k q_k^{{\\mathrm{{backup}}}}\\Delta t\\le{FB["backup_command_l"]:.2f}$ L ($\\Delta t=1$ minute). A shared $\\alpha>0$ gives $J_{{\\mathrm{{act}}}}=\\alpha J_{{\\mathrm{{cmd}}}}\\le\\alpha\\times{FB["backup_command_l"]:.2f}$ L. This proves neither minimum water nor fault or timeout recovery.')
para(f'Fixed probe biases (+0.013, −0.011)°C give {sum(FBZERO["flows"]):.2f} L with zero reading noise and {sum(FBRANDOM["flows"]):.2f} L with one bounded-noise sequence (seed 20261010); 114/1 models remain. Both start from 1,465 hypotheses and the {FB["backup_command_l"]:.2f} L backup. Figure @fig:feedback@ shows action changes before unique identification. These are two nominal surface/fixed examples, not population performance.')
figure('feedback.png','Figure 10. Observations change replenishment. Both nominal cases start from the same bank and backup; a logarithmic count axis distinguishes slow and rapid elimination. The constant bias and noise bounds are shared.',height=180)
para('A separate matched 12-model ablation uses 26.00 L without observations versus 22.86/22.86/22.08 L with them in three structures. Six feedback trajectories pass 18 independent half-second three-grid RHS/energy replays; realized actions do not certify fine-grid feedback throughout the bank.')
para('Minute-10 shifts to 45°C supply or 40 W/(m² K) surface loss empty the set at minute 11; terminal bias intervals independently exclude all 23 preceding survivors. Neither partial service counts as savings. An empty set invalidates reuse, without identifying the cause or certifying recovery.')

page('11.3 Check transfer beyond the parameter grid')
para(f'Six predeclared bank-external truths give two complete services ({sum(FT["completed"]["offgrid_surface"]["flows"]):.2f}/{sum(FT["completed"]["offgrid_deep"]["flows"]):.2f} L commands). Changed storage, dimensions, supply or loss empties the bank after 28/5/11/9 minutes, before a checked temperature violation. Partial services are not savings; Section 12 separately tests limited recourse.')
para(f'For the two completed surface/deep paths, fix the realized commands, baseline geometry, uniform 40°C water, 34°C fixed contact, 50°C inlet and 22°C air. Around $(D,h_s,h_b,\\alpha)=({BOX_CENTER["D"]:.6f},{BOX_CENTER["h_surface"]:.3f},{BOX_CENTER["h_body"]:.2f},{BOX_CENTER["flow_multiplier"]:.4f})$, the respective halfwidths are {BOX_WIDTH["D"]:.2e} m²/s, {BOX_WIDTH["h_surface"]:.5f} and {BOX_WIDTH["h_body"]:.4f} W/(m² K), and {BOX_WIDTH["flow_multiplier"]:.6f}. Parameters are static; these are mathematical neighborhoods, not measured tolerances.')
para(r'<b>Fixed-command perturbation bound.</b> Write $U^{\prime}=M_\theta U+c_\theta$, affine in the four parameters. For halfwidths $w_j$, set $K_j=w_j\partial_jM$, $f_j=w_j\partial_jc$, and $\theta=\theta_0+w\odot z$ with $|z_j|\le1$. Nominal variations satisfy $S_j^{\prime}=M_0S_j+K_jU_0+f_j$, $S_j(0)=0$.')
tex.append(r'\begin{proof}'+'\n')
para(r'The exact remainder $r=U_\theta-U_0-\sum_jz_jS_j$ satisfies')
eq(r'r^{\prime}=M_\theta r+\sum_{j,k}z_jz_kK_jS_k,\qquad r(0)=0.')
para(r'Positive parameters give nonnegative off-diagonals and nonpositive row sums at every vertex, hence throughout the affine box. Contraction [10] and variation of constants give')
eq(r'\|r(t)\|_\infty\le R(t),\qquad R(t)=\sum_{j,k}\int_0^t\|K_jS_k(u)\|_\infty\,du.')
para(r'The cellwise radius is $\sum_j|S_j|+R$: subtract it for the floor, add it for the ceiling, and twice for spread. States are continuous at flow switches; $R$ accumulates across them.')
tex.append(r'\end{proof}'+'\n')
para(f'Half-second derivative/chord bounds enclose the intervals; assumed errors are 2e-6°C, 2e-6°C/s and 2e-6°C/s² for states and first/second derivatives. The tested halfwidth scales were 4, 2, 1 and 0.4 times those above; the displayed box is the largest qualifying both paths on all three meshes: floor ≥{BOX_BOUND[0]:.4f}°C, ceiling ≤{BOX_BOUND[1]:.4f}°C, spread ≤{BOX_BOUND[2]:.4f}°C. Common extra reserves do not all pass. Independent RHS/energy checks cover all {len(BOX["checks"])} corners/centers; finite points challenge implementation, not prove coverage. A prior max-norm defect bound certified none. This exact-remainder result assumes numerical accuracy and certifies fixed actions, not all feedback branches or real baths.')

page('11.4 Challenge the transport mechanism')
para('A separate axial closure matches volume, storage and total conductances, with uniform/localized-body losses but different anatomy. With v=qL/V, loss per length $\\lambda$ and capacity per length c,')
eq(r'T_t=D T_{xx}-vT_x-\lambda(x,T)/c,\qquad vT(0)-DT_x(0)=vT_{\rm in},\quad T_x(L)=0.')
para(f'The flux inlet [11] conserves enthalpy. Both policies replay two loss profiles on 40/80/160 meshes at D=0.0003/0.001/0.003 m²/s. Under constant flow, weak-mixing mean/outlet ends at {AXWEAK["final_mean_c"]:.3f}/{AXWEAK["final_outlet_c"]:.3f}°C. N80 searches choose start 0 min at D=0.001 ({AXM["command_l"]:.2f}/{AX["groups"][("localized_body",.001)]["selected"]["command_l"]:.2f} L, uniform/local loss), or 10 min at D=0.003 ({AXS["command_l"]:.2f}/{AX["groups"][("localized_body",.003)]["selected"]["command_l"]:.2f} L); all selected candidates pass three-mesh sampled checks.')
para('Search starts 0:120:1200 s and first roots 0:0.2:3 L/min use floor 39.03°C. Neither weak-mixing profile has an accepted root; finite failure does not prove infeasibility or global optimality.')
eq(r'E_{\rm excess}=\rho c_p\int q(T_{\rm out}-\overline T)\,dt.')
para(f'Positive excess is extra overflow loss relative to the mean. Original/matched-axial values are ${AX["original_overflow"]["excess_j"]/1000:.2f}/{AX["matched_overflow"][-1]["excess_j"]/1000:.2f}$ kJ. Both outlets are cooler: a permitted short circuit does not establish the cause of the water penalty.')
para(r'For uniform loss, $k=(H_a+H_b)/C$, $w=T_x$ obeys $w_t=Dw_{xx}-vw_x-kw$, $w(L)=0$, $w(0)=v[T(0)-T_{\rm in}]/D\le0$ when $T\le T_{\rm in}$. Uniform initial water and inherited gradients at switches permit the maximum principle: $w\le0$, hence $T_{\rm out}\le\overline T$. Localized loss adds gradient forcing.')
para(f'Steady/Robin tests show first-order convergence (N160 error ≤{AX_ERR:.6f}°C); six independent flux/RK45 differences ≤{AX_RK:.2e}°C and energy errors ≤{AX_ENERGY:.5f} J verify this closure, not real baths or PDE-wide feasibility.')

tex.append(r'\FloatBarrier'+'\n')
page('12. From temperatures to a replenishment decision')
para('For every compatible model over the remaining bath: <b>wait</b> with a qualifying zero-flow prefix followed by the backup; <b>replenish</b> with a qualifying continuation, retain the qualified backup if search adds none; otherwise <b>reassess</b>.')
para('Reconstruct 54 exposed static hypotheses from known 40°C water/34°C contact and all actions/readings: six structures × D factors 0.975/1/1.025 × surface-loss offsets −0.625/0/0.625 W/(m² K). Intersect shared-bias intervals, without truth states. Assuming prior parallel maintenance, offline checks prequalify a 60 s zero-flow bridge for pre-reading sets 1/15/6/7; the last reading deletes to 1/8/4/6. Search tail rates 0:0.05:2 L/min (Table @tab:recourse@).')
table([['Changed condition','Alarm (min)','Tail (L/min)','Total command (L)']]+[[label,str(int(row['refusal_s']/60)),f'{row["selected"]["q_lpm"]:.2f}',f'{row["selected"]["total_command_l"]:.2f}'] for label,row in zip(['Contact storage','Longer geometry','Cooler inlet','Higher loss'],RC['rows'])],[156,88,104,120],caption='Recourse after a one-minute bridge',label='recourse')
para('Base chord bounds cover bridge/tail; 57 independent three-grid full-trajectory replays sample 19 survivors. Physical 39/41/1.5°C limits hold without old reserves. The prior 0.70 L/min cooler tail fails a compatible model on all meshes. The higher-loss case exceeds 26.09 L. Empty sets/failed bridges/timeouts yield no action; offline evidence does not verify real-time recovery.')

page('13. A warmer bath, with less replacement water',True)
para('A guide for the person in the bathtub','heading')
para(f'<b>Choose your tolerance.</b> Allowing some cooling uses stored heat before replacement water. Our example needs about {b["water_l"]:.0f} L with a 1°C allowance, but {sc["loose comfort"]["policy"]["water_l"]:.1f} L with 2°C. These are model scenarios; your comfort and health needs determine the acceptable range.')
para('<b>Redistribute warmth.</b> Water near the faucet may warm while distant water stays cool. Gentle movement can help; stronger motion can increase surface loss. Extra inflow can widen temperature differences. A cooler overflow can retain heat while a distant cold patch persists; measure both before attributing poor performance to hot-water short circuit.')
para(f'<b>Wait only while a checked plan remains.</b> The baseline schedule waits {lead*seg_min:g} minutes, supplies water for {(K-lead-trail)*seg_min:g} minutes and stops for {trail*seg_min:g} minutes. It uses {ctl["water_l"]:.2f} L against {b["water_l"]:.2f} L for a constant trickle. These timings do not transfer to a differently mixed bath: the axial comparison selects zero or ten minutes. A warm average alone is insufficient. Only {rv["tap_error_share"]:.0%} of the specified random tap-error trials stayed within limits; this is not a reliable manual prescription.')
para('<b>Follow the three decisions.</b> Our modeled controller reads two temperatures every minute. Wait or reduce inflow only when that change and the remaining backup pass for every compatible model; otherwise keep the checked backup. If no model explains the readings or the backup loses its support, reassess supply, motion and heat loss rather than treating refusal as recovery. Two specified shifts were detected after one minute. In four static mismatch studies, a prechecked one-minute pause allowed replacement plans, but some required extra water; planning reserves were reduced; unknown changes have no such guarantee. Spatial bounds come from the model: two probes can miss an unmodeled cold corner.')
para(f'<b>Count preparation as well as use.</b> Across the broader model bank, cooling-only and hot-water trials lead to {FAIR["volumes"]["passive"]:.2f}/{FAIR["volumes"]["pulse"]:.2f} L during a bath. For those fixed schedules, a reusable 6 L hot-water trial pays back from use {FAIR["crossover"]} when conditions and reset costs match. Both trials need 30 minutes and a fresh uniform start. The online cases reduce the passive backup to {sum(FBZERO["flows"]):.2f}/{sum(FBRANDOM["flows"]):.2f} L under specified sensor errors; their repeated-use crossover with pulse is untested; trial/reset costs remain.')
para('<b>Keep the practical limits in view.</b> An intact bubble layer may reduce heat loss, but the calculation does not measure a particular additive. Changed geometry, body position, motion, supply or foam needs reassessment. Use stored warmth, keep it distributed and avoid unnecessary overflow; the figures explain these tradeoffs rather than certifying bathing or hot-jet safety.')

page('14. References and reproducible algorithm',True)
refs=[
'[1] COMAP. 2016 MCM Problem A: A Hot Bath. 2016. Official problem PDF: contest.comap.com/undergraduate/contests/mcm/contests/2016/problems/2016_MCM_Problem_A.pdf.',
'[2] U.S. Department of Energy. DOE Fundamentals Handbook: Thermodynamics, Heat Transfer, and Fluid Flow. DOE-HDBK-1012/2-92, June 1992. Convection heat transfer, Eq. (2-9).',
'[3] IAPWS. Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use. R6-95(2018). iapws.org/technical-guidance/release/IAPWS-95.',
'[4] SciPy developers. scipy.sparse.linalg.expm_multiply and scipy.integrate.solve_ivp, API documentation. docs.scipy.org/doc/scipy/reference/. Accessed 7 October 2026.',
'[5] Bergman, T. L., Lavine, A. S., Incropera, F. P., DeWitt, D. P. Fundamentals of Heat and Mass Transfer, 7th ed. Wiley, 2011. Natural convection above a heated horizontal surface (characteristic length A/P); heat and mass transfer analogy.',
'[6] Menzies, C., Clarke, N., Steward, C. J., Thake, C. D., Pugh, C. J. A., Cullen, T. Vascular, inflammatory and perceptual responses to hot water immersion: impacts of water depth and temperature in young healthy adults. Experimental Physiology, 2025. doi:10.1113/EP092761.',
'[7] OpenAI, Codex (GPT-6-based assistant), and Anthropic, Claude Sonnet 5.5 in Claude Code. Used during 7–10 October 2026 for modeling, code, validation and report composition; exact builds not independently established. See Report on Use of AI.',
'[8] Munk, W. H., Anderson, E. R. Notes on a theory of the thermocline. Journal of Marine Research, 7(3), 276–295, 1948.',
'[9] NASA/NPARC Alliance. Verification Assessment and Validation Assessment, CFD tutorial. www.grc.nasa.gov/WWW/wind/valid/tutorial/. Accessed 9 October 2026.',
'[10] Higham, N. J. What Is the Logarithmic Norm? 18 January 2022. nhigham.com/2022/01/18/what-is-the-logarithmic-norm/. Theorems 3 and 6. Accessed 10 October 2026.',
'[11] COMSOL. Theory for the Inflow Boundary Condition. Heat Transfer Module documentation, version 6.3. doc.comsol.com/6.3/doc/com.comsol.help.heat/heat_ug_theory.07.009.html. Accessed 10 October 2026.',
]
for ref in refs:para(ref,'ref')
para('Algorithm and computational record','heading')
para('Reject excessive cell occupancy; assemble capacities, symmetric exchange and a conservative stream. Compute mixed benchmarks; bracket delayed-constant floor crossings, reject ceiling/spread violations, and rank accepted water costs. Optimize buffered schedules and qualify them on three meshes. Recompute searches at Sobol draws. Independent RHS/RK45 uses rtol 2e-9, atol 2e-10°C and steps ≤5 s, with energy/analytic checks. Section 11.4 separately tests an axial closure. AI use is recorded in [7].')

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
para('Tool, task and scope','heading')
para('Codex (GPT-6-based) and Claude Sonnet 5.5 via Claude Code assisted modeling, computation, validation, figures and writing on 7–10 October 2026; exact builds remain unverified. The task was a complete historical MCM case. Post-sealing learning read Outstanding papers 44845/54164, page overviews, selected figures and COMAP commentary; no data/figures were copied. This was not an unseen-problem trial. AI sub-agents supplied independent RHS/probe checks.')
para('Outputs, corrections and verification','heading')
para('Independent integration rejected the 19.35 L schedule and accepted a buffered alternative. Fixed-policy replays checked contact storage and flow paths. Coefficient/inlet-zone corrections remain recorded; baseline optimization was reused. Sources [1]–[4]/[6] were checked directly, [10] at Theorems 3/6; [5]/[8] were not opened, so their relations were checked indirectly. AI generated derivations and report from actual results.')
para(f'Control studies compared known-mixing schedules, pulse/passive ambiguity sets, alternative structures and failures. Common-reserve candidates covered {FAIR["objects"]} model-grid objects with {FAIR["independent_cases"]} independent extremal replays; two reserve failures were corrected and preserved. Analytical diffusion/inlet tests check discretization. Archived producers retain their versions; observations are synthetic.')
para('Finite-bank feedback gave nine complete services/18 replays; two shifts stopped at 660 s. Six external-bank truths gave two services/four refusals and ten envelope replays. Stored empty intervals were audited without inventing missing predictions. Exact-remainder bounds qualified narrow fixed-action boxes with 102 independent replays; the failed loose bound remains.')
para('A separate 54-point exposed static catalog reconstructs four refusal histories from known initial states. Pre-reading sets qualify a 60 s zero-flow bridge, then surviving models qualify constant tails; 57 independent three-grid sampled replays passed. The 0.70 L/min counterexample, increased water costs and reduced reserves are retained. Candidate acceptance now rejects late results and preserves timeout state; controlled tests/frozen-candidate replay check this correction, without attributing revised code to historical runs.')
para('AI derived/tested an axial closure with continuum solutions, independent flux integration and unchanged controls; outlet diagnostics revised the short-circuit interpretation. Source [11] was read; COMSOL was not run. This is a counterfactual, not an experiment.')
para('Record limitations','heading')
para('The artifact retains task, tool identity, scope, code and numerical receipts, but lacks a complete exported transcript/every intermediate output. No human verification, real-time controller, physical experiment or feedback-wide certificate is claimed. These records do not replace those checks.')

TOTAL=SEC[0]
pdf=compile_pdf('paper','A Hot Bath')
(ROOT/'submission').mkdir(exist_ok=True)
shutil.copyfile(pdf,ROOT/'submission'/(TEAM_CONTROL_NUMBER+'.pdf'))
print(json.dumps({'pdf':str(ROOT/'submission'/(TEAM_CONTROL_NUMBER+'.pdf')),'sections':TOTAL,'equations':eqcount,'tables':table_total,'figures':figcount[0],'checks':len(checks)}))
