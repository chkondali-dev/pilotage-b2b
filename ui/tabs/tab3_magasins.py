from data.config import C
from data.config import MOIS
from metrics.kpi import color_delta
from metrics.kpi import compare_years_date_to_date
from metrics.kpi import evol_pct
from metrics.kpi import fmt_pct
from metrics.kpi import poids_convention_cube
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import plotly.express as px
from ui.components import section
import streamlit as st
from metrics.kpi import truncate_n1_date_to_date


def render(ctx):
    section('Performance réseau')
    if 'Magasin' not in ctx.df_vc.columns:
        st.info('Données magasin non disponibles')
    else:
        _d2d = truncate_n1_date_to_date(ctx.df_vc_filt, ctx.annee_sel, ctx.annee_sel - 1, ctx.mois_sel)
        _base_n = _d2d[_d2d['Année'] == ctx.annee_sel].copy()
        _base_n1 = _d2d[_d2d['Année'] == ctx.annee_sel - 1].copy()
        all_stores = sorted(_base_n['Magasin'].dropna().unique()) if 'Magasin' in _base_n.columns else []
        col_search, col_reset = st.columns([5, 1])
        with col_search:
            search_term = st.text_input('🔍 Filtre magasin', placeholder='Tapez pour chercher...', label_visibility='collapsed')
        with col_reset:
            st.markdown('###')
            if st.button('🔄 Réinitialiser', use_container_width=True):
                st.session_state.pop('store_selector', None)
                st.rerun()
        filtered_stores = [s for s in all_stores if search_term.lower() in s.lower()] if search_term else all_stores[:50]
        options = ['Tous'] + filtered_stores
        selected_store = st.selectbox('Magasin', options, index=0, key='store_selector', format_func=lambda x: '🌐 Tous les magasins' if x == 'Tous' else f'🏪 {x}', label_visibility='collapsed')
        if selected_store == 'Tous':
            ca_mag_n = _base_n.groupby('Magasin')['Montant TTC'].sum().rename('CA N')
            ca_mag_n1 = _base_n1.groupby('Magasin')['Montant TTC'].sum().rename('CA N-1')
            ca_mag = pd.concat([ca_mag_n, ca_mag_n1], axis=1).fillna(0).reset_index()
            ca_mag['Evolution %'] = np.where(ca_mag['CA N-1'] > 0, ((ca_mag['CA N'] - ca_mag['CA N-1']) / ca_mag['CA N-1'] * 100).round(1), 0.0)
            if not ctx.df_cube_mag.empty and 'Magasin' in ctx.df_cube_mag.columns:
                cube_agg = ctx.df_cube_mag.groupby('Magasin')['CA Magasin'].sum().reset_index()
                cube_agg.columns = ['Magasin', 'CA Total Magasin']
                ca_mag = ca_mag.merge(cube_agg, on='Magasin', how='left').fillna(0)
            else:
                ca_mag['CA Total Magasin'] = 0
            total_n = ca_mag['CA N'].sum()
            ca_mag['Poids %'] = (ca_mag['CA N'] / total_n * 100).round(1) if total_n > 0 else 0.0
            ca_mag = ca_mag.sort_values('CA N', ascending=False)
            simple_sum = _base_n['Montant TTC'].sum()
            k1, k2, k3, k4 = st.columns(4)
            k1.metric('🏪 Magasins actifs', len(ca_mag[ca_mag['CA N'] > 0]))
            k2.metric('💰 CA Total Conventions', f'{simple_sum:,.0f} TND')
            k3.metric('📈 En croissance', len(ca_mag[ca_mag['Evolution %'] > 0]))
            k3.caption(f'/ {len(ca_mag)}')
            k4.metric('📉 En baisse', len(ca_mag[ca_mag['Evolution %'] < 0]))
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                top10 = ca_mag.head(10)
                fig_top = px.bar(top10, x='CA N', y='Magasin', orientation='h', title=f'Top 10 — CA {ctx.annee_sel}', color='CA N', color_continuous_scale=['#1D4ED8', '#3B82F6', '#60A5FA'], text_auto='.0f', height=450)
                fig_top.update_layout(yaxis=dict(autorange='reversed'))
                st.plotly_chart(fig_top, use_container_width=True)
            with col_m2:
                fig_evo = px.bar(top10, x='Evolution %', y='Magasin', orientation='h', title='Top 10 — Évolution N/N-1', color='Evolution %', color_continuous_scale=['#DC2626', '#FCD34D', '#059669'], text_auto='+.1f', height=450)
                fig_evo.update_layout(yaxis=dict(autorange='reversed'))
                fig_evo.add_vline(x=0, line_dash='dash', line_color='grey')
                st.plotly_chart(fig_evo, use_container_width=True)
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if 'Enseigne' in _base_n.columns:
                    by_ense = _base_n.groupby('Enseigne')['Montant TTC'].sum()
                    fig_ense = px.pie(values=by_ense.values, names=by_ense.index, title='CA par Enseigne', hole=0.4)
                    fig_ense.update_traces(textinfo='percent+label')
                    st.plotly_chart(fig_ense, use_container_width=True)
            with col_p2:
                if 'Type vente à crédit' in _base_n.columns:
                    by_type = _base_n.groupby('Type vente à crédit')['Montant TTC'].sum()
                    by_type = by_type[by_type > 0]
                    fig_type = px.bar(by_type.reset_index(), x='Type vente à crédit', y='Montant TTC', title='CA par Type de vente', text_auto='.0f', color='Montant TTC', color_continuous_scale=['#1D4ED8', '#3B82F6'])
                    st.plotly_chart(fig_type, use_container_width=True)
            with st.expander('📋 Tableau complet des magasins'):
                display_cols = ['Magasin', 'CA N', 'Poids %', 'Evolution %']
                available = [c for c in display_cols if c in ca_mag.columns]
                st.dataframe(ca_mag[available].style.format({'CA N': '{:,.0f}', 'Poids %': '{:.1f}%', 'Evolution %': '{:+.1f}%'}, na_rep='—'), use_container_width=True, height=400)
            # Poids Convention / CA EM par magasin (cube x VC, jours communs)
            if not ctx.df_cube_mag.empty and 'Magasin' in ctx.df_cube_mag.columns:
                section('Poids Convention / CA EM par magasin')
                _scope_vc = ctx.df_vc.copy()
                if ctx.mois_sel and 'Mois' in _scope_vc.columns:
                    _scope_vc = _scope_vc[_scope_vc['Mois'].isin(ctx.mois_sel)]
                _poids = poids_convention_cube(ctx.df_cube_mag, _scope_vc,
                                               ctx.annee_sel, ctx.mois_sel or None)
                if _poids['ca_total'] > 0 and not _poids['detail'].empty:
                    _det = _poids['detail'].copy()
                    _pct_txt = f"{_poids['poids_pct']:.1f}%" if pd.notna(_poids['poids_pct']) else '—'
                    if _poids.get('jours'):
                        st.caption(f"Scope commun : {_poids['jours']} jours ({_poids['periode']}) — conventions = EM uniquement.")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric('⚖️ Poids Convention', _pct_txt)
                    c2.metric('🧾 CA Total EM (cube)', f"{_poids['ca_total']:,.0f} TND")
                    c3.metric('🏛️ CA Convention', f"{_poids['ca_conv']:,.0f} TND")
                    c4.metric('💵 CA Comptant estimé', f"{_poids['ca_comptant']:,.0f} TND")
                    if _poids['nb_alertes']:
                        st.warning(f"⚠️ {_poids['nb_alertes']} magasin(s) avec CA Convention > CA Total cube — à contrôler (mapping ou décalage de dates).")
                    _top = _det.head(15).copy()
                    fig_stack = go.Figure()
                    fig_stack.add_trace(go.Bar(x=_top['Magasin'], y=_top['CA Convention'], name='Convention', marker_color=C['purple']))
                    fig_stack.add_trace(go.Bar(x=_top['Magasin'], y=_top['CA Comptant'], name='Comptant estimé', marker_color=C['slate']))
                    fig_stack.update_layout(barmode='stack', height=380, title='Top 15 — Convention vs Comptant estimé',
                                            margin=dict(l=10, r=10, t=40, b=90), xaxis=dict(tickangle=45))
                    st.plotly_chart(fig_stack, use_container_width=True)
                    with st.expander('📋 Détail poids par magasin'):
                        st.dataframe(_det.style.format({'CA Total': '{:,.0f}', 'CA Convention': '{:,.0f}', 'CA Comptant': '{:,.0f}', 'Poids Conv %': '{:.1f}%'}, na_rep='—'), use_container_width=True, height=400)
                        csv = _det.to_csv(index=False).encode('utf-8')
                        st.download_button('📥 Export CSV poids', data=csv, file_name='poids_convention_magasins.csv', mime='text/csv')
        else:
            store_n = _base_n[_base_n['Magasin'] == selected_store]
            store_n1 = _base_n1[_base_n1['Magasin'] == selected_store]
            enseigne = store_n['Enseigne'].iloc[0] if 'Enseigne' in store_n.columns and len(store_n) > 0 else 'N/A'
            st.markdown(f"## 🏪 {selected_store} &nbsp;<span style='background:#1D4ED8;color:white;padding:2px 10px;border-radius:4px;font-size:11px'>{enseigne}</span>", unsafe_allow_html=True)
            ca_n_s = store_n['Montant TTC'].sum() if len(store_n) > 0 else 0
            ca_n1_s = store_n1['Montant TTC'].sum() if len(store_n1) > 0 else 0
            evol_s = evol_pct(ca_n_s, ca_n1_s)
            nb_fact_s = len(store_n)
            panier_s = ca_n_s / nb_fact_s if nb_fact_s > 0 else 0
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric(f'💰 CA {ctx.annee_sel}', f'{ca_n_s:,.0f} TND', fmt_pct(evol_s), delta_color=color_delta(evol_s))
            k2.metric(f'📅 CA {ctx.annee_sel - 1}', f'{ca_n1_s:,.0f} TND')
            k3.metric('🧾 Factures', nb_fact_s)
            k4.metric('📊 Panier moyen', f'{panier_s:,.0f} TND')
            k5.metric('🏷️ Enseigne', enseigne)
            # Poids Convention / CA global du magasin (cube x VC)
            if not ctx.df_cube_mag.empty and 'Magasin' in ctx.df_cube_mag.columns:
                _cube_s = ctx.df_cube_mag[ctx.df_cube_mag['Magasin'] == selected_store]
                if ctx.mois_sel and 'Mois' in _cube_s.columns:
                    _cube_s = _cube_s[_cube_s['Mois'].isin(ctx.mois_sel)]
                _tot_s = float(_cube_s['CA Magasin'].sum()) if not _cube_s.empty else 0.0
                if _tot_s > 0:
                    _compt_s = max(_tot_s - float(ca_n_s), 0.0)
                    _pct_s = float(ca_n_s) / _tot_s * 100
                    st.info(f"⚖️ Poids Convention / CA global — {selected_store} : **{_pct_s:.1f}%** "
                            f"(Conv {float(ca_n_s):,.0f} / Total cube {_tot_s:,.0f} TND — Comptant estimé {_compt_s:,.0f} TND)"
                            + (" — ⚠️ Conv > Total (écart périmètre)" if float(ca_n_s) > _tot_s else ""))
            if 'Mois' in store_n.columns:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    ca_mens = store_n.groupby('Mois')['Montant TTC'].sum().reset_index()
                    ca_mens['Mois_nom'] = ca_mens['Mois'].map(MOIS)
                    ca_mens_n1_v = store_n1.groupby('Mois')['Montant TTC'].sum().reindex(ca_mens['Mois']).fillna(0).values
                    ca_mens[f'CA {ctx.annee_sel - 1}'] = ca_mens_n1_v
                    fig_mens = px.bar(ca_mens, x='Mois_nom', y=['Montant TTC', f'CA {ctx.annee_sel - 1}'], title=f'CA Mensuel', barmode='group', text_auto='.0f', color_discrete_map={'Montant TTC': '#1D4ED8', f'CA {ctx.annee_sel - 1}': '#94A3B8'})
                    fig_mens.update_layout(height=260, showlegend=False)
                    st.plotly_chart(fig_mens, use_container_width=True)
                with col_c2:
                    ca_cum = store_n.groupby('Mois')['Montant TTC'].sum().cumsum().reset_index()
                    ca_cum['Mois_nom'] = ca_cum['Mois'].map(MOIS)
                    fig_cum = px.line(ca_cum, x='Mois_nom', y='Montant TTC', title='CA Cumulé', markers=True)
                    fig_cum.update_traces(line_color='#1D4ED8', line_width=3)
                    fig_cum.update_layout(height=260)
                    st.plotly_chart(fig_cum, use_container_width=True)
            st.markdown('### 🏛️ Conventions')
            if 'Type vente à crédit' in store_n.columns:
                mk = store_n['Type vente à crédit'].fillna('').str.upper().str.contains('CONV')
                conv_n = store_n[mk]
                if 'Nom' in conv_n.columns and len(conv_n) > 0:
                    detail = conv_n.groupby('Nom').agg(Montant_TTC=('Montant TTC', 'sum'), Nb_Factures=('Montant TTC', 'count'), Derniere_Vente=('Date', 'max')).reset_index()
                    detail.columns = ['Convention', 'Montant TTC', 'Nb Factures', 'Dernière Vente']
                    detail = detail.sort_values('Montant TTC', ascending=False)
                    detail['Montant TTC'] = detail['Montant TTC'].apply(lambda x: f'{x:,.0f}')
                    detail['Dernière Vente'] = detail['Dernière Vente'].dt.strftime('%d/%m/%Y')
                    st.dataframe(detail, use_container_width=True, height=min(300, 35 * (len(detail) + 1)))
                else:
                    st.info('Aucune convention sur la période.')
            st.markdown('### 💳 Autres segments')

            @st.cache_data(show_spinner=False)
            def _cached_segment_kpis(df_src_val, store, _df_vc_ref, annee, mois_tuple):
                df_n = pd.DataFrame()
                df_n1 = pd.DataFrame()
                if 'Unite Code' in df_src_val.columns:
                    code_col = next((c for c in _df_vc_ref.columns if c.lower() == 'unite code'), None)
                    if code_col and 'Magasin' in _df_vc_ref.columns:
                        codes = _df_vc_ref[_df_vc_ref['Magasin'] == store][code_col].dropna().unique()
                        if len(codes) > 0:
                            sc = [str(c).strip() for c in codes]
                            scf = [c + '.0' if not c.endswith('.0') else c for c in sc]
                            match = df_src_val['Unite Code'].astype(str).str.strip().isin(sc + scf)
                            df_n = df_src_val[match & (df_src_val['Année'] == annee)]
                            df_n1 = df_src_val[match & (df_src_val['Année'] == annee - 1)]
                if df_n.empty:
                    return ('empty', 0, 0, 0, 0)
                ml = list(mois_tuple) if mois_tuple else None
                if ml:
                    df_n = df_n[df_n['Mois'].isin(ml)]
                    df_n1 = df_n1[df_n1['Mois'].isin(ml)]
                if len(df_n) > 0 and 'Jour' in df_n.columns and (len(df_n1) > 0):
                    comp = compare_years_date_to_date(pd.concat([df_n, df_n1]), annee, annee - 1, ml)
                    ca_n_val = comp['CA N'].sum() if not comp.empty else 0
                    ca_n1_val = comp['CA N-1'].sum() if not comp.empty else 0
                else:
                    ca_n_val = df_n['Montant TTC'].sum() if len(df_n) > 0 else 0
                    ca_n1_val = df_n1['Montant TTC'].sum() if len(df_n1) > 0 else 0
                ev = evol_pct(ca_n_val, ca_n1_val)
                nb = len(df_n)
                pm = ca_n_val / nb if nb > 0 else 0
                return ('ok', ca_n_val, ca_n1_val, ev, nb, pm)

            def _segment_expander(label, icon, df_src):
                with st.expander(f'{icon} {label}', expanded=False):
                    mo_tup = tuple(ctx.mois_sel) if ctx.mois_sel else ()
                    result = _cached_segment_kpis(df_src, selected_store, ctx.df_vc, ctx.annee_sel, mo_tup)
                    status = result[0]
                    if status == 'empty':
                        st.info(f'Aucune donnée {label} pour ce magasin.')
                        return
                    _, ca_n_val, ca_n1_val, ev, nb, pm = result
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f'{icon} Dossiers', nb)
                    c2.metric(f'💰 CA {ctx.annee_sel}', f'{ca_n_val:,.0f} TND', fmt_pct(ev) if ca_n_val > 0 else None, delta_color=color_delta(ev))
                    c3.metric(f'📅 CA {ctx.annee_sel - 1}', f'{ca_n1_val:,.0f} TND')
                    c4.metric('📊 Panier moyen', f'{pm:,.0f} TND' if nb > 0 else '0 TND')
            _segment_expander('Crédit Conso', '💳', ctx.df_credit)
            _segment_expander('Crédit Particulier', '👤', ctx.df_credit_part)
            _segment_expander('Convention EDC', '🏫', ctx.df_edc)
            with st.expander('📄 Détail des opérations'):
                cols_show = [c for c in store_n.columns if c in ['Date', 'Mois', 'Nom', 'Montant TTC', 'Type vente à crédit', 'Enseigne']]
                st.dataframe(store_n[cols_show].sort_values('Date', ascending=False), use_container_width=True)
    with st.expander('📊 Consolidation multi-sources (Crédit, EDC, Particulier)', expanded=False):
        'Vue consolidée tous types de financement (ex-Tab Pilotage)'
        df_vc_tmp = ctx.df_vc.copy()
        df_cr_tmp = ctx.df_credit.copy()
        df_edc_tmp = ctx.df_edc.copy()
        df_part_tmp = ctx.df_credit_part.copy()
        TYPE_MAP = {'vc': 'Convention', 'vc_credit': 'Crédit Conso UBCI', 'vc_part': 'Crédit Particulier', 'vc_edc': 'EDC'}

        def _prep_source(df, df_code, src_key):
            if df.empty:
                return pd.DataFrame()
            df = df.copy()
            date_col = next((c for c in df.columns if 'date' in c.lower()), None)
            ca_col = next((c for c in df.columns if 'montant' in c.lower() or 'ca' in c.lower()), None)
            mag_col = next((c for c in df.columns if c.lower() == 'code magasin'.lower()), None)
            if not mag_col:
                mag_col = next((c for c in df.columns if 'code' in c.lower() and 'magasin' in c.lower()), None)
            if date_col and ca_col and mag_col:
                try:
                    df['_date'] = pd.to_datetime(df[date_col], errors='coerce')
                except Exception:
                    df['_date'] = pd.NaT
                df['_ca'] = pd.to_numeric(df[ca_col], errors='coerce')
                if not df_code.empty:
                    code_col = next((c for c in df_code.columns if 'code' in c.lower()), None)
                    name_col = next((c for c in df_code.columns if c != code_col), None)
                    if code_col and name_col:
                        mapping = df_code.set_index(code_col)[name_col].to_dict()
                        df['_code_mag'] = df[mag_col].astype(str).str.strip()
                        df['_nom_mag'] = df[mag_col].astype(str).str.strip().map(mapping).fillna(df['_code_mag'])
                    else:
                        df['_code_mag'] = df[mag_col].astype(str)
                        df['_nom_mag'] = df[mag_col].astype(str)
                else:
                    df['_code_mag'] = df[mag_col].astype(str)
                    df['_nom_mag'] = df[mag_col].astype(str)
                df['_type'] = TYPE_MAP.get(src_key, src_key)
                return df[['_date', '_ca', '_code_mag', '_nom_mag', '_type']]
            return pd.DataFrame()
        sources = [('vc', df_vc_tmp), ('vc_credit', df_cr_tmp), ('vc_part', df_part_tmp), ('vc_edc', df_edc_tmp)]
        df_all_list = []
        for key, df_src in sources:
            prepped = _prep_source(df_src, ctx.code_df, key)
            if not prepped.empty:
                df_all_list.append(prepped)
        if df_all_list:
            df_consol = pd.concat(df_all_list, ignore_index=True, copy=False)
        else:
            df_consol = pd.DataFrame()
        if df_consol.empty:
            st.warning('⚠️ Aucune donnée disponible.')
        else:
            df_consol['Année'] = df_consol['_date'].dt.year
            df_consol['Mois'] = df_consol['_date'].dt.month
            df_consol['JMois'] = df_consol['_date'].dt.to_period('M').astype(str)
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                all_magasins = sorted(df_consol['_nom_mag'].dropna().unique().tolist())
                mag_sel_x = st.multiselect('Magasin(s)', all_magasins, default=[], key='consol_mag')
            with col_f2:
                min_d = df_consol['_date'].min()
                max_d = df_consol['_date'].max()
                if pd.notna(min_d) and pd.notna(max_d):
                    date_range_x = st.date_input('Période', value=(min_d.date(), max_d.date()), key='consol_date')
                    date_deb_x, date_fin_x = (date_range_x[0], date_range_x[1] if len(date_range_x) == 2 else (None, None))
                else:
                    date_deb_x, date_fin_x = (None, None)
            with col_f3:
                all_mois = sorted(df_consol['Mois'].dropna().unique().tolist())
                mois_sel_x = st.multiselect('Mois', all_mois, default=all_mois, format_func=lambda x: MOIS.get(x, str(x)), key='consol_mois')
            df_f = df_consol.copy()
            if mag_sel_x:
                df_f = df_f[df_f['_nom_mag'].isin(mag_sel_x)]
            if mois_sel_x:
                df_f = df_f[df_f['Mois'].isin(mois_sel_x)]
            if date_deb_x and date_fin_x:
                df_f = df_f[(df_f['_date'] >= pd.Timestamp(date_deb_x)) & (df_f['_date'] <= pd.Timestamp(date_fin_x))]
            df_f['_ca'] = pd.to_numeric(df_f['_ca'], errors='coerce')
            df_f = df_f.dropna(subset=['_ca'])
            if df_f.empty:
                st.info('Aucune transaction pour les filtres sélectionnés.')
            else:
                an = int(ctx.annee_sel)
                an1 = an - 1
                st.markdown('##### Répartition CA par type de financement')
                ca_by_type = df_f[df_f['Année'] == an].groupby('_type')['_ca'].sum().reset_index()
                ca_by_type.columns = ['Type', 'CA']
                ca_by_type['%'] = (ca_by_type['CA'] / ca_by_type['CA'].sum() * 100).round(1)
                pc1, pc2 = st.columns([1, 1])
                with pc1:
                    fig_pie = px.pie(ca_by_type, values='CA', names='Type', hole=0.4, color_discrete_sequence=[C['blue'], C['green'], C['purple'], C['amber']])
                    fig_pie.update_layout(margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_pie, use_container_width=True)
                with pc2:
                    st.dataframe(ca_by_type.rename(columns={'CA': 'CA (TND)'}), use_container_width=True)
                st.markdown('##### CA par type — même période')
                available_types = [t for t in TYPE_MAP.values() if t in df_f['_type'].unique()]
                col_types = st.columns(len(available_types)) if available_types else [st.columns(1)]
                for idx, type_label in enumerate(available_types):
                    df_t = df_f[df_f['_type'] == type_label]
                    with col_types[idx]:
                        st.markdown(f'**{type_label}**')
                        if df_t.empty:
                            st.info(f'Aucune donnée')
                            continue
                        ca_t = df_t[df_t['Année'] == an]['_ca'].sum()
                        ca_t1 = df_t[df_t['Année'] == an1]['_ca'].sum()
                        evo_t = evol_pct(ca_t, ca_t1)
                        nb_t = len(df_t[df_t['Année'] == an])
                        pan_t = ca_t / nb_t if nb_t > 0 else 0
                        st.metric(f'CA {an}', f'{ca_t:,.0f} TND', fmt_pct(evo_t), delta_color=color_delta(evo_t))
                        st.metric(f'CA {an1}', f'{ca_t1:,.0f} TND')
                        st.metric('Transactions', nb_t)
                        st.metric('Panier moyen', f'{pan_t:,.0f} TND')
                        pie_data = df_t.groupby('_nom_mag')['_ca'].sum().reset_index()
                        pie_data.columns = ['Magasin', 'CA']
                        if not pie_data.empty:
                            fig_p = px.pie(pie_data.head(10), values='CA', names='Magasin', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
                            fig_p.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=300)
                            st.plotly_chart(fig_p, use_container_width=True, key=f'consol_pie_{type_label}')
                st.markdown('##### Tableau détaillé')
                detail = df_f[df_f['Année'] == an].groupby(['_nom_mag', '_type'])['_ca'].sum().reset_index()
                detail.columns = ['Magasin', 'Type', 'CA']
                detail['%'] = (detail['CA'] / detail['CA'].sum() * 100).round(2)
                detail = detail.sort_values('CA', ascending=False)
                st.dataframe(detail, use_container_width=True)
                csv = detail.to_csv(index=False).encode('utf-8')
                st.download_button('📥 Export CSV', data=csv, file_name='pilotage_magasin.csv', mime='text/csv')

    def _render_enseigne_section(enseigne, color_scale):
        _df = ctx.df_vc_filt[ctx.df_vc_filt['Enseigne'] == enseigne].copy()
        if _df.empty:
            st.caption(f'Aucune donnée {enseigne} disponible.')
            return
        _d2d = truncate_n1_date_to_date(_df, ctx.annee_sel, ctx.annee_sel - 1, ctx.mois_sel)
        _n = _d2d[_d2d['Année'] == ctx.annee_sel]
        _n1 = _d2d[_d2d['Année'] == ctx.annee_sel - 1]
        _ca_n = _n['Montant TTC'].sum()
        _ca_n1 = _n1['Montant TTC'].sum()
        _ev = evol_pct(_ca_n, _ca_n1)
        _nb_mag = _n['Magasin'].nunique()
        _nb_mag_n1 = _n1['Magasin'].nunique()
        _part = _ca_n / ctx.df_vc[ctx.df_vc['Année'] == ctx.annee_sel]['Montant TTC'].sum() * 100 if not ctx.df_vc[ctx.df_vc['Année'] == ctx.annee_sel].empty else 0
        _c1, _c2, _c3, _c4, _c5 = st.columns(5)
        _c1.metric(f'CA {enseigne} {ctx.annee_sel}', f'{_ca_n:,.0f}', fmt_pct(_ev), delta_color=color_delta(_ev))
        _c2.metric(f'CA {enseigne} {ctx.annee_sel - 1}', f'{_ca_n1:,.0f}')
        _c3.metric('Magasins actifs', _nb_mag, f'{_nb_mag - _nb_mag_n1:+d} vs N-1')
        _c4.metric('Part du CA total', f'{_part:.1f}%')
        _c5.metric('Panier moyen', f'{_ca_n / len(_n):,.0f}' if len(_n) > 0 else '0')
        _t = _df[_df['Année'].isin([ctx.annee_sel, ctx.annee_sel - 1])]
        _t = _t.groupby(['Année', 'Mois'])['Montant TTC'].sum().reset_index()
        fig_t = go.Figure()
        for yr in [ctx.annee_sel, ctx.annee_sel - 1]:
            _by = _t[_t['Année'] == yr]
            fig_t.add_trace(go.Bar(x=_by['Mois'], y=_by['Montant TTC'], name=str(yr), marker_color=C['blue'] if yr == ctx.annee_sel else C['slate'], opacity=0.8 if yr == ctx.annee_sel else 0.5))
        fig_t.update_layout(height=250, barmode='group', xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), ticktext=[MOIS[i] for i in range(1, 13)]), margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_t, use_container_width=True)
        _top = _n.groupby('Magasin')['Montant TTC'].sum().nlargest(10).reset_index()
        if not _top.empty:
            fig_tp = px.bar(_top, x='Montant TTC', y='Magasin', orientation='h', title=f'Top 10 Magasins {enseigne} — {ctx.annee_sel}', color='Montant TTC', color_continuous_scale=color_scale, text_auto='.0f')
            fig_tp.update_layout(height=420, yaxis=dict(autorange='reversed'), margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_tp, use_container_width=True)
    section('BATAM — Performance réseau')
    _render_enseigne_section('BATAM', ['#D97706', '#F59E0B'])
    section('MG — Performance réseau')
    _render_enseigne_section('MG', ['#1D4ED8', '#3B82F6', '#60A5FA'])