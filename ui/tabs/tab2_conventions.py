from data.config import C
from data.config import MOIS
from ui.components import badge
from metrics.kpi import ca_sum_date_to_date
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
import numpy as np
import pandas as pd
import plotly.express as px
from ui.components import section
import streamlit as st
from metrics.kpi import truncate_n1_date_to_date


def render(ctx):
    _src_filt = ctx.df_vc_filt.copy()
    if ctx.conv_sel != 'Tous':
        _src_filt = _src_filt[_src_filt['Nom'] == ctx.conv_sel]
    ca_total_n, ca_total_n1, ev_total = ca_sum_date_to_date(_src_filt, ctx.annee_sel, ctx.annee_sel - 1, ctx.mois_sel)
    _rm = ctx.risk_mat.copy() if not ctx.risk_mat.empty else pd.DataFrame()
    if ctx.conv_sel != 'Tous' and (not _rm.empty):
        _rm = _rm[_rm['Nom'] == ctx.conv_sel]
    nb_convs = len(_rm[_rm['CA N'] > 0]) if not _rm.empty else 0
    with st.expander('🔍 Debug TAB 2', expanded=False):
        st.write('**conv_sel (sidebar) :**', ctx.conv_sel)
        st.write('**type_vente_sel :**', ctx.type_vente_sel)
        st.write('**mois_sel :**', ctx.mois_sel)
        st.write('**df_vc_filt shape :**', ctx.df_vc_filt.shape)
        if 'Nom' in ctx.df_vc_filt.columns:
            st.write('**Conventions dispo :**', sorted(ctx.df_vc_filt['Nom'].dropna().unique()))
        st.write('**risk_mat shape :**', ctx.risk_mat.shape if not ctx.risk_mat.empty else 'EMPTY')
        st.write('**_rm shape :**', _rm.shape if not _rm.empty else 'EMPTY')
        if not _rm.empty:
            st.write('**_rm Noms :**', _rm['Nom'].tolist())
            st.write('**_rm CA N :**', _rm['CA N'].tolist())
        st.write('**ca_total_n :**', ca_total_n)
        st.write('**nb_convs :**', nb_convs)
    if not _rm.empty:
        risky = _rm[_rm['Statut'].str.contains('Déclin|Inactif', na=False)]
        nb_risky = len(risky)
    else:
        nb_risky = 0
    section('Portefeuille conventions — Vue synthétique')
    pk1, pk2, pk3, pk4 = st.columns(4)
    pk1.metric('📋 Conventions actives', nb_convs)
    pk2.metric('💰 CA Total N', f'{ca_total_n:,.0f} TND', fmt_pct(ev_total), delta_color=color_delta(ev_total))
    pk3.metric('⚠️ À risque', nb_risky, delta_color='inverse' if nb_risky > 0 else 'off')
    pk4.metric('🔄 Inactives', ctx.nb_inact, delta_color='inverse' if ctx.nb_inact > 0 else 'off')
    if not _rm.empty:
        top10 = _rm.nlargest(10, 'CA N')[['Nom', 'CA N', 'Évolution %', 'Statut']].copy()
        top10 = top10.sort_values('CA N', ascending=True)
        fig_top = px.bar(top10, x='CA N', y='Nom', orientation='h', title='Top 10 conventions par CA', color='Statut', text_auto='.0f', color_discrete_map={'✅ Croissance': C['green'], '📉 Déclin': C['amber'], '⚠️ Déclin fort': C['red'], '🆕 Nouveau': C['blue'], '❌ Inactif': '#9CA3AF', '❓ Aucun historique': '#D1D5DB'}, height=400)
        fig_top.update_layout(xaxis_title='CA N (TND)', yaxis_title='', legend=dict(orientation='h', y=-0.15, x=0, font=dict(size=11)))
        fig_top.update_traces(marker=dict(line=dict(width=0.5, color='white')))
        st.plotly_chart(fig_top, use_container_width=True)
    _coh = cohortes_conventions(ctx.df_vc_filt, ctx.annee_sel, mois_sel=ctx.mois_sel)
    if not _coh.empty:
        section('Segments — Ancienneté des conventions')
        _cc1, _cc2 = st.columns([2, 1])
        with _cc1:
            fig_coh = px.bar(_coh, x='Cohorte', y='CA N', color='Cohorte', title=f'CA {ctx.annee_sel} par cohorte', text_auto='.0f', height=320, color_discrete_map={'✅ Fidèles': C['green'], '🆕 Nouvelles': C['blue'], '🔄 Revenantes': C['amber'], '❌ Perdues': C['slate']})
            fig_coh.update_layout(xaxis_title='', yaxis_title='CA N (TND)', showlegend=False)
            st.plotly_chart(fig_coh, use_container_width=True)
        with _cc2:
            _coh_disp = _coh.drop(columns=['__detail__'], errors='ignore')
            st.dataframe(_coh_disp.style.format({'CA N': '{:,.0f}', 'CA N-1': '{:,.0f}', 'Variation %': '{:+.1f}%', 'Poids % N': '{:.1f}%'}, na_rep='—'), use_container_width=True, hide_index=True)
        if '__detail__' in _coh.columns:
            _seg_labels = _coh['Cohorte'].tolist()
            _seg_choice = st.selectbox("Voir le détail d'un segment", ['— Choisir —'] + _seg_labels, key='seg_detail_choice')
            if _seg_choice != '— Choisir —':
                _recs = _coh.loc[_coh['Cohorte'] == _seg_choice, '__detail__'].iloc[0]
                _rows = pd.DataFrame(_recs, columns=['Nom', 'Cohorte', 'CA N', 'CA N-1'])
                _rows = _rows.sort_values('CA N', ascending=False)
                _rows['Évolution %'] = np.where(_rows['CA N-1'] > 0, (_rows['CA N'] - _rows['CA N-1']) / _rows['CA N-1'] * 100, np.nan).round(1)

                @st.dialog(f'{_seg_choice} — {_rows.shape[0]} convention(s)')
                def _show_seg():
                    st.dataframe(_rows[['Nom', 'CA N', 'CA N-1', 'Évolution %']].style.format({'CA N': '{:,.0f}', 'CA N-1': '{:,.0f}', 'Évolution %': '{:+.1f}%'}, na_rep='—'), use_container_width=True, hide_index=True)
                    _csv = _rows[['Nom', 'CA N', 'CA N-1', 'Évolution %']].to_csv(index=False).encode('utf-8')
                    st.download_button('Télécharger (CSV)', data=_csv, file_name=f'segment_{_seg_choice}.csv', mime='text/csv')
                _show_seg()
    if not _rm.empty and 'CA N' in _rm.columns and ('CA N-1' in _rm.columns):
        section('Top hausses / pertes — Variation en TND')
        _rm_tnd = _rm.copy()
        _rm_tnd['Δ CA (TND)'] = _rm_tnd['CA N'] - _rm_tnd['CA N-1']
        _gains = _rm_tnd[_rm_tnd['Δ CA (TND)'] > 0].nlargest(5, 'Δ CA (TND)')
        _pertes = _rm_tnd[_rm_tnd['Δ CA (TND)'] < 0].nsmallest(5, 'Δ CA (TND)')
        _tot_g = float(_rm_tnd.loc[_rm_tnd['Δ CA (TND)'] > 0, 'Δ CA (TND)'].sum())
        _tot_p = float(_rm_tnd.loc[_rm_tnd['Δ CA (TND)'] < 0, 'Δ CA (TND)'].sum())
        _tg1, _tg2 = st.columns(2)
        with _tg1:
            st.markdown(f'**📈 Top 5 hausses** — total +{_tot_g:,.0f} TND')
            if not _gains.empty:
                st.dataframe(_gains[['Nom', 'CA N', 'CA N-1', 'Δ CA (TND)', 'Évolution %']].style.format({'CA N': '{:,.0f}', 'CA N-1': '{:,.0f}', 'Δ CA (TND)': '{:+,.0f}', 'Évolution %': '{:+.1f}%'}, na_rep='—'), use_container_width=True, hide_index=True)
            else:
                st.caption('Aucune hausse vs N-1.')
        with _tg2:
            st.markdown(f'**📉 Top 5 pertes** — total {_tot_p:,.0f} TND')
            if not _pertes.empty:
                st.dataframe(_pertes[['Nom', 'CA N', 'CA N-1', 'Δ CA (TND)', 'Évolution %']].style.format({'CA N': '{:,.0f}', 'CA N-1': '{:,.0f}', 'Δ CA (TND)': '{:+,.0f}', 'Évolution %': '{:+.1f}%'}, na_rep='—'), use_container_width=True, hide_index=True)
            else:
                st.caption('Aucune perte vs N-1.')
    section('Taux de conversion client — Effectif vs Acheteurs')
    _conv_rate = conversion_conventions(ctx.df_vc_filt, ctx.annee_sel, ctx.mois_sel if ctx.mois_sel else None)
    _kpi_conv = kpi_conversion_globale(_conv_rate)
    if not _conv_rate.empty:
        tg = _kpi_conv.get('Taux global %')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Taux de conversion global', f'{tg:.2f} %' if pd.notna(tg) else '—', help='Acheteurs distincts / Effectif total (conventions avec effectif > 0)')
        c2.metric('Acheteurs distincts', f"{_kpi_conv['Nb acheteurs']:,}".replace(',', ' '))
        c3.metric('Effectif total suivi', f"{_kpi_conv['Effectif total']:,}".replace(',', ' '))
        c4.metric('Conventions suivies', _kpi_conv['Nb conventions suivies'], f"{_kpi_conv['Nb sans effectif']} sans effectif" if _kpi_conv['Nb sans effectif'] else None)
        _top_conv = _conv_rate[_conv_rate['Effectif'] > 0].head(15).sort_values('Taux %', ascending=True)
        if not _top_conv.empty:
            fig_conv = px.bar(_top_conv, x='Taux %', y='Nom', orientation='h', title='Top 15 — Taux de conversion par convention', text='Taux %', height=450, hover_data=['Nb acheteurs', 'Effectif', 'Nb factures'])
            fig_conv.update_layout(xaxis_title='Taux % (acheteurs / effectif)', yaxis_title='')
            st.plotly_chart(fig_conv, use_container_width=True)
        _conv_show = _conv_rate.copy()
        if ctx.conv_sel != 'Tous':
            _conv_show = _conv_show[_conv_show['Nom'] == ctx.conv_sel]
        st.dataframe(_conv_show.style.format({'Effectif': '{:,.0f}', 'Nb acheteurs': '{:,.0f}', 'Nb factures': '{:,.0f}', 'Taux %': '{:.1f}%'}, na_rep='—'), use_container_width=True, height=350)
        st.caption('Source effectifs : data/effectifs_conventions.csv — « — » = effectif manquant ou nul. Acheteurs = N° Client distincts ayant acheté sur la période.')
        with st.expander('➕ Ajouter / corriger un effectif', expanded=False):
            _e1, _e2 = st.columns([2, 1])
            with _e1:
                _new_nom = st.selectbox('Convention', sorted(_conv_rate['Nom'].tolist()), key='eff_conv_nom')
            with _e2:
                _new_eff = st.number_input('Effectif', min_value=0, step=10, key='eff_conv_val')
            if st.button("Enregistrer l'effectif", key='eff_conv_save'):
                try:
                    import csv as _csv
                    from metrics.kpi import EFFECTIFS_PATH as _EFF_P
                    _rows = list(_csv.DictReader(open(_EFF_P, encoding='utf-8'), delimiter=';')) if _EFF_P.exists() else []
                    _upd = False
                    for _r in _rows:
                        if str(_r.get('societe', '')).strip().lower() == str(_new_nom).strip().lower():
                            _r['effectif'] = str(int(_new_eff))
                            _upd = True
                    if not _upd:
                        _rows.append({'societe': _new_nom, 'effectif': str(int(_new_eff))})
                    with open(_EFF_P, 'w', newline='', encoding='utf-8') as _f:
                        _w = _csv.DictWriter(_f, fieldnames=['societe', 'effectif'], delimiter=';')
                        _w.writeheader()
                        _w.writerows(_rows)
                    st.success(f'Effectif enregistré : {_new_nom} = {int(_new_eff)}')
                    st.cache_data.clear()
                    st.rerun()
                except Exception as _e:
                    st.error(f'Erreur : {_e}')
    else:
        st.caption('Aucune donnée de conversion sur la période.')
    section('Liste des conventions')
    conv_table = _rm.copy() if not _rm.empty else pd.DataFrame()
    if not conv_table.empty:
        if 'Magasin' in ctx.df_vc_filt.columns:
            mc = ctx.df_vc_filt.groupby('Nom')['Magasin'].nunique().reset_index()
            mc.columns = ['Nom', 'Nb magasins']
            conv_table = conv_table.merge(mc, on='Nom', how='left').fillna(0)
            conv_table['Nb magasins'] = conv_table['Nb magasins'].astype(int)
        if 'Date' in ctx.df_vc_filt.columns:
            lf = ctx.df_vc_filt.groupby('Nom')['Date'].max().reset_index()
            lf.columns = ['Nom', 'Dernière facture']
            conv_table = conv_table.merge(lf, on='Nom', how='left')
        search_c = st.text_input('🔍 Filtrer par nom', placeholder='Tapez un nom de convention...', label_visibility='collapsed')
        if search_c:
            conv_table = conv_table[conv_table['Nom'].str.contains(search_c, case=False, na=False)]
        cols_show = [c for c in ['Nom', 'CA N', 'CA N-1', 'Évolution %', 'Statut', 'Nb magasins', 'Dernière facture'] if c in conv_table.columns]
        st.dataframe(conv_table[cols_show].style.format({'CA N': '{:,.0f}', 'CA N-1': '{:,.0f}', 'Évolution %': '{:+.1f}%'}, subset=['CA N', 'CA N-1', 'Évolution %'], na_rep='—'), use_container_width=True, height=350)
    section('Analyse individuelle')
    conv_detail = None
    if ctx.conv_sel != 'Tous' and (not _rm.empty) and (ctx.conv_sel in _rm['Nom'].values):
        conv_detail = ctx.conv_sel
    elif not _rm.empty:
        _all = sorted(_rm['Nom'].tolist())
        conv_detail = st.selectbox('Sélectionner une convention', _all, index=0, key='conv_selector')
    if conv_detail:
        st.caption(f'Convention : **{conv_detail}**')
        df_cv = ctx.df_vc_filt[ctx.df_vc_filt['Nom'] == conv_detail].copy()
        ca_cv_n, ca_cv_n1, ev_cv = ca_sum_date_to_date(df_cv, ctx.annee_sel, ctx.annee_sel - 1, ctx.mois_sel)
        nb_fact_cv = len(df_cv[df_cv['Année'] == ctx.annee_sel])
        panier_cv = ca_cv_n / nb_fact_cv if nb_fact_cv > 0 else 0
        cv_statut = _rm[_rm['Nom'] == conv_detail]['Statut'].iloc[0] if not _rm.empty and conv_detail in _rm['Nom'].values else ''
        st.markdown(f"### {conv_detail} &nbsp;{badge(cv_statut, 'red' if 'Déclin' in cv_statut or 'Inactif' in cv_statut else 'green' if 'Croissance' in cv_statut else 'amber')}", unsafe_allow_html=True)
        ci1, ci2, ci3, ci4 = st.columns(4)
        ci1.metric(f'CA {ctx.annee_sel}', f'{ca_cv_n:,.0f} TND', f'{fmt_pct(ev_cv)} vs {ctx.annee_sel - 1}', delta_color=color_delta(ev_cv))
        ci2.metric(f'CA {ctx.annee_sel - 1}', f'{ca_cv_n1:,.0f} TND')
        ci3.metric(f'Factures {ctx.annee_sel}', nb_fact_cv)
        ci4.metric('Panier moyen', f'{panier_cv:,.0f} TND')
        _one = conversion_conventions(ctx.df_vc_filt[ctx.df_vc_filt['Nom'] == conv_detail], ctx.annee_sel, ctx.mois_sel if ctx.mois_sel else None)
        if not _one.empty:
            _r = _one.iloc[0]
            _eff = _r.get('Effectif')
            _ach = int(_r.get('Nb acheteurs', 0))
            _tx = _r.get('Taux %')
            t1, t2, t3 = st.columns(3)
            t1.metric('Taux de conversion', f'{_tx:.1f} %' if pd.notna(_tx) else '—', help='Acheteurs distincts / effectif total de la convention')
            t2.metric('Acheteurs', f'{_ach:,}'.replace(',', ' '))
            t3.metric('Effectif', f'{_eff:,.0f}' if pd.notna(_eff) and _eff else '—')
            if pd.isna(_tx):
                st.caption('Effectif manquant ou nul pour cette convention — renseignez-le dans la section « Taux de conversion client » ci-dessus.')
        col_cv1, col_cv2 = st.columns(2)
        df_cv_comp = compare_years_date_to_date(df_cv, ctx.annee_sel, ctx.annee_sel - 1, ctx.mois_sel)
        with col_cv1:
            fig_cv_g = chart_grouped_bar(df_cv_comp, 'Mois Nom', 'CA N', 'CA N-1', f'CA Mensuel — {conv_detail}', ctx.annee_sel)
            st.plotly_chart(fig_cv_g, use_container_width=True)
        with col_cv2:
            _df_fn = df_cv[df_cv['Année'] == ctx.annee_sel]
            _df_fn1 = truncate_n1_date_to_date(df_cv, ctx.annee_sel, ctx.annee_sel - 1, ctx.mois_sel)
            _df_fn1 = _df_fn1[_df_fn1['Année'] == ctx.annee_sel - 1]
            _cn = _df_fn.groupby('Mois')['Montant TTC'].sum().reset_index()
            _cn1 = _df_fn1.groupby('Mois')['Montant TTC'].sum().reset_index()
            _cn['CA Cum N'] = _cn['Montant TTC'].cumsum()
            _cn1['CA Cum N-1'] = _cn1['Montant TTC'].cumsum()
            df_cum = _cn[['Mois', 'CA Cum N']].merge(_cn1[['Mois', 'CA Cum N-1']], on='Mois', how='outer').ffill().fillna(0)
            df_cum['Mois Nom'] = df_cum['Mois'].map(MOIS)
            fig_cum = chart_line_compare(df_cum, 'Mois Nom', 'CA Cum N', 'CA Cum N-1', f'CA Cumulé — {conv_detail}', ctx.annee_sel)
            st.plotly_chart(fig_cum, use_container_width=True)
        col_cv3, col_cv4 = st.columns(2)
        with col_cv3:
            if 'Magasin' in df_cv.columns:
                mag = _df_fn.groupby('Magasin')['Montant TTC'].sum().nlargest(10).reset_index()
                if not mag.empty:
                    fig_mag_cv = chart_bar(mag, 'Montant TTC', 'Magasin', 'Top Magasins', C['purple'], h=360, orientation='h')
                    st.plotly_chart(fig_mag_cv, use_container_width=True)
                else:
                    st.info('Aucun magasin avec des transactions en N pour cette convention.')
        with col_cv4:
            ca_cash = _df_fn['Montant TTC'].sum() if len(_df_fn) > 0 else 0
            ca_credit = ctx.df_credit[ctx.df_credit['Nom'] == conv_detail]['Montant TTC'].sum() if 'Nom' in ctx.df_credit.columns else 0
            if ca_cash > 0 or ca_credit > 0:
                fig_pie_cv = chart_pie([ca_cash, ca_credit], ['Cash', 'Crédit'], f'Cash vs Crédit — {conv_detail}')
                st.plotly_chart(fig_pie_cv, use_container_width=True)
        st.markdown('### 🏪 Magasins contributeurs')
        if 'Magasin' in df_cv.columns and len(_df_fn) > 0:
            detail_m = _df_fn.groupby('Magasin').agg(Montant_TTC=('Montant TTC', 'sum'), Nb_Factures=('Montant TTC', 'count'), Derniere_Vente=('Date', 'max')).reset_index()
            detail_m.columns = ['Magasin', 'Montant TTC', 'Nb Factures', 'Dernière Vente']
            if len(_df_fn1) > 0:
                ca_n1_m = _df_fn1.groupby('Magasin')['Montant TTC'].sum().reset_index()
                ca_n1_m.columns = ['Magasin', 'CA N-1']
                detail_m = detail_m.merge(ca_n1_m, on='Magasin', how='left').fillna(0)
                detail_m['Évolution %'] = np.where(detail_m['CA N-1'] > 0, ((detail_m['Montant TTC'] - detail_m['CA N-1']) / detail_m['CA N-1'] * 100).round(1), np.nan)
                detail_m['CA N-1'] = detail_m['CA N-1'].apply(lambda x: f'{x:,.0f}' if x > 0 else '-')
            else:
                detail_m['CA N-1'] = '-'
                detail_m['Évolution %'] = np.nan
            detail_m = detail_m.sort_values('Montant TTC', ascending=False)
            detail_m['Montant TTC'] = detail_m['Montant TTC'].apply(lambda x: f'{x:,.0f}')
            detail_m['Dernière Vente'] = detail_m['Dernière Vente'].dt.strftime('%d/%m/%Y')
            detail_m['Évolution %'] = detail_m['Évolution %'].apply(lambda x: '—' if pd.isna(x) else f'{x:+.1f}%')
            st.dataframe(detail_m, use_container_width=True, height=min(400, 35 * (len(detail_m) + 1)))
        else:
            st.info('Aucune donnée magasin disponible pour cette convention.')