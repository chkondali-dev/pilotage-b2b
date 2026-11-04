from metrics.kpi import evol_pct
from trend_alert_panel import render_alert_panel
from ui.components import section
import streamlit as st


@st.cache_data(show_spinner=False)
def _cached_scan_all(df_vc_in, df_edc_in, df_conv_in, df_code_in):
    """Scan tendances TrendAnalyzer — recalculé uniquement si les entrées changent."""
    from trend_analyzer import TrendAnalyzer
    ta = TrendAnalyzer(df_vc=df_vc_in, df_edc=df_edc_in, conventions=df_conv_in, code_magasin=df_code_in)
    return ta.scan_all()


def render(ctx):
    ca_n = ctx.ca_n
    ca_n1 = ctx.ca_n1
    st.markdown('### 🚨 Alertes Tendances')
    try:
        with st.spinner('Analyse des tendances...'):
            alerts = _cached_scan_all(ctx.df_vc, ctx.df_edc, ctx.df_conv, ctx.code_df)
            if 'Nom' in ctx.df_vc_filt.columns:
                _df_ytd_n = ctx.df_vc_filt[ctx.df_vc_filt['Année'] == ctx.annee_sel].copy()
                _df_ytd_n1 = ctx.df_vc_filt[ctx.df_vc_filt['Année'] == ctx.annee_sel - 1].copy()
                if ctx.mois_sel and len(ctx.mois_sel) > 0:
                    _df_ytd_n = _df_ytd_n[_df_ytd_n['Mois'].isin(ctx.mois_sel)]
                    _df_ytd_n1 = _df_ytd_n1[_df_ytd_n1['Mois'].isin(ctx.mois_sel)]
                if 'Jour' in _df_ytd_n.columns and (not _df_ytd_n.empty):
                    _conv_jours = _df_ytd_n.groupby(['Nom', 'Mois'])['Jour'].apply(max).to_dict()
                else:
                    _conv_jours = {}
                _ytd_index = {}
                _ytd_orig = {}
                for (n, m), jours in _conv_jours.items():
                    key = str(n).strip().upper()
                    if key not in _ytd_index:
                        _ytd_index[key] = {}
                        _ytd_orig[key] = n
                    _ytd_index[key][m] = jours
                for a in alerts.get('convention_alerts', []):
                    nom = str(a.get('nom', '')).strip().upper()
                    if not nom or nom not in _ytd_index:
                        continue
                    orig = _ytd_orig[nom]
                    dn = _df_ytd_n[_df_ytd_n['Nom'] == orig]
                    dn1 = _df_ytd_n1[_df_ytd_n1['Nom'] == orig]
                    if dn.empty:
                        continue
                    ca_n = float(dn['Montant TTC'].sum())
                    ca_n1 = 0.0
                    for m, max_jour in _ytd_index[nom].items():
                        ca_n1 += float(dn1[(dn1['Mois'] == m) & (dn1['Jour'] <= int(max_jour))]['Montant TTC'].sum())
                    evo = evol_pct(ca_n, ca_n1)
                    a['metrics']['ytd_change_pct'] = evo
            render_alert_panel(alerts, df=ctx.df_vc, annee_n=ctx.annee_sel)
    except Exception as e:
        st.warning(f'Analyse des tendances indisponible: {e}')
    section('Anomalies — Factures outliers')
    _out = ctx.df_vc[ctx.df_vc['Année'] == ctx.annee_sel].copy()
    if not _out.empty and 'Montant TTC' in _out.columns and ('Magasin' in _out.columns):
        _out_stats = _out.groupby('Magasin')['Montant TTC'].agg(['mean', 'std', 'count']).reset_index()
        _out_stats.columns = ['Magasin', 'Moyenne', 'Ecart_type', 'Nb']
        _out_stats = _out_stats[_out_stats['Ecart_type'] > 0]
        if not _out_stats.empty:
            _out_merged = _out.merge(_out_stats[['Magasin', 'Moyenne', 'Ecart_type']], on='Magasin')
            _out_merged['Z_score'] = abs(_out_merged['Montant TTC'] - _out_merged['Moyenne']) / _out_merged['Ecart_type']
            _outliers = _out_merged[_out_merged['Z_score'] > 3].copy()
            _outliers['Écart %'] = ((_outliers['Montant TTC'] - _outliers['Moyenne']) / _outliers['Moyenne'] * 100).round(1)
            if len(_outliers) > 0:
                st.caption(f'{len(_outliers)} factures anormales détectées (|Z|>3, σ par magasin)')
                _od = _outliers.sort_values('Z_score', ascending=False).head(20)
                _od['Montant TTC'] = _od['Montant TTC'].round(0)
                _od['Moyenne'] = _od['Moyenne'].round(0)
                cols_o = [c for c in ['Nom', 'Magasin', 'Montant TTC', 'Moyenne', 'Écart %', 'Date'] if c in _od.columns]
                st.dataframe(_od[cols_o], use_container_width=True, height=300, column_config={'Montant TTC': st.column_config.NumberColumn(format='%d'), 'Moyenne': st.column_config.NumberColumn(format='%d')})
            else:
                st.caption('Aucune anomalie détectée sur la période.')
        else:
            st.caption('Pas assez de données par magasin.')
    else:
        st.caption('Données insuffisantes.')