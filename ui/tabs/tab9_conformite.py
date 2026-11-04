from data.config import SEUILS
from metrics.kpi import alertes_achats_repetes
from charts.factory import chart_stacked_bar
import pandas as pd
from ui.components import section
import streamlit as st


def render(ctx):
    st.markdown('### 🛡️ Conformité 40% — Achats répétés')
    st.caption(f"Règle réglementaire : la retenue sur salaire d'un adhérent ne doit pas dépasser 40% de son salaire net (art. 5 des conventions). **🔴 Alerte** : ≥ {SEUILS['achats_annee_alerte']} achats à crédit par nom et par année · **🟡 À risque** : ≥ {SEUILS['achats_annee_risque']} — à vérifier manuellement auprès de l'Amicale (mensualité vs fiche de paie).")
    cc0, cc1, cc2 = st.columns([3, 2, 2])
    with cc0:
        _flux_conf = st.selectbox('Flux', options=['Crédit particulier', 'Conventions (VC)', 'Tous flux'], index=0, key='conf40_flux', help="Conventions (VC) = adhérents d'Amicales ; crédit particulier = individus.")
    with cc1:
        _seuil_alert = st.number_input('Seuil alerte 🔴', min_value=2, max_value=10, value=int(SEUILS['achats_annee_alerte']), step=1, help='Seuil par défaut centralisé dans data/config.py (SEUILS).', key='conf40_seuil')
    with cc2:
        _seuil_rq = st.number_input('Seuil risque 🟡', min_value=1, max_value=int(_seuil_alert), value=min(int(SEUILS['achats_annee_risque']), int(_seuil_alert)), step=1, key='conf40_seuil_rq')
    if _flux_conf == 'Conventions (VC)':
        _df_conf = ctx.df_vc.copy()
    elif _flux_conf == 'Tous flux':
        _pieces = [d for d in (ctx.df_credit_part, ctx.df_vc) if not d.empty]
        _df_conf = pd.concat(_pieces, ignore_index=True) if _pieces else pd.DataFrame()
    else:
        _df_conf = ctx.df_credit_part.copy()
    _annees_dispo = sorted((int(a) for a in _df_conf['Année'].dropna().unique())) if not _df_conf.empty and 'Année' in _df_conf.columns else []
    _an_conf = st.selectbox('Année', options=_annees_dispo, index=_annees_dispo.index(ctx.annee_sel) if ctx.annee_sel in _annees_dispo else 0, key='conf40_annee') if _annees_dispo else None
    _alertes = alertes_achats_repetes(_df_conf, annee=_an_conf, seuil=_seuil_alert, seuil_risque=_seuil_rq)
    _alertes_all = alertes_achats_repetes(_df_conf, seuil=_seuil_alert, seuil_risque=_seuil_rq)
    if _df_conf.empty:
        st.info('Aucune donnée disponible sur ce flux.')
    else:
        _n_al = int((_alertes['Niveau'] == '🔴 Alerte').sum()) if not _alertes.empty else 0
        _n_rq = int((_alertes['Niveau'] == '🟡 À risque').sum()) if not _alertes.empty else 0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"🔴 Alertes ({(_an_conf if _an_conf else 'toutes années')})", f'{_n_al:,}'.replace(',', ' '))
        m2.metric('🟡 À risque', f'{_n_rq:,}'.replace(',', ' '))
        m3.metric('Mensualité cumulée max', f"{_alertes['Mensualité est.'].max():,.0f} TND".replace(',', ' ') if not _alertes.empty else '0 TND', help="Somme des mensualités estimées de l'adhérent le plus exposé.")
        m4.metric('Toutes années', f'{len(_alertes_all):,}'.replace(',', ' '), help=f"Total des lignes (alertes + à risque) sur l'historique complet.")
        if not _alertes_all.empty:
            section('Répartition par année')
            _par_an = _alertes_all.groupby(['Année', 'Niveau']).agg(**{'Nb adhérents': ('Nom', 'nunique'), 'Achats concernés': ('Nb achats', 'sum'), 'Montant (TND)': ('Montant total', 'sum')}).reset_index().sort_values(['Année', 'Niveau'])
            _fig_par_an = chart_stacked_bar(_par_an, x='Année', cat='Niveau', y='Nb adhérents', title=f'Conformité 40% par année — {_flux_conf}', h=260)
            st.plotly_chart(_fig_par_an, use_container_width=True)
        section(f"Lignes de conformité — {(_an_conf if _an_conf else 'toutes années')} " + f'({_flux_conf})')
        if _alertes.empty:
            st.success(f"Aucun adhérent à {_seuil_rq} achats ou plus dans l'année {(_an_conf if _an_conf else 'considérée')} — situation conforme.")
        else:
            _nb_al = int((_alertes['Niveau'] == '🔴 Alerte').sum())
            _nb_rq = int((_alertes['Niveau'] == '🟡 À risque').sum())
            st.warning(f'**{_nb_al} alerte(s) 🔴** + **{_nb_rq} à risque 🟡** — risque de dépassement des 40% du salaire net à vérifier.')
            cols_t = [c for c in ['Niveau', 'Nom', 'Convention', 'N° Client', 'Nb N° Client', 'Nb achats', 'Montant total', 'Mensualité est.', 'Dernier achat'] if c in _alertes.columns]
            _st = _alertes[cols_t].style.format({'Montant total': '{:,.0f} TND', 'Mensualité est.': '{:,.0f} TND', 'Dernier achat': lambda d: d.strftime('%d/%m/%Y') if hasattr(d, 'strftime') else str(d)})
            st.dataframe(_st, use_container_width=True, hide_index=True)
            csv_conf = _alertes.to_csv(index=False).encode('utf-8')
            st.download_button('📥 Export CSV — alertes conformité 40%', data=csv_conf, file_name=f"alertes_conformite40_{_an_conf or 'tout'}.csv", mime='text/csv', key='dl_conf40')
        with st.expander('ℹ️ Méthodologie', expanded=False):
            st.markdown(f"- **Niveaux** : 🔴 **Alerte** ≥ {_seuil_alert} achats/an par nom · 🟡 **À risque** ≥ {_seuil_rq} (seuils centralisés dans `data/config.py`).\n- **Clé d'identification** : le **nom de l'adhérent normalisé** (casse, accents, espaces et ponctuation unifiés).\n- **Colonne « Nb N° Client »** : nombre de N° Client différents rattachés à ce nom sur l'année (>1 = réinscription ou homonyme à vérifier).\n- **Colonne « Convention »** : déterminée par le **type de vente** de chaque facture (`Type vente à crédit` ∈ `TYPES_CONVENTION`, ex. `VC.CONV.` → nom de la colonne `Nom`) — **« Hors convention »** sinon (cas du crédit particulier : `VC.PARTIC.`).\n- **Mensualité estimée** : `Montant TTC / Nbr_Mois_Echéance`, somme des factures de l'année — estimation brute, sans intérêts ni échéanciers en cours.\n- **Exclusions** : factures annulées, noms vides.\n- **Limite** : le salaire net individuel n'étant pas dans les données, ce tableau liste les cas **à vérifier manuellement** auprès de l'Amicale (fiche de paie) — il ne remplace pas le calcul exact des 40%.")