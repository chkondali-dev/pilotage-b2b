"""
Dashboard Pilotage B2B — SMG (MG & BATAM)
Architecture modulaire, BI décisionnel, visualisation executive
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import subprocess
import sys
import os
import json
from io import BytesIO
import base64
from datetime import datetime, timedelta
from pathlib import Path
from trend_alert_panel import render_alert_panel

from data.config import C, MOIS, LOGO_MG_URL, LOGO_BATAM_URL, SEUILS
from data.loader import load_all_data
from data.transforms import prepare_data
from metrics.kpi import (
    compare_years, compare_years_date_to_date, ca_sum_date_to_date,
    truncate_n1_date_to_date,
    evol_pct, convention_risk_matrix, inactive_conventions, get_rolling_3m,
    fmt_pct, color_delta,
    nb_factures, panier_moyen, bridge_volume_panier,
    run_rate_fin_annee, data_health,
    objectif_tracking, cohortes_conventions, narratif_executif,
    ventes_positives, concentration_portefeuille, volumes_panier, business_insights,
    conversion_conventions, kpi_conversion_globale,
)
from charts.factory import (
    chart_bar, chart_grouped_bar, chart_line_compare, chart_variation_bar,
    chart_bridge, chart_risk_table, chart_gauge, chart_pie,
)
from ui.components import inject_css, hero, section, badge, rank_card, kpi_card
from utils.github import push_csv_to_github
import business.conventions as conv

st.set_page_config(
    page_title="Pilotage B2B — SMG",
    layout="wide",
    page_icon="\U0001f4ca",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# SECTION 7 — BOOTSTRAP
# ══════════════════════════════════════════════════════════════

inject_css()

# ── Header ────────────────────────────────────────────────────
col_h, col_l1, col_l2 = st.columns([8, 1, 1])
with col_h:
    hero(
        "Dashboard Pilotage B2B",
        "Performance des conventions MG & BATAM — Outil de décision commerciale direction",
        ["Business Central VC.CONV", "MG + BATAM", "Mis à jour automatiquement"],
    )
with col_l1:
    try:
        st.image(LOGO_MG_URL, width=90)
    except Exception:
        pass
with col_l2:
    try:
        st.image(LOGO_BATAM_URL, width=90)
    except Exception:
        pass

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### \U0001f50d Filtres")
    annee_sel = st.selectbox("Année", [2026, 2025, 2024, 2023], index=0)

    # Filtre mois — vide = année complète (comparaison N/N-1 homogène)
    all_mois = list(range(1, 13))
    mois_sel = st.multiselect(
        "Mois (vide = année complète)",
        all_mois,
        default=[],
        format_func=lambda x: MOIS.get(x, str(x)),
    )

    # Filtre Type de vente
    type_vente_sel = st.selectbox(
        "Type de vente",
        ["Global", "Convention", "Credit conso", "Credit particulier"]
    )

    st.markdown("---")
    if st.button("\U0001f504 Actualiser"):
        st.cache_data.clear()
        st.rerun()

# ── Chargement données ────────────────────────────────────────
with st.spinner("Chargement des données…"):
    _raw = load_all_data()

df_vc, df_credit, df_edc, df_conv, code_df, df_credit_part, df_cube_mag, df_prospection, df_crm = prepare_data(_raw)
_raw_part = _raw.get("credit_particulier", pd.DataFrame())

# ── Registre LENS — 6 périmètres d'un seul onglet (filtre unique) ──────────
LENS_LABELS = [
    "EDC",
    "🛡️ Mutuelle Sûreté",
    "🛡️ Mutuelle Garde NLE & Protection Civile",
    "🌐 Convention globale",
    "🌐 Conso globale",
    "🌐 Particulier globale",
]


def _lens_meta(label):
    """Métadonnées du périmètre : df filtré, titre court, flux parent, recos."""
    _has_nom = not df_credit.empty and "Nom" in df_credit.columns

    def _mut(sub_pat):
        return (df_credit[df_credit["Nom"].str.contains(sub_pat, case=False, na=False)].copy()
                if _has_nom else df_credit.iloc[0:0])

    if label == "EDC":
        return {"key": "edc", "short": "EDC", "df": df_edc, "parent": None,
                "flux_label": "", "spec_recos": [],
                "title": "\U0001f3eb Convention EDC — Ministère de l'Éducation",
                "caption": "Convention Ministère de l'Éducation — flux EDC. Lecture en 5 sections : "
                           "situation → dynamique → réseau → échéance → synthèse."}
    if label.startswith("🛡️ Mutuelle Sûreté"):
        return {"key": "surete", "short": "Mut. Sûreté", "df": _mut("MUT PERS SURETE"),
                "parent": df_credit, "flux_label": "crédit conso",
                "spec_recos": ["Relancer commercialement le compte (rencontre direction, animation du "
                               "réseau, mise en avant de l'offre) et capitaliser sur la dynamique observée."],
                "title": "\U0001f6e1\ufe0f Mutuelle Personnel Sûreté Nationale — Prison & Rééducation",
                "caption": "Compte dédié extrait du flux Crédit Conso (VC.CONSO.) — client "
                           "« MUT PERS SURETE NLE PRISON &REEDUC ». Lecture en 5 sections : "
                           "situation → dynamique → réseau → échéance → synthèse."}
    if label.startswith("🛡️ Mutuelle Garde"):
        return {"key": "garde", "short": "Mut. Garde NLE & PC", "df": _mut("MUTUELLE GARDE NLE"),
                "parent": df_credit, "flux_label": "crédit conso",
                "spec_recos": ["Maintenir la dynamique du compte, sécuriser le renouvellement de la "
                               "convention et étendre l'offre aux magasins du réseau sans dossier."],
                "title": "\U0001f6e1\ufe0f Mutuelle Garde NLE & Protection Civile",
                "caption": "Compte dédié extrait du flux Crédit Conso — mutuelle Garde NLE & "
                           "Protection Civile. Lecture en 5 sections : situation → dynamique → "
                           "réseau → échéance → synthèse."}
    if label.startswith("🌐 Convention"):
        return {"key": "conv", "short": "Toutes conventions", "df": df_vc, "parent": None,
                "flux_label": "", "spec_recos": [],
                "title": "\U0001f310 Conventionnel — toutes les conventions",
                "caption": "Vue globale du flux Conventionnel (VC) : l'ensemble des conventions, "
                           "tous magasins confondus. Lecture en 5 sections : situation → dynamique → "
                           "réseau → échéance → synthèse."}
    if label.startswith("🌐 Conso"):
        return {"key": "conso", "short": "Tout le crédit conso", "df": df_credit, "parent": None,
                "flux_label": "", "spec_recos": [],
                "title": "\U0001f310 Tout le crédit conso",
                "caption": "Vue globale du flux Crédit Conso : tous les comptes confondus. "
                           "Lecture en 5 sections : situation → dynamique → réseau → échéance → synthèse."}
    return {"key": "part", "short": "Tout le crédit particulier", "df": df_credit_part,
            "parent": None, "flux_label": "", "spec_recos": [],
            "title": "\U0001f310 Tout le crédit particulier",
            "caption": "Vue globale du flux Crédit Particulier : tous les comptes confondus. "
                       "Lecture en 5 sections : situation → dynamique → réseau → échéance → synthèse."}


if df_vc.empty or "Année" not in df_vc.columns:
    st.error("\u26a0\ufe0f Aucune donnée VC chargée. Vérifiez la connexion GitHub.")
    st.stop()

# ── Pré-calculs partagés (calculés une seule fois) ────────────
# Apply type_vente filter first
if type_vente_sel == "Global":
    df_vc_filt = df_vc.copy()
    if not df_credit.empty:
        df_vc_filt = pd.concat([df_vc_filt, df_credit], ignore_index=True)
    if not df_credit_part.empty:
        df_vc_filt = pd.concat([df_vc_filt, df_credit_part], ignore_index=True)
elif type_vente_sel == "Convention":
    df_vc_filt = df_vc.copy()
elif type_vente_sel == "Credit conso":
    df_vc_filt = df_credit.copy() if not df_credit.empty else pd.DataFrame()
elif type_vente_sel == "Credit particulier":
    df_vc_filt = df_credit_part.copy() if not df_credit_part.empty else pd.DataFrame()
else:
    df_vc_filt = df_vc.copy()

# Portée multi-années (même filtre Type de vente, SANS filtre Année/Mois) :
# waterfall, heatmap de saisonnalité et prévision doivent rester pluriannuels.
df_vc_scope = df_vc_filt.copy()

if mois_sel:
    df_vc_filt = df_vc_filt[df_vc_filt["Mois"].isin(mois_sel)]

# Convention filter (dépend de l'année)
_conv_options = (
    ["Tous"] + sorted(df_vc_filt["Nom"].dropna().unique().tolist())
    if "Nom" in df_vc.columns else ["Tous"]
)


@st.cache_data(show_spinner=False)
def _cached_scan_all(df_vc_in, df_edc_in, df_conv_in, df_code_in):
    """Scan tendances TrendAnalyzer — recalculé uniquement si les entrées changent."""
    from trend_analyzer import TrendAnalyzer
    ta = TrendAnalyzer(df_vc=df_vc_in, df_edc=df_edc_in,
                       conventions=df_conv_in, code_magasin=df_code_in)
    return ta.scan_all()


@st.cache_data(show_spinner=False)
def _cached_data_health(df):
    """Santé des données — recalculée uniquement si les données changent."""
    return data_health(df)


with st.sidebar:
    conv_sel = st.selectbox("Convention", _conv_options)
    seuil_inactif = st.slider(
        "Seuil d'inactivite (jours)",
        min_value=15, max_value=180, value=SEUILS["inactivite_jours"], step=15,
        help="Conventions sans facture depuis plus de N jours",
    )
    objectif_m = st.number_input(
        "Objectif CA annuel (M TND)",
        min_value=0.0, value=float(SEUILS["objectif_defaut_m"]), step=0.5,
        help="Cible annuelle — % atteinte, jauge et narratif exécutif",
    )

    with st.expander("\U0001fa7a Santé des données", expanded=False):
        _health = _cached_data_health(df_vc)
        st.markdown(f"### {_health['Statut']} Santé des données")
        _h1, _h2 = st.columns(2)
        with _h1:
            st.metric("Lignes", f"{_health['Lignes']:,}".replace(",", " "))
            st.metric("Doublons exacts", _health["Doublons exacts"])
            st.metric("Montants ≤ 0", _health["Montants ≤ 0"])
        with _h2:
            st.metric("Dernière facture", _health["Dernière facture"] or "—")
            st.metric("Retard alimentation",
                      f"{_health['Retard (j)']} j" if _health["Retard (j)"] is not None else "—")
            st.metric("Jours sans facture (90j)", _health["Jours sans facture (90j)"])
        if _health["NaN Date"] > 0 or _health["NaN Montant"] > 0:
            st.caption(f"⚠️ NaN — Date : {_health['NaN Date']} | Montant : {_health['NaN Montant']}")

    st.markdown("---")
    with st.expander("\U0001f4c4 Rapport Mensuel IA", expanded=False):
        RAPPORT_DIR = Path.home() / "Downloads" / "rapport_mensuel"
        RAPPORT_DIR.mkdir(parents=True, exist_ok=True)

        # Selecteurs mois/annee pour le rapport
        default_month = datetime.now().month
        default_year = datetime.now().year
        mois_noms = ["Janvier","Fevrier","Mars","Avril","Mai","Juin",
                     "Juillet","Aout","Septembre","Octobre","Novembre","Decembre"]

        col_m, col_a = st.columns(2)
        with col_m:
            rapport_mois = st.selectbox("Mois", range(1, 13),
                index=default_month - 1,
                format_func=lambda m: mois_noms[m - 1])
        with col_a:
            rapport_annee = st.selectbox("Annee", [2023, 2024, 2025, 2026],
                index=[2023, 2024, 2025, 2026].index(default_year))

        # Lister les rapports existants
        txt_files = sorted(
            RAPPORT_DIR.glob("rapport_mensuel_*.txt"),
            key=os.path.getmtime, reverse=True
        )

        if txt_files:
            latest = txt_files[0]
            mtime = datetime.fromtimestamp(os.path.getmtime(latest))
            parts = latest.stem.split("_")
            periode = f"{parts[2]}/{parts[3]}" if len(parts) >= 4 else ""
            st.caption(f"Periode : {periode} | Genere le {mtime.strftime('%d/%m/%Y a %H:%M')}")

            html_file = RAPPORT_DIR / latest.name.replace(".txt", ".html")
            if html_file.exists():
                with open(html_file, "r", encoding="utf-8") as f:
                    st.download_button("Telecharger .html", data=f,
                                       file_name=html_file.name, mime="text/html",
                                       use_container_width=True)
        else:
            st.caption("Aucun rapport disponible.")

        if st.button("Generer maintenant", type="primary", use_container_width=True):
            with st.spinner("Generation en cours (~2 min)..."):
                env = os.environ.copy()
                # Forcer LLM_API_KEY depuis st.secrets (Streamlit Cloud) ou depuis la variable existante
                api_key = ""
                for src in [st.secrets, os.environ]:
                    try:
                        k = src.get("LLM_API_KEY", "")
                        if k:
                            api_key = k
                            break
                    except Exception:
                        continue
                if api_key:
                    env["LLM_API_KEY"] = api_key
                result = subprocess.run(
                    [sys.executable, str(Path(__file__).parent / "monthly_report.py"),
                     "--month", str(rapport_mois),
                     "--year", str(rapport_annee),
                     "--no-email",
                     "--api-key", api_key],
                    capture_output=True, text=True, timeout=300, env=env,
                )
            if result.returncode == 0:
                st.success("Rapport genere !")
                st.rerun()
            else:
                st.error(f"Erreur : {result.stderr[:200]}")

# ── Slice filtré ──────────────────────────────────────────────
df_filt = df_vc_filt[df_vc_filt["Année"] == annee_sel].copy()
if conv_sel != "Tous":
    df_filt = df_filt[df_filt["Nom"] == conv_sel]

# ── Cache lourd : ces calculs coûteux ne sont PAS rejoués si les entrées n'ont pas changé ──
@st.cache_data(show_spinner=False)
def _cached_precalcs(df, annee, seuil, mois_tuple, _df_conv_ref):
    """Tous les calculs lourds qui tournaient à chaque interaction."""
    comp = compare_years_date_to_date(df, annee, annee - 1, list(mois_tuple) if mois_tuple else None)
    rm   = convention_risk_matrix(df, annee)
    inac = inactive_conventions(df, seuil, annee_n=annee)
    r3m  = get_rolling_3m(df)
    ca_n, ca_n1, ev_nn1 = ca_sum_date_to_date(df, annee, annee - 1, list(mois_tuple) if mois_tuple else None)
    ca_n2 = df[df["Année"] == annee - 2]["Montant TTC"].sum()
    nb_a  = df[df["Année"] == annee]["Nom"].dropna().nunique() if "Nom" in df.columns else 0
    nb_i  = len(inac)
    nb_t  = len(_df_conv_ref) if not _df_conv_ref.empty else 0
    return comp, rm, inac, r3m, ca_n, ca_n1, ev_nn1, ca_n2, nb_a, nb_i, nb_t

df_comp, risk_mat, df_inactive, df_3m, ca_n, ca_n1, ev_nn1, ca_n2, nb_actives, nb_inact, nb_total = \
    _cached_precalcs(df_vc_filt, annee_sel, seuil_inactif, tuple(mois_sel) if mois_sel else (), df_conv)

ev_n1n2 = evol_pct(ca_n1, ca_n2)

# ── Compteurs risques ─────────────────────────────────────────
if not risk_mat.empty:
    nb_declin_fort = len(risk_mat[risk_mat["Statut"] == "\U0001f534 Déclin fort"])
    nb_inactif_cv  = len(risk_mat[risk_mat["Statut"] == "\U0001f534 Inactif"])
    nb_croissance  = len(risk_mat[risk_mat["Statut"].isin(["\U0001f7e9 Croissance", "\U0001f7e9 Nouveau"])])
else:
    nb_declin_fort = nb_inactif_cv = nb_croissance = 0

# ══════════════════════════════════════════════════════════════
# SECTION 8 — TABS
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# GIT SYNC — Persister les donnees sur GitHub
# ══════════════════════════════════════════════════════════════

# (fonction push_csv_to_github importee depuis utils.github)

tabs = st.tabs([
    "\U0001f3e0 Vue Exécutive",
    "\U0001f4c8 CA & Tendances",
    "\U0001f4cb Conventions",
    "\U0001f3ea Magasins",
    "\U0001f9ed Tous flux & Mutuelles",
    "\U0001f4cb Conventions encours",
    "\U0001f91d CRM",
    "\U0001f6a8 Alertes Tendances",
    "\U0001f4c2 Archive Rapports",
])

# ══════════════════════════════════════════════════════════════
# TAB 0 — VUE EXÉCUTIVE
# ══════════════════════════════════════════════════════════════
with tabs[0]:

    # ── KPI strip : 8 KPI utiles, valeur + évolution + contexte ──
    section("Indicateurs clés")
    _vol0 = volumes_panier(df_vc_filt, annee_sel, mois_sel)
    _conc0 = concentration_portefeuille(df_vc_filt, annee_sel, mois_sel)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        f"CA {annee_sel}",
        f"{ca_n:,.0f} TND",
        f"{fmt_pct(ev_nn1)} vs {annee_sel-1}",
        delta_color=color_delta(ev_nn1),
    )
    k2.metric(
        f"Factures {annee_sel}",
        f"{_vol0['Nb N']:,}".replace(",", " "),
        f"{fmt_pct(_vol0['Evo Nb %'])} vs N-1" if pd.notna(_vol0["Evo Nb %"]) else "—",
        delta_color=color_delta(_vol0["Evo Nb %"]),
    )
    k3.metric(
        "Panier moyen",
        f"{_vol0['Panier N']:,.0f} TND" if pd.notna(_vol0["Panier N"]) else "—",
        f"{fmt_pct(_vol0['Evo panier %'])} vs N-1" if pd.notna(_vol0["Evo panier %"]) else "—",
        delta_color=color_delta(_vol0["Evo panier %"]),
    )
    k4.metric(
        "Conventions actives",
        f"{nb_actives}",
        f"{_conc0['Top3 %']:.1f}% top 3" if pd.notna(_conc0["Top3 %"]) else f"/ {nb_total} total",
    )

    # ── CA à risque + inactivité : conventions inactives ─────────
    if nb_inact > 0 and not df_inactive.empty and "CA N-1" in df_inactive.columns:
        _ca_risque = float(df_inactive["CA N-1"].sum())
        if _ca_risque > 0:
            st.warning(
                f"\U0001f4b0 À risque : **{_ca_risque:,.0f} TND** de CA {annee_sel - 1} "
                f"(période sélectionnée) proviennent de **{nb_inact} convention(s)** sans "
                f"facture depuis plus de {seuil_inactif} jours — à relancer en priorité."
            )
    elif nb_inact == 0:
        st.success("✅ Aucune convention inactive — portefeuille vivant.")

    # ── À retenir : insights automatiques (max 5, triés par impact) ──
    _ins0 = business_insights(df_vc_filt, annee_sel, risk_mat, mois_sel)
    if _ins0:
        st.markdown("**💡 À retenir**")
        for _ico, _txt in _ins0:
            st.markdown(f"{_ico} {_txt}")

    # ── Synthèse exécutive : objectif + narratif (P2) ─────
    section("Synthèse exécutive")
    _rr0 = run_rate_fin_annee(df_vc_scope, annee_sel)
    _obj = objectif_tracking(
        _rr0["CA YTD"], float(objectif_m) * 1_000_000,
        _rr0["Jours écoulés"], _rr0["Jours année"],
    )
    _oc1, _oc2 = st.columns([1, 2])
    with _oc1:
        if pd.notna(_obj["Atteinte %"]):
            st.plotly_chart(
                chart_gauge(_obj["CA YTD"], _obj["Objectif"],
                            f"Atteinte objectif {annee_sel}"), use_container_width=True,
            )
        else:
            st.caption("Définissez un objectif > 0 dans la sidebar.")
    with _oc2:
        oc_a, oc_b, oc_c = st.columns(3)
        oc_a.metric("Objectif", f"{_obj['Objectif']:,.0f} TND")
        oc_b.metric("Atteinte", fmt_pct(_obj["Atteinte %"]) if pd.notna(_obj["Atteinte %"]) else "—")
        oc_c.metric("Avance/retard prorata",
                    f"{_obj['Avance/retard']:+,.0f} TND" if pd.notna(_obj["Avance/retard"]) else "—")
    _ctx_narr = {
        "annee": annee_sel, "ca_n": ca_n, "ca_n1": ca_n1, "evo_pct": ev_nn1,
        "objectif": _obj["Objectif"], "atteinte_pct": _obj["Atteinte %"],
        "avance_retard": _obj["Avance/retard"], "run_rate": _rr0["Projection"],
        "ca_risque": float(df_inactive["CA N-1"].sum())
        if (nb_inact > 0 and not df_inactive.empty and "CA N-1" in df_inactive.columns) else 0.0,
        "nb_inact": nb_inact,
    }
    _br_narr = bridge_volume_panier(df_vc_scope, annee_sel, mois_sel)
    _ctx_narr["bridge"] = _br_narr.set_index("Étape")["Effet (TND)"].to_dict()
    if not risk_mat.empty and "CA N" in risk_mat.columns:
        _rm_narr = risk_mat.copy()
        _rm_narr["Δ CA (TND)"] = _rm_narr["CA N"] - _rm_narr["CA N-1"]
        _g = _rm_narr[_rm_narr["Δ CA (TND)"] > 0].nlargest(1, "Δ CA (TND)")
        _f = _rm_narr[_rm_narr["CA N-1"] > 0].nsmallest(1, "Évolution %")
        if not _g.empty:
            _ctx_narr["top_hausse"] = {"nom": _g.iloc[0]["Nom"], "delta": float(_g.iloc[0]["Δ CA (TND)"])}
        if not _f.empty:
            _ctx_narr["flop"] = {"nom": _f.iloc[0]["Nom"], "evo": _f.iloc[0]["Évolution %"]}
    for _ico, _txt in narratif_executif(_ctx_narr):
        st.markdown(f"{_ico} {_txt}")

    mois_label = ", ".join([MOIS.get(m, str(m)) for m in mois_sel]) if mois_sel else f"{annee_sel}"

    # ── Évolution CA : mensuel N vs N-1 + cumul ──────────────
    section("Évolution du chiffre d'affaires")
    col_a, col_b = st.columns(2)

    with col_a:
        fig_gb = chart_grouped_bar(
            df_comp, "Mois Nom", "CA N", "CA N-1",
            f"CA Mensuel — {annee_sel} vs {annee_sel-1}", annee_sel,
        )
        st.plotly_chart(fig_gb, use_container_width=True)

    with col_b:
        # Cumul N vs N-1 : lecture d'écart qui se creuse / se résorbe
        _cum = df_comp[["Mois Nom", "CA N", "CA N-1"]].copy() if not df_comp.empty else pd.DataFrame()
        if not _cum.empty:
            _cum["Cumul N"] = _cum["CA N"].cumsum()
            _cum["Cumul N-1"] = _cum["CA N-1"].cumsum()
            fig_cum = chart_line_compare(
                _cum, "Mois Nom", "Cumul N", "Cumul N-1",
                f"CA Cumulé — {annee_sel} vs {annee_sel-1}", annee_sel,
            )
            st.plotly_chart(fig_cum, use_container_width=True)
        else:
            st.caption("Aucune donnée disponible.")

    # ── Portefeuille conventions : Top 10 + variations ────────
    section("Portefeuille conventions — Performance")
    col_c, col_d = st.columns(2)

    with col_c:
        _top10 = ventes_positives(df_filt).groupby("Nom")["Montant TTC"].sum().nlargest(10).reset_index()
        fig_t10 = chart_bar(
            _top10, "Montant TTC", "Nom",
            f"Top 10 conventions — {annee_sel}", C["blue"], h=400, orientation="h",
        )
        st.plotly_chart(fig_t10, use_container_width=True)

    with col_d:
        fig_var = chart_variation_bar(
            risk_mat.head(20), "Nom", "Évolution %",
            f"Évolution N/N-1 — Top 20 conventions", h=400,
        )
        st.plotly_chart(fig_var, use_container_width=True)

    # ── Signaux : tableau risque + Top/Flop (mêmes sources) ─────
    section("Signaux décisionnels — Risques & Opportunités")
    col_e, col_f, col_g = st.columns([3, 1, 1])

    with col_e:
        fig_sc = chart_risk_table(
            risk_mat.head(20), annee_sel,
            "État du portefeuille — Vue condensée", h=450,
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    if "Nom" in df_filt.columns and len(df_filt) > 0:
        ca_cli = ventes_positives(df_filt).groupby("Nom")["Montant TTC"].sum()
        top3   = ca_cli.nlargest(3)

        with col_f:
            st.markdown("**\U0001f3c6 Top 3**")
            for i, (nom, ca) in enumerate(top3.items(), 1):
                rank_card(i, nom, f"{ca:,.0f} TND", "top")

        with col_g:
            # Flop 3 = plus fortes BAISSES N vs N-1 (base N-1 exigée), pas les plus petits CA
            st.markdown("**\u26a0\ufe0f Flop 3 — Fortes baisses**")
            if not risk_mat.empty:
                _flop = risk_mat[risk_mat["CA N-1"] > 0].nsmallest(3, "Évolution %")
                if not _flop.empty:
                    for i, (_, _r) in enumerate(_flop.iterrows(), 1):
                        rank_card(i, _r["Nom"], f"{fmt_pct(_r['Évolution %'])} vs N-1", "flop")
                else:
                    st.caption("Aucune baisse mesurable — pas de base N-1.")
            else:
                st.caption("Données de risque indisponibles.")

    # ── Dynamique du portefeuille : actives + nouvelles (tout historique) ──
    section("Dynamique du portefeuille — Entrées / Sorties")
    # Build full dataset for the selected years
    _pieces = [df_vc]
    if not df_credit.empty:
        _pieces.append(df_credit)
    if not df_credit_part.empty:
        _pieces.append(df_credit_part)
    _all = pd.concat(_pieces, ignore_index=True)
    _all = _all[_all["Année"].between(annee_sel - 1, annee_sel)].copy()

    if not _all.empty and "Nom" in _all.columns:
        _all["Periode"] = _all["Année"].astype(str) + "-" + _all["Mois"].astype(str).str.zfill(2)
        # Active conventions per month
        _act = _all.groupby("Periode")["Nom"].nunique().reset_index(name="Actives")
        # First invoice date per convention → SUR TOUT L'HISTORIQUE (pas la fenêtre 2 ans) :
        # une convention antérieure à la fenêtre n'est pas « nouvelle ».
        _first = pd.concat(_pieces, ignore_index=True).groupby("Nom")["Date"].min().reset_index()
        _first["Periode"] = _first["Date"].dt.year.astype(str) + "-" + _first["Date"].dt.month.astype(str).str.zfill(2)
        _new = _first["Periode"].value_counts().reset_index()
        _new.columns = ["Periode", "Nouvelles"]
        _pf = _act.merge(_new, on="Periode", how="left").fillna(0)
        _pf["Nouvelles"] = _pf["Nouvelles"].astype(int)
        _pf = _pf.sort_values("Periode")

        _pf_a = _pf[_pf["Periode"] >= f"{annee_sel-1}-01"]
        fig_pf = go.Figure()
        fig_pf.add_trace(go.Scatter(x=_pf_a["Periode"], y=_pf_a["Actives"],
                                    name="Actives", line=dict(color=C["blue"], width=3)))
        fig_pf.add_trace(go.Bar(x=_pf_a["Periode"], y=_pf_a["Nouvelles"],
                                name="Nouvelles", marker_color=C["green"], opacity=0.5,
                                yaxis="y2"))
        fig_pf.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                            yaxis=dict(title="Actives", side="left"),
                            yaxis2=dict(title="Nouvelles", side="right", overlaying="y"),
                            legend=dict(orientation="h", y=1.05))
        _col_pf1, _col_pf2 = st.columns([3, 1])
        with _col_pf1:
            st.plotly_chart(fig_pf, use_container_width=True)
        with _col_pf2:
            _pf_annee = _pf[_pf["Periode"].str.startswith(str(annee_sel))]
            _pf_n1 = _pf[_pf["Periode"].str.startswith(str(annee_sel - 1))]
            avg_a = _pf_annee["Actives"].mean()
            avg_n1 = _pf_n1["Actives"].mean()
            evo_pf = evol_pct(avg_a, avg_n1)
            st.metric("Moy. actives/mois", f"{avg_a:.0f}",
                      f"{fmt_pct(evo_pf)} vs N-1" if pd.notna(evo_pf) else "—",
                      delta_color=color_delta(evo_pf))
            st.metric("Nouvelles YTD", f"{_pf_annee['Nouvelles'].sum():.0f}")

    # ── Concentration : Top 3 + Pareto (ventes positives) ──────
    section("Concentration du portefeuille")
    if pd.notna(_conc0["Top3 %"]):
        _k1, _k2, _k3 = st.columns(3)
        _k1.metric("Part Top 3", f"{_conc0['Top3 %']:.1f}%")
        _k2.metric("HHI", f"{_conc0['HHI']}", f"{_conc0['Niveau']}")
        _k3.metric("Conventions", f"{_conc0['Nb']}")
        _conc_top = _conc0["courbe"]
        fig_conc = go.Figure()
        fig_conc.add_trace(go.Bar(x=_conc_top["Nom"], y=_conc_top["CA"],
                                  name="CA", marker_color=C["blue"]))
        fig_conc.add_trace(go.Scatter(x=_conc_top["Nom"], y=_conc_top["Cumul %"],
                                      name="% cumulé", yaxis="y2",
                                      line=dict(color=C["red"], width=2),
                                      marker=dict(color=C["red"])))
        fig_conc.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10),
                               yaxis=dict(title="CA"),
                               yaxis2=dict(title="% cumulé", overlaying="y",
                                           side="right", range=[0, 105]))
        st.plotly_chart(fig_conc, use_container_width=True)
    else:
        st.caption("Aucune donnée disponible.")


# ══════════════════════════════════════════════════════════════
# TAB 1 — CA & TENDANCES
# ══════════════════════════════════════════════════════════════
with tabs[1]:

    # ══════════════════════════════════════════════════════
    # SECTION VEILLE — CHIFFRE DE LA VEILLE (jour unique)
    # ══════════════════════════════════════════════════════
    st.markdown("### \U0001f4ca Performance veille — chiffre de la veille")

    # Date sélectionnable (par défaut hier) — jour unique comparé au même jour N-1.
    default_date = (datetime.now() - timedelta(days=1)).date()
    hier_date = st.date_input("Choisir une date", value=default_date, key="veille_date")
    annee_hier = hier_date.year
    mois_hier = hier_date.month

    _fin_win = hier_date
    _deb_win = hier_date
    _deb_win_n1 = (pd.Timestamp(_deb_win) - pd.DateOffset(years=1)).date()
    _fin_win_n1 = (pd.Timestamp(_fin_win) - pd.DateOffset(years=1)).date()

    df_vc_hier = df_vc[(df_vc["Date"].dt.date >= _deb_win) & (df_vc["Date"].dt.date <= _fin_win)].copy()
    df_vc_n1 = df_vc[(df_vc["Date"].dt.date >= _deb_win_n1) & (df_vc["Date"].dt.date <= _fin_win_n1)].copy()

    # KPI veille (jour unique vs même jour N-1)
    ca_veille = df_vc_hier["Montant TTC"].sum() if len(df_vc_hier) > 0 else 0
    ca_n1_meme_jour = df_vc_n1["Montant TTC"].sum() if len(df_vc_n1) > 0 else 0
    evo_veille = ((ca_veille - ca_n1_meme_jour) / ca_n1_meme_jour * 100) if ca_n1_meme_jour > 0 else float("nan")
    nb_tickets_veille = len(df_vc_hier)
    panier_veille = ca_veille / nb_tickets_veille if nb_tickets_veille > 0 else 0

    # KPI Cards horizontales
    kp1, kp2, kp3, kp4 = st.columns(4)
    kp1.metric("CA veille", f"{ca_veille:,.0f} TND")
    kp2.metric("Évolution vs N-1", fmt_pct(evo_veille))
    kp3.metric("Nb factures", nb_tickets_veille)
    kp4.metric("Panier moyen", f"{panier_veille:,.0f} TND")

    st.caption(
        f"\U0001f4c5 Fenêtre : {_deb_win.strftime('%d/%m/%Y')} → {_fin_win.strftime('%d/%m/%Y')} — "
        f"comparée à {_deb_win_n1.strftime('%d/%m/%Y')} → {_fin_win_n1.strftime('%d/%m/%Y')} (N-1)"
    )

    # Analyse par segment
    col_seg1, col_seg2 = st.columns(2)

    with col_seg1:
        st.markdown("**Top 5 Conventions — veille**")
        if not df_vc_hier.empty and "Montant TTC" in df_vc_hier.columns and "Nom" in df_vc_hier.columns:
            top5_conv = df_vc_hier.groupby("Nom")["Montant TTC"].sum().nlargest(5)
            df_top5 = top5_conv.reset_index()
            df_top5.columns = ["Convention", "CA"]
            fig_top5 = px.bar(
                df_top5, x="CA", y="Convention", orientation="h",
                title="Top 5 Conventions",
                color="CA", color_continuous_scale=["#DCFCE7", "#15803D"],
            )
            fig_top5.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_top5, use_container_width=True)

    with col_seg2:
        st.markdown("**Top 5 Magasins — veille**")
        if not df_vc_hier.empty and "Montant TTC" in df_vc_hier.columns:
            for code_col_src in ["Code Navision", "Unite Code"]:
                if code_col_src in df_vc_hier.columns and "Magasin" in df_vc_hier.columns:
                    top5_mag = df_vc_hier.groupby("Magasin")["Montant TTC"].sum().nlargest(5)
                    if len(top5_mag) > 0:
                        df_top5m = top5_mag.reset_index()
                        df_top5m.columns = ["Magasin", "CA"]
                        fig_top5m = px.bar(
                            df_top5m, x="CA", y="Magasin", orientation="h",
                            title="Top 5 Magasins",
                            color="CA", color_continuous_scale=["#DCFCE7", "#15803D"],
                        )
                        fig_top5m.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
                        st.plotly_chart(fig_top5m, use_container_width=True)
                        break
            else:
                st.caption("Colonne Magasin non disponible")

    # Analyse par enseigne MG/BATAM
    st.markdown("### 3. Analyse par Enseigne (MG / BATAM)")

    col_ens1, col_ens2 = st.columns([1, 2])

    with col_ens1:
        st.markdown("**CA par Enseigne**")
        has_enseigne = not df_vc_hier.empty and "Enseigne" in df_vc_hier.columns

        if has_enseigne:
            ca_ens = df_vc_hier.groupby("Enseigne")["Montant TTC"].sum()
            total_ca = ca_ens.sum()

            mg_ca = ca_ens.get("MG", 0)
            bam_ca = ca_ens.get("BATAM", 0)
            mg_pct = (mg_ca / total_ca * 100) if total_ca > 0 else 0
            bam_pct = (bam_ca / total_ca * 100) if total_ca > 0 else 0

            st.metric("CA MG", f"{mg_ca:,.0f} TND", f"{mg_pct:.1f}% du total")
            st.metric("CA BATAM", f"{bam_ca:,.0f} TND", f"{bam_pct:.1f}% du total")
            st.caption(f"**Total:** {total_ca:,.0f} TND")
        else:
            st.info("Pas de donnees d'enseigne disponibles")

    with col_ens2:
        if has_enseigne:
            fig_pie = px.pie(
                values=ca_ens.values if len(ca_ens) > 0 else [1, 1],
                names=ca_ens.index if len(ca_ens) > 0 else ["MG", "BATAM"],
                title="Repartition du CA: MG vs BATAM",
                color_discrete_sequence=["#1D4ED8", "#059669"],
                hole=0.4,
            )
            fig_pie.update_traces(
                textinfo="percent+label",
                hoverinfo="label+percent+value",
            )
            fig_pie.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # Alertes automatiques
    st.markdown("### \U0001f514 Alertes & Insights — Veille (vs N-1)")

    alertes = []
    couleur_alertes = []

    if evo_veille < SEUILS["alerte_veille_pct"]:
        alertes.append(f"\u26a0\ufe0f Baisse significative: {evo_veille:.1f}% vs N-1 (veille)")
        couleur_alertes.append("inverse")
    elif evo_veille >= 0:
        alertes.append(f"\u2705 Belle performance: +{evo_veille:.1f}% vs N-1 (veille)")
        couleur_alertes.append("normal")

    if panier_veille < _vol0["Panier N"] * SEUILS["panier_bas_ratio"] and pd.notna(_vol0["Panier N"]):
        alertes.append(f"\U0001f4c9 Panier bas: {panier_veille:,.0f} TND (moy: {_vol0['Panier N']:,.0f})")
        couleur_alertes.append("inverse")

    if not df_vc_hier.empty:
        worst = df_vc_hier[df_vc_hier["Montant TTC"] > 0].nsmallest(1, "Montant TTC")
        if len(worst) > 0:
            w_mag = worst.iloc[0]["Magasin"] if "Magasin" in worst.columns else worst.iloc[0].get("Nom", "")
            w_ca = worst.iloc[0]["Montant TTC"]
            if w_ca < 100:
                alertes.append(f"\U0001f6a8 Magasin critique: {w_mag} (CA: {w_ca:,.0f})")
                couleur_alertes.append("inverse")

    if "Enseigne" in df_vc_hier.columns:
        ca_ens = df_vc_hier.groupby("Enseigne")["Montant TTC"].sum()
        total_ca = ca_ens.sum()
        mg_pct = (ca_ens.get("MG", 0) / total_ca * 100) if total_ca > 0 else 0
        bam_pct = (ca_ens.get("BATAM", 0) / total_ca * 100) if total_ca > 0 else 0

        if total_ca > 0:
            if mg_pct > 80:
                alertes.append(f"\u2696\ufe0f Desequilibre: MG {mg_pct:.0f}% / BATAM {bam_pct:.0f}%")
                couleur_alertes.append("inverse")
            elif bam_pct > 80:
                alertes.append(f"\u2696\ufe0f Desequilibre: BATAM {bam_pct:.0f}% / MG {mg_pct:.0f}%")
                couleur_alertes.append("inverse")

    if not alertes:
        alertes.append("\u2705 Aucune alerte — veille normale")
        couleur_alertes.append("normal")

    for txt, col in zip(alertes, couleur_alertes):
        st.write(f"{txt}")

    st.markdown("---")

    section("Tendance mensuelle")
    col_t1, col_t2 = st.columns(2)

    with col_t1:
        fig_line = chart_line_compare(
            df_comp, "Mois Nom", "CA N", "CA N-1",
            f"Tendance mensuelle {annee_sel} vs {annee_sel-1}", annee_sel,
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with col_t2:
        fig_mvar = chart_variation_bar(
            df_comp, "Mois Nom", "Variation %",
            f"Variation mensuelle % — {annee_sel} vs {annee_sel-1}",
        )
        st.plotly_chart(fig_mvar, use_container_width=True)

# ── CA Journalier ──────────────────────────────────────────
    section("CA Journalier")

    _dj_n  = df_vc_filt[df_vc_filt["Année"] == annee_sel]
    _dj_n1 = df_vc_filt[df_vc_filt["Année"] == annee_sel - 1]

    ca_jn  = _dj_n.groupby("Jour")["Montant TTC"].sum().rename("CA N").reset_index()
    ca_jn1 = _dj_n1.groupby("Jour")["Montant TTC"].sum().rename("CA N-1").reset_index()
    df_jour = ca_jn.merge(ca_jn1, on="Jour", how="outer").fillna(0).sort_values("Jour")

    fig_jour = chart_line_compare(
        df_jour, "Jour", "CA N", "CA N-1",
        f"CA Journalier — {annee_sel} vs {annee_sel-1}", annee_sel, h=380,
    )
    fig_jour.update_xaxes(dtick=1, tickangle=45)
    st.plotly_chart(fig_jour, use_container_width=True)

    # ── Rolling 3 mois + Jauge ─────────────────────────────────
    section("3 derniers mois glissants")
    col_r1, col_r2 = st.columns([2, 1])

    with col_r1:
        fig_3m = chart_bar(
            df_3m, "Periode", "Montant TTC",
            "CA Rolling 3 mois", C["blue"],
        )
        st.plotly_chart(fig_3m, use_container_width=True)

    with col_r2:
        fig_gauge = chart_gauge(ca_n, ca_n1, f"Atteinte {annee_sel} vs {annee_sel-1}")
        st.plotly_chart(fig_gauge, use_container_width=True)

    # Données brutes en expander
    with st.expander("\U0001f4c4 Données brutes — CA Journalier"):
        df_jour["Variation %"] = np.where(
            df_jour["CA N-1"] > 0,
            (df_jour["CA N"] - df_jour["CA N-1"]) / df_jour["CA N-1"] * 100,
            np.nan,  # sans base N-1 → « — »
        ).round(1)
        st.dataframe(df_jour, use_container_width=True)

    # ── Heatmap CA mensuel × année ─────────────────────────────
    section("Saisonnalité — Heatmap CA mensuel × année")
    _hm = df_vc_scope.groupby(["Année", "Mois"])["Montant TTC"].sum().reset_index()  # filtre Type, toutes années/mois
    _hm_pivot = _hm.pivot(index="Année", columns="Mois", values="Montant TTC").fillna(0)
    _hm_pivot = _hm_pivot.rename(columns=MOIS)
    fig_hm = px.imshow(_hm_pivot, text_auto=".0f", aspect="auto",
                       title="CA mensuel par année",
                       color_continuous_scale="Blues",
                       labels=dict(color="CA"))
    fig_hm.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_hm, use_container_width=True)

    # ── Prévision rolling 3m — M+1 ─────────────────────────────
    section("Prévision — Rolling 3 mois")
    _prev_df = df_vc_scope[df_vc_scope["Année"] >= max(annee_sel - 1, df_vc_scope["Année"].min())].copy()
    _prev_m = _prev_df.groupby(["Année", "Mois"])["Montant TTC"].sum().reset_index()
    _prev_m["Periode"] = _prev_m["Année"].astype(str) + "-" + _prev_m["Mois"].astype(str).str.zfill(2)
    _prev_m = _prev_m.sort_values(["Année", "Mois"]).tail(6)  # last 6 months
    if len(_prev_m) >= 3:
        _ma = _prev_m["Montant TTC"].rolling(3, min_periods=1).mean()
        _prev_m["Prev M+1"] = _ma.shift(1)
        _prev_m["Prev M+1"] = _prev_m["Prev M+1"].fillna(_prev_m["Montant TTC"].mean())
        _next_p = _prev_m.iloc[-1]["Montant TTC"]
        _next_ma = _ma.iloc[-1]
        _next_val = (_next_p * 0.4 + _next_ma * 0.6)  # weighted blend
        _col_p1, _col_p2 = st.columns([2, 1])
        with _col_p1:
            fig_p = go.Figure()
            fig_p.add_trace(go.Bar(x=_prev_m["Periode"], y=_prev_m["Montant TTC"],
                                   name="CA réalisé", marker_color=C["blue"]))
            fig_p.add_trace(go.Scatter(x=[_prev_m["Periode"].iloc[-1], f"{annee_sel}-{_prev_m['Mois'].iloc[-1] + 1:02d}"],
                                       y=[_next_p, _next_val],
                                       mode="lines+markers", name="Prévision",
                                       line=dict(color=C["red"], dash="dash", width=2),
                                       marker=dict(color=C["red"], size=8)))
            fig_p.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_p, use_container_width=True)
        with _col_p2:
            st.metric("Prévision M+1", f"{_next_val:,.0f}",
                      delta=f"{((_next_val - _next_p)/_next_p*100):+.1f}%" if _next_p > 0 else None)
            st.caption(f"Basée sur moyenne mobile 3m (pondérée 60/40)")

            # ── Run-rate fin d'année (P1) ──────────────────────
            _rr = run_rate_fin_annee(df_vc_scope, annee_sel)
            _ca_n1_full = float(df_vc_scope[df_vc_scope["Année"] == annee_sel - 1]["Montant TTC"].sum()) \
                if "Montant TTC" in df_vc_scope.columns else 0.0
            _rr_evo = evol_pct(_rr["Projection"], _ca_n1_full)
            st.metric(
                f"Run-rate fin {annee_sel}",
                f"{_rr['Projection']:,.0f} TND" if pd.notna(_rr["Projection"]) else "—",
                f"{fmt_pct(_rr_evo)} vs {annee_sel-1} (annuel)" if pd.notna(_rr["Projection"]) else None,
                delta_color=color_delta(_rr_evo),
            )
            st.caption(f"CA YTD {_rr['CA YTD']:,.0f} / {_rr['Jours écoulés']} j écoulés × {_rr['Jours année']} j")

    # ── Pont volume × panier (P1) : décomposition de ΔCA N vs N-1 ──
    section("Pont de variation — Volume × Panier")
    _bridge = bridge_volume_panier(df_vc_scope, annee_sel, mois_sel)
    _beff = _bridge.set_index("Étape")["Effet (TND)"]
    if pd.notna(_beff.get("+ Volume")):
        st.plotly_chart(
            chart_bridge(_bridge, "Étape", "Valeur",
                         f"Décomposition ΔCA {annee_sel} vs {annee_sel-1}"
                         f"{(' — ' + mois_label) if mois_sel else ''}"),
            use_container_width=True,
        )
        bc1, bc2, bc3 = st.columns(3)
        bc1.metric("Effet volume", f"{_beff.get('+ Volume'):+,.0f} TND",
                   f"{_bridge.set_index('Étape').loc['+ Volume', 'Nb factures']:+,.0f} factures")
        _dpan = _bridge.set_index("Étape").loc["+ Panier", "Panier moyen"]
        bc2.metric("Effet panier", f"{_beff.get('+ Panier'):+,.0f} TND",
                   f"{_dpan:+,.0f} TND/facture")
        bc3.metric("Effet mix", f"{_beff.get('+ Mix'):+,.0f} TND",
                   f"Δ total {_beff.get('= CA N'):+,.0f} TND")
    else:
        st.caption("Pas de base N-1 sur la période — pont non calculable.")


# ══════════════════════════════════════════════════════════════
# TAB 2 — CONVENTIONS
# ══════════════════════════════════════════════════════════════
with tabs[2]:

    # ── Données agrégées portefeuille (date-à-date) ──────
    _src_filt = df_vc_filt.copy()
    if conv_sel != "Tous":
        _src_filt = _src_filt[_src_filt["Nom"] == conv_sel]
    ca_total_n, ca_total_n1, ev_total = ca_sum_date_to_date(_src_filt, annee_sel, annee_sel - 1, mois_sel)
    _rm = risk_mat.copy() if not risk_mat.empty else pd.DataFrame()
    if conv_sel != "Tous" and not _rm.empty:
        _rm = _rm[_rm["Nom"] == conv_sel]
    nb_convs = len(_rm[_rm["CA N"] > 0]) if not _rm.empty else 0

    # ── Debug ────────────────────────────────────────────
    with st.expander("\U0001f50d Debug TAB 2", expanded=False):
        st.write("**conv_sel (sidebar) :**", conv_sel)
        st.write("**type_vente_sel :**", type_vente_sel)
        st.write("**mois_sel :**", mois_sel)
        st.write("**df_vc_filt shape :**", df_vc_filt.shape)
        if "Nom" in df_vc_filt.columns:
            st.write("**Conventions dispo :**", sorted(df_vc_filt["Nom"].dropna().unique()))
        st.write("**risk_mat shape :**", risk_mat.shape if not risk_mat.empty else "EMPTY")
        st.write("**_rm shape :**", _rm.shape if not _rm.empty else "EMPTY")
        if not _rm.empty:
            st.write("**_rm Noms :**", _rm["Nom"].tolist())
            st.write("**_rm CA N :**", _rm["CA N"].tolist())
        st.write("**ca_total_n :**", ca_total_n)
        st.write("**nb_convs :**", nb_convs)

    if not _rm.empty:
        risky = _rm[_rm["Statut"].str.contains("Déclin|Inactif", na=False)]
        nb_risky = len(risky)
    else:
        nb_risky = 0

    # ── 1. KPIs portefeuille ─────────────────────────────
    section("Portefeuille conventions — Vue synthétique")
    pk1, pk2, pk3, pk4 = st.columns(4)
    pk1.metric("\U0001f4cb Conventions actives", nb_convs)
    pk2.metric("\U0001f4b0 CA Total N", f"{ca_total_n:,.0f} TND", fmt_pct(ev_total),
               delta_color=color_delta(ev_total))
    pk3.metric("\u26a0\ufe0f À risque", nb_risky, delta_color="inverse" if nb_risky > 0 else "off")
    pk4.metric("\U0001f504 Inactives", nb_inact, delta_color="inverse" if nb_inact > 0 else "off")

    # ── 2. Top conventions ──────────────────────────────
    if not _rm.empty:
        top10 = _rm.nlargest(10, "CA N")[["Nom", "CA N", "Évolution %", "Statut"]].copy()
        top10 = top10.sort_values("CA N", ascending=True)
        fig_top = px.bar(
            top10, x="CA N", y="Nom", orientation="h",
            title="Top 10 conventions par CA",
            color="Statut", text_auto=".0f",
            color_discrete_map={
                "\u2705 Croissance": C["green"], "\U0001f4c9 Déclin": C["amber"],
                "\u26a0\ufe0f Déclin fort": C["red"], "\U0001f195 Nouveau": C["blue"],
                "\u274c Inactif": "#9CA3AF", "\u2753 Aucun historique": "#D1D5DB",
            },
            height=400,
        )
        fig_top.update_layout(xaxis_title="CA N (TND)", yaxis_title="",
                              legend=dict(orientation="h", y=-0.15, x=0, font=dict(size=11)))
        fig_top.update_traces(marker=dict(line=dict(width=0.5, color="white")))
        st.plotly_chart(fig_top, use_container_width=True)

    # ── 2c. Cohortes par ancienneté (P2) ──────────────────
    _coh = cohortes_conventions(df_vc_filt, annee_sel, mois_sel=mois_sel)
    if not _coh.empty:
        section("Segments — Ancienneté des conventions")
        _cc1, _cc2 = st.columns([2, 1])
        with _cc1:
            fig_coh = px.bar(
                _coh, x="Cohorte", y="CA N", color="Cohorte",
                title=f"CA {annee_sel} par cohorte",
                text_auto=".0f", height=320,
                color_discrete_map={
                    "✅ Fidèles": C["green"], "🆕 Nouvelles": C["blue"],
                    "🔄 Revenantes": C["amber"], "❌ Perdues": C["slate"],
                },
            )
            fig_coh.update_layout(xaxis_title="", yaxis_title="CA N (TND)", showlegend=False)
            st.plotly_chart(fig_coh, use_container_width=True)
        with _cc2:
            st.dataframe(
                _coh.style.format(
                    {"CA N": "{:,.0f}", "CA N-1": "{:,.0f}",
                     "Variation %": "{:+.1f}%", "Poids % N": "{:.1f}%"},
                    na_rep="—",
                ),
                use_container_width=True, hide_index=True,
            )
        # ── Drill-down : clic sur un segment → popup avec la liste des conventions
        _detail = _coh.attrs.get("detail", pd.DataFrame())
        if _detail is not None and not _detail.empty:
            _seg_labels = _coh["Cohorte"].tolist()
            _seg_choice = st.selectbox(
                "Voir le détail d'un segment",
                ["— Choisir —"] + _seg_labels,
                key="seg_detail_choice",
            )
            if _seg_choice != "— Choisir —":
                _rows = _detail[_detail["Cohorte"] == _seg_choice].copy()
                _rows = _rows.sort_values("CA N", ascending=False)
                _rows["Évolution %"] = np.where(
                    _rows["CA N-1"] > 0,
                    (_rows["CA N"] - _rows["CA N-1"]) / _rows["CA N-1"] * 100,
                    np.nan,
                ).round(1)

                @st.dialog(f"{_seg_choice} — {_rows.shape[0]} convention(s)")
                def _show_seg():
                    st.dataframe(
                        _rows[["Nom", "CA N", "CA N-1", "Évolution %"]].style.format(
                            {"CA N": "{:,.0f}", "CA N-1": "{:,.0f}",
                             "Évolution %": "{:+.1f}%"},
                            na_rep="—",
                        ),
                        use_container_width=True, hide_index=True,
                    )
                    _csv = _rows[["Nom", "CA N", "CA N-1", "Évolution %"]].to_csv(
                        index=False).encode("utf-8")
                    st.download_button(
                        "Télécharger (CSV)", data=_csv,
                        file_name=f"segment_{_seg_choice}.csv",
                        mime="text/csv",
                    )

                _show_seg()

    # ── 2b. Top hausses / pertes en TND (P1) ──────────────
    if not _rm.empty and "CA N" in _rm.columns and "CA N-1" in _rm.columns:
        section("Top hausses / pertes — Variation en TND")
        _rm_tnd = _rm.copy()
        _rm_tnd["Δ CA (TND)"] = _rm_tnd["CA N"] - _rm_tnd["CA N-1"]
        _gains = _rm_tnd[_rm_tnd["Δ CA (TND)"] > 0].nlargest(5, "Δ CA (TND)")
        _pertes = _rm_tnd[_rm_tnd["Δ CA (TND)"] < 0].nsmallest(5, "Δ CA (TND)")
        _tot_g = float(_rm_tnd.loc[_rm_tnd["Δ CA (TND)"] > 0, "Δ CA (TND)"].sum())
        _tot_p = float(_rm_tnd.loc[_rm_tnd["Δ CA (TND)"] < 0, "Δ CA (TND)"].sum())
        _tg1, _tg2 = st.columns(2)
        with _tg1:
            st.markdown(f"**\U0001f4c8 Top 5 hausses** — total +{_tot_g:,.0f} TND")
            if not _gains.empty:
                st.dataframe(
                    _gains[["Nom", "CA N", "CA N-1", "Δ CA (TND)", "Évolution %"]].style.format(
                        {"CA N": "{:,.0f}", "CA N-1": "{:,.0f}",
                         "Δ CA (TND)": "{:+,.0f}", "Évolution %": "{:+.1f}%"},
                        na_rep="—",
                    ),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.caption("Aucune hausse vs N-1.")
        with _tg2:
            st.markdown(f"**\U0001f4c9 Top 5 pertes** — total {_tot_p:,.0f} TND")
            if not _pertes.empty:
                st.dataframe(
                    _pertes[["Nom", "CA N", "CA N-1", "Δ CA (TND)", "Évolution %"]].style.format(
                        {"CA N": "{:,.0f}", "CA N-1": "{:,.0f}",
                         "Δ CA (TND)": "{:+,.0f}", "Évolution %": "{:+.1f}%"},
                        na_rep="—",
                    ),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.caption("Aucune perte vs N-1.")

    # ── 2d. Taux de conversion client (Effectif vs Acheteurs) ──
    section("Taux de conversion client — Effectif vs Acheteurs")
    _conv_rate = conversion_conventions(df_vc_filt, annee_sel, mois_sel if mois_sel else None)
    _kpi_conv = kpi_conversion_globale(_conv_rate)
    if not _conv_rate.empty:
        tg = _kpi_conv.get("Taux global %")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Taux de conversion global",
                  f"{tg:.2f} %" if pd.notna(tg) else "—",
                  help="Acheteurs distincts / Effectif total (conventions avec effectif > 0)")
        c2.metric("Acheteurs distincts", f"{_kpi_conv['Nb acheteurs']:,}".replace(",", " "))
        c3.metric("Effectif total suivi", f"{_kpi_conv['Effectif total']:,}".replace(",", " "))
        c4.metric("Conventions suivies", _kpi_conv["Nb conventions suivies"],
                  f"{_kpi_conv['Nb sans effectif']} sans effectif" if _kpi_conv["Nb sans effectif"] else None)
        _top_conv = _conv_rate[_conv_rate["Effectif"] > 0].head(15).sort_values("Taux %", ascending=True)
        if not _top_conv.empty:
            fig_conv = px.bar(_top_conv, x="Taux %", y="Nom", orientation="h",
                              title="Top 15 — Taux de conversion par convention",
                              text="Taux %", height=450,
                              hover_data=["Nb acheteurs", "Effectif", "Nb factures"])
            fig_conv.update_layout(xaxis_title="Taux % (acheteurs / effectif)",
                                   yaxis_title="")
            st.plotly_chart(fig_conv, use_container_width=True)
        _conv_show = _conv_rate.copy()
        if conv_sel != "Tous":
            _conv_show = _conv_show[_conv_show["Nom"] == conv_sel]
        st.dataframe(
            _conv_show.style.format(
                {"Effectif": "{:,.0f}", "Nb acheteurs": "{:,.0f}",
                 "Nb factures": "{:,.0f}", "Taux %": "{:.1f}%"},
                na_rep="—"),
            use_container_width=True, height=350,
        )
        st.caption("Source effectifs : data/effectifs_conventions.csv — "
                   "« — » = effectif manquant ou nul. Acheteurs = N° Client distincts "
                   "ayant acheté sur la période.")
        with st.expander("➕ Ajouter / corriger un effectif", expanded=False):
            _e1, _e2 = st.columns([2, 1])
            with _e1:
                _new_nom = st.selectbox("Convention",
                    sorted(_conv_rate["Nom"].tolist()), key="eff_conv_nom")
            with _e2:
                _new_eff = st.number_input("Effectif", min_value=0, step=10,
                    key="eff_conv_val")
            if st.button("Enregistrer l'effectif", key="eff_conv_save"):
                try:
                    import csv as _csv
                    from metrics.kpi import EFFECTIFS_PATH as _EFF_P
                    _rows = list(_csv.DictReader(
                        open(_EFF_P, encoding="utf-8"), delimiter=";")) \
                        if _EFF_P.exists() else []
                    _upd = False
                    for _r in _rows:
                        if str(_r.get("societe", "")).strip().lower() == \
                           str(_new_nom).strip().lower():
                            _r["effectif"] = str(int(_new_eff))
                            _upd = True
                    if not _upd:
                        _rows.append({"societe": _new_nom,
                                      "effectif": str(int(_new_eff))})
                    with open(_EFF_P, "w", newline="",
                              encoding="utf-8") as _f:
                        _w = _csv.DictWriter(_f, fieldnames=["societe", "effectif"],
                                             delimiter=";")
                        _w.writeheader()
                        _w.writerows(_rows)
                    st.success(f"Effectif enregistré : {_new_nom} = {int(_new_eff)}")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as _e:
                    st.error(f"Erreur : {_e}")
    else:
        st.caption("Aucune donnée de conversion sur la période.")

    # ── 3. Tableau des conventions (interactif) ──────────
    section("Liste des conventions")

    conv_table = _rm.copy() if not _rm.empty else pd.DataFrame()
    if not conv_table.empty:
        if "Magasin" in df_vc_filt.columns:
            mc = df_vc_filt.groupby("Nom")["Magasin"].nunique().reset_index()
            mc.columns = ["Nom", "Nb magasins"]
            conv_table = conv_table.merge(mc, on="Nom", how="left").fillna(0)
            conv_table["Nb magasins"] = conv_table["Nb magasins"].astype(int)
        if "Date" in df_vc_filt.columns:
            lf = df_vc_filt.groupby("Nom")["Date"].max().reset_index()
            lf.columns = ["Nom", "Dernière facture"]
            conv_table = conv_table.merge(lf, on="Nom", how="left")

        search_c = st.text_input("\U0001f50d Filtrer par nom", placeholder="Tapez un nom de convention...", label_visibility="collapsed")
        if search_c:
            conv_table = conv_table[conv_table["Nom"].str.contains(search_c, case=False, na=False)]

        cols_show = [c for c in ["Nom", "CA N", "CA N-1", "Évolution %", "Statut", "Nb magasins", "Dernière facture"]
                     if c in conv_table.columns]
        st.dataframe(
            conv_table[cols_show].style.format(
                {"CA N": "{:,.0f}", "CA N-1": "{:,.0f}", "Évolution %": "{:+.1f}%"},
                subset=["CA N", "CA N-1", "Évolution %"],
                na_rep="—"
            ),
            use_container_width=True, height=350,
        )

    # ── 4. Détail convention (sélection individuelle) ────
    section("Analyse individuelle")

    conv_detail = None
    if conv_sel != "Tous" and not _rm.empty and conv_sel in _rm["Nom"].values:
        conv_detail = conv_sel
    elif not _rm.empty:
        _all = sorted(_rm["Nom"].tolist())
        conv_detail = st.selectbox("Sélectionner une convention", _all,
                                    index=0, key="conv_selector")

    if conv_detail:
        st.caption(f"Convention : **{conv_detail}**")
        df_cv = df_vc_filt[df_vc_filt["Nom"] == conv_detail].copy()
        ca_cv_n, ca_cv_n1, ev_cv = ca_sum_date_to_date(df_cv, annee_sel, annee_sel - 1, mois_sel)
        nb_fact_cv = len(df_cv[df_cv["Année"] == annee_sel])
        panier_cv  = ca_cv_n / nb_fact_cv if nb_fact_cv > 0 else 0

        cv_statut = _rm[_rm["Nom"] == conv_detail]["Statut"].iloc[0] if not _rm.empty and conv_detail in _rm["Nom"].values else ""
        st.markdown(f"### {conv_detail} &nbsp;{badge(cv_statut, 'red' if 'Déclin' in cv_statut or 'Inactif' in cv_statut else 'green' if 'Croissance' in cv_statut else 'amber')}", unsafe_allow_html=True)

        ci1, ci2, ci3, ci4 = st.columns(4)
        ci1.metric(f"CA {annee_sel}", f"{ca_cv_n:,.0f} TND",
                   f"{fmt_pct(ev_cv)} vs {annee_sel-1}",
                   delta_color=color_delta(ev_cv))
        ci2.metric(f"CA {annee_sel-1}", f"{ca_cv_n1:,.0f} TND")
        ci3.metric(f"Factures {annee_sel}", nb_fact_cv)
        ci4.metric("Panier moyen", f"{panier_cv:,.0f} TND")

        # ── Taux de conversion de CETTE convention (pas de noms clients) ──
        _one = conversion_conventions(df_vc_filt[df_vc_filt["Nom"] == conv_detail],
                                      annee_sel, mois_sel if mois_sel else None)
        if not _one.empty:
            _r = _one.iloc[0]
            _eff = _r.get("Effectif")
            _ach = int(_r.get("Nb acheteurs", 0))
            _tx = _r.get("Taux %")
            t1, t2, t3 = st.columns(3)
            t1.metric("Taux de conversion",
                      f"{_tx:.1f} %" if pd.notna(_tx) else "—",
                      help="Acheteurs distincts / effectif total de la convention")
            t2.metric("Acheteurs", f"{_ach:,}".replace(",", " "))
            t3.metric("Effectif", f"{_eff:,.0f}" if pd.notna(_eff) and _eff else "—")
            if pd.isna(_tx):
                st.caption("Effectif manquant ou nul pour cette convention — "
                           "renseignez-le dans la section « Taux de conversion client » ci-dessus.")

        col_cv1, col_cv2 = st.columns(2)
        df_cv_comp = compare_years_date_to_date(df_cv, annee_sel, annee_sel - 1, mois_sel)

        with col_cv1:
            fig_cv_g = chart_grouped_bar(
                df_cv_comp, "Mois Nom", "CA N", "CA N-1",
                f"CA Mensuel — {conv_detail}", annee_sel,
            )
            st.plotly_chart(fig_cv_g, use_container_width=True)

        with col_cv2:
            _df_fn  = df_cv[df_cv["Année"] == annee_sel]
            _df_fn1 = truncate_n1_date_to_date(df_cv, annee_sel, annee_sel - 1, mois_sel)
            _df_fn1 = _df_fn1[_df_fn1["Année"] == annee_sel - 1]
            _cn  = _df_fn.groupby("Mois")["Montant TTC"].sum().reset_index()
            _cn1 = _df_fn1.groupby("Mois")["Montant TTC"].sum().reset_index()
            _cn["CA Cum N"]    = _cn["Montant TTC"].cumsum()
            _cn1["CA Cum N-1"] = _cn1["Montant TTC"].cumsum()
            df_cum = _cn[["Mois", "CA Cum N"]].merge(
                _cn1[["Mois", "CA Cum N-1"]], on="Mois", how="outer"
            ).ffill().fillna(0)
            df_cum["Mois Nom"] = df_cum["Mois"].map(MOIS)
            fig_cum = chart_line_compare(
                df_cum, "Mois Nom", "CA Cum N", "CA Cum N-1",
                f"CA Cumulé — {conv_detail}", annee_sel,
            )
            st.plotly_chart(fig_cum, use_container_width=True)

        col_cv3, col_cv4 = st.columns(2)
        with col_cv3:
            if "Magasin" in df_cv.columns:
                mag = _df_fn.groupby("Magasin")["Montant TTC"].sum().nlargest(10).reset_index()
                if not mag.empty:
                    fig_mag_cv = chart_bar(
                        mag, "Montant TTC", "Magasin",
                        "Top Magasins", C["purple"], h=360, orientation="h",
                    )
                    st.plotly_chart(fig_mag_cv, use_container_width=True)
                else:
                    st.info("Aucun magasin avec des transactions en N pour cette convention.")

        with col_cv4:
            ca_cash   = _df_fn["Montant TTC"].sum() if len(_df_fn) > 0 else 0
            ca_credit = (df_credit[df_credit["Nom"] == conv_detail]["Montant TTC"].sum()
                         if "Nom" in df_credit.columns else 0)
            if ca_cash > 0 or ca_credit > 0:
                fig_pie_cv = chart_pie([ca_cash, ca_credit], ["Cash", "Crédit"],
                                       f"Cash vs Crédit — {conv_detail}")
                st.plotly_chart(fig_pie_cv, use_container_width=True)

        st.markdown("### \U0001f3ea Magasins contributeurs")
        if "Magasin" in df_cv.columns and len(_df_fn) > 0:
            detail_m = _df_fn.groupby("Magasin").agg(
                Montant_TTC=("Montant TTC", "sum"),
                Nb_Factures=("Montant TTC", "count"),
                Derniere_Vente=("Date", "max"),
            ).reset_index()
            detail_m.columns = ["Magasin", "Montant TTC", "Nb Factures", "Dernière Vente"]

            if len(_df_fn1) > 0:
                ca_n1_m = _df_fn1.groupby("Magasin")["Montant TTC"].sum().reset_index()
                ca_n1_m.columns = ["Magasin", "CA N-1"]
                detail_m = detail_m.merge(ca_n1_m, on="Magasin", how="left").fillna(0)
                detail_m["Évolution %"] = np.where(
                    detail_m["CA N-1"] > 0,
                    ((detail_m["Montant TTC"] - detail_m["CA N-1"]) / detail_m["CA N-1"] * 100).round(1),
                    np.nan,  # sans base N-1 → « — »
                )
                detail_m["CA N-1"] = detail_m["CA N-1"].apply(lambda x: f"{x:,.0f}" if x > 0 else "-")
            else:
                detail_m["CA N-1"] = "-"
                detail_m["Évolution %"] = np.nan  # pas de base N-1 → « — »

            detail_m = detail_m.sort_values("Montant TTC", ascending=False)  # tri AVANT formatage
            detail_m["Montant TTC"]   = detail_m["Montant TTC"].apply(lambda x: f"{x:,.0f}")
            detail_m["Dernière Vente"] = detail_m["Dernière Vente"].dt.strftime("%d/%m/%Y")
            detail_m["Évolution %"]   = detail_m["Évolution %"].apply(
                lambda x: "—" if pd.isna(x) else f"{x:+.1f}%"
            )

            st.dataframe(detail_m,
                         use_container_width=True, height=min(400, 35 * (len(detail_m) + 1)))
        else:
            st.info("Aucune donnée magasin disponible pour cette convention.")


# ══════════════════════════════════════════════════════════════
# TAB 3 — MAGASINS
# ══════════════════════════════════════════════════════════════
with tabs[3]:
    section("Performance réseau")

    if "Magasin" not in df_vc.columns:
        st.info("Données magasin non disponibles")
    else:
        # Date-à-date via la SOURCE UNIQUE (conserve les jours N-1 sans facture N — metrics.kpi)
        _d2d = truncate_n1_date_to_date(df_vc_filt, annee_sel, annee_sel - 1, mois_sel)
        _base_n  = _d2d[_d2d["Année"] == annee_sel].copy()
        _base_n1 = _d2d[_d2d["Année"] == annee_sel - 1].copy()

        all_stores = sorted(_base_n["Magasin"].dropna().unique()) if "Magasin" in _base_n.columns else []

        col_search, col_reset = st.columns([5, 1])
        with col_search:
            search_term = st.text_input("\U0001f50d Filtre magasin", placeholder="Tapez pour chercher...", label_visibility="collapsed")
        with col_reset:
            st.markdown("###")
            if st.button("\U0001f504 Réinitialiser", use_container_width=True):
                st.session_state.pop("store_selector", None)
                st.rerun()

        filtered_stores = [s for s in all_stores if search_term.lower() in s.lower()] if search_term else all_stores[:50]
        options = ["Tous"] + filtered_stores

        selected_store = st.selectbox(
            "Magasin", options, index=0, key="store_selector",
            format_func=lambda x: "\U0001f310 Tous les magasins" if x == "Tous" else f"\U0001f3ea {x}",
            label_visibility="collapsed",
        )

        if selected_store == "Tous":
            ca_mag_n  = _base_n.groupby("Magasin")["Montant TTC"].sum().rename("CA N")
            ca_mag_n1 = _base_n1.groupby("Magasin")["Montant TTC"].sum().rename("CA N-1")
            ca_mag = pd.concat([ca_mag_n, ca_mag_n1], axis=1).fillna(0).reset_index()

            ca_mag["Evolution %"] = np.where(
                ca_mag["CA N-1"] > 0,
                ((ca_mag["CA N"] - ca_mag["CA N-1"]) / ca_mag["CA N-1"] * 100).round(1),
                0.0
            )

            if not df_cube_mag.empty and "Magasin" in df_cube_mag.columns:
                cube_agg = df_cube_mag.groupby("Magasin")["CA Magasin"].sum().reset_index()
                cube_agg.columns = ["Magasin", "CA Total Magasin"]
                ca_mag = ca_mag.merge(cube_agg, on="Magasin", how="left").fillna(0)
            else:
                ca_mag["CA Total Magasin"] = 0

            total_n = ca_mag["CA N"].sum()
            ca_mag["Poids %"] = (ca_mag["CA N"] / total_n * 100).round(1) if total_n > 0 else 0.0

            ca_mag = ca_mag.sort_values("CA N", ascending=False)
            simple_sum = _base_n["Montant TTC"].sum()

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("\U0001f3ea Magasins actifs", len(ca_mag[ca_mag["CA N"] > 0]))
            k2.metric("\U0001f4b0 CA Total Conventions", f"{simple_sum:,.0f} TND")
            k3.metric("\U0001f4c8 En croissance", len(ca_mag[ca_mag["Evolution %"] > 0]), f"/ {len(ca_mag)}")
            k4.metric("\U0001f4c9 En baisse", len(ca_mag[ca_mag["Evolution %"] < 0]))

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                top10 = ca_mag.head(10)
                fig_top = px.bar(top10, x="CA N", y="Magasin", orientation="h",
                                title=f"Top 10 — CA {annee_sel}", color="CA N",
                                color_continuous_scale=["#1D4ED8", "#3B82F6", "#60A5FA"],
                                text_auto=".0f", height=450)
                fig_top.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_top, use_container_width=True)
            with col_m2:
                fig_evo = px.bar(top10, x="Evolution %", y="Magasin", orientation="h",
                               title="Top 10 — Évolution N/N-1", color="Evolution %",
                               color_continuous_scale=["#DC2626", "#FCD34D", "#059669"],
                               text_auto="+.1f", height=450)
                fig_evo.update_layout(yaxis=dict(autorange="reversed"))
                fig_evo.add_vline(x=0, line_dash="dash", line_color="grey")
                st.plotly_chart(fig_evo, use_container_width=True)

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if "Enseigne" in _base_n.columns:
                    by_ense = _base_n.groupby("Enseigne")["Montant TTC"].sum()
                    fig_ense = px.pie(values=by_ense.values, names=by_ense.index,
                                     title="CA par Enseigne", hole=0.4)
                    fig_ense.update_traces(textinfo="percent+label")
                    st.plotly_chart(fig_ense, use_container_width=True)
            with col_p2:
                if "Type vente à crédit" in _base_n.columns:
                    by_type = _base_n.groupby("Type vente à crédit")["Montant TTC"].sum()
                    by_type = by_type[by_type > 0]
                    fig_type = px.bar(by_type.reset_index(), x="Type vente à crédit", y="Montant TTC",
                                    title="CA par Type de vente", text_auto=".0f",
                                    color="Montant TTC", color_continuous_scale=["#1D4ED8", "#3B82F6"])
                    st.plotly_chart(fig_type, use_container_width=True)

            with st.expander("\U0001f4cb Tableau complet des magasins"):
                display_cols = ["Magasin", "CA N", "Poids %", "Evolution %"]
                available = [c for c in display_cols if c in ca_mag.columns]
                st.dataframe(
                    ca_mag[available].style.format(
                        {"CA N": "{:,.0f}", "Poids %": "{:.1f}%", "Evolution %": "{:+.1f}%"},
                        na_rep="—"
                    ), use_container_width=True, height=400
                )

        else:
            store_n  = _base_n[_base_n["Magasin"] == selected_store]
            store_n1 = _base_n1[_base_n1["Magasin"] == selected_store]
            enseigne = store_n["Enseigne"].iloc[0] if "Enseigne" in store_n.columns and len(store_n) > 0 else "N/A"

            st.markdown(f"## \U0001f3ea {selected_store} &nbsp;"
                        f"<span style='background:#1D4ED8;color:white;padding:2px 10px;border-radius:4px;font-size:11px'>{enseigne}</span>",
                        unsafe_allow_html=True)

            ca_n_s = store_n["Montant TTC"].sum() if len(store_n) > 0 else 0
            ca_n1_s = store_n1["Montant TTC"].sum() if len(store_n1) > 0 else 0
            evol_s = evol_pct(ca_n_s, ca_n1_s)
            nb_fact_s = len(store_n)
            panier_s = ca_n_s / nb_fact_s if nb_fact_s > 0 else 0

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric(f"\U0001f4b0 CA {annee_sel}", f"{ca_n_s:,.0f} TND", fmt_pct(evol_s), delta_color=color_delta(evol_s))
            k2.metric(f"\U0001f4c5 CA {annee_sel-1}", f"{ca_n1_s:,.0f} TND")
            k3.metric("\U0001f9fe Factures", nb_fact_s)
            k4.metric("\U0001f4ca Panier moyen", f"{panier_s:,.0f} TND")
            k5.metric("\U0001f3f7\ufe0f Enseigne", enseigne)

            if "Mois" in store_n.columns:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    ca_mens = store_n.groupby("Mois")["Montant TTC"].sum().reset_index()
                    ca_mens["Mois_nom"] = ca_mens["Mois"].map(MOIS)
                    ca_mens_n1_v = store_n1.groupby("Mois")["Montant TTC"].sum().reindex(ca_mens["Mois"]).fillna(0).values
                    ca_mens[f"CA {annee_sel-1}"] = ca_mens_n1_v
                    fig_mens = px.bar(ca_mens, x="Mois_nom", y=["Montant TTC", f"CA {annee_sel-1}"],
                                     title=f"CA Mensuel", barmode="group", text_auto=".0f",
                                     color_discrete_map={"Montant TTC": "#1D4ED8", f"CA {annee_sel-1}": "#94A3B8"})
                    fig_mens.update_layout(height=260, showlegend=False)
                    st.plotly_chart(fig_mens, use_container_width=True)
                with col_c2:
                    ca_cum = store_n.groupby("Mois")["Montant TTC"].sum().cumsum().reset_index()
                    ca_cum["Mois_nom"] = ca_cum["Mois"].map(MOIS)
                    fig_cum = px.line(ca_cum, x="Mois_nom", y="Montant TTC", title="CA Cumulé", markers=True)
                    fig_cum.update_traces(line_color="#1D4ED8", line_width=3)
                    fig_cum.update_layout(height=260)
                    st.plotly_chart(fig_cum, use_container_width=True)

            st.markdown("### \U0001f3db\ufe0f Conventions")
            if "Type vente à crédit" in store_n.columns:
                mk = store_n["Type vente à crédit"].fillna("").str.upper().str.contains("CONV")
                conv_n = store_n[mk]
                if "Nom" in conv_n.columns and len(conv_n) > 0:
                    detail = conv_n.groupby("Nom").agg(
                        Montant_TTC=("Montant TTC", "sum"),
                        Nb_Factures=("Montant TTC", "count"),
                        Derniere_Vente=("Date", "max"),
                    ).reset_index()
                    detail.columns = ["Convention", "Montant TTC", "Nb Factures", "Dernière Vente"]
                    detail = detail.sort_values("Montant TTC", ascending=False)  # tri AVANT formatage
                    detail["Montant TTC"] = detail["Montant TTC"].apply(lambda x: f"{x:,.0f}")
                    detail["Dernière Vente"] = detail["Dernière Vente"].dt.strftime("%d/%m/%Y")
                    st.dataframe(detail,
                                use_container_width=True, height=min(300, 35 * (len(detail) + 1)))
                else:
                    st.info("Aucune convention sur la période.")

            st.markdown("### \U0001f4b3 Autres segments")

            @st.cache_data(show_spinner=False)
            def _cached_segment_kpis(df_src_val, store, _df_vc_ref, annee, mois_tuple):
                df_n = pd.DataFrame()
                df_n1 = pd.DataFrame()
                if "Unite Code" in df_src_val.columns:
                    code_col = next((c for c in _df_vc_ref.columns if c.lower() == "unite code"), None)
                    if code_col and "Magasin" in _df_vc_ref.columns:
                        codes = _df_vc_ref[_df_vc_ref["Magasin"] == store][code_col].dropna().unique()
                        if len(codes) > 0:
                            sc = [str(c).strip() for c in codes]
                            scf = [c + ".0" if not c.endswith(".0") else c for c in sc]
                            match = df_src_val["Unite Code"].astype(str).str.strip().isin(sc + scf)
                            df_n = df_src_val[match & (df_src_val["Année"] == annee)]
                            df_n1 = df_src_val[match & (df_src_val["Année"] == annee - 1)]
                if df_n.empty:
                    return "empty", 0, 0, 0, 0

                ml = list(mois_tuple) if mois_tuple else None
                if ml:
                    df_n = df_n[df_n["Mois"].isin(ml)]
                    df_n1 = df_n1[df_n1["Mois"].isin(ml)]

                if len(df_n) > 0 and "Jour" in df_n.columns and len(df_n1) > 0:
                    comp = compare_years_date_to_date(pd.concat([df_n, df_n1]),
                                                      annee, annee - 1, ml)
                    ca_n_val = comp["CA N"].sum() if not comp.empty else 0
                    ca_n1_val = comp["CA N-1"].sum() if not comp.empty else 0
                else:
                    ca_n_val = df_n["Montant TTC"].sum() if len(df_n) > 0 else 0
                    ca_n1_val = df_n1["Montant TTC"].sum() if len(df_n1) > 0 else 0

                ev = evol_pct(ca_n_val, ca_n1_val)
                nb = len(df_n)
                pm = ca_n_val / nb if nb > 0 else 0
                return "ok", ca_n_val, ca_n1_val, ev, nb, pm

            def _segment_expander(label, icon, df_src):
                with st.expander(f"{icon} {label}", expanded=False):
                    mo_tup = tuple(mois_sel) if mois_sel else ()
                    result = _cached_segment_kpis(df_src, selected_store, df_vc, annee_sel, mo_tup)
                    status = result[0]
                    if status == "empty":
                        st.info(f"Aucune donnée {label} pour ce magasin.")
                        return
                    _, ca_n_val, ca_n1_val, ev, nb, pm = result

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"{icon} Dossiers", nb)
                    c2.metric(f"\U0001f4b0 CA {annee_sel}", f"{ca_n_val:,.0f} TND",
                              fmt_pct(ev) if ca_n_val > 0 else None,
                              delta_color=color_delta(ev))
                    c3.metric(f"\U0001f4c5 CA {annee_sel-1}", f"{ca_n1_val:,.0f} TND")
                    c4.metric("\U0001f4ca Panier moyen", f"{pm:,.0f} TND" if nb > 0 else "0 TND")

            _segment_expander("Crédit Conso", "\U0001f4b3", df_credit)
            _segment_expander("Crédit Particulier", "\U0001f464", df_credit_part)
            _segment_expander("Convention EDC", "\U0001f3eb", df_edc)

            with st.expander("\U0001f4c4 Détail des opérations"):
                cols_show = [c for c in store_n.columns if c in ["Date", "Mois", "Nom", "Montant TTC", "Type vente à crédit", "Enseigne"]]
                st.dataframe(store_n[cols_show].sort_values("Date", ascending=False), use_container_width=True)

    with st.expander("\U0001f4ca Consolidation multi-sources (Crédit, EDC, Particulier)", expanded=False):
        """Vue consolidée tous types de financement (ex-Tab Pilotage)"""
        df_vc_tmp     = df_vc.copy()
        df_cr_tmp     = df_credit.copy()
        df_edc_tmp    = df_edc.copy()
        df_part_tmp   = df_credit_part.copy()

        TYPE_MAP = {
            "vc":    "Convention",
            "vc_credit": "Crédit Conso UBCI",
            "vc_part": "Crédit Particulier",
            "vc_edc": "EDC",
        }

        def _prep_source(df, df_code, src_key):
            if df.empty:
                return pd.DataFrame()
            df = df.copy()
            date_col = next((c for c in df.columns if "date" in c.lower()), None)
            ca_col  = next((c for c in df.columns if "montant" in c.lower() or "ca" in c.lower()), None)
            mag_col = next((c for c in df.columns if c.lower() == "code magasin".lower()), None)
            if not mag_col:
                mag_col = next((c for c in df.columns if "code" in c.lower() and "magasin" in c.lower()), None)
            if date_col and ca_col and mag_col:
                try:
                    df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
                except Exception:
                    df["_date"] = pd.NaT
                df["_ca"] = pd.to_numeric(df[ca_col], errors="coerce")
                if not df_code.empty:
                    code_col = next((c for c in df_code.columns if "code" in c.lower()), None)
                    name_col = next((c for c in df_code.columns if c != code_col), None)
                    if code_col and name_col:
                        mapping = df_code.set_index(code_col)[name_col].to_dict()
                        df["_code_mag"] = df[mag_col].astype(str).str.strip()
                        df["_nom_mag"] = df[mag_col].astype(str).str.strip().map(mapping).fillna(df["_code_mag"])
                    else:
                        df["_code_mag"] = df[mag_col].astype(str)
                        df["_nom_mag"] = df[mag_col].astype(str)
                else:
                    df["_code_mag"] = df[mag_col].astype(str)
                    df["_nom_mag"] = df[mag_col].astype(str)
                df["_type"] = TYPE_MAP.get(src_key, src_key)
                return df[["_date", "_ca", "_code_mag", "_nom_mag", "_type"]]
            return pd.DataFrame()

        sources = [
            ("vc", df_vc_tmp),
            ("vc_credit", df_cr_tmp),
            ("vc_part", df_part_tmp),
            ("vc_edc", df_edc_tmp),
        ]

        df_all_list = []
        for key, df_src in sources:
            prepped = _prep_source(df_src, code_df, key)
            if not prepped.empty:
                df_all_list.append(prepped)

        if df_all_list:
            df_consol = pd.concat(df_all_list, ignore_index=True, copy=False)
        else:
            df_consol = pd.DataFrame()

        if df_consol.empty:
            st.warning("\u26a0\ufe0f Aucune donnée disponible.")
        else:
            df_consol["Année"] = df_consol["_date"].dt.year
            df_consol["Mois"] = df_consol["_date"].dt.month
            df_consol["JMois"] = df_consol["_date"].dt.to_period("M").astype(str)

            # Filtres inline
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                all_magasins = sorted(df_consol["_nom_mag"].dropna().unique().tolist())
                mag_sel_x = st.multiselect("Magasin(s)", all_magasins, default=[], key="consol_mag")
            with col_f2:
                min_d = df_consol["_date"].min()
                max_d = df_consol["_date"].max()
                if pd.notna(min_d) and pd.notna(max_d):
                    date_range_x = st.date_input("Période", value=(min_d.date(), max_d.date()), key="consol_date")
                    date_deb_x, date_fin_x = date_range_x[0], date_range_x[1] if len(date_range_x) == 2 else (None, None)
                else:
                    date_deb_x, date_fin_x = None, None
            with col_f3:
                all_mois = sorted(df_consol["Mois"].dropna().unique().tolist())
                mois_sel_x = st.multiselect("Mois", all_mois, default=all_mois, format_func=lambda x: MOIS.get(x, str(x)), key="consol_mois")

            df_f = df_consol.copy()
            if mag_sel_x:
                df_f = df_f[df_f["_nom_mag"].isin(mag_sel_x)]
            if mois_sel_x:
                df_f = df_f[df_f["Mois"].isin(mois_sel_x)]
            if date_deb_x and date_fin_x:
                df_f = df_f[(df_f["_date"] >= pd.Timestamp(date_deb_x)) & (df_f["_date"] <= pd.Timestamp(date_fin_x))]

            df_f["_ca"] = pd.to_numeric(df_f["_ca"], errors="coerce")
            df_f = df_f.dropna(subset=["_ca"])

            if df_f.empty:
                st.info("Aucune transaction pour les filtres sélectionnés.")
            else:
                an  = int(annee_sel)
                an1 = an - 1

                st.markdown("##### Répartition CA par type de financement")
                ca_by_type = df_f[df_f["Année"] == an].groupby("_type")["_ca"].sum().reset_index()
                ca_by_type.columns = ["Type", "CA"]
                ca_by_type["%"] = (ca_by_type["CA"] / ca_by_type["CA"].sum() * 100).round(1)

                pc1, pc2 = st.columns([1, 1])
                with pc1:
                    fig_pie = px.pie(ca_by_type, values="CA", names="Type", hole=0.4,
                                   color_discrete_sequence=[C["blue"], C["green"], C["purple"], C["amber"]])
                    fig_pie.update_layout(margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_pie, use_container_width=True)
                with pc2:
                    st.dataframe(ca_by_type.rename(columns={"CA": "CA (TND)"}), use_container_width=True)

                st.markdown("##### CA par type — même période")
                available_types = [t for t in TYPE_MAP.values() if t in df_f["_type"].unique()]
                col_types = st.columns(len(available_types)) if available_types else [st.columns(1)]
                for idx, type_label in enumerate(available_types):
                    df_t = df_f[df_f["_type"] == type_label]
                    with col_types[idx]:
                        st.markdown(f"**{type_label}**")
                        if df_t.empty:
                            st.info(f"Aucune donnée")
                            continue

                        ca_t   = df_t[df_t["Année"] == an]["_ca"].sum()
                        ca_t1  = df_t[df_t["Année"] == an1]["_ca"].sum()
                        evo_t  = evol_pct(ca_t, ca_t1)
                        nb_t   = len(df_t[df_t["Année"] == an])
                        pan_t  = ca_t / nb_t if nb_t > 0 else 0

                        st.metric(f"CA {an}", f"{ca_t:,.0f} TND", fmt_pct(evo_t), delta_color=color_delta(evo_t))
                        st.metric(f"CA {an1}", f"{ca_t1:,.0f} TND")
                        st.metric("Transactions", nb_t)
                        st.metric("Panier moyen", f"{pan_t:,.0f} TND")

                        pie_data = df_t.groupby("_nom_mag")["_ca"].sum().reset_index()
                        pie_data.columns = ["Magasin", "CA"]
                        if not pie_data.empty:
                            fig_p = px.pie(pie_data.head(10), values="CA", names="Magasin", hole=0.4,
                                         color_discrete_sequence=px.colors.qualitative.Set3)
                            fig_p.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=300)
                            st.plotly_chart(fig_p, use_container_width=True, key=f"consol_pie_{type_label}")

                st.markdown("##### Tableau détaillé")
                detail = df_f[df_f["Année"] == an].groupby(["_nom_mag", "_type"])["_ca"].sum().reset_index()
                detail.columns = ["Magasin", "Type", "CA"]
                detail["%"] = (detail["CA"] / detail["CA"].sum() * 100).round(2)
                detail = detail.sort_values("CA", ascending=False)
                st.dataframe(detail, use_container_width=True)

                csv = detail.to_csv(index=False).encode("utf-8")
                st.download_button("\U0001f4e5 Export CSV", data=csv, file_name="pilotage_magasin.csv", mime="text/csv")

    # ── Performance par enseigne ─────────────────────────────
    def _render_enseigne_section(enseigne, color_scale):
        _df = df_vc_filt[df_vc_filt["Enseigne"] == enseigne].copy()
        if _df.empty:
            st.caption(f"Aucune donnée {enseigne} disponible.")
            return
        # Date-à-date via la SOURCE UNIQUE (conserve les jours N-1 sans facture N — metrics.kpi)
        _d2d = truncate_n1_date_to_date(_df, annee_sel, annee_sel - 1, mois_sel)
        _n  = _d2d[_d2d["Année"] == annee_sel]
        _n1 = _d2d[_d2d["Année"] == annee_sel - 1]
        _ca_n  = _n["Montant TTC"].sum()
        _ca_n1 = _n1["Montant TTC"].sum()
        _ev = evol_pct(_ca_n, _ca_n1)
        _nb_mag = _n["Magasin"].nunique()
        _nb_mag_n1 = _n1["Magasin"].nunique()
        _part = _ca_n / df_vc[df_vc["Année"] == annee_sel]["Montant TTC"].sum() * 100 if not df_vc[df_vc["Année"] == annee_sel].empty else 0
        _c1, _c2, _c3, _c4, _c5 = st.columns(5)
        _c1.metric(f"CA {enseigne} {annee_sel}", f"{_ca_n:,.0f}", fmt_pct(_ev),
                   delta_color=color_delta(_ev))
        _c2.metric(f"CA {enseigne} {annee_sel-1}", f"{_ca_n1:,.0f}")
        _c3.metric("Magasins actifs", _nb_mag, f"{_nb_mag - _nb_mag_n1:+d} vs N-1")
        _c4.metric("Part du CA total", f"{_part:.1f}%")
        _c5.metric("Panier moyen", f"{_ca_n/len(_n):,.0f}" if len(_n) > 0 else "0")
        # Monthly trend
        _t = _df[_df["Année"].isin([annee_sel, annee_sel-1])]
        _t = _t.groupby(["Année", "Mois"])["Montant TTC"].sum().reset_index()
        fig_t = go.Figure()
        for yr in [annee_sel, annee_sel-1]:
            _by = _t[_t["Année"] == yr]
            fig_t.add_trace(go.Bar(x=_by["Mois"], y=_by["Montant TTC"],
                                   name=str(yr),
                                   marker_color=C["blue"] if yr == annee_sel else C["slate"],
                                   opacity=0.8 if yr == annee_sel else 0.5))
        fig_t.update_layout(height=250, barmode="group",
                            xaxis=dict(tickmode="array", tickvals=list(range(1,13)),
                                       ticktext=[MOIS[i] for i in range(1,13)]),
                            margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_t, use_container_width=True)
        # Top stores
        _top = _n.groupby("Magasin")["Montant TTC"].sum().nlargest(10).reset_index()
        if not _top.empty:
            fig_tp = px.bar(_top, x="Montant TTC", y="Magasin", orientation="h",
                            title=f"Top 10 Magasins {enseigne} — {annee_sel}",
                            color="Montant TTC", color_continuous_scale=color_scale,
                            text_auto=".0f")
            fig_tp.update_layout(height=420, yaxis=dict(autorange="reversed"),
                                 margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_tp, use_container_width=True)

    section("BATAM — Performance réseau")
    _render_enseigne_section("BATAM", ["#D97706", "#F59E0B"])

    section("MG — Performance réseau")
    _render_enseigne_section("MG", ["#1D4ED8", "#3B82F6", "#60A5FA"])


# ══════════════════════════════════════════════════════════════
# TAB 4 — LENS · TOUS FLUX & MUTUELLES
# ══════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("🧭 Tous flux & Mutuelles — sélecteur de périmètre")
    st.caption(
        "Un seul corps de lecture pour 6 périmètres : EDC, Mutuelle Sûreté, "
        "Mutuelle Garde NLE & Protection Civile, et les vues Convention / Conso / "
        "Particulier globales. Lecture en 5 sections : situation → dynamique → "
        "réseau → échéance → synthèse."
    )
    _lens_label = st.selectbox(
        "Périmètre",
        LENS_LABELS,
        key="lens_p",
        help="Filtre appliqué à toute la page : données, filtres, graphiques, synthèse.",
    )
    meta = _lens_meta(_lens_label)
    st.subheader(meta["title"])
    st.caption(meta["caption"])

    if not meta["df"].empty and "Année" in meta["df"].columns:
        # ── NIVEAU 0 · préparation du périmètre + dates ──────────────
        edc = meta["df"].copy()
        if "Montant TTC" not in edc.columns:
            edc["Montant TTC"] = 0.0
        edc["Montant TTC"] = pd.to_numeric(edc["Montant TTC"], errors="coerce").fillna(0.0)
        _mag = edc["Magasin"].astype(str).str.strip() if "Magasin" in edc.columns else pd.Series("", index=edc.index)
        _mag_abs = _mag.str.lower().isin(["", "nan", "none", "<na>"])
        _mag_digit = (~_mag_abs) & _mag.str.match(r"^\d+(\.0)?$", na=False)
        edc["Magasin"] = _mag.where(~_mag_abs, "Magasin non renseigné")
        edc.loc[_mag_digit, "Magasin"] = "Code " + _mag[_mag_digit].str.replace(r"\.0$", "", regex=True) + " (non mappé)"
        if "Enseigne" not in edc.columns:
            edc["Enseigne"] = "MG"
        edc["Enseigne"] = edc["Enseigne"].where(
            edc["Enseigne"].astype(str).str.strip().str.len() > 0, "MG"
        )

        # ── NIVEAU 1 · filtres du compte ─────────────────────────────
        annees_dispo = sorted({int(a) for a in edc["Année"].dropna().unique()}, reverse=True)
        fc1, fc2, fc3 = st.columns([1, 1.3, 2.2])
        with fc1:
            edc_yr = st.selectbox("Année de référence", annees_dispo, index=0, key="edc_yr")
        with fc2:
            _ens_all = sorted(str(e) for e in edc["Enseigne"].dropna().unique().tolist())
            ens_sel = st.multiselect("Enseigne", _ens_all, default=[], key=f"lens_{meta['key']}_ens")
        with fc3:
            _mag_base = edc[edc["Enseigne"].isin(ens_sel)] if ens_sel else edc
            _mags = sorted(str(m) for m in _mag_base["Magasin"].dropna().unique().tolist())
            mag_sel = st.multiselect("Établissement", _mags, default=[], key=f"lens_{meta['key']}_mag")
        edc_f = edc
        if ens_sel:
            edc_f = edc_f[edc_f["Enseigne"].isin(ens_sel)]
        if mag_sel:
            edc_f = edc_f[edc_f["Magasin"].isin(mag_sel)]

        # ── Périodes comparées — UNE SEULE discipline date à date ────
        df_edc_n = edc_f[edc_f["Année"] == edc_yr]
        if mois_sel:
            df_edc_n = df_edc_n[df_edc_n["Mois"].isin(mois_sel)]
        _trunc_e = truncate_n1_date_to_date(edc_f, edc_yr, edc_yr - 1, mois_sel)
        df_edc_n1 = _trunc_e[_trunc_e["Année"] == edc_yr - 1]
        if mois_sel:
            df_edc_n1 = df_edc_n1[df_edc_n1["Mois"].isin(mois_sel)]
        comp = (
            compare_years_date_to_date(edc_f, edc_yr, edc_yr - 1, mois_sel)
            if len(df_edc_n) > 0 and len(df_edc_n1) > 0
            else pd.DataFrame()
        )
        if not comp.empty:
            ca_e_n = float(comp["CA N"].sum())
            ca_e_n1 = float(comp["CA N-1"].sum())
        else:
            ca_e_n = float(df_edc_n["Montant TTC"].sum())
            ca_e_n1 = float(df_edc_n1["Montant TTC"].sum())

        ev_edc = evol_pct(ca_e_n, ca_e_n1)
        nb_f_edc = len(df_edc_n)
        nb_f_n1 = len(df_edc_n1)
        panier_e = ca_e_n / nb_f_edc if nb_f_edc > 0 else 0.0
        panier_n1 = ca_e_n1 / nb_f_n1 if nb_f_n1 > 0 else 0.0
        mois_dispo_n = sorted(
            int(m) for m in edc_f[edc_f["Année"] == edc_yr]["Mois"].dropna().unique()
        )
        ca_e_annee = float(edc_f[edc_f["Année"] == edc_yr]["Montant TTC"].sum())

        def _edc_delta(n_val: float, n1_val: float):
            """Delta % affichable, None sans base N-1 (évite le +0.0% artificiel)."""
            return f"{evol_pct(n_val, n1_val):+.1f}%" if n1_val > 0 else None

        st.caption(
            f"Année {edc_yr} — mois disponibles : "
            f"{', '.join(MOIS.get(m, str(m)) for m in mois_dispo_n) or 'aucun'}"
            + (f" • Mois analysés : {', '.join(MOIS.get(m, str(m)) for m in sorted(mois_sel))}" if mois_sel else "")
            + (" • Périmètre : tous les établissements"
               if not mag_sel else f" • Périmètre : {len(mag_sel)} établissement(s)")
        )

        # ══ SECTION 1 · SITUATION — indicateurs clés ════════════════
        section("1 · Situation — indicateurs clés")

        _kpi_row = st.columns(5 if meta["parent"] is not None else 4)
        e1, e2, e3, e4 = _kpi_row[:4]
        with e1:
            kpi_card(
                f"CA {edc_yr}",
                f"{ca_e_n:,.0f} TND",
                _edc_delta(ca_e_n, ca_e_n1),
                delta_tone="normal",
                ref_label=f"CA {edc_yr - 1}",
                ref_value=f"{ca_e_n1:,.0f} TND",
                help=f"Comparé date à date avec {edc_yr - 1} : mêmes mois et mêmes jours que {edc_yr}.",
            )
        with e2:
            st.metric(
                "Nb factures",
                f"{nb_f_edc:,}",
                _edc_delta(nb_f_edc, nb_f_n1),
                delta_color="normal",
                help=f"Factures de la période, vs {edc_yr - 1} sur la même période (date à date).",
            )
        with e3:
            st.metric(
                "Panier moyen",
                f"{panier_e:,.0f} TND",
                _edc_delta(panier_e, panier_n1),
                delta_color="normal",
                help="CA de la période divisé par le nombre de factures de la période.",
            )
        with e4:
            st.metric(
                "Écart vs N-1",
                f"{ca_e_n - ca_e_n1:+,.0f} TND",
                help=f"Écart en valeur du CA vs {edc_yr - 1} sur la période comparée (date à date).",
            )

        if meta["parent"] is not None:
            _par = meta["parent"]
            _par_p = _par[_par["Année"] == edc_yr]
            if mois_sel:
                _par_p = _par_p[_par_p["Mois"].isin(mois_sel)]
            _ca_parent = float(
                pd.to_numeric(_par_p["Montant TTC"], errors="coerce").fillna(0).sum()
            )
            _part_pct = (ca_e_n / _ca_parent * 100) if _ca_parent > 0 else None
            with _kpi_row[4]:
                st.metric(
                    f"Part du périmètre ({meta['flux_label']})",
                    f"{_part_pct:.2f} %" if _part_pct is not None else "—",
                    help=f"CA {edc_yr} de ce périmètre rapporté au CA total du flux "
                         f"{meta['flux_label']} sur la même période (année et mois filtrés).",
                )

        # ── Agrégat établissements — base N-1 tronquée, cohérente des tuiles ──
        etab = (
            df_edc_n.groupby("Magasin")
            .agg(CA_N=("Montant TTC", "sum"), Nb=("Montant TTC", "count"))
            .reset_index()
            .rename(columns={"CA_N": "CA N"})
        )
        _et_n1 = (
            df_edc_n1.groupby("Magasin")["Montant TTC"].sum().rename("CA N-1").reset_index()
        )
        etab = etab.merge(_et_n1, on="Magasin", how="outer")
        etab["CA N"] = etab["CA N"].fillna(0.0)
        etab["CA N-1"] = etab["CA N-1"].fillna(0.0)
        etab["Nb"] = etab["Nb"].fillna(0).astype(int)
        etab["Évolution %"] = np.where(
            etab["CA N-1"] > 0,
            ((etab["CA N"] - etab["CA N-1"]) / etab["CA N-1"] * 100).round(1),
            np.nan,
        )
        etab["Panier moyen"] = (etab["CA N"] / etab["Nb"].replace(0, np.nan)).fillna(0).round(0)
        total_edc_n = float(etab["CA N"].sum())
        etab["Poids %"] = (etab["CA N"] / total_edc_n * 100).round(1) if total_edc_n > 0 else 0.0
        etab = etab.sort_values("CA N", ascending=False).reset_index(drop=True)
        etab["Poids cumulé %"] = etab["Poids %"].cumsum().round(1) if total_edc_n > 0 else 0.0
        etab["Statut"] = np.select(
            [
                (etab["CA N"] == 0) & (etab["CA N-1"] == 0),
                (etab["CA N"] > 0) & (etab["CA N-1"] == 0),
                (etab["CA N"] == 0) & (etab["CA N-1"] > 0),
                etab["Évolution %"] <= SEUILS["declin_fort_pct"],
                etab["Évolution %"] < 0,
            ],
            [
                "⚫ Aucun CA",
                "\U0001f7e2 Nouveau",
                "\U0001f534 Sorti",
                "\U0001f534 Déclin fort",
                "\U0001f7e1 Déclin",
            ],
            default="\U0001f7e2 Croissance",
        )
        _hors_net = etab["Magasin"].isin(["Magasin non renseigné", "Inconnu"]) | etab[
            "Magasin"
        ].str.startswith("Code ", na=False)
        mag_net = etab[~_hors_net].copy()
        mag_net_tot = float(mag_net["CA N"].sum())
        if mag_net_tot > 0:
            mag_net["Poids net %"] = (mag_net["CA N"] / mag_net_tot * 100).round(1)
            mag_net["Poids net cumulé %"] = mag_net["Poids net %"].cumsum().round(1)
        else:
            mag_net["Poids net %"] = 0.0
            mag_net["Poids net cumulé %"] = 0.0
        n_actifs = int((mag_net["CA N"] > 0).sum())
        n_actifs_n1 = int((mag_net["CA N-1"] > 0).sum())
        n_nouveaux = int(((mag_net["CA N"] > 0) & (mag_net["CA N-1"] == 0)).sum())
        n_sortis = int(((mag_net["CA N"] == 0) & (mag_net["CA N-1"] > 0)).sum())
        n_en_hausse = int((mag_net["Évolution %"] > 0).sum())
        n_en_baisse = int((mag_net["Évolution %"] < 0).sum())

        c_et1, c_et2, c_et3, c_et4, c_et5 = st.columns(5)
        with c_et1:
            st.metric(
                "Établissements actifs",
                f"{n_actifs}",
                _edc_delta(n_actifs, n_actifs_n1),
                delta_color="normal",
                help="Établissements avec au moins une facture sur la période (réseau mappé, hors codes non mappés).",
            )
        with c_et2:
            st.metric(
                "Nouveaux",
                f"{n_nouveaux}",
                help=f"Avec CA en {edc_yr} et aucun CA sur la période {edc_yr - 1} correspondante.",
            )
        with c_et3:
            st.metric(
                "Sortis",
                f"{n_sortis}",
                help=f"Sans CA en {edc_yr} alors qu'ils en avaient sur la période {edc_yr - 1}.",
            )
        with c_et4:
            st.metric(
                "En croissance",
                f"{n_en_hausse}",
                help="CA de la période supérieur à la base N-1 tronquée (date à date).",
            )
        with c_et5:
            st.metric(
                "En baisse",
                f"{n_en_baisse}",
                help="CA de la période inférieur à la base N-1 tronquée (date à date).",
            )

        # ── États contextuels ───────────────────────────────────────
        if len(df_edc_n) == 0 and len(df_edc_n1) == 0:
            st.warning(
                f"Aucune ligne sur le périmètre et les mois sélectionnés — "
                f"CA {edc_yr} toutes périodes : {ca_e_annee:,.0f} TND. "
                "Élargissez le filtre « Mois » (barre latérale) ou le périmètre établissement."
            )
        elif mois_sel and mois_dispo_n and max(mois_sel) > max(mois_dispo_n):
            st.info(
                f"ℹ️ Données {edc_yr} disponibles jusqu'à "
                f"{MOIS.get(max(mois_dispo_n), str(max(mois_dispo_n)))} — "
                "les mois suivants ne sont pas encore comptabilisés."
            )

        # ══ SECTION 2 · DYNAMIQUE & SAISONNALITÉ ═══════════════════
        section("2 · Dynamique & saisonnalité")
        if comp.empty:
            st.info(f"Pas de comparatif {edc_yr - 1} exploitable pour le périmètre sélectionné.")
        else:
            st.plotly_chart(
                chart_grouped_bar(
                    comp,
                    "Mois Nom",
                    "CA N",
                    "CA N-1",
                    f"CA mensuel {meta['short']} — {edc_yr} vs {edc_yr - 1} (date à date)",
                    edc_yr,
                ),
                use_container_width=True,
            )

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                comp_cum = comp.sort_values("Mois").copy()
                comp_cum["CA N"] = comp_cum["CA N"].cumsum()
                comp_cum["CA N-1"] = comp_cum["CA N-1"].cumsum()
                st.plotly_chart(
                    chart_line_compare(
                        comp_cum,
                        "Mois Nom",
                        "CA N",
                        "CA N-1",
                        f"CA cumulé {meta['short']} — {edc_yr} vs {edc_yr - 1} (date à date)",
                        edc_yr,
                    ),
                    use_container_width=True,
                )
            with col_g2:
                _fn = df_edc_n.groupby("Mois").size().to_dict()
                _fn1 = df_edc_n1.groupby("Mois").size().to_dict()
                fact_m = comp[["Mois", "Mois Nom"]].copy()
                fact_m["Factures N"] = [int(_fn.get(int(m), 0)) for m in fact_m["Mois"]]
                fact_m["Factures N-1"] = [int(_fn1.get(int(m), 0)) for m in fact_m["Mois"]]
                fig_fm = px.bar(
                    fact_m.melt(
                        id_vars=["Mois", "Mois Nom"],
                        value_vars=["Factures N-1", "Factures N"],
                        var_name="Période",
                        value_name="Factures",
                    ),
                    x="Mois Nom",
                    y="Factures",
                    color="Période",
                    barmode="group",
                    color_discrete_map={"Factures N-1": "#94A3B8", "Factures N": "#1D4ED8"},
                    title=f"Factures mensuelles {meta['short']} — {edc_yr} vs {edc_yr - 1} (date à date)",
                )
                fig_fm.update_layout(
                    height=380,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    margin=dict(l=16, r=16, t=52, b=16),
                )
                st.plotly_chart(fig_fm, use_container_width=True)

        # ══ SECTION 3 · RÉSEAU DES ÉTABLISSEMENTS ══════════════════
        section("3 · Réseau des établissements")
        col_r1, col_r2 = st.columns([3, 2])
        with col_r1:
            top10 = mag_net.head(10).sort_values("CA N")
            fig_top = px.bar(
                top10,
                x="CA N",
                y="Magasin",
                orientation="h",
                title=f"Top 10 établissements — {meta['short']} — {edc_yr}",
                color="CA N",
                color_continuous_scale=["#1D4ED8", "#3B82F6", "#60A5FA"],
                text_auto=".0f",
            )
            fig_top.update_layout(height=400, yaxis=dict(autorange="reversed"))
            fig_top.update_traces(textposition="outside")
            st.plotly_chart(fig_top, use_container_width=True)
        with col_r2:
            st.markdown(f"#### Concentration du réseau ({edc_yr})")
            if n_actifs > 0:
                _top1_p = float(mag_net["Poids net %"].iloc[0])
                _top3_p = float(mag_net["Poids net %"].head(3).sum())
                st.markdown(
                    f"- **Top 1** : {_top1_p:.1f} % du CA réseau\n"
                    f"- **Top 3** : {_top3_p:.1f} % du CA réseau\n"
                    f"- **Établissements actifs** : {n_actifs}\n"
                    f"- **CA moyen / établissement** : {mag_net_tot / n_actifs:,.0f} TND"
                )
                if _top3_p > 50:
                    st.info("⚠️ Concentration forte : plus de la moitié du CA repose sur 3 établissements.")
            else:
                st.markdown("- Aucun établissement actif sur la période sélectionnée.")
        # Pareto — cumul du CA par établissement (remplace le donut)
        if mag_net_tot > 0 and len(mag_net) > 0:
            par = mag_net.head(15)
            fig_par = go.Figure()
            fig_par.add_trace(
                go.Bar(
                    x=par["Magasin"],
                    y=par["CA N"],
                    name="CA",
                    marker_color=["#1D4ED8" if i < 3 else "#93C5FD" for i in range(len(par))],
                    text=[f"{v / 1e3:.1f}k" for v in par["CA N"]],
                    textposition="outside",
                )
            )
            fig_par.add_trace(
                go.Scatter(
                    x=par["Magasin"],
                    y=par["Poids net cumulé %"],
                    name="Cumul %",
                    yaxis="y2",
                    mode="lines+markers",
                    line=dict(color="#F59E0B", width=2),
                    marker=dict(size=8),
                )
            )
            fig_par.update_layout(
                title=f"Concentration du CA par établissement {meta['short']} — top {len(par)} (Pareto)",
                yaxis=dict(title="CA (TND)"),
                yaxis2=dict(
                    title="% cumulé",
                    overlaying="y",
                    side="right",
                    range=[0, 105],
                    showgrid=False,
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                height=430,
                template="plotly_white",
                hovermode="x unified",
            )
            st.plotly_chart(fig_par, use_container_width=True)
        else:
            st.info("Aucun CA réseau à représenter pour le périmètre sélectionné.")

        # Mouvements N vs N-1 (hausses / baisses en valeur)
        var_src = mag_net[(mag_net["CA N"] > 0) & (mag_net["CA N-1"] > 0)].copy()
        if len(var_src) > 0:
            var_src["Abs"] = var_src["Évolution %"].abs()
            var_show = pd.concat(
                [var_src.nlargest(8, "Abs"), var_src.nsmallest(8, "Abs")]
            ).drop_duplicates(subset="Magasin")
            st.plotly_chart(
                chart_variation_bar(
                    var_show,
                    "Magasin",
                    "Évolution %",
                    f"Mouvements de CA par établissement {meta['short']} — {edc_yr} vs {edc_yr - 1} (date à date)",
                ),
                use_container_width=True,
            )
        else:
            st.info(
                f"Pas de base {edc_yr - 1} comparable établissement par établissement "
                "— voir les nouveaux et sortants ci-dessous."
            )

        with st.expander("\U0001f4cb Tableau complet des établissements"):
            display_df = etab.rename(
                columns={"CA N": f"CA {edc_yr}", "CA N-1": f"CA {edc_yr - 1}", "Nb": "Nb factures"}
            )
            display_df = display_df[
                ["Magasin", "Statut", f"CA {edc_yr}", f"CA {edc_yr - 1}",
                 "Évolution %", "Nb factures", "Panier moyen", "Poids %", "Poids cumulé %"]
            ]
            st.dataframe(
                display_df.style.format(
                    {
                        f"CA {edc_yr}": "{:,.0f}",
                        f"CA {edc_yr - 1}": "{:,.0f}",
                        "Évolution %": "{:+.1f}%",
                        "Panier moyen": "{:,.0f}",
                        "Poids %": "{:.1f}%",
                        "Poids cumulé %": "{:.1f}%",
                    },
                    na_rep="—",
                ),
                use_container_width=True,
                height=440,
            )

        mvn, mvs = st.columns(2)
        with mvn:
            _news = etab[etab["Statut"].str.contains("Nouveau", na=False)]["Magasin"].tolist()
            st.markdown(f"**\U0001f195 Nouveaux établissements** ({len(_news)})")
            if _news:
                st.markdown("\n".join(f"- {m}" for m in _news[:8]))
                if len(_news) > 8:
                    st.caption(f"+ {len(_news) - 8} autres — voir tableau complet")
            else:
                st.info("Aucun nouvel établissement sur la période.")
        with mvs:
            _sors = etab[etab["Statut"].str.contains("Sorti", na=False)]["Magasin"].tolist()
            st.markdown(f"**\U0001f6aa Sans activité sur la période** ({len(_sors)})")
            if _sors:
                st.markdown("\n".join(f"- {m}" for m in _sors[:8]))
                if len(_sors) > 8:
                    st.caption(f"+ {len(_sors) - 8} autres — voir tableau complet")
            else:
                st.info("Aucun établissement sorti vs la période N-1.")

        # ══ SECTION 4 · DURÉE D'ÉCHÉANCE ════════════════════════════
        section("4 · Durée d'échéance")
        ech = pd.DataFrame()
        _col_ech = next((c for c in edc.columns if c.startswith("Nbr_Mois_Ech")), None)
        if _col_ech and len(df_edc_n) > 0:
            ech = (
                df_edc_n.groupby(_col_ech)
                .agg(CA=("Montant TTC", "sum"), Nb=("Montant TTC", "count"))
                .reset_index()
                .rename(columns={_col_ech: "Nbr_Mois_Echance"})
            )
        if len(ech) > 0:
            ech["Nbr_Mois_Echance"] = (
                pd.to_numeric(ech["Nbr_Mois_Echance"], errors="coerce").fillna(0).astype(int)
            )
            ech = ech.groupby("Nbr_Mois_Echance", as_index=False)[["CA", "Nb"]].sum()
            ech["Part %"] = (ech["CA"] / ech["CA"].sum() * 100).round(1)
            ech["Label"] = ech["Part %"].apply(lambda p: f"{p}%")
            ech = ech.sort_values("Nbr_Mois_Echance")

            # Garde-fou : distribution monomodale (ex. Sûreté ≈ 100 % à « 0 mois »)
            _nb_tot_ech = float(ech["Nb"].sum())
            _zero_share = (
                float(ech.loc[ech["Nbr_Mois_Echance"] == 0, "Nb"].sum()) / _nb_tot_ech
                if _nb_tot_ech > 0 else 0.0
            )
            if _zero_share >= 0.98:
                st.caption(
                    f"ℹ️ Durée d'échéance non exploitable sur ce périmètre : "
                    f"{_zero_share:.0%} des dossiers à « 0 mois ». "
                    "Lecture orientée sur les sections 1-3 et la synthèse."
                )
                ech = pd.DataFrame()  # neutralise aussi l'insight « durée dominante »
            else:
                col_ec1, col_ec2 = st.columns([2, 1])
                with col_ec1:
                    fig_ech = chart_bar(
                        ech,
                        "Nbr_Mois_Echance",
                        "CA",
                        f"Répartition par durée d'échéance — {meta['short']} — {edc_yr}",
                        C["blue"],
                    )
                    fig_ech.update_xaxes(title="Durée (mois)", type="category")
                    fig_ech.update_yaxes(title="CA TTC (TND)")
                    fig_ech.update_traces(text=ech["Label"].tolist(), textposition="outside")
                    st.plotly_chart(fig_ech, use_container_width=True)
                with col_ec2:
                    st.plotly_chart(
                        chart_pie(
                            ech["CA"].tolist(),
                            [f"{int(m)} mois" for m in ech["Nbr_Mois_Echance"]],
                            "Part par échéance",
                        ),
                        use_container_width=True,
                    )
        else:
            st.info("Aucune donnée de durée d'échéance sur la période sélectionnée (colonne absente ou vide).")

        # ══ SECTION 5 · SYNTHÈSE & RECOMMANDATIONS ══════════════════
        section("5 · Synthèse & recommandations")
        insights, reco = [], []

        if ca_e_n1 > 0:
            insights.append(
                f"- **Tendance** : CA {edc_yr} à {ca_e_n:,.0f} TND vs {ca_e_n1:,.0f} TND en {edc_yr - 1} "
                f"sur la période comparée (**{ev_edc:+.1f} %**)."
            )
        elif ca_e_n > 0:
            insights.append(
                f"- **Tendance** : activité de {ca_e_n:,.0f} TND sans base comparable en {edc_yr - 1}."
            )
        else:
            insights.append("- **Tendance** : aucun CA sur la période sélectionnée.")
        insights.append(
            f"- **Volume** : {nb_f_edc} factures vs {nb_f_n1} en {edc_yr - 1} "
            f"(panier moyen {panier_e:,.0f} TND vs {panier_n1:,.0f} TND)."
        )
        if mag_net_tot > 0 and n_actifs > 0:
            _lead = mag_net.iloc[0]
            insights.append(
                f"- **Réseau** : {n_actifs} établissements actifs, {n_nouveaux} nouveau(x), "
                f"{n_sortis} sorti(s) ; leader **{_lead['Magasin']}** = {float(_lead['CA N']):,.0f} TND "
                f"({float(_lead['Poids net %']):.1f} % du CA réseau)."
            )
            insights.append(
                f"- **Concentration** : top 3 = {float(mag_net['Poids net %'].head(3).sum()):.1f} % du CA réseau."
            )
        if not comp.empty:
            _bm = comp.loc[comp["CA N"].idxmax()]
            insights.append(
                f"- **Saisonnalité** : meilleur mois {edc_yr} = **{_bm['Mois Nom']}** "
                f"({float(_bm['CA N']):,.0f} TND)."
            )
        if mois_sel and ca_e_annee > ca_e_n + 1:
            insights.append(
                f"- **Périmètre** : analyse limitée aux mois sélectionnés — "
                f"CA {edc_yr} toutes périodes = {ca_e_annee:,.0f} TND."
            )
        if len(ech) > 0:
            _dom = ech.loc[ech["CA"].idxmax()]
            insights.append(
                f"- **Échéance** : durée dominante **{int(_dom['Nbr_Mois_Echance'])} mois** "
                f"({float(_dom['CA']):,.0f} TND, {float(_dom['Part %']):.1f} % du CA période)."
            )

        if ca_e_n1 > 0 and ev_edc < 0:
            reco.append(
                "\U0001f3af **Relancer la performance** : la base comparable est établie — "
                "cibler les établissements en repli (variation bar ci-dessus)."
            )
        elif ca_e_n1 > 0:
            reco.append(
                "\U0001f3af **Capitaliser** : la période progresse au-dessus de N-1 — "
                "sécuriser la montée en charge des établissements leaders."
            )
        else:
            reco.append(
                "\U0001f3af **Structurer la mesure** : sans base N-1 exploitable sur ce périmètre, "
                "élargir les mois ou fiabiliser l'historique."
            )
        if n_actifs > 0 and float(mag_net["Poids net %"].head(3).sum()) > 50:
            reco.append(
                "\U0001f517 **Réduire la concentration** : le top 3 pèse plus de 50 % du CA "
                "réseau — développer le second cercle d'établissements."
            )
        if n_nouveaux == 0 and n_actifs > 0:
            reco.append(
                "\U0001f680 **Dynamiser le réseau** : aucun nouvel établissement sur la période — "
                "relancer les ouvertures / conventions en préparation."
            )
        if n_sortis > 0:
            reco.append(
                f"\U0001f501 **Auditer les sorties** : {n_sortis} établissement(s) sans activité vs "
                f"{edc_yr - 1} — comprendre les causes avant clôture."
            )
        if n_en_baisse > 0:
            reco.append(
                f"\U0001f4c8 **Plan d'action baisses** : accompagner les {n_en_baisse} "
                "établissements en repli (note mensuelle)."
            )
        reco.append(
            "\U0001f6e5\ufe0f **Prochaine lecture** : rejouer cette page à J+5 du clos de "
            f"{MOIS.get(mois_dispo_n[-1], '—') if mois_dispo_n else '—'} {edc_yr} pour verrouiller "
            "l'écart date à date avant diffusion."
        )

        # — Lecture comptes mutuelles : taux de récurrence + recos dédiées ──
        if meta["parent"] is not None:
            _idc = "N° Client" if "N° Client" in edc.columns else ("N°" if "N°" in edc.columns else None)
            _taux_recur = None
            if _idc is not None:
                _ids_n = set(df_edc_n[_idc].dropna().astype(str))
                _ids_n1 = set(df_edc_n1[_idc].dropna().astype(str))
                if _ids_n1:
                    _taux_recur = len(_ids_n & _ids_n1) * 100.0 / len(_ids_n1)
            if _taux_recur is not None:
                insights.append(
                    f"- **Fidélisation** : taux de récurrence de **{_taux_recur:.1f} %** — "
                    f"adhérents actifs en {edc_yr - 1} également actifs sur la période {edc_yr}."
                )
                if _taux_recur < 10:
                    reco.append(
                        f"🎯 **Relance adhérents** : taux de récurrence {_taux_recur:.1f} % — "
                        f"cibler les adhérents actifs en {edc_yr - 1} sans dossier en {edc_yr} "
                        "(relance SMS / appel, offre de réassurance du réseau)."
                    )
            reco.extend(f"🎯 {r}" for r in meta["spec_recos"])

        col_a1, col_a2 = st.columns([3, 2])
        with col_a1:
            st.markdown("### Constats clés")
            st.markdown("\n".join(insights))
        with col_a2:
            st.markdown("### Recommandations")
            st.markdown("\n".join(reco))
    else:
        st.warning(f"\u26a0\ufe0f Aucune donnée {meta['short']} disponible.")


# ══════════════════════════════════════════════════════════════
# TAB 5 — CONVENTIONS SMG (suivi, DSO, alertes, GPO)
# ══════════════════════════════════════════════════════════════
with tabs[5]:

    st.markdown("Conventions encours")
    st.caption("Suivi des projets de convention — de la prospection a la finalisation.")

    if not df_prospection.empty:
        st.markdown("### Pipeline Prospection")
        st.caption(f"{len(df_prospection)} prospects suivis dans le pipeline")

        non_dem = len(df_prospection[df_prospection["AVANCEMENT2"] == "Non démarré"])
        en_cours = len(df_prospection[df_prospection["AVANCEMENT2"] == "En cours"])
        cloture = len(df_prospection[df_prospection["AVANCEMENT2"] == "Clôturé"])

        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("Total prospects", len(df_prospection))
        pc2.metric("Non démarré", non_dem)
        pc3.metric("En cours", en_cours)
        pc4.metric("Clôturé", cloture)

        import plotly.express as px
        df_pipe = pd.DataFrame({
            "Étape": ["Non démarré", "En cours", "Clôturé"],
            "Prospects": [non_dem, en_cours, cloture]
        })
        fig_bar = px.bar(df_pipe, y="Étape", x="Prospects", orientation="h",
            title="Répartition du pipeline",
            color="Étape",
            color_discrete_map={"Non démarré": "#94A3B8", "En cours": "#1D4ED8", "Clôturé": "#059669"},
            text="Prospects")
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10),
            showlegend=False, xaxis_visible=False, yaxis_title=None)
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("#### Détails prospects")
        cols_prosp = ["conventions en cours", "AVANCEMENT2", "contacts", "EMAIL", "RANKING"]
        cols_exist = [c for c in cols_prosp if c in df_prospection.columns]
        st.dataframe(df_prospection[cols_exist], use_container_width=True)

        st.divider()

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    csv_path = os.path.join(data_dir, "conventions_signees.csv")
    if not os.path.exists(csv_path):
        st.info("Fichier data/conventions_signees.csv introuvable.")
    else:
        df_sig = pd.read_csv(csv_path, sep=";")
        if df_sig.empty or "code" not in df_sig.columns:
            st.info("CSV vide ou mal formatte.")
        else:
            cf1, cf2 = st.columns([1, 2])
            with cf1:
                sf = st.selectbox("Filtrer par statut",
                    ["Tous","Prospection","Negociation","En cours","Finalisation","Signe","Finalise","Refuse","Archive"])
            with cf2:
                q = st.text_input("Rechercher un client", "")

            mask = pd.Series(True, index=df_sig.index)
            if sf != "Tous":
                mask &= df_sig["statut"].fillna("").str.strip() == sf
            if q.strip():
                mask &= df_sig["client"].fillna("").str.lower().str.contains(q.strip().lower())

            df_filt = df_sig[mask].copy()
            today = pd.Timestamp.now()

            rows_data = []
            tot_j = 0
            stats = {}
            for _, r in df_filt.iterrows():
                d = pd.NaT
                f = pd.NaT
                if pd.notna(r.get("date_debut_prospection","")):
                    d = pd.Timestamp(r["date_debut_prospection"])
                if pd.notna(r.get("date_signature","")):
                    f = pd.Timestamp(r["date_signature"])
                dur = (f - d).days if pd.notna(f) and pd.notna(d) else ((today - d).days if pd.notna(d) else 0)
                tot_j += dur
                s = str(r.get("statut","")).strip()
                stats[s] = stats.get(s, 0) + 1
                rows_data.append({
                    "Client": r["client"], "Statut": s,
                    "Debut": str(d.date()) if pd.notna(d) else "-",
                    "Delai (j)": dur,
                    "Modifs": int(r.get("nb_modifications",0)),
                    "Notes": str(r.get("notes",""))
                })

            if len(rows_data) > 0:
                dm = round(tot_j/len(rows_data), 1)
                ss = " | ".join([f"{s}: {c}" for s,c in sorted(stats.items())])
                c1, c2, c3 = st.columns(3)
                c1.metric("Projets", len(rows_data))
                c2.metric("Delai moyen", f"{dm} jrs")
                c3.caption(ss)

            st.markdown("#### Edition")
            df_edit = df_filt.copy()
            df_edit["_idx"] = df_filt.index
            df_edit["Client"] = df_edit["client"]
            df_edit["Statut"] = df_edit["statut"]
            df_edit["Debut"] = df_edit["date_debut_prospection"].fillna("-")
            df_edit["Delai (j)"] = 0
            df_edit["Modifs"] = df_edit["nb_modifications"].fillna(0).astype(int)
            df_edit["Archiver"] = False
            df_edit["Notes"] = df_edit["notes"]
            for i in df_edit.index:
                r = df_edit.loc[i]
                d = pd.NaT; f = pd.NaT
                if pd.notna(r.get("date_debut_prospection","")):
                    d = pd.Timestamp(r["date_debut_prospection"])
                if pd.notna(r.get("date_signature","")):
                    f = pd.Timestamp(r["date_signature"])
                dur = (f - d).days if pd.notna(f) and pd.notna(d) else ((today - d).days if pd.notna(d) else 0)
                df_edit.at[i, "Delai (j)"] = dur

            edited = st.data_editor(
                df_edit[["Client","Statut","Debut","Delai (j)","Modifs","Notes","Archiver","_idx"]],
                column_config={
                    "Client": st.column_config.TextColumn("Client", disabled=True),
                    "Statut": st.column_config.TextColumn("Statut", help="Valeurs: Prospection, Negociation, En cours, Finalisation, Signe, Finalise, Refuse"),
                    "Debut": st.column_config.TextColumn("Debut", disabled=True),
                    "Delai (j)": st.column_config.NumberColumn("Delai (j)", disabled=True),
                    "Modifs": st.column_config.NumberColumn("Modifs", disabled=True),
                    "Notes": st.column_config.TextColumn("Notes", width="large"),
                    "Archiver": st.column_config.CheckboxColumn("Archiver"),
                    "_idx": st.column_config.NumberColumn("_idx", disabled=True, width="small")
                },
                use_container_width=True, hide_index=True, key="editor_conv"
            )

            if edited is not None and "_idx" in edited.columns:
                ca, cb = st.columns([1, 3])
                with ca:
                    if st.button("Sauvegarder les modifications"):
                        modifs = 0
                        for _, row in edited.iterrows():
                            oidx = int(row["_idx"])
                            if oidx in df_sig.index:
                                code = str(df_sig.at[oidx, "code"]).strip()
                                if conv.update_convention(
                                        code, statut=str(row.get("Statut", "")).strip(),
                                        notes=str(row.get("Notes", ""))):
                                    modifs += 1
                        if modifs:
                            push_csv_to_github("data/conventions_signees.csv", "update(data): modifications conventions [auto]")
                            st.success("Modifications sauvegardees et synchronisees sur GitHub !")
                            st.rerun()
                        else:
                            st.info("Aucune modification.")

                with cb:
                    to_arch = [int(r["_idx"]) for _, r in edited.iterrows() if r.get("Archiver", False)]
                    if to_arch:
                        st.warning(f"{len(to_arch)} projet(s) a archiver")
                        if st.button("Confirmer l'archivage"):
                            for idx in to_arch:
                                if idx in df_sig.index:
                                    conv.update_convention(
                                        str(df_sig.at[idx, "code"]).strip(), statut="Archive")
                            push_csv_to_github("data/conventions_signees.csv", "update(data): archivage convention [auto]")
                            st.success(f"{len(to_arch)} projet(s) archive(s) et synchronise(s) sur GitHub !")
                            st.rerun()

            if stats:
                st.markdown("#### Repartition par statut")
                import plotly.express as px
                df_chart = pd.DataFrame({"Statut": list(stats.keys()), "Nombre": list(stats.values())})
                colors = {"Prospection":"#F59E0B","Negociation":"#F97316","En cours":"#3B82F6",
                          "Finalisation":"#8B5CF6","Signe":"#10B981","Finalise":"#059669","Refuse":"#DC2626"}
                fig = px.bar(df_chart, x="Statut", y="Nombre", color="Statut",
                             color_discrete_map=colors, text="Nombre", height=280)
                fig.update_traces(textposition="outside")
                fig.update_layout(margin=dict(l=10,r=10,t=10,b=10))
                st.plotly_chart(fig, use_container_width=True, key="chart_statut")

            st.markdown("#### Ajouter un projet")
            with st.expander("Nouvelle convention"):
                with st.form("conv_form"):
                    x1, x2 = st.columns(2)
                    with x1:
                        nc = st.text_input("Client")
                        ns = st.selectbox("Statut",
                            ["Prospection","Negociation","En cours","Finalisation","Signe","Finalise","Refuse"])
                    with x2:
                        nd = st.date_input("Debut prospection", value=today)
                        nv = st.text_input("Scenario", "01-Prive avec Amicale")
                    if st.form_submit_button("Ajouter"):
                        new_code = nc.upper().replace(" ","_")[:20] if nc else "NOUVEAU"
                        conv.register_convention(new_code, nc, scenario=nv, garantie="", statut=ns,
                                                 date_debut_prospection=str(nd))
                        push_csv_to_github("data/conventions_signees.csv", "update(data): nouvelle convention [auto]")
                        st.success(f"Ajoute : {nc}")
                        st.rerun()

with tabs[6]:
    if df_crm is not None and len(df_crm) > 0:
        ca_pot_total = df_crm["CA potentiel"].sum()
        ca_real_total = df_crm["CA realise"].sum()
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total prospects", len(df_crm))
        en_cours = len(df_crm[df_crm["Statut pipeline"]=="En cours"])
        k2.metric("En cours", en_cours)
        cloture = len(df_crm[df_crm["Statut pipeline"]=="Cloture"])
        k3.metric("Cloturees", cloture)
        k4.metric("CA potentiel", f"{ca_pot_total:,.0f}")
        k5.metric("CA realise", f"{ca_real_total:,.0f}",
                  delta=f"{((ca_real_total/ca_pot_total*100) if ca_pot_total > 0 else 0):.0f}% taux real.")

        col1, col2, col3 = st.columns(3)
        with col1:
            pipe = df_crm["Statut pipeline"].value_counts().reset_index()
            pipe.columns = ["Statut", "Nb"]
            fig_pipe = px.bar(pipe, x="Statut", y="Nb", color="Statut",
                              title="Pipeline Commercial", text_auto=True, height=300)
            fig_pipe.update_layout(showlegend=False)
            st.plotly_chart(fig_pipe, use_container_width=True)
        with col2:
            prio = df_crm["Priorite relance"].value_counts().reset_index()
            prio.columns = ["Priorite", "Nb"]
            fig_prio = px.pie(prio, values="Nb", names="Priorite",
                              title="Priorites Relance", height=300, hole=0.4)
            st.plotly_chart(fig_prio, use_container_width=True)
        with col3:
            sect = df_crm["Secteur"].value_counts().reset_index()
            sect.columns = ["Secteur", "Nb"]
            fig_sect = px.pie(sect, values="Nb", names="Secteur",
                              title="Secteurs", height=300, hole=0.4,
                              color_discrete_sequence=["#059669", "#1D4ED8", "#D97706"])
            st.plotly_chart(fig_sect, use_container_width=True)

        st.markdown("<div class='sec-hdr'>Prospects</div>", unsafe_allow_html=True)
        cols_show = [
            "Nom entreprise", "Statut pipeline", "Priorite relance",
            "Secteur", "CA potentiel", "CA realise",
            "Responsable commercial", "Date derniere activite"
        ]
        cols_ok = [c for c in cols_show if c in df_crm.columns]
        df_disp = df_crm[cols_ok].head(20).reset_index(drop=True)
        ev = st.dataframe(df_disp, use_container_width=True, height=450,
                          column_config={c: st.column_config.NumberColumn(format="%d")
                                         for c in ["CA potentiel", "CA realise"]
                                         if c in df_disp.columns},
                          on_select="rerun", selection_mode="single-row")
        sel = ev.selection.rows if hasattr(ev, 'selection') else []
        if sel:
            idx = sel[0]
            client = df_crm.loc[df_disp.index[idx]]
            nm = str(client.get("Nom entreprise", ""))
            with st.container():
                st.markdown(f"<div style='background:#f0f2f6;padding:1.2rem 1.5rem;border-radius:12px;margin-top:0.5rem'>"
                            f"<h3 style='margin:0 0 1rem 0'>{nm}</h3>", unsafe_allow_html=True)
                cx = st.columns(4)
                cx[0].markdown(f"**Contact**<br>{client.get('Contact', '')}", unsafe_allow_html=True)
                cx[1].markdown(f"**Telephone**<br>{client.get('Telephone', '')}", unsafe_allow_html=True)
                cx[2].markdown(f"**Secteur**<br>{client.get('Secteur', '')}", unsafe_allow_html=True)
                ca_p = client.get("CA potentiel", 0)
                ca_r = client.get("CA realise", 0)
                cx[3].markdown(f"**CA potentiel**<br>{ca_p:,.0f}  \n**CA realise**<br>{ca_r:,.0f}", unsafe_allow_html=True)
                cmt = str(client.get("Commentaire", ""))
                if cmt and cmt != "nan" and cmt.strip():
                    st.markdown(f"**Commentaire :** {cmt}")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("CRM desactive. Verifiez TDC2.xlsx et crm.py")

with tabs[7]:
    st.markdown("### \U0001f6a8 Alertes Tendances")
    try:
        with st.spinner("Analyse des tendances..."):
            alerts = _cached_scan_all(df_vc, df_edc, df_conv, code_df)
            if "Nom" in df_vc_filt.columns:
                _df_ytd_n = df_vc_filt[df_vc_filt["Année"] == annee_sel].copy()
                _df_ytd_n1 = df_vc_filt[df_vc_filt["Année"] == annee_sel - 1].copy()
                if mois_sel and len(mois_sel) > 0:
                    _df_ytd_n = _df_ytd_n[_df_ytd_n["Mois"].isin(mois_sel)]
                    _df_ytd_n1 = _df_ytd_n1[_df_ytd_n1["Mois"].isin(mois_sel)]
                if "Jour" in _df_ytd_n.columns and not _df_ytd_n.empty:
                    _conv_jours = _df_ytd_n.groupby(["Nom", "Mois"])["Jour"].apply(max).to_dict()
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
                for a in alerts.get("convention_alerts", []):
                    nom = str(a.get("nom", "")).strip().upper()
                    if not nom or nom not in _ytd_index:
                        continue
                    orig = _ytd_orig[nom]
                    dn = _df_ytd_n[_df_ytd_n["Nom"] == orig]
                    dn1 = _df_ytd_n1[_df_ytd_n1["Nom"] == orig]
                    if dn.empty:
                        continue
                    ca_n = float(dn["Montant TTC"].sum())
                    ca_n1 = 0.0
                    for m, max_jour in _ytd_index[nom].items():
                        ca_n1 += float(dn1[(dn1["Mois"] == m) & (dn1["Jour"] <= int(max_jour))]["Montant TTC"].sum())
                    evo = evol_pct(ca_n, ca_n1)
                    a["metrics"]["ytd_change_pct"] = evo
            render_alert_panel(alerts)
    except Exception as e:
        st.warning(f"Analyse des tendances indisponible: {e}")

    # ── Détection d'outliers factures ────────────────────────────
    section("Anomalies — Factures outliers")
    _out = df_vc[df_vc["Année"] == annee_sel].copy()
    if not _out.empty and "Montant TTC" in _out.columns and "Magasin" in _out.columns:
        _out_stats = _out.groupby("Magasin")["Montant TTC"].agg(["mean", "std", "count"]).reset_index()
        _out_stats.columns = ["Magasin", "Moyenne", "Ecart_type", "Nb"]
        _out_stats = _out_stats[_out_stats["Ecart_type"] > 0]
        if not _out_stats.empty:
            _out_merged = _out.merge(_out_stats[["Magasin", "Moyenne", "Ecart_type"]], on="Magasin")
            _out_merged["Z_score"] = abs(_out_merged["Montant TTC"] - _out_merged["Moyenne"]) / _out_merged["Ecart_type"]
            _outliers = _out_merged[_out_merged["Z_score"] > 3].copy()
            _outliers["Écart %"] = ((_outliers["Montant TTC"] - _outliers["Moyenne"]) / _outliers["Moyenne"] * 100).round(1)
            if len(_outliers) > 0:
                st.caption(f"{len(_outliers)} factures anormales détectées (|Z|>3, σ par magasin)")
                _od = _outliers.sort_values("Z_score", ascending=False).head(20)
                _od["Montant TTC"] = _od["Montant TTC"].round(0)
                _od["Moyenne"] = _od["Moyenne"].round(0)
                cols_o = [c for c in ["Nom", "Magasin", "Montant TTC", "Moyenne", "Écart %", "Date"] if c in _od.columns]
                st.dataframe(_od[cols_o], use_container_width=True, height=300,
                             column_config={"Montant TTC": st.column_config.NumberColumn(format="%d"),
                                            "Moyenne": st.column_config.NumberColumn(format="%d")})
            else:
                st.caption("Aucune anomalie détectée sur la période.")
        else:
            st.caption("Pas assez de données par magasin.")
    else:
        st.caption("Données insuffisantes.")

# ══════════════════════════════════════════════════════════════
# TAB 8 — ARCHIVE RAPPORTS
# ══════════════════════════════════════════════════════════════
with tabs[8]:
    st.markdown("### \U0001f4c2 Archive des Rapports Mensuels")
    archive_path = Path(__file__).parent / ".cache_monthly" / "report_archive.json"

    if not archive_path.exists():
        st.info("Aucun rapport archive pour l'instant. Utilisez `python monthly_report.py` pour generer un rapport.")
    else:
        try:
            archive = json.loads(archive_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            archive = []

        if not archive:
            st.info("Archive vide.")
        else:
            # Navigation par mois/annee
            periodes = sorted(set((e["annee"], e["mois"]) for e in archive), reverse=True)
            col1, col2 = st.columns([1, 3])
            with col1:
                selected = st.selectbox(
                    "Periode",
                    options=[f"{MOIS.get(m, m)} {a}" for a, m in periodes],
                    index=0,
                )
            with col2:
                st.markdown(f"**{len(archive)} rapport(s)** archive(s)")

            # Filtrer
            selected_entries = [e for e in archive
                                if f"{MOIS.get(e['mois'], e['mois'])} {e['annee']}" == selected]

            for entry in reversed(selected_entries):
                filename = entry.get("filename", "?")
                ts = entry.get("timestamp", "")[:16].replace("T", " ")
                kpi = entry.get("kpi", {})
                exec_summary = entry.get("exec_summary")

                with st.container(border=True):
                    cols = st.columns([3, 1, 1])
                    with cols[0]:
                        st.markdown(f"**{filename}**  \n"
                                    f"Genere le {ts}")
                    with cols[1]:
                        st.metric("CA Total", f"{kpi.get('ca_total',0):,.0f}")
                    with cols[2]:
                        var = kpi.get("var_total", 0)
                        st.metric("Variation", fmt_pct(var),
                                  delta_color=color_delta(var))

                    # Exec summary
                    if exec_summary and exec_summary.get("tendance_globale"):
                        tg = exec_summary["tendance_globale"]
                        st.markdown(f"**Tendance :** {tg.get('texte', '')}  \n"
                                    f"Direction: {tg.get('direction','?').upper()} — "
                                    f"Intensite: {tg.get('intensite','?')}")
                        points = exec_summary.get("points_cles", [])
                        if points:
                            for p in points:
                                st.markdown(f"- {p}")

                    # Actions
                    report_dir = Path.home() / "Downloads" / "rapport_mensuel"
                    html_file = report_dir / filename
                    if html_file.exists():
                        with open(html_file, "r", encoding="utf-8") as fh:
                            html_content = fh.read()
                        st.download_button(
                            label="\U0001f4e5 Telecharger le rapport HTML",
                            data=html_content,
                            file_name=filename,
                            mime="text/html",
                            key=f"dl_{filename}",
                        )
                    else:
                        st.caption(f"Fichier non trouve: {html_file.name}")

                    # Lien pour ouvrir
                    try:
                        _rel = html_file.relative_to(Path(__file__).parent)
                        st.markdown(f"[Ouvrir le rapport](./{_rel})")
                    except ValueError:
                        pass

# ── Footer ────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Dashboard B2B SMG — MG & BATAM  ·  "
    f"Source : VC.CONV. Business Central  ·  "
    f"Genere automatiquement  ·  "
    f"Filtres actifs: Annee {annee_sel} "
    + (f"| Mois: {', '.join([MOIS.get(m, str(m)) for m in mois_sel])} " if mois_sel else "")
    + (f"| Conv. {conv_sel}" if conv_sel != "Tous" else "")
    + (f"| Seuil inactivite: {seuil_inactif}j" if seuil_inactif != SEUILS["inactivite_jours"] else "")
)
