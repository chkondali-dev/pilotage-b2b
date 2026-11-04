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
from ui.components import rank_card
from metrics.kpi import run_rate_fin_annee
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

# --- NOUVEAUX INDICATEURS EXECUTIFS ---
section('Résumé Exécutif')

# Calcul des nouveaux indicateurs
# Conventions n et n-1
conventions_n = len(ctx.df_vc_filt[ctx.df_vc_filt['Annee'] == ctx.annee_sel]) if 'Annee' in ctx.df_vc_filt.columns else 0
conventions_n1 = len(ctx.df_vc_filt[ctx.df_vc_filt['Annee'] == ctx.annee_sel - 1]) if 'Annee' in ctx.df_vc_filt.columns and ctx.annee_sel - 1 >= 0 else 0
evol_conventions = evol_pct(conventions_n, conventions_n1)

# Clients uniques n et n-1
clients_n = ctx.df_vc_filt['Nom'].nunique() if 'Nom' in ctx.df_vc_filt.columns else 0
clients_n1 = ctx.df_vc_filt[ctx.df_vc_filt['Annee'] == ctx.annee_sel - 1]['Nom'].nunique() if 'Annee' in ctx.df_vc_filt.columns and ctx.annee_sel - 1 >= 0 else 0
evol_clients = evol_pct(clients_n, clients_n1)

# Magasins contributeurs (CA > 0)
magasins_contributeurs = len(ctx.df_vc_filt[ctx.df_vc_filt['CA'] > 0]['Magasin'].unique()) if 'Magasin' in ctx.df_vc_filt.columns and 'CA' in ctx.df_vc_filt.columns else 0

# Dossiers (produits uniques)
dossiers = ctx.df_vc_filt['Produit'].nunique() if 'Produit' in ctx.df_vc_filt.columns else 0

# Top 5 Magasins : Meilleures Progressions vs N-1
if 'Magasin' in ctx.df_vc_filt.columns and 'CA' in ctx.df_vc_filt.columns and ctx.annee_sel - 1 >= 0:
    magasins_data = ctx.df_vc_filt.groupby('Magasin').agg(
        CA_n=('CA', 'sum'),
        CA_n1=('CA', lambda x: x.iloc[-1] if len(x) > 0 else 0),
    ).reset_index()
    magasins_data['Evolution %'] = magasins_data.apply(
        lambda row: evol_pct(row['CA_n'], row['CA_n1']) if row['CA_n1'] != 0 else (100.0 if row['CA_n'] > 0 else 0),
        axis=1,
    )
    meilleurs = magasins_data.nlargest(5, 'Evolution %')
    pires = magasins_data.nsmallest(5, 'Evolution %')
else:
    meilleurs = []
    pires = []

# Display Top 5 Magasins progrès
with k1:
    if meilleurs:
        for _, r in meilleurs.iterrows():
            st.caption(f"{r['Magasin']}: {fmt_pct(r['Evolution %'])} vs N-1, CA: {r['CA_n']:,.0f} TND")
    else:
        st.caption('Aucune donnée magasin disponible')

# Top 5 Magasins : Plus fortes baisses
with k2:
    if pires:
        for _, r in pires.iterrows():
            st.caption(f"{r['Magasin']}: {fmt_pct(r['Evolution %'])} vs N-1, CA: {r['CA_n']:,.0f} TND")
    else:
        st.caption('Aucune baisse mesurable')

# Conventions n et n-1
section('Évolution des Conventions')
col1, col2 = st.columns(2)
with col1:
    st.metric(f'Conventions {ctx.annee_sel}', f'{conventions_n}')
with col2:
    st.metric(f'Conventions {ctx.annee_sel - 1}', f'{conventions_n1}', f'{fmt_pct(evol_conventions)}')

# Clients uniques
section('Évolution des Clients')
col1, col2 = st.columns(2)
with col1:
    st.metric(f'Clients {ctx.annee_sel}', f'{clients_n}')
with col2:
    st.metric(f'Clients {ctx.annee_sel - 1}', f'{clients_n1}', f'{fmt_pct(evol_clients)}')

# Magasins contributeurs
section('Magasins Contributeurs')
st.metric('Nombre de magasins avec CA > 0', f'{magasins_contributeurs}')

# Dossiers
section('Dossiers Produits')
st.metric('Nombre de produits uniques', f'{dossiers}')

# Narratif exécutif
section('Narratif Exécutif')
st.write(narratif_executif(ctx))

# Concentration du portefeuille
section('Concentration du Portefeuille')
if pd.notna(_conc0['Top3 %']):
    _k1, _k2, _k3 = st.columns(3)
    _k1.metric('Part Top 3', f"{_conc0['Top3 %']:.1f}%")
    _k2.metric('HHI', f"{_conc0['HHI']}")
    _k2.caption(f"{_conc0['Niveau']}")
    _conc_top = _conc0['courbe']
    fig_conc = go.Figure()
    fig_conc.add_trace(go.Bar(x=_conc_top['Nom'], y=_conc_top['CA'], name='CA', marker_color=C['blue']))
    fig_conc.add_trace(go.Scatter(x=_conc_top['Nom'], y=_conc_top['Cumul %'], name='% cumulé', yaxis='y2', line=dict(color=C['red'], width=2), marker=dict(color=C['red'])))
    fig_conc.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(title='CA'), yaxis2=dict(title='% cumulé', overlaying='y', side='right', range=[0, 105]))
    st.plotly_chart(fig_conc, use_container_width=True)
else:
    st.caption('Aucune donnée disponible.')