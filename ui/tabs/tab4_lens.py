from data.config import C
from data.config import MOIS
from data.config import SEUILS
from charts.factory import chart_bar
from charts.factory import chart_grouped_bar
from charts.factory import chart_line_compare
from charts.factory import chart_pie
from charts.factory import chart_variation_bar
from metrics.kpi import compare_years_date_to_date
from metrics.kpi import evol_pct
import plotly.graph_objects as go
from ui.components import kpi_card
import numpy as np
import pandas as pd
import plotly.express as px
from ui.components import section
import streamlit as st
from metrics.kpi import truncate_n1_date_to_date


def render(ctx):
    def _lens_meta(label):
        """Métadonnées du périmètre : df filtré, titre court, flux parent, recos."""
        _has_nom = not ctx.df_credit.empty and 'Nom' in ctx.df_credit.columns

        def _mut(sub_pat):
            return ctx.df_credit[ctx.df_credit['Nom'].str.contains(sub_pat, case=False, na=False)].copy() if _has_nom else ctx.df_credit.iloc[0:0]
        if label == 'EDC':
            return {'key': 'edc', 'short': 'EDC', 'df': ctx.df_edc, 'parent': None, 'flux_label': '', 'spec_recos': [], 'title': "🏫 Convention EDC — Ministère de l'Éducation", 'caption': "Convention Ministère de l'Éducation — flux EDC. Lecture en 5 sections : situation → dynamique → réseau → échéance → synthèse."}
        if label.startswith('🛡️ Mutuelle Sûreté'):
            return {'key': 'surete', 'short': 'Mut. Sûreté', 'df': _mut('MUT PERS SURETE'), 'parent': ctx.df_credit, 'flux_label': 'crédit conso', 'spec_recos': ["Relancer commercialement le compte (rencontre direction, animation du réseau, mise en avant de l'offre) et capitaliser sur la dynamique observée."], 'title': '🛡️ Mutuelle Personnel Sûreté Nationale — Prison & Rééducation', 'caption': 'Compte dédié extrait du flux Crédit Conso (VC.CONSO.) — client « MUT PERS SURETE NLE PRISON &REEDUC ». Lecture en 5 sections : situation → dynamique → réseau → échéance → synthèse.'}
        if label.startswith('🛡️ Mutuelle Garde'):
            return {'key': 'garde', 'short': 'Mut. Garde NLE & PC', 'df': _mut('MUTUELLE GARDE NLE'), 'parent': ctx.df_credit, 'flux_label': 'crédit conso', 'spec_recos': ["Maintenir la dynamique du compte, sécuriser le renouvellement de la convention et étendre l'offre aux magasins du réseau sans dossier."], 'title': '🛡️ Mutuelle Garde NLE & Protection Civile', 'caption': 'Compte dédié extrait du flux Crédit Conso — mutuelle Garde NLE & Protection Civile. Lecture en 5 sections : situation → dynamique → réseau → échéance → synthèse.'}
        if label.startswith('🌐 Convention'):
            return {'key': 'conv', 'short': 'Toutes conventions', 'df': ctx.df_vc, 'parent': None, 'flux_label': '', 'spec_recos': [], 'title': '🌐 Conventionnel — toutes les conventions', 'caption': "Vue globale du flux Conventionnel (VC) : l'ensemble des conventions, tous magasins confondus. Lecture en 5 sections : situation → dynamique → réseau → échéance → synthèse."}
        if label.startswith('🌐 Conso'):
            return {'key': 'conso', 'short': 'Tout le crédit conso', 'df': ctx.df_credit, 'parent': None, 'flux_label': '', 'spec_recos': [], 'title': '🌐 Tout le crédit conso', 'caption': 'Vue globale du flux Crédit Conso : tous les comptes confondus. Lecture en 5 sections : situation → dynamique → réseau → échéance → synthèse.'}
        return {'key': 'part', 'short': 'Tout le crédit particulier', 'df': ctx.df_credit_part, 'parent': None, 'flux_label': '', 'spec_recos': [], 'title': '🌐 Tout le crédit particulier', 'caption': 'Vue globale du flux Crédit Particulier : tous les comptes confondus. Lecture en 5 sections : situation → dynamique → réseau → échéance → synthèse.'}
    st.subheader('🧭 Tous flux & Mutuelles — sélecteur de périmètre')
    st.caption('Un seul corps de lecture pour 6 périmètres : EDC, Mutuelle Sûreté, Mutuelle Garde NLE & Protection Civile, et les vues Convention / Conso / Particulier globales. Lecture en 5 sections : situation → dynamique → réseau → échéance → synthèse.')
    _lens_label = st.selectbox('Périmètre', ctx.lens_labels, key='lens_p', help='Filtre appliqué à toute la page : données, filtres, graphiques, synthèse.')
    meta = _lens_meta(_lens_label)
    st.subheader(meta['title'])
    st.caption(meta['caption'])
    if not meta['df'].empty and 'Année' in meta['df'].columns:
        edc = meta['df'].copy()
        if 'Montant TTC' not in edc.columns:
            edc['Montant TTC'] = 0.0
        edc['Montant TTC'] = pd.to_numeric(edc['Montant TTC'], errors='coerce').fillna(0.0)
        _mag = edc['Magasin'].astype(str).str.strip() if 'Magasin' in edc.columns else pd.Series('', index=edc.index)
        _mag_abs = _mag.str.lower().isin(['', 'nan', 'none', '<na>'])
        _mag_digit = ~_mag_abs & _mag.str.match('^\\d+(\\.0)?$', na=False)
        edc['Magasin'] = _mag.where(~_mag_abs, 'Magasin non renseigné')
        edc.loc[_mag_digit, 'Magasin'] = 'Code ' + _mag[_mag_digit].str.replace('\\.0$', '', regex=True) + ' (non mappé)'
        if 'Enseigne' not in edc.columns:
            edc['Enseigne'] = 'MG'
        edc['Enseigne'] = edc['Enseigne'].where(edc['Enseigne'].astype(str).str.strip().str.len() > 0, 'MG')
        annees_dispo = sorted({int(a) for a in edc['Année'].dropna().unique()}, reverse=True)
        fc1, fc2, fc3 = st.columns([1, 1.3, 2.2])
        with fc1:
            edc_yr = st.selectbox('Année de référence', annees_dispo, index=0, key='edc_yr')
        with fc2:
            _ens_all = sorted((str(e) for e in edc['Enseigne'].dropna().unique().tolist()))
            ens_sel = st.multiselect('Enseigne', _ens_all, default=[], key=f"lens_{meta['key']}_ens")
        with fc3:
            _mag_base = edc[edc['Enseigne'].isin(ens_sel)] if ens_sel else edc
            _mags = sorted((str(m) for m in _mag_base['Magasin'].dropna().unique().tolist()))
            mag_sel = st.multiselect('Établissement', _mags, default=[], key=f"lens_{meta['key']}_mag")
        edc_f = edc
        if ens_sel:
            edc_f = edc_f[edc_f['Enseigne'].isin(ens_sel)]
        if mag_sel:
            edc_f = edc_f[edc_f['Magasin'].isin(mag_sel)]
        df_edc_n = edc_f[edc_f['Année'] == edc_yr]
        if ctx.mois_sel:
            df_edc_n = df_edc_n[df_edc_n['Mois'].isin(ctx.mois_sel)]
        _trunc_e = truncate_n1_date_to_date(edc_f, edc_yr, edc_yr - 1, ctx.mois_sel)
        df_edc_n1 = _trunc_e[_trunc_e['Année'] == edc_yr - 1]
        if ctx.mois_sel:
            df_edc_n1 = df_edc_n1[df_edc_n1['Mois'].isin(ctx.mois_sel)]
        comp = compare_years_date_to_date(edc_f, edc_yr, edc_yr - 1, ctx.mois_sel) if len(df_edc_n) > 0 and len(df_edc_n1) > 0 else pd.DataFrame()
        if not comp.empty:
            ca_e_n = float(comp['CA N'].sum())
            ca_e_n1 = float(comp['CA N-1'].sum())
        else:
            ca_e_n = float(df_edc_n['Montant TTC'].sum())
            ca_e_n1 = float(df_edc_n1['Montant TTC'].sum())
        ev_edc = evol_pct(ca_e_n, ca_e_n1)
        nb_f_edc = len(df_edc_n)
        nb_f_n1 = len(df_edc_n1)
        panier_e = ca_e_n / nb_f_edc if nb_f_edc > 0 else 0.0
        panier_n1 = ca_e_n1 / nb_f_n1 if nb_f_n1 > 0 else 0.0
        mois_dispo_n = sorted((int(m) for m in edc_f[edc_f['Année'] == edc_yr]['Mois'].dropna().unique()))
        ca_e_annee = float(edc_f[edc_f['Année'] == edc_yr]['Montant TTC'].sum())

        def _edc_delta(n_val: float, n1_val: float):
            """Delta % affichable, None sans base N-1 (évite le +0.0% artificiel)."""
            return f'{evol_pct(n_val, n1_val):+.1f}%' if n1_val > 0 else None
        st.caption(f"Année {edc_yr} — mois disponibles : {', '.join((MOIS.get(m, str(m)) for m in mois_dispo_n)) or 'aucun'}" + (f" • Mois analysés : {', '.join((MOIS.get(m, str(m)) for m in sorted(ctx.mois_sel)))}" if ctx.mois_sel else '') + (' • Périmètre : tous les établissements' if not mag_sel else f' • Périmètre : {len(mag_sel)} établissement(s)'))
        section('1 · Situation — indicateurs clés')
        _kpi_row = st.columns(5 if meta['parent'] is not None else 4)
        e1, e2, e3, e4 = _kpi_row[:4]
        with e1:
            kpi_card(f'CA {edc_yr}', f'{ca_e_n:,.0f} TND', _edc_delta(ca_e_n, ca_e_n1), delta_tone='normal', ref_label=f'CA {edc_yr - 1}', ref_value=f'{ca_e_n1:,.0f} TND', help=f'Comparé date à date avec {edc_yr - 1} : mêmes mois et mêmes jours que {edc_yr}.')
        with e2:
            st.metric('Nb factures', f'{nb_f_edc:,}', _edc_delta(nb_f_edc, nb_f_n1), delta_color='normal', help=f'Factures de la période, vs {edc_yr - 1} sur la même période (date à date).')
        with e3:
            st.metric('Panier moyen', f'{panier_e:,.0f} TND', _edc_delta(panier_e, panier_n1), delta_color='normal', help='CA de la période divisé par le nombre de factures de la période.')
        with e4:
            st.metric('Écart vs N-1', f'{ca_e_n - ca_e_n1:+,.0f} TND', help=f'Écart en valeur du CA vs {edc_yr - 1} sur la période comparée (date à date).')
        if meta['parent'] is not None:
            _par = meta['parent']
            _par_p = _par[_par['Année'] == edc_yr]
            if ctx.mois_sel:
                _par_p = _par_p[_par_p['Mois'].isin(ctx.mois_sel)]
            _ca_parent = float(pd.to_numeric(_par_p['Montant TTC'], errors='coerce').fillna(0).sum())
            _part_pct = ca_e_n / _ca_parent * 100 if _ca_parent > 0 else None
            with _kpi_row[4]:
                st.metric(f"Part du périmètre ({meta['flux_label']})", f'{_part_pct:.2f} %' if _part_pct is not None else '—', help=f"CA {edc_yr} de ce périmètre rapporté au CA total du flux {meta['flux_label']} sur la même période (année et mois filtrés).")
        etab = df_edc_n.groupby('Magasin').agg(CA_N=('Montant TTC', 'sum'), Nb=('Montant TTC', 'count')).reset_index().rename(columns={'CA_N': 'CA N'})
        _et_n1 = df_edc_n1.groupby('Magasin')['Montant TTC'].sum().rename('CA N-1').reset_index()
        etab = etab.merge(_et_n1, on='Magasin', how='outer')
        etab['CA N'] = etab['CA N'].fillna(0.0)
        etab['CA N-1'] = etab['CA N-1'].fillna(0.0)
        etab['Nb'] = etab['Nb'].fillna(0).astype(int)
        etab['Évolution %'] = np.where(etab['CA N-1'] > 0, ((etab['CA N'] - etab['CA N-1']) / etab['CA N-1'] * 100).round(1), np.nan)
        etab['Panier moyen'] = (etab['CA N'] / etab['Nb'].replace(0, np.nan)).fillna(0).round(0)
        total_edc_n = float(etab['CA N'].sum())
        etab['Poids %'] = (etab['CA N'] / total_edc_n * 100).round(1) if total_edc_n > 0 else 0.0
        etab = etab.sort_values('CA N', ascending=False).reset_index(drop=True)
        etab['Poids cumulé %'] = etab['Poids %'].cumsum().round(1) if total_edc_n > 0 else 0.0
        etab['Statut'] = np.select([(etab['CA N'] == 0) & (etab['CA N-1'] == 0), (etab['CA N'] > 0) & (etab['CA N-1'] == 0), (etab['CA N'] == 0) & (etab['CA N-1'] > 0), etab['Évolution %'] <= SEUILS['declin_fort_pct'], etab['Évolution %'] < 0], ['⚫ Aucun CA', '🟢 Nouveau', '🔴 Sorti', '🔴 Déclin fort', '🟡 Déclin'], default='🟢 Croissance')
        _hors_net = etab['Magasin'].isin(['Magasin non renseigné', 'Inconnu']) | etab['Magasin'].str.startswith('Code ', na=False)
        mag_net = etab[~_hors_net].copy()
        mag_net_tot = float(mag_net['CA N'].sum())
        if mag_net_tot > 0:
            mag_net['Poids net %'] = (mag_net['CA N'] / mag_net_tot * 100).round(1)
            mag_net['Poids net cumulé %'] = mag_net['Poids net %'].cumsum().round(1)
        else:
            mag_net['Poids net %'] = 0.0
            mag_net['Poids net cumulé %'] = 0.0
        n_actifs = int((mag_net['CA N'] > 0).sum())
        n_actifs_n1 = int((mag_net['CA N-1'] > 0).sum())
        n_nouveaux = int(((mag_net['CA N'] > 0) & (mag_net['CA N-1'] == 0)).sum())
        n_sortis = int(((mag_net['CA N'] == 0) & (mag_net['CA N-1'] > 0)).sum())
        n_en_hausse = int((mag_net['Évolution %'] > 0).sum())
        n_en_baisse = int((mag_net['Évolution %'] < 0).sum())
        c_et1, c_et2, c_et3, c_et4, c_et5 = st.columns(5)
        with c_et1:
            st.metric('Établissements actifs', f'{n_actifs}', _edc_delta(n_actifs, n_actifs_n1), delta_color='normal', help='Établissements avec au moins une facture sur la période (réseau mappé, hors codes non mappés).')
        with c_et2:
            st.metric('Nouveaux', f'{n_nouveaux}', help=f'Avec CA en {edc_yr} et aucun CA sur la période {edc_yr - 1} correspondante.')
        with c_et3:
            st.metric('Sortis', f'{n_sortis}', help=f"Sans CA en {edc_yr} alors qu'ils en avaient sur la période {edc_yr - 1}.")
        with c_et4:
            st.metric('En croissance', f'{n_en_hausse}', help='CA de la période supérieur à la base N-1 tronquée (date à date).')
        with c_et5:
            st.metric('En baisse', f'{n_en_baisse}', help='CA de la période inférieur à la base N-1 tronquée (date à date).')
        if len(df_edc_n) == 0 and len(df_edc_n1) == 0:
            st.warning(f'Aucune ligne sur le périmètre et les mois sélectionnés — CA {edc_yr} toutes périodes : {ca_e_annee:,.0f} TND. Élargissez le filtre « Mois » (barre latérale) ou le périmètre établissement.')
        elif ctx.mois_sel and mois_dispo_n and (max(ctx.mois_sel) > max(mois_dispo_n)):
            st.info(f"ℹ️ Données {edc_yr} disponibles jusqu'à {MOIS.get(max(mois_dispo_n), str(max(mois_dispo_n)))} — les mois suivants ne sont pas encore comptabilisés.")
        section('2 · Dynamique & saisonnalité')
        if comp.empty:
            st.info(f'Pas de comparatif {edc_yr - 1} exploitable pour le périmètre sélectionné.')
        else:
            st.plotly_chart(chart_grouped_bar(comp, 'Mois Nom', 'CA N', 'CA N-1', f"CA mensuel {meta['short']} — {edc_yr} vs {edc_yr - 1} (date à date)", edc_yr), use_container_width=True)
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                comp_cum = comp.sort_values('Mois').copy()
                comp_cum['CA N'] = comp_cum['CA N'].cumsum()
                comp_cum['CA N-1'] = comp_cum['CA N-1'].cumsum()
                st.plotly_chart(chart_line_compare(comp_cum, 'Mois Nom', 'CA N', 'CA N-1', f"CA cumulé {meta['short']} — {edc_yr} vs {edc_yr - 1} (date à date)", edc_yr), use_container_width=True)
            with col_g2:
                _fn = df_edc_n.groupby('Mois').size().to_dict()
                _fn1 = df_edc_n1.groupby('Mois').size().to_dict()
                fact_m = comp[['Mois', 'Mois Nom']].copy()
                fact_m['Factures N'] = [int(_fn.get(int(m), 0)) for m in fact_m['Mois']]
                fact_m['Factures N-1'] = [int(_fn1.get(int(m), 0)) for m in fact_m['Mois']]
                fig_fm = px.bar(fact_m.melt(id_vars=['Mois', 'Mois Nom'], value_vars=['Factures N-1', 'Factures N'], var_name='Période', value_name='Factures'), x='Mois Nom', y='Factures', color='Période', barmode='group', color_discrete_map={'Factures N-1': '#94A3B8', 'Factures N': '#1D4ED8'}, title=f"Factures mensuelles {meta['short']} — {edc_yr} vs {edc_yr - 1} (date à date)")
                fig_fm.update_layout(height=380, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5), margin=dict(l=16, r=16, t=52, b=16))
                st.plotly_chart(fig_fm, use_container_width=True)
        section('3 · Réseau des établissements')
        col_r1, col_r2 = st.columns([3, 2])
        with col_r1:
            top10 = mag_net.head(10).sort_values('CA N')
            fig_top = px.bar(top10, x='CA N', y='Magasin', orientation='h', title=f"Top 10 établissements — {meta['short']} — {edc_yr}", color='CA N', color_continuous_scale=['#1D4ED8', '#3B82F6', '#60A5FA'], text_auto='.0f')
            fig_top.update_layout(height=400, yaxis=dict(autorange='reversed'))
            fig_top.update_traces(textposition='outside')
            st.plotly_chart(fig_top, use_container_width=True)
        with col_r2:
            st.markdown(f'#### Concentration du réseau ({edc_yr})')
            if n_actifs > 0:
                _top1_p = float(mag_net['Poids net %'].iloc[0])
                _top3_p = float(mag_net['Poids net %'].head(3).sum())
                st.markdown(f'- **Top 1** : {_top1_p:.1f} % du CA réseau\n- **Top 3** : {_top3_p:.1f} % du CA réseau\n- **Établissements actifs** : {n_actifs}\n- **CA moyen / établissement** : {mag_net_tot / n_actifs:,.0f} TND')
                if _top3_p > 50:
                    st.info('⚠️ Concentration forte : plus de la moitié du CA repose sur 3 établissements.')
            else:
                st.markdown('- Aucun établissement actif sur la période sélectionnée.')
        if mag_net_tot > 0 and len(mag_net) > 0:
            par = mag_net.head(15)
            fig_par = go.Figure()
            fig_par.add_trace(go.Bar(x=par['Magasin'], y=par['CA N'], name='CA', marker_color=['#1D4ED8' if i < 3 else '#93C5FD' for i in range(len(par))], text=[f'{v / 1000.0:.1f}k' for v in par['CA N']], textposition='outside'))
            fig_par.add_trace(go.Scatter(x=par['Magasin'], y=par['Poids net cumulé %'], name='Cumul %', yaxis='y2', mode='lines+markers', line=dict(color='#F59E0B', width=2), marker=dict(size=8)))
            fig_par.update_layout(title=f"Concentration du CA par établissement {meta['short']} — top {len(par)} (Pareto)", yaxis=dict(title='CA (TND)'), yaxis2=dict(title='% cumulé', overlaying='y', side='right', range=[0, 105], showgrid=False), legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5), height=430, template='plotly_white', hovermode='x unified')
            st.plotly_chart(fig_par, use_container_width=True)
        else:
            st.info('Aucun CA réseau à représenter pour le périmètre sélectionné.')
        var_src = mag_net[(mag_net['CA N'] > 0) & (mag_net['CA N-1'] > 0)].copy()
        if len(var_src) > 0:
            var_src['Abs'] = var_src['Évolution %'].abs()
            var_show = pd.concat([var_src.nlargest(8, 'Abs'), var_src.nsmallest(8, 'Abs')]).drop_duplicates(subset='Magasin')
            st.plotly_chart(chart_variation_bar(var_show, 'Magasin', 'Évolution %', f"Mouvements de CA par établissement {meta['short']} — {edc_yr} vs {edc_yr - 1} (date à date)"), use_container_width=True)
        else:
            st.info(f'Pas de base {edc_yr - 1} comparable établissement par établissement — voir les nouveaux et sortants ci-dessous.')
        with st.expander('📋 Tableau complet des établissements'):
            display_df = etab.rename(columns={'CA N': f'CA {edc_yr}', 'CA N-1': f'CA {edc_yr - 1}', 'Nb': 'Nb factures'})
            display_df = display_df[['Magasin', 'Statut', f'CA {edc_yr}', f'CA {edc_yr - 1}', 'Évolution %', 'Nb factures', 'Panier moyen', 'Poids %', 'Poids cumulé %']]
            st.dataframe(display_df.style.format({f'CA {edc_yr}': '{:,.0f}', f'CA {edc_yr - 1}': '{:,.0f}', 'Évolution %': '{:+.1f}%', 'Panier moyen': '{:,.0f}', 'Poids %': '{:.1f}%', 'Poids cumulé %': '{:.1f}%'}, na_rep='—'), use_container_width=True, height=440)
        mvn, mvs = st.columns(2)
        with mvn:
            _news = etab[etab['Statut'].str.contains('Nouveau', na=False)]['Magasin'].tolist()
            st.markdown(f'**🆕 Nouveaux établissements** ({len(_news)})')
            if _news:
                st.markdown('\n'.join((f'- {m}' for m in _news[:8])))
                if len(_news) > 8:
                    st.caption(f'+ {len(_news) - 8} autres — voir tableau complet')
            else:
                st.info('Aucun nouvel établissement sur la période.')
        with mvs:
            _sors = etab[etab['Statut'].str.contains('Sorti', na=False)]['Magasin'].tolist()
            st.markdown(f'**🚪 Sans activité sur la période** ({len(_sors)})')
            if _sors:
                st.markdown('\n'.join((f'- {m}' for m in _sors[:8])))
                if len(_sors) > 8:
                    st.caption(f'+ {len(_sors) - 8} autres — voir tableau complet')
            else:
                st.info('Aucun établissement sorti vs la période N-1.')
        section("4 · Durée d'échéance")
        ech = pd.DataFrame()
        _col_ech = next((c for c in edc.columns if c.startswith('Nbr_Mois_Ech')), None)
        if _col_ech and len(df_edc_n) > 0:
            ech = df_edc_n.groupby(_col_ech).agg(CA=('Montant TTC', 'sum'), Nb=('Montant TTC', 'count')).reset_index().rename(columns={_col_ech: 'Nbr_Mois_Echance'})
        if len(ech) > 0:
            ech['Nbr_Mois_Echance'] = pd.to_numeric(ech['Nbr_Mois_Echance'], errors='coerce').fillna(0).astype(int)
            ech = ech.groupby('Nbr_Mois_Echance', as_index=False)[['CA', 'Nb']].sum()
            ech['Part %'] = (ech['CA'] / ech['CA'].sum() * 100).round(1)
            ech['Label'] = ech['Part %'].apply(lambda p: f'{p}%')
            ech = ech.sort_values('Nbr_Mois_Echance')
            _nb_tot_ech = float(ech['Nb'].sum())
            _zero_share = float(ech.loc[ech['Nbr_Mois_Echance'] == 0, 'Nb'].sum()) / _nb_tot_ech if _nb_tot_ech > 0 else 0.0
            if _zero_share >= 0.98:
                st.caption(f"ℹ️ Durée d'échéance non exploitable sur ce périmètre : {_zero_share:.0%} des dossiers à « 0 mois ». Lecture orientée sur les sections 1-3 et la synthèse.")
                ech = pd.DataFrame()
            else:
                col_ec1, col_ec2 = st.columns([2, 1])
                with col_ec1:
                    fig_ech = chart_bar(ech, 'Nbr_Mois_Echance', 'CA', f"Répartition par durée d'échéance — {meta['short']} — {edc_yr}", C['blue'])
                    fig_ech.update_xaxes(title='Durée (mois)', type='category')
                    fig_ech.update_yaxes(title='CA TTC (TND)')
                    fig_ech.update_traces(text=ech['Label'].tolist(), textposition='outside')
                    st.plotly_chart(fig_ech, use_container_width=True)
                with col_ec2:
                    st.plotly_chart(chart_pie(ech['CA'].tolist(), [f'{int(m)} mois' for m in ech['Nbr_Mois_Echance']], 'Part par échéance'), use_container_width=True)
        else:
            st.info("Aucune donnée de durée d'échéance sur la période sélectionnée (colonne absente ou vide).")
        section('5 · Synthèse & recommandations')
        insights, reco = ([], [])
        if ca_e_n1 > 0:
            insights.append(f'- **Tendance** : CA {edc_yr} à {ca_e_n:,.0f} TND vs {ca_e_n1:,.0f} TND en {edc_yr - 1} sur la période comparée (**{ev_edc:+.1f} %**).')
        elif ca_e_n > 0:
            insights.append(f'- **Tendance** : activité de {ca_e_n:,.0f} TND sans base comparable en {edc_yr - 1}.')
        else:
            insights.append('- **Tendance** : aucun CA sur la période sélectionnée.')
        insights.append(f'- **Volume** : {nb_f_edc} factures vs {nb_f_n1} en {edc_yr - 1} (panier moyen {panier_e:,.0f} TND vs {panier_n1:,.0f} TND).')
        if mag_net_tot > 0 and n_actifs > 0:
            _lead = mag_net.iloc[0]
            insights.append(f"- **Réseau** : {n_actifs} établissements actifs, {n_nouveaux} nouveau(x), {n_sortis} sorti(s) ; leader **{_lead['Magasin']}** = {float(_lead['CA N']):,.0f} TND ({float(_lead['Poids net %']):.1f} % du CA réseau).")
            insights.append(f"- **Concentration** : top 3 = {float(mag_net['Poids net %'].head(3).sum()):.1f} % du CA réseau.")
        if not comp.empty:
            _bm = comp.loc[comp['CA N'].idxmax()]
            insights.append(f"- **Saisonnalité** : meilleur mois {edc_yr} = **{_bm['Mois Nom']}** ({float(_bm['CA N']):,.0f} TND).")
        if ctx.mois_sel and ca_e_annee > ca_e_n + 1:
            insights.append(f'- **Périmètre** : analyse limitée aux mois sélectionnés — CA {edc_yr} toutes périodes = {ca_e_annee:,.0f} TND.')
        if len(ech) > 0:
            _dom = ech.loc[ech['CA'].idxmax()]
            insights.append(f"- **Échéance** : durée dominante **{int(_dom['Nbr_Mois_Echance'])} mois** ({float(_dom['CA']):,.0f} TND, {float(_dom['Part %']):.1f} % du CA période).")
        if ca_e_n1 > 0 and ev_edc < 0:
            reco.append('🎯 **Relancer la performance** : la base comparable est établie — cibler les établissements en repli (variation bar ci-dessus).')
        elif ca_e_n1 > 0:
            reco.append('🎯 **Capitaliser** : la période progresse au-dessus de N-1 — sécuriser la montée en charge des établissements leaders.')
        else:
            reco.append("🎯 **Structurer la mesure** : sans base N-1 exploitable sur ce périmètre, élargir les mois ou fiabiliser l'historique.")
        if n_actifs > 0 and float(mag_net['Poids net %'].head(3).sum()) > 50:
            reco.append("🔗 **Réduire la concentration** : le top 3 pèse plus de 50 % du CA réseau — développer le second cercle d'établissements.")
        if n_nouveaux == 0 and n_actifs > 0:
            reco.append('🚀 **Dynamiser le réseau** : aucun nouvel établissement sur la période — relancer les ouvertures / conventions en préparation.')
        if n_sortis > 0:
            reco.append(f'🔁 **Auditer les sorties** : {n_sortis} établissement(s) sans activité vs {edc_yr - 1} — comprendre les causes avant clôture.')
        if n_en_baisse > 0:
            reco.append(f"📈 **Plan d'action baisses** : accompagner les {n_en_baisse} établissements en repli (note mensuelle).")
        reco.append(f"🛥️ **Prochaine lecture** : rejouer cette page à J+5 du clos de {(MOIS.get(mois_dispo_n[-1], '—') if mois_dispo_n else '—')} {edc_yr} pour verrouiller l'écart date à date avant diffusion.")
        if meta['parent'] is not None:
            _idc = 'N° Client' if 'N° Client' in edc.columns else 'N°' if 'N°' in edc.columns else None
            _taux_recur = None
            if _idc is not None:
                _ids_n = set(df_edc_n[_idc].dropna().astype(str))
                _ids_n1 = set(df_edc_n1[_idc].dropna().astype(str))
                if _ids_n1:
                    _taux_recur = len(_ids_n & _ids_n1) * 100.0 / len(_ids_n1)
            if _taux_recur is not None:
                insights.append(f'- **Fidélisation** : taux de récurrence de **{_taux_recur:.1f} %** — adhérents actifs en {edc_yr - 1} également actifs sur la période {edc_yr}.')
                if _taux_recur < 10:
                    reco.append(f'🎯 **Relance adhérents** : taux de récurrence {_taux_recur:.1f} % — cibler les adhérents actifs en {edc_yr - 1} sans dossier en {edc_yr} (relance SMS / appel, offre de réassurance du réseau).')
            reco.extend((f'🎯 {r}' for r in meta['spec_recos']))
        col_a1, col_a2 = st.columns([3, 2])
        with col_a1:
            st.markdown('### Constats clés')
            st.markdown('\n'.join(insights))
        with col_a2:
            st.markdown('### Recommandations')
            st.markdown('\n'.join(reco))
    else:
        st.warning(f"⚠️ Aucune donnée {meta['short']} disponible.")