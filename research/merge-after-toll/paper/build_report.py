"""Build a complete baseline or revised paper from one frozen result JSON.
No solver is invoked here. Numerical prose, tables and figures share that input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.stats import t as student_t


def number(x, digits=0):
    return f'{x:,.{digits}f}'


def document(r, output):
    cfg=r['config']; improved=r['phase']=='improved'; b=r['baseline']
    pieces=[]
    def put(s): pieces.append(s+('\n\n' if not s.startswith('\\') and ' & ' not in s and not s.endswith('\\\\') else '\n'))
    def section(title): put(r'\section{'+title+'}')
    def table(caption, header, rows, cols=None, label=None):
        cols=cols or 'l'+'r'*(len(header)-1)
        put(r'\begin{table}[H]\centering\small\caption{'+caption+'}'+(r'\label{'+label+'}' if label else '')+r'\begin{tabular}{@{}'+cols+r'@{}}\toprule')
        put(' & '.join(header)+r'\\\midrule')
        for row in rows: put(' & '.join(str(x) for x in row)+r'\\')
        put(r'\bottomrule\end{tabular}\end{table}')
    def figure(caption, body, label):
        put(r'\begin{figure}[htbp]\centering\begin{tikzpicture}'+body+r'\end{tikzpicture}\caption{'+caption+r'}\label{'+label+r'}\end{figure}')
    def lineplot(xs, series, xlabel, ylabel, caption, label, ymin=0):
        body=r'\begin{axis}[width=.82\linewidth,height=5.2cm,scale only axis,axis lines=left,grid=major,grid style={gray!15},xlabel={'+xlabel+'},ylabel={'+ylabel+'},ymin='+str(ymin)+r',legend style={font=\footnotesize,draw=none,at={(.5,1.05)},anchor=south,legend columns=2},tick label style={font=\small},label style={font=\small}]'
        for name, ys, color, dash in series:
            body+=r'\addplot[thick,'+color+','+dash+r'] coordinates {'+' '.join(f'({x:.8g},{y:.8g})' for x,y in zip(xs,ys))+r'};\addlegendentry{'+name+'}'
        body+=r'\end{axis}'
        figure(caption,body,label)
    nominal=r['search']['nominal'] if improved else b
    robust=r['search']['robust'] if improved else b
    expanded=r['expansion'] if improved else None
    nomcap=nominal.get('capacities_vph',{}).get('nominal',b['capacity_vph'])
    robustcap=min(robust['capacities_vph'].values()) if improved else b['capacity_vph']
    put(r'''\documentclass[12pt,letterpaper]{article}
\usepackage[margin=1in,headheight=15pt]{geometry}
\usepackage{amsmath,amsthm}
\usepackage{newtxtext,newtxmath}
\usepackage{booktabs,array,microtype,fancyhdr,caption,float}
\usepackage{pgfplots}\pgfplotsset{compat=1.18}
\usetikzlibrary{arrows.meta,positioning,calc}
\usepackage[hidelinks]{hyperref}
\definecolor{main}{HTML}{0072B2}\definecolor{accent}{HTML}{D55E00}
\definecolor{green}{HTML}{009E73}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{Team 7391857}\fancyhead[R]{Merge After Toll}\fancyfoot[C]{\thepage}
\setlength{\emergencystretch}{2em}
\setlength{\parindent}{1.2em}\setlength{\parskip}{3pt}
\captionsetup{font=small,labelfont=bf}
\newtheorem{proposition}{Proposition}
\begin{document}
\thispagestyle{empty}
\noindent\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lcr}
Problem Chosen & 2017 MCM & Team Control Number\\
\Large B & \Large Summary Sheet & \Large 7391857
\end{tabular*}
\vspace{1.0em}
\begin{center}{\LARGE\bfseries Paying for the Bottleneck:\\[4pt] A Compatible-Flow Design for Toll-Plaza Merging}\end{center}
''')
    if improved:
        sim=lambda policy,scenario='nominal',load='heavy': next(x for x in r['simulations'] if x['policy']==policy and x['scenario']==scenario and x['load']==load)
        put('A wider toll barrier does not guarantee a faster exit. Drivers require compatible payment facilities, and the resulting streams must share a smaller set of travel lanes. We model these two constraints together, then size a smooth, order-preserving fan-in and examine finite queues.')
        put(f'The worked case has {cfg["booths"]} booths and {cfg["lanes"]} outgoing lanes. Pooling booth capacities gives an upper bound of {number(b["pooled_upper_vph"])} vehicles/hour, yet the initial arrangement sustains at most {number(b["capacity_vph"])} arriving vehicles/hour at the nominal payment composition. A payment-to-exit flow network exposes this gap. Its minimum-cut formula gives an exact capacity threshold within the model; an independently implemented maximum-flow calculation checks the threshold and a linear program supplies the routing rates.')
        totals=np.array(nominal['counts']).sum(axis=0)
        put(f'Enumerating {number(r["search"]["enumerated"])} clustered layouts yields a nominal design with {totals[0]} staffed, {totals[1]} exact-change and {totals[2]} electronic booths. Its threshold is {number(nomcap)} vehicles/hour, {number((nomcap/b["capacity_vph"]-1)*100,1)}\\% above the initial layout. A {number(nominal["recovery_length_m"],2)} m recovery zone precedes a {number(nominal["taper_length_m"])} m taper. The dimensions satisfy the stated kinematic constraints and a historical departure-zone screen; they do not estimate crash risk.')
        put(f'Payment uncertainty changes the decision. The best eight-booth layout guarantees a threshold of {number(robustcap,1)} vehicles/hour across the three declared mixtures, below the heavy demand of {number(cfg["heavy_vph"])} vehicles/hour. At least {sum(r["minimum_robust_counts"])} booths are necessary to cover that demand in all three mixtures with the assumed 12/6/2-second service means. A feasible expanded layout is constructed; its lowest scenario threshold is {number(min(expanded["capacities_vph"].values()),1)} vehicles/hour.')
        small=next(x for x in r['finite_buffers'] if x['slots']==16 and x['policy']=='expanded' and x['scenario']=='nominal')
        put(f'Across eight paired {number(cfg["horizon_s"]/60)}-minute demand episodes with unlimited downstream holding, mean waiting under nominal heavy traffic falls from {number(sim("baseline")["mean_delay_s"],1)} s to {number(sim("nominal")["mean_delay_s"],1)} s. Finite occupancy changes the expansion decision: with 16 downstream slots per exit group, vehicles in the longer expanded design wait {number(small["mean_delay_s"],1)} s on average. A traversal-occupancy bound explains why more booths need more downstream space. Shorter autonomous-vehicle headways cannot remove a payment bottleneck. Slower service defeats the eleven-booth guarantee; fourteen booths then become necessary, without a verified design at that count. We recommend matching booth mix, routing and holding space before expansion, then calibrating with site observations.')
    else:
        put(f'We examine a barrier with {cfg["booths"]} booths feeding {cfg["lanes"]} travel lanes. A first capacity calculation compares aggregate toll service with the exit lanes. It gives {number(b["pooled_upper_vph"])} vehicles/hour, but a separate payment-compatibility check limits the same arrangement to {number(b["type_upper_vph"])} vehicles/hour. Thus the pooled result cannot be used as a feasible operating recommendation.')
        put('A smooth fan-in connects each contiguous group of booths to an exit lane. Quintic lateral paths provide zero lateral velocity and acceleration at each end. Their maximum slope and acceleration determine a conditional minimum length. An exit headway rule separates successive discharges; it does not estimate crash frequency or model interactions inside the taper.')
        put(f'At light demand ({number(cfg["light_vph"])} vehicles/hour), average service capacity exceeds demand under the nominal payment mix. At heavy demand ({number(cfg["heavy_vph"])} vehicles/hour), staffed booths overload. Increasing automated-vehicle penetration can reduce exit headways, but cannot increase staffed-booth service. The next decision is therefore the number and assignment of payment-compatible booths, rather than simply a shorter taper or faster exit.')
        put('This baseline identifies the limiting mechanism but does not yet establish the best layout, finite-horizon delay or a design robust to payment shifts. The design recommendation is conditional: retain the smooth geometric concept, avoid treating pooled capacity as achievable, and resolve the payment allocation before selecting a construction option.')
    put(r'\noindent\textbf{Keywords:} toll plaza; compatible flow; minimum cut; queueing; geometric design.')
    put(r'\clearpage\tableofcontents\clearpage')
    section('The design question')
    put(r"The task is to design the departure side of a barrier toll, including its shape, dimensions and merging pattern, while balancing traffic throughput, accident prevention and construction cost \cite{comap}. We retain a general model with $B$ booths and $L<B$ exit lanes and examine the problem's eight-to-three example. Payment type and vehicle automation are different attributes: electronic toll collection does not imply an autonomous vehicle.")
    put('A useful design must explain why it improves on a plausible alternative. Our baseline uses a block of staffed booths, a block of exact-change booths and a block of electronic booths. Our proposed alternative distributes compatible service among channelized exit groups and controls release by the receiving lane. No claim of superiority over every existing real plaza is possible without local demand, geometry and compliance data.')
    table('How the requested decisions are answered.', ['Decision','Model or evidence'], [
        ['Shape, size and pattern','Smooth fan-in and contiguous exit groups'],
        ['Throughput and payment proportions','Compatible-flow network and cut threshold'],
        ['Accident prevention','Kinematic bounds and controlled discharge'],
        ['Cost','Pavement and equipment scenario; frontier'],
        ['Light/heavy demand','Finite queues with paired input streams' if improved else 'Capacity screening; delay not yet quantified'],
        ['Automated vehicles','Headway sensitivity with unchanged toll service']], cols=r'p{.32\linewidth}p{.61\linewidth}')
    section('Inputs, assumptions and scope')
    put(r'No site observations are supplied. Table~\ref{tab:inputs} states the service, cost and behavior assumptions used in the design scenarios; these inputs are not measurements from New Jersey. The official problem provides the task, while FHWA guidance motivates distinguishing model verification from field calibration \cite{fhwa}. We do not calibrate a traffic model by choosing parameters that make our design look favorable.')
    inputs=[['Booths / exit lanes',f'{cfg["booths"]} / {cfg["lanes"]}','Worked design'],
            ['Mean service: staffed / exact / ETC', ' / '.join(number(x,1) for x in cfg['mean_service_s'])+' s','Assumed service scenarios'],
            ['Service coefficients of variation',' / '.join(number(x,2) for x in cfg['service_cv']),'Lognormal service draws'],
            ['Human / AV--AV headway',f'{number(cfg["human_headway_s"],1)} / {number(cfg["av_pair_headway_s"],1)} s','Assumed exit control'],
            ['Travel-lane width',f'{number(cfg["lane_width_m"],1)} m','Geometric assumption'],
            ['Booth center spacing',f'{number(cfg.get("booth_pitch_m",cfg["lane_width_m"]),1)} m','Includes assumed island allowance'],
            ['Parallel recovery length',f'{number(cfg.get("recovery_length_m",0),2)} m','Historical guidance; assumed acceleration'],
            ['Departure speed',f'{number(cfg["departure_speed_m_s"],1)} m/s','Constant-speed path calculation'],
            ['Maximum slope / lateral acceleration',f'{number(cfg["max_path_slope"],2)} / {number(cfg["lateral_accel_m_s2"],1)} m/s$^2$','Scenario constraints'],
            ['Road construction',f'\\${number(cfg["road_cost_usd_m2"])} /m$^2$','Cost scenario; excludes land purchase'],
            ['Demand: light / heavy',f'{number(cfg["light_vph"])} / {number(cfg["heavy_vph"])} veh/h','30-minute demand episodes']]
    table('Scenario inputs and their status.', ['Input','Value','Interpretation'],inputs,cols=r'p{.34\linewidth}p{.25\linewidth}p{.32\linewidth}',label='tab:inputs')
    put('Vehicles retain their payment class during a visit. Within each class, signs or advance assignment direct vehicles to compatible booths. Booths assigned to an exit group form a contiguous block, and vehicles do not cross group boundaries after payment. The capacity certificate assumes adequate approach capacity and unlimited downstream holding. We test the latter assumption separately with a finite-occupancy blocking model. Neither version is a calibrated car-following simulation.')
    rows=[[name.replace('_',' '), *[number(x*100,0)+r'\%' for x in shares]] for name,shares in cfg['payment_scenarios'].items()]
    table('Demand proportions, independent of booth proportions.', ['Scenario','Staffed','Exact','ETC'],rows)
    put(r'Let $n_{gt}$ be the number of booths of payment type $t$ assigned to exit group $g$, $\mu_t=3600/s_t$ the mean booth service rate in vehicles/hour, and $p_t$ the proportion of arriving vehicles requiring type $t$. The arrival rate is $\lambda$; $C_g$ is the discharge capacity of exit $g$. A layout satisfies $n_{gt}\in\mathbb Z_{\ge0}$, $\sum_{g,t}n_{gt}=B$, and every exit group and payment class is nonempty in the worked search.')
    section('Why aggregate capacity is not a design')
    put(r'A pooled estimate is the upper bound $U=\min(\sum_{g,t}n_{gt}\mu_t,\sum_g C_g)$. It ignores whether the arriving drivers can use the available service. Every payment class separately requires $\lambda p_t\le\mu_t\sum_g n_{gt}$.')
    put(f'The baseline has booth totals '+ '/'.join(str(int(x)) for x in np.array(b['counts']).sum(axis=0))+f'. Its pooled bound is {number(b["pooled_upper_vph"])} vehicles/hour, whereas the payment bound is {number(b["type_upper_vph"])} vehicles/hour. In particular, staffed service supplies {number(np.array(b["counts"]).sum(axis=0)[0]*3600/cfg["mean_service_s"][0])} vehicles/hour, which must serve {number(cfg["payment_scenarios"]["nominal"][0]*100)}\\% of arrivals. Extra unused electronic capacity does not serve that queue.')
    put('This is one structural failure, not several unrelated numerical errors. It changes the throughput claim, the heavy-traffic interpretation and the preferred booth mix. A design based only on the pooled number would therefore need to be revised in all three places.')
    section('A compatible-flow capacity certificate')
    put(r'For a specified layout, let $x_{gt}$ be the rate of type-$t$ vehicles sent through group $g$. Feasible routing satisfies')
    put(r'''\begin{align}
0\le x_{gt}&\le n_{gt}\mu_t, &\sum_g x_{gt}&=\lambda p_t, &\sum_t x_{gt}&\le C_g. \label{eq:flow}
\end{align}''')
    put(r'Construct a directed network with source-to-type arcs of capacity $\lambda p_t$, type-to-group arcs $n_{gt}\mu_t$, and group-to-sink arcs $C_g$. The constraints hold exactly when the maximum flow equals $\lambda$. This representation preserves both payment compatibility and lane capacity.')
    put(r'''\begin{proposition}
For $p_t>0$, the largest feasible fluid rate in this network is
\begin{equation}
\lambda^*(n,p,C)=\min_{\varnothing\ne S\subseteq\{1,\ldots,T\}}
\frac{\sum_g\min\{C_g,\sum_{t\in S}n_{gt}\mu_t\}}{\sum_{t\in S}p_t}.\label{eq:cut}
\end{equation}
\end{proposition}
\begin{proof}
Fix the set $S$ of type nodes on the source side of a cut. The source arcs of all other types contribute $\lambda(1-p(S))$. For each group, placing it on the sink side cuts the type-to-group arcs from $S$, while placing it on the source side cuts its exit arc. The least contribution is therefore $\min(C_g,\sum_{t\in S}n_{gt}\mu_t)$. Every cut has capacity at least $\lambda$ precisely when the inequalities in \eqref{eq:cut} hold. The empty set imposes no restriction. The maximum-flow/minimum-cut theorem then gives sufficiency as well as necessity.
\end{proof}''')
    put(r'With three payment classes, only seven reduced cuts are needed per layout. A linear program constructs the rates $x_{gt}$ after selection. Equation~\eqref{eq:cut} limits sustainable arrivals of a specified payment composition. It is not an upper bound on departures in every finite time window: queued vehicles can change the payment composition of completed traffic. Under random arrivals and service, equality is not a finite-delay guarantee; stable operation needs slack.')
    if not improved:
        put('The certificate gives a route to improve the baseline, but this draft does not yet enumerate layouts or quantify queue delays. It supports the rejection of the pooled recommendation, not an assertion that an optimal construction design has been found.')
    section('Smooth geometry and controlled merging')
    if improved:
        put(r'The archived FHWA departure guidance recommends a recovery area of at least 200 ft, preferably 300 ft, before the transition \cite{departure}. We use the preferred 300 ft (91.44 m), retaining parallel trajectories there. At the assumed $1\,\mathrm{m/s^2}$ acceleration, a vehicle leaving a cash booth from rest reaches the longitudinal taper speed within this recovery area. The ETC path starts at that speed. The recovery length is not proof of adequate queue storage.')
    put(r'Place booth centers $y_i^0$ at the chosen booth spacing, and exit centers $y_g^1$ at the travel-lane spacing. Contiguous groups preserve the left-to-right order of destinations. Measure $x$ from the start of the taper, after recovery. Over taper distance $D$, define $u=x/D$ and')
    put(r'''\begin{equation}
y_i(x)=y_i^0+(y_{g(i)}^1-y_i^0)f(u),\qquad
f(u)=10u^3-15u^4+6u^5.\label{eq:path}
\end{equation}''')
    put(r'The first and second lateral derivatives vanish at both ends. Since $0\le f(u)\le1$, two ordered start points with ordered destinations remain ordered for every $x$: their separation is a convex combination of their initial and final separation. This rules out path crossings between groups in the idealized geometry. Paths within a group converge, so timed release is still needed; ordered centerlines alone do not prevent vehicle collisions.')
    put(r'For $d_{\max}=\max_i|y_{g(i)}^1-y_i^0|$, $\max f\prime=15/8$ and $\max|f\prime\prime|=10\sqrt3/3$. At constant longitudinal speed $v$, slope limit $m$ and lateral acceleration limit $a_y$ imply')
    put(r'''\begin{equation}
D\ge\max\left(\frac{15d_{\max}}{8m},\;v\sqrt{\frac{10\sqrt3\,d_{\max}}{3a_y}}\right).\label{eq:length}
\end{equation}''')
    put('We round the taper lower bound upward to the next five meters. Road edges use the same transition function between barrier and exit widths. Their taper area is length times mean width; the parallel recovery area must be added separately. The design is therefore a recovery section followed by a curved taper.')
    if improved:
        put(r'For conventional departure speeds up to 40 mph, the same historical guidance gives $D_{\rm ft}\ge W_{\rm ft}(1.5S_{\rm mph}^2/105+5)$ \cite{departure}. We use the edge offset $W=(Bw_b-Lw)/2$ and take the larger of this screen and \eqref{eq:length}. This is not an assertion of current, complete engineering compliance. Dedicated non-stop lanes and site-specific sight distance require their own applicable checks.')
    put(r'Each exit group has a discharge order and headway $h$, giving $C_g=3600/h$. Signs identify payment-compatible routes before the barrier, markings maintain groups, and entry metering coordinates the merging streams and separates exit discharges. Vehicle lengths, emergency braking, sight distance and interactions within the taper remain unresolved. Finite occupancy tests blocking at the booths; it does not verify collision avoidance.')
    if improved:
        put(r'Waiting can be placed before the taper rather than inside the merging paths. Let $r_k$ be the time a vehicle is ready after recovery, ordered within its group, and let $T=D/v$ be the common taper travel time. Meter entry by $e_k=\max(r_k,e_{k-1}+h)$. Then $d_k=e_k+T=\max(r_k+T,d_{k-1}+h)$, exactly the discharge recurrence used below. With a shared constant longitudinal speed, two successive vehicles in that group remain at least $vh$ apart in the taper. As an illustrative passenger-car condition, a 5 m vehicle plus 2 m clearance requires $vh\ge7$ m; at 10 m/s even the shortest assumed 0.9 s headway gives 9 m. This is a conditional spacing certificate, not a braking or crash-risk model. It excludes heavy vehicles, cross-group body envelopes and the physical arrangement of the entrance queues. Downstream occupancy still includes entrance waiting, so the equivalence does not create free holding space.')
    design=nominal
    recovery=design.get('recovery_length_m',0)
    taper=design.get('taper_length_m',design['length_m'])
    xs=np.linspace(0,design['length_m'],81); u=np.clip((xs-recovery)/taper,0,1); f=10*u**3-15*u**4+6*u**5
    body=r'\begin{axis}[width=.84\linewidth,height=5.0cm,scale only axis,xlabel={Distance after barrier (m)},ylabel={Lateral position (m)},axis lines=left,grid=major,grid style={gray!15},tick label style={font=\small},label style={font=\small}]'
    colors=['main','green','accent']; labelsdone=set()
    for a,z in zip(design['booth_start_y_m'],design['exit_y_m']):
        g=sorted(set(design['exit_y_m'])).index(z)
        body+=r'\addplot[thick,'+colors[g]+r',no marks'+(',forget plot' if g in labelsdone else '')+r'] coordinates {'+' '.join(f'({x:.4f},{y:.5f})' for x,y in zip(xs,a+(z-a)*f))+r'};'
        if g not in labelsdone: body+=r'\addlegendentry{Exit '+str(g+1)+'}';labelsdone.add(g)
    body+=r'\end{axis}'
    figure('Order-preserving centerline paths for the selected '+('nominal design' if improved else 'baseline')+'. Curves within one group merge at its assigned exit. Release spacing is a separate control requirement.',body,'fig:paths')
    if improved:
        section('Layout selection and construction trade-offs')
        put(f'We enumerate {number(r["search"]["enumerated"])} layouts with payment types clustered in the order ETC, exact-change, staffed, and contiguous exit groups. The ETC-left convention follows the historical mainline guidance \\cite{{orientation}}. An unrestricted comparison of {number(r["unrestricted_search"]["enumerated"])} matrices attains the same nominal and worst-case optimum thresholds for these inputs, so clustering sacrifices no capacity optimum here. This equivalence is not asserted for other demand or geometry scenarios. Ties minimize capital cost, then the largest number of streams feeding one exit.')
        put(r'The cost scenario is $K_c=c_A A+\sum_t k_t N_t$, where $A=RBw_b+D(Bw_b+Lw)/2$ includes recovery and taper pavement. Equipment assumptions for staffed, exact-change and electronic booths are '+', '.join('\\$'+number(x) for x in cfg['equipment_cost_usd'])+'. This full-build comparison excludes land acquisition, shoulders, maintenance, staffing and discounting. It cannot establish investment return or a final construction budget; land opportunity cost is added in the scenarios below.')
        policies={'Initial':b,'Nominal':nominal,'Robust':robust,'Expanded':expanded}
        rows=[]
        for name,d in policies.items():
            caps=d.get('capacities_vph',{'nominal':b['capacity_vph']})
            counts=np.array(d['counts']).sum(axis=0)
            rows.append([name,'/'.join(str(int(x)) for x in counts),number(d['length_m'],2),number(d['capital_usd']/1e6,3),number(caps['nominal']),number(min(caps.values()),1) if len(caps)>1 else '--'])
        table('Capacity and capital scenarios. Counts are staffed/exact/ETC; length includes recovery and taper. Rate columns are fluid arrival thresholds (veh/h).', ['Design','Counts','Length (m)','Cost (\\$m)','Nominal','Worst'],rows,cols='llrrrr',label='tab:design')
        put(f'The nominal design increases the threshold from {number(b["capacity_vph"])} to {number(nomcap)} vehicles/hour. Relative to the nominal design, the robust design retains that nominal threshold and raises the electronic-heavy threshold from {number(nominal["capacities_vph"]["electronic_heavy"])} to {number(robust["capacities_vph"]["electronic_heavy"])} vehicles/hour, at an additional assumed capital cost of \\${number(robust["capital_usd"]-nominal["capital_usd"])}. It cannot remove the cash-heavy bottleneck.')
        table('Contiguous exit groups of the nominal and robust designs.', ['Design / group','Staffed','Exact','ETC'], [[name+f' / {g+1}',*row] for name,d in [('Nominal',nominal),('Robust',robust)] for g,row in enumerate(d['counts'])])
        pts=r['search']['frontier']
        lineplot([p[0]/1e6 for p in pts],[('Eight-booth frontier',[p[1] for p in pts],'main','mark=*')],
                 'Scenario capital cost (million USD)','Worst-case threshold (veh/h)',
                 'Nondominated cost/capacity points within the enumerated eight-booth family. Different land prices or admissible routing rules can change this frontier.','fig:frontier')
        landrows=[]
        for name in ['nominal','robust','expanded']:
            landrows.append([name,number(policies[{'nominal':'Nominal','robust':'Robust','expanded':'Expanded'}[name]]['area_m2'],2),*[number(x['total_capital_usd']/1e6,3) for x in r['land_cost_scenarios'][name]]])
        table('Land opportunity-cost scenarios added to road and equipment costs. Column prices are USD/m$^2$: illustrative assumptions, not local quotations. Totals are in millions of USD.', ['Design','Area (m$^2$)','0','200','1000'],landrows,cols='lrrrr')
        extra_area=expanded['area_m2']-robust['area_m2']
        put(f'Expansion needs {number(extra_area,2)} m$^2$ more modeled pavement footprint than the robust eight-booth option. Each additional dollar per square meter of land opportunity cost therefore adds \\${number(extra_area,2)} to the expansion premium. Equal-area eight-booth designs retain their equipment-cost difference, while higher land cost makes expansion more expensive. Without project life, traffic revenue or a delay valuation, these scenarios cannot establish an investment break-even point. The footprint still excludes shoulders and approach-side land.')
        section('An infeasibility result and a feasible expansion')
        put(r'For a target demand $q$, a necessary condition under every payment mixture is $N_t\mu_t\ge q\max_s p_{st}$. Therefore $N_t\ge\lceil q\max_s p_{st}/\mu_t\rceil$. This gives a lower bound independent of lane routing and geometric preferences.')
        needed=r['minimum_robust_counts']
        put(f'At {number(cfg["heavy_vph"])} vehicles/hour, the three type minima are '+', '.join(str(x) for x in needed)+f' booths, totaling {sum(needed)}. Hence no eight-, nine- or ten-booth arrangement with the same service capabilities can accommodate all three mixtures. This is stronger than failing to find a good layout: the payment requirements alone exclude those totals.')
        put(f'A layout with those {sum(needed)} booths and {cfg["lanes"]} exits is feasible. Its scenario thresholds are '+', '.join(f'{name.replace("_"," ")}: {number(cap,1)} vehicles/hour' for name,cap in expanded['capacities_vph'].items())+f'. Its departure zone, including recovery and taper, is {number(expanded["length_m"],2)} m long, with assumed full-build cost \\${number(expanded["capital_usd"])}. We search only allocations of the necessary booth-count vector for this expansion; the capacity certificate proves feasibility, while the smallest count follows from the lower bound. We do not claim minimum cost over all larger facilities or all road geometries.')
        put(f'The robust eight-booth threshold is {number(robustcap,1)} vehicles/hour. A rate strictly above it would require at least five staffed, two exact-change and two electronic booths under the declared scenario maxima, exceeding eight in total. The selected design reaches the bound in the fluid model. The nominal threshold is likewise conditional on the three service means and nominal shares, rather than a universal property of eight booths.')
        section('Light and heavy traffic: finite-episode queues')
        put(f'Arrivals form a Poisson stream for {number(cfg["horizon_s"]/60)} minutes and are then stopped while the queues drain. Payment types are independent marks with the specified scenario probabilities. Lognormal service times preserve the assumed means and coefficients of variation. For each scenario/load combination we use the same arrivals, payment marks, service draws and routing uniforms across all designs. The eight preselected seeds are '+', '.join(str(s) for s in cfg['seeds'])+'. These replications quantify variation in the model, not uncertainty about real traffic.')
        put(r"The LP routing witness gives each compatible booth a fixed fraction of its type demand. A booth is a single server. After service and recovery, a vehicle travels the taper and joins its receiving lane; discharge times satisfy $d_k=\max(a_k,d_{k-1}+h)$, where $a_k=r_k+T$ is the free-arrival time at the taper end. Total waiting excludes the vehicle's realized service and free recovery/traversal time. All arrivals are retained through clearance, so vehicles remaining at the demand horizon are not dropped. This section first assumes unlimited holding; the next tests blocking.")
        rows=[]
        for scenario in cfg['payment_scenarios']:
            for policy in ['baseline','nominal','robust','expanded']:
                light=sim(policy,scenario,'light'); heavy=sim(policy,scenario,'heavy')
                rows.append([scenario.replace('_',' ') if policy=='baseline' else '',policy,number(light['mean_delay_s'],1),number(heavy['mean_delay_s'],1),number(heavy['mean_output_vph']),number(heavy['mean_clearance_s'],1)])
        table('Eight-replication means with unlimited holding. Waiting includes arrivals through drainage; output and clearance refer to heavy demand. Output counts only demand-window departures. Wait and clearance are in seconds; output is in veh/h.', ['Payment mix','Design','Light wait','Heavy wait','Output','Clearance'],rows,cols='llrrrr',label='tab:queues')
        put(f'Under nominal heavy demand, mean waiting decreases from {number(sim("baseline")["mean_delay_s"],1)} s to {number(sim("nominal")["mean_delay_s"],1)} s. Under cash-heavy demand, even the robust eight-booth option has mean waiting {number(sim("robust","cash_heavy")["mean_delay_s"],1)} s because demand exceeds its threshold; finite simulation cannot convert overload into stability. The expanded layout reduces that mean to {number(sim("expanded","cash_heavy")["mean_delay_s"],1)} s, but the remaining wait warns against operating close to capacity.')
        # Paired uncertainty is over replication differences, not independent-arm SE.
        base=np.array([x['mean_delay_s'] for x in sim('baseline')['replicas']]); cand=np.array([x['mean_delay_s'] for x in sim('nominal')['replicas']])
        differences=base-cand
        se=float(differences.std(ddof=1)/np.sqrt(len(differences)))
        half=float(student_t.ppf(.975,len(differences)-1))*se
        put(f'The paired nominal-heavy mean reduction is {number(differences.mean(),1)} s, with an approximate 95\\% Student-$t$ interval [{number(differences.mean()-half,1)}, {number(differences.mean()+half,1)}] s over the eight replications. This interval describes Monte Carlo variation under the model, not uncertainty in service means, driver compliance or road behavior. Light-traffic differences are much smaller, so this improvement is not a uniform reduction for every operating condition.')
        section('When additional booths make blocking worse')
        put(r'Let $K$ be the number of downstream occupancy slots in each exit group, counting vehicles from toll release until exit, including travel and waiting. If the group is full, a vehicle that has completed service remains at its booth, preventing the next service. Once a vehicle exits, the earliest blocked completion is admitted. Thus finite occupancy can reduce toll service itself. The slots are an abstract resource, not a calibrated geometric vehicle count; the event model still does not resolve lane-changing collisions.')
        put(r'For free traversal times $\tau_t$, a stationary rate requires $\sum_t x_{gt}\tau_t/3600\le K$ for every group, because waiting can only increase occupancy. Minimizing $K$ over \eqref{eq:flow} gives a necessary holding bound. It excludes waiting and stochastic bursts, so satisfying it is not sufficient. Conversely, a design below this bound cannot sustain the target rate under the modeled travel times, regardless of routing.')
        boundrows=[]
        for name in ['robust','expanded']:
            for scenario,record in r['occupancy_bounds'][name].items():
                value=record['continuous_lower_bound']
                boundrows.append([name,scenario.replace('_',' '),'infeasible service demand' if value is None else number(value,4),'--' if value is None else record['rounded_necessary_slots']])
        table('Necessary per-group occupancy at the heavy demand. Infeasible service demand means no amount of holding fixes the payment constraint.', ['Design','Payment mix','Continuous lower bound','Integer minimum'],boundrows,cols='llrr')
        rows=[]
        for slots in cfg['finite_occupancy_slots']:
            for scenario in cfg['payment_scenarios']:
                entries={x['policy']:x for x in r['finite_buffers'] if x['slots']==slots and x['scenario']==scenario}
                rows.append([slots,scenario.replace('_',' '),number(entries['robust']['mean_delay_s'],1),number(entries['expanded']['mean_delay_s'],1),number(entries['expanded']['mean_output_vph'])])
        table('Finite-occupancy heavy-demand experiments, eight paired seeds. The eight-booth column uses the robust design. Waiting covers drainage; output covers the demand window.', ['$K$','Payment mix','8-booth wait (s)','11-booth wait (s)','11-booth output'],rows,cols='rlrrr')
        frow=lambda name,slots,scenario='nominal':next(x for x in r['finite_buffers'] if x['policy']==name and x['slots']==slots and x['scenario']==scenario)
        put(f'At $K=16$, nominal heavy-traffic waiting is {number(frow("robust",16)["mean_delay_s"],1)} s for the robust eight-booth design but {number(frow("expanded",16)["mean_delay_s"],1)} s for the expansion. At $K=64$, the expansion wait falls to {number(frow("expanded",64)["mean_delay_s"],1)} s. More booths require a wider and longer taper; vehicles occupy the downstream corridor longer, so expansion without matching holding resources can worsen delay. This is a conditional queueing mechanism, not an empirical prediction for a particular plaza.')
        lineplot(cfg['finite_occupancy_slots'],[(name,[frow(name,k)['mean_output_vph'] for k in cfg['finite_occupancy_slots']],color,dash) for name,color,dash in [('robust','main','mark=*'),('expanded','accent','dashed,mark=square*')]],'Occupancy slots per group','Demand-window output (veh/h)','Nominal heavy-demand output with finite occupancy. These are transient observed rates, distinct from the compatible-flow arrival thresholds.','fig:buffers')
        put('We also tested an actual-demand minimax resource-load routing objective. It slightly improves some conditions but worsens nominal-design waiting in the cash-heavy overload case. A smaller maximum utilization is therefore not equivalent to smaller mean waiting. We retain the capacity-witness routing for this comparison and archive the rejected candidate; no claim of minimum-delay routing is made.')
        section('Automated vehicles and sensitivity of the recommendation')
        put(r'Let $a$ be the autonomous-vehicle fraction. If neighboring vehicle types are independently mixed and only an AV--AV pair uses the shorter headway, the scenario mean is $h(a)=h_H(1-a^2)+h_Aa^2$. No toll-service advantage is granted merely because a vehicle is autonomous. This isolates whether the bottleneck is at the payment barrier or the receiving lanes; real platooning or different mixed-pair behavior would require another headway model.')
        avrows=[]
        for av in cfg['av_shares']:
            entries=[x for x in r['automation'] if x['av_share']==av]
            avrows.append([number(av*100)+r'\%',number(entries[0]['headway_s'],3),*[number(next(x for x in entries if x['policy']==name)['capacity_vph']) for name in ['baseline','nominal','robust','expanded']]])
        table('Nominal-payment thresholds as AV share changes. All booths and toll-service assumptions stay fixed.', ['AV share','Headway (s)','Initial','Nominal','Robust','Expanded'],avrows)
        lineplot([a*100 for a in cfg['av_shares']],[(name,[next(x for x in r['automation'] if x['policy']==name and x['av_share']==a)['capacity_vph'] for a in cfg['av_shares']],color,dash) for name,color,dash in [('baseline','accent','dashed'),('nominal','main','solid'),('expanded','green','densely dotted')]],'Autonomous-vehicle share (\\%)','Nominal threshold (veh/h)',
                 'Headway improvement matters only when an exit-related cut is limiting. A flat curve means that the service/compatibility bottleneck remains.','fig:av')
        put('The initial layout and nominal eight-booth design are payment-limited across these nominal AV scenarios. An autonomous fleet can therefore increase receiving-lane capability without improving their total threshold. This does not mean automation has no safety or operational value; those outcomes are outside the capacity calculation. It means automation alone is not the remedy for this specified service bottleneck.')
        put(r'Equation~\eqref{eq:cut} also supplies exact payment-share thresholds. Holding all else fixed, a set $S$ overloads once $p(S)>\sum_g\min(C_g,\sum_{t\in S}n_{gt}\mu_t)/q$. Such inequalities are actionable: before adding pavement, measure the relevant payment proportions and test which cut is active. The scenario frontier should be recomputed when mean service or allowed routing changes. The sensitivity calculation uses the mean headway as a deterministic exit interval; it does not simulate AV pair sequences or platoon correlations. A monetary preference between robustness and lower cost remains a decision for the authority, not a number inferred from a synthetic objective.')
        stressrows=[[name,*[number(r['service_stress'][name][scenario],1) for scenario in cfg['payment_scenarios']]] for name in ['baseline','nominal','robust','expanded']]
        table('Slower-service stress test: conditional thresholds (veh/h). The layouts are held fixed, not reoptimized.', ['Design','Nominal mix','Cash-heavy','Electronic-heavy'],stressrows)
        put('With assumed service means of '+ '/'.join(number(x,0) for x in cfg['service_stress_s'])+' seconds, the expanded layout no longer meets heavy demand in every mixture. The payment-only lower count becomes '+ '/'.join(str(x) for x in r['stressed_minimum_robust_counts'])+f' booths, totaling {sum(r["stressed_minimum_robust_counts"])}. This stress calculation establishes a necessary count only; no layout at that count has been constructed or checked. The eleven-booth recommendation is conditional on the original service scenario.')
        section('Verification, strengths and remaining limits')
        put('An independent network-flow implementation checks every reported selected-layout threshold at the threshold and one vehicle/hour above it. The routing witnesses are checked for payment conservation, booth bounds and exit bounds. A separate exhaustive search over type totals verifies the minimum robust booth count. Analytic derivative maxima establish the path bounds, with dense numerical samples checking the generated geometry and its ordering. The queue experiment checks vehicle conservation and retains residual queues through clearance.')
        put('A separate reviewer implementation compared 256 randomized cut calculations with an independently formulated LP, checked queue examples by hand, and reproduced unlimited holding with nonbinding finite occupancy. An analytic payment-subset occupancy bound and explicit feasible routing independently attain each expanded-layout slot lower bound. These are author-external agent checks within the same model family, not human or field verification. Entry and exit metering equivalence was checked against finite-event traces without changing the numerical trajectories.')
        put('These checks have different scopes. A maximum-flow calculation verifies the conditional network result; it cannot show that drivers obey route guidance. A geometrically ordered set of centerlines does not constitute a crash model. Replication consistency cannot supply calibration data. FHWA describes calibration against capacity and performance observations; our report has no such observations and therefore does not describe the model as field-validated \\cite{fhwa}.')
        put('The main strength is an interpretable bottleneck certificate linking payment mix to lane design. It both constructs feasible improvements and proves when a requested demand cannot be served with the given booth count. The main weakness is the absence of site calibration and a spatial interaction model. Finite occupancy and simple acceleration are now included, but the occupancy slots have not been mapped to safe physical storage. Open-loop routing, heavy vehicles, driver compliance and land constraints can change a practical preference even when the flow inequalities remain correct.')
    section('Recommendation')
    if improved:
        put(f'For the nominal payment mixture, choose the {number(nomcap)}-vehicle/hour layout when capital is the main secondary criterion. If payment proportions may shift toward electronic collection, the robust eight-booth alternative buys broader service compatibility for an assumed \\${number(robust["capital_usd"]-nominal["capital_usd"])} increase. Neither option is a reliable way to serve {number(cfg["heavy_vph"])} vehicles/hour under the cash-heavy mixture. For that service requirement across all three mixtures, the model requires at least {sum(r["minimum_robust_counts"])} booths and supplies one feasible allocation.')
        put(f'Expansion is conditional on matching downstream space: in nominal heavy traffic, the eleven-booth design waits {number(frow("expanded",16)["mean_delay_s"],1)} s at 16 slots per group, compared with {number(frow("robust",16)["mean_delay_s"],1)} s for the robust eight-booth design. Slower service also defeats the eleven-booth guarantee. Neither booth count nor a necessary occupancy bound alone is a construction specification.')
        put('Use channelized, order-preserving fan-in paths and a receiving-lane discharge rule, but validate holding space and vehicle interactions before fixing the construction drawing. Collect observed payment shares, service distributions and queue discharge rates before selecting the final booth mix. The most valuable operational change is the one that relaxes the active bottleneck; extra exit capacity is ineffective while the payment cut remains binding.')
    else:
        put('Do not build or operate to the pooled capacity estimate. Staffed service is the first bottleneck to investigate. A payment-aware allocation, compared under light and heavy traffic and checked against finite storage, is needed before choosing a preferred layout. The smooth taper gives an explicit geometric starting point, while its safety interpretation remains limited to the stated kinematics.')
    put(r'''\clearpage\section*{Letter to the New Jersey Turnpike Authority}
\addcontentsline{toc}{section}{Letter to the New Jersey Turnpike Authority}
\noindent Dear Members of the Authority,
''')
    put('We recommend treating a toll plaza as a set of payment-compatible services connected to receiving traffic lanes. The number of open booths by itself can be misleading: unused electronic capacity cannot process a driver who requires a staffed booth. The operating plan should identify the limiting payment or exit group before adding pavement or changing discharge speeds.')
    if improved:
        put(f'For the illustrative eight-booth, three-lane facility, our nominal arrangement raises the modeled capacity threshold from {number(b["capacity_vph"])} to {number(nomcap)} vehicles per hour. It uses '+ '/'.join(str(int(x)) for x in np.array(nominal['counts']).sum(axis=0))+' staffed/exact-change/electronic booths, allocated among contiguous exit groups. Each group receives compatible demand and is metered at the taper entrance. A parallel recovery section of '+number(nominal['recovery_length_m'],2)+' meters precedes a smooth taper of '+number(nominal['taper_length_m'])+' meters, which meets our assumed slope and lateral-acceleration limits at '+number(cfg['departure_speed_m_s'])+' meters per second.')
        put(f'The nominal design is not the best choice for every payment mixture. An eight-booth robust alternative costs an additional assumed \\${number(robust["capital_usd"]-nominal["capital_usd"])} and handles an electronic-heavy mixture better. Under cash-heavy demand, however, every eight-booth design remains limited. Serving {number(cfg["heavy_vph"])} vehicles per hour under all three studied mixtures requires at least {sum(r["minimum_robust_counts"])} booths with the stated service capabilities. We provide a feasible expanded arrangement rather than suggesting that shorter headways alone can solve this constraint.')
        put(f'In the nominal heavy-traffic experiments, mean waiting falls from {number(sim("baseline")["mean_delay_s"],1)} to {number(sim("nominal")["mean_delay_s"],1)} seconds. These figures come from specified synthetic demand episodes, not observations of your road. They identify a promising change to test; they are not forecasts of achieved delay or accident reduction.')
        put(f'Expansion also lengthens traversal. At 16 downstream slots per group, its nominal heavy-traffic waiting rises to {number(frow("expanded",16)["mean_delay_s"],1)} seconds, above the robust eight-booth alternative. At 64 slots per group, the expanded design\'s nominal heavy-traffic mean waiting falls to {number(frow("expanded",64)["mean_delay_s"],1)} seconds, removing this particular modeled penalty in the tested scenario. We therefore recommend testing a combined booth-and-storage plan rather than approving extra booths in isolation.')
    else:
        put(f'Our initial calculation finds that the pooled {number(b["pooled_upper_vph"])}-vehicle/hour figure overstates what the current payment mix can use. The staffed-booth restriction gives only {number(b["type_upper_vph"])} vehicles per hour for the baseline arrangement. Heavy demand of {number(cfg["heavy_vph"])} vehicles per hour therefore cannot be accommodated indefinitely. More favorable exit headways alone do not remove this payment bottleneck.')
        put('We propose a smooth, channelized fan-in and payment-aware allocation as the next design step. We have not yet quantified finite queues or established the preferred booth mix; a construction commitment should wait for that comparison and local measurements.')
    put('Before construction, price the required land, measure payment proportions and service times, test whether drivers follow route guidance, and check finite holding space and vehicle trajectories. Our idealized centerlines and release intervals address specific kinematic concerns, but do not estimate crashes or replace engineering standards. A pilot can first change signs and booth assignments; major pavement expansion should follow only when the observed limiting mechanism justifies it.')
    put(r'\noindent Respectfully,\\Team 7391857')
    put(r'''\clearpage
\begin{thebibliography}{9}
\bibitem{comap} COMAP. 2017 MCM Problem B: Merge After Toll. 2017. Official problem statement.
\url{https://www.contest.comap.com/undergraduate/contests/mcm/contests/2017/problems/2017_MCM_Problem_B.pdf}.
\bibitem{fhwa} Federal Highway Administration. Traffic Analysis Toolbox, Volume III: Guidelines for Applying Traffic Microsimulation Modeling Software. 2004, Chapter 5, Model Calibration. FHWA-HRT-04-040.
\url{https://ops.fhwa.dot.gov/trafficanalysistools/tat_vol3/sect5.htm}.
\bibitem{departure} Wilbur Smith Associates, for the Federal Highway Administration. State of the Practice and Recommendations on Traffic Control Strategies at Toll Plazas. June 2006, Section 6.4.2, Departure Zones.
\url{https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter642.htm}.
\bibitem{orientation} Wilbur Smith Associates, for the Federal Highway Administration. State of the Practice and Recommendations on Traffic Control Strategies at Toll Plazas. June 2006, Section 2.2.4, Toll Lane Configuration.
\url{https://mutcd.fhwa.dot.gov/rpt/tcstoll/chapter224.htm}.
\end{thebibliography}
\clearpage\section*{Report on Use of AI Tools}
\addcontentsline{toc}{section}{Report on Use of AI Tools}
An OpenAI Codex agent conducted the problem interpretation, mathematical modeling, programming, numerical experiments and English writing in one delegated research episode. The agent selected the historical task and read its official statement and general FHWA guidance. No same-problem submitted solution or judges' commentary was consulted during this episode. Possible exposure during model pretraining is unknown.

The user supplied the plugin-development objective and authorized local research; the user did not supply this case's model choices or perform its mathematical verification. Other agent roles of the same model family reviewed the numerical tools and, where recorded in the accompanying archive, the case. Such review is not human verification or independent field validation.

Python and its scientific libraries performed layout enumeration, flow construction and queue calculations. LaTeX produced this document. Numerical verification checks the model against distinct algorithms and analytic conditions; it does not establish empirical safety or traffic calibration. The accompanying research archive retains the available run receipts, failed candidates and review scope. Full raw model input/output transcripts are not available in that archive, and no complete interaction log is reconstructed from summaries.
\end{document}
''')
    output.mkdir(parents=True,exist_ok=True)
    tex=output/'paper.tex';tex.write_text(''.join(pieces))
    return tex


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=json.loads(a.results.read_text());tex=document(r,a.output)
    (a.output/'build-input.json').write_text(json.dumps({'results_sha256':hashlib.sha256(a.results.read_bytes()).hexdigest(),'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'phase':r['phase']},indent=2))
    print(tex)
