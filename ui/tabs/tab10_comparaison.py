from data.config import C
from data.config import MOIS
from ui.components import badge
from metrics.kpi import ca_sum_date_to_date
from metrics.kpi import poids_convention_cube
from charts.factory import chart_bar
from charts.factory import chart_grouped_bar
from charts.factory import chart_line_compare
from charts.factory import chart_pie
from metrics.kpi import cohortes_conventions
from metrics.kpi import color_delta
from metrics.kpi import compare_years_date_to_date
from metrics.kpi import conversion_conventions
from metrics.kpi import fmt_pct
from metrics.kpi import kpi_conversion_globale
from metrics.kpi import truncate_n1_date_to_date
import numpy as np
import pandas as pd
import plotly.express as px
from ui.components import section
import streamlit as st
from metrics.kpi import evol_pct
def render(ctx):
    """Onglet Comparaison Convention / CA — Vue Magasin/Région."""
    st.title('📊 Comparaison Convention / CA')

    # --- Filtres ---
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        annee = st.selectbox('Année', sorted(ctx.df_vc['Annee'].unique()) if 'Annee' in ctx.df_vc.columns else [ctx.annee_sel], index=0, key='cmp_annee')
    with col_f2:
        if 'Mois' in ctx.df_vc.columns:
            mois_options = sorted(ctx.df_vc['Mois'].dropna().unique())
            mois_sel = st.multiselect('Mois', mois_options, default=ctx.mois_sel, key='cmp_mois')
        else:
            mois_sel = ctx.mois_sel
    with col_f3:
        # Filtre par région/enseigne
        enseignes = ['Tous'] + sorted(ctx.df_vc['Enseigne'].dropna().unique()) if 'Enseigne' in ctx.df_vc.columns else ['Tous']
        enseigne_sel = st.selectbox('Enseigne', enseignes, index=0, key='cmp_enseigne')

    # --- Filtrer les données ---
    df_vc_f = ctx.df_vc_filt.copy()
    if annee is not None and 'Annee' in df_vc_f.columns:
        df_vc_f = df_vc_f[df_vc_f['Annee'] == annee]
    if mois_sel:
        if isinstance(mois_sel, int):
            df_vc_f = df_vc_f[df_vc_f['Mois'] == mois_sel]
        elif isinstance(mois_sel, list) and len(mois_sel) > 0:
            df_vc_f = df_vc_f[df_vc_f['Mois'].isin(mois_sel)]
    if enseigne_sel and enseigne_sel != 'Tous':
        df_vc_f = df_vc_f[df_vc_f['Enseigne'] == enseigne_sel]

    # --- Calcul du poids convention ---
    annee_cmp = annee if annee else ctx.annee_sel
    mois_cmp = mois_sel if isinstance(mois_sel, int) else None
    res = poids_convention_cube(ctx.df_cube_mag, df_vc_f, annee_cmp, mois_cmp)

    # --- KPI Cards ---
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    with col_k1:
        st.metric('📦 Poids Convention', f'{res["poids_pct"]}%' if not pd.isna(res["poids_pct"]) else 'Non disponible')
    with col_k2:
        st.metric('💰 CA Convention', f'{res["ca_conv"]:,.0f} TND')
    with col_k3:
        st.metric('🏗️ CA Total Cube', f'{res["ca_total"]:,.0f} TND')
    with col_k4:
        st.metric('💵 CA Comptant', f'{res["ca_comptant"]:,.0f} TND')

    st.divider()

    # --- Vue par Magasin ---
    st.subheader('🏪 Performance par Magasin')
    if 'Magasin' in df_vc_f.columns and not df_vc_f.empty:
        df_mag = df_vc_f.groupby('Magasin').agg(
            CA_Conv=('Montant TTC', 'sum'),
        ).reset_index()
        # On peut enrichir avec le cube si dispo
        if not ctx.df_cube_mag.empty and 'Magasin' in ctx.df_cube_mag.columns:
            cube_mag = ctx.df_cube_mag.groupby('Magasin')['CA Magasin'].sum().reset_index()
            cube_mag.columns = ['Magasin', 'CA_Cube']
            df_mag = df_mag.merge(cube_mag, on='Magasin', how='left').fillna(0)

        df_mag = df_mag.sort_values('CA_Conv', ascending=False).head(20)

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            fig_mag = chart_bar(df_mag.head(10), 'CA_Conv', 'Magasin', f'CA Convention par Magasin — {annee_cmp}', C['green'], h=400, orientation='h')
            st.plotly_chart(fig_mag, use_container_width=True)
        with col_m2:
            st.info('Graphique CA Convention')

        # Tableau détaillé
        st.dataframe(
            df_mag[['Magasin', 'CA_Conv']].rename(columns={'CA_Conv': 'CA Convention'}),
            use_container_width=True,
            height=min(400, 35 * (len(df_mag) + 1))
        )
    else:
        st.info('Aucune donnée magasin disponible pour les filtres sélectionnés.')

    st.divider()

    # --- Vue par Enseigne / Région ---
    st.subheader('🌍 Performance par Enseigne / Région')
    if 'Enseigne' in df_vc_f.columns and not df_vc_f.empty:
        df_ens = df_vc_f.groupby('Enseigne').agg(
            CA_Conv=('Montant TTC', 'sum'),
        ).reset_index()
        df_ens = df_ens.sort_values('CA_Conv', ascending=False)

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            fig_ens = chart_pie(df_ens.head(10), 'CA_Conv', 'Enseigne', f'Part Convention par Enseigne — {annee_cmp}', hole=0.4)
            st.plotly_chart(fig_ens, use_container_width=True)
        with col_e2:
            fig_ens_b = chart_bar(df_ens, 'CA_Conv', 'Enseigne', f'CA Convention par Enseigne — {annee_cmp}', C['orange'], h=400, orientation='h')
            st.plotly_chart(fig_ens_b, use_container_width=True)

        st.dataframe(
            df_ens[['Enseigne', 'CA_Conv']].rename(columns={'CA_Conv': 'CA Convention'}),
            use_container_width=True
        )
    else:
        st.info('Aucune donnée par enseigne/région disponible.')

    st.divider()

    # --- Alertes : magasins où la convention > CA total ---
    st.subheader('⚠️ Alertes : Magasins en surpoids convention')
    if 'Magasin' in df_vc_f.columns and not df_vc_f.empty and not ctx.df_cube_mag.empty and 'Magasin' in ctx.df_cube_mag.columns:
        # Regroupement par magasin
        magasin_data = []
        for mag in df_vc_f['Magasin'].dropna().unique():
            ca_conv_m = df_vc_f[df_vc_f['Magasin'] == mag]['Montant TTC'].sum()
            ca_total_m = ctx.df_cube_mag[ctx.df_cube_mag['Magasin'] == mag]['CA Magasin'].sum() if mag in ctx.df_cube_mag['Magasin'].unique() else 0
            if ca_total_m > 0:
                poids = round(ca_conv_m / ca_total_m * 100, 1)
                statut = '🔴 SURPOIDS' if poids > 50 else ('🟢 NORMAL' if poids < 20 else '🟠 ATTENTION')
                magasin_data.append({'Magasin': mag, 'CA_Conv': ca_conv_m, 'CA_Total': ca_total_m, 'Poids %': poids, 'Statut': statut})

        if magasin_data:
            df_alertes = pd.DataFrame(magasin_data).sort_values('Poids %', ascending=False)
            st.dataframe(
                df_alertes[['Magasin', 'CA_Conv', 'CA_Total', 'Poids %', 'Statut']],
                use_container_width=True,
                height=min(400, 35 * (len(df_alertes) + 1))
            )
            nb_alertes = len(df_alertes[df_alertes['Statut'] == '🔴 SURPOIDS'])
            st.caption(f'{nb_alertes} magasin(s) en surpoids convention (> 50%)')
        else:
            st.info('Aucune alerte de surpoids détectée.')
    else:
        st.info('Données insuffisantes pour générer des alertes magasin.')
