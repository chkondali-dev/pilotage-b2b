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
import logging
from io import BytesIO
import base64
from datetime import datetime, timedelta
from pathlib import Path
from trend_alert_panel import render_alert_panel

from data.config import (
    C, MOIS, LOGO_MG_URL, LOGO_BATAM_URL, SEUILS, JALONS_STATUTS,
    STATUTS_CONVENTION, annees_selecteur_principal, annees_selecteur_rapport,
)
from data.loader import load_all_data
from data.transforms import prepare_data, enrich_prospection, PROSP_ETAPES, ajoute_crm
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
    alertes_achats_repetes,
)
from charts.factory import (
    chart_bar, chart_grouped_bar, chart_line_compare, chart_variation_bar,
    chart_bridge, chart_risk_table, chart_gauge, chart_pie, chart_stacked_bar,
)
from ui.components import inject_css, hero, section, badge, rank_card, kpi_card
from utils.github import push_csv_to_github, file_sha
import business.conventions as conv

from ui.tabs.context import TabCtx
from ui.tabs.tab0_executive import render as _render_tab0
from ui.tabs.tab1_tendances import render as _render_tab1
from ui.tabs.tab2_conventions import render as _render_tab2
from ui.tabs.tab3_magasins import render as _render_tab3
from ui.tabs.tab4_lens import render as _render_tab4
from ui.tabs.tab5_conventions import render as _render_tab5
from ui.tabs.tab6_crm import render as _render_tab6
from ui.tabs.tab7_alertes import render as _render_tab7
from ui.tabs.tab8_archive import render as _render_tab8
from ui.tabs.tab9_conformite import render as _render_tab9

import re
import unicodedata


logger = logging.getLogger(__name__)

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
    except Exception as _e:
        logger.warning("Logo MG indisponible : %s", _e)
with col_l2:
    try:
        st.image(LOGO_BATAM_URL, width=90)
    except Exception as _e:
        logger.warning("Logo BATAM indisponible : %s", _e)

# ── Chargement données (AVANT les filtres : le sélecteur Année est dérivé des données) ──
with st.spinner("Chargement des données…"):
    _raw = load_all_data()

df_vc, df_credit, df_edc, df_conv, code_df, df_credit_part, df_cube_mag, df_prospection, df_crm = prepare_data(_raw)
_raw_part = _raw.get("credit_particulier", pd.DataFrame())

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### \U0001f50d Filtres")
    # Années dérivées des données (Phase 1.1) : jamais figée, jamais de ValueError.
    _annees_data = set()
    for _df_flux in (df_vc, df_credit, df_credit_part):
        if "Année" in _df_flux.columns:
            _annees_data.update(int(a) for a in _df_flux["Année"].dropna().unique())
    annee_sel = st.selectbox(
        "Année",
        annees_selecteur_principal(_annees_data, datetime.now().year),
        index=0,
    )

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
            _rap_opts, _rap_idx = annees_selecteur_rapport(_annees_data, default_year)
            rapport_annee = st.selectbox("Annee", _rap_opts, index=_rap_idx)

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
                     "--no-email"],
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

REGISTRY_CSV_REL = "data/conventions_signees.csv"


def _registry_sha_now():
    """sha blob du registre local APRÈS une synchro réussie (nouvelle base)."""
    return file_sha(Path(__file__).parent / REGISTRY_CSV_REL)


def _sync_registre(commit_msg: str, msg_ok: str) -> bool:
    """Pousse le registre sur GitHub et affiche le statut RÉEL (Phase 1.2).

    « synchronisé » affiché uniquement si le push réussit ; sinon st.error avec
    la cause. La modification reste locale et l'intention est conservée dans
    st.session_state["sync_pending"] pour retenter (bouton en haut de l'onglet
    Conventions encours).
    """
    res = push_csv_to_github(
        REGISTRY_CSV_REL, commit_msg,
        base_sha=st.session_state.get("registry_base_sha"),
    )
    if res["ok"]:
        st.session_state.pop("sync_pending", None)
        st.session_state["registry_base_sha"] = _registry_sha_now()
        st.success(msg_ok)
        return True
    st.session_state["sync_pending"] = {
        "commit_msg": commit_msg, "status": res["status"], "detail": res["detail"]}
    st.error(f"GitHub non synchronisé ({res['status']}) : {res['detail']}")
    st.caption("Modifications conservées localement dans data/conventions_signees.csv "
               "— « Réessayer la synchronisation » en haut de l'onglet Conventions encours.")
    return False

# ===============================================================
# SECTION 8 - NAVIGATION (onglets extraits vers ui/tabs/)
# ===============================================================
# Chaque onglet est un module ui/tabs/<nom>.py exposant
# render(ctx: TabCtx). Seul l'onglet selectionne est rendu
# (rendu paresseux, Phase 2 : moins de calcul par rerun).
_TAB_ITEMS = [
    ('🏠 Vue Exécutive', _render_tab0),
    ('📈 CA & Tendances', _render_tab1),
    ('📋 Conventions', _render_tab2),
    ('🏪 Magasins', _render_tab3),
    ('🧭 Tous flux & Mutuelles', _render_tab4),
    ('📋 Conventions encours', _render_tab5),
    ('🤝 CRM', _render_tab6),
    ('🚨 Alertes Tendances', _render_tab7),
    ('📂 Archive Rapports', _render_tab8),
    ('🛡️ Conformité 40%', _render_tab9),
]
_TAB_LABELS = [lbl for lbl, _ in _TAB_ITEMS]


def _norm_label(value):
    """Libelle d'onglet normalise : sans emoji, sans accent."""
    text = unicodedata.normalize('NFKD', str(value))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


_TAB_INDEX = {_norm_label(lbl): i for i, (lbl, _) in enumerate(_TAB_ITEMS)}

_tab_sel = st.segmented_control(
    'Navigation',
    _TAB_LABELS,
    default=_TAB_LABELS[0],
    label_visibility='collapsed',
)
_tab_idx = _TAB_INDEX.get(_norm_label(_tab_sel), 0) if _tab_sel else 0

_tab_ctx = TabCtx(
    df_vc=df_vc,
    df_credit=df_credit,
    df_credit_part=df_credit_part,
    df_edc=df_edc,
    df_conv=df_conv,
    code_df=code_df,
    df_cube_mag=df_cube_mag,
    df_prospection=df_prospection,
    df_crm=df_crm,
    df_vc_filt=df_vc_filt,
    df_vc_scope=df_vc_scope,
    df_filt=df_filt,
    annee_sel=annee_sel,
    mois_sel=mois_sel,
    conv_sel=conv_sel,
    type_vente_sel=type_vente_sel,
    seuil_inactif=seuil_inactif,
    objectif_m=objectif_m,
    df_comp=df_comp,
    risk_mat=risk_mat,
    df_inactive=df_inactive,
    df_3m=df_3m,
    ca_n=ca_n,
    ca_n1=ca_n1,
    ev_nn1=ev_nn1,
    ca_n2=ca_n2,
    ev_n1n2=ev_n1n2,
    nb_actives=nb_actives,
    nb_inact=nb_inact,
    nb_total=nb_total,
    nb_declin_fort=nb_declin_fort,
    nb_inactif_cv=nb_inactif_cv,
    nb_croissance=nb_croissance,
    lens_labels=LENS_LABELS,
    base_dir=str(Path(__file__).parent),
)
_TAB_ITEMS[_tab_idx][1](_tab_ctx)


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
