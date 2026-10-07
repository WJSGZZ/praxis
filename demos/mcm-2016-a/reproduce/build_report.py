"""Professional single-file MCM report; numerical evidence is supplied, never invented."""
import argparse,json,math,re,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
import model,control
TEAM_CONTROL_NUMBER='7391856'
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);args=parser.parse_args()
r=json.loads((args.run/'results.json').read_text());checks=json.loads((args.run/'checks.json').read_text())
assert all(c['passed'] for c in checks)
p=r['parameters'];b=r['policy'];a=r['analytic'];sc=r['scenarios'];z=np.load(args.run/'trajectory.npz')
E=json.loads((args.run/'extended.json').read_text());wf=lambda floor:next(f_['constant_l'] for f_ in E['frontier'] if f_['floor']==floor);ctl=E['control']['best'];prov=E['provenance'];lr=E['literature_ranges'];ctl_checks=E['checks']
assert all(c['passed'] for c in ctl_checks)
save=100*(1-ctl['water_l']/b['water_l']);qq=lr['water_quantiles_l'];sp=lr['spearman_with_water']
ct=E['control']['runs']
ROOT.joinpath('submission').mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT.parents[2]))
import subprocess,shutil
from scripts import texplot
escape=lambda s:s
tex=[];eqcount=0;tabcount=0;SEC=[0]
CAPS=['Where each requirement is answered','Modeling options compared','Baseline inputs','Coefficient anchors and the values used','Symbols',
 'Baseline result under the best constant rate','Constant rate, scheduled flow and the bounds','Geometry, size and body scenarios',
 'Mixing, surface, comfort and supply scenarios','Mesh and time-step replay','Scenario definitions','Scenario definitions (continued)']
UNI={'′':r"$'$",'Ṫ':r'$\dot T$','∫':r'$\int$','≥':r'$\geq$','≤':r'$\leq$','≈':r'$\approx$','→':r'$\rightarrow$','≠':r'$\neq$','⁻':r'$^{-}$','¹':r'$^{1}$','⁰':r'$^{0}$','∂':r'$\partial$','ρ':r'$\rho$','Δ':r'$\Delta$','∑':r'$\sum$','−':'-','µ':r'$\mu$','∞':r'$\infty$','∎':r'$\blacksquare$'}
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
    return re.sub(r'@fig:(\w+)@',r'\\ref{fig:\1}',''.join(out))
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
def table(rows,widths=None):
    global tabcount
    tabcount+=1;n=len(rows[0]);tot=float(sum(widths)) if widths else 1
    if widths:cols=''.join(r'>{\raggedright\arraybackslash}p{%.3f\linewidth}'%((w/tot)*0.98-0.02*0) for w in widths)
    else:cols='l'*n
    lines=[' & '.join(tx(c) for c in row) for row in rows]
    tex.append(r'\begin{table}[htbp]\centering\small\caption{'+CAPS[tabcount-1]+'}\n\\begin{tabular}{'+cols+'}\n\\toprule\n'+lines[0]+r' \\ \midrule'+'\n'+(r' \\ '+'\n').join(lines[1:])+r' \\ \bottomrule'+'\n\\end{tabular}\n\\end{table}\n')
def eq(s):
    global eqcount
    eqcount+=1;tex.append(r'\begin{equation}'+re.sub(r'\{\\rm ',r'{\\mathrm ',s)+r'\end{equation}'+'\n')
figcount=[0]
def figure(name,caption,height=None):
    figcount[0]+=1
    m=re.match(r'^Figure (\d+)\. (.*)$',caption,re.S);assert m,caption
    tex.append(texplot.figure_env(FIG[name],tx(m.group(2)),label='fig:'+name.replace('.png','')))
PREAMBLE=r'''\documentclass[12pt,letterpaper]{article}
\usepackage[left=1in,right=1in,top=0.95in,bottom=0.8in,headheight=15pt]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{newtxtext,newtxmath}
\usepackage{booktabs,array,graphicx,xcolor,caption,fvextra,fancyhdr,lastpage,titlesec,needspace}
\usepackage[hidelinks,pdfauthor={},pdftitle={A Hot Bath: Conserving Water Without Losing Uniformity}]{hyperref}
\urlstyle{same}\Urlmuskip=0mu plus 1mu
'''+texplot.PREAMBLE+r'''
\linespread{1.12}
\setlength{\parindent}{1.5em}\setlength{\parskip}{3pt}
\titleformat{\section}{\Large\bfseries}{\thesection}{0.6em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection}{0.6em}{}
\titlespacing*{\section}{0pt}{16pt plus 3pt}{8pt}
\titlespacing*{\subsection}{0pt}{12pt plus 2pt}{6pt}
\captionsetup{font=small,labelfont=bf,labelsep=period,justification=centering}
\captionsetup[table]{position=above,skip=5pt}\captionsetup[figure]{position=below,skip=4pt}
\setcounter{tocdepth}{2}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{Team \# 7391856}\fancyhead[R]{Page \thepage{} of \pageref{LastPage}}
\renewcommand{\headrulewidth}{0.4pt}
\begin{document}
'''
def compile_pdf(stem,title):
    d=ROOT/'paper';d.mkdir(exist_ok=True)
    (d/(stem+'.tex')).write_text(PREAMBLE+''.join(tex)+'\n\\end{document}\n')
    xe=shutil.which('xelatex') or next(iter(sorted(Path.home().glob('texlive/*/bin/*/xelatex'))),None)
    if xe:
        for _ in range(3):res=subprocess.run([str(xe),'-interaction=nonstopmode','-halt-on-error',stem+'.tex'],cwd=d,capture_output=True,text=True)
        ok=res.returncode==0;log=res.stdout
    else:
        res=subprocess.run([shutil.which('tectonic') or str(Path.home()/'.local/bin/tectonic'),stem+'.tex'],cwd=d,capture_output=True,text=True);ok=res.returncode==0;log=res.stdout+res.stderr
    (d/(stem+'.compile.log')).write_text(log)
    assert ok,log[-2500:]
    return d/(stem+'.pdf')

# Figures are pgfplots/TikZ source built from the numerical record; fonts match the paper.
FIG={}
t=z['t']/60;T=z['T'];mean=T@z['volume']/z['volume'].sum()
ax=texplot.Axis('Time (min)','Temperature (°C)',height='5.0cm',xmin=0,xmax=30,ymin=38.85,ymax=p['ceiling']+.2,legend='south west',legend_columns=2)
ax.band(t,T.min(1),T.max(1),label='Spatial range').line(t,mean,label='Volume-weighted mean').line(t,T.min(1),color='clay',style='dashed',label='Coldest cell').hline(p['floor']).hline(p['ceiling'])
FIG['temperature.png']=ax.tex().replace('°C','$^\\circ$C')
labels=['Constant rate','Constant rate, fine grid','Optimized schedule','Perfect mixing','Energy bound'];values=[b['water_l'],r['mesh']['fine_policy']['water_l'],ctl['water_l'],a['mixed_optimum_l'],a['energy_lower_bound_l']]
FIG['bounds.png']=texplot.hbar_chart(labels,values,['sand','sand','teal','clay','slate'],'Added water over 30 min (L)',height='5.0cm',xmax=max(values)*1.3)
seg_min=ctl['segment_s']/60;edges=list(np.arange(len(ctl['flow_lpm'])+1)*seg_min)
Yc=control.piecewise(p,model.network(p),ctl['flow_lpm'],5.);tc=np.linspace(0,30,len(Yc))
a1=texplot.Axis('','Flow (L/min)',width='0.9\\linewidth',height='2.6cm',xmin=0,xmax=30,ymin=0,legend='north east',extra='scale only axis,name=top,xticklabels={}')
a1.stairs(ctl['flow_lpm'],edges,label='Optimized schedule').line([0,30],[b['flow_lpm']]*2,color='clay',style='dashed',label='Best constant rate')
a2=texplot.Axis('Time (min)','Temp. ($^\\circ$C)',width='0.9\\linewidth',height='3.0cm',xmin=0,xmax=30,ymin=38.85,ymax=41.15,legend='south west',legend_columns=2,extra='scale only axis,at={(top.south)},anchor=north,yshift=-0.35cm')
a2.band(tc,Yc.min(1),Yc.max(1)).line(tc,Yc.min(1),color='clay',style='dashed',label='Coldest cell').line(tc,Yc.max(1),label='Hottest cell').hline(p['floor']).hline(p['ceiling'])
FIG['control.png']=a1.tex()+'\n'+a2.tex()
boxes=['Assumptions\nand anchors\n§2','Mixed benchmark\nand bound\n§3–4','Spatial network\nand solver\n§5–6','Rate, schedule,\nscenarios\n§7–9','Validation,\nranges, mesh\n§10–11','Conclusion,\nuser guide\n§12–13']
FIG['roadmap.png']=texplot.flow_diagram(boxes,node_width='2.1cm')
rows_=lr['rows'];okr=[r_ for r_ in rows_ if r_['feasible']];bad=[r_ for r_ in rows_ if not r_['feasible']]
top=max(r_['water_l'] for r_ in okr)*1.08
ax=texplot.Axis('Surface coefficient (W/(m$^2$ K))','Added water (L)',height='5.0cm',legend='north west')
ax.scatter([r_['inputs']['h_surface'] for r_ in okr],[r_['water_l'] for r_ in okr],color='teal',label='Accepted policy')
if bad:ax.scatter([r_['inputs']['h_surface'] for r_ in bad],[top]*len(bad),color='clay',mark='x',size=2.6,label='None accepted')
ax.vline(p['h_surface'])
FIG['ranges.png']=ax.tex()
fr=E['frontier'];okf=[f_ for f_ in fr if f_['constant_l'] is not None]
ax=texplot.Axis('Allowed fall below the starting temperature ($^\\circ$C)','Added water (L)',height='5.0cm',legend='north east')
ax.line([f_['fall'] for f_ in fr],[f_['mixed_l'] for f_ in fr],label='Perfectly mixed optimum (proved)').line([f_['fall'] for f_ in fr],[f_['bound_l'] for f_ in fr],color='slate',style='dashed',width=0.9,label='Energy lower bound')
ax.line([f_['fall'] for f_ in okf],[f_['constant_l'] for f_ in okf],color='clay',marks='*',label='Best constant rate, spatial model')
badf=[f_ for f_ in fr if f_['constant_l'] is None]
if badf:ax.scatter([f_['fall'] for f_ in badf],[0]*len(badf),color='clay',mark='x',size=2.6,label='None accepted')
ax.vline(p['initial']-p['floor'])
FIG['frontier.png']=ax.tex()
cube=T[-1].reshape(tuple(r['grid']))
FIG['spatial.png']=texplot.heatmap_panels([cube[:,:,k].tolist() for k in range(3)],['Bottom layer','Middle layer','Top layer'],'Length (m)','Width (m)',(p['L'],p['W']),float(T[-1].min()),float(T[-1].max()),cbar_label='Final cell-average temperature ($^\\circ$C)',xticks=[0,.75,1.5],yticks=[0,.325,.65])

tex.append(r'\thispagestyle{fancy}\begin{center}\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}ccc}'+'\n'
 r'\textbf{Problem Chosen}&\textbf{MCM/ICM}&\textbf{Team Control Number}\\'+'\n'
 r'{\Large\textbf{A}}&\textbf{Summary Sheet}&{\Large\textbf{'+TEAM_CONTROL_NUMBER+r'}}\end{tabular*}\end{center}\vspace{-4pt}\hrule\vspace{10pt}'+'\n')

para('A Hot Bath: Conserving Water Without Losing Uniformity','title')
para('Summary','heading')
para('Maintaining a warm bath is a coupled problem of heat loss, replenishment and transport. A hot inlet can improve the mean temperature while leaving distant water cool and sending useful heat directly to the overflow. We therefore minimize added water subject to explicit limits on every modeled cell, rather than optimizing an average alone.')
para('We prove a coast-then-hold policy optimal for a well-mixed bath, then use a three-dimensional finite-volume thermal network with coefficients anchored in standard correlations and a published immersion study (Section 2). The best constant rate is compared with an optimized piecewise-constant schedule; neither is proved optimal among all controls.')
para(f'In a 164.25 L water-volume scenario lasting 30 minutes, with an initial temperature of 40°C and a 39°C lower limit, the best constant-rate policy adds <b>{b["water_l"]:.2f} L</b> at {b["flow_lpm"]:.3f} L/min from the start, and a {ctl["segments"]}-segment schedule found by constrained optimization needs <b>{ctl["water_l"]:.2f} L</b>, {save:.0f}% less. The well-mixed optimum is {a["mixed_optimum_l"]:.2f} L, while an independent energy argument gives a {a["energy_lower_bound_l"]:.2f} L lower bound for the spatial problem. A finer mesh changes the constant-rate result by {100*abs(r["mesh"]["fine_policy"]["water_l"]-b["water_l"])/b["water_l"]:.2f}%.')
para(f'The answer depends strongly on the surface and body loss coefficients. Across {lr["samples"]} Sobol draws over literature-based ranges, {lr["feasible"]} had an accepted constant-rate policy, with required water from {qq["0.05"]:.0f} to {qq["0.95"]:.0f} L (5th–95th percentile, median {qq["0.5"]:.0f} L). Weak mixing yields no accepted candidate under the stated temperature limits; stronger mixing saves water, but added surface loss can reverse that benefit. In the assumed foam scenario replenishment falls to {sc["foam"]["policy"]["water_l"]:.1f} L. A tolerance sweep puts each extra 0.5°C of allowed fall at about {(wf(39.25)-wf(38.0))/2.5:.0f} L until a 2.5°C fall needs none, and vertical stratification adds little water but uses most of the spread margin. These are conditional calculations, not measurements or product claims.')
para(f'Independent integration, analytic limits, energy accounting and a between-samples envelope support the results: {len(checks)} model checks and {len(ctl_checks)} for the schedule. A one-page user guide and the limitations follow; AI assistance is disclosed in the references and appended report.')
para('<b>Keywords:</b> thermal network; energy balance; lower bound; optimal control; sensitivity analysis')

tex.append(r'\clearpage\renewcommand{\contentsname}{Contents}\tableofcontents'+'\n')
page('1. Define the decision before optimizing',True)
para('The task is to preserve both warmth and spatial uniformity in an overflowing, unheated tub, and to examine geometry, the bather and motion, and a bubble-bath layer [1]. The report separates physical requirements from preference assumptions. There is no supplied temperature record or measured heat-transfer coefficient to fit.')
para('The decision variables are an inlet flow rate and the time at which a constant trickle begins. The tub is already full: added water displaces an equal volume through the overflow. The horizon is 1,800 s. Our baseline accepts cell averages between 39°C and 41°C, with an instantaneous spread of at most 1.5°C. These choices operationalize comfort; they are not medical limits or numbers specified by the problem.')
eq(r'J=1000\int_0^{t_f}q(t)\,dt')
eq(r'T_{\min}\leq T_i(t)\leq T_{\max},\quad \max_iT_i(t)-\min_iT_i(t)\leq\Delta')
para('Here q is in m³/s and J is in litres. We prioritize the least water within the constraints, rather than assigning arbitrary weights to unlike units. Tightening the temperature tolerance is a separate scenario. Zero flow is admitted: if the initial stored heat suffices, using no added water is globally water-minimal.')
table([['Requirement','Where answered'],['Temperature in space and time','Sections 3, 5–7; Figures @fig:spatial@–@fig:temperature@'],['Water-use strategy and its scope','Sections 4, 6–7 and 12'],['Tub/body geometry, size and temperature','Section 8'],['Motion and bubble-bath additive','Section 9'],['Validation and sensitivity','Sections 8–11'],['One-page non-technical explanation','Section 13']],[210,258])
para('Spatial temperature means a control-volume average. It does not bound the unresolved temperature of a faucet jet or a skin-contact film. This distinction determines which practical conclusions the simulation can support.')

para('<b>Modeling options.</b> A lumped model (Newton cooling) keeps one temperature and cannot see a cold corner. A flow solver resolves velocity but needs a turbulence closure and a faucet jet that nothing available here can constrain. A finite-volume thermal network sits between them: it keeps conservation exact, resolves where heat is lost and delivered, and makes mixing an explicit, testable parameter [5]. We use the lumped model as a proved benchmark (Sections 3–4) and the network for the decision (Sections 5–11).')
table([['Option','Resolves','Evidence it needs','Role here'],['Lumped (Newton)','Mean temperature','Two loss coefficients','Proved benchmark'],['Thermal network','Cells, heat paths, overflow','Loss, body and mixing coefficients','Decision model'],['Flow solver','Velocity and buoyancy','Turbulence closure, jet data','Not used']],[100,120,130,118])
figure('roadmap.png','Figure 1. Roadmap: how the sections build from assumptions to a recommendation.',height=111)
page('2. Physical assumptions and scenario inputs')
para('Each assumption below is paired with its reason and, where it matters, the scenario that tests it. Coefficients cannot be identified from the problem statement alone, so they come from the anchors in Section 2.1.')
table([['Quantity','Baseline / units','Status'],['Tub L × W × H','1.50 × 0.65 × 0.23 m','Assumed geometry'],['Displaced body volume / area','0.060 m³ / 1.15 m²','Assumed'],['Water density / heat capacity','1000 kg/m³ / 4180 J/(kg K)','Rounded constants'],['Air / skin / inlet temperature','22 / 34 / 50°C','Fixed reservoirs'],['Surface / wall / body coefficient','25 / 6.5 / 25 W/(m² K)','Literature-anchored (next page)'],['Mixing diffusivity D','0.001 m²/s','Uncalibrated closure; range tested'],['Initial / lower / upper limit','40 / 39 / 41°C','Preference scenario'],['Time / allowed spread','1800 s / 1.5°C','Preference scenario']],[182,188,98])
para('<b>A1. Constant density and heat capacity.</b> Water properties change by under 1% between 39 and 41°C, and the constants are rounded values, not an evaluated IAPWS table [3]. <i>Reason:</i> the resulting capacity error is small next to the loss coefficients.')
para('<b>A2. Heat exchange proportional to temperature difference.</b> Surface, shell and body exchange follow Newton’s law with effective coefficients [2]. <i>Reason:</i> the temperature span is narrow, so linearization is acceptable. The surface coefficient aggregates convection, radiation and evaporation, so evaporation is not added twice; evaporative volume change is neglected.')
para('<b>A3. Skin held at a fixed temperature.</b> <i>Reason:</i> thermoregulation is outside the problem; skin temperature is varied (32 and 36°C) instead of resolved.')
para('<b>A4. Inlet-to-overflow surface stream.</b> The hot water travels along a prescribed surface path to the overflow, so short circuit is possible. <i>Reason:</i> a different inlet geometry would need its own transport network and evidence.')
para('<b>A5. Mixing as one effective diffusivity D.</b> Motion enters through D, with a separate surface-loss scenario. <i>Reason:</i> molecular diffusion alone would not represent circulation; D is anchored only by an order-of-magnitude scaling (Section 2.1) and is tested over a range; vertical mixing is tested separately in Section 9.')

page('2.1 Where the coefficients come from')
sf=prov['surface'];wl=prov['wall'];bd=prov['body']
para(f'No temperature record exists to fit, so each coefficient is anchored in a standard relation or a published measurement and given a range. Surface loss sums natural convection above a hot horizontal surface ($\\mathrm{{Nu}}=0.15\\,\\mathrm{{Ra}}^{{1/3}}$ for $10^{{7}}<\\mathrm{{Ra}}<10^{{11}}$, length $A/P$ [5]; here $\\mathrm{{Ra}}={sf["rayleigh"]/1e7:.1f}\\times10^{{7}}$), linearized radiation (emissivity 0.96) and evaporation by the Lewis analogy. For open water at 40°C in 22°C air at 50% humidity the parts are {sf["parts"]["convection"]:.1f}, {sf["parts"]["radiation"]:.1f} and {sf["parts"]["evaporation"]:.1f} W/(m² K) ({sf["evaporation_kg_m2_h"]:.2f} kg/m² h evaporated), {sf["open_water_total"]:.1f} in total. A bather covers part of the surface; with an assumed exposed fraction of 0.7 the central value is {sf["central"]:.1f}, and we use 25 within the range 17–37.')
para(f'The shell coefficient is a series resistance: a 5 mm shell (0.19 W/(m K)) with film coefficients of 300 inside and 8 W/(m² K) outside gives {wl["central"]:.1f}, and {wl["range"][0]:.1f}–{wl["range"][1]:.1f} for other thicknesses. These are typical engineering values, not measurements of a particular tub. The body coefficient is anchored by a measurement: Menzies et al. report a rectal-temperature rise of 0.9 ± 0.3°C after 30 minutes in 40°C water to the shoulders [6]. Taking the mean body mass of the study participants, 73 kg, $c=3470$ J/(kg K) and a mean body rise of 1–2°C, the average heat uptake is {bd["anchor"][0]["average_uptake_w"]:.0f}–{bd["anchor"][1]["average_uptake_w"]:.0f} W, equal to {bd["anchor"][0]["equivalent_h_body"]:.0f}–{bd["anchor"][1]["equivalent_h_body"]:.0f} W/(m² K) with skin held at 34°C. We use 25, because a fixed skin node overstates the driving difference later in the bath. The mean body rise and the driving difference are assumptions, so this is an order-of-magnitude anchor, not a calibration.')
para('Mixing has only a scaling anchor. A mixing-length estimate $D\\approx 0.1\\,u\'\\ell$, with a velocity scale $u\'$ and eddy size $\\ell$, gives about 1e-4 m²/s for buoyancy-driven flow alone ($u\'=0.02$ m/s, $\\ell=0.05$ m), 1e-3 for gentle movement of the bather (0.1 m/s, 0.1 m) and 6e-3 for vigorous movement (0.3 m/s, 0.2 m). We use 0.001 and test 0.0003–0.003. This is a scaling argument, not a measurement, so D stays a scenario. The 39–41°C window is a preference; immersion studies use 40–42°C water [6], which is not a safety standard. A 40.5°C upper limit was tried first: the coarse mesh accepted a 24.51 L constant-rate policy, but the finer mesh accepted none, because the inlet-cell average rises under refinement. The limit was set to 41°C, where both meshes agree.')
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
para('<b>Step 1, an identity.</b> Dividing the balance by $T_{\\mathrm{in}}-T$ and integrating over the horizon gives')
eq(r'\int q\,dt=\frac{C}{\rho c_p}\log\frac{T_{\rm in}-T_0}{T_{\rm in}-T_f}+\int\frac{\ell(T)}{\rho c_p(T_{\rm in}-T)}\,dt')
para('<b>Step 2, monotonicity.</b> The integrand $\\ell(T)/(T_{\\mathrm{in}}-T)$ has derivative $[H_a(T_{\\mathrm{in}}-T_a)+H_b(T_{\\mathrm{in}}-T_b)]/(T_{\\mathrm{in}}-T)^2>0$, so it increases with $T$, and the logarithmic term increases with the final temperature. Water use is therefore an increasing functional of the temperature path.')
para('<b>Step 3, the lowest admissible path.</b> Because $q\\ge 0$, comparison with the no-flow solution gives $T(t)\\ge T_c(t)$, the cooling curve of Section 3, and feasibility requires $T(t)\\ge T_{\\min}$. The pointwise lowest admissible path is $\\max(T_c(t),T_{\\min})$: coast until $T_c$ reaches $T_{\\min}$, then hold.')
para('<b>Step 4, attainability.</b> Holding $T=T_{\\min}$ means $\\dot T=0$, which needs the rate')
eq(r'q_{\rm hold}=\frac{\ell(T_{\min})}{\rho c_p(T_{\rm in}-T_{\min})}')
para(f'When this rate is within the bound, the path is feasible, and by Step 2 it is optimal. ∎ For the baseline it adds {a["mixed_optimum_l"]:.2f} L: wait {a["coast_s"]/60:.2f} min, then supply {a["hold_lpm"]:.3f} L/min. This is a proved optimum of the mixed model, not a guarantee for a spatially nonuniform tub.')
para('<b>Proposition 2 (energy lower bound).</b> In the spatial model, suppose every cell satisfies $T_i(t)\\ge T_{\\min}$. Summing the cell balances gives $\\sum_i C_iT_i(t_f)-CT_0=-\\int L\\,dt+\\rho c_p\\int q(T_{\\mathrm{in}}-T_{\\mathrm{out}})\\,dt$, with $L$ the total loss. Each loss term increases with its cell temperature, and $H_a$ and $H_b$ are the sums of the cell conductances, so $L(t)\\ge\\ell(T_{\\min})$. The outlet cell satisfies $T_{\\mathrm{out}}\\ge T_{\\min}$, so $T_{\\mathrm{in}}-T_{\\mathrm{out}}\\le T_{\\mathrm{in}}-T_{\\min}$, and the left side is at least $C(T_{\\min}-T_0)$. Combining these three facts,')
eq(r'J\geq\max\left(0,\frac{1000[\ell(T_{\min})t_f-C(T_0-T_{\min})]}{\rho c_p(T_{\rm in}-T_{\min})}\right)')
para(f'The resulting {a["energy_lower_bound_l"]:.2f} L is a genuine conditional lower bound, valid for any control, but it is not tight: the initial water is hotter than the floor and loses more heat, and limited mixing adds further cost. Section 7.1 shows how much of the gap an optimized schedule recovers.')

page('5. A conservative model in three dimensions')
para('The rectangular water envelope is divided into 8 × 4 × 3 cells. Each has a capacity $C_i$ and exchanges heat only across common faces. Top cells lose heat to the room; bottom and side faces lose heat through the shell. The bather is represented by a smooth, three-dimensional displacement field and a distributed skin contact term.')
eq(r'C_i\dot T_i=\sum_jg_{ij}(T_j-T_i)+H_{a,i}(T_a-T_i)+H_{b,i}(T_b-T_i)+S_i')
eq(r'g_{ij}=\rho c_pD\frac{A_{ij}}{d_{ij}}\min(\phi_i,\phi_j),\quad C_i=\rho c_pV_i')
para('Here $\\phi$ is fluid fraction, $A_{ij}$ a face area and $d_{ij}$ the center separation. Symmetric $g_{ij}$ guarantees that internal heat exchange cancels when the equations are summed. D is an effective mixing closure; molecular diffusion alone would not represent motion or buoyant circulation.')
eq(r'w_i\propto\exp\left[-\frac{1}{2}\sum_{k=1}^3\left(\frac{x_{ik}-b_k}{s_k}\right)^2\right],\quad \sum_iw_i=1')
eq(r'V_i=V_{\rm cell}-V_bw_i,\quad H_{b,i}=h_bA_bw_i')
para('Baseline $\\mathbf{b}=(0.55L,\\,W/2,\\,0.45H)$, with widths $\\mathbf{s}=(0.40,0.16,0.12)$ m. Fluid fraction is $\\phi_i=V_i/V_{\\mathrm{cell}}$. The center $\\mathbf{b}$ and widths $\\mathbf{s}$ set the spatial distribution of body effects. Body volume and contact area remain independent inputs: shape is varied through $\\mathbf{s}$ at fixed volume and area. This is a homogenized immersed-body representation, not an anatomically resolved obstruction. A cell whose occupied fraction reaches 0.95 is rejected rather than assigned a negative capacity.')
para('A fixed envelope volume is preserved by balancing inlet and overflow. In the baseline the exact displaced-water volume is 164.25 L. Shape scenarios preserve envelope volume when isolating aspect-ratio effects. Volume scenarios deliberately change water depth and hence both storage and side-wall area.')

page('5.1 Spatial evidence: the mean is not the whole bath')
figure('spatial.png','Figure 4. Final temperatures in the three horizontal cell layers. All layers use one color scale; the top layer contains the prescribed inlet-to-overflow stream. Geometry is in metres, and values are cell averages.',height=199)
para('The heat map is calculated from the same archived trajectory as Figure @fig:temperature@. It shows where the imposed transport path and environmental/body sinks leave temperature differences. The plots are horizontal slices through a three-dimensional network with exchange between layers, not three independent two-dimensional models.')
para('A temperature range summarizes the spread but cannot show its location. The maps make the physical interpretation inspectable: localized replenishment and distributed losses must be balanced through mixing. Every cell contributes to the comfort test; a high mean cannot compensate for a cold region.')
para('The Gaussian body representation changes both storage and exchange distribution. A map does not prove that this homogenized representation captures anatomy, recirculation or buoyancy. Its role is to reveal the actual implications of the declared model, not to create the appearance of a resolved flow simulation. The refinement table separately checks how cell size affects the result.')

page('6. Inlet transport, solver and strategy search')
para('Inlet and overflow are on opposite ends of a surface stream. Every path edge carries the same q: the first cell receives hot water, interior cells receive upstream water and lose the same volume downstream, and the last cell discharges through the overflow.')
eq(r'S_1=\rho c_pq(T_{\rm in}-T_1),\quad S_i=\rho c_pq(T_{i-1}-T_i)')
eq(r'\sum_i C_i\dot T_i=-\sum_iH_{a,i}(T_i-T_a)-\sum_iH_{b,i}(T_i-T_b)+\rho c_pq(T_{\rm in}-T_{\rm out})')
para('This stream deliberately allows hot-water short circuit. Heat can leave at a locally warm outlet before warming a distant cold region. It is an explicit transport assumption, not an inferred flow field. Alternative inlet placement would require another transport network and calibration.')
para('For a fixed flow, the network is affine linear. Augmenting the state by a constant one permits matrix-exponential propagation, avoiding a large forward-Euler step restriction [4]. A delayed-start policy has two exact constant-control segments.')
eq(r'\dot{\mathbf{T}}=A(q)\mathbf{T}+\mathbf{b}(q),\quad \mathbf{z}(t+\tau)=e^{\widetilde{A}(q)\tau}\mathbf{z}(t)')
para('Starts are tested at 0, 120, …, 1200 seconds. For each, rates from 0 to 3 L/min are bracketed on a 0.2 L/min grid; the first crossing of the lower-temperature requirement is refined by Brent’s root method. The search targets $T_{\\min}+0.03$°C as numerical reserve, then checks the upper-temperature and spread limits at 5-second output intervals. Starts that already violate the floor are rejected.')
para('This is a reproducible candidate search. Nonmonotone flow responses, untested delays, pulsed inputs, inlet relocation and feedback are not excluded by the calculation. A failed search means no candidate was accepted, not that every possible action is infeasible. The independent checks further examine the chosen trajectory between samples.')

page('7. The spatial result and the mixing penalty')
figure('temperature.png','Figure 5. Matrix-exponential cell temperatures under the selected policy. The shaded range includes all cells; the mean alone would hide cold and hot locations.',height=208)
table([['Result','Baseline'],['Rate / start',f'{b["flow_lpm"]:.3f} L/min / {b["delay_s"]/60:.1f} min'],['Added water',f'{b["water_l"]:.2f} L'],['Minimum / maximum',f'{b["min_temp"]:.3f} / {b["max_temp"]:.3f}°C'],['Maximum simultaneous spread',f'{b["max_span"]:.3f}°C'],['Final volume-weighted mean',f'{b["final_mean"]:.3f}°C']],[300,168])
para('Within the constant-rate family, starting the trickle immediately ranks ahead of delayed starts here, even though waiting is optimal in the ideal mixed model. The distant water needs time to receive heat; larger late rates create a warmer inlet region before they solve the cold-region constraint. This is a concrete consequence of resolving space.')
para(f'Holding a perfectly mixed bath at 40°C throughout would use {a["constant_at_target_l"]:.2f} L. This is a stricter reference service, not a like-for-like optimum. Our accepted 1°C cooling allowance uses less water partly because it provides a different service. The comparable mixed model with the same lower limit uses {a["mixed_optimum_l"]:.2f} L. The gap also reflects our restricted control family and 0.03°C numerical reserve; it cannot be attributed purely to imperfect mixing.')

page('7.1 A time-varying schedule uses less water')
flows=ctl['flow_lpm'];K=len(flows);lead=next((i for i,v in enumerate(flows) if v>1e-3),K);trail=next((i for i,v in enumerate(reversed(flows)) if v>1e-3),K);seg_min=ctl['segment_s']/60
para(f'Constant-rate policies are a narrow family. We therefore optimize piecewise-constant inlet flow in K equal segments (K = 3, 6, 12) by sequential quadratic programming, minimizing added water under the same all-cell limits (with the 0.03°C reserve), sampled every 15 s and re-checked at 5 s, from four starting schedules. The problem is non-convex: each result is the best local optimum found, with no global claim.')
rows=[['Policy','Water (L)','Change','Min / max (°C)','Spread (°C)'],['Best constant rate',f'{b["water_l"]:.2f}','—',f'{b["min_temp"]:.2f} / {b["max_temp"]:.2f}',f'{b["max_span"]:.2f}']]
for run in ct:rows.append([f'{run["segments"]} segments',f'{run["water_l"]:.2f}',f'{100*(run["water_l"]/b["water_l"]-1):+.1f}%',f'{run["min_temp"]:.2f} / {run["max_temp"]:.2f}',f'{run["max_span"]:.2f}'])
rows+=[['Perfect-mixing optimum',f'{a["mixed_optimum_l"]:.2f}','','',''],['Energy lower bound',f'{a["energy_lower_bound_l"]:.2f}','','','']]
table(rows,[150,70,70,100,78])
pseudo='''Input: network, limits, K, starting schedules\nfor each starting schedule x0:\n  minimize sum(x)*segment_time  over 0 <= x <= 3 L/min\n  subject to  min_i T_i(t) >= Tmin+reserve,  max_i T_i(t) <= Tmax,\n              max_i T_i(t) - min_i T_i(t) <= span   (every 15 s)\nreplay the best x at 5 s; keep it only if all margins >= 0'''
tex.append('\\noindent\\begin{minipage}{\\linewidth}\\begin{Verbatim}[frame=single,fontsize=\\small,framesep=4pt]\n'+pseudo+'\n\\end{Verbatim}\n\\end{minipage}\n')

figure('control.png',f'Figure 6. Best {K}-segment schedule against the best constant rate (top) and the range of cell temperatures (bottom); dotted lines mark the limits.',height=176)
para(f'The {K}-segment schedule is {"off" if lead else "on"} for the first {lead*seg_min:.1f} minutes and off for the last {trail*seg_min:.1f} minutes, with a peak of {max(flows):.2f} L/min between. It adds {ctl["water_l"]:.2f} L, {save:.1f}% below the constant rate, and narrows the gap to the energy lower bound from {b["water_l"]-a["energy_lower_bound_l"]:.1f} L to {ctl["water_l"]-a["energy_lower_bound_l"]:.1f} L. Refining from 3 to {K} segments gains only {100*(ct[0]["water_l"]-ctl["water_l"])/ct[0]["water_l"]:.1f}%: the saving comes from the shape. The optimum touches the lower limit and the spread limit ({ctl["max_span"]:.2f}°C) and comes close to the upper limit ({ctl["max_temp"]:.2f}°C).')
para('We have not isolated why the best schedule stops at the end. One candidate explanation, an inference rather than a model result, is that hot water added late leaves through the overflow before it warms the remote cells, while stored heat carries the final minutes. ')

page('7.2 What does staying close to the start temperature cost?')
fm={f_['floor']:f_ for f_ in E['frontier']}
w=lambda fl:fm[fl]['constant_l']
para(f'The task asks for a bath close to its initial temperature without wasting much water, which is a trade-off rather than a single optimum. Figure @fig:frontier@ repeats the search while the allowed fall below 40°C changes from 0.25 to 3°C; the 1°C case is the baseline. With a fall of 2.5°C or more the stored heat suffices and no water is added. At 2°C the best constant rate adds {w(38.0):.1f} L, at 1.5°C {w(38.5):.1f} L, at 1°C {w(39.0):.1f} L and at 0.75°C {w(39.25):.1f} L. Between 2°C and 0.75°C each further 0.5°C of tolerance is therefore worth roughly {(w(39.25)-w(38.0))/(2.0-.75)/2:.0f} L, almost linearly. For a fall of 0.5°C or less no constant-rate policy was accepted; the perfectly mixed bath would still need {fm[39.5]["mixed_l"]:.1f} L at 0.5°C.')
figure('frontier.png','Figure 7. Added water against the allowed temperature fall. The mixed optimum and energy bound are closed forms; markers on the brown curve are searched constant-rate policies, and the dotted line is the baseline.',height=182)
para(f'The curve is the practical answer to “how close is close enough”: below a 2.5°C fall every degree of tolerance bought back costs about the same, so the tolerance is worth choosing deliberately. The perfectly mixed curve lies below the spatial one at every tolerance, and the gap widens as the tolerance tightens, from {fm[38.0]["constant_l"]-fm[38.0]["mixed_l"]:.1f} L at 2°C to {fm[39.25]["constant_l"]-fm[39.25]["mixed_l"]:.1f} L at 0.75°C: the stricter the comfort requirement, the more uneven mixing costs. Only constant-rate policies are searched here; scheduled flow (Section 7.1) lowers the baseline point by about 18% and would shift the brown curve down by a similar fraction, an expectation that was not recomputed at the other tolerances.')

page('7.3 Can a user follow the schedule?')
tol=E['control']['tolerance'];price=E['control']['buffer_price'];rob=E['control'].get('robust_tolerance')
us=tol['uniform_scale_slack_c'];rnd=tol['random_error'];pl=[-x['slack_plus20'] for x in tol['segments']];mi=[-x['slack_minus20'] for x in tol['segments']]
pw={x['buffer_c']:x['water_l'] for x in price}
para(f'A schedule that a person cannot follow is of little use, so we perturb the tap instead of the physics. The optimized schedule touches the spread limit, so its slack to the stated limits is zero. Scaling every segment by 0.9 or 1.1 leaves a shortfall of {-us["0.90"]:.3f} and {-us["1.10"]:.3f}°C. With independent errors of 10% in each segment, {rnd["0.10"]["share_within_limits"]:.0%} of 200 draws stay within the limits; the median shortfall is {-rnd["0.10"]["median_slack_c"]:.3f}°C and the 5th-percentile draw misses by {-rnd["0.10"]["p05_slack_c"]:.3f}°C. The violations are small but certain: an optimum that lies on its constraints has no tolerance.')
para(f'The error is not symmetric. Raising one segment by 20% breaks the limits by {min(pl):.3f} to {max(pl):.3f}°C, because extra hot water overheats the inlet region and widens the spread; lowering a single segment by 20% costs at most {max(mi):.3f}°C. The first segment is the most forgiving. Over-delivery is the error to guard against.')
buf=f'{pw[0.1]:.2f} L (+{(pw[0.1]/pw[0.]-1):.1%})' if pw.get(0.1) else 'no schedule'
rob_text=''
if rob:
    r10=rob['random_error']['0.10']
    rob_text=f' With that buffer, {r10["share_within_limits"]:.0%} of 200 draws with 10% segment errors stay within the limits.'
para(f'The price of a margin is measured on a 6-segment version. Requiring all three limits to hold with a buffer b gives {pw[0.]:.2f} L at b = 0, {buf} at 0.1°C, and no schedule at 0.2°C or 0.3°C: the 1.5°C spread limit leaves no room for a larger buffer in this family.'+rob_text+' A user who cannot hold the tap to within a few percent should buy the 0.1°C buffer or accept the constant trickle, which does not sit on the spread limit.')

page('8. Separate geometry, size and body effects')
rows=[['Change from baseline','Water (L)','Interpretation']]
for key,desc in [('shallow wide','Same envelope volume'),('deep narrow','Same envelope volume'),('small bath','Lower water depth'),('large bath','Higher water depth'),('larger body','More displacement/contact'),('long body','Shape only; fixed volume/area'),('warmer skin','Skin at 36°C'),('cooler skin','Skin at 32°C')]:
 v=sc[key]['policy'];rows.append([key.title(),f'{v["water_l"]:.2f}' if v['feasible'] else 'No candidate',desc])
table(rows,[148,86,234])
para(f'At equal volume, the wide, shallow tub has a larger exposed top area and a changed diffusion length, and no candidate was accepted for it. The deep, narrow tub needs {sc["deep narrow"]["policy"]["water_l"]:.2f} L against {b["water_l"]:.2f} L, because a deep, narrow envelope reduces top-area heat loss, although a real deep bath may stratify, which Section 9 tests with a separate vertical-mixing scenario. Geometry is therefore more than an interchangeable cooling coefficient.')
para(f'Changing depth at fixed length and width changes thermal storage and shell area. Greater water volume slows cooling, which can lower added water over a short fixed horizon: the large bath needs {sc["large bath"]["policy"]["water_l"]:.2f} L, while no candidate was accepted for the small bath. That does not mean a larger bath conserves total water: filling it initially uses more. J counts replenishment only, and this distinction prevents a misleading conservation claim.')
para('The larger-body scenario simultaneously displaces more water and increases assumed contact area; it is a combined size scenario and has no accepted candidate. The long-body scenario isolates the spatial distribution by keeping total body volume and contact area fixed. Warmer skin reduces the temperature difference driving body heat loss. These changes quantify conditional dependence; they do not establish measured human heat transfer.')
para('To transfer the model to a real tub, measure water volume after entry, submerged contact geometry, temperatures at several depths and distances, and no-inlet cooling. Shape and temperature should not be inferred from a single mean cooling curve.')

page('9. Motion and a bubble layer can change the policy')
rows=[['Scenario','Added water (L)','Search outcome']]
for key in ['weak mixing','strong mixing','moving with added surface loss','stratified','foam','tight comfort','loose comfort','low loss','high loss','cool supply']:
 v=sc[key]['policy'];rows.append([key.title(),f'{v["water_l"]:.2f}' if v['feasible'] else '—','Accepted' if v['feasible'] else 'None accepted'])
table(rows,[224,116,128])
para(f'Increasing D reduces the gradient created by the localized inlet. The strong-mixing scenario uses {sc["strong mixing"]["policy"]["water_l"]:.2f} L against {b["water_l"]:.2f} L, but motion may also increase heat loss. When D is increased together with a 20% increase in the surface coefficient (30 instead of 25 W/(m² K)), the need rises to {sc["moving with added surface loss"]["policy"]["water_l"]:.2f} L and most of the benefit disappears. The comparison deliberately separates transport improvement from its possible boundary cost.')
para(f'Stratification is tested separately. A hot inlet layer is lighter than the water below, and the stable density gradient suppresses vertical mixing. With a cell height of 0.077 m, a vertical temperature difference of 1 K, a velocity scale of 0.02 m/s and an expansion coefficient of about 3.8e-4 per K, the gradient Richardson number is $\\mathrm{{Ri}}=g\\beta\\,\\Delta T\\,\\ell/u^2\\approx 0.7$. The Munk–Anderson stability function for scalars, $(1+3.33\\,\\mathrm{{Ri}})^{{-3/2}}$ [8], then reduces vertical diffusivity to about 0.15 of its neutral value. We test a vertical-to-horizontal ratio of 0.2. The best constant rate becomes {sc["stratified"]["policy"]["water_l"]:.2f} L against {b["water_l"]:.2f} L, but the maximum spread rises from {b["max_span"]:.2f} to {sc["stratified"]["policy"]["max_span"]:.2f}°C, close to the 1.50°C limit. Stratification therefore costs little water here and takes most of the uniformity margin; the ratio is an order-of-magnitude scenario and the Richardson estimate uses assumed velocity and temperature scales.')
para(f'The foam scenario multiplies only the effective surface coefficient by 0.4. With all other inputs fixed, the best constant rate falls to {sc["foam"]["policy"]["water_l"]:.2f} L. The assumed 60% reduction is a scenario, not an experimentally established property of bubble-bath additive. If the layer breaks up or motion raises evaporation, this result must be recomputed.')
none=[k.title() for k,v in sc.items() if not v['policy']['feasible']]
para('No accepted candidate exists for: '+', '.join(none)+'. They are reported as such, not hidden in a favorable average. Their outcomes identify where the restricted strategy must change. Potential responses include improved circulation, a different inlet path, a shorter bath, or a different comfort tolerance. The paper does not certify which response is safe or optimal without corresponding physical evidence.')

page('10. Validation: independent evidence and remaining error')
figure('bounds.png','Figure 8. Water-use comparison under the same lower limit. The energy bound is conditional on the network assumptions; the feasible spatial result remains above it.',height=208)
num=lambda name:json.loads(next(c['evidence'] for c in checks if c['name']==name))
energy=num('instantaneous_energy_balance_with_overflow');rk=num('independent_RK45_vs_archived_matrix_exponential');env=num('continuous_time_policy_envelope')
para(f'All {len(checks)} recorded checks pass. Independent heat-flow arithmetic sums environmental losses, body exchange and local-temperature overflow; the largest instantaneous residual is {energy["max_residual_w"]:.2e} W. An adaptive RK45 integration with independently assembled right-hand side agrees with the archived matrix-exponential trajectory within {rk["maximum_temperature_difference_c"]:.2e}°C. This tests numerical implementation, not a second physical model.')
para('A constructed uniform-loss problem reproduces its analytic exponential cooling solution. Internal exchange cancels globally, and the stream has exactly one overflow sink. Positive off-diagonal dynamics and nonpositive row sums support physical bounds and a contractive derivative estimate for each constant-flow segment.')
para(f'One-second sampling is supplemented by a derivative bound: if |dTi/dt| ≤ L, a point lies at most 0.5 seconds from a sample, so temperatures differ by at most L/2 and spread by at most L. With a numerical allowance, the resulting lower envelope is {env["lower_temperature_bound_c"]:.4f}°C, upper {env["upper_temperature_bound_c"]:.4f}°C, and spread upper bound {env["span_upper_bound_c"]:.4f}°C. This is a conditional floating-point envelope, not interval-arithmetic certification.')

ind=E['control']['independent']
para(f'The optimized schedule is replayed with the independently assembled right-hand side and RK45 at one-second samples. It agrees with the matrix-exponential trajectory within {ind["max_difference_c"]:.1e}°C and satisfies the limits (minimum {ind["min_temp"]:.3f}°C, maximum {ind["max_temp"]:.3f}°C, spread {ind["max_span"]:.3f}°C, each within the 0.002°C sampling tolerance); its {ctl["water_l"]:.2f} L exceeds the {a["energy_lower_bound_l"]:.2f} L energy bound, as it must. These two checks cover this one schedule and are separate from the {len(checks)} model checks.')

page('11. Resolution, uncertainty and transfer to a real bath')
f=r['mesh']['fine_policy'];fp=r['mesh']['coarse_policy_on_fine']
table([['Resolution / replay','Water (L)','Minimum','Maximum spread'],['8 × 4 × 3 selected',f'{b["water_l"]:.3f}',f'{b["min_temp"]:.3f}°C',f'{b["max_span"]:.3f}°C'],['12 × 6 × 4 selected',f'{f["water_l"]:.3f}',f'{f["min_temp"]:.3f}°C',f'{f["max_span"]:.3f}°C'],['Coarse policy on fine grid',f'{fp["water_l"]:.3f}',f'{fp["min_temp"]:.3f}°C',f'{fp["max_span"]:.3f}°C']],[180,85,93,110])
para(f'The selected water amounts differ by {100*abs(f["water_l"]-b["water_l"])/b["water_l"]:.2f}%. The fine grid preserves the coarse-policy constraints at sampled times. The larger fine-grid spread exposes a more localized inlet temperature: a close water-volume result does not establish pointwise temperature convergence. Two meshes are a diagnostic, not an asymptotic convergence-order study.')
para('Parameter uncertainty concerns heat loss, body exchange and mixing. Structural uncertainty concerns the prescribed surface stream, fixed skin reservoir, homogenized body and constant effective D. These are different errors. The scenario table explores parameter dependence and one coupled motion effect; it is not a probability distribution or confidence interval.')
names_lr={'h_surface':'surface coefficient','h_body':'body coefficient','air_temp':'room temperature','body_temp':'skin temperature','h_wall':'shell coefficient','D':'mixing diffusivity'}
para(f'Literature-range analysis. Section 2 gives ranges for six inputs. {lr["samples"]} scrambled Sobol points cover them (D log-uniform), and the constant-rate search runs at each. {lr["feasible"]} points have an accepted candidate. Among those, the required water is {qq["0.05"]:.1f}, {qq["0.25"]:.1f}, {qq["0.5"]:.1f}, {qq["0.75"]:.1f} and {qq["0.95"]:.1f} L at the 5th, 25th, 50th, 75th and 95th percentiles. The remaining {lr["samples"]-lr["feasible"]} points, mostly at high loss, have none. The baseline of {b["water_l"]:.1f} L sits in the upper half of this distribution.')
figure('ranges.png','Figure 9. Required water against the surface coefficient for each Sobol draw. Crosses at the top mark draws with no accepted policy; the vertical line is the baseline.',height=182)
para('Spearman rank correlations with water, over accepted draws: '+', '.join(f'{names_lr[k]} {v:+.2f}' for k,v in sorted(sp.items(),key=lambda kv:-abs(kv[1])))+'.')
para('The correlations use accepted draws only, so they understate inputs that push draws into infeasibility. The draws are uniform over ranges that we chose; they are not a probability distribution for any real tub. The main message is that the loss coefficients and the room temperature, not the mixing closure, decide how much water is needed, which is why Section 2 anchors them in outside evidence.')
para('A calibration plan should begin with an inlet-free cooling experiment, recording water volume and room conditions. Multiple temperature probes distinguish aggregate heat loss from mixing. A separate inlet experiment records flow and inlet/outlet temperatures, allowing overflow energy to be checked. Motion and foam need matched trials because both can alter transfer coefficients. Reserve an entire experiment for prediction checks after fitting. A single mean-temperature series cannot separate the surface, shell and body coefficients, so only calibrated and independently tested parameters would support advice for a particular bath.')

page('12. Conclusions and a policy with clear scope')
para(f'The model supports four linked findings. First, tolerating a modest temperature decline lets stored heat replace some inlet water. Second, spatial transport changes the ideal mixed recommendation: the best constant rate starts at once, and a schedule that withholds water at both ends needs {save:.0f}% less. Third, the water required is dominated by the surface and body loss coefficients: from {qq["0.05"]:.0f} to {qq["0.95"]:.0f} L across the literature-based ranges. Fourth, improving mixing helps only to the extent that it does not create offsetting boundary loss or hot-water short circuit.')
para(f'For the stated baseline, the best constant trickle is {b["flow_lpm"]:.3f} L/min for {b["water_l"]:.2f} L over 30 minutes; the {K}-segment schedule uses {ctl["water_l"]:.2f} L. These are the best accepted results of the documented searches, with all-cell constraints and independent numerical checks. Neither is a universal faucet prescription or a proved global optimum over all time-varying controls.')
para('The spatial model earns its complexity by explaining a disagreement with a proved simple benchmark and by rejecting strategies that a mean-only calculation would accept. Conservative accounting, anchored coefficients with stated ranges, a feasible-policy versus lower-bound gap, and an explicit refinement check make the recommendation inspectable.')
para(f'<b>Strengths.</b> The conservation laws hold exactly and are checked by an independently assembled integrator; the benchmark and the lower bound are proved, so the spatial result is bracketed; the coefficients carry sources, ranges and a sensitivity analysis; the optimized schedule shrinks the gap to the bound from {b["water_l"]-a["energy_lower_bound_l"]:.1f} to {ctl["water_l"]-a["energy_lower_bound_l"]:.1f} L.')
para('<b>Weaknesses.</b> The surface stream and the effective D stand in for flow physics; the body coefficient rests on an assumed mean body rise and skin gradient; the schedule is a local optimum; the inlet-cell limit depends on mesh resolution; and no bath experiment was run.')
para('The limitations are consequential. Three-dimensional geometry is represented, but fluid momentum, buoyancy, jet entrainment, free-surface motion and detailed body anatomy are not solved. No bath experiment was conducted. Temperature limits express a preference assumption. Coarse cell averages cannot establish burn safety near the inlet, and the shape scenarios do not resolve stable vertical layers.')
para('Before using a numerical rate in practice, identify the real tub’s cooling and mixing behavior. Until then, the defensible transferable advice is to avoid unnecessary replenishment, distinguish cold-region temperature from the mean, improve distribution before increasing flow, and reconsider a strategy when geometry or motion changes. The following page translates these principles without requiring the user to interpret the equations.')

page('13. A warmer bath, with less replacement water',True)
para('A guide for the person in the bathtub','heading')
para(f'<b>Decide what “warm enough” means.</b> A bath need not stay at exactly its starting temperature to remain acceptable. In our example, allowing a 1°C fall still needs about {b["water_l"]:.0f} L of replacement water, while allowing a 2°C fall needs only {sc["loose comfort"]["policy"]["water_l"]:.1f} L. Your actual comfort and health needs must determine the acceptable range.')
para('<b>Distribute the warmth before turning up the tap.</b> The water near the faucet can warm while the far end remains cool. Gentle movement can help redistribute heat. More vigorous motion is not automatically better: it may also increase heat loss from the surface.')
para(f'<b>Run the tap in the middle, not at the ends.</b> For the tub and mixing conditions analyzed here, the least-water schedule adds no hot water for the first {lead*seg_min:g} minutes or the last {trail*seg_min:g} minutes and a steady stream in between; a constant trickle from the start used {100*(b["water_l"]/ctl["water_l"]-1):.0f}% more. In a bath that mixes very quickly, waiting until it has cooled slightly can save more. There is no single schedule that works for every tub.')
para(f'<b>Do not follow a clever schedule too exactly, or too generously.</b> The least-water schedule sits on the edge of what is comfortable: a tap that runs 10% hot or cold crosses the edge by about a tenth of a degree, and extra hot water does more harm than too little. Keep a small margin; in our example it costs about {(pw[0.1]/pw[0.]-1):.0%} more water.')
para('<b>Check more than one location.</b> A comfortable mean temperature can hide a cold far corner or a hot inlet region. Check the bath away from the faucet and at different depths. Do not use a model’s cell-average temperature as a reason to contact a hot jet.')
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
'[7] OpenAI, Codex (GPT-6-based assistant), and Anthropic, Claude Sonnet 5.5 in Claude Code. Used on 7 October 2026 for modeling, code, validation and report composition; exact builds not independently established. See Report on Use of AI Tools.',
'[8] Munk, W. H., Anderson, E. R. Notes on a theory of the thermocline. Journal of Marine Research, 7(3), 276–295, 1948.',
]
for ref in refs:para(ref,'ref')
para('Algorithm and computational record','heading')
para('1. Form cell volumes and capacities; reject excessive body occupancy. Assemble symmetric face exchange, environmental/body conductances and the conservative stream. 2. Compute the mixed closed forms and energy lower bound. 3. Evaluate delayed constant-flow candidates with matrix exponentials and refine the first bracketed lower-temperature crossing. Reject spread or upper-limit violations. 4. Rank accepted candidates by added litres. 5. Independently integrate and check balances, analytic limits, parameter arithmetic and constraints; replay a finer mesh and perturb physical scenarios. 6. Optimize piecewise-constant schedules (multi-start SQP) and replay the best independently. 7. Rerun the constant-rate search at Sobol draws over the literature ranges. Independent RK45 checks use relative tolerance 2e-9, absolute 2e-10°C and steps of at most 5 s. AI assistance is acknowledged in [7].')

names={'D':'D (m²/s)','Dz_ratio':'vertical/horizontal D ratio','h_surface':'surface coefficient (W/m²K)','foam':'surface multiplier','floor':'lower limit (°C)','L':'length (m)','W':'width (m)','H':'depth (m)','body_volume':'body displacement (m³)','body_area':'body contact area (m²)','body_shape':'body widths s (m)','body_temp':'skin temperature (°C)','h_wall':'wall coefficient (W/m²K)','h_body':'body coefficient (W/m²K)','inlet_temp':'inlet temperature (°C)'}
items=list(sc.items())
for part in range(2):
 page('Appendix A. Scenario definitions'+(' (continued)' if part else ''),True)
 para('Each row changes only the listed baseline inputs. All unspecified inputs remain as stated in Section 2; geometry and conductance are then rebuilt. The equal-volume aspect-ratio cases retain the envelope volume of 0.22425 m³. Widths s describe a smooth displacement distribution, not measured anatomical semiaxes.')
 rows=[['Scenario','Changed input(s)']]
 for label,item in items[part*9:(part+1)*9]:
  text='; '.join(names.get(k,k)+' = '+(str(v) if isinstance(v,list) else f'{v:.6g}') for k,v in item['changes'].items())
  rows.append([label.title(),text])
 table(rows,[144,324])
 para('Accepted candidates are independently replayed on their scenario network at intervals of no more than five seconds. These scenario checks are sampled checks; the stronger one-second continuous-time envelope is reported for the selected baseline policy only. “None accepted” refers to the documented finite search and is not an infeasibility theorem.')

page('Report on Use of AI Tools',True)
para('Tool and scope','heading')
para('OpenAI Codex, a GPT-6-based assistant, was used on 7 October 2026. The later revision (literature-based coefficients, schedule optimization, range analysis and rebuilding of this report) used Anthropic’s Claude, Sonnet 5.5, through Claude Code on the same date. Structure and presentation were informed by five Outstanding papers on other problems; none on this problem was read. The assistant once read COMAP’s published judges’ commentary on this problem during development and then removed every change it had prompted. The assistant selected the historical problem, located and read sources, formulated the mixed and spatial models, wrote and revised Python code, designed checks, interpreted numerical runs, generated figures, and drafted and typeset the English report. An assistant sub-agent wrote the independent-RHS validation routine; this is AI-assisted code review, not review by another human.')
para('Task','heading')
para('The task was to select a classic historical MCM problem and build a rigorous, professional case from it. The conversation wording is not reproduced in this report or in the development record.')
para('Outputs, corrections and verification','heading')
para('AI-produced outputs are the model, validation and report-building sources; the mathematical derivations, scenario tables, figures and text in this document. Numerical values came from actual Python runs. Citations [1]–[4] were checked against the linked sources; [5] and [8] were not opened (their relations were checked against web summaries and a turbulence-model source) and [6] was read in full from the open-access author manuscript. The first baseline coefficients and the 40.5°C upper limit were replaced after anchoring and mesh refinement.')
para('Record limitations','heading')
para('A full exported interaction transcript and every intermediate AI output were not available in this artifact. The task description, tool identification, scope, code artifacts and numerical receipts are retained in the accompanying development record; this report does not invent a transcript. No independent human review or physical bath experiment is claimed.')
para('Python, NumPy and SciPy performed the mathematics; the report was typeset in XeLaTeX, with figures drawn by pgfplots and TikZ from the archived numerical record. These deterministic tools do not establish empirical validity. The service model/build beyond the available GPT-6-based identifier was not independently verified.')

TOTAL=SEC[0]
pdf=compile_pdf('main','A Hot Bath')
(ROOT/'submission').mkdir(exist_ok=True)
shutil.copyfile(pdf,ROOT/'submission'/(TEAM_CONTROL_NUMBER+'.pdf'))
print(json.dumps({'pdf':str(ROOT/'submission'/(TEAM_CONTROL_NUMBER+'.pdf')),'sections':TOTAL,'equations':eqcount,'tables':tabcount,'figures':figcount[0],'checks':len(checks)}))
