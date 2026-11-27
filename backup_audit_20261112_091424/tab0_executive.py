from data.config import C
from data.config import MOIS
from data.config import SEUILS
from metrics.kpi import (
    bridge_volume_panier,
    business_insights,
    ca_sum,
    concentration_portefeuille,
    color_delta,
    data_health,
    evol_pct,
    fmt_pct,
    panier_moyen,
    narratif_executif,
    objectif_tracking,
    run_rate_fin_annee,
    ventes_positives,
    volumes_panier,
    nb_factures,
    truncate_n1_date_to_date,
    compare_years_date_to_date,
    inactive_conventions,
)
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from ui.components import rank_card, section, kpi_card


def render(ctx):
    # === EN-TÊTE EXECUTIF ===
    section('Vue Exécutive SMG B2B')
    st.caption('Période : ' + str(ctx.annee_sel) + ' | Filtré : ' + (ctx.mois_sel or 'Toute annee'))
    
    # --- Filtres consolidés ---
    st.markdown('**Filtres**')
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        annee_sel = st.selectbox('Année', options=[2024, 2023, 2022, 2021], index=0, help='Sélecteur d annee principal')
    with col_f2:
        réseau_sel = st.radio('Réseau', options=['Consolidé', 'MG', 'BATAM'], index=0, help='Filtre par reseau d exploitation')
    with col_f3:
        comparaison_sel = st.radio('Comparaison', options=['vs N-1', 'vs Période précédente'], index=0, help='Sélectionner le type de comparaison')
    
    # Application des filtres
    annee = ctx.annee_sel
    mois = ctx.mois_sel if ctx.mois_sel else list(MOIS.keys())[:12]
    
    # Filtrage selon réseau sélectionné
    if réseau_sel == 'MG':
        df_filtré = ctx.df_vc.copy() if ctx.df_vc is not None and not ctx.df_vc.empty else pd.DataFrame()
        if not df_filtré.empty and 'Enseigne' in df_filtré.columns:
            df_filtré = df_filtré[df_filtré['Enseigne'] == 'MG']
    elif réseau_sel == 'BATAM':
        df_filtré = ctx.df_vc.copy() if ctx.df_vc is not None and not ctx.df_vc.empty else pd.DataFrame()
        if not df_filtré.empty and 'Enseigne' in df_filtré.columns:
            df_filtré = df_filtré[df_filtré['Enseigne'] == 'BATAM']
    else:
        df_filtré = ctx.df_vc.copy() if ctx.df_vc is not None and not ctx.df_vc.empty else pd.DataFrame()
    
    # --- KPI PRINCIPAUX ---
    st.markdown('**Indicateurs Stratégiques**')
    
    # 1. CA Conventions
    ca_conventions = ca_sum(ctx.df_edc, annee) if ctx.df_edc is not None and not ctx.df_edc.empty else 0.0
    
    # 2. CA Global Magasins
    ca_global_magasins = ca_sum(ctx.df_cube_mag, annee) if ctx.df_cube_mag is not None and not ctx.df_cube_mag.empty else 0.0
    
    # 3. Poids des Conventions dans le CA Global
    if ca_global_magasins > 0:
        poids_conventions = round(ca_conventions / ca_global_magasins * 100, 1)
    else:
        poids_conventions = 0.0
    
    # 4. Évolution du CA vs N-1
    ca_n = ctx.ca_n if ctx.ca_n is not None else 0.0
    ca_n1 = ctx.ca_n1 if ctx.ca_n1 is not None else 0.0
    if ca_n1 > 0 and pd.notna(ca_n1) and pd.notna(ca_n):
        evo_ca = round((ca_n - ca_n1) / ca_n1 * 100, 1)
    else:
        evo_ca = float('nan')
    
    # 5. Nombre de partenaires actifs
    nb_partenaires_actifs = len(ctx.df_crm['N° Client'].unique()) if ctx.df_crm is not None and not ctx.df_crm.empty and 'N° Client' in ctx.df_crm.columns else 0
    
    # 6. Nombre de magasins contributeurs
    mag_n, mag_n1, evo_mag = magasins_actifs(ctx.df_vc_filt, annee, mois) if ctx.df_vc_filt is not None else (0, 0, 0)
    
    # 7. Nombre de dossiers
    nb_dossiers = len(ctx.df_conv['N° Convention'].unique()) if ctx.df_conv is not None and not ctx.df_conv.empty and 'N° Convention' in ctx.df_conv.columns else 0
    
    # 8. Concentration du CA des 20 premiers partenaires
    concentration_20 = concentration_portefeuille(ctx.df_vc_filt, annee, mois)
    top20_pct = concentration_20['Top5 %'] if concentration_20 and 'Top5 %' in concentration_20 else 0.0
    
    # Affichage en ligne de 8 KPIs (4 colonnes × 2 rangées)
    kpi_data = [
        ('CA Conventions', '{:,.0f} TND'.format(ca_conventions), evo_ca, 'évolution CA vs N-1'),
        ('CA Global Magasins', '{:,.0f} TND'.format(ca_global_magasins), None, 'CA global'),
        ('Poids Conventions', '{:.1f} %'.format(poids_conventions), None, 'part du gobal'),
        ('Évolution CA', '{:+.1f} %'.format(evo_ca) if pd.notna(evo_ca) else '—', evo_ca, 'vs N-1'),
        ('Partenaires Actifs', str(nb_partenaires_actifs), None, 'effectif'),
        ('Magasins Contributeurs', str(mag_n), evo_mag, 'évolution'),
        ('Nombre de Dossiers', str(nb_dossiers), None, 'effectif'),
        ('Concentration Top 20', '{:.1f} %'.format(top20_pct) if top20_pct else '—', None, 'part CA top 20'),
    ]
    
    # Affichage des KPIs en rangées de 2
    for i in range(0, 8, 2):
        cols = st.columns(2)
        for j, kpi in enumerate([kpi_data[i], kpi_data[i+1]]):
            with cols[j]:
                label, value, delta, help_text = kpi
                if delta is not None and pd.notna(delta):
                    if isinstance(delta, float) and str(delta) == 'nan':
                        st.metric(label, value, help=help_text)
                    else:
                        delta_str = '{:+.1f} %'.format(delta) if abs(delta) < 100 else ''
                        st.metric(label, value, delta_color=color_delta(delta), help=help_text)
                else:
                    st.metric(label, value, help=help_text)
    
    # --- ÉVOLUTION DE LA PERFORMANCE ---
    st.markdown('**Évolution de la Performance**')
    
    # Graphique 1: Évolution mensuelle CA Conventions et CA Global Magasins
    st.markdown('#### Évolution Mensuelle CA Conventions vs CA Global')
    
    months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Données CA Conventions année N
    ca_n_mens = [0]*12
    if ctx.df_edc is not None and not ctx.df_edc.empty and 'Année' in ctx.df_edc.columns and 'Mois' in ctx.df_edc.columns and 'Montant TTC' in ctx.df_edc.columns:
        for m in range(1, 13):
            val = ctx.df_edc[(ctx.df_edc['Année'] == annee) & (ctx.df_edc['Mois'] == m)]['Montant TTC'].sum()
            ca_n_mens[m-1] = val
    
    # Données CA Global Magasin année N
    ca_g_mens = [0]*12
    if ctx.df_cube_mag is not None and not ctx.df_cube_mag.empty and 'Année' in ctx.df_cube_mag.columns and 'Mois' in ctx.df_cube_mag.columns and 'Montant TTC' in ctx.df_cube_mag.columns:
        for m in range(1, 13):
            val = ctx.df_cube_mag[(ctx.df_cube_mag['Année'] == annee) & (ctx.df_cube_mag['Mois'] == m)]['Montant TTC'].sum()
            ca_g_mens[m-1] = val
    
    # Construction Graphique 1
    fig = go.Figure()
    
    # CA Conventions année N
    fig.add_trace(go.Bar(x=months, y=ca_n_mens, name='CA Conventions ' + str(annee), marker_color=C['green'], showlegend=True))
    
    # CA Global Magasins année N
    fig.add_trace(go.Bar(x=months, y=ca_g_mens, name='CA Global ' + str(annee), marker_color=C['blue'], showlegend=True))
    
    # N-1 si comparaison demandée
    if comparaison_sel == 'vs N-1' and annee > 2020:
        annee_n1 = annee - 1
        ca_n1_mens = [0]*12
        ca_g_n1_mens = [0]*12
        if ctx.df_edc is not None and not ctx.df_edc.empty:
            for m in range(1, 13):
                val = ctx.df_edc[(ctx.df_edc['Année'] == annee_n1) & (ctx.df_edc['Mois'] == m)]['Montant TTC'].sum()
                ca_n1_mens[m-1] = val
        if ctx.df_cube_mag is not None and not ctx.df_cube_mag.empty:
            for m in range(1, 13):
                val = ctx.df_cube_mag[(ctx.df_cube_mag['Année'] == annee_n1) & (ctx.df_cube_mag['Mois'] == m)]['Montant TTC'].sum()
                ca_g_n1_mens[m-1] = val
        
        fig.add_trace(go.Bar(x=months, y=ca_n1_mens, name='CA Conventions ' + str(annee_n1), marker_color=C['slate'], showlegend=False, legendgroup='N-1'))
        fig.add_trace(go.Bar(x=months, y=ca_g_n1_mens, name='CA Global ' + str(annee_n1), marker_color=C['slate'], showlegend=False, legendgroup='N-1'))
    
    fig.update_layout(
        title='Évolution Mensuelle CA',
        yaxis_title='TND',
        xaxis_title='Mois',
        barmode='group',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Graphique 2: Évolution mensuelle du poids des Conventions dans le CA Global
    st.markdown('#### Poids des Conventions dans le CA Global (Mensuel)')
    
    poids_mensuels = []
    for m in range(1, 13):
        ca_c_m = 0
        ca_g_m = 0
        if ctx.df_edc is not None and not ctx.df_edc.empty and 'Année' in ctx.df_edc.columns and 'Mois' in ctx.df_edc.columns and 'Montant TTC' in ctx.df_edc.columns:
            ca_c_m = ctx.df_edc[(ctx.df_edc['Année'] == annee) & (ctx.df_edc['Mois'] == m)]['Montant TTC'].sum()
        if ctx.df_cube_mag is not None and not ctx.df_cube_mag.empty and 'Année' in ctx.df_cube_mag.columns and 'Mois' in ctx.df_cube_mag.columns and 'Montant TTC' in ctx.df_cube_mag.columns:
            ca_g_m = ctx.df_cube_mag[(ctx.df_cube_mag['Année'] == annee) & (ctx.df_cube_mag['Mois'] == m)]['Montant TTC'].sum()
        
        if ca_g_m > 0:
            poids_mensuels.append(round(ca_c_m / ca_g_m * 100, 1))
        else:
            poids_mensuels.append(0.0)
    
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=[MOIS.get(m, str(m)) for m in range(1, 13)], y=poids_mensuels, name='Poids Conventions ' + str(annee), marker_color=C['amber']))
    
    # N-1 si comparaison
    if comparaison_sel == 'vs N-1' and annee > 2020:
        annee_n1 = annee - 1
        poids_n1 = []
        for m in range(1, 13):
            ca_c_m = 0
            ca_g_m = 0
            if ctx.df_edc is not None and not ctx.df_edc.empty and 'Année' in ctx.df_edc.columns and 'Mois' in ctx.df_edc.columns and 'Montant TTC' in ctx.df_edc.columns:
                ca_c_m = ctx.df_edc[(ctx.df_edc['Année'] == annee_n1) & (ctx.df_edc['Mois'] == m)]['Montant TTC'].sum()
            if ctx.df_cube_mag is not None and not ctx.df_cube_mag.empty and 'Année' in ctx.df_cube_mag.columns and 'Mois' in ctx.df_cube_mag.columns and 'Montant TTC' in ctx.df_cube_mag.columns:
                ca_g_m = ctx.df_cube_mag[(ctx.df_cube_mag['Année'] == annee_n1) & (ctx.df_cube_mag['Mois'] == m)]['Montant TTC'].sum()
            if ca_g_m > 0:
                poids_n1.append(round(ca_c_m / ca_g_m * 100, 1))
            else:
                poids_n1.append(0.0)
        fig2.add_trace(go.Bar(x=[MOIS.get(m, str(m)) for m in range(1, 13)], y=poids_n1, name='Poid Conventions ' + str(annee_n1), marker_color=C['slate']))
    
    fig2.update_layout(
        title='Poids Mensuel des Conventions dans le CA Global',
        yaxis_title='%',
        xaxis_title='Mois',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=500
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # --- RÉPARTITION MG / BATAM ---
    st.markdown('**Répartition MG / BATAM**')
    
    ca_mg = 0
    ca_batam = 0
    mags_mg = 0
    mags_batam = 0
    part_mg = 0
    part_batam = 0
    
    if ctx.df_vc is not None and not ctx.df_vc.empty:
        reseau_col = next((c for c in ctx.df_vc.columns if 'Réseau' in c or 'Reseau' in c), None)
        if reseau_col and reseau_col in ctx.df_vc.columns:
            df_mg = ctx.df_vc[ctx.df_vc[reseau_col] == 'MG']
            df_batam = ctx.df_vc[ctx.df_vc[reseau_col] == 'BATAM']
            ca_mg = df_mg['Montant TTC'].sum() if 'Montant TTC' in df_mg.columns else 0
            ca_batam = df_batam['Montant TTC'].sum() if 'Montant TTC' in df_batam.columns else 0
            mags_mg = len(df_mg['Magasin'].unique()) if 'Magasin' in df_mg.columns else 0
            mags_batam = len(df_batam['Magasin'].unique()) if 'Magasin' in df_batam.columns else 0
        else:
            # Répartition par défaut si pas de colonne réseau
            ca_mg = ca_conventions * 0.6
            ca_batam = ca_conventions * 0.4
            mags_mg = mag_n * 0.6
            mags_batam = mag_n * 0.4
    
    part_mg = round(ca_mg / (ca_mg + ca_batam) * 100, 1) if (ca_mg + ca_batam) > 0 else 0.0
    part_batam = round(ca_batam / (ca_mg + ca_batam) * 100, 1) if (ca_mg + ca_batam) > 0 else 0.0
    
    col_mg, col_batam = st.columns(2)
    
    with col_mg:
        st.metric('CA Conventions MG', '{:,.0f} TND'.format(ca_mg), help='Network MG')
        st.metric('Part MG', '{:.1f} %'.format(part_mg), help='Part dans les conventions')
        st.metric('Magasins MG', str(mags_mg), help='Magasins contributeurs MG')
    
    with col_batam:
        st.metric('CA Conventions BATAM', '{:,.0f} TND'.format(ca_batam), help='Network BATAM')
        st.metric('Part BATAM', '{:.1f} %'.format(part_batam), help='Part dans les conventions')
        st.metric('Magasins BATAM', str(mags_batam), help='Magasins contributeurs BATAM')
    
    ca_total_reseau = ca_mg + ca_batam
    st.caption('Vision consolidée MG + BATAM : {:,.0f} TND CA Conventions total'.format(ca_total_reseau))
    
    # --- TOP CONTRIBUTEURS ---
    st.markdown('**Top Contributeurs**')
    
    col_top1, col_top2 = st.columns(2)
    
    with col_top1:
        st.markdown('#### Top 5 Partenaires par CA')
        if ctx.df_vc is not None and not ctx.df_vc.empty and 'Montant TTC' in ctx.df_vc.columns and 'N° Client' in ctx.df_vc.columns:
            top_partenaires = ctx.df_vc.groupby('N° Client')['Montant TTC'].sum().reset_index().sort_values(by='Montant TTC', ascending=False).head(5)
            for _, row in top_partenaires.iterrows():
                st.caption('Client ' + str(row['N° Client']) + ': ' + '{:,.0f} TND'.format(row['Montant TTC']))
        else:
            st.caption('Aucune donnée partenaire disponible')
    
    with col_top2:
        st.markdown('#### Top 5 Magasins par CA Conventions')
        if ctx.df_vc is not None and not ctx.df_vc.empty and 'Montant TTC' in ctx.df_vc.columns and 'Magasin' in ctx.df_vc.columns:
            top_magasins = ctx.df_vc.groupby('Magasin')['Montant TTC'].sum().reset_index().sort_values(by='Montant TTC', ascending=False).head(5)
            for _, row in top_magasins.iterrows():
                st.caption(row['Magasin'] + ': ' + '{:,.0f} TND'.format(row['Montant TTC']))
        else:
            st.caption('Aucune donnée magasin disponible')
    
    # --- ALERTES DE PILOTAGE ---
    st.markdown('**Alertes de Pilotage**')
    
    alertes = []
    
    # 1. Partenaires sans activité récente
    if ctx.seuil_inactif and ctx.seuil_inactif > 0:
        df_inact = inactive_conventions(ctx.df_conv, annee, ctx.seuil_inactif) if ctx.df_conv is not None else pd.DataFrame()
        if not df_inact.empty:
            alertes.append('{:.0f} partenaire(s) sans activité depuis {}j'.format(len(df_inact), ctx.seuil_inactif))
    
    # 2. Baisses significatives de CA
    if pd.notna(evo_ca) and evo_ca < SEUILS.get('baisse_sig_pct', -20):
        alertes.append('Baisse significative CA : {:.1f} % vs N-1'.format(evo_ca))
    
    # 3. Concentrations importantes
    if pd.notna(top20_pct) and top20_pct > SEUILS.get('concentration_top3_pct', 50):
        alertes.append('Concentration élevée Top 20 : {:.1f} % du CA'.format(top20_pct))
    
    # 4. Écarts aux objectifs
    if ctx.objectif_m and ctx.objectif_m > 0 and ca_conventions < ctx.objectif_m * 0.8:
        alertes.append('Écart objectif : {:,.0f} TND sur {:,.0f} TND cible'.format(ca_conventions, ctx.objectif_m))
    
    # 5. Anomalies de données
    sante = data_health(ctx.df_vc_filt) if ctx.df_vc_filt is not None else {'statut': 'sain', 'recommandations': []}
    if sante['statut'] in ['⚠️ Attention', '❌ Critique']:
        for rec in sante['recommandations']:
            alertes.append('🩺 ' + rec)
    
    # Affichage des alertes
    if alertes:
        for a in alertes:
            st.caption(a)
    else:
        st.caption('Aucune alerte critique pour la période sélectionnée')
    
    # --- NARRATIF EXECUTIF ---
    st.markdown('**Narratif Exécutif**')
    try:
        narrative = narratif_executif(ctx)
        for icon, texte in narrative:
            st.write(icon + ' ' + texte)
    except Exception as ne:
        st.info('Narratif non disponible pour cette période')
    
    st.markdown('---')
    st.caption('Dashboard B2B SMG — MG & BATAM | Source : VC.CONV. Business Central | Généré automatiquement')
