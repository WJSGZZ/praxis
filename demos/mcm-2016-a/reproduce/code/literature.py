"""Surface heat-loss coefficient of an open warm-water surface from standard textbook relations."""
import numpy as np

SIGMA=5.670374e-8;RV=461.5;G=9.81

def psat(t_c):
    """Magnus form, Pa; adequate for 10-45 C."""
    return 610.94*np.exp(17.625*t_c/(t_c+243.04))

def surface_coefficients(Ts=40.,Ta=22.,rh=.5,L=1.5,W=.65,emissivity=.96,exposed=1.):
    """Convection, radiation and evaporation expressed as W/(m2 K) relative to the bulk temperature.

    Upper surface of a hot horizontal plate, characteristic length A/P, natural-convection correlations
    Nu=.54Ra^(1/4) (1e4-1e7) and .15Ra^(1/3) (1e7-1e11); Lewis analogy for mass transfer;
    still-air properties near 305 K. The evaporation term is the dominant uncertainty: published evaporation correlations differ by tens of percent, so the
    result is a scenario value, not a measurement; the tested range for the surface coefficient is wider than the spread between correlations."""
    Tf=(Ts+Ta)/2+273.15;nu,alpha,k=1.6e-5,2.25e-5,.0265;rho_a,cp_a=1.16,1007.;Le=.85;hfg=2.406e6   # latent heat of water near 40 C
    Lc=L*W/(2*(L+W));dT=Ts-Ta
    Ra=G*dT*Lc**3/(Tf*nu*alpha)
    Nu=.54*Ra**.25 if Ra<1e7 else .15*Ra**(1/3)
    hc=Nu*k/Lc
    hr=emissivity*SIGMA*((Ts+273.15)**2+(Ta+273.15)**2)*(Ts+Ta+546.3)
    hm=hc/(rho_a*cp_a*Le**(2/3))
    drho=psat(Ts)/(RV*(Ts+273.15))-rh*psat(Ta)/(RV*(Ta+273.15))
    he=hfg*hm*drho/dT
    parts=dict(convection=hc,radiation=hr,evaporation=he)
    return dict(parts=parts,total=exposed*sum(parts.values()),Ra=Ra,rayleigh_regime='turbulent' if Ra>=1e7 else 'laminar',char_length_m=Lc,evaporation_kg_m2_h=hm*drho*3600)


def wall_coefficient(thickness=.005,conductivity=.19,h_inside=300.,h_outside=8.):
    """Series resistance water -> shell -> room, W/(m2 K). Typical engineering values, not measured for a specific tub.
    h_outside combines natural convection (~3-4) and linearized radiation (~4-5) at a room-temperature outer wall."""
    return 1./(1./h_inside+thickness/conductivity+1./h_outside)


def body_uptake_anchor(mass=73.,specific_heat=3470.,mean_body_rise=(1.0,2.0),minutes=30.,water_minus_skin=6.,area=1.15):
    """Average heat uptake implied by measured core warming, and the equivalent skin-to-water coefficient.

    Menzies et al. (2025) report a rectal-temperature rise of 0.9 +/- 0.3 C after 30 min of shoulder-deep 40 C immersion.
    Mean body temperature rises more than core temperature because the skin warms toward the water; the
    1-2 C range for the mean rise and the fixed 6 K driving difference are assumptions. The 73 kg mass is the mean of the study's 22 participants (13 men 80.3 kg, 9 women 62.1 kg); the paper's full text reports no whole-body skin temperature."""
    out=[]
    for rise in mean_body_rise:
        watts=mass*specific_heat*rise/(minutes*60.)
        out.append(dict(mean_body_rise_c=rise,average_uptake_w=watts,equivalent_h_body=watts/(water_minus_skin*area)))
    return out


def provenance():
    open_water=surface_coefficients(exposed=1.)
    return dict(
        surface=dict(open_water_total=open_water['total'],parts=open_water['parts'],evaporation_kg_m2_h=open_water['evaporation_kg_m2_h'],
                     rayleigh=open_water['Ra'],regime=open_water['rayleigh_regime'],
                     range_open_water=[surface_coefficients(rh=.7,Ta=26.)['total'],surface_coefficients(rh=.3,Ta=20.)['total']],
                     exposed_fraction_assumed=.7,central=surface_coefficients(exposed=.7)['total'],used_baseline=25.),
        wall=dict(central=wall_coefficient(),range=[wall_coefficient(.008,.19,300.,6.),wall_coefficient(.003,.19,300.,10.)],used_baseline=6.5),
        body=dict(anchor=body_uptake_anchor(),used_baseline=25.))
