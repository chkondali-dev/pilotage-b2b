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

from data.config import C, MOIS, LOGO_MG_URL, LOGO_BATAM_URL
from data.loader import load_all_data
from data.transforms import prepare_data
from metrics.kpi import (
    compare_years, compare_years_date_to_date, ca_sum_date_to_date,
    truncate_n1_date_to_date,
    evol_pct, convention_risk_matrix, inactive_conventions, get_rolling_3m,
)
from charts.factory import (
    chart_bar, chart_grouped_bar, chart_line_compare, chart_variation_bar,
    chart_waterfall, chart_risk_table, chart_gauge, chart_pie,
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

    # Filtre mois - default to current month
    current_month = datetime.now().month
    all_mois = list(range(1, 13))
    mois_sel = st.multiselect(
        "Mois",
        all_mois,
        default=[current_month],
        format_func=lambda x: MOIS.get(x, str(x))
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

# Mutuelle Personnel Sûreté Nationale — Prison & Rééducation (extrait du crédit conso)
df_mutuelle = (
    df_credit[df_credit["Nom"].str.contains("MUT PERS SURETE NLE PRISON", case=False, na=False)].copy()
    if not df_credit.empty and "Nom" in df_credit.columns
    else pd.DataFrame()
)

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

if mois_sel:
    df_vc_filt = df_vc_filt[df_vc_filt["Mois"].isin(mois_sel)]

# Convention filter (dépend de l'année)
_conv_options = (
    ["Tous"] + sorted(df_vc_filt["Nom"].dropna().unique().tolist())
    if "Nom" in df_vc.columns else ["Tous"]
)
with st.sidebar:
    conv_sel = st.selectbox("Convention", _conv_options)
    seuil_inactif = st.slider(
        "Seuil d'inactivite (jours)",
        min_value=15, max_value=180, value=60, step=15,
        help="Conventions sans facture depuis plus de N jours",
    )

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
    inac = inactive_conventions(df, seuil)
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

panier_min = df_filt["Montant TTC"].min() if len(df_filt) > 0 else 0
panier_max = df_filt["Montant TTC"].max() if len(df_filt) > 0 else 0
panier_moy  = df_filt["Montant TTC"].mean() if len(df_filt) > 0 else 0

_df_mois = df_vc_filt[df_vc_filt["Année"] == annee_sel].copy()
if mois_sel:
    _df_mois = _df_mois[_df_mois["Mois"].isin(mois_sel)]

min_mag = _df_mois.loc[_df_mois["Montant TTC"].idxmin(), "Nom"] if len(_df_mois) > 0 and "Nom" in _df_mois.columns else ""
max_mag = _df_mois.loc[_df_mois["Montant TTC"].idxmax(), "Nom"] if len(_df_mois) > 0 and "Nom" in _df_mois.columns else ""

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
    "\U0001f3eb EDC",
    "\U0001f6e1\ufe0f Mutuelle Sûreté",
    "\U0001f4cb Conventions encours",
    "\U0001f91d CRM",
    "\U0001f6a8 Alertes Tendances",
    "\U0001f4c2 Archive Rapports",
])

# ══════════════════════════════════════════════════════════════
# TAB 0 — VUE EXÉCUTIVE
# ══════════════════════════════════════════════════════════════
with tabs[0]:

    # ── KPI strip ─────────────────────────────────────────────
    section("Indicateurs clés")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(
        f"CA {annee_sel}",
        f"{ca_n:,.0f} TND",
        f"{ev_nn1:+.1f}% vs {annee_sel-1}",
        delta_color="normal" if ev_nn1 >= 0 else "inverse",
    )
    k2.metric(
        f"CA {annee_sel-1}",
        f"{ca_n1:,.0f} TND",
        f"{ev_n1n2:+.1f}% vs {annee_sel-2}",
        delta_color="normal" if ev_n1n2 >= 0 else "inverse",
    )
    k3.metric("Conventions actives", nb_actives, f"/ {nb_total} total")
    k4.metric(
        "Conventions inactives",
        nb_inact,
        f"\u26a0\ufe0f >{seuil_inactif}j sans facture" if nb_inact > 0 else "\u2705 Aucune",
        delta_color="inverse" if nb_inact > 0 else "off",
    )
    k5.metric("Panier moyen", f"{panier_moy:,.0f} TND")

    nb_transactions = len(df_filt) if len(df_filt) > 0 else 0

    # ── Statistiques journalières ────────────────────────────
    section("Statistiques journalières")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Nb transactions", nb_transactions)
    s2.metric("Panier min", f"{panier_min:,.0f} TND")
    s3.metric("Panier max", f"{panier_max:,.0f} TND")
    s4.metric("Panier moyen", f"{panier_moy:,.0f} TND")

    mois_label = ", ".join([MOIS.get(m, str(m)) for m in mois_sel]) if mois_sel else f"{annee_sel}"
    st.caption(f"\U0001f4cc Panier min: {min_mag}  |  Panier max: {max_mag}  ({mois_label})")

    # ── Évolution CA ──────────────────────────────────────────
    section("Évolution du chiffre d'affaires")
    col_a, col_b = st.columns(2)

    with col_a:
        ca_by_year = (
            df_vc.groupby("Année")["Montant TTC"].sum().reset_index().sort_values("Année")
        )
        fig_wf = chart_waterfall(ca_by_year, "Année", "Montant TTC",
                                  "CA par année — Waterfall évolution")
        st.plotly_chart(fig_wf, use_container_width=True)

    with col_b:
        fig_gb = chart_grouped_bar(
            df_comp, "Mois Nom", "CA N", "CA N-1",
            f"CA Mensuel — {annee_sel} vs {annee_sel-1}", annee_sel,
        )
        st.plotly_chart(fig_gb, use_container_width=True)

    # ── Portefeuille conventions ───────────────────────────────
    section("Portefeuille conventions — Performance")
    col_c, col_d = st.columns(2)

    with col_c:
        top10 = df_filt.groupby("Nom")["Montant TTC"].sum().nlargest(10).reset_index()
        fig_t10 = chart_bar(
            top10, "Montant TTC", "Nom",
            f"Top 10 conventions — {annee_sel}", C["blue"], h=400, orientation="h",
        )
        st.plotly_chart(fig_t10, use_container_width=True)

    with col_d:
        fig_var = chart_variation_bar(
            risk_mat.head(20), "Nom", "Évolution %",
            f"Évolution N/N-1 — Top 20 conventions", h=400,
        )
        st.plotly_chart(fig_var, use_container_width=True)

    # ── Tableau risque simplifié + Top/Flop ────────────────────
    section("Signaux décisionnels — Risques & Opportunités")
    col_e, col_f, col_g = st.columns([3, 1, 1])

    with col_e:
        fig_sc = chart_risk_table(
            risk_mat.head(20), annee_sel,
            "État du portefeuille — Vue condensée", h=450,
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    if "Nom" in df_filt.columns and len(df_filt) > 0:
        ca_cli = df_filt.groupby("Nom")["Montant TTC"].sum()
        top3   = ca_cli.nlargest(3)
        flop3  = ca_cli[ca_cli > 0].nsmallest(3) if len(ca_cli[ca_cli > 0]) >= 3 else ca_cli.nsmallest(3)

        with col_f:
            st.markdown("**\U0001f3c6 Top 3**")
            for i, (nom, ca) in enumerate(top3.items(), 1):
                rank_card(i, nom, f"{ca:,.0f} TND", "top")

        with col_g:
            st.markdown("**\u26a0\ufe0f Flop 3**")
            for i, (nom, ca) in enumerate(flop3.items(), 1):
                rank_card(i, nom, f"{ca:,.0f} TND", "flop")

    # ── Dynamique du portefeuille ────────────────────────────
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
        # First invoice date per convention → monthly new conventions
        _first = _all.groupby("Nom")["Date"].min().reset_index()
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
            evo_pf = ((avg_a - avg_n1) / avg_n1 * 100) if avg_n1 > 0 else 0
            st.metric("Moy. actives/mois", f"{avg_a:.0f}", f"{evo_pf:+.1f}% vs N-1")
            st.metric("Nouvelles YTD", f"{_pf_annee['Nouvelles'].sum():.0f}")
            # Net growth
            net = _pf_annee["Nouvelles"].sum() if not _pf_annee.empty else 0
            st.metric("Variation nette", f"{net:+.0f}")

    # ── Concentration du portefeuille ────────────────────────
    section("Concentration du portefeuille")
    _conc = df_filt.groupby("Nom")["Montant TTC"].sum().reset_index()
    _conc = _conc.sort_values("Montant TTC", ascending=False)
    _total_ca = _conc["Montant TTC"].sum()
    if _total_ca > 0:
        _conc["Share"] = _conc["Montant TTC"] / _total_ca
        _conc["ShareSq"] = _conc["Share"] ** 2
        _hhi = int(_conc["ShareSq"].sum() * 10000)
        _top1 = _conc["Montant TTC"].iloc[0]
        _top3 = _conc["Montant TTC"].iloc[:3].sum()
        _top5 = _conc["Montant TTC"].iloc[:5].sum()
        _top10 = _conc["Montant TTC"].iloc[:10].sum()
        _hhi_label = "Faible" if _hhi < 1000 else "Modérée" if _hhi < 2500 else "Élevée"
        _c1, _c2, _c3, _c4, _c5 = st.columns(5)
        _c1.metric("HHI", f"{_hhi}", f"{_hhi_label}")
        _c2.metric("Part Top 1", f"{_top1/_total_ca*100:.1f}%")
        _c3.metric("Part Top 3", f"{_top3/_total_ca*100:.1f}%")
        _c4.metric("Part Top 5", f"{_top5/_total_ca*100:.1f}%")
        _c5.metric("Part Top 10", f"{_top10/_total_ca*100:.1f}%")
        # Concentration chart: cumulative share
        _conc["Cumul"] = _conc["Share"].cumsum() * 100
        _conc_top = _conc.head(20)
        fig_conc = go.Figure()
        fig_conc.add_trace(go.Bar(x=_conc_top["Nom"].str[:20], y=_conc_top["Montant TTC"],
                                  name="CA", marker_color=C["blue"]))
        fig_conc.add_trace(go.Scatter(x=_conc_top["Nom"].str[:20], y=_conc_top["Cumul"],
                                      name="% Cumulé", yaxis="y2",
                                      line=dict(color=C["red"], width=2),
                                      marker=dict(color=C["red"])))
        fig_conc.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10),
                               yaxis=dict(title="CA"),
                               yaxis2=dict(title="% Cumulé", overlaying="y", side="right"))
        st.plotly_chart(fig_conc, use_container_width=True)
    else:
        st.caption("Aucune donnée disponible.")


# ══════════════════════════════════════════════════════════════
# TAB 1 — CA & TENDANCES
# ══════════════════════════════════════════════════════════════
with tabs[1]:

    # ══════════════════════════════════════════════════════
    # SECTION VEILLE — DECISIONNELLE (date sélectionnable)
    # ══════════════════════════════════════════════════════
    st.markdown("### \U0001f4ca Performance veille")

    # Date sélectionnable (par défaut hier)
    default_date = (datetime.now() - timedelta(days=1)).date()
    hier_date = st.date_input("Choisir une date", value=default_date, key="veille_date")
    annee_hier = hier_date.year
    mois_hier = hier_date.month

    df_vc_hier = df_vc[(df_vc["Date"].dt.date == hier_date)].copy()
    df_vc_n1 = df_vc[(df_vc["Année"] == annee_hier - 1) & (df_vc["Mois"] == mois_hier) & (df_vc["Jour"] == hier_date.day)].copy()

    # KPI veille
    ca_veille = df_vc_hier["Montant TTC"].sum() if len(df_vc_hier) > 0 else 0
    ca_n1_meme_jour = df_vc_n1["Montant TTC"].sum() if len(df_vc_n1) > 0 else 0
    evo_veille = ((ca_veille - ca_n1_meme_jour) / ca_n1_meme_jour * 100) if ca_n1_meme_jour > 0 else 0
    nb_tickets_veille = len(df_vc_hier)
    panier_veille = ca_veille / nb_tickets_veille if nb_tickets_veille > 0 else 0

    # KPI Cards horizontales
    kp1, kp2, kp3, kp4 = st.columns(4)
    kp1.metric("CA Veille", f"{ca_veille:,.0f} TND", delta_color="normal" if evo_veille >= 0 else "inverse")
    kp2.metric("Evolution vs N-1", f"{evo_veille:+.1f}%", delta_color="normal" if evo_veille >= 0 else "inverse")
    kp3.metric("Nb Tickets", nb_tickets_veille)
    kp4.metric("Panier Moyen", f"{panier_veille:,.0f} TND")

    st.caption(f"\U0001f4c5 Date sélectionnée: {hier_date.strftime('%d/%m/%Y')}")

    # Analyse par segment
    col_seg1, col_seg2 = st.columns(2)

    with col_seg1:
        st.markdown("**Top 5 Conventions — Veille**")
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
        st.markdown("**Top 5 Magasins — Veille**")
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
    st.markdown("### \U0001f514 Alertes & Insights — Veille")

    alertes = []
    couleur_alertes = []

    if evo_veille < -20:
        alertes.append(f"\u26a0\ufe0f Baisse significative: {evo_veille:.1f}% vs N-1")
        couleur_alertes.append("inverse")
    elif evo_veille >= 0:
        alertes.append(f"\u2705 Belle performance: +{evo_veille:.1f}% vs N-1")
        couleur_alertes.append("normal")

    if panier_veille < panier_moy * 0.8:
        alertes.append(f"\U0001f4c9 Panier bas: {panier_veille:,.0f} TND (moy: {panier_moy:,.0f})")
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
        df_jour["Variation %"] = (
            (df_jour["CA N"] - df_jour["CA N-1"]) / df_jour["CA N-1"].replace(0, 1) * 100
        ).round(1)
        st.dataframe(df_jour, use_container_width=True)

    # ── Heatmap CA mensuel × année ─────────────────────────────
    section("Saisonnalité — Heatmap CA mensuel × année")
    _hm = df_vc.groupby(["Année", "Mois"])["Montant TTC"].sum().reset_index()
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
    _prev_df = df_vc[df_vc["Année"] >= max(annee_sel - 1, df_vc["Année"].min())].copy()
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
    pk2.metric("\U0001f4b0 CA Total N", f"{ca_total_n:,.0f} TND", f"{ev_total:+.1f}%",
               delta_color="normal" if ev_total >= 0 else "inverse")
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
                   f"{ev_cv:+.1f}% vs {annee_sel-1}",
                   delta_color="normal" if ev_cv >= 0 else "inverse")
        ci2.metric(f"CA {annee_sel-1}", f"{ca_cv_n1:,.0f} TND")
        ci3.metric(f"Factures {annee_sel}", nb_fact_cv)
        ci4.metric("Panier moyen", f"{panier_cv:,.0f} TND")

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
                detail_m["Évolution %"] = ((detail_m["Montant TTC"] - detail_m["CA N-1"]) / detail_m["CA N-1"].replace(0, 1) * 100).round(1)
                detail_m["CA N-1"] = detail_m["CA N-1"].apply(lambda x: f"{x:,.0f}" if x > 0 else "-")
            else:
                detail_m["CA N-1"] = "-"
                detail_m["Évolution %"] = 0.0

            detail_m["Montant TTC"]   = detail_m["Montant TTC"].apply(lambda x: f"{x:,.0f}")
            detail_m["Dernière Vente"] = detail_m["Dernière Vente"].dt.strftime("%d/%m/%Y")
            detail_m["Évolution %"]   = detail_m["Évolution %"].apply(lambda x: f"{x:+.1f}%")

            st.dataframe(detail_m.sort_values("Montant TTC", ascending=False),
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
        _base_n  = df_vc_filt[df_vc_filt["Année"] == annee_sel].copy()
        _base_n1 = df_vc_filt[df_vc_filt["Année"] == annee_sel - 1].copy()
        # ponytail: date-à-date — tronquer N-1 aux mêmes (Mois, Jour) que N
        if "Jour" in _base_n.columns and "Jour" in _base_n1.columns and not _base_n.empty:
            _n_dates = _base_n[["Mois", "Jour"]].drop_duplicates()
            _base_n1 = _base_n1.merge(_n_dates, on=["Mois", "Jour"], how="inner")

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
            k1.metric(f"\U0001f4b0 CA {annee_sel}", f"{ca_n_s:,.0f} TND", f"{evol_s:+.1f}%", delta_color="normal" if evol_s >= 0 else "inverse")
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
                    detail["Montant TTC"] = detail["Montant TTC"].apply(lambda x: f"{x:,.0f}")
                    detail["Dernière Vente"] = detail["Dernière Vente"].dt.strftime("%d/%m/%Y")
                    st.dataframe(detail.sort_values("Montant TTC", ascending=False),
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
                    c2.metric(f"\U0001f4b0 CA {annee_sel}", f"{ca_n_val:,.0f} TND", f"{ev:+.1f}%" if ca_n_val > 0 else None,
                              delta_color="normal" if ev >= 0 else "inverse")
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

                        st.metric(f"CA {an}", f"{ca_t:,.0f} TND", f"{evo_t:+.1f}%")
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
        _n  = _df[_df["Année"] == annee_sel]
        _n1 = _df[_df["Année"] == annee_sel - 1]
        if "Jour" in _n.columns and "Jour" in _n1.columns and not _n.empty:
            _n1 = _n1.merge(_n[["Mois", "Jour"]].drop_duplicates(), on=["Mois", "Jour"], how="inner")  # ponytail: date-à-date
        _ca_n  = _n["Montant TTC"].sum()
        _ca_n1 = _n1["Montant TTC"].sum()
        _ev = evol_pct(_ca_n, _ca_n1) if _ca_n1 > 0 else 0
        _nb_mag = _n["Magasin"].nunique()
        _nb_mag_n1 = _n1["Magasin"].nunique()
        _part = _ca_n / df_vc[df_vc["Année"] == annee_sel]["Montant TTC"].sum() * 100 if not df_vc[df_vc["Année"] == annee_sel].empty else 0
        _c1, _c2, _c3, _c4, _c5 = st.columns(5)
        _c1.metric(f"CA {enseigne} {annee_sel}", f"{_ca_n:,.0f}", f"{_ev:+.1f}%",
                   delta_color="normal" if _ev >= 0 else "inverse")
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
# TAB 4 — EDC
# ══════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("\U0001f3eb Convention EDC — Ministère de l'Éducation")

    if not df_edc.empty and "Année" in df_edc.columns:
        edc_yr = st.selectbox("Année", [2026, 2025, 2024], key="edc_yr")

        df_edc_n  = df_edc[df_edc["Année"] == edc_yr]
        df_edc_n1 = df_edc[df_edc["Année"] == edc_yr - 1]

        if mois_sel:
            df_edc_n  = df_edc_n[df_edc_n["Mois"].isin(mois_sel)]
            df_edc_n1 = df_edc_n1[df_edc_n1["Mois"].isin(mois_sel)]

        if len(df_edc_n) > 0 and "Jour" in df_edc_n.columns and len(df_edc_n1) > 0:
            edc_comp = compare_years_date_to_date(
                pd.concat([df_edc_n, df_edc_n1]),
                edc_yr, edc_yr - 1, mois_sel
            )
            ca_e_n = edc_comp["CA N"].sum() if not edc_comp.empty else 0.0
            ca_e_n1 = edc_comp["CA N-1"].sum() if not edc_comp.empty else 0.0
        else:
            ca_e_n    = float(df_edc_n["Montant TTC"].sum())  if "Montant TTC" in df_edc_n.columns  else 0.0
            ca_e_n1   = float(df_edc_n1["Montant TTC"].sum()) if "Montant TTC" in df_edc_n1.columns else 0.0

        ev_edc    = evol_pct(ca_e_n, ca_e_n1)
        nb_f_edc  = len(df_edc_n)
        panier_e  = ca_e_n / nb_f_edc if nb_f_edc > 0 else 0

        e1, e2, e3, e4 = st.columns(4)
        e1.metric(f"CA {edc_yr}", f"{ca_e_n:,.0f} TND", f"{ev_edc:+.1f}%",
                  delta_color="normal" if ev_edc >= 0 else "inverse")
        e2.metric(f"CA {edc_yr-1}", f"{ca_e_n1:,.0f} TND")
        e3.metric("Nb factures", nb_f_edc)
        e4.metric("Panier moyen", f"{panier_e:,.0f} TND")

        section(f"Top Établissements — {edc_yr}")

        etab = (
            df_edc_n.groupby("Magasin")
            .agg(CA_N=("Montant TTC", "sum"), Nb=("Montant TTC", "count"))
            .reset_index()
            .sort_values("CA_N", ascending=False)
        )
        etab["Panier moyen"] = (etab["CA_N"] / etab["Nb"]).round(0)
        total_edc_n = etab["CA_N"].sum()
        etab["Poids %"] = (etab["CA_N"] / total_edc_n * 100).round(1) if total_edc_n > 0 else 0.0

        etab_n1 = (
            df_edc_n1.groupby("Magasin")
            .agg(CA_N1=("Montant TTC", "sum"))
            .reset_index()
        )
        etab = etab.merge(etab_n1, on="Magasin", how="left").fillna(0)
        etab["Evolution %"] = np.where(
            etab["CA_N1"] > 0,
            ((etab["CA_N"] - etab["CA_N1"]) / etab["CA_N1"] * 100).round(1),
            0.0
        )

        c_et1, c_et2, c_et3, c_et4 = st.columns(4)
        c_et1.metric("\U0001f3ea Établissements actifs", len(etab[etab["CA_N"] > 0]))
        c_et2.metric("\U0001f4b0 CA Total EDC", f"{total_edc_n:,.0f} TND")
        c_et3.metric("\U0001f4c8 En croissance", len(etab[etab["Evolution %"] > 0]))
        c_et4.metric("\U0001f4c9 En baisse", len(etab[etab["Evolution %"] < 0]))

        col_b1, col_b2 = st.columns([3, 2])
        with col_b1:
            top10 = etab.head(10).sort_values("CA_N")
            fig_top = px.bar(
                top10, x="CA_N", y="Magasin", orientation="h",
                title=f"Top 10 Établissements — {edc_yr}",
                color="CA_N", color_continuous_scale=["#1D4ED8", "#3B82F6", "#60A5FA"],
                text_auto=".0f"
            )
            fig_top.update_layout(height=400, yaxis=dict(autorange="reversed"))
            fig_top.update_traces(textposition="outside")
            st.plotly_chart(fig_top, use_container_width=True)
        with col_b2:
            fig_pie = px.pie(
                etab.head(8), values="CA_N", names="Magasin",
                title="Répartition du CA EDC", hole=0.42,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("\U0001f4cb Tableau complet des établissements"):
            display_cols = ["Magasin", "CA_N", "Nb", "Panier moyen", "Poids %", "Evolution %"]
            rename_map = {
                "Magasin": "Établissement", "CA_N": "CA N", "Nb": "Nb factures",
                "Poids %": "Poids %", "Evolution %": "Évolution %"
            }
            display_df = etab[display_cols].rename(columns=rename_map)
            st.dataframe(
                display_df.style.format({
                    "CA N": "{:,.0f}", "Panier moyen": "{:,.0f}",
                    "Poids %": "{:.1f}%", "Évolution %": "{:+.1f}%"
                }, na_rep="—"),
                use_container_width=True, height=400
            )

        section("Répartition par durée d'échéance")
        if "Nbr_Mois_Echance" in df_edc.columns:
            ech = (
                df_edc_n.groupby("Nbr_Mois_Echance")
                .agg(CA=("Montant TTC", "sum"), Nb=("Montant TTC", "count"))
                .reset_index()
            )
            ech["Part %"] = (ech["CA"] / ech["CA"].sum() * 100).round(1)
            ech["Label"]  = ech["Part %"].apply(lambda p: f"{p}%")
            ech = ech.sort_values("CA", ascending=False)

            col_ec1, col_ec2 = st.columns([2, 1])
            with col_ec1:
                fig_ech = chart_bar(
                    ech, "Nbr_Mois_Echance", "CA",
                    f"Répartition par durée d'échéance — {edc_yr}", C["blue"],
                )
                fig_ech.update_xaxes(title="Durée (mois)", type="category")
                fig_ech.update_yaxes(title="CA TTC (TND)")
                fig_ech.update_traces(text=ech["Label"].tolist(), textposition="outside")
                st.plotly_chart(fig_ech, use_container_width=True)

            with col_ec2:
                fig_pie_e = chart_pie(
                    ech["CA"].tolist(),
                    [f"{m} mois" for m in ech["Nbr_Mois_Echance"]],
                    "Part par échéance",
                )
                st.plotly_chart(fig_pie_e, use_container_width=True)

        section("Tendance mensuelle EDC")
        df_edc_comp = compare_years_date_to_date(df_edc, edc_yr, edc_yr - 1)
        if not df_edc_comp.empty:
            fig_edc_t = chart_grouped_bar(
                df_edc_comp, "Mois Nom", "CA N", "CA N-1",
                f"EDC mensuel — {edc_yr} vs {edc_yr-1}", edc_yr,
            )
            st.plotly_chart(fig_edc_t, use_container_width=True)
    else:
        st.warning("\u26a0\ufe0f Aucune donnée EDC disponible.")


# ══════════════════════════════════════════════════════════════
# TAB 5 — MUTUELLE SÛRETÉ NATIONALE — PRISON & RÉÉDUCATION
# ══════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("\U0001f6e1\ufe0f Mutuelle Personnel Sûreté Nationale — Prison & Rééducation")
    st.caption(
        "Compte dédié extrait du flux Crédit Conso (VC.CONSO.) — client "
        "« MUT PERS SURETE NLE PRISON &REEDUC ». Lecture en 3 niveaux : situation → performance → détail."
    )

    if df_mutuelle.empty or "Année" not in df_mutuelle.columns:
        st.warning("\u26a0\ufe0f Aucune donnée Mutuelle Sûreté disponible dans le fichier crédit conso.")
    else:
        # ── NIVEAU 0 · Préparation (nulls, codes non mappés) ──
        mut = df_mutuelle.copy()
        if "Montant TTC" not in mut.columns:
            mut["Montant TTC"] = 0.0
        mut["Montant TTC"] = pd.to_numeric(mut["Montant TTC"], errors="coerce").fillna(0.0)
        if "Montant ouvert" not in mut.columns:
            mut["Montant ouvert"] = 0.0
        mut["Montant ouvert"] = pd.to_numeric(mut["Montant ouvert"], errors="coerce").fillna(0.0)

        def _txt(series, default="—"):
            """Colonne texte propre : jamais de NaN (pandas 3 conserve les NaN en dtype str)."""
            s = series.astype(object)
            s = s.where(s.notna(), default)
            return s.astype(str).str.strip().replace({"nan": default, "None": default, "": default})

        mut["Dossier"] = (
            _txt(mut["N°"]) if "N°" in mut.columns else pd.Series(mut.index.astype(str), index=mut.index)
        )
        mut["Adhérent ID"] = _txt(mut["N° Client"]) if "N° Client" in mut.columns else "—"
        mut["Adhérent"] = _txt(mut["Nom Client"]) if "Nom Client" in mut.columns else mut["Adhérent ID"]
        mut["Enseigne"] = _txt(mut["Enseigne"], "MG") if "Enseigne" in mut.columns else "MG"

        # Magasin : libellés explicites quand le code est absent ou non mappé
        _mag_raw = mut["Magasin"] if "Magasin" in mut.columns else pd.Series("", index=mut.index)
        _mag = _txt(_mag_raw, "Magasin non renseigné")
        _code = _txt(mut["Unite Code"], "") if "Unite Code" in mut.columns else pd.Series("", index=mut.index)
        _code = _code.str.replace(r"\.0$", "", regex=True)
        _mag_absent = _mag_raw.isna() | _mag.str.lower().isin(["nan", "none", "<na>", ""])
        _mag_non_mappe = (~_mag_absent) & _mag.str.match(r"^\d+$", na=False)
        mut["Magasin"] = _mag.where(~_mag_absent, "Magasin non renseigné")
        mut.loc[_mag_non_mappe, "Magasin"] = "Code " + _code[_mag_non_mappe].astype(str) + " (non mappé)"

        mut["_cloture"] = (
            _txt(mut["Clôturé"], "false").str.lower().isin(["true", "1", "1.0", "oui", "yes"])
            if "Clôturé" in mut.columns else True
        )
        mut["_annule"] = (
            _txt(mut["Annulé"], "false").str.lower().isin(["true", "1", "1.0", "oui", "yes"])
            if "Annulé" in mut.columns else False
        )
        _col_ech = next((c for c in mut.columns if c.startswith("Nbr_Mois_Ech")), None)

        # ── NIVEAU 0 · Filtres du compte ──────────────────────
        annees_dispo = sorted({int(a) for a in mut["Année"].dropna().unique()}, reverse=True)
        fc1, fc2, fc3 = st.columns([1, 1.3, 2.2])
        with fc1:
            mut_yr = st.selectbox("Année de référence", annees_dispo, index=0, key="mut_yr")
        with fc2:
            ens_sel = st.multiselect("Enseigne", sorted(mut["Enseigne"].unique().tolist()), default=[], key="mut_ens")
        with fc3:
            _base_ens = mut[mut["Enseigne"].isin(ens_sel)] if ens_sel else mut
            mag_sel = st.multiselect("Magasin", sorted(_base_ens["Magasin"].unique().tolist()), default=[], key="mut_mag")

        mut_f = mut
        if ens_sel:
            mut_f = mut_f[mut_f["Enseigne"].isin(ens_sel)]
        if mag_sel:
            mut_f = mut_f[mut_f["Magasin"].isin(mag_sel)]

        # ── Périmètre & périodes comparées (date à date) ──────
        mut_n = mut_f[mut_f["Année"] == mut_yr].copy()
        if mois_sel:
            mut_n = mut_n[mut_n["Mois"].isin(mois_sel)]
        _trunc = truncate_n1_date_to_date(mut_f, mut_yr, mut_yr - 1, mois_sel)
        mut_n1 = _trunc[_trunc["Année"] == mut_yr - 1].copy()
        if mois_sel:
            # truncate_n1_date_to_date borne seulement les jours des mois sélectionnés
            # (les autres mois restent, pour les tendances) -> on applique le filtre mois ici.
            mut_n1 = mut_n1[mut_n1["Mois"].isin(mois_sel)]
        comp = (
            compare_years_date_to_date(mut_f, mut_yr, mut_yr - 1, mois_sel)
            if len(mut_n) > 0 and len(mut_n1) > 0 else pd.DataFrame()
        )
        ca_n = float(comp["CA N"].sum()) if not comp.empty else float(mut_n["Montant TTC"].sum())
        ca_n1 = float(comp["CA N-1"].sum()) if not comp.empty else float(mut_n1["Montant TTC"].sum())
        ca_n_annee = float(mut_f[mut_f["Année"] == mut_yr]["Montant TTC"].sum())
        mois_dispo_n = sorted(int(m) for m in mut_f[mut_f["Année"] == mut_yr]["Mois"].dropna().unique())

        def _safe_div(a, b):
            """Division protégée (retourne 0 si dénominateur nul)."""
            return a / b if b else 0.0

        def _delta(n_val, n1_val):
            """Delta % affichable, None si aucune base de comparaison en N-1."""
            return f"{evol_pct(n_val, n1_val):+.1f}%" if n1_val > 0 else None

        st.caption(
            f"Année {mut_yr} — mois disponibles : "
            f"{', '.join(MOIS.get(m, str(m)) for m in mois_dispo_n) or 'aucun'}"
            + (
                f" • Périmètre filtré : {', '.join(ens_sel)}"
                + (f" · {len(mag_sel)} magasin(s)" if mag_sel else "")
                if (ens_sel or mag_sel) else " • Périmètre : toutes enseignes / tous magasins"
            )
        )
        # ══ NIVEAU 1 · SITUATION — indicateurs clés ══════════
        section("1 · Situation du compte")
        nb_n = int(mut_n["Dossier"].nunique())
        nb_n1 = int(mut_n1["Dossier"].nunique())
        adh_n = int(mut_n["Adhérent ID"].nunique())
        adh_n1 = int(mut_n1["Adhérent ID"].nunique())
        panier_n = _safe_div(ca_n, nb_n)
        panier_n1 = _safe_div(ca_n1, nb_n1)
        ca_adh_n = _safe_div(ca_n, adh_n)
        ca_adh_n1 = _safe_div(ca_n1, adh_n1)

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            kpi_card(
                f"CA {mut_yr}", f"{ca_n:,.0f} TND", _delta(ca_n, ca_n1),
                delta_tone="normal" if ca_n >= ca_n1 else "inverse",
                ref_label=f"CA {mut_yr-1}",
                ref_value=f"{ca_n1:,.0f} TND",
                help=f"Comparé date à date avec {mut_yr-1} sur les mois sélectionnés ; "
                     f"référence {mut_yr-1} sur la même période : {ca_n1:,.0f} TND.",
            )
        k2.metric(
            "Adhérents actifs", f"{adh_n:,}", _delta(adh_n, adh_n1),
            delta_color="normal" if adh_n >= adh_n1 else "inverse",
            help="Adhérents uniques ayant au moins un dossier sur la période.",
        )
        k3.metric(
            "Dossiers", f"{nb_n:,}", _delta(nb_n, nb_n1),
            delta_color="normal" if nb_n >= nb_n1 else "inverse",
        )
        k4.metric(
            "Panier moyen / dossier", f"{panier_n:,.0f} TND", _delta(panier_n, panier_n1),
            delta_color="normal" if panier_n >= panier_n1 else "inverse",
        )
        k5.metric(
            "CA moyen / adhérent", f"{ca_adh_n:,.0f} TND", _delta(ca_adh_n, ca_adh_n1),
            delta_color="normal" if ca_adh_n >= ca_adh_n1 else "inverse",
        )

        # ── Acquisition, place dans le flux, recouvrement ────
        ids_n = set(mut_n["Adhérent ID"].dropna())
        ids_n1 = set(mut_n1["Adhérent ID"].dropna())
        nouveaux = ids_n - ids_n1
        non_reconduits = ids_n1 - ids_n

        _cc = df_credit.copy()
        if "Année" in _cc.columns:
            _cc = _cc[_cc["Année"].isin([mut_yr, mut_yr - 1])]
            if mois_sel:
                _cc = _cc[_cc["Mois"].isin(mois_sel)]
        _cc_n = float(_cc[_cc["Année"] == mut_yr]["Montant TTC"].sum()) if not _cc.empty else 0.0
        _cc_n1 = float(_cc[_cc["Année"] == mut_yr - 1]["Montant TTC"].sum()) if not _cc.empty else 0.0
        part_n = _safe_div(ca_n * 100, _cc_n)
        part_n1 = _safe_div(ca_n1 * 100, _cc_n1)

        nonclot = mut[~mut["_cloture"]]
        encours = float(nonclot["Montant ouvert"].sum())
        _hist = mut.groupby("Adhérent ID")["Dossier"].nunique()
        adh_hist = int(len(_hist))
        adh_fideles = int((_hist >= 2).sum())
        taux_recur = _safe_div(adh_fideles * 100, adh_hist)
        _mag_reseau = ~mut["Magasin"].isin(["Magasin non renseigné"]) & ~mut["Magasin"].str.startswith("Code ", na=False)
        mag_actifs_n = int(mut_n[(mut_n["Montant TTC"] > 0) & _mag_reseau.reindex(mut_n.index, fill_value=False)]["Magasin"].nunique())
        mag_actifs_n1 = int(mut_n1[(mut_n1["Montant TTC"] > 0) & _mag_reseau.reindex(mut_n1.index, fill_value=False)]["Magasin"].nunique())

        k6, k7, k8, k9, k10 = st.columns(5)
        k6.metric("Nouveaux adhérents", f"{len(nouveaux):,}",
                  help=f"Adhérents actifs sur la période, absents de la même période en {mut_yr-1}.")
        k7.metric("Adhérents non reconduits", f"{len(non_reconduits):,}",
                  help=f"Adhérents actifs sur la même période en {mut_yr-1}, sans dossier cette période.")
        k8.metric("Magasins actifs", f"{mag_actifs_n:,}", _delta(mag_actifs_n, mag_actifs_n1),
                  delta_color="normal" if mag_actifs_n >= mag_actifs_n1 else "inverse",
                  help="Points de vente distincts avec CA, hors dossiers non rattachés à un magasin.")
        k9.metric("Part du CA crédit conso", f"{part_n:.2f}%",
                  f"{part_n - part_n1:+.2f} pts" if part_n1 > 0 else None,
                  help="Poids du compte Mutuelle dans le CA total du flux Crédit Conso (même période).")
        k10.metric(f"CA {mut_yr} toutes périodes", f"{ca_n_annee:,.0f} TND",
                   help="CA du millésime complet, indépendant du filtre « Mois » — sert de référence "
                        "lorsque la période analysée est partielle.")

        if len(mut_n) == 0 and len(mut_n1) == 0:
            st.warning(
                "Aucune ligne sur le périmètre et les mois sélectionnés. "
                f"CA {mut_yr} toutes périodes confondues : {ca_n_annee:,.0f} TND. "
                "Élargissez le filtre « Mois » (barre latérale) ou réinitialisez les filtres du compte."
            )
        elif mois_sel and mois_dispo_n and max(mois_sel) > max(mois_dispo_n):
            st.info(
                f"\u2139\ufe0f Données {mut_yr} disponibles jusqu'à "
                f"{MOIS.get(max(mois_dispo_n), max(mois_dispo_n))} — les mois suivants ne sont pas encore comptabilisés."
            )
        # ══ NIVEAU 2 · PERFORMANCE — dynamique du compte ═════
        section("2 · Dynamique & saisonnalité")

        if comp.empty:
            st.info(f"Pas de comparatif {mut_yr-1} exploitable pour le périmètre sélectionné.")
        else:
            st.plotly_chart(
                chart_grouped_bar(
                    comp, "Mois Nom", "CA N", "CA N-1",
                    f"CA mensuel Mutuelle — {mut_yr} vs {mut_yr-1} (date à date)", mut_yr,
                ),
                use_container_width=True,
            )
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                comp_cum = comp.sort_values("Mois").copy()
                comp_cum["CA N"] = comp_cum["CA N"].cumsum()
                comp_cum["CA N-1"] = comp_cum["CA N-1"].cumsum()
                st.plotly_chart(
                    chart_line_compare(
                        comp_cum, "Mois Nom", "CA N", "CA N-1",
                        f"CA cumulé — {mut_yr} vs {mut_yr-1}", mut_yr,
                    ),
                    use_container_width=True,
                )
            with col_c2:
                _dn = mut_n.groupby("Mois")["Dossier"].nunique().to_dict()
                _dn1 = mut_n1.groupby("Mois")["Dossier"].nunique().to_dict()
                dos_m = comp[["Mois", "Mois Nom"]].copy()
                dos_m["Dossiers N"] = [int(_dn.get(int(m), 0)) for m in dos_m["Mois"]]
                dos_m["Dossiers N-1"] = [int(_dn1.get(int(m), 0)) for m in dos_m["Mois"]]
                fig_dos = px.bar(
                    dos_m.melt(id_vars=["Mois", "Mois Nom"], value_vars=["Dossiers N-1", "Dossiers N"],
                               var_name="Période", value_name="Dossiers"),
                    x="Mois Nom", y="Dossiers", color="Période", barmode="group", text_auto=True,
                    title=f"Dossiers mensuels — {mut_yr} vs {mut_yr-1}",
                    color_discrete_map={"Dossiers N-1": C["slate"], "Dossiers N": C["blue"]},
                )
                fig_dos.update_layout(
                    template="plotly_white", height=380, margin=dict(l=16, r=16, t=52, b=16),
                    legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center", yanchor="bottom"),
                    font=dict(family="DM Sans, Figtree, sans-serif", color=C["ink"], size=13),
                )
                fig_dos.update_yaxes(title="Dossiers")
                st.plotly_chart(fig_dos, use_container_width=True)

        # ══ NIVEAU 2 · PERFORMANCE — mix & réseau magasins ═══
        section("3 · Mix enseigne & réseau magasins")

        ens_cmp = (
            pd.concat([
                mut_n.groupby("Enseigne")["Montant TTC"].sum().rename("CA N"),
                mut_n1.groupby("Enseigne")["Montant TTC"].sum().rename("CA N-1"),
            ], axis=1).fillna(0).reset_index().sort_values("CA N", ascending=False)
        )
        ens_cmp["Poids %"] = (
            (ens_cmp["CA N"] / ens_cmp["CA N"].sum() * 100).round(1) if ens_cmp["CA N"].sum() > 0 else 0.0
        )

        mag_tab = (
            mut_n.groupby("Magasin")
            .agg(CA_N=("Montant TTC", "sum"), Dossiers=("Dossier", "nunique"),
                 Adherents=("Adhérent ID", "nunique"))
            .reset_index()
            .rename(columns={"CA_N": "CA N", "Adherents": "Adhérents"})
        )
        _mag_n1 = mut_n1.groupby("Magasin")["Montant TTC"].sum().rename("CA N-1").reset_index()
        mag_tab = mag_tab.merge(_mag_n1, on="Magasin", how="outer")
        mag_tab["CA N"] = mag_tab["CA N"].fillna(0.0)
        mag_tab["CA N-1"] = mag_tab["CA N-1"].fillna(0.0)
        mag_tab["Dossiers"] = mag_tab["Dossiers"].fillna(0).astype(int)
        mag_tab["Adhérents"] = mag_tab["Adhérents"].fillna(0).astype(int)
        mag_tab["Évolution %"] = np.where(
            mag_tab["CA N-1"] > 0,
            ((mag_tab["CA N"] - mag_tab["CA N-1"]) / mag_tab["CA N-1"] * 100).round(1),
            np.nan,
        )
        mag_tab["Panier moyen"] = (
            mag_tab["CA N"] / mag_tab["Dossiers"].replace(0, np.nan)
        ).fillna(0).round(0)
        mag_tot = float(mag_tab["CA N"].sum())
        mag_tab["Poids %"] = (mag_tab["CA N"] / mag_tot * 100).round(1) if mag_tot > 0 else 0.0
        mag_tab = mag_tab.sort_values("CA N", ascending=False).reset_index(drop=True)
        mag_tab["Poids cumulé %"] = mag_tab["Poids %"].cumsum().round(1) if mag_tot > 0 else 0.0
        mag_tab["Statut"] = np.select(
            [
                (mag_tab["CA N"] == 0) & (mag_tab["CA N-1"] == 0),
                (mag_tab["CA N"] > 0) & (mag_tab["CA N-1"] == 0),
                (mag_tab["CA N"] == 0) & (mag_tab["CA N-1"] > 0),
                mag_tab["Évolution %"] <= -20,
                mag_tab["Évolution %"] < 0,
            ],
            ["\u26ab Aucun CA", "\U0001f7e2 Nouveau", "\U0001f534 Sorti",
             "\U0001f534 Déclin fort", "\U0001f7e1 Déclin"],
            default="\U0001f7e2 Croissance",
        )
        # Réseau strictement identifié (hors dossiers non rattachés à un point de vente)
        _hors_reseau = mag_tab["Magasin"].isin(["Magasin non renseigné"]) | mag_tab["Magasin"].str.startswith("Code ", na=False)
        mag_net = mag_tab[~_hors_reseau].copy()
        mag_net_tot = float(mag_net["CA N"].sum())
        if mag_net_tot > 0:
            mag_net["Poids net %"] = (mag_net["CA N"] / mag_net_tot * 100).round(1)
            mag_net["Poids net cumulé %"] = mag_net["Poids net %"].cumsum().round(1)
        else:
            mag_net["Poids net %"] = 0.0
            mag_net["Poids net cumulé %"] = 0.0
        top3_poids = float(mag_net.head(3)["Poids net %"].sum()) if len(mag_net) > 0 else 0.0
        cm1, cm2 = st.columns(2)
        with cm1:
            st.plotly_chart(
                chart_grouped_bar(
                    ens_cmp, "Enseigne", "CA N", "CA N-1",
                    f"CA par enseigne — {mut_yr} vs {mut_yr-1}", mut_yr,
                ),
                use_container_width=True,
            )
        with cm2:
            top10 = mag_net.head(10).sort_values("CA N")
            fig_top = px.bar(
                top10, x="CA N", y="Magasin", orientation="h",
                title=f"Top 10 magasins — {mut_yr}",
                color="CA N", color_continuous_scale=["#1D4ED8", "#3B82F6", "#60A5FA"], text_auto=".0f",
            )
            fig_top.update_layout(height=380, yaxis=dict(autorange="reversed"))
            fig_top.update_traces(textposition="outside")
            st.plotly_chart(fig_top, use_container_width=True)

        # ── Concentration (Pareto) ───────────────────────────
        if mag_net_tot > 0 and len(mag_net) > 0:
            par = mag_net.head(15).copy()
            fig_par = go.Figure()
            fig_par.add_bar(
                x=par["Magasin"], y=par["CA N"], name=f"CA {mut_yr}", marker_color=C["blue"],
                text=[f"{v/1e3:,.0f}k" for v in par["CA N"]], textposition="outside", textfont_size=9,
            )
            fig_par.add_scatter(
                x=par["Magasin"], y=par["Poids net cumulé %"], name="Poids cumulé %", mode="lines+markers",
                line=dict(color=C["amber"], width=3), marker=dict(size=7), yaxis="y2",
            )
            fig_par.update_layout(
                template="plotly_white", height=430,
                title=f"Concentration du CA — top 15 magasins ({mut_yr})",
                yaxis=dict(title="CA TTC (TND)"),
                yaxis2=dict(title="Poids cumulé %", overlaying="y", side="right",
                            range=[0, 105], showgrid=False),
                legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center", yanchor="bottom"),
                margin=dict(l=16, r=16, t=70, b=16),
                font=dict(family="DM Sans, Figtree, sans-serif", color=C["ink"], size=13),
            )
            fig_par.update_xaxes(tickangle=-30)
            st.plotly_chart(fig_par, use_container_width=True)
        else:
            st.info("Aucun CA magasin sur la période sélectionnée.")

        # ── Mouvements par magasin (top hausses / baisses) ───
        var_src = mag_net[(mag_net["CA N"] > 0) & (mag_net["CA N-1"] > 0)].copy()
        if len(var_src) > 0:
            var_src = var_src.sort_values("Évolution %")
            var_show = pd.concat([var_src.head(8), var_src.tail(8)]).drop_duplicates(subset=["Magasin"])
            st.plotly_chart(
                chart_variation_bar(
                    var_show, "Magasin", "Évolution %",
                    f"Mouvements de CA par magasin — {mut_yr} vs {mut_yr-1}",
                ),
                use_container_width=True,
            )
        else:
            st.info("Historique insuffisant pour calculer les évolutions par magasin.")

        with st.expander("\U0001f4cb Tableau détaillé du réseau magasins"):
            if len(mag_tab) > 0:
                disp = mag_tab[
                    ["Magasin", "Statut", "CA N", "CA N-1", "Évolution %", "Dossiers",
                     "Adhérents", "Panier moyen", "Poids %", "Poids cumulé %"]
                ].rename(columns={"CA N": f"CA {mut_yr}", "CA N-1": f"CA {mut_yr-1}"})
                st.dataframe(
                    disp.style.format({
                        f"CA {mut_yr}": "{:,.0f}", f"CA {mut_yr-1}": "{:,.0f}",
                        "Évolution %": "{:+.1f}%", "Panier moyen": "{:,.0f}",
                        "Poids %": "{:.1f}%", "Poids cumulé %": "{:.1f}%",
                    }, na_rep="—"),
                    use_container_width=True, height=420,
                )
            else:
                st.info("Aucun magasin sur la période sélectionnée.")

        # ── Mouvements du réseau (entrées / sorties) ─────────
        _mag_new = mag_net[mag_net["Statut"].str.contains("Nouveau", na=False)].sort_values("CA N", ascending=False)
        _mag_out = mag_net[mag_net["Statut"].str.contains("Sorti", na=False)].sort_values("CA N-1", ascending=False)
        mvn, mvs = st.columns(2)
        with mvn:
            st.markdown(f"#### \U0001f195 Magasins actifs nouveaux — {mut_yr}")
            if len(_mag_new) > 0:
                for _, r in _mag_new.head(8).iterrows():
                    st.markdown(f"- **{r['Magasin']}** — {r['CA N']:,.0f} TND · {int(r['Dossiers'])} dossier(s)")
                if len(_mag_new) > 8:
                    st.caption(f"… et {len(_mag_new) - 8} autre(s) magasin(s), "
                               f"soit {_mag_new['CA N'].sum():,.0f} TND au total.")
            else:
                st.caption("Aucun magasin nouveau sur la période.")
        with mvs:
            st.markdown(f"#### \U0001f6aa Magasins sans activité — {mut_yr}")
            if len(_mag_out) > 0:
                for _, r in _mag_out.head(8).iterrows():
                    st.markdown(f"- **{r['Magasin']}** — {r['CA N-1']:,.0f} TND en {mut_yr-1}")
                if len(_mag_out) > 8:
                    st.caption(f"… et {len(_mag_out) - 8} autre(s) magasin(s), "
                               f"soit {_mag_out['CA N-1'].sum():,.0f} TND de CA perdu.")
            else:
                st.caption("Aucun magasin sorti : le réseau actif est stable.")
        # ══ NIVEAU 3 · DÉTAIL — adhérents & fidélisation ═════
        section("4 · Adhérents & fidélisation")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Adhérents actifs", f"{adh_n:,}", _delta(adh_n, adh_n1),
                  delta_color="normal" if adh_n >= adh_n1 else "inverse")
        a2.metric("Nouveaux adhérents", f"{len(nouveaux):,}",
                  help="Acquisition : adhérents actifs cette période, absents de la même période en N-1.")
        a3.metric("Adhérents non reconduits", f"{len(non_reconduits):,}",
                  help="À reconquérir : actifs sur la même période en N-1, sans dossier cette période.")
        a4.metric("Adhérents fidèles (≥ 2 dossiers)", f"{adh_fideles:,} / {adh_hist:,}",
                  help=f"Taux de récurrence historique du compte : {taux_recur:.1f}%.")

        adh_tab = (
            mut_n.groupby(["Adhérent ID", "Adhérent"])
            .agg(CA_N=("Montant TTC", "sum"), Dossiers=("Dossier", "nunique"))
            .reset_index().rename(columns={"CA_N": "CA N"})
        )
        _adh_n1 = mut_n1.groupby("Adhérent ID")["Montant TTC"].sum().rename("CA N-1").reset_index()
        adh_tab = adh_tab.merge(_adh_n1, on="Adhérent ID", how="left")
        adh_tab["CA N-1"] = adh_tab["CA N-1"].fillna(0.0)
        adh_tab = adh_tab.sort_values("CA N", ascending=False).reset_index(drop=True)
        adh_tot = float(adh_tab["CA N"].sum())
        adh_tab["Poids %"] = (adh_tab["CA N"] / adh_tot * 100).round(2) if adh_tot > 0 else 0.0
        adh_tab["Statut"] = np.where(
            adh_tab["Adhérent ID"].isin(nouveaux),
            "\U0001f7e2 Nouveau",
            "\U0001f501 Déjà adhérent en " + str(mut_yr - 1),
        )
        top10_adh_poids = float(adh_tab.head(10)["Poids %"].sum()) if len(adh_tab) > 0 else 0.0

        ca1, ca2 = st.columns([3, 2])
        with ca1:
            if len(adh_tab) > 0:
                top_adh = adh_tab.head(10).sort_values("CA N")[["Adhérent", "CA N"]]
                st.plotly_chart(
                    chart_bar(top_adh, "CA N", "Adhérent",
                              f"Top 10 adhérents — {mut_yr}", C["purple"], 400, orientation="h"),
                    use_container_width=True,
                )
            else:
                st.info("Aucun adhérent sur la période sélectionnée.")
        with ca2:
            st.markdown(f"#### Concentration adhérents — {mut_yr}")
            st.markdown(
                f"- Top 10 adhérents : **{top10_adh_poids:.1f}%** du CA du compte "
                f"({adh_tab.head(10)['CA N'].sum():,.0f} TND)\n"
                f"- CA moyen par adhérent actif : **{ca_adh_n:,.0f} TND**\n"
                f"- Dossiers uniques : **{max(adh_hist - adh_fideles, 0):,}** adhérents sur {adh_hist:,} "
                f"(taux de récurrence **{taux_recur:.1f}%**)"
            )
            if len(adh_tab) > 0 and top10_adh_poids < 20:
                st.info("CA très atomisé côté adhérents : la performance se pilote par le réseau magasins, "
                        "pas par un portefeuille de comptes clés.")

        with st.expander("\U0001f4cb Tableau des adhérents (top 50 par CA)"):
            if len(adh_tab) > 0:
                adh_disp = adh_tab.head(50)[
                    ["Adhérent", "Adhérent ID", "Statut", "CA N", "CA N-1", "Dossiers", "Poids %"]
                ].rename(columns={"CA N": f"CA {mut_yr}", "CA N-1": f"CA {mut_yr-1}",
                                  "Adhérent ID": "N° client"})
                st.dataframe(
                    adh_disp.style.format({
                        f"CA {mut_yr}": "{:,.0f}", f"CA {mut_yr-1}": "{:,.0f}", "Poids %": "{:.2f}%",
                    }, na_rep="—"),
                    use_container_width=True, height=420,
                )
            else:
                st.info("Aucun adhérent sur la période sélectionnée.")
        # ══ NIVEAU 3 · DÉTAIL — recouvrement & qualité ═══════
        section("5 · Recouvrement & qualité des données")
        _annules = mut[mut["_annule"]]
        _ech_vals = pd.to_numeric(mut[_col_ech], errors="coerce") if _col_ech else pd.Series(dtype="float64")
        _ech_zero = int(_ech_vals.fillna(0).eq(0).sum()) if _col_ech else len(mut)
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Dossiers non clôturés", f"{len(nonclot):,}",
                  help="Sur l'ensemble de l'historique du compte, tous millésimes confondus.")
        r2.metric("Encours ouvert", f"{encours:,.0f} TND",
                  help="Somme de la colonne « Montant ouvert » des dossiers non clôturés.")
        r3.metric("Dossiers annulés", f"{len(_annules):,}",
                  f"{_annules['Montant TTC'].sum():,.0f} TND" if len(_annules) > 0 else None)
        r4.metric("Échéances renseignées", f"{len(mut) - _ech_zero:,} / {len(mut):,}",
                  help=f"Colonne « {_col_ech or 'Nbr_Mois_Echance'} » : quasi-totalité des dossiers à 0 "
                       "\u2192 risque d'amortissement non analysable en l'état.")

        with st.expander("\U0001f6a8 Dossiers non clôturés — suivi recouvrement"):
            if len(nonclot) > 0:
                nc_disp = nonclot[["Date", "Dossier", "Adhérent", "Magasin", "Montant TTC", "Montant ouvert"]].copy()
                nc_disp["Date"] = pd.to_datetime(nc_disp["Date"], errors="coerce").dt.strftime("%d/%m/%Y")
                st.dataframe(
                    nc_disp.rename(columns={"Dossier": "N° facture", "Montant TTC": "Montant facturé",
                                            "Montant ouvert": "Reste à amortir"})
                    .style.format({"Montant facturé": "{:,.0f}", "Reste à amortir": "{:,.0f}"}, na_rep="—"),
                    use_container_width=True, height=320,
                )
                st.caption(f"Encours total à suivre : **{encours:,.0f} TND** sur {len(nonclot)} dossier(s).")
            else:
                st.success("Aucun dossier en cours : tous les dossiers du compte sont clôturés.")

        with st.expander("\U0001f9ea Qualité des données du compte"):
            _q_absent = mut[mut["Magasin"] == "Magasin non renseigné"]
            _q_non_mappe = mut[(mut["Magasin"].str.startswith("Code "))
                               & (mut["Magasin"].str.contains("non mappé"))]
            _frais = (
                pd.to_numeric(mut["Frais Dossier"], errors="coerce").fillna(0)
                if "Frais Dossier" in mut.columns else pd.Series([0.0])
            )
            q_tot = float(mut["Montant TTC"].sum())
            q_rows = pd.DataFrame([
                {"Point de contrôle": "Dossiers sans magasin renseigné (code source absent)",
                 "Dossiers": int(_q_absent["Dossier"].nunique()),
                 "CA concerné": float(_q_absent["Montant TTC"].sum())},
                {"Point de contrôle": "Dossiers avec code magasin non mappé",
                 "Dossiers": int(_q_non_mappe["Dossier"].nunique()),
                 "CA concerné": float(_q_non_mappe["Montant TTC"].sum())},
                {"Point de contrôle": "Durée d'échéance non renseignée (valeur 0)",
                 "Dossiers": int(_ech_zero),
                 "CA concerné": float(mut["Montant TTC"].sum())},
                {"Point de contrôle": "Frais de dossier non valorisés (colonne nulle)",
                 "Dossiers": int(len(mut)),
                 "CA concerné": float(_frais.sum())},
                {"Point de contrôle": "Dossiers annulés",
                 "Dossiers": int(len(_annules)),
                 "CA concerné": float(_annules["Montant TTC"].sum())},
            ])
            q_rows["Part du CA"] = (q_rows["CA concerné"] / q_tot * 100).round(2) if q_tot > 0 else 0.0
            st.dataframe(
                q_rows.style.format({"Dossiers": "{:,.0f}", "CA concerné": "{:,.0f}", "Part du CA": "{:.2f}%"}),
                use_container_width=True, hide_index=True,
            )
            st.caption(
                f"Base analysée : {len(mut):,} dossiers · {q_tot:,.0f} TND · "
                f"{adh_hist:,} adhérents uniques · {mut['Magasin'].nunique():,} points de vente distincts."
            )
        # ══ NIVEAU 4 · DÉCISION — synthèse automatique ═══════
        section("6 · Synthèse & recommandations")
        insights = []

        if ca_n1 > 0:
            _sens = "en croissance" if ca_n >= ca_n1 else "en recul"
            insights.append(
                f"**Tendance globale** : CA {_sens} de **{abs(evol_pct(ca_n, ca_n1)):.1f}%** vs {mut_yr-1} "
                f"({ca_n:,.0f} TND contre {ca_n1:,.0f} TND, comparés date à date)."
            )
        elif ca_n > 0:
            insights.append(
                f"**Tendance globale** : activité nouvelle en {mut_yr} ({ca_n:,.0f} TND) — "
                f"aucune donnée comparable en {mut_yr-1}."
            )

        if adh_n > 0 or adh_n1 > 0:
            insights.append(
                f"**Adhérents** : {adh_n:,} actifs vs {adh_n1:,} sur la même période en {mut_yr-1} "
                f"({evol_pct(adh_n, adh_n1):+.1f}%) — {len(nouveaux):,} nouveaux, "
                f"{len(non_reconduits):,} non reconduits."
            )

        if adh_hist > 0:
            if taux_recur < 10:
                insights.append(
                    f"**Fidélisation** : seulement {adh_fideles:,} adhérents sur {adh_hist:,} ont réalisé "
                    f"≥ 2 dossiers (taux de récurrence {taux_recur:.1f}%) — offre essentiellement mono-achat."
                )
            else:
                insights.append(
                    f"**Fidélisation** : taux de récurrence de {taux_recur:.1f}% "
                    f"({adh_fideles:,} adhérents avec ≥ 2 dossiers sur {adh_hist:,})."
                )

        if len(mag_net) > 0 and mag_net_tot > 0:
            _top1 = mag_net.iloc[0]
            insights.append(
                f"**Meilleur magasin** : {_top1['Magasin']} — {_top1['CA N']:,.0f} TND "
                f"({_top1['Poids net %']:.1f}% du CA réseau du compte)."
            )
            insights.append(
                f"**Concentration réseau** : top 3 magasins = {top3_poids:.1f}% du CA réseau — "
                + ("\u26a0\ufe0f forte dépendance à quelques points de vente."
                   if top3_poids > 50 else "répartition relativement équilibrée.")
            )

        _delta_mag = pd.DataFrame()
        if len(mag_net) > 0:
            _delta_mag = mag_net[mag_net["CA N"] > 0][["Magasin", "CA N", "CA N-1"]].copy()
            _delta_mag["Delta CA"] = _delta_mag["CA N"] - _delta_mag["CA N-1"]
        if len(_delta_mag) > 0:
            _up = _delta_mag.nlargest(1, "Delta CA").iloc[0]
            _down = _delta_mag.nsmallest(1, "Delta CA").iloc[0]
            if _up["Delta CA"] > 0:
                insights.append(
                    f"**Moteur de croissance** : {_up['Magasin']} apporte {_up['Delta CA']:+,.0f} TND vs {mut_yr-1}."
                )
            if _down["Delta CA"] < 0:
                insights.append(
                    f"**Point de vigilance** : {_down['Magasin']} recule de {abs(_down['Delta CA']):,.0f} TND "
                    f"({_down['CA N']:,.0f} TND en {mut_yr})."
                )

        if len(_mag_new) > 0 or len(_mag_out) > 0:
            insights.append(
                f"**Dynamique du réseau** : {len(_mag_new)} magasin(s) nouveau(x) actif(s) "
                f"({_mag_new['CA N'].sum():,.0f} TND) et {len(_mag_out)} magasin(s) sans activité en {mut_yr} "
                f"({_mag_out['CA N-1'].sum():,.0f} TND en {mut_yr-1})."
            )

        _mens = mut_n.groupby("Mois")["Montant TTC"].sum() if len(mut_n) > 0 else pd.Series(dtype="float64")
        if len(_mens) > 0:
            _bm, _wm = int(_mens.idxmax()), int(_mens.idxmin())
            insights.append(
                f"**Saisonnalité** : meilleur mois = {MOIS.get(_bm, _bm)} ({_mens.max():,.0f} TND), "
                f"plus faible = {MOIS.get(_wm, _wm)} ({_mens.min():,.0f} TND)."
            )

        if _cc_n > 0:
            insights.append(
                f"**Place dans le crédit conso** : {part_n:.2f}% du CA crédit conso en {mut_yr}"
                + (f" ({part_n - part_n1:+.2f} pts vs {mut_yr-1})." if part_n1 > 0 else ".")
            )

        insights.append(
            f"**Recouvrement** : {len(nonclot)} dossier(s) non clôturé(s) pour {encours:,.0f} TND d'encours ouvert"
            + (" (tous millésimes confondus)." if len(nonclot) > 0 else " — compte intégralement clôturé.")
        )

        if len(_q_absent) > 0 or len(_q_non_mappe) > 0:
            insights.append(
                f"**Qualité de données** : {int(_q_absent['Dossier'].nunique())} dossier(s) sans magasin renseigné "
                f"et {int(_q_non_mappe['Dossier'].nunique())} avec un code magasin non mappé — à corriger à la source "
                "(impact direct sur l'analyse réseau)."
            )

        if mois_sel and ca_n_annee > 0 and abs(ca_n_annee - ca_n) > 1:
            insights.append(
                f"**Périmètre** : analyse limitée aux mois "
                f"{', '.join(MOIS.get(m, str(m)) for m in sorted(mois_sel))} — CA {mut_yr} toutes périodes "
                f"confondues : {ca_n_annee:,.0f} TND."
            )
        recos = []
        _ev = evol_pct(ca_n, ca_n1)
        if ca_n1 > 0 and _ev < -10:
            recos.append("Relancer commercialement le compte (rencontre direction Mutuelle, animation du réseau, "
                         "offre échéances adaptée).")
        elif ca_n1 > 0 and _ev > 5:
            recos.append("Capitaliser sur la croissance : sécuriser le réassort et dupliquer le dispositif "
                         "des magasins moteurs.")
        if top3_poids > 50:
            recos.append("Réduire la dépendance : ouvrir l'offre dans les magasins du réseau sans dossier enregistré "
                         "sur la période.")
        if adh_hist > 0 and taux_recur < 10:
            recos.append(f"Taux de récurrence de {taux_recur:.1f}% : mettre en place une relance des adhérents "
                         f"éligibles ({len(non_reconduits):,} non reconduits cette période) via le CRM.")
        if len(nonclot) > 0:
            recos.append(f"Régulariser les {len(nonclot)} dossier(s) non clôturé(s) — {encours:,.0f} TND d'encours "
                         "— avec le service recouvrement.")
        if len(mut) > 0 and _ech_zero == len(mut):
            recos.append("Fiabiliser la donnée « nombre de mois d'échéance » (100% des dossiers à 0) : "
                         "prérequis au suivi du risque d'amortissement.")
        if len(_mag_out) > 0:
            recos.append(f"Analyser les {len(_mag_out)} magasin(s) sans activité sur la période "
                         "(référencement, formation, mix produit disponible).")
        if len(_q_absent) > 0 or len(_q_non_mappe) > 0:
            recos.append("Corriger le renseignement du code magasin dans les factures (dossiers non rattachés "
                         "à un point de vente).")
        if not recos:
            recos.append("Maintenir la dynamique actuelle et sécuriser le renouvellement de la convention Mutuelle.")

        col_an1, col_an2 = st.columns([3, 2])
        with col_an1:
            st.markdown("#### \U0001f4ca Constats clés")
            for ins in insights:
                st.markdown(f"- {ins}")
        with col_an2:
            st.markdown("#### \U0001f3af Recommandations")
            for rec in recos:
                st.markdown(f"- {rec}")



# ══════════════════════════════════════════════════════════════
# TAB 6 — CONVENTIONS SMG (suivi, DSO, alertes, GPO)
# ══════════════════════════════════════════════════════════════
with tabs[6]:

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

with tabs[7]:
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

with tabs[8]:
    st.markdown("### \U0001f6a8 Alertes Tendances")
    try:
        from trend_analyzer import TrendAnalyzer
        with st.spinner("Analyse des tendances..."):
            ta = TrendAnalyzer(df_vc=df_vc, df_edc=df_edc, conventions=df_conv, code_magasin=code_df)
            alerts = ta.scan_all()
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
                    evo = round((ca_n - ca_n1) / ca_n1 * 100, 1) if ca_n1 > 0 else (100.0 if ca_n > 0 else 0.0)
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
# TAB 9 — ARCHIVE RAPPORTS
# ══════════════════════════════════════════════════════════════
with tabs[9]:
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
                        st.metric("Variation", f"{var:+.1f}%",
                                  delta_color="normal" if var >= 0 else "inverse")

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
    + (f"| Seuil inactivite: {seuil_inactif}j" if seuil_inactif != 60 else "")
)
