from data.config import C
from data.config import MOIS
from data.config import SEUILS
from metrics.kpi import bridge_volume_panier
from charts.factory import chart_bar
from charts.factory import chart_bridge
from charts.factory import chart_gauge
from charts.factory import chart_line_compare
from charts.factory import chart_variation_bar
from metrics.kpi import color_delta
from datetime import datetime
from metrics.kpi import evol_pct
from metrics.kpi import fmt_pct
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import plotly.express as px
from metrics.kpi import run_rate_fin_annee
from ui.components import section
import streamlit as st
from datetime import timedelta
from metrics.kpi import volumes_panier


def render(ctx):
    _vol0 = volumes_panier(ctx.df_vc_filt, ctx.annee_sel, ctx.mois_sel)
    mois_label = ', '.join([MOIS.get(m, str(m)) for m in ctx.mois_sel]) if ctx.mois_sel else f'{ctx.annee_sel}'
    st.markdown('### 📊 Performance veille — chiffre de la veille')
    default_date = (datetime.now() - timedelta(days=1)).date()
    hier_date = st.date_input('Choisir une date', value=default_date, key='veille_date')
    annee_hier = hier_date.year
    mois_hier = hier_date.month
    _fin_win = hier_date
    _deb_win = hier_date
    _deb_win_n1 = (pd.Timestamp(_deb_win) - pd.DateOffset(years=1)).date()
    _fin_win_n1 = (pd.Timestamp(_fin_win) - pd.DateOffset(years=1)).date()
    df_vc_hier = ctx.df_vc[(ctx.df_vc['Date'].dt.date >= _deb_win) & (ctx.df_vc['Date'].dt.date <= _fin_win)].copy()
    df_vc_n1 = ctx.df_vc[(ctx.df_vc['Date'].dt.date >= _deb_win_n1) & (ctx.df_vc['Date'].dt.date <= _fin_win_n1)].copy()
    ca_veille = df_vc_hier['Montant TTC'].sum() if len(df_vc_hier) > 0 else 0
    ca_n1_meme_jour = df_vc_n1['Montant TTC'].sum() if len(df_vc_n1) > 0 else 0
    evo_veille = (ca_veille - ca_n1_meme_jour) / ca_n1_meme_jour * 100 if ca_n1_meme_jour > 0 else float('nan')
    nb_tickets_veille = len(df_vc_hier)
    panier_veille = ca_veille / nb_tickets_veille if nb_tickets_veille > 0 else 0
    kp1, kp2, kp3, kp4 = st.columns(4)
    kp1.metric('CA veille', f'{ca_veille:,.0f} TND')
    kp2.metric('Évolution vs N-1', fmt_pct(evo_veille))
    kp3.metric('Nb factures', nb_tickets_veille)
    kp4.metric('Panier moyen', f'{panier_veille:,.0f} TND')
    st.caption(f"📅 Fenêtre : {_deb_win.strftime('%d/%m/%Y')} → {_fin_win.strftime('%d/%m/%Y')} — comparée à {_deb_win_n1.strftime('%d/%m/%Y')} → {_fin_win_n1.strftime('%d/%m/%Y')} (N-1)")
    col_seg1, col_seg2 = st.columns(2)
    with col_seg1:
        st.markdown('**Top 5 Conventions — veille**')
        if not df_vc_hier.empty and 'Montant TTC' in df_vc_hier.columns and ('Nom' in df_vc_hier.columns):
            top5_conv = df_vc_hier.groupby('Nom')['Montant TTC'].sum().nlargest(5)
            df_top5 = top5_conv.reset_index()
            df_top5.columns = ['Convention', 'CA']
            fig_top5 = px.bar(df_top5, x='CA', y='Convention', orientation='h', title='Top 5 Conventions', color='CA', color_continuous_scale=['#DCFCE7', '#15803D'])
            fig_top5.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_top5, use_container_width=True)
    with col_seg2:
        st.markdown('**Top 5 Magasins — veille**')
        if not df_vc_hier.empty and 'Montant TTC' in df_vc_hier.columns:
            for code_col_src in ['Code Navision', 'Unite Code']:
                if code_col_src in df_vc_hier.columns and 'Magasin' in df_vc_hier.columns:
                    top5_mag = df_vc_hier.groupby('Magasin')['Montant TTC'].sum().nlargest(5)
                    if len(top5_mag) > 0:
                        df_top5m = top5_mag.reset_index()
                        df_top5m.columns = ['Magasin', 'CA']
                        fig_top5m = px.bar(df_top5m, x='CA', y='Magasin', orientation='h', title='Top 5 Magasins', color='CA', color_continuous_scale=['#DCFCE7', '#15803D'])
                        fig_top5m.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
                        st.plotly_chart(fig_top5m, use_container_width=True)
                        break
            else:
                st.caption('Colonne Magasin non disponible')
    st.markdown('### 3. Analyse par Enseigne (MG / BATAM)')
    col_ens1, col_ens2 = st.columns([1, 2])
    with col_ens1:
        st.markdown('**CA par Enseigne**')
        has_enseigne = not df_vc_hier.empty and 'Enseigne' in df_vc_hier.columns
        if has_enseigne:
            ca_ens = df_vc_hier.groupby('Enseigne')['Montant TTC'].sum()
            total_ca = ca_ens.sum()
            mg_ca = ca_ens.get('MG', 0)
            bam_ca = ca_ens.get('BATAM', 0)
            mg_pct = mg_ca / total_ca * 100 if total_ca > 0 else 0
            bam_pct = bam_ca / total_ca * 100 if total_ca > 0 else 0
            st.metric('CA MG', f'{mg_ca:,.0f} TND')
            st.caption(f'{mg_pct:.1f}% du total')
            st.metric('CA BATAM', f'{bam_ca:,.0f} TND')
            st.caption(f'{bam_pct:.1f}% du total')
            st.caption(f'**Total:** {total_ca:,.0f} TND')
        else:
            st.info("Pas de donnees d'enseigne disponibles")
    with col_ens2:
        if has_enseigne:
            fig_pie = px.pie(values=ca_ens.values if len(ca_ens) > 0 else [1, 1], names=ca_ens.index if len(ca_ens) > 0 else ['MG', 'BATAM'], title='Repartition du CA: MG vs BATAM', color_discrete_sequence=['#1D4ED8', '#059669'], hole=0.4)
            fig_pie.update_traces(textinfo='percent+label', hoverinfo='label+percent+value')
            fig_pie.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20), legend=dict(orientation='h', yanchor='bottom', y=-0.1, xanchor='center', x=0.5))
            st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('### 🔔 Alertes & Insights — Veille (vs N-1)')
    alertes = []
    couleur_alertes = []
    if evo_veille < SEUILS['alerte_veille_pct']:
        alertes.append(f'⚠️ Baisse significative: {evo_veille:.1f}% vs N-1 (veille)')
        couleur_alertes.append('inverse')
    elif evo_veille >= 0:
        alertes.append(f'✅ Belle performance: +{evo_veille:.1f}% vs N-1 (veille)')
        couleur_alertes.append('normal')
    if panier_veille < _vol0['Panier N'] * SEUILS['panier_bas_ratio'] and pd.notna(_vol0['Panier N']):
        alertes.append(f"📉 Panier bas: {panier_veille:,.0f} TND (moy: {_vol0['Panier N']:,.0f})")
        couleur_alertes.append('inverse')
    if not df_vc_hier.empty:
        worst = df_vc_hier[df_vc_hier['Montant TTC'] > 0].nsmallest(1, 'Montant TTC')
        if len(worst) > 0:
            w_mag = worst.iloc[0]['Magasin'] if 'Magasin' in worst.columns else worst.iloc[0].get('Nom', '')
            w_ca = worst.iloc[0]['Montant TTC']
            if w_ca < 100:
                alertes.append(f'🚨 Magasin critique: {w_mag} (CA: {w_ca:,.0f})')
                couleur_alertes.append('inverse')
    if 'Enseigne' in df_vc_hier.columns:
        ca_ens = df_vc_hier.groupby('Enseigne')['Montant TTC'].sum()
        total_ca = ca_ens.sum()
        mg_pct = ca_ens.get('MG', 0) / total_ca * 100 if total_ca > 0 else 0
        bam_pct = ca_ens.get('BATAM', 0) / total_ca * 100 if total_ca > 0 else 0
        if total_ca > 0:
            if mg_pct > 80:
                alertes.append(f'⚖️ Desequilibre: MG {mg_pct:.0f}% / BATAM {bam_pct:.0f}%')
                couleur_alertes.append('inverse')
            elif bam_pct > 80:
                alertes.append(f'⚖️ Desequilibre: BATAM {bam_pct:.0f}% / MG {mg_pct:.0f}%')
                couleur_alertes.append('inverse')
    if not alertes:
        alertes.append('✅ Aucune alerte — veille normale')
        couleur_alertes.append('normal')
    for txt, col in zip(alertes, couleur_alertes):
        st.write(f'{txt}')
    st.markdown('---')
    section('Tendance mensuelle')
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        fig_line = chart_line_compare(ctx.df_comp, 'Mois Nom', 'CA N', 'CA N-1', f'Tendance mensuelle {ctx.annee_sel} vs {ctx.annee_sel - 1}', ctx.annee_sel)
        st.plotly_chart(fig_line, use_container_width=True)
    with col_t2:
        fig_mvar = chart_variation_bar(ctx.df_comp, 'Mois Nom', 'Variation %', f'Variation mensuelle % — {ctx.annee_sel} vs {ctx.annee_sel - 1}')
        st.plotly_chart(fig_mvar, use_container_width=True)
    section('CA Journalier')
    _dj_n = ctx.df_vc_filt[ctx.df_vc_filt['Année'] == ctx.annee_sel]
    _dj_n1 = ctx.df_vc_filt[ctx.df_vc_filt['Année'] == ctx.annee_sel - 1]
    ca_jn = _dj_n.groupby('Jour')['Montant TTC'].sum().rename('CA N').reset_index()
    ca_jn1 = _dj_n1.groupby('Jour')['Montant TTC'].sum().rename('CA N-1').reset_index()
    df_jour = ca_jn.merge(ca_jn1, on='Jour', how='outer').fillna(0).sort_values('Jour')
    fig_jour = chart_line_compare(df_jour, 'Jour', 'CA N', 'CA N-1', f'CA Journalier — {ctx.annee_sel} vs {ctx.annee_sel - 1}', ctx.annee_sel, h=380)
    fig_jour.update_xaxes(dtick=1, tickangle=45)
    st.plotly_chart(fig_jour, use_container_width=True)
    section('3 derniers mois glissants')
    col_r1, col_r2 = st.columns([2, 1])
    with col_r1:
        fig_3m = chart_bar(ctx.df_3m, 'Periode', 'Montant TTC', 'CA Rolling 3 mois', C['blue'])
        st.plotly_chart(fig_3m, use_container_width=True)
    with col_r2:
        fig_gauge = chart_gauge(ctx.ca_n, ctx.ca_n1, f'Atteinte {ctx.annee_sel} vs {ctx.annee_sel - 1}')
        st.plotly_chart(fig_gauge, use_container_width=True)
    with st.expander('📄 Données brutes — CA Journalier'):
        df_jour['Variation %'] = np.where(df_jour['CA N-1'] > 0, (df_jour['CA N'] - df_jour['CA N-1']) / df_jour['CA N-1'] * 100, np.nan).round(1)
        st.dataframe(df_jour, use_container_width=True)
    section('Saisonnalité — Heatmap CA mensuel × année')
    _hm = ctx.df_vc_scope.groupby(['Année', 'Mois'])['Montant TTC'].sum().reset_index()
    _hm_pivot = _hm.pivot(index='Année', columns='Mois', values='Montant TTC').fillna(0)
    _hm_pivot = _hm_pivot.rename(columns=MOIS)
    fig_hm = px.imshow(_hm_pivot, text_auto='.0f', aspect='auto', title='CA mensuel par année', color_continuous_scale='Blues', labels=dict(color='CA'))
    fig_hm.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_hm, use_container_width=True)
    section('Prévision — Rolling 3 mois')
    _prev_df = ctx.df_vc_scope[ctx.df_vc_scope['Année'] >= max(ctx.annee_sel - 1, ctx.df_vc_scope['Année'].min())].copy()
    _prev_m = _prev_df.groupby(['Année', 'Mois'])['Montant TTC'].sum().reset_index()
    _prev_m['Periode'] = _prev_m['Année'].astype(str) + '-' + _prev_m['Mois'].astype(str).str.zfill(2)
    _prev_m = _prev_m.sort_values(['Année', 'Mois']).tail(6)
    if len(_prev_m) >= 3:
        _ma = _prev_m['Montant TTC'].rolling(3, min_periods=1).mean()
        _prev_m['Prev M+1'] = _ma.shift(1)
        _prev_m['Prev M+1'] = _prev_m['Prev M+1'].fillna(_prev_m['Montant TTC'].mean())
        _next_p = _prev_m.iloc[-1]['Montant TTC']
        _next_ma = _ma.iloc[-1]
        _next_val = _next_p * 0.4 + _next_ma * 0.6
        _col_p1, _col_p2 = st.columns([2, 1])
        with _col_p1:
            fig_p = go.Figure()
            fig_p.add_trace(go.Bar(x=_prev_m['Periode'], y=_prev_m['Montant TTC'], name='CA réalisé', marker_color=C['blue']))
            fig_p.add_trace(go.Scatter(x=[_prev_m['Periode'].iloc[-1], f"{ctx.annee_sel}-{_prev_m['Mois'].iloc[-1] + 1:02d}"], y=[_next_p, _next_val], mode='lines+markers', name='Prévision', line=dict(color=C['red'], dash='dash', width=2), marker=dict(color=C['red'], size=8)))
            fig_p.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_p, use_container_width=True)
        with _col_p2:
            st.metric('Prévision M+1', f'{_next_val:,.0f}', delta=f'{(_next_val - _next_p) / _next_p * 100:+.1f}%' if _next_p > 0 else None)
            st.caption(f'Basée sur moyenne mobile 3m (pondérée 60/40)')
            _rr = run_rate_fin_annee(ctx.df_vc_scope, ctx.annee_sel)
            _ca_n1_full = float(ctx.df_vc_scope[ctx.df_vc_scope['Année'] == ctx.annee_sel - 1]['Montant TTC'].sum()) if 'Montant TTC' in ctx.df_vc_scope.columns else 0.0
            _rr_evo = evol_pct(_rr['Projection'], _ca_n1_full)
            st.metric(f'Run-rate fin {ctx.annee_sel}', f"{_rr['Projection']:,.0f} TND" if pd.notna(_rr['Projection']) else '—', f'{fmt_pct(_rr_evo)} vs {ctx.annee_sel - 1} (annuel)' if pd.notna(_rr['Projection']) else None, delta_color=color_delta(_rr_evo))
            st.caption(f"CA YTD {_rr['CA YTD']:,.0f} / {_rr['Jours écoulés']} j écoulés × {_rr['Jours année']} j")
    section('Pont de variation — Volume × Panier')
    _bridge = bridge_volume_panier(ctx.df_vc_scope, ctx.annee_sel, ctx.mois_sel)
    _beff = _bridge.set_index('Étape')['Effet (TND)']
    if pd.notna(_beff.get('+ Volume')):
        st.plotly_chart(chart_bridge(_bridge, 'Étape', 'Valeur', f"Décomposition ΔCA {ctx.annee_sel} vs {ctx.annee_sel - 1}{(' — ' + mois_label if ctx.mois_sel else '')}"), use_container_width=True)
        bc1, bc2, bc3 = st.columns(3)
        bc1.metric('Effet volume', f"{_beff.get('+ Volume'):+,.0f} TND", f"{_bridge.set_index('Étape').loc['+ Volume', 'Nb factures']:+,.0f} factures")
        _dpan = _bridge.set_index('Étape').loc['+ Panier', 'Panier moyen']
        bc2.metric('Effet panier', f"{_beff.get('+ Panier'):+,.0f} TND", f'{_dpan:+,.0f} TND/facture')
        _bmix = _beff.get('+ Interaction', _beff.get('+ Mix'))
        bc3.metric('Effet interaction', f'{_bmix:+,.0f} TND' if pd.notna(_bmix) else '—', f"Δ total {_beff.get('= CA N'):+,.0f} TND")
    else:
        st.caption('Pas de base N-1 sur la période — pont non calculable.')