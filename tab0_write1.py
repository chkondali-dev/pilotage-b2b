from data.config import C
from data.config import MOIS
from metrics.kpi import bridge_volume_panier
from metrics.kpi import business_insights
from metrics.kpi import poids_convention_cube
from charts.factory import chart_bar
from charts.factory import chart_gauge
from charts.factory import chart_grouped_bar
from charts.factory import chart_line_compare
from charts.factory import chart_risk_table
from charts.factory import chart_variation_bar
from metrics.kpi import color_delta
from metrics.kpi import concentration_portefeuille
from metrics.kpi import evol_pct
from metrics.kpi import fmt_pct
from metrics.kpi import panier_moyen
import plotly.graph_objects as go
from metrics.kpi import narratif_executif
from metrics.kpi import objectif_tracking
import pandas as pd
from ui.components import section
import streamlit as st
from metrics.kpi import ventes_positives
from metrics.kpi import volumes_panier

def render(ctx):
    section('Indicateurs clés')
    _vol0 = volumes_panier(ctx.df_vc_filt, ctx.annee_sel, ctx.mois_sel)
    _conc0 = concentration_portefeuille(ctx.df_vc_filt, ctx.annee_sel, ctx.mois_sel)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f'CA {ctx.annee_sel}', f'{ctx.ca_n:,.0f} TND', f'{fmt_pct(ctx.ev_nn1)} vs {ctx.annee_sel - 1}', delta_color=color_delta(ctx.ev_nn1))
    with k2:
        st.metric('Conventions actives', f'{ctx.nb_actives}')
        st.caption(f'{_conc0["Top3 %"]:.1f}% top 3' if pd.notna(_conc0["Top3 %"]) else f'/ {ctx.nb_total} total')
    k3.metric('Panier moyen', f"{_vol0['Panier N']:,.0f} TND" if pd.notna(_vol0['Panier N']) else '—', f"{fmt_pct(_vol0['Evo panier %'])} vs N-1" if pd.notna(_vol0['Evo panier %']) else '—', delta_color=color_delta(_vol0['Evo panier %']))
    with k4:
        st.metric('Concentration Top 3', f'{_conc0["Top3 %"]:.1f}%' if pd.notna(_conc0["Top3 %"]) else '—', help='Part du CA détenue par les 3 plus gros clients')