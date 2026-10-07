"""Professional single-file MCM report; numerical evidence is supplied, never invented."""
import argparse,json,math,re,sys
from pathlib import Path
from xml.sax.saxutils import escape
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.mathtext import MathTextParser
from matplotlib.font_manager import FontProperties
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,Flowable,KeepTogether

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
import model,control
TEAM_CONTROL_NUMBER='7391856'
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);args=parser.parse_args()
r=json.loads((args.run/'results.json').read_text());checks=json.loads((args.run/'checks.json').read_text())
assert all(c['passed'] for c in checks)
p=r['parameters'];b=r['policy'];a=r['analytic'];sc=r['scenarios'];z=np.load(args.run/'trajectory.npz')
E=json.loads((args.run/'extended.json').read_text());ctl=E['control']['best'];prov=E['provenance'];lr=E['literature_ranges'];ctl_checks=E['checks']
assert all(c['passed'] for c in ctl_checks)
save=100*(1-ctl['water_l']/b['water_l']);qq=lr['water_quantiles_l'];sp=lr['spearman_with_water']
ct=E['control']['runs']
ROOT.joinpath('figures').mkdir(exist_ok=True);ROOT.joinpath('submission').mkdir(exist_ok=True)
fontdir=Path('/System/Library/Fonts/Supplemental')
for name,file in [('Text','Times New Roman.ttf'),('Bold','Times New Roman Bold.ttf'),('Italic','Times New Roman Italic.ttf')]:pdfmetrics.registerFont(TTFont(name,str(fontdir/file)))
pdfmetrics.registerFontFamily('Text',normal='Text',bold='Bold',italic='Italic',boldItalic='Bold')
styles={k:ParagraphStyle(k,fontName='Text',fontSize=12,leading=16.8,spaceAfter=8,allowWidows=0,allowOrphans=0) for k in ['body','caption','table']}
styles['title']=ParagraphStyle('title',parent=styles['body'],fontName='Bold',fontSize=19,leading=23,spaceAfter=15)
styles['heading']=ParagraphStyle('heading',parent=styles['body'],fontName='Bold',fontSize=15,leading=19,spaceAfter=12,keepWithNext=True)
styles['table'].leading=14.2
styles['caption'].leading=15
flow=[];content=[];pages=0;eqcount=0

def para(s,kind='body'):
 flow.append(Paragraph(s,styles[kind]));content.append({'kind':kind,'text':s})
def page(title):
 global pages
 if pages:flow.append(PageBreak())
 pages+=1;para(title,'title');content.append({'page':pages})
def table(rows,widths=None):
 data=[[Paragraph(escape(str(x)),styles['table']) for x in row] for row in rows]
 t=Table(data,colWidths=widths or [468/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,0),.8,colors.black),('LINEBELOW',(0,0),(-1,0),.5,colors.black),('LINEBELOW',(0,-1),(-1,-1),.8,colors.black),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
 flow.extend([t,Spacer(1,10)]);content.append({'table':rows})
mathparser=MathTextParser('path');matplotlib.rcParams['mathtext.fontset']='stix'
class Equation(Flowable):
 def __init__(self,s,num):
  super().__init__();self.s=s;self.num=num;self.v=mathparser.parse('$'+s+'$',dpi=72,prop=FontProperties(size=14));self.width=456;self.height=max(28,float(self.v.height)+18)
  if self.v.width>426:raise ValueError('Equation too wide '+s)
 def draw(self):
  c=self.canv;v=self.v;c.saveState();c.translate((432-v.width)/2,8+v.depth)
  for glyph in v.glyphs:
   font,size,num=glyph[:3];ox,oy=glyph[-2:];font.set_size(size,72);font.load_char(num);verts,codes=font.get_path();path=c.beginPath();i=0;last=(0,0)
   while i<len(codes):
    op=codes[i];x,y=verts[i];x+=ox;y+=oy
    if op==1:path.moveTo(x,y);last=(x,y);i+=1
    elif op==2:path.lineTo(x,y);last=(x,y);i+=1
    elif op==3:
     ex,ey=verts[i+1];ex+=ox;ey+=oy;path.curveTo(last[0]+2*(x-last[0])/3,last[1]+2*(y-last[1])/3,ex+2*(x-ex)/3,ey+2*(y-ey)/3,ex,ey);last=(ex,ey);i+=2
    elif op==4:
     x2,y2=verts[i+1];ex,ey=verts[i+2];path.curveTo(x,y,x2+ox,y2+oy,ex+ox,ey+oy);last=(ex+ox,ey+oy);i+=3
    elif op==79:path.close();i+=1
    else:raise ValueError(op)
   c.drawPath(path,fill=1,stroke=0)
  for x,y,w,h in v.rects:c.rect(x,y,w,h,fill=1,stroke=0)
  c.restoreState();c.setFont('Text',12);c.drawRightString(456,self.height/2-3,'('+str(self.num)+')')
def eq(s):
 global eqcount
 eqcount+=1;flow.append(Equation(s,eqcount));content.append({'equation':s,'number':eqcount})
def figure(name,caption,height=210):
 flow.append(Image(str(ROOT/'figures'/name),width=468,height=height));para(caption,'caption');content.append({'figure':name})

plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':15,'axes.spines.top':False,'axes.spines.right':False,'axes.labelsize':15,'xtick.labelsize':15,'ytick.labelsize':15,'legend.fontsize':15,'figure.dpi':180})
t=z['t']/60;T=z['T'];mean=T@z['volume']/z['volume'].sum()
fig,ax=plt.subplots(figsize=(8,3.55));ax.fill_between(t,T.min(1),T.max(1),color='#17766e',alpha=.14,label='Spatial range');ax.plot(t,mean,color='#17766e',label='Volume-weighted mean');ax.plot(t,T.min(1),color='#9e6440',ls='--',label='Coldest cell');ax.axhline(p['floor'],color='black',ls=':',lw=1);ax.axhline(p['ceiling'],color='black',ls=':',lw=1);ax.set(xlabel='Time (min)',ylabel='Temperature (°C)',ylim=(38.85,p['ceiling']+.2));ax.legend(loc='lower left',ncol=2);fig.tight_layout();fig.savefig(ROOT/'figures'/'temperature.png');plt.close(fig)
labels=['Constant rate','Constant rate, fine grid','Optimized schedule','Perfect mixing','Energy bound'];values=[b['water_l'],r['mesh']['fine_policy']['water_l'],ctl['water_l'],a['mixed_optimum_l'],a['energy_lower_bound_l']]
fig,ax=plt.subplots(figsize=(8,3.55));ax.barh(labels[::-1],values[::-1],color=['#aaa69b','#b5bba8','#17766e','#9e6440','#5d696e']);ax.set(xlabel='Added water over 30 min (L)',xlim=(0,max(values)*1.3));
for i,v in enumerate(values[::-1]):ax.text(v+.12,i,f'{v:.2f} L',va='center')
fig.tight_layout();fig.savefig(ROOT/'figures'/'bounds.png');plt.close(fig)

seg_min=ctl['segment_s']/60;edges=np.arange(len(ctl['flow_lpm'])+1)*seg_min
fig,(ax1,ax2)=plt.subplots(2,1,figsize=(8,3.2),sharex=True,gridspec_kw={'height_ratios':[1,1.15]},layout='constrained')
ax1.stairs(ctl['flow_lpm'],edges,color='#17766e',lw=2,label='Optimized schedule');ax1.hlines(b['flow_lpm'],0,30,color='#9e6440',ls='--',label='Best constant rate');ax1.set_ylabel('Flow (L/min)',fontsize=13);ax1.legend(loc='upper right',fontsize=12)
Yc=control.piecewise(p,model.network(p),ctl['flow_lpm'],5.);tc=np.linspace(0,30,len(Yc))
ax2.fill_between(tc,Yc.min(1),Yc.max(1),color='#17766e',alpha=.14);ax2.plot(tc,Yc.min(1),color='#9e6440',ls='--',label='Coldest cell');ax2.plot(tc,Yc.max(1),color='#17766e',label='Hottest cell');ax2.axhline(p['floor'],color='black',ls=':',lw=1);ax2.axhline(p['ceiling'],color='black',ls=':',lw=1)
ax2.set(xlabel='Time (min)',ylim=(38.85,41.15));ax2.set_ylabel('Temp. (°C)',fontsize=13);ax2.legend(loc='lower left',ncol=2,fontsize=12)
fig.savefig(ROOT/'figures'/'control.png');plt.close(fig)

cube=T[-1].reshape(tuple(r['grid']))
fig,axes=plt.subplots(1,3,figsize=(8,3.4),layout='constrained')
for k,ax in enumerate(axes):
 im=ax.imshow(cube[:,:,k].T,origin='lower',extent=[0,p['L'],0,p['W']],vmin=T[-1].min(),vmax=T[-1].max(),cmap='viridis',aspect='equal')
 ax.set(title=['Bottom layer','Middle layer','Top layer'][k],xlabel='Length (m)',ylabel='Width (m)' if k==0 else '')
 ax.set_xticks([0,.75,1.5]);ax.set_yticks([0,.325,.65])
fig.colorbar(im,ax=axes,orientation='horizontal',shrink=.8,label='Final cell-average temperature (°C)',pad=.1)
fig.savefig(ROOT/'figures'/'spatial.png');plt.close(fig)

# Official Summary Sheet hierarchy: metadata first, then the summary content.
# The current official sample has a stale visible year; historical cases omit it.
pages=1
summary_style=ParagraphStyle('summary_metadata',parent=styles['table'],fontName='Bold',alignment=1,leading=16)
summary_cells=[
 Paragraph('Problem Chosen<br/><font size="18">A</font>',summary_style),
 Paragraph('MCM/ICM<br/>Summary Sheet',summary_style),
 Paragraph('Team Control Number<br/><font size="18">'+TEAM_CONTROL_NUMBER+'</font>',summary_style),
]
summary_header=Table([summary_cells],colWidths=[152]*3,hAlign='LEFT')
summary_header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),12),('LINEBELOW',(0,0),(-1,-1),.6,colors.black)]))
flow.extend([summary_header,Spacer(1,16)])
content.append({'page':1,'summary_metadata':{'problem':'A','team_control_number':TEAM_CONTROL_NUMBER,'label':'MCM/ICM Summary Sheet'}})
para('A Hot Bath: Conserving Water Without Losing Uniformity','title')
para('Summary','heading')
para('Maintaining a warm bath is a coupled problem of heat loss, replenishment and transport. A hot inlet can improve the mean temperature while leaving distant water cool and sending useful heat directly to the overflow. We therefore minimize added water subject to explicit limits on every modeled cell, rather than optimizing an average alone.')
para('We first derive a well-mixed energy balance and prove a coast-then-hold policy optimal for that idealized system. A three-dimensional finite-volume thermal network then represents shell and surface losses, body displacement and heat exchange, internal mixing, and a conservative inlet-to-overflow stream. Its heat-transfer coefficients are anchored in standard correlations and a published immersion study rather than chosen freely (Section 2). We compare the best constant-rate policy with a piecewise-constant schedule found by constrained optimization; neither is a proof of unrestricted control optimality.')
para(f'In a 164.25 L water-volume scenario lasting 30 minutes, with an initial temperature of 40°C and a 39°C lower limit, the best constant-rate policy adds <b>{b["water_l"]:.2f} L</b> at {b["flow_lpm"]:.3f} L/min from the start. A {ctl["segments"]}-segment schedule that withholds hot water at the start and the end needs <b>{ctl["water_l"]:.2f} L</b>, {save:.0f}% less. The well-mixed optimum is {a["mixed_optimum_l"]:.2f} L, while an independent energy argument gives a {a["energy_lower_bound_l"]:.2f} L lower bound for the spatial problem. A finer mesh changes the constant-rate result by {100*abs(r["mesh"]["fine_policy"]["water_l"]-b["water_l"])/b["water_l"]:.2f}%.')
para(f'The answer depends strongly on the surface and body loss coefficients. Across {lr["samples"]} Sobol draws over literature-based ranges, {lr["feasible"]} had an accepted constant-rate policy, with required water from {qq["0.05"]:.0f} to {qq["0.95"]:.0f} L (5th–95th percentile, median {qq["0.5"]:.0f} L). Weak mixing yields no accepted candidate under the stated temperature limits; stronger mixing saves water, but added surface loss can reverse that benefit. In the assumed foam scenario replenishment falls to {sc["foam"]["policy"]["water_l"]:.1f} L. These are conditional calculations, not measurements or product claims.')
para(f'Independent adaptive integration, analytic limits, energy accounting and a time-between-samples envelope support the numerical results. The report includes {len(checks)} recorded model checks and {len(ctl_checks)} for the optimized schedule, sensitivity scenarios, a one-page user explanation and transparent limitations. AI-assisted development is disclosed in the references and appended use report.')

page('1. Define the decision before optimizing')
para('The task is to preserve both warmth and spatial uniformity in an overflowing, unheated tub, and to examine geometry, the bather and motion, and a bubble-bath layer [1]. The report separates physical requirements from preference assumptions. There is no supplied temperature record or measured heat-transfer coefficient to fit.')
para('The decision variables are an inlet flow rate and the time at which a constant trickle begins. The tub is already full: added water displaces an equal volume through the overflow. The horizon is 1,800 s. Our baseline accepts cell averages between 39°C and 41°C, with an instantaneous spread of at most 1.5°C. These choices operationalize comfort; they are not medical limits or numbers specified by the problem.')
eq(r'J=1000\int_0^{t_f}q(t)\,dt')
eq(r'T_{\min}\leq T_i(t)\leq T_{\max},\quad \max_iT_i(t)-\min_iT_i(t)\leq\Delta')
para('Here q is in m³/s and J is in litres. We prioritize the least water within the constraints, rather than assigning arbitrary weights to unlike units. Tightening the temperature tolerance is a separate scenario. Zero flow is admitted: if the initial stored heat suffices, using no added water is globally water-minimal.')
table([['Requirement','Where answered'],['Temperature in space and time','Sections 3, 5–7; Figures 1–2'],['Water-use strategy and its scope','Sections 4, 6–7 and 12'],['Tub/body geometry, size and temperature','Section 8'],['Motion and bubble-bath additive','Section 9'],['Validation and sensitivity','Sections 8–11'],['One-page non-technical explanation','Section 13']],[210,258])
para('Spatial temperature means a control-volume average. It does not bound the unresolved temperature of a faucet jet or a skin-contact film. This distinction determines which practical conclusions the simulation can support.')

page('2. Physical assumptions and scenario inputs')
para('A constant-density, constant-heat-capacity liquid stores sensible heat. The exchange law is proportional to temperature difference; coefficients depend on the situation and normally require empirical calibration [2]. Rounded water-property constants are used as approximations, not as an evaluated IAPWS property-table dataset [3].')
table([['Quantity','Baseline / units','Status'],['Tub L × W × H','1.50 × 0.65 × 0.23 m','Assumed geometry'],['Displaced body volume / area','0.060 m³ / 1.15 m²','Assumed'],['Water density / heat capacity','1000 kg/m³ / 4180 J/(kg K)','Rounded constants'],['Air / skin / inlet temperature','22 / 34 / 50°C','Fixed reservoirs'],['Surface / wall / body coefficient','25 / 6.5 / 25 W/(m² K)','Literature-anchored (next page)'],['Mixing diffusivity D','0.001 m²/s','Uncalibrated closure; range tested'],['Initial / lower / upper limit','40 / 39 / 41°C','Preference scenario'],['Time / allowed spread','1800 s / 1.5°C','Preference scenario']],[182,188,98])
para('The surface coefficient aggregates convection, linearized radiation and evaporation over a narrow temperature range. The shell coefficient aggregates water-side transfer, wall conduction and external loss to room air. This avoids adding an evaporation term twice; it does not predict humidity or foam chemistry separately. Evaporation-related volume change is neglected relative to the water volume; the boundary coefficient models its heat effect only.')
para('Skin temperature is held fixed as an effective reservoir. A 30-minute bath can change skin temperature; the fixed value is therefore varied, not claimed to resolve thermoregulation. Bath motion is represented through D, with an additional surface-loss scenario. Coefficients cannot be identified from this problem statement alone.')

page('2 (continued). Where the coefficients come from')
sf=prov['surface'];wl=prov['wall'];bd=prov['body']
para(f'No temperature record exists to fit, so each coefficient is anchored in a standard relation or a published measurement and given a range. Surface loss sums natural convection above a hot horizontal surface (Nu = 0.15 Ra^(1/3) for 10^7 < Ra < 10^11, length A/P [6]; here Ra = {sf["rayleigh"]/1e7:.1f} × 10^7), linearized radiation (emissivity 0.96) and evaporation by the Lewis analogy. For open water at 40°C in 22°C air at 50% humidity the parts are {sf["parts"]["convection"]:.1f}, {sf["parts"]["radiation"]:.1f} and {sf["parts"]["evaporation"]:.1f} W/(m² K) ({sf["evaporation_kg_m2_h"]:.2f} kg/m² h evaporated), {sf["open_water_total"]:.1f} in total. A bather covers part of the surface; with an assumed exposed fraction of 0.7 the central value is {sf["central"]:.1f}, and we use 25 within the range 17–37.')
para(f'The shell coefficient is a series resistance: a 5 mm shell (0.19 W/(m K)) with film coefficients of 300 inside and 8 W/(m² K) outside gives {wl["central"]:.1f}, and {wl["range"][0]:.1f}–{wl["range"][1]:.1f} for other thicknesses. These are typical engineering values, not measurements of a particular tub. The body coefficient is anchored by a measurement: Menzies et al. report a rectal-temperature rise of 0.9 ± 0.3°C after 30 minutes in 40°C water to the shoulders [7]. Assuming a 75 kg body, c = 3470 J/(kg K) and a mean body rise of 1–2°C, the average heat uptake is {bd["anchor"][0]["average_uptake_w"]:.0f}–{bd["anchor"][1]["average_uptake_w"]:.0f} W, equal to {bd["anchor"][0]["equivalent_h_body"]:.0f}–{bd["anchor"][1]["equivalent_h_body"]:.0f} W/(m² K) with skin held at 34°C. We use 25, because a fixed skin node overstates the driving difference later in the bath. The mass and the mean rise are assumptions, so this is an order-of-magnitude anchor, not a calibration.')
para('Mixing has no anchor: D = 0.001 m²/s is a scenario inside the range 0.0003–0.003. The 39–41°C window is a preference; immersion studies use 40–42°C water [7], which is not a safety standard. A 40.5°C upper limit was tried first: the coarse mesh accepted a 24.51 L constant-rate policy, but the finer mesh accepted none, because the inlet-cell average rises under refinement. The limit was set to 41°C, where both meshes agree.')
table([['Coefficient','Relation or anchor','Derived value','Used (range tested)'],['Surface, W/(m² K)','Convection + radiation + evaporation [6]',f'{sf["open_water_total"]:.1f} open; {sf["central"]:.1f} at 70%','25 (17–37)'],['Shell, W/(m² K)','Series resistance, typical shell values',f'{wl["central"]:.1f} ({wl["range"][0]:.1f}–{wl["range"][1]:.1f})','6.5 (4.5–8.5)'],['Body, W/(m² K)','Uptake implied by core rise [7]',f'{bd["anchor"][0]["equivalent_h_body"]:.0f}–{bd["anchor"][1]["equivalent_h_body"]:.0f} at fixed skin','25 (12–40)'],['Mixing D, m²/s','No anchor; scenario','—','0.001 (0.0003–0.003)']],[96,162,110,100])

page('3. A transparent well-mixed benchmark')
para('Let C be total water heat capacity, Ha the air/shell conductance and Hb the body conductance. A well-mixed overflow has the same temperature as the bath. Integrating the physical energy balance gives')
eq(r'C\dot T=H_a(T_a-T)+H_b(T_b-T)+\rho c_pq(T_{\rm in}-T)')
eq(r'C=\rho c_p(LWH-V_b),\quad H_b=h_bA_b')
eq(r'H_a=h_s fLW+h_w\{LW+2H(L+W)\}')
para('The foam multiplier f equals one without a layer. Setting q = 0, define H = Ha + Hb and Te = (Ha Ta + Hb Tb)/H. The cooling solution and first time to reach the lower limit are')
eq(r'T(t)=T_e+(T_0-T_e)e^{-Ht/C}')
eq(r't_c=\frac{C}{H}\log\frac{T_0-T_e}{T_{\min}-T_e}')
para(f'Baseline conductances are Ha = {a["air_conductance"]:.2f} W/K and Hb = {a["body_conductance"]:.2f} W/K, and C = {p["rho"]*p["cp"]*(p["L"]*p["W"]*p["H"]-p["body_volume"]):,.0f} J/K. Thus Te = {a["equilibrium"]:.2f}°C and tc = {a["coast_s"]/60:.2f} min.')
para('A heat-loss model must approach an environmental equilibrium rather than zero Celsius. This analytic boundary also supplies a direct check on signs and units. The benchmark describes mixing perfectly; the spatial model will test the cost of departing from that assumption.')

page('4. What can be proved about water use?')
para('For the ideal mixed bath, let loss(T) = Ha(T − Ta) + Hb(T − Tb), with the inlet warmer than the permitted bath. Rearranging the balance and integrating gives')
eq(r'\int q\,dt=\frac{C}{\rho c_p}\log\frac{T_{\rm in}-T_0}{T_{\rm in}-T_f}+\int\frac{\ell(T)}{\rho c_p(T_{\rm in}-T)}\,dt')
para('The integral’s temperature-dependent factor is strictly increasing because its derivative has numerator Ha(Tin − Ta) + Hb(Tin − Tb) &gt; 0. The terminal term is also increasing in final temperature. Nonnegative heating cannot make the bath colder than its no-flow trajectory. Under the lower-bound constraint, coast to Tmin and then hold there is the pointwise lowest feasible trajectory. It therefore minimizes both terms, provided the required holding rate is within the faucet bound.')
eq(r'q_{\rm hold}=\frac{\ell(T_{\min})}{\rho c_p(T_{\rm in}-T_{\min})}')
para(f'This ideal optimum adds {a["mixed_optimum_l"]:.2f} L: wait {a["coast_s"]/60:.2f} min, then supply {a["hold_lpm"]:.3f} L/min. This is a proved optimum of the mixed model, not a policy guarantee for a spatially nonuniform tub.')
para('For the spatial bath, all cell temperatures above Tmin imply total loss at least loss(Tmin). The outlet is also at least Tmin, so a litre can contribute at most ρcp(Tin − Tmin)/1000 of net sensible energy. The initial stored heat above the floor is at most C(T0 − Tmin). Consequently any feasible policy obeys')
eq(r'J\geq\max\left(0,\frac{1000[\ell(T_{\min})t_f-C(T_0-T_{\min})]}{\rho c_p(T_{\rm in}-T_{\min})}\right)')
para(f'The resulting {a["energy_lower_bound_l"]:.2f} L is a genuine conditional lower bound, but it is not tight enough to prove our spatial policy optimal. Initial hotter water loses more heat, and limited mixing adds further cost.')

page('5. A conservative model in three dimensions')
para('The rectangular water envelope is divided into 8 × 4 × 3 cells. Each has a capacity Ci and exchanges heat only across common faces. Top cells lose heat to the room; bottom and side faces lose heat through the shell. The bather is represented by a smooth, three-dimensional displacement field and a distributed skin contact term.')
eq(r'C_i\dot T_i=\sum_jg_{ij}(T_j-T_i)+H_{a,i}(T_a-T_i)+H_{b,i}(T_b-T_i)+S_i')
eq(r'g_{ij}=\rho c_pD\frac{A_{ij}}{d_{ij}}\min(\phi_i,\phi_j),\quad C_i=\rho c_pV_i')
para('Here φ is fluid fraction, Aij a face area and dij the center separation. Symmetric gij guarantees that internal heat exchange cancels when the equations are summed. D is an effective mixing closure; molecular diffusion alone would not represent motion or buoyant circulation.')
eq(r'w_i\propto\exp\left[-\frac{1}{2}\sum_{k=1}^3\left(\frac{x_{ik}-b_k}{s_k}\right)^2\right],\quad \sum_iw_i=1')
eq(r'V_i=V_{\rm cell}-V_bw_i,\quad H_{b,i}=h_bA_bw_i')
para('Baseline b = (0.55L, W/2, 0.45H), with widths s = (0.40, 0.16, 0.12) m. Fluid fraction is φi = Vi/Vcell. The center b and widths s set the spatial distribution of body effects. Body volume and contact area remain independent inputs: shape is varied through s at fixed volume and area. This is a homogenized immersed-body representation, not an anatomically resolved obstruction. A cell whose occupied fraction reaches 0.95 is rejected rather than assigned a negative capacity.')
para('A fixed envelope volume is preserved by balancing inlet and overflow. In the baseline the exact displaced-water volume is 164.25 L. Shape scenarios preserve envelope volume when isolating aspect-ratio effects. Volume scenarios deliberately change water depth and hence both storage and side-wall area.')

page('Spatial evidence: the mean is not the whole bath')
figure('spatial.png','Figure 1. Final temperatures in the three horizontal cell layers. All layers use one color scale; the top layer contains the prescribed inlet-to-overflow stream. Geometry is in metres, and values are cell averages.',height=199)
para('The heat map is calculated from the same archived trajectory as Figure 2. It shows where the imposed transport path and environmental/body sinks leave temperature differences. The plots are horizontal slices through a three-dimensional network with exchange between layers, not three independent two-dimensional models.')
para('A temperature range summarizes the spread but cannot show its location. The maps make the physical interpretation inspectable: localized replenishment and distributed losses must be balanced through mixing. Every cell contributes to the comfort test; a high mean cannot compensate for a cold region.')
para('The Gaussian body representation changes both storage and exchange distribution. A map does not prove that this homogenized representation captures anatomy, recirculation or buoyancy. Its role is to reveal the actual implications of the declared model, not to create the appearance of a resolved flow simulation. The refinement table separately checks how cell size affects the result.')

page('6. Inlet transport, solver and strategy search')
para('Inlet and overflow are on opposite ends of a surface stream. Every path edge carries the same q: the first cell receives hot water, interior cells receive upstream water and lose the same volume downstream, and the last cell discharges through the overflow.')
eq(r'S_1=\rho c_pq(T_{\rm in}-T_1),\quad S_i=\rho c_pq(T_{i-1}-T_i)')
eq(r'\sum_i C_i\dot T_i=-\sum_iH_{a,i}(T_i-T_a)-\sum_iH_{b,i}(T_i-T_b)+\rho c_pq(T_{\rm in}-T_{\rm out})')
para('This stream deliberately allows hot-water short circuit. Heat can leave at a locally warm outlet before warming a distant cold region. It is an explicit transport assumption, not an inferred flow field. Alternative inlet placement would require another transport network and calibration.')
para('For a fixed flow, the network is affine linear. Augmenting the state by a constant one permits matrix-exponential propagation, avoiding a large forward-Euler step restriction [4]. A delayed-start policy has two exact constant-control segments.')
eq(r'\dot{\mathbf{T}}=A(q)\mathbf{T}+\mathbf{b}(q),\quad \mathbf{z}(t+\tau)=e^{\widetilde{A}(q)\tau}\mathbf{z}(t)')
para('Starts are tested at 0, 120, …, 1200 seconds. For each, rates from 0 to 3 L/min are bracketed on a 0.2 L/min grid; the first crossing of the lower-temperature requirement is refined by Brent’s root method. The search targets Tmin + 0.03°C as numerical reserve, then checks the upper-temperature and spread limits at 5-second output intervals. Starts that already violate the floor are rejected.')
para('This is a reproducible candidate search. Nonmonotone flow responses, untested delays, pulsed inputs, inlet relocation and feedback are not excluded by the calculation. A failed search means no candidate was accepted, not that every possible action is infeasible. The independent checks further examine the chosen trajectory between samples.')

page('7. The spatial result and the mixing penalty')
figure('temperature.png','Figure 2. Matrix-exponential cell temperatures under the selected policy. The shaded range includes all cells; the mean alone would hide cold and hot locations.',height=208)
table([['Result','Baseline'],['Rate / start',f'{b["flow_lpm"]:.3f} L/min / {b["delay_s"]/60:.1f} min'],['Added water',f'{b["water_l"]:.2f} L'],['Minimum / maximum',f'{b["min_temp"]:.3f} / {b["max_temp"]:.3f}°C'],['Maximum simultaneous spread',f'{b["max_span"]:.3f}°C'],['Final volume-weighted mean',f'{b["final_mean"]:.3f}°C']],[300,168])
para('Within the constant-rate family, starting the trickle immediately ranks ahead of delayed starts here, even though waiting is optimal in the ideal mixed model. The distant water needs time to receive heat; larger late rates create a warmer inlet region before they solve the cold-region constraint. This is a concrete consequence of resolving space.')
para(f'Holding a perfectly mixed bath at 40°C throughout would use {a["constant_at_target_l"]:.2f} L. This is a stricter reference service, not a like-for-like optimum. Our accepted 1°C cooling allowance uses less water partly because it provides a different service. The comparable mixed model with the same lower limit uses {a["mixed_optimum_l"]:.2f} L. The gap also reflects our restricted control family and 0.03°C numerical reserve; it cannot be attributed purely to imperfect mixing.')

page('7 (continued). A time-varying schedule uses less water')
flows=ctl['flow_lpm'];K=len(flows);lead=next((i for i,v in enumerate(flows) if v>1e-3),K);trail=next((i for i,v in enumerate(reversed(flows)) if v>1e-3),K);seg_min=ctl['segment_s']/60
para(f'Constant-rate policies are a narrow family. We therefore optimize piecewise-constant inlet flow in K equal segments (K = 3, 6, 12) by sequential quadratic programming, minimizing added water under the same all-cell limits (with the 0.03°C reserve), sampled every 15 s and re-checked at 5 s, from four starting schedules. The problem is non-convex: each result is the best local optimum found, with no global claim.')
rows=[['Policy','Water (L)','Change','Min / max (°C)','Spread (°C)'],['Best constant rate',f'{b["water_l"]:.2f}','—',f'{b["min_temp"]:.2f} / {b["max_temp"]:.2f}',f'{b["max_span"]:.2f}']]
for run in ct:rows.append([f'{run["segments"]} segments',f'{run["water_l"]:.2f}',f'{100*(run["water_l"]/b["water_l"]-1):+.1f}%',f'{run["min_temp"]:.2f} / {run["max_temp"]:.2f}',f'{run["max_span"]:.2f}'])
rows+=[['Perfect-mixing optimum',f'{a["mixed_optimum_l"]:.2f}','','',''],['Energy lower bound',f'{a["energy_lower_bound_l"]:.2f}','','','']]
table(rows,[150,70,70,100,78])
figure('control.png',f'Figure 3. Best {K}-segment schedule against the best constant rate (top) and the range of cell temperatures (bottom); dotted lines mark the limits.',height=176)
para(f'The {K}-segment schedule is {"off" if lead else "on"} for the first {lead*seg_min:.1f} minutes and off for the last {trail*seg_min:.1f} minutes, with a peak of {max(flows):.2f} L/min between. It adds {ctl["water_l"]:.2f} L, {save:.1f}% below the constant rate, and narrows the gap to the energy lower bound from {b["water_l"]-a["energy_lower_bound_l"]:.1f} L to {ctl["water_l"]-a["energy_lower_bound_l"]:.1f} L. Refining from 3 to {K} segments gains only {100*(ct[0]["water_l"]-ctl["water_l"])/ct[0]["water_l"]:.1f}%: the saving comes from the shape. The optimum touches the lower limit and the spread limit ({ctl["max_span"]:.2f}°C) and comes close to the upper limit ({ctl["max_temp"]:.2f}°C).')
para('We have not isolated why the best schedule stops at the end. One candidate explanation, an inference rather than a model result, is that hot water added late leaves through the overflow before it warms the remote cells, while stored heat carries the final minutes. ')

page('8. Separate geometry, size and body effects')
rows=[['Change from baseline','Water (L)','Interpretation']]
for key,desc in [('shallow wide','Same envelope volume'),('deep narrow','Same envelope volume'),('small bath','Lower water depth'),('large bath','Higher water depth'),('larger body','More displacement/contact'),('long body','Shape only; fixed volume/area'),('warmer skin','Skin at 36°C'),('cooler skin','Skin at 32°C')]:
 v=sc[key]['policy'];rows.append([key.title(),f'{v["water_l"]:.2f}' if v['feasible'] else 'No candidate',desc])
table(rows,[148,86,234])
para(f'At equal volume, the wide, shallow tub has a larger exposed top area and a changed diffusion length, and no candidate was accepted for it. The deep, narrow tub needs {sc["deep narrow"]["policy"]["water_l"]:.2f} L against {b["water_l"]:.2f} L, because a deep, narrow envelope reduces top-area heat loss, although a real deep bath may develop vertical stratification not resolved by a constant D. Geometry is therefore more than an interchangeable cooling coefficient.')
para(f'Changing depth at fixed length and width changes thermal storage and shell area. Greater water volume slows cooling, which can lower added water over a short fixed horizon: the large bath needs {sc["large bath"]["policy"]["water_l"]:.2f} L, while no candidate was accepted for the small bath. That does not mean a larger bath conserves total water: filling it initially uses more. J counts replenishment only, and this distinction prevents a misleading conservation claim.')
para('The larger-body scenario simultaneously displaces more water and increases assumed contact area; it is a combined size scenario and has no accepted candidate. The long-body scenario isolates the spatial distribution by keeping total body volume and contact area fixed. Warmer skin reduces the temperature difference driving body heat loss. These changes quantify conditional dependence; they do not establish measured human heat transfer.')
para('To transfer the model to a real tub, measure water volume after entry, submerged contact geometry, temperatures at several depths and distances, and no-inlet cooling. Shape and temperature should not be inferred from a single mean cooling curve.')

page('9. Motion and a bubble layer can change the policy')
rows=[['Scenario','Added water (L)','Search outcome']]
for key in ['weak mixing','strong mixing','moving with added surface loss','foam','tight comfort','loose comfort','low loss','high loss','cool supply']:
 v=sc[key]['policy'];rows.append([key.title(),f'{v["water_l"]:.2f}' if v['feasible'] else '—','Accepted' if v['feasible'] else 'None accepted'])
table(rows,[224,116,128])
para(f'Increasing D reduces the gradient created by the localized inlet. The strong-mixing scenario uses {sc["strong mixing"]["policy"]["water_l"]:.2f} L against {b["water_l"]:.2f} L, but motion may also increase heat loss. When D is increased together with a 20% increase in the surface coefficient (30 instead of 25 W/(m² K)), the need rises to {sc["moving with added surface loss"]["policy"]["water_l"]:.2f} L and most of the benefit disappears. The comparison deliberately separates transport improvement from its possible boundary cost.')
para(f'The foam scenario multiplies only the effective surface coefficient by 0.4. With all other inputs fixed, the best constant rate falls to {sc["foam"]["policy"]["water_l"]:.2f} L. The assumed 60% reduction is a scenario, not an experimentally established property of bubble-bath additive. If the layer breaks up or motion raises evaporation, this result must be recomputed.')
none=[k.title() for k,v in sc.items() if not v['policy']['feasible']]
para('No accepted candidate exists for: '+', '.join(none)+'. They are reported as such, not hidden in a favorable average. Their outcomes identify where the restricted strategy must change. Potential responses include improved circulation, a different inlet path, a shorter bath, or a different comfort tolerance. The paper does not certify which response is safe or optimal without corresponding physical evidence.')

page('10. Validation: independent evidence and remaining error')
figure('bounds.png','Figure 4. Water-use comparison under the same lower limit. The energy bound is conditional on the network assumptions; the feasible spatial result remains above it.',height=208)
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
para('Spearman rank correlations with water, over accepted draws: '+', '.join(f'{names_lr[k]} {v:+.2f}' for k,v in sorted(sp.items(),key=lambda kv:-abs(kv[1])))+'.')
para('The correlations use accepted draws only, so they understate inputs that push draws into infeasibility. The draws are uniform over ranges that we chose; they are not a probability distribution for any real tub. The main message is that the loss coefficients and the room temperature, not the mixing closure, decide how much water is needed, which is why Section 2 anchors them in outside evidence.')
para('A calibration plan should begin with an inlet-free cooling experiment, recording water volume and room conditions. Multiple temperature probes distinguish aggregate heat loss from mixing. A separate inlet experiment records flow and inlet/outlet temperatures, allowing overflow energy to be checked. Motion and foam need matched trials because both can alter transfer coefficients. Reserve an entire experiment for prediction checks after fitting. A single mean-temperature series cannot separate the surface, shell and body coefficients, so only calibrated and independently tested parameters would support advice for a particular bath.')

page('12. Conclusions and a policy with clear scope')
para(f'The model supports four linked findings. First, tolerating a modest temperature decline lets stored heat replace some inlet water. Second, spatial transport changes the ideal mixed recommendation: the best constant rate starts at once, and a schedule that withholds water at both ends needs {save:.0f}% less. Third, the water required is dominated by the surface and body loss coefficients: from {qq["0.05"]:.0f} to {qq["0.95"]:.0f} L across the literature-based ranges. Fourth, improving mixing helps only to the extent that it does not create offsetting boundary loss or hot-water short circuit.')
para(f'For the stated baseline, the best constant trickle is {b["flow_lpm"]:.3f} L/min for {b["water_l"]:.2f} L over 30 minutes; the {K}-segment schedule uses {ctl["water_l"]:.2f} L. These are the best accepted results of the documented searches, with all-cell constraints and independent numerical checks. Neither is a universal faucet prescription or a proved global optimum over all time-varying controls.')
para('The spatial model earns its complexity by explaining a disagreement with a proved simple benchmark and by rejecting strategies that a mean-only calculation would accept. Conservative accounting, anchored coefficients with stated ranges, a feasible-policy versus lower-bound gap, and an explicit refinement check make the recommendation inspectable.')
para('The limitations are consequential. Three-dimensional geometry is represented, but fluid momentum, buoyancy, jet entrainment, free-surface motion and detailed body anatomy are not solved. No bath experiment was conducted. Temperature limits express a preference assumption. Coarse cell averages cannot establish burn safety near the inlet, and the shape scenarios do not resolve stable vertical layers.')
para('Before using a numerical rate in practice, identify the real tub’s cooling and mixing behavior. Until then, the defensible transferable advice is to avoid unnecessary replenishment, distinguish cold-region temperature from the mean, improve distribution before increasing flow, and reconsider a strategy when geometry or motion changes. The following page translates these principles without requiring the user to interpret the equations.')

page('13. A warmer bath, with less replacement water')
para('A guide for the person in the bathtub','heading')
para(f'<b>Decide what “warm enough” means.</b> A bath need not stay at exactly its starting temperature to remain acceptable. In our example, allowing a 1°C fall still needs about {b["water_l"]:.0f} L of replacement water, while allowing a 2°C fall needs only {sc["loose comfort"]["policy"]["water_l"]:.1f} L. Your actual comfort and health needs must determine the acceptable range.')
para('<b>Distribute the warmth before turning up the tap.</b> The water near the faucet can warm while the far end remains cool. Gentle movement can help redistribute heat. More vigorous motion is not automatically better: it may also increase heat loss from the surface.')
para(f'<b>Run the tap in the middle, not at the ends.</b> For the tub and mixing conditions analyzed here, the least-water schedule adds no hot water for the first {lead*seg_min:g} minutes or the last {trail*seg_min:g} minutes and a steady stream in between; a constant trickle from the start used {100*(b["water_l"]/ctl["water_l"]-1):.0f}% more. In a bath that mixes very quickly, waiting until it has cooled slightly can save more. There is no single schedule that works for every tub.')
para('<b>Check more than one location.</b> A comfortable mean temperature can hide a cold far corner or a hot inlet region. Check the bath away from the faucet and at different depths. Do not use a model’s cell-average temperature as a reason to contact a hot jet.')
para('<b>Remember where the added water goes.</b> Once the tub is full, extra water leaves through the overflow. Hot water that runs along the surface to the overflow may escape before its warmth reaches you. Increasing the stream can waste heat without fixing unevenness.')
para('<b>A bubble layer may help, but the amount is uncertain.</b> An intact insulating surface layer can reduce heat loss. Our calculation explores such a layer; it does not measure the effect of a particular additive. If the layer disappears or the bath behaves differently, reassess rather than relying on the example’s saving.')
para('<b>The practical rule:</b> use the bath’s stored warmth, keep temperature distributed, and add only as much water as your actual conditions require. The numerical example explains these tradeoffs; it is not a tested bathing or safety standard.')

page('14. References and reproducible algorithm')
refs=[
'[1] COMAP. 2016 MCM Problem A: A Hot Bath. 2016. Official problem PDF: contest.comap.com/undergraduate/contests/mcm/contests/2016/problems/2016_MCM_Problem_A.pdf.',
'[2] U.S. Department of Energy. DOE Fundamentals Handbook: Thermodynamics, Heat Transfer, and Fluid Flow. DOE-HDBK-1012/2-92, June 1992. Convection heat transfer, Eq. (2-9).',
'[3] IAPWS. Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use. R6-95(2018). iapws.org/technical-guidance/release/IAPWS-95.',
'[4] SciPy developers. scipy.sparse.linalg.expm_multiply and scipy.integrate.solve_ivp, API documentation. docs.scipy.org/doc/scipy/reference/. Accessed 7 October 2026.',
'[5] Shannon, K. M. Judges’ Commentary: Hot Bath Problem. The UMAP Journal 37(3), 277–281, 2016. faculty.winthrop.edu/abernathyz/MathComps/2016_MCM_A-Com.pdf.',
'[6] Bergman, T. L., Lavine, A. S., Incropera, F. P., DeWitt, D. P. Fundamentals of Heat and Mass Transfer, 7th ed. Wiley, 2011. Natural convection above a heated horizontal surface (characteristic length A/P); heat and mass transfer analogy.',
'[7] Menzies, C., Clarke, N., Steward, C. J., Thake, C. D., Pugh, C. J. A., Cullen, T. Vascular, inflammatory and perceptual responses to hot water immersion: impacts of water depth and temperature in young healthy adults. Experimental Physiology, 2025. doi:10.1113/EP092761.',
'[8] OpenAI, Codex (GPT-6-based assistant), and Anthropic, Claude Sonnet 5.5 in Claude Code. Used on 7 October 2026 for modeling, code, validation and report composition; exact builds not independently established. See Report on Use of AI Tools.'
]
for ref in refs:para(escape(ref))
para('Algorithm and computational record','heading')
para('1. Form cell volumes and capacities; reject excessive body occupancy. Assemble symmetric face exchange, environmental/body conductances and the conservative stream. 2. Compute the mixed closed forms and energy lower bound. 3. Evaluate delayed constant-flow candidates with matrix exponentials and refine the first bracketed lower-temperature crossing. Reject spread or upper-limit violations. 4. Rank accepted candidates by added litres. 5. Independently integrate and check balances, analytic limits, parameter arithmetic and constraints; replay a finer mesh and perturb physical scenarios. 6. Optimize piecewise-constant schedules (multi-start SQP) and replay the best independently. 7. Rerun the constant-rate search at Sobol draws over the literature ranges. Independent RK45 checks use relative tolerance 2e-9, absolute 2e-10°C and steps of at most 5 s. The organization and practical page respond to the guidance in [5]; AI assistance is acknowledged in [8].')

names={'D':'D (m²/s)','h_surface':'surface coefficient (W/m²K)','foam':'surface multiplier','floor':'lower limit (°C)','L':'length (m)','W':'width (m)','H':'depth (m)','body_volume':'body displacement (m³)','body_area':'body contact area (m²)','body_shape':'body widths s (m)','body_temp':'skin temperature (°C)','h_wall':'wall coefficient (W/m²K)','h_body':'body coefficient (W/m²K)','inlet_temp':'inlet temperature (°C)'}
items=list(sc.items())
for part in range(2):
 page('Appendix A. Scenario definitions'+(' (continued)' if part else ''))
 para('Each row changes only the listed baseline inputs. All unspecified inputs remain as stated in Section 2; geometry and conductance are then rebuilt. The equal-volume aspect-ratio cases retain the envelope volume of 0.22425 m³. Widths s describe a smooth displacement distribution, not measured anatomical semiaxes.')
 rows=[['Scenario','Changed input(s)']]
 for label,item in items[part*9:(part+1)*9]:
  text='; '.join(names.get(k,k)+' = '+(str(v) if isinstance(v,list) else f'{v:.6g}') for k,v in item['changes'].items())
  rows.append([label.title(),text])
 table(rows,[144,324])
 para('Accepted candidates are independently replayed on their scenario network at intervals of no more than five seconds. These scenario checks are sampled checks; the stronger one-second continuous-time envelope is reported for the selected baseline policy only. “None accepted” refers to the documented finite search and is not an infeasibility theorem.')

page('Report on Use of AI Tools')
para('Tool and scope','heading')
para('OpenAI Codex, a GPT-6-based assistant, was used on 7 October 2026. The later revision (literature-based coefficients, schedule optimization, range analysis and rebuilding of this report) used Anthropic’s Claude, Sonnet 5.5, through Claude Code on the same date. The assistant selected the historical problem, located and read sources, formulated the mixed and spatial models, wrote and revised Python code, designed checks, interpreted numerical runs, generated figures, and drafted and typeset the English report. An assistant sub-agent wrote the independent-RHS validation routine; this is AI-assisted code review, not review by another human.')
para('Task','heading')
para('The task was to select a classic historical MCM problem and build a rigorous, professional case from it. The conversation wording is not reproduced in this report or in the development record.')
para('Outputs, corrections and verification','heading')
para('AI-produced outputs are the model, validation and report-building sources; the mathematical derivations, scenario tables, figures and text in this document. Numerical values came from actual Python runs. A weak-mixing policy search failed the imposed constraints and remains reported as such. An early continuous-time envelope failed; the flow-search reserve was increased from 0.01°C to 0.03°C before the accepted run. Citations [1]–[5] were checked against the linked sources; [6] was not opened (its correlations were checked against web summaries) and [7] was read as an abstract only. The first baseline coefficients and the 40.5°C upper limit were replaced after anchoring and mesh refinement.')
para('Record limitations','heading')
para('A full exported interaction transcript and every intermediate AI output were not available in this artifact. The task description, tool identification, scope, code artifacts and numerical receipts are retained in the accompanying development record; this report does not invent a transcript. No independent human review or physical bath experiment is claimed.')
para('Python, NumPy and SciPy performed the mathematics; Matplotlib generated plots and STIX vector formula outlines; ReportLab produced the PDF with embedded Times New Roman faces. These deterministic tools do not establish empirical validity. The service model/build beyond the available GPT-6-based identifier was not independently verified.')

TOTAL=pages
# Counting canvas with pages held in memory, so headers reflect final actual count.
from reportlab.pdfgen.canvas import Canvas
class Numbered(Canvas):
 def __init__(self,*x,**kw):super().__init__(*x,**kw);self.saved=[]
 def showPage(self):self.saved.append(dict(self.__dict__));self._startPage()
 def save(self):
  n=len(self.saved)
  for state in self.saved:
   self.__dict__.update(state);self.setFont('Text',12);self.drawString(72,758,'Team # '+TEAM_CONTROL_NUMBER);self.drawRightString(540,758,f'Page {self._pageNumber} of {n}');self.setLineWidth(.4);self.line(72,751,540,751);super().showPage()
  super().save()
path=ROOT/'submission'/(TEAM_CONTROL_NUMBER+'.pdf')
SimpleDocTemplate(str(path),pagesize=letter,leftMargin=72,rightMargin=72,topMargin=54,bottomMargin=54,title='A Hot Bath: Conserving Water Without Losing Uniformity',author='',pageCompression=1).build(flow,canvasmaker=Numbered)
(ROOT/'report-content.json').write_text(json.dumps(content,indent=2))
print(json.dumps({'pdf':str(path),'planned_pages':TOTAL,'equations':eqcount,'checks':len(checks)}))
