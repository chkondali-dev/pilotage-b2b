"""
Dashboard Pilotage B2B — SMG (MG & BATAM)
Refactored: architecture modulaire, BI décisionnel, visualisation executive
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
from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path

st.set_page_config(
    page_title="Pilotage B2B — SMG",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# SECTION 1 — CONFIGURATION
# ══════════════════════════════════════════════════════════════

GITHUB_RAW        = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"
GITHUB_RAW_IMAGES = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/"
LOGO_MG_URL       = GITHUB_RAW_IMAGES + "logo-1653837429.jpg"
LOGO_BATAM_URL    = GITHUB_RAW_IMAGES + "logo.svg"

FILES = {
    "vc":                 "Factures%20ventes%20enregistr%C3%A9es%20VC%20(4).xlsx",
    "vc_credit":          "Factures%20ventes%20enregistr%C3%A9es%20VC%20credit%20conso.xlsx",
    "vc_edc":             "Factures%20ventes%20enregistr%C3%A9es%20VC%20CONVENTION%20EDC.xlsx",
    "credit_particulier": "CREDIT%20PARTICULIER.xlsx",
    "conventions_signees": "TDC%20CONVENTION%201.xlsm",
    "code_magasin":       "Code%20MAGASIN%20Business%20Central.xlsx",
    "cube_magasin":       "CUBE%20MAGASIN.xlsx",
}

# ─── Palette sémantique ───────────────────────────────────────
# Règle stricte : vert = croissance, rouge = déclin/alerte,
# bleu = N courant, ardoise = N-1 (neutre, jamais rouge)
C = {
    "green":   "#059669",  # croissance / positif
    "red":     "#DC2626",  # déclin / alerte
    "blue":    "#1D4ED8",  # année N (valeur principale)
    "slate":   "#94A3B8",  # année N-1 (référence neutre)
    "amber":   "#D97706",  # avertissement / modéré
    "purple":  "#6D28D9",  # accent secondaire
    "ink":     "#0F172A",
    "muted":   "#64748B",
    "border":  "#E2E8F0",
    "surface": "#F8FAFC",
}

MOIS = {
    1: "Jan", 2: "Fév",  3: "Mar", 4: "Avr",
    5: "Mai", 6: "Juin", 7: "Juil",8: "Aoû",
    9: "Sep", 10:"Oct",  11:"Nov", 12:"Déc",
}

# ─── Noms individuels détectés dans la colonne `Nom` (erreurs de saisie) ──
# Ces entrées doivent être exclues des vues "Convention".
NOMS_INDIVIDUELS = {"AHMED ABIDI", "AMARA MISSAOUI", "BILEL BEN AMMAR", "MED KAIS SMAILI"}

# ══════════════════════════════════════════════════════════════
# SECTION 2 — DATA LOADING  (cache agressif)
# ══════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, ttl=3600)
def _fetch(url: str) -> bytes:
    """HTTP fetch avec cache 1h — évite les re-téléchargements."""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content

@st.cache_data(show_spinner=False, ttl=3600)
def load_all_data() -> dict:
    """Charge tous les fichiers Excel depuis GitHub, retourne un dict de DataFrames."""
    dfs: dict = {}
    for key, fname in FILES.items():
        try:
            raw = _fetch(GITHUB_RAW + fname)
            if key == "conventions_signees":
                sheets = pd.read_excel(BytesIO(raw), engine="openpyxl", sheet_name=None)
                dfs[key] = _clean(list(sheets.values())[0])
            else:
                dfs[key] = _clean(pd.read_excel(BytesIO(raw), engine="openpyxl"))
        except Exception as exc:
            st.sidebar.warning(f"⚠️ Fichier {key} : {exc}")
            dfs[key] = pd.DataFrame()
    return dfs


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.replace("\n", " ").str.strip()
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def _filter_conventions(df: pd.DataFrame) -> pd.DataFrame:
    """Exclut les entrées avec des noms individuels dans la colonne Convention."""
    if df.empty or "Nom" not in df.columns:
        return df
    return df[~df["Nom"].str.upper().str.strip().isin(NOMS_INDIVIDUELS)].copy()


# ══════════════════════════════════════════════════════════════
# SECTION 3 — DATA PROCESSING
# ══════════════════════════════════════════════════════════════

def _add_date_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Extrait Année / Mois / Jour depuis 'Date comptabilisation'."""
    # Try to find the date column case-insensitively
    date_col = next((c for c in df.columns if "date" in c.lower() and "comptabil" in c.lower()), None)
    
    if date_col is None:
        return df
    
    df = df.copy()
    df["Date"]  = pd.to_datetime(df[date_col], errors="coerce")
    df["Année"] = df["Date"].dt.year.astype("Int64")
    df["Mois"]  = df["Date"].dt.month.astype("Int64")
    df["Jour"]  = df["Date"].dt.day.astype("Int64")
    return df


def _map_magasins(df: pd.DataFrame, code_df: pd.DataFrame) -> pd.DataFrame:
    """
    Mapping code Navision → nom magasin + enseigne.
    """
    if len(df) == 0:
        return df
    
    df = df.copy()
    df["Enseigne"] = "MG"
    df["Magasin"] = "Inconnu"
    
    if code_df.empty:
        return df
    
    code_df = code_df.copy()
    code_df.columns = code_df.columns.str.strip()
    
    # Utiliser Unite Code dans VC -> Code Navision dans mapping
    code_col_src = next((c for c in df.columns if c.lower() == "unite code"), None)
    if not code_col_src:
        return df
    
    # Code Navision est la colonne 0 dans le fichier de mapping
    code_col = list(code_df.columns)[0]
    unite_col = list(code_df.columns)[2]
    
    def get_ense(unit):
        s = str(unit).upper()
        return "BATAM" if "BATAM" in s or "BTM" in s else "MG"
    
    code_df["Enseigne"] = code_df[unite_col].apply(get_ense)
    code_df[code_col] = code_df[code_col].astype(str).str.strip()
    
    mapping_nom = code_df.set_index(code_col)[unite_col].to_dict()
    mapping_ense = code_df.set_index(code_col)["Enseigne"].to_dict()
    
    df[code_col_src] = df[code_col_src].astype(str).str.strip()
    df["Magasin"] = df[code_col_src].map(mapping_nom).fillna(df[code_col_src])
    df["Enseigne"] = df[code_col_src].map(mapping_ense).fillna("MG")
    
    return df


# NOTE: _raw commence par _ → Streamlit skip le hashing de ce paramètre
@st.cache_data(show_spinner=False)
def prepare_data(_raw: dict) -> tuple:
    """
    Point d'entrée unique pour tout le processing.
    Retourne (df_vc, df_credit, df_edc, df_conv, code_df, df_credit_part).
    """
    code_df   = _raw.get("code_magasin", pd.DataFrame())
    df_vc     = _filter_conventions(_map_magasins(_add_date_cols(_raw.get("vc",       pd.DataFrame())), code_df))
    df_credit = _filter_conventions(_map_magasins(_add_date_cols(_raw.get("vc_credit", pd.DataFrame())), code_df))
    df_edc    = _map_magasins(_add_date_cols(_raw.get("vc_edc", pd.DataFrame())), code_df)
    # Renommer UNIQUEMENT la colonne avec accent aigu qui pose problème
    if "Nbr_Mois_Échance" in df_edc.columns:
        df_edc = df_edc.rename(columns={"Nbr_Mois_Échance": "Nbr_Mois_Echance"})
    df_conv   = _raw.get("conventions_signees", pd.DataFrame())
    df_credit_part = _map_magasins(_add_date_cols(_raw.get("credit_particulier", pd.DataFrame())), code_df)
    df_cube_mag = load_cube_magasin(_raw.get("cube_magasin", pd.DataFrame()), code_df)
    return df_vc, df_credit, df_edc, df_conv, code_df, df_credit_part, df_cube_mag


# ══════════════════════════════════════════════════════════════
# SECTION 4 — KPI ENGINE  (logique métier centralisée)
# ══════════════════════════════════════════════════════════════

def ca_sum(df: pd.DataFrame, annee: int, mois=None) -> float:
    d = df[df["Année"] == annee]
    if mois and isinstance(mois, list) and len(mois) > 0:
        d = d[d["Mois"].isin(mois)]
    elif mois and isinstance(mois, int):
        d = d[d["Mois"] == mois]
    return float(d["Montant TTC"].sum()) if "Montant TTC" in d.columns else 0.0


def evol_pct(n: float, n1: float) -> float:
    return round((n - n1) / n1 * 100, 1) if n1 > 0 else 0.0


def load_cube_magasin(df_raw: pd.DataFrame, code_df: pd.DataFrame = pd.DataFrame()) -> pd.DataFrame:
    """Parse CUBE MAGASIN - extract BC code, map to Unite name, melt to long format."""
    if df_raw.empty:
        return pd.DataFrame()
    df_raw = df_raw.copy()
    df_raw.columns = df_raw.columns.str.strip()
    # Find header row (row with store names)
    header_row = None
    for i, val in enumerate(df_raw.iloc[:, 0]):
        if pd.notna(val) and ("étiquettes" in str(val) or "lignes" in str(val).lower()):
            header_row = i
            break
    if header_row is None:
        return pd.DataFrame()
    # Headers are in row header_row, first column is "Date", rest are store names
    headers = df_raw.iloc[header_row].tolist()
    # Data starts after header row
    data = df_raw.iloc[header_row + 1:].copy()
    data.columns = headers
    data = data.rename(columns={headers[0]: "Date"})
    # Remove rows with NaN dates
    data = data[data["Date"].notna()].copy()
    
    # Build BC code -> Unite mapping from code_df
    bc_to_unite = {}
    if not code_df.empty:
        code_df = code_df.copy()
        bc_col = next((c for c in code_df.columns if "business" in c.lower() or "central" in c.lower()), None)
        unite_col = next((c for c in code_df.columns if c not in [bc_col, code_df.columns[0], "enseigne"] and "code" not in c.lower()), None)
        if bc_col and unite_col:
            code_df[bc_col] = pd.to_numeric(code_df[bc_col], errors="coerce")
            bc_to_unite = code_df.dropna(subset=[bc_col]).set_index(bc_col)[unite_col].to_dict()
    
    # Map store names: extract BC code prefix, map to Unite name, fallback to raw name
    def map_store_name(store_name):
        s = str(store_name).strip()
        parts = s.split(" - ")
        if len(parts) >= 1:
            try:
                bc_code = float(parts[0])
                if bc_code in bc_to_unite:
                    return bc_to_unite[bc_code].strip()
            except:
                pass
        # Fallback: try to extract store name after " - "
        if " - " in s:
            return s.split(" - ", 1)[1].strip()
        return s
    
    store_cols = [c for c in data.columns if c != "Date" and pd.notna(c)]
    data_long = data.melt(id_vars=["Date"], value_vars=store_cols, var_name="StoreRaw", value_name="CA Magasin")
    data_long["Magasin"] = data_long["StoreRaw"].apply(map_store_name)
    data_long["Date"] = pd.to_datetime(data_long["Date"], errors="coerce")
    data_long["Année"] = data_long["Date"].dt.year
    data_long["Mois"] = data_long["Date"].dt.month
    data_long = data_long.dropna(subset=["Date", "CA Magasin"])
    data_long["CA Magasin"] = pd.to_numeric(data_long["CA Magasin"], errors="coerce").fillna(0)
    return data_long[["Date", "Magasin", "CA Magasin", "Année", "Mois"]]


def ca_par_mois(df: pd.DataFrame, annee: int) -> pd.DataFrame:
    return (
        df[df["Année"] == annee]
        .groupby("Mois")["Montant TTC"].sum()
        .reset_index()
    )


def compare_years(df: pd.DataFrame, annee_n: int, annee_n1: int) -> pd.DataFrame:
    """Comparaison mensuelle N vs N-1 — produit la base de données pour les charts trends."""
    if df.empty or "Montant TTC" not in df.columns:
        return pd.DataFrame(columns=["Mois", "CA N", "CA N-1", "Variation %", "Mois Nom"])
    n  = ca_par_mois(df, annee_n).rename(columns={"Montant TTC": "CA N"})
    n1 = ca_par_mois(df, annee_n1).rename(columns={"Montant TTC": "CA N-1"})
    comp = n.merge(n1, on="Mois", how="outer").sort_values("Mois").fillna(0)
    comp["Variation %"] = (
        (comp["CA N"] - comp["CA N-1"]) / comp["CA N-1"].replace(0, 1) * 100
    ).round(1)
    comp["Mois Nom"] = comp["Mois"].map(MOIS)
    return comp


def compare_years_date_to_date(df: pd.DataFrame, annee_n: int, annee_n1: int, mois_sel: list = None) -> pd.DataFrame:
    """
    Comparaison N vs N-1 DATE À DATE (même nombre de jours).
    Si Mai 2026 a des données jusqu'au jour 7, on compare les 7 premiers jours de Mai 2025.
    """
    if df.empty or "Montant TTC" not in df.columns:
        return pd.DataFrame(columns=["Mois", "CA N", "CA N-1", "Variation %", "Mois Nom", "Jours comparés"])
    
    # Appliquer le filtre mois sur les deux années
    df_filtered = df.copy()
    if mois_sel is not None and len(mois_sel) > 0:
        df_filtered = df_filtered[df_filtered["Mois"].isin(mois_sel)]
    
    # Déterminer les mois à analyser
    df_n = df_filtered[df_filtered["Année"] == annee_n].copy()
    df_n1 = df_filtered[df_filtered["Année"] == annee_n1].copy()
    
    if "Mois" not in df_n.columns or "Jour" not in df_n.columns or df_n.empty:
        # Pas de données jour, fallback sur comparaison mensuelle classique
        return compare_years(df_filtered, annee_n, annee_n1)
    
    # Pour chaque mois, trouver le nombre max de jours disponibles en N
    max_days_per_month = df_n.groupby("Mois")["Jour"].max().to_dict()
    
    result_rows = []
    for mois in sorted(max_days_per_month.keys()):
        max_jour = max_days_per_month[mois]
        
        # Filtrer N et N-1 pour ce mois, jour <= max_jour
        ca_n = df_n[(df_n["Mois"] == mois) & (df_n["Jour"] <= max_jour)]["Montant TTC"].sum()
        ca_n1 = df_n1[(df_n1["Mois"] == mois) & (df_n1["Jour"] <= max_jour)]["Montant TTC"].sum()
        
        var_pct = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else (100 if ca_n > 0 else 0)
        
        result_rows.append({
            "Mois": mois,
            "CA N": ca_n,
            "CA N-1": ca_n1,
            "Variation %": round(var_pct, 1),
            "Mois Nom": MOIS.get(mois, str(mois)),
            "Jours comparés": max_jour
        })
    
    comp = pd.DataFrame(result_rows)
    
    return comp


def ca_sum_date_to_date(df: pd.DataFrame, annee_n: int, annee_n1: int, mois_sel: list = None) -> tuple:
    """
    Calcul CA total date à date pour les deux années.
    Retourne (CA N, CA N-1,Evolution %)
    """
    comp = compare_years_date_to_date(df, annee_n, annee_n1, mois_sel)
    if comp.empty:
        return 0, 0, 0
    
    ca_n = comp["CA N"].sum()
    ca_n1 = comp["CA N-1"].sum()
    evo = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else (100 if ca_n > 0 else 0)
    
    return ca_n, ca_n1, round(evo, 1)


def get_rolling_3m(df: pd.DataFrame) -> pd.DataFrame:
    """CA des 3 derniers mois glissants — extrait UNIQUE (supprime duplication dans tabs)."""
    now = pd.Timestamp.now()
    periods = [(now - pd.DateOffset(months=i)) for i in range(2, -1, -1)]
    masks = [(df["Année"] == p.year) & (df["Mois"] == p.month) for p in periods]
    combined = masks[0] | masks[1] | masks[2]
    d = (
        df[combined]
        .groupby(["Année", "Mois"])["Montant TTC"].sum()
        .reset_index()
    )
    d["Periode"] = d["Mois"].map(MOIS) + " " + d["Année"].astype(str)
    return d.sort_values(["Année", "Mois"])


def convention_risk_matrix(df_vc: pd.DataFrame, annee_n: int, annee_n1: int = None) -> pd.DataFrame:
    """
    Matrice risque / opportunité par convention.
    Classifie chaque convention selon CA et évolution N/N-1.
    Applique la troncature jour à jour (N-1 limité au max jour de N).
    Version vectorisée pour performance.
    """
    if annee_n1 is None:
        annee_n1 = annee_n - 1
    if df_vc.empty or "Nom" not in df_vc.columns:
        return pd.DataFrame()

    # Date-à-date : tronquer N-1 au même nombre de jours que N
    df = df_vc.copy()
    if "Jour" in df.columns:
        df_n = df[df["Année"] == annee_n]
        if not df_n.empty:
            max_days = df_n.groupby("Mois")["Jour"].max()
            for mois, max_jour in max_days.items():
                mask = (df["Année"] == annee_n1) & (df["Mois"] == mois) & (df["Jour"] > max_jour)
                df = df[~mask]

    ca_n  = df[df["Année"] == annee_n].groupby("Nom")["Montant TTC"].sum().rename("CA N")
    ca_n1 = df[df["Année"] == annee_n1].groupby("Nom")["Montant TTC"].sum().rename("CA N-1")
    mat = pd.concat([ca_n, ca_n1], axis=1).fillna(0).reset_index()
    mat["Évolution %"] = (
        (mat["CA N"] - mat["CA N-1"]) / mat["CA N-1"].replace(0, 1) * 100
    ).round(1)

    # Vectorisation au lieu de apply() pour performance
    conditions = [
        (mat["CA N"] == 0) & (mat["CA N-1"] == 0),
        mat["CA N"] == 0,
        mat["CA N-1"] == 0,
        mat["Évolution %"] <= -20,
        mat["Évolution %"] < 0,
    ]
    choices = [
        "⚫ Aucun historique",
        "🔴 Inactif",
        "🟢 Nouveau",
        "🔴 Déclin fort",
        "🟡 Déclin",
    ]
    mat["Statut"] = np.select(conditions, choices, default="🟢 Croissance")
    
    return mat.sort_values("CA N", ascending=False)


def inactive_conventions(df_vc: pd.DataFrame, threshold_days: int = 60) -> pd.DataFrame:
    """Détecte les conventions sans facture depuis N jours."""
    if df_vc.empty or "Nom" not in df_vc.columns or "Date" not in df_vc.columns:
        return pd.DataFrame()
    today = pd.Timestamp.today().normalize()
    last = df_vc.groupby("Nom")["Date"].max().reset_index()
    last.columns = ["Convention", "Dernière Facture"]
    last["Jours inactifs"] = (today - last["Dernière Facture"]).dt.days
    return (
        last[last["Jours inactifs"] > threshold_days]
        .sort_values("Jours inactifs", ascending=False)
        .reset_index(drop=True)
    )


# ══════════════════════════════════════════════════════════════
# SECTION 5 — CHART FACTORY  (fonctions réutilisables)
# ══════════════════════════════════════════════════════════════

# Layout de base appliqué à tous les graphiques
_BASE = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="white",
    font=dict(family="DM Sans, Figtree, sans-serif", color=C["ink"], size=13),
    margin=dict(l=16, r=16, t=52, b=16),
    title=dict(font=dict(size=15, color=C["ink"])),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="center", x=0.5, font=dict(size=12),
    ),
)


def _base(fig: go.Figure, h: int = 380) -> go.Figure:
    fig.update_layout(**_BASE, height=h)
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.13)", zeroline=False, tickfont=dict(size=11))
    return fig


def _empty(title: str, h: int = 380) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text="Aucune donnée disponible",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(color=C["muted"], size=14),
    )
    return _base(fig, h)


def chart_bar(
    df: pd.DataFrame, x: str, y: str, title: str,
    color: str = None, h: int = 380, orientation: str = "v",
) -> go.Figure:
    """Bar chart vertical ou horizontal avec labels automatiques."""
    color = color or C["blue"]
    if df is None or df.empty:
        return _empty(title, h)
    if orientation == "h":
        fig = px.bar(df, x=x, y=y, orientation="h", title=title,
                     color_discrete_sequence=[color], text_auto=".3s")
        fig.update_layout(yaxis=dict(autorange="reversed"))
    else:
        fig = px.bar(df, x=x, y=y, title=title,
                     color_discrete_sequence=[color], text_auto=".3s")
    fig.update_traces(textposition="outside", textfont_size=10, cliponaxis=False)
    return _base(fig, h)


def chart_grouped_bar(
    df: pd.DataFrame, x: str, y_n: str, y_n1: str,
    title: str, annee_n: int, h: int = 380,
) -> go.Figure:
    """Barres groupées N vs N-1 avec couleurs sémantiques."""
    if df is None or df.empty:
        return _empty(title, h)
    fig = go.Figure([
        go.Bar(
            x=df[x], y=df[y_n1], name=str(annee_n - 1),
            marker_color=C["slate"],
            text=[f"{v/1e3:.1f}k" for v in df[y_n1]],
            textposition="outside", textfont_size=9,
        ),
        go.Bar(
            x=df[x], y=df[y_n], name=str(annee_n),
            marker_color=C["blue"],
            text=[f"{v/1e3:.1f}k" for v in df[y_n]],
            textposition="outside", textfont_size=9,
        ),
    ])
    fig.update_layout(barmode="group", title=title)
    return _base(fig, h)


def chart_line_compare(
    df: pd.DataFrame, x: str, y_n: str, y_n1: str,
    title: str, annee_n: int, h: int = 380,
) -> go.Figure:
    """Courbes N vs N-1 avec fill sous N."""
    if df is None or df.empty:
        return _empty(title, h)
    fig = go.Figure([
        go.Scatter(
            x=df[x], y=df[y_n1], name=str(annee_n - 1),
            mode="lines+markers",
            line=dict(color=C["slate"], width=2, dash="dot"),
            marker=dict(size=5),
        ),
        go.Scatter(
            x=df[x], y=df[y_n], name=str(annee_n),
            mode="lines+markers",
            line=dict(color=C["blue"], width=3),
            marker=dict(size=8, color=C["blue"]),
            fill="tonexty",
            fillcolor="rgba(29,78,216,0.06)",
        ),
    ])
    fig.update_layout(title=title)
    return _base(fig, h)


def chart_variation_bar(
    df: pd.DataFrame, cat_col: str, var_col: str,
    title: str, h: int = 380,
) -> go.Figure:
    """
    Barres horizontales colorées vert/rouge par signe de la variation.
    Remplace px.bar(..., color='Évol_Category') pour une sémantique plus claire.
    """
    if df is None or df.empty:
        return _empty(title, h)
    df = df.copy().sort_values(var_col)
    colors = [C["green"] if v >= 0 else C["red"] for v in df[var_col]]
    labels = [f"{v:+.1f}%" for v in df[var_col]]
    fig = go.Figure(go.Bar(
        x=df[var_col], y=df[cat_col], orientation="h",
        marker_color=colors,
        text=labels, textposition="outside", textfont_size=10,
    ))
    fig.add_vline(x=0, line_color=C["muted"], line_width=1)
    fig.update_layout(title=title, xaxis_title="Évolution %")
    return _base(fig, h)


def chart_waterfall(
    df_years: pd.DataFrame, year_col: str, val_col: str,
    title: str, h: int = 380,
) -> go.Figure:
    """Waterfall CA par année — montre l'évolution cumulée."""
    if df_years is None or df_years.empty:
        return _empty(title, h)
    df_sorted = df_years.sort_values(year_col)
    years  = df_sorted[year_col].astype(str).tolist()
    vals   = df_sorted[val_col].tolist()
    
    if not vals or len(vals) < 1:
        return _empty(title, h)
    
    deltas = [vals[0]] + [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    measure = ["absolute"] + ["relative"] * (len(deltas) - 1)
    texts = [f"{v/1e3:.0f}k" for v in deltas]

    fig = go.Figure(go.Waterfall(
        orientation="v", x=years, y=deltas, measure=measure,
        connector=dict(line=dict(color=C["muted"], width=1, dash="dot")),
        increasing=dict(marker_color=C["green"]),
        decreasing=dict(marker_color=C["red"]),
        totals=dict(marker_color=C["blue"]),
        textposition="outside", text=texts,
    ))
    fig.update_layout(title=title, showlegend=False)
    return _base(fig, h)


def chart_risk_table(
    df: pd.DataFrame, annee_n: int, title: str, h: int = 480,
) -> go.Figure:
    """
    Tableau condensé risque / opportunité - Simplifié pour directeurs
    """
    if df is None or df.empty:
        return _empty(title, h)

    # Préparer les données pour le tableau
    df_disp = df.head(20).copy()
    
    # Ajouter indicateur visuel simple
    def get_indicateur(statut):
        if "Croissance" in statut or "Nouveau" in statut:
            return "✅"
        elif "Déclin fort" in statut or "Inactif" in statut:
            return "🔴"
        elif "Déclin" in statut:
            return "🟡"
        else:
            return "⚫"
    
    df_disp["Statut"] = df_disp["Statut"].apply(get_indicateur)
    
    # Créer tableau simple
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["<b>Convention</b>", "<b>CA " + str(annee_n) + "</b>", "<b>CA " + str(annee_n-1) + "</b>", "<b>Évolution</b>", "<b>Statut</b>"],
            fill_color=C["blue"],
            font=dict(color="white", size=12),
            align="left",
            height=35,
        ),
        cells=dict(
            values=[
                df_disp["Nom"].astype(str),
                df_disp["CA N"].apply(lambda x: f"{x:,.0f}"),
                df_disp["CA N-1"].apply(lambda x: f"{x:,.0f}"),
                df_disp["Évolution %"].apply(lambda x: f"{x:+.1f}%"),
                df_disp["Statut"],
            ],
            fill_color=[[C["surface"]] * len(df_disp)],
            font=dict(size=11),
            align="left",
            height=30,
        )
    )])
    
    fig.update_layout(
        title=title,
        height=h,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def chart_gauge(value: float, ref: float, title: str, h: int = 260) -> go.Figure:
    """Jauge d'atteinte CA N vs N-1."""
    pct   = min(max((value / ref * 100) if ref > 0 else 0, 0), 150)
    color = C["green"] if pct >= 100 else (C["amber"] if pct >= 70 else C["red"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta=dict(reference=ref, relative=True, valueformat=".1%"),
        title=dict(text=title, font=dict(size=13)),
        gauge=dict(
            axis=dict(range=[0, ref * 1.5], tickformat=",.0f"),
            bar=dict(color=color, thickness=0.28),
            bgcolor="white",
            borderwidth=0,
            steps=[
                dict(range=[0,         ref * 0.7],  color="rgba(220,38,38,0.06)"),
                dict(range=[ref * 0.7, ref],         color="rgba(217,119,6,0.06)"),
                dict(range=[ref,       ref * 1.5],   color="rgba(5,150,105,0.08)"),
            ],
            threshold=dict(
                line=dict(color=C["muted"], width=2),
                thickness=0.8, value=ref,
            ),
        ),
        number=dict(suffix=" TND", valueformat=",.0f"),
    ))
    fig.update_layout(template="plotly_white", height=h, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def chart_pie(values, names, title: str, h: int = 340) -> go.Figure:
    fig = px.pie(
        values=values, names=names, title=title, hole=0.42,
        color_discrete_sequence=[C["blue"], C["green"], C["amber"], C["purple"]],
    )
    fig.update_traces(textinfo="percent+label", textfont_size=12, pull=[0.04] * len(values))
    return _base(fig, h)


def chart_inactive_bar(df: pd.DataFrame, title: str, h: int = 380) -> go.Figure:
    """Barres horizontales d'inactivité, dégradé amber→rouge selon l'ancienneté."""
    if df is None or df.empty:
        return _empty(title, h)
    df = df.copy().head(20)
    colors = df["Jours inactifs"].apply(
        lambda d: C["red"] if d > 90 else (C["amber"] if d > 60 else "#F97316")
    ).tolist()
    fig = go.Figure(go.Bar(
        x=df["Jours inactifs"], y=df["Convention"],
        orientation="h",
        marker_color=colors,
        text=[f"{d}j" for d in df["Jours inactifs"]],
        textposition="outside", textfont_size=10,
    ))
    fig.update_layout(
        title=title,
        yaxis=dict(autorange="reversed"),
        xaxis_title="Jours sans facture",
    )
    return _base(fig, max(300, len(df) * 28))


# ══════════════════════════════════════════════════════════════
# SECTION 6 — UI COMPONENTS  (CSS + helpers)
# ══════════════════════════════════════════════════════════════

def inject_css():
    st.markdown(f"""
    <style>
    /* ── Typographie Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Figtree:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}

    /* ── Fond global ── */
    .stApp {{
        background:
            radial-gradient(ellipse at 0% 0%, rgba(29,78,216,0.08) 0%, transparent 40%),
            radial-gradient(ellipse at 100% 0%, rgba(5,150,105,0.08) 0%, transparent 40%),
            linear-gradient(180deg, #f0f4ff 0%, #f7fafc 55%, #eef7f5 100%);
    }}
    .block-container {{ padding: 1rem 2rem 3rem; max-width: 1400px; }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0a0f1e 0%, #0f2040 60%, #0d2e28 100%);
        border-right: 1px solid rgba(255,255,255,0.05);
    }}
    [data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
    [data-testid="stSidebar"] label {{ color: #94a3b8 !important; font-size: 0.78rem !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 0.05em; }}
    [data-testid="stSidebar"] .stButton>button {{
        background: linear-gradient(135deg, #14b8a6 0%, #0f766e 100%);
        border: none; border-radius: 10px; font-weight: 700;
        color: white !important; width: 100%; margin-top: 8px;
        padding: 0.5rem; transition: opacity .2s;
    }}
    [data-testid="stSidebar"] .stButton>button:hover {{ opacity: 0.88; }}

    /* ── Metrics ── */
    [data-testid="stMetric"] {{
        background: rgba(255,255,255,0.92);
        border: 1px solid {C["border"]};
        border-radius: 16px;
        padding: 0.9rem 1.1rem;
        box-shadow: 0 2px 12px rgba(15,23,42,0.06);
        transition: box-shadow .2s;
    }}
    [data-testid="stMetric"]:hover {{ box-shadow: 0 6px 24px rgba(15,23,42,0.10); }}
    [data-testid="metric-container"] > div:first-child {{
        font-size: 0.72rem; font-weight: 700; color: {C["muted"]};
        text-transform: uppercase; letter-spacing: 0.07em;
    }}
    [data-testid="metric-container"] > div:nth-child(2) {{
        font-size: 1.6rem; font-weight: 800; color: {C["ink"]}; line-height: 1.1;
    }}

    /* ── Charts ── */
    div[data-testid="stPlotlyChart"] {{
        background: rgba(255,255,255,0.88);
        border: 1px solid {C["border"]};
        border-radius: 18px;
        padding: 0.3rem;
        box-shadow: 0 2px 14px rgba(15,23,42,0.05);
        transition: box-shadow .2s;
    }}
    div[data-testid="stPlotlyChart"]:hover {{ box-shadow: 0 8px 28px rgba(15,23,42,0.09); }}

    /* ── Expanders ── */
    [data-testid="stExpander"] summary {{
        background: rgba(248,250,252,0.85);
        border-radius: 10px;
        border: 1px solid {C["border"]};
        padding: 0.5rem 1rem;
        font-weight: 600; font-size: 0.88rem; color: {C["ink"]};
    }}

    /* ── Expander dans la sidebar : fond clair lisible ── */
    [data-testid="stSidebar"] [data-testid="stExpander"] {{
        background: rgba(255,255,255,0.10);
        border-radius: 12px;
        padding: 2px;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.08);
        color: #f1f5f9 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        background: #f8fafc;
        border-radius: 0 0 10px 10px;
        padding: 8px 12px 4px;
        margin-top: -2px;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] * {{
        color: #1e293b !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] label {{
        color: #475569 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] .stCaption {{
        color: #64748b !important;
    }}
    /* Selectboxes dans l'expander */
    [data-testid="stSidebar"] [data-testid="stExpander"] div[data-baseweb="select"] > div {{
        background: white !important;
        border: 1px solid #cbd5e1 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] div[data-baseweb="select"] * {{
        color: #1e293b !important;
    }}

    /* ── Tabs ── */
    [data-testid="stTabs"] button[role="tab"] {{
        border-radius: 11px; padding: 0.45rem 0.9rem;
        font-weight: 600; font-size: 0.88rem;
        background: rgba(255,255,255,0.6);
        border: 1px solid rgba(148,163,184,0.18);
        margin-right: 4px; transition: all .15s;
    }}
    [data-testid="stTabs"] button[aria-selected="true"] {{
        background: linear-gradient(135deg, rgba(29,78,216,0.11) 0%, rgba(5,150,105,0.12) 100%);
        border-color: rgba(29,78,216,0.26);
        color: {C["ink"]} !important; font-weight: 700;
    }}

    /* ── Hero banner ── */
    .hero {{
        background: linear-gradient(135deg, #0a0f1e 0%, #1a3060 52%, #0d3d34 100%);
        border-radius: 22px; padding: 1.6rem 2rem;
        color: white; margin-bottom: 1.4rem;
        box-shadow: 0 16px 48px rgba(10,15,30,0.18);
        position: relative; overflow: hidden;
    }}
    .hero::before, .hero::after {{
        content:""; position:absolute; border-radius:50%;
        background: rgba(255,255,255,0.04);
    }}
    .hero::before {{ width:300px; height:300px; right:-80px; top:-80px; }}
    .hero::after  {{ width:180px; height:180px; left:40%; bottom:-60px; }}
    .hero-tag {{
        display:inline-block; padding:3px 12px; border-radius:99px;
        background:rgba(255,255,255,0.10); border:1px solid rgba(255,255,255,0.12);
        font-size:0.68rem; font-weight:800; letter-spacing:0.12em;
        text-transform:uppercase; margin-bottom:0.75rem;
    }}
    .hero-title {{ font-family:'Figtree',sans-serif; font-size:1.95rem; font-weight:800; margin:0; line-height:1.1; }}
    .hero-sub   {{ font-size:0.9rem; color:rgba(255,255,255,0.72); margin:0.5rem 0 0; max-width:680px; }}
    .hero-chips {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:1rem; }}
    .hero-chip  {{
        padding:4px 12px; border-radius:99px;
        background:rgba(255,255,255,0.09); border:1px solid rgba(255,255,255,0.10);
        font-size:0.78rem; font-weight:500;
    }}

    /* ── Section headers ── */
    .sec-hdr {{
        font-size:0.72rem; font-weight:800; color:{C["muted"]};
        text-transform:uppercase; letter-spacing:0.10em;
        margin:1.6rem 0 0.8rem; padding-bottom:5px;
        border-bottom:2px solid {C["border"]};
    }}

    /* ── Alert / status badges ── */
    .badge {{
        display:inline-flex; align-items:center; gap:5px;
        padding:4px 12px; border-radius:99px;
        font-weight:700; font-size:0.80rem;
    }}
    .b-red    {{ background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; }}
    .b-amber  {{ background:#fffbeb; color:#92400e; border:1px solid #fde68a; }}
    .b-green  {{ background:#f0fdf4; color:#166534; border:1px solid #bbf7d0; }}
    .b-blue   {{ background:#eff6ff; color:#1e40af; border:1px solid #bfdbfe; }}

    /* ── Convention rank cards ── */
    .rank-card {{
        border-radius:14px; padding:11px 14px; margin-bottom:8px;
        transition: transform .15s;
    }}
    .rank-card:hover {{ transform: translateX(3px); }}
    .rank-top  {{ background:linear-gradient(135deg,#f0fdf4,#dcfce7); border:1px solid #86efac; }}
    .rank-flop {{ background:linear-gradient(135deg,#fff7ed,#ffedd5); border:1px solid #fdba74; }}
    .rank-num  {{ font-size:0.65rem; font-weight:800; margin-bottom:4px; }}
    .rank-name {{ font-weight:700; color:{C["ink"]}; font-size:0.88rem; line-height:1.2; }}
    .rank-val  {{ font-weight:800; font-size:1.05rem; margin-top:4px; }}
    .rank-top  .rank-num {{ color:#16a34a; }}
    .rank-top  .rank-val {{ color:#15803d; }}
    .rank-flop .rank-num {{ color:#ea580c; }}
    .rank-flop .rank-val {{ color:#c2410c; }}
    </style>
    """, unsafe_allow_html=True)


def hero(title: str, subtitle: str, chips: list):
    chips_html = "".join(f"<span class='hero-chip'>{c}</span>" for c in chips)
    st.markdown(f"""
    <div class="hero">
      <div class="hero-tag">Pilotage Commercial B2B — SMG</div>
      <h1 class="hero-title">{title}</h1>
      <p class="hero-sub">{subtitle}</p>
      <div class="hero-chips">{chips_html}</div>
    </div>""", unsafe_allow_html=True)


def section(title: str):
    st.markdown(f"<div class='sec-hdr'>{title}</div>", unsafe_allow_html=True)


def badge(text: str, tone: str = "blue"):
    cls = {"red": "b-red", "amber": "b-amber", "green": "b-green", "blue": "b-blue"}.get(tone, "b-blue")
    st.markdown(f"<span class='badge {cls}'>{text}</span>", unsafe_allow_html=True)


def rank_card(rank: int, name: str, value: str, variant: str = "top"):
    cls = "rank-top" if variant == "top" else "rank-flop"
    label = f"#{rank} TOP" if variant == "top" else f"#{rank} FLOP"
    st.markdown(f"""
    <div class="rank-card {cls}">
      <div class="rank-num">{label}</div>
      <div class="rank-name">{name}</div>
      <div class="rank-val">{value}</div>
    </div>""", unsafe_allow_html=True)


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
    st.markdown("### 🔍 Filtres")
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
    if st.button("🔄 Actualiser"):
        st.cache_data.clear()
        st.rerun()

# ── Chargement données ────────────────────────────────────────
with st.spinner("Chargement des données…"):
    _raw = load_all_data()

df_vc, df_credit, df_edc, df_conv, code_df, df_credit_part, df_cube_mag = prepare_data(_raw)
_raw_part = _raw.get("credit_particulier", pd.DataFrame())

if df_vc.empty or "Année" not in df_vc.columns:
    st.error("⚠️ Aucune donnée VC chargée. Vérifiez la connexion GitHub.")
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
    with st.expander("📄 Rapport Mensuel IA", expanded=False):
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

df_comp     = compare_years(df_vc_filt, annee_sel, annee_sel - 1)
risk_mat    = convention_risk_matrix(df_vc_filt, annee_sel)
df_inactive = inactive_conventions(df_vc_filt, seuil_inactif)
df_3m       = get_rolling_3m(df_vc_filt)

ca_n, ca_n1, ev_nn1 = ca_sum_date_to_date(df_vc_filt, annee_sel, annee_sel - 1, mois_sel)
ca_n2 = df_vc_filt[df_vc_filt["Année"] == annee_sel - 2]["Montant TTC"].sum()
ev_n1n2 = evol_pct(ca_n1, ca_n2)

nb_actives  = df_vc_filt[df_vc_filt["Année"] == annee_sel]["Nom"].dropna().nunique() \
              if "Nom" in df_vc_filt.columns else 0
nb_total    = len(df_conv) if not df_conv.empty else 0
nb_inact    = len(df_inactive)
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
    nb_declin_fort = len(risk_mat[risk_mat["Statut"] == "🔴 Déclin fort"])
    nb_inactif_cv  = len(risk_mat[risk_mat["Statut"] == "🔴 Inactif"])
    nb_croissance  = len(risk_mat[risk_mat["Statut"].isin(["🟢 Croissance", "🟢 Nouveau"])])
else:
    nb_declin_fort = nb_inactif_cv = nb_croissance = 0

# ══════════════════════════════════════════════════════════════
# SECTION 8 — TABS
# ══════════════════════════════════════════════════════════════

tabs = st.tabs([
    "🏠 Vue Exécutive",
    "📈 CA & Tendances",
    "📋 Conventions",
    "🏪 Magasins",
    "🏫 EDC",
    "🏬 Pilotage par magasin",
    "📋 Conventions SMG",
    "🤝 CRM",
])

# ══════════════════════════════════════════════════════════════
# TAB 0 — VUE EXÉCUTIVE
# (Fusionne l'ancien ACCUEIL + DASHBOARD GLOBAL — 100% dédupliqué)
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
        f"⚠️ >{seuil_inactif}j sans facture" if nb_inact > 0 else "✅ Aucune",
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
    st.caption(f"📌 Panier min: {min_mag}  |  Panier max: {max_mag}  ({mois_label})")

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

    # ── Tableau risque simplifié + Top/Flop ────────────────────────────────
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
            st.markdown("**🏆 Top 3**")
            for i, (nom, ca) in enumerate(top3.items(), 1):
                rank_card(i, nom, f"{ca:,.0f} TND", "top")

        with col_g:
            st.markdown("**⚠️ Flop 3**")
            for i, (nom, ca) in enumerate(flop3.items(), 1):
                rank_card(i, nom, f"{ca:,.0f} TND", "flop")


# ════════════��═��═══════════════════════════════════════════════
# TAB 1 — CA & TENDANCES
# ══════════════════════════════════════════════════════
with tabs[1]:

    # ══════════════════════════════════════════════════════
    # SECTION VEILLE — DECISIONNELLE (date sélectionnable)
    # ══════════════════════════════════════════════════════
    st.markdown("### 📊 Performance veille")
    
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
    
    st.caption(f"📅 Date sélectionnée: {hier_date.strftime('%d/%m/%Y')}")
    
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
            # Essayer colonne Code Navision pour le mapping
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
    st.markdown("### 🔔 Alertes & Insights — Veille")
    
    alertes = []
    couleur_alertes = []
    
    if evo_veille < -20:
        alertes.append(f"⚠️ Baisse significative: {evo_veille:.1f}% vs N-1")
        couleur_alertes.append("inverse")
    elif evo_veille >= 0:
        alertes.append(f"✅ Belle performance: +{evo_veille:.1f}% vs N-1")
        couleur_alertes.append("normal")
    
    if panier_veille < panier_moy * 0.8:
        alertes.append(f"📉 Panier bas: {panier_veille:,.0f} TND (moy: {panier_moy:,.0f})")
        couleur_alertes.append("inverse")
    
    if not df_vc_hier.empty:
        worst = df_vc_hier[df_vc_hier["Montant TTC"] > 0].nsmallest(1, "Montant TTC")
        if len(worst) > 0:
            w_mag = worst.iloc[0]["Magasin"] if "Magasin" in worst.columns else worst.iloc[0].get("Nom", "")
            w_ca = worst.iloc[0]["Montant TTC"]
            if w_ca < 100:
                alertes.append(f"🚨 Magasin critique: {w_mag} (CA: {w_ca:,.0f})")
                couleur_alertes.append("inverse")
    
    # Check forEnseigne
    if "Enseigne" in df_vc_hier.columns:
        ca_ens = df_vc_hier.groupby("Enseigne")["Montant TTC"].sum()
        total_ca = ca_ens.sum()
        mg_pct = (ca_ens.get("MG", 0) / total_ca * 100) if total_ca > 0 else 0
        bam_pct = (ca_ens.get("BATAM", 0) / total_ca * 100) if total_ca > 0 else 0
        
        if total_ca > 0:
            if mg_pct > 80:
                alertes.append(f"⚖️ Desequilibre: MG {mg_pct:.0f}% / BATAM {bam_pct:.0f}%")
                couleur_alertes.append("inverse")
            elif bam_pct > 80:
                alertes.append(f"⚖️ Desequilibre: BATAM {bam_pct:.0f}% / MG {mg_pct:.0f}%")
                couleur_alertes.append("inverse")
    
    if not alertes:
        alertes.append("✅ Aucune alerte — veille normale")
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
        # Variation mensuelle — barres vertes/rouges
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

    # Données brutes en expander (aucun tableau visible par défaut)
    with st.expander("📄 Données brutes — CA Journalier"):
        df_jour["Variation %"] = (
            (df_jour["CA N"] - df_jour["CA N-1"]) / df_jour["CA N-1"].replace(0, 1) * 100
        ).round(1)
        st.dataframe(df_jour, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# TAB 2 — CONVENTIONS
# ══════════════════════════════════════════════════════════════
with tabs[2]:

    # ── Données agrégées portefeuille (date-à-date) ──────
    ca_total_n, ca_total_n1, ev_total = ca_sum_date_to_date(df_vc_filt, annee_sel, annee_sel - 1, mois_sel)
    nb_convs = len(risk_mat[risk_mat["CA N"] > 0]) if not risk_mat.empty else 0

    if not risk_mat.empty:
        risky = risk_mat[risk_mat["Statut"].str.contains("Déclin|Inactif", na=False)]
        nb_risky = len(risky)
    else:
        nb_risky = 0

    # ── 1. KPIs portefeuille ─────────────────────────────
    section("Portefeuille conventions — Vue synthétique")
    pk1, pk2, pk3, pk4 = st.columns(4)
    pk1.metric("📋 Conventions actives", nb_convs)
    pk2.metric("💰 CA Total N", f"{ca_total_n:,.0f} TND", f"{ev_total:+.1f}%",
               delta_color="normal" if ev_total >= 0 else "inverse")
    pk3.metric("⚠️ À risque", nb_risky, delta_color="inverse" if nb_risky > 0 else "off")
    pk4.metric("🔄 Inactives", nb_inact, delta_color="inverse" if nb_inact > 0 else "off")

    # ── 2. Top conventions ──────────────────────────────
    if not risk_mat.empty:
        top10 = risk_mat.nlargest(10, "CA N")[["Nom", "CA N", "Évolution %", "Statut"]].copy()
        top10 = top10.sort_values("CA N", ascending=True)
        fig_top = px.bar(
            top10, x="CA N", y="Nom", orientation="h",
            title="Top 10 conventions par CA",
            color="Statut", text_auto=".0f",
            color_discrete_map={
                "✅ Croissance": C["green"], "📉 Déclin": C["amber"],
                "⚠️ Déclin fort": C["red"], "🆕 Nouveau": C["blue"],
                "❌ Inactif": "#9CA3AF", "❓ Aucun historique": "#D1D5DB",
            },
            height=400,
        )
        fig_top.update_layout(xaxis_title="CA N (TND)", yaxis_title="",
                              legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)))
        fig_top.update_traces(marker=dict(line=dict(width=0.5, color="white")))
        st.plotly_chart(fig_top, use_container_width=True)

    # ── 3. Tableau des conventions (interactif) ──────────
    section("Liste des conventions")

    conv_table = risk_mat.copy() if not risk_mat.empty else pd.DataFrame()
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

        search_c = st.text_input("🔍 Filtrer par nom", placeholder="Tapez un nom de convention...", label_visibility="collapsed")
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

    all_convs = sorted(conv_table["Nom"].tolist()) if not conv_table.empty else []
    conv_detail = st.selectbox("Sélectionner une convention", all_convs, index=0) if all_convs else None

    if conv_detail:
        df_cv = df_vc_filt[df_vc_filt["Nom"] == conv_detail].copy()
        ca_cv_n, ca_cv_n1, ev_cv = ca_sum_date_to_date(df_cv, annee_sel, annee_sel - 1, mois_sel)
        nb_fact_cv = len(df_cv[df_cv["Année"] == annee_sel])
        panier_cv  = ca_cv_n / nb_fact_cv if nb_fact_cv > 0 else 0

        # Badge statut
        cv_statut = risk_mat[risk_mat["Nom"] == conv_detail]["Statut"].iloc[0] if not risk_mat.empty and conv_detail in risk_mat["Nom"].values else ""
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
            st.plotly_chart(fig_cv_g, use_container_width=True, key=f"cv_bar_{conv_detail}")

        with col_cv2:
            _df_fn  = df_cv[df_cv["Année"] == annee_sel]
            _df_fn1 = df_cv[df_cv["Année"] == annee_sel - 1]
            # Troncature date-à-date : N-1 limité au max jour de N par mois
            if "Jour" in _df_fn.columns and not _df_fn.empty:
                max_days = _df_fn.groupby("Mois")["Jour"].max()
                for mois, max_jour in max_days.items():
                    _df_fn1 = _df_fn1[~((_df_fn1["Mois"] == mois) & (_df_fn1["Jour"] > max_jour))]
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
            st.plotly_chart(fig_cum, use_container_width=True, key=f"cv_cum_{conv_detail}")

        col_cv3, col_cv4 = st.columns(2)
        with col_cv3:
            if "Magasin" in df_cv.columns:
                mag = _df_fn.groupby("Magasin")["Montant TTC"].sum().nlargest(10).reset_index()
                if not mag.empty:
                    fig_mag_cv = chart_bar(
                        mag, "Montant TTC", "Magasin",
                        "Top Magasins", C["purple"], h=360, orientation="h",
                    )
                    st.plotly_chart(fig_mag_cv, use_container_width=True, key=f"cv_mag_{conv_detail}")
                else:
                    st.info("Aucun magasin avec des transactions en N pour cette convention.")

        with col_cv4:
            ca_cash   = _df_fn["Montant TTC"].sum() if len(_df_fn) > 0 else 0
            ca_credit = (df_credit[df_credit["Nom"] == conv_detail]["Montant TTC"].sum()
                         if "Nom" in df_credit.columns else 0)
            if ca_cash > 0 or ca_credit > 0:
                fig_pie_cv = chart_pie([ca_cash, ca_credit], ["Cash", "Crédit"],
                                       f"Cash vs Crédit — {conv_detail}")
                st.plotly_chart(fig_pie_cv, use_container_width=True, key=f"cv_pie_{conv_detail}")

        # ── Magasins contributeurs ──────────────────────────
        st.markdown("### 🏪 Magasins contributeurs")
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

        all_stores = sorted(_base_n["Magasin"].dropna().unique()) if "Magasin" in _base_n.columns else []

        # ── Recherche ──────────────────────────────────────────────
        col_search, col_reset = st.columns([5, 1])
        with col_search:
            search_term = st.text_input("🔍 Filtre magasin", placeholder="Tapez pour chercher...", label_visibility="collapsed")
        with col_reset:
            st.markdown("###")
            if st.button("🔄 Réinitialiser", use_container_width=True):
                st.session_state.pop("store_selector", None)
                st.rerun()

        filtered_stores = [s for s in all_stores if search_term.lower() in s.lower()] if search_term else all_stores[:50]
        options = ["Tous"] + filtered_stores

        selected_store = st.selectbox(
            "Magasin", options, index=0, key="store_selector",
            format_func=lambda x: "🌐 Tous les magasins" if x == "Tous" else f"🏪 {x}",
            label_visibility="collapsed",
        )

        # ────────────────────────────────────────────────────────────
        # VUE RÉSEAU
        # ────────────────────────────────────────────────────────────
        if selected_store == "Tous":
            ca_mag_n  = _base_n.groupby("Magasin")["Montant TTC"].sum().rename("CA N")
            ca_mag_n1 = _base_n1.groupby("Magasin")["Montant TTC"].sum().rename("CA N-1")
            ca_mag = pd.concat([ca_mag_n, ca_mag_n1], axis=1).fillna(0).reset_index()

            # Correction : évite replace(0,1) qui donne des % aberrants quand N-1=0
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

            # Correction : poids = part de chaque magasin dans le CA N total du portefeuille
            total_n = ca_mag["CA N"].sum()
            ca_mag["Poids %"] = (ca_mag["CA N"] / total_n * 100).round(1) if total_n > 0 else 0.0

            ca_mag = ca_mag.sort_values("CA N", ascending=False)
            simple_sum = _base_n["Montant TTC"].sum()

            # KPIs
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("🏪 Magasins actifs", len(ca_mag[ca_mag["CA N"] > 0]))
            k2.metric("💰 CA Total Conventions", f"{simple_sum:,.0f} TND")
            k3.metric("📈 En croissance", len(ca_mag[ca_mag["Evolution %"] > 0]), f"/ {len(ca_mag)}")
            k4.metric("📉 En baisse", len(ca_mag[ca_mag["Evolution %"] < 0]))

            # Top 20 + Évolution
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                top20 = ca_mag.head(20)
                fig_top = px.bar(top20, x="CA N", y="Magasin", orientation="h",
                                title=f"Top 20 — CA {annee_sel}", color="CA N",
                                color_continuous_scale=["#1D4ED8", "#3B82F6", "#60A5FA"], text_auto=".0f")
                fig_top.update_layout(height=400, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_top, use_container_width=True)
            with col_m2:
                fig_evo = px.bar(top20, x="Evolution %", y="Magasin", orientation="h",
                               title="Évolution N/N-1", color="Evolution %",
                               color_continuous_scale=["#DC2626", "#FCD34D", "#059669"], text_auto="+.1f")
                fig_evo.update_layout(height=400, yaxis=dict(autorange="reversed"))
                fig_evo.add_vline(x=0, line_dash="dash", line_color="grey")
                st.plotly_chart(fig_evo, use_container_width=True)

            # Pénétration + Enseigne + Type vente en grille compacte
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

            with st.expander("📋 Tableau complet des magasins"):
                display_cols = ["Magasin", "CA N", "Poids %", "Evolution %"]
                available = [c for c in display_cols if c in ca_mag.columns]
                st.dataframe(
                    ca_mag[available].style.format(
                        {"CA N": "{:,.0f}", "Poids %": "{:.1f}%", "Evolution %": "{:+.1f}%"},
                        na_rep="—"
                    ), use_container_width=True, height=400
                )

        # ────────────────────────────────────────────────────────────
        # VUE DÉTAIL MAGASIN
        # ────────────────────────────────────────────────────────────
        else:
            store_n  = _base_n[_base_n["Magasin"] == selected_store]
            store_n1 = _base_n1[_base_n1["Magasin"] == selected_store]
            enseigne = store_n["Enseigne"].iloc[0] if "Enseigne" in store_n.columns and len(store_n) > 0 else "N/A"

            st.markdown(f"## 🏪 {selected_store} &nbsp;"
                        f"<span style='background:#1D4ED8;color:white;padding:2px 10px;border-radius:4px;font-size:11px'>{enseigne}</span>",
                        unsafe_allow_html=True)

            ca_n_s = store_n["Montant TTC"].sum() if len(store_n) > 0 else 0
            ca_n1_s = store_n1["Montant TTC"].sum() if len(store_n1) > 0 else 0
            evol_s = evol_pct(ca_n_s, ca_n1_s)
            nb_fact_s = len(store_n)
            panier_s = ca_n_s / nb_fact_s if nb_fact_s > 0 else 0

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric(f"💰 CA {annee_sel}", f"{ca_n_s:,.0f} TND", f"{evol_s:+.1f}%", delta_color="normal" if evol_s >= 0 else "inverse")
            k2.metric(f"📅 CA {annee_sel-1}", f"{ca_n1_s:,.0f} TND")
            k3.metric("🧾 Factures", nb_fact_s)
            k4.metric("📊 Panier moyen", f"{panier_s:,.0f} TND")
            k5.metric("🏷️ Enseigne", enseigne)

            # ── CA Mensuel + Cumulé ─────────────────────────────────
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

            # ── Conventions (tableau visible directement) ────────────
            st.markdown("### 🏛️ Conventions")
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

            # ── Crédit Conso / Particulier / EDC (sous-tabs) ───────
            st.markdown("### 💳 Autres segments")
            tabs_credit = st.tabs(["Crédit Conso", "Crédit Particulier", "Convention EDC"])

            def _build_credit_tab(tab, df_src, label, icon):
                with tab:
                    # Mapping code magasin
                    df_filtered_n = pd.DataFrame()
                    df_filtered_n1 = pd.DataFrame()
                    if "Unite Code" in df_src.columns:
                        code_col = next((c for c in df_vc.columns if c.lower() == "unite code"), None)
                        if code_col and "Magasin" in df_vc.columns:
                            codes = df_vc[df_vc["Magasin"] == selected_store][code_col].dropna().unique()
                            if len(codes) > 0:
                                sc = [str(c).strip() for c in codes]
                                scf = [c + ".0" if not c.endswith(".0") else c for c in sc]
                                match = df_src["Unite Code"].astype(str).str.strip().isin(sc + scf)
                                df_filtered_n = df_src[match & (df_src["Année"] == annee_sel)]
                                df_filtered_n1 = df_src[match & (df_src["Année"] == annee_sel - 1)]
                    if df_filtered_n.empty:
                        st.info(f"Aucune donnée {label} pour ce magasin.")
                        return

                    if mois_sel:
                        df_filtered_n = df_filtered_n[df_filtered_n["Mois"].isin(mois_sel)]
                        df_filtered_n1 = df_filtered_n1[df_filtered_n1["Mois"].isin(mois_sel)]

                    # Date-to-date si possible
                    if len(df_filtered_n) > 0 and "Jour" in df_filtered_n.columns and len(df_filtered_n1) > 0:
                        comp = compare_years_date_to_date(pd.concat([df_filtered_n, df_filtered_n1]),
                                                          annee_sel, annee_sel - 1, mois_sel)
                        ca_n_val = comp["CA N"].sum() if not comp.empty else 0
                        ca_n1_val = comp["CA N-1"].sum() if not comp.empty else 0
                    else:
                        ca_n_val = df_filtered_n["Montant TTC"].sum() if len(df_filtered_n) > 0 else 0
                        ca_n1_val = df_filtered_n1["Montant TTC"].sum() if len(df_filtered_n1) > 0 else 0

                    ev = evol_pct(ca_n_val, ca_n1_val)
                    nb = len(df_filtered_n)
                    pm = ca_n_val / nb if nb > 0 else 0

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"{icon} Dossiers", nb)
                    c2.metric(f"💰 CA {annee_sel}", f"{ca_n_val:,.0f} TND", f"{ev:+.1f}%" if ca_n_val > 0 else None,
                              delta_color="normal" if ev >= 0 else "inverse")
                    c3.metric(f"📅 CA {annee_sel-1}", f"{ca_n1_val:,.0f} TND")
                    c4.metric("📊 Panier moyen", f"{pm:,.0f} TND" if nb > 0 else "0 TND")

            _build_credit_tab(tabs_credit[0], df_credit, "Crédit Conso", "💳")
            _build_credit_tab(tabs_credit[1], df_credit_part, "Crédit Particulier", "👤")
            _build_credit_tab(tabs_credit[2], df_edc, "Convention EDC", "🏫")

            # ── Détail des opérations ───────────────────────────────
            with st.expander("📄 Détail des opérations"):
                cols_show = [c for c in store_n.columns if c in ["Date", "Mois", "Nom", "Montant TTC", "Type vente à crédit", "Enseigne"]]
                st.dataframe(store_n[cols_show].sort_values("Date", ascending=False), use_container_width=True)


# ══════════════════════════════════════════════════════════════
# TAB 4 — EDC
# ══════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("🏫 Convention EDC — Ministère de l'Éducation")

    if not df_edc.empty and "Année" in df_edc.columns:
        edc_yr = st.selectbox("Année", [2026, 2025, 2024], key="edc_yr")

        df_edc_n  = df_edc[df_edc["Année"] == edc_yr]
        df_edc_n1 = df_edc[df_edc["Année"] == edc_yr - 1]

        # Appliquer le filtre mois (sidebar)
        if mois_sel:
            df_edc_n  = df_edc_n[df_edc_n["Mois"].isin(mois_sel)]
            df_edc_n1 = df_edc_n1[df_edc_n1["Mois"].isin(mois_sel)]
        
        # Date-to-date comparison for EDC tab
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

        # ─── Top Établissements ─────────────────────────────────
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
        c_et1.metric("🏪 Établissements actifs", len(etab[etab["CA_N"] > 0]))
        c_et2.metric("💰 CA Total EDC", f"{total_edc_n:,.0f} TND")
        c_et3.metric("📈 En croissance", len(etab[etab["Evolution %"] > 0]))
        c_et4.metric("📉 En baisse", len(etab[etab["Evolution %"] < 0]))

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

        with st.expander("📋 Tableau complet des établissements"):
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
                # Overlay % labels
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
        df_edc_comp = compare_years(df_edc, edc_yr, edc_yr - 1)
        if not df_edc_comp.empty:
            fig_edc_t = chart_grouped_bar(
                df_edc_comp, "Mois Nom", "CA N", "CA N-1",
                f"EDC mensuel — {edc_yr} vs {edc_yr-1}", edc_yr,
            )
            st.plotly_chart(fig_edc_t, use_container_width=True)
    else:
        st.warning("⚠️ Aucune donnée EDC disponible.")


# ══════════════════════════════════════════════════════════════
with tabs[5]:
    section("Pilotage par magasin")

    df_vc_tmp     = df_vc.copy()
    df_cr_tmp     = df_credit.copy()
    df_edc_tmp    = df_edc.copy()
    df_part_tmp   = df_credit_part.copy()

    # Mapping types
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
        
        # Try exact "Code magasin" first, then fallback
        mag_col = next((c for c in df.columns if c.lower() == "code magasin".lower()), None)
        if not mag_col:
            mag_col = next((c for c in df.columns if "code" in c.lower() and "magasin" in c.lower()), None)
        
        if date_col and ca_col and mag_col:
            try:
                df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
            except:
                df["_date"] = pd.NaT
            df["_ca"] = pd.to_numeric(df[ca_col], errors="coerce")
            
            # Map store code to name using code_df
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
        st.warning("⚠️ Aucune donnée disponible.")
    else:
        # Add date columns
        df_consol["Année"] = df_consol["_date"].dt.year
        df_consol["Mois"] = df_consol["_date"].dt.month
        df_consol["JMois"] = df_consol["_date"].dt.to_period("M").astype(str)

        # === FILTERS ===
        with st.sidebar:
            st.markdown("### Filtres")
            
            all_magasins = sorted(df_consol["_nom_mag"].dropna().unique().tolist())
            mag_sel = st.multiselect("Magasin(s)", all_magasins, default=[], format_func=str)
            
            min_d = df_consol["_date"].min()
            max_d = df_consol["_date"].max()
            if pd.notna(min_d) and pd.notna(max_d):
                date_range = st.date_input("Période", value=(min_d.date(), max_d.date()))
                date_deb, date_fin = date_range[0], date_range[1] if len(date_range) == 2 else (None, None)
            else:
                date_deb, date_fin = None, None
            
            all_mois = sorted(df_consol["Mois"].dropna().unique().tolist())
            mois_sel = st.multiselect("Mois", all_mois, default=all_mois, format_func=lambda x: MOIS.get(x, str(x)))

        # Apply filters
        df_f = df_consol.copy()
        if mag_sel:
            df_f = df_f[df_f["_nom_mag"].isin(mag_sel)]
        if mois_sel:
            df_f = df_f[df_f["Mois"].isin(mois_sel)]
        if date_deb and date_fin:
            df_f = df_f[(df_f["_date"] >= pd.Timestamp(date_deb)) & (df_f["_date"] <= pd.Timestamp(date_fin))]
        
        df_f["_ca"] = pd.to_numeric(df_f["_ca"], errors="coerce")
        df_f = df_f.dropna(subset=["_ca"])

        if df_f.empty:
            st.info("Aucune transaction pour les filtres sélectionnés.")
        else:
            # === KPIs per type (same period) ===
            an  = int(annee_sel)
            an1 = an - 1

            section("Répartition CA par type de financement")
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

            section("CA par type — même période")

            available_types = [t for t in TYPE_MAP.values() if t in df_f["_type"].unique()]
            col_types = st.columns(len(available_types)) if available_types else [st.columns(1)]
            for idx, type_label in enumerate(available_types):
                df_t = df_f[df_f["_type"] == type_label]
                with col_types[idx]:
                    st.markdown(f"### {type_label}")
                    if df_t.empty:
                        st.info(f"Aucune donnée")
                        continue

                    # KPIs for this type
                    ca_t   = df_t[df_t["Année"] == an]["_ca"].sum()
                    ca_t1  = df_t[df_t["Année"] == an1]["_ca"].sum()
                    evo_t  = evol_pct(ca_t, ca_t1)
                    nb_t   = len(df_t[df_t["Année"] == an])
                    pan_t  = ca_t / nb_t if nb_t > 0 else 0

                    st.metric(f"CA {an}", f"{ca_t:,.0f} TND", f"{evo_t:+.1f}%")
                    st.metric(f"CA {an1}", f"{ca_t1:,.0f} TND")
                    st.metric("Transactions", nb_t)
                    st.metric("Panier moyen", f"{pan_t:,.0f} TND")

                    # Pie chart - same period
                    pie_data = df_t.groupby("_nom_mag")["_ca"].sum().reset_index()
                    pie_data.columns = ["Magasin", "CA"]
                    if not pie_data.empty:
                        fig_p = px.pie(pie_data.head(10), values="CA", names="Magasin", hole=0.4,
                                     color_discrete_sequence=px.colors.qualitative.Set3)
                        fig_p.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=300)
                        st.plotly_chart(fig_p, use_container_width=True, key=f"mag_pie_{type_label}")

            # Tableau détaillé
            section("Tableau détaillé")
            detail = df_f[df_f["Année"] == an].groupby(["_nom_mag", "_type"])["_ca"].sum().reset_index()
            detail.columns = ["Magasin", "Type", "CA"]
            detail["%"] = (detail["CA"] / detail["CA"].sum() * 100).round(2)
            detail = detail.sort_values("CA", ascending=False)
            st.dataframe(detail, use_container_width=True)

            csv = detail.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export CSV", data=csv, file_name="pilotage_magasin.csv", mime="text/csv")


# ══════════════════════════════════════════════════════════════
# TAB 6 — CONVENTIONS SMG (suivi, DSO, alertes, GPO)
# ══════════════════════════════════════════════════════════════
with tabs[6]:

    st.markdown("### 📋 Pilotage Conventions SMG — GPO View")

    # ── Session state for conventions data ──
    if "smg_convs" not in st.session_state:
        st.session_state.smg_convs = [
            {"ref":"CONV-2026-001","client":"SONEDE","scenario":3,"regime":"Classique","plafond":3000,"duree":18,"taux":0.75,"encours":1200,"ds":22,"statut":"Active","date_fin":"2027-07-15","contact":"H. Chkondali","notes":"Paiements OK"},
            {"ref":"CONV-2026-002","client":"MUTUELLE CIMENTERIE","scenario":9,"regime":"PLUS","plafond":25000,"duree":12,"taux":0.75,"encours":8500,"ds":35,"statut":"Active","date_fin":"2027-02-01","contact":"H. Chkondali","notes":"Phase pilote 3 mois"},
            {"ref":"CONV-2026-003","client":"ONTT","scenario":6,"regime":"PLUS","plafond":2000,"duree":6,"taux":0.75,"encours":400,"ds":18,"statut":"En cours signature","date_fin":"2026-09-10","contact":"H. Chkondali","notes":"500 adherents pilote"},
            {"ref":"CONV-2026-004","client":"BEN AROUS AMICALE","scenario":4,"regime":"Classique","plafond":3000,"duree":18,"taux":0.75,"encours":2800,"ds":48,"statut":"Active","date_fin":"2026-12-01","contact":"H. Chkondali","notes":"Utilisation quasi max"},
            {"ref":"CONV-2025-012","client":"SOCIETE X","scenario":1,"regime":"Classique","plafond":3000,"duree":18,"taux":0.75,"encours":500,"ds":42,"statut":"Expiree","date_fin":"2026-07-20","contact":"H. Chkondali","notes":"A renouveler"},
        ]

    def jours_restants(date_str):
        try:
            return (datetime.strptime(date_str, "%Y-%m-%d") - datetime.now()).days
        except:
            return 999

    def niveau_alerte(jrs):
        if jrs < 0: return ("\U0001f534 Expiree", "inverse")
        if jrs <= 30: return ("\U0001f534 Urgent", "inverse")
        if jrs <= 60: return ("\U0001f7e0 Attention", "off")
        if jrs <= 90: return ("\U0001f535 Anticiper", "off")
        return ("\U0001f7e2 OK", "normal")

    def util_pct(encours, plafond):
        return round(encours / plafond * 100, 1) if plafond > 0 else 0

    # ── Refresh data ──
    df_smg = pd.DataFrame(st.session_state.smg_convs)
    df_smg["jrs_restants"] = df_smg["date_fin"].apply(jours_restants)
    df_smg["alerte"] = df_smg["jrs_restants"].apply(lambda j: niveau_alerte(j)[0])
    df_smg["util_pct"] = df_smg.apply(lambda r: util_pct(r["encours"], r["plafond"]), axis=1)

    # ── Top KPIs ──
    actives = df_smg[df_smg["statut"] == "Active"]
    alert_rouge = len(df_smg[df_smg["jrs_restants"].between(0, 30)])
    alert_jaune = len(df_smg[df_smg["jrs_restants"].between(31, 60)])
    encours_total = actives["encours"].sum()
    dso_moy = round(actives["ds"].mean(), 1) if len(actives) > 0 else 0
    util_moy = round(actives["util_pct"].mean(), 1) if len(actives) > 0 else 0

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("Conventions actives", len(actives))
    kpi2.metric("Encours total", f"{encours_total:,.0f} TND")
    kpi3.metric("DSO moyen", f"{dso_moy} jrs")
    kpi4.metric("Utilisation ligne moy.", f"{util_moy}%")
    kpi5.metric("Alertes rouges", alert_rouge, delta_color="inverse")
    kpi6.metric("Alertes jaunes", alert_jaune, delta_color="off")

    # ── Tableau de suivi ──
    st.markdown("### Suivi des conventions")
    display_cols = {
        "ref": "Convention", "client": "Client", "scenario": "Sc.", "regime": "Regime",
        "plafond": "Plafond", "duree": "Mois", "encours": "Encours",
        "util_pct": "Util.%", "ds": "DSO(j)", "jrs_restants": "Jours",
        "alerte": "Alerte", "statut": "Statut", "date_fin": "Echeance",
        "notes": "Notes",
    }
    df_display = df_smg[list(display_cols.keys())].rename(columns=display_cols)
    df_display["Util.%"] = df_display["Util.%"].apply(lambda x: f"{x}%")
    st.dataframe(df_display, use_container_width=True, height=280)

    # ── Alertes échéances ──
    st.markdown("### \U0001f514 Alertes echeances (prochains 90 jours)")
    alertes = df_smg[(df_smg["jrs_restants"] >= 0) & (df_smg["jrs_restants"] <= 90)].sort_values("jrs_restants")
    if len(alertes) > 0:
        for _, r in alertes.iterrows():
            lvl, delta = niveau_alerte(r["jrs_restants"])
            st.metric(f"{r['client']} - {r['ref']}", f"{r['jrs_restants']} jours restants",
                      f"{lvl}", delta_color=delta)
    else:
        st.success("Aucune echeance dans les 90 jours.")

    # ── Gestion rapide ──
    st.markdown("### \u2699\ufe0f Ajouter / Modifier une convention")
    with st.expander("Formulaire convention"):
        with st.form("smg_form"):
            col1, col2 = st.columns(2)
            with col1:
                ref = st.text_input("Ref convention", "CONV-2026-005")
                client = st.text_input("Client", "")
                scenario = st.selectbox("Scenario", range(1, 11), format_func=lambda x: f"S{x:02d}")
            with col2:
                regime = st.selectbox("Regime", ["Classique", "PLUS"])
                plafond = st.number_input("Plafond (TND)", 300, 50000, 3000)
                encours = st.number_input("Encours (TND)", 0, 50000, 0)
            col3, col4 = st.columns(2)
            with col3:
                duree = st.number_input("Duree (mois)", 1, 24, 12)
                dso = st.number_input("DSO (jours)", 0, 365, 30)
            with col4:
                statut = st.selectbox("Statut", ["Active", "En cours signature", "Expiree", "Resiliee"])
                date_fin = st.date_input("Date echeance", datetime.now() + timedelta(days=365))
            notes = st.text_area("Notes", "")
            submitted = st.form_submit_button("Ajouter / Mettre a jour")
            if submitted and client and ref:
                exists = [i for i, c in enumerate(st.session_state.smg_convs) if c["ref"] == ref]
                entry = {"ref":ref,"client":client,"scenario":scenario,"regime":regime,
                         "plafond":plafond,"duree":duree,"taux":0.75,"encours":encours,
                         "ds":dso,"statut":statut,"date_fin":date_fin.strftime("%Y-%m-%d"),
                         "contact":"H. Chkondali","notes":notes}
                if exists:
                    st.session_state.smg_convs[exists[0]] = entry
                else:
                    st.session_state.smg_convs.append(entry)
                st.rerun()

    # ── Export CSV ──
    csv_data = df_display.to_csv(index=False).encode("utf-8")
    st.download_button("Exporter CSV", data=csv_data, file_name="conventions_smg.csv", mime="text/csv")


# --- CRM ---
with tabs[7]:
    try:
        import sys as _cs, os as _co, importlib as _ci
        _cp = _co.path.join(_co.path.dirname(__file__), "crm.py")
        if not _co.path.exists(_cp):
            df_crm = None; st.info("crm.py absent")
        else:
            _spec = _ci.util.spec_from_file_location("crm_mod", _cp)
            _crm = _ci.util.module_from_spec(_spec)
            _spec.loader.exec_module(_crm)
            _r2 = requests.get(GITHUB_RAW + "TDC2.xlsx", timeout=30)
            if _r2.status_code == 200:
                df_crm = _crm.load_crm_data(source=BytesIO(_r2.content))
            else:
                df_crm = None; st.warning("TDC2.xlsx introuvable sur GitHub")
    except Exception as _ec:
        st.warning(f"CRM: {_ec}")
        df_crm = None

    if df_crm is not None and len(df_crm) > 0:
        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Total prospects", len(df_crm))
        en_cours = len(df_crm[df_crm["Statut pipeline"]=="En cours"])
        k2.metric("En cours", en_cours)
        cloture = len(df_crm[df_crm["Statut pipeline"]=="Cloture"])
        k3.metric("Cloturees", cloture)

        col1, col2 = st.columns(2)
        with col1:
            pipe = df_crm["Statut pipeline"].value_counts().reset_index()
            pipe.columns = ["Statut", "Nb"]
            fig_pipe = px.bar(pipe, x="Statut", y="Nb", color="Statut", title="Pipeline Commercial", text_auto=True, height=350)
            fig_pipe.update_layout(showlegend=False)
            st.plotly_chart(fig_pipe, use_container_width=True)
        with col2:
            prio = df_crm["Priorite relance"].value_counts().reset_index()
            prio.columns = ["Priorite", "Nb"]
            fig_prio = px.pie(prio, values="Nb", names="Priorite", title="Priorites Relance", height=350, hole=0.4)
            st.plotly_chart(fig_prio, use_container_width=True)

        st.markdown("<div class='sec-hdr'>TOP Prospects</div>", unsafe_allow_html=True)
        cols_show = ["Nom entreprise", "Statut pipeline", "Priorite relance", "Secteur", "Contact", "Date derniere activite"]
        cols_ok = [c for c in cols_show if c in df_crm.columns]
        df_disp = df_crm[cols_ok].head(15)
        ev = st.dataframe(df_disp, use_container_width=True, height=400,
                          on_select="rerun", selection_mode="single-row")
        sel = ev.selection.rows if hasattr(ev, 'selection') else []
        if sel:
            idx = sel[0]
            client = df_crm.loc[df_disp.index[idx]]
            nm = str(client.get("Nom entreprise", ""))
            with st.container():
                st.markdown(f"<div style='background:#f0f2f6;padding:1.2rem 1.5rem;border-radius:12px;margin-top:0.5rem'>"
                            f"<h3 style='margin:0 0 1rem 0'>{nm}</h3>", unsafe_allow_html=True)
                cx = st.columns(3)
                cx[0].markdown(f"**Contact**<br>{client.get('Contact', '')}", unsafe_allow_html=True)
                cx[1].markdown(f"**Telephone**<br>{client.get('Telephone', '')}", unsafe_allow_html=True)
                cmt = str(client.get("Commentaire", ""))
                if cmt and cmt != "nan" and cmt.strip():
                    cx[2].markdown(f"**Commentaire**<br>{cmt}", unsafe_allow_html=True)
                else:
                    cx[2].markdown("**Commentaire**<br>—", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("CRM desactive. Verifiez TDC2.xlsx et crm.py")
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