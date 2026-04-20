"""
Dashboard Pilotage B2B — SMG (MG & BATAM)
Refactored: architecture modulaire, BI décisionnel, visualisation executive
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import BytesIO
from urllib.parse import quote

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
    "vc":                 quote("Factures ventes enregistrées VC (4).xlsx"),
    "vc_credit":          quote("Factures ventes enregistrées VC credit conso.xlsx"),
    "vc_edc":             quote("Factures ventes enregistrées VC CONVENTION EDC.xlsx"),
    "conventions_signees": quote("TDC CONVENTION 1.xlsm"),
    "code_magasin":       quote("Code MAGASIN Business Central.xlsx"),
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


# ══════════════════════════════════════════════════════════════
# SECTION 3 — DATA PROCESSING
# ══════════════════════════════════════════════════════════════

def _add_date_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Extrait Année / Mois / Jour depuis 'Date comptabilisation'."""
    if "Date comptabilisation" not in df.columns:
        return df
    df = df.copy()
    df["Date"]  = pd.to_datetime(df["Date comptabilisation"], errors="coerce")
    df["Année"] = df["Date"].dt.year.astype("Int64")
    df["Mois"]  = df["Date"].dt.month.astype("Int64")
    df["Jour"]  = df["Date"].dt.day.astype("Int64")
    return df


def _map_magasins(df: pd.DataFrame, code_df: pd.DataFrame) -> pd.DataFrame:
    """
    Mapping vectorisé code→nom magasin.
    REMPLACE l'ancien get_magasin_name() appelé row-by-row via apply(lambda).
    Gain : O(1) merge vs O(n) dict lookups.
    """
    if code_df.empty or "Code magasin" not in df.columns:
        return df
    code_df = code_df.copy()
    code_df.columns = [c.strip() for c in code_df.columns]
    # Cherche la colonne code en premier
    code_col = next((c for c in code_df.columns if "code" in c.lower()), None)
    # Cherche la colonne nom en excluant la colonne code
    name_col = next(
        (c for c in code_df.columns
         if c != code_col and any(k in c.lower() for k in ("unit", "nom", "magasin", "libelle"))),
        None,
    )
    # Fallback : prend la deuxième colonne si aucun match sémantique
    if not name_col and len(code_df.columns) >= 2:
        name_col = next((c for c in code_df.columns if c != code_col), None)
    if not code_col or not name_col:
        return df
    mapping = code_df.set_index(code_col)[name_col].to_dict()
    df = df.copy()
    df["Magasin"] = (
        df["Code magasin"].astype(str).str.strip()
        .map(mapping)
        .fillna(df["Code magasin"].astype(str))
    )
    return df


# NOTE: _raw commence par _ → Streamlit skip le hashing de ce paramètre
@st.cache_data(show_spinner=False)
def prepare_data(_raw: dict) -> tuple:
    """
    Point d'entrée unique pour tout le processing.
    Retourne (df_vc, df_credit, df_edc, df_conv, code_df).
    """
    code_df   = _raw.get("code_magasin", pd.DataFrame())
    df_vc     = _map_magasins(_add_date_cols(_raw.get("vc",       pd.DataFrame())), code_df)
    df_credit = _map_magasins(_add_date_cols(_raw.get("vc_credit", pd.DataFrame())), code_df)
    df_edc    = _add_date_cols(_raw.get("vc_edc", pd.DataFrame()))
    df_conv   = _raw.get("conventions_signees", pd.DataFrame())
    return df_vc, df_credit, df_edc, df_conv, code_df


# ══════════════════════════════════════════════════════════════
# SECTION 4 — KPI ENGINE  (logique métier centralisée)
# ══════════════════════════════════════════════════════════════

def ca_sum(df: pd.DataFrame, annee: int, mois=None) -> float:
    d = df[df["Année"] == annee]
    if mois and mois != "Tous":
        d = d[d["Mois"] == mois]
    return float(d["Montant TTC"].sum()) if "Montant TTC" in d.columns else 0.0


def evol_pct(n: float, n1: float) -> float:
    return round((n - n1) / n1 * 100, 1) if n1 > 0 else 0.0


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


def convention_risk_matrix(df_vc: pd.DataFrame, annee_n: int) -> pd.DataFrame:
    """
    Matrice risque / opportunité par convention.
    Classifie chaque convention selon CA et évolution N/N-1.
    """
    if df_vc.empty or "Nom" not in df_vc.columns:
        return pd.DataFrame()
    ca_n  = df_vc[df_vc["Année"] == annee_n].groupby("Nom")["Montant TTC"].sum().rename("CA N")
    ca_n1 = df_vc[df_vc["Année"] == annee_n - 1].groupby("Nom")["Montant TTC"].sum().rename("CA N-1")
    mat = pd.concat([ca_n, ca_n1], axis=1).fillna(0).reset_index()
    mat["Évolution %"] = (
        (mat["CA N"] - mat["CA N-1"]) / mat["CA N-1"].replace(0, 1) * 100
    ).round(1)

    def _classify(row):
        if row["CA N"] == 0 and row["CA N-1"] == 0:
            return "⚫ Aucun historique"
        if row["CA N"] == 0:
            return "🔴 Inactif"
        if row["CA N-1"] == 0:
            return "🟢 Nouveau"
        if row["Évolution %"] <= -20:
            return "🔴 Déclin fort"
        if row["Évolution %"] < 0:
            return "🟡 Déclin"
        return "🟢 Croissance"

    mat["Statut"] = mat.apply(_classify, axis=1)
    return mat.sort_values("CA N", ascending=False)


def inactive_conventions(df_vc: pd.DataFrame, threshold_days: int = 30) -> pd.DataFrame:
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
    return _base(fig.update_layout(title=title), h)


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


def chart_scatter_risk(
    df: pd.DataFrame, annee_n: int, title: str, h: int = 480,
) -> go.Figure:
    """
    Matrice risque / opportunité :
      X = CA N  |  Y = Évolution %  |  Taille = CA N  |  Couleur = Statut
    """
    if df is None or df.empty:
        return _empty(title, h)

    _color_map = {
        "🔴 Inactif":        C["red"],
        "🔴 Déclin fort":    C["red"],
        "🟡 Déclin":         C["amber"],
        "🟢 Nouveau":        C["green"],
        "🟢 Croissance":     C["green"],
        "⚫ Aucun historique": C["muted"],
    }
    max_ca = df["CA N"].max() or 1
    fig = go.Figure()
    for statut, grp in df.groupby("Statut"):
        fig.add_trace(go.Scatter(
            x=grp["CA N"], y=grp["Évolution %"],
            mode="markers+text",
            name=statut,
            text=grp["Nom"],
            textposition="top center",
            textfont=dict(size=9, color=C["ink"]),
            marker=dict(
                size=grp["CA N"].clip(lower=1).apply(
                    lambda v: max(8, min(36, v / max_ca * 36))
                ),
                color=_color_map.get(statut, C["muted"]),
                opacity=0.82,
                line=dict(width=1, color="white"),
            ),
        ))
    # Quadrants
    fig.add_hline(y=0,  line_dash="dash", line_color=C["muted"], line_width=1, opacity=0.6)
    fig.add_vline(x=df["CA N"].median(), line_dash="dot", line_color=C["border"],
                  line_width=1, opacity=0.5)
    fig.update_layout(
        title=title,
        xaxis_title=f"CA {annee_n} (TND)",
        yaxis_title="Évolution vs N-1 (%)",
    )
    return _base(fig, h)


def chart_gauge(value: float, ref: float, title: str, h: int = 260) -> go.Figure:
    """Jauge d'atteinte CA N vs N-1."""
    ref_safe = ref if ref > 0 else max(value, 1)
    pct   = min(max((value / ref_safe * 100) if ref_safe > 0 else 0, 0), 150)
    color = C["green"] if pct >= 100 else (C["amber"] if pct >= 70 else C["red"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta=dict(reference=ref, relative=True, valueformat=".1%"),
        title=dict(text=title, font=dict(size=13)),
        gauge=dict(
            axis=dict(range=[0, ref_safe * 1.5], tickformat=",.0f"),
            bar=dict(color=color, thickness=0.28),
            bgcolor="white",
            borderwidth=0,
            steps=[
                dict(range=[0,              ref_safe * 0.7], color="rgba(220,38,38,0.06)"),
                dict(range=[ref_safe * 0.7, ref_safe],       color="rgba(217,119,6,0.06)"),
                dict(range=[ref_safe,       ref_safe * 1.5], color="rgba(5,150,105,0.08)"),
            ],
            threshold=dict(
                line=dict(color=C["muted"], width=2),
                thickness=0.8, value=ref_safe,
            ),
        ),
        number=dict(suffix=" TND", valueformat=",.0f"),
    ))
    gauge_layout = {**_BASE, "height": h, "margin": dict(l=20, r=20, t=40, b=10)}
    fig.update_layout(**gauge_layout)
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
        font-weight: 600; font-size: 0.88rem; color: {C["muted"]};
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
    st.markdown("### 🔍 Filtres globaux")
    annee_sel = st.selectbox("Année N", [2026, 2025, 2024, 2023], index=0)
    mois_sel  = st.selectbox(
        "Mois",
        ["Tous"] + list(range(1, 13)),
        index=pd.Timestamp.now().month,
        format_func=lambda x: MOIS.get(x, "Tous") if x != "Tous" else "Tous",
    )
    st.markdown("---")
    if st.button("🔄 Actualiser les données"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Filtres appliqués à tous les onglets")

# ── Chargement données ────────────────────────────────────────
with st.spinner("Chargement des données…"):
    _raw = load_all_data()

df_vc, df_credit, df_edc, df_conv, code_df = prepare_data(_raw)

if df_vc.empty or "Année" not in df_vc.columns:
    st.error("⚠️ Aucune donnée VC chargée. Vérifiez la connexion GitHub.")
    st.stop()

# Convention filter (dépend de l'année)
_conv_options = (
    ["Tous"] + sorted(df_vc[df_vc["Année"] == annee_sel]["Nom"].dropna().unique().tolist())
    if "Nom" in df_vc.columns else ["Tous"]
)
with st.sidebar:
    conv_sel = st.selectbox("Convention", _conv_options)

# ── Slice filtré ──────────────────────────────────────────────
df_filt = df_vc[df_vc["Année"] == annee_sel].copy()
if mois_sel != "Tous":
    df_filt = df_filt[df_filt["Mois"] == mois_sel]
if conv_sel != "Tous":
    df_filt = df_filt[df_filt["Nom"] == conv_sel]

# ── Pré-calculs partagés (calculés une seule fois) ────────────
df_comp     = compare_years(df_vc, annee_sel, annee_sel - 1)
risk_mat    = convention_risk_matrix(df_vc, annee_sel)
df_inactive = inactive_conventions(df_vc)
df_3m       = get_rolling_3m(df_vc)

ca_n        = ca_sum(df_vc, annee_sel, mois_sel)
ca_n1       = ca_sum(df_vc, annee_sel - 1, mois_sel)
ca_n2       = ca_sum(df_vc, annee_sel - 2, mois_sel)
ev_nn1      = evol_pct(ca_n, ca_n1)
ev_n1n2     = evol_pct(ca_n1, ca_n2)

nb_actives  = df_vc[df_vc["Année"] == annee_sel]["Nom"].dropna().nunique() \
              if "Nom" in df_vc.columns else 0
nb_total    = len(df_conv) if not df_conv.empty else 0
nb_inact    = len(df_inactive)
panier_moy  = df_filt["Montant TTC"].mean() if len(df_filt) > 0 else 0

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
    "🔔 Alertes & Risques",
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
        "⚠️ >30j sans facture" if nb_inact > 0 else "✅ Aucune",
        delta_color="inverse" if nb_inact > 0 else "off",
    )
    k5.metric("Panier moyen", f"{panier_moy:,.0f} TND")

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

    # ── Carte risque + Top/Flop ────────────────────────────────
    section("Signaux décisionnels — Risques & Opportunités")
    col_e, col_f, col_g = st.columns([3, 1, 1])

    with col_e:
        fig_sc = chart_scatter_risk(
            risk_mat.head(35), annee_sel,
            "Carte risque / opportunité — Toutes les conventions", h=400,
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


# ══════════════════════════════════════════════════════════════
# TAB 1 — CA & TENDANCES
# ══════════════════════════════════════════════════════════════
with tabs[1]:

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

    _dj_n  = df_vc[df_vc["Année"] == annee_sel]
    _dj_n1 = df_vc[df_vc["Année"] == annee_sel - 1]
    if mois_sel != "Tous":
        _dj_n  = _dj_n[_dj_n["Mois"]   == mois_sel]
        _dj_n1 = _dj_n1[_dj_n1["Mois"] == mois_sel]

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

    section("Vue globale du portefeuille")

    # Scatter risk matrix plein écran
    fig_risk_full = chart_scatter_risk(
        risk_mat, annee_sel,
        f"Matrice risque / opportunité — Portefeuille complet {annee_sel}", h=500,
    )
    st.plotly_chart(fig_risk_full, use_container_width=True)

    with st.expander("📊 Tableau de pilotage conventions"):
        if not risk_mat.empty:
            disp = risk_mat.rename(columns={
                "CA N":  f"CA {annee_sel}",
                "CA N-1": f"CA {annee_sel-1}",
            })
            st.dataframe(disp, use_container_width=True)

    # ── Analyse individuelle ───────────────────────────────────
    section("Analyse individuelle par convention")

    all_convs = sorted(df_vc["Nom"].dropna().unique().tolist()) if "Nom" in df_vc.columns else []
    conv_detail = st.selectbox("Sélectionner une convention", all_convs, key="conv_detail")

    if conv_detail:
        df_cv      = df_vc[df_vc["Nom"] == conv_detail].copy()
        ca_cv_n    = ca_sum(df_cv, annee_sel)
        ca_cv_n1   = ca_sum(df_cv, annee_sel - 1)
        ev_cv      = evol_pct(ca_cv_n, ca_cv_n1)
        nb_fact_cv = len(df_cv[df_cv["Année"] == annee_sel])
        panier_cv  = ca_cv_n / nb_fact_cv if nb_fact_cv > 0 else 0

        ci1, ci2, ci3, ci4 = st.columns(4)
        ci1.metric(
            f"CA {annee_sel}", f"{ca_cv_n:,.0f} TND",
            f"{ev_cv:+.1f}% vs {annee_sel-1}",
            delta_color="normal" if ev_cv >= 0 else "inverse",
        )
        ci2.metric(f"CA {annee_sel-1}", f"{ca_cv_n1:,.0f} TND")
        ci3.metric(f"Factures {annee_sel}", nb_fact_cv)
        ci4.metric("Panier moyen", f"{panier_cv:,.0f} TND")

        col_cv1, col_cv2 = st.columns(2)
        df_cv_comp = compare_years(df_cv, annee_sel, annee_sel - 1)

        with col_cv1:
            fig_cv_g = chart_grouped_bar(
                df_cv_comp, "Mois Nom", "CA N", "CA N-1",
                f"CA Mensuel — {conv_detail}", annee_sel,
            )
            st.plotly_chart(fig_cv_g, use_container_width=True)

        with col_cv2:
            # Cumulé
            _cn  = df_cv[df_cv["Année"] == annee_sel].groupby("Mois")["Montant TTC"].sum().reset_index()
            _cn1 = df_cv[df_cv["Année"] == annee_sel - 1].groupby("Mois")["Montant TTC"].sum().reset_index()
            _cn["CA Cum N"]   = _cn["Montant TTC"].cumsum()
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
                mag = (
                    df_cv[df_cv["Année"] == annee_sel]
                    .groupby("Magasin")["Montant TTC"].sum()
                    .nlargest(10).reset_index()
                )
                fig_mag_cv = chart_bar(
                    mag, "Montant TTC", "Magasin",
                    "Top Magasins", C["purple"], h=360, orientation="h",
                )
                st.plotly_chart(fig_mag_cv, use_container_width=True)

        with col_cv4:
            ca_cash   = df_cv[df_cv["Année"] == annee_sel]["Montant TTC"].sum()
            ca_credit = (
                df_credit[df_credit["Nom"] == conv_detail]["Montant TTC"].sum()
                if "Nom" in df_credit.columns else 0
            )
            if ca_cash > 0 or ca_credit > 0:
                fig_pie_cv = chart_pie(
                    [ca_cash, ca_credit], ["Cash", "Crédit"],
                    f"Cash vs Crédit — {conv_detail}",
                )
                st.plotly_chart(fig_pie_cv, use_container_width=True)

    # TDC conventions signées
    if not df_conv.empty:
        with st.expander("📁 Liste des conventions signées (TDC)"):
            cols_ok = [c for c in ["SOCIETES", "Code BC", "Effectifs", "CA 2025",
                                    "POTENTIEL", "MATURITE", "SCORE"] if c in df_conv.columns]
            if cols_ok:
                c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
                c_kpi1.metric("Nb conventions", len(df_conv))
                c_kpi2.metric("Effectif total",
                               f"{pd.to_numeric(df_conv['Effectifs'], errors='coerce').sum():,.0f}"
                               if "Effectifs" in df_conv.columns else "N/A")
                c_kpi3.metric("CA 2025 portefeuille",
                               f"{pd.to_numeric(df_conv['CA 2025'], errors='coerce').sum():,.0f} TND"
                               if "CA 2025" in df_conv.columns else "N/A")
                st.dataframe(df_conv[cols_ok], use_container_width=True)


# ══════════════════════════════════════════════════════════════
# TAB 3 — MAGASINS
# ══════════════════════════════════════════════════════════════
with tabs[3]:
    section("Performance réseau magasins")

    if "Magasin" in df_vc.columns:
        _base_n  = df_vc[df_vc["Année"] == annee_sel]
        _base_n1 = df_vc[df_vc["Année"] == annee_sel - 1]
        if mois_sel != "Tous":
            _base_n  = _base_n[_base_n["Mois"]   == mois_sel]
            _base_n1 = _base_n1[_base_n1["Mois"] == mois_sel]

        ca_mag_n  = _base_n.groupby("Magasin")["Montant TTC"].sum().rename("CA N")
        ca_mag_n1 = _base_n1.groupby("Magasin")["Montant TTC"].sum().rename("CA N-1")
        ca_mag = pd.concat([ca_mag_n, ca_mag_n1], axis=1).fillna(0).reset_index()
        ca_mag["Évolution %"] = (
            (ca_mag["CA N"] - ca_mag["CA N-1"]) / ca_mag["CA N-1"].replace(0, 1) * 100
        ).round(1)
        ca_mag = ca_mag.sort_values("CA N", ascending=False)

        # KPI magasins
        m1, m2, m3 = st.columns(3)
        m1.metric("Nb magasins actifs", len(ca_mag[ca_mag["CA N"] > 0]))
        m2.metric("CA total réseau", f"{ca_mag['CA N'].sum():,.0f} TND")
        m3.metric("Magasins en hausse",
                  len(ca_mag[ca_mag["Évolution %"] > 0]),
                  f"/ {len(ca_mag)} total")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            fig_mt = chart_bar(
                ca_mag.head(20), "CA N", "Magasin",
                f"Top 20 magasins — CA {annee_sel}", C["blue"], h=520, orientation="h",
            )
            st.plotly_chart(fig_mt, use_container_width=True)

        with col_m2:
            fig_mv = chart_variation_bar(
                ca_mag.head(20), "Magasin", "Évolution %",
                f"Évolution N/N-1 — Top 20 magasins", h=520,
            )
            st.plotly_chart(fig_mv, use_container_width=True)

        with st.expander("📄 Données complètes réseau"):
            st.dataframe(
                ca_mag.rename(columns={"CA N": f"CA {annee_sel}", "CA N-1": f"CA {annee_sel-1}"}),
                use_container_width=True,
            )
    else:
        st.info("Données magasins non disponibles (mapping code→nom absent).")


# ══════════════════════════════════════════════════════════════
# TAB 4 — EDC
# ══════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("🏫 Convention EDC — Ministère de l'Éducation")

    if not df_edc.empty and "Année" in df_edc.columns:
        edc_yr = st.selectbox("Année", [2026, 2025, 2024], key="edc_yr")

        df_edc_n  = df_edc[df_edc["Année"] == edc_yr]
        df_edc_n1 = df_edc[df_edc["Année"] == edc_yr - 1]
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
# TAB 5 — ALERTES & RISQUES
# ══════════════════════════════════════════════════════════════
with tabs[5]:

    section("Tableau de bord des risques")

    # ── Résumé badges ─────────────────────────────────────────
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("🔴 Déclin fort (>-20%)",  nb_declin_fort)
    b2.metric("⬛ Conventions inactives", nb_inactif_cv)
    b3.metric("⚠️ En inactivité >30j",   nb_inact)
    b4.metric("🟢 En croissance",         nb_croissance)

    # ── Inactivité >30 jours ───────────────────────────────────
    section("Conventions à réactiver — inactivité > 30 jours")

    if not df_inactive.empty:
        fig_ia = chart_inactive_bar(
            df_inactive,
            f"Conventions inactives — {len(df_inactive)} comptes sans facture depuis >30j",
        )
        st.plotly_chart(fig_ia, use_container_width=True)

        with st.expander(f"📋 Liste complète ({len(df_inactive)} conventions)"):
            st.dataframe(df_inactive, use_container_width=True)
    else:
        st.success("✅ Aucune convention inactive détectée (seuil : 30 jours).")

    # ── Conventions en déclin ──────────────────────────────────
    section("Conventions en déclin — Analyse des pertes")

    if not risk_mat.empty:
        declining = risk_mat[
            risk_mat["Statut"].isin(["🔴 Déclin fort", "🟡 Déclin"])
        ].copy()
        declining["Perte TND"] = (declining["CA N-1"] - declining["CA N"]).clip(lower=0)
        declining = declining.sort_values("Perte TND", ascending=False)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if not declining.empty:
                fig_perte = chart_bar(
                    declining.head(15), "Perte TND", "Nom",
                    "Perte CA vs N-1 (TND)", C["red"], h=460, orientation="h",
                )
                st.plotly_chart(fig_perte, use_container_width=True)
            else:
                st.success("✅ Aucune convention en déclin.")

        with col_d2:
            if not declining.empty:
                fig_dec_pct = chart_variation_bar(
                    declining.head(15), "Nom", "Évolution %",
                    "Variation % — Conventions en déclin", h=460,
                )
                st.plotly_chart(fig_dec_pct, use_container_width=True)

    # ── Opportunités ───────────────────────────────────────────
    section("Opportunités — Conventions à fort potentiel")

    if not risk_mat.empty:
        opps = (
            risk_mat[risk_mat["Statut"].isin(["🟢 Croissance", "🟢 Nouveau"])]
            .sort_values("CA N", ascending=False)
            .head(10)
        )
        if not opps.empty:
            fig_opp = chart_bar(
                opps, "CA N", "Nom",
                f"Top opportunités — CA {annee_sel}", C["green"], h=380, orientation="h",
            )
            st.plotly_chart(fig_opp, use_container_width=True)
        else:
            st.info("Aucune convention en croissance détectée pour cette période.")


# ── Footer ────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Dashboard B2B SMG — MG & BATAM  ·  "
    f"Source : VC.CONV. Business Central  ·  "
    f"Généré automatiquement  ·  "
    f"Filtres actifs : Année {annee_sel} "
    f"{'| Mois ' + MOIS.get(mois_sel, '') if mois_sel != 'Tous' else ''} "
    f"{'| Conv. ' + conv_sel if conv_sel != 'Tous' else ''}"
)
