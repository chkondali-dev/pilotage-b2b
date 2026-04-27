"""
==================================================================================================
DASHBOARD RETAIL SMG - PILOTAGE COMMERCIAL (CORPORATE DESIGN)
==================================================================================================
Design: Corporate Finance/Banque - Bleu/Gris Classique
Navigation: Onglets en haut
Focus: CA total, Evolution N-1, Top produit
==================================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# ════════════════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="SMG - Pilotage Commercial",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ════════════════════════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM - CORPORATE FINANCE
# ════════════════════════════════════════════════════════════════════════════════════════════════

COLORS = {
    # Primary corporate blues
    "primary": "#0F4C81",        # Bleu marine classique
    "primary_light": "#1E6BB8",  # Bleu clair
    "primary_dark": "#0A3659",    # Bleu foncé
    
    # Greys - neutral professional
    "grey_900": "#1A1A2E",        # Noir bleuté
    "grey_800": "#2D3748",        # Gris foncé
    "grey_700": "#4A5568",        # Gris moyen
    "grey_600": "#718096",        # Gris muted
    "grey_500": "#A0AEC0",        # Gris clair
    "grey_400": "#CBD5E0",        # Gris très clair
    "grey_300": "#E2E8F0",        # Bordure légère
    "grey_200": "#EDF2F7",        # Fond gris clair
    "grey_100": "#F7FAFC",        # Presque blanc
    
    # Semantic
    "success": "#059669",         # Vert croissance
    "danger": "#C53030",          # Rouge alerte
    "warning": "#D69E2E",         # Orange avertissement
    "info": "#3182CE",            # Bleu info
    
    # Background
    "bg_white": "#FFFFFF",
    "bg_light": "#F8FAFC",
    "bg_dark": "#1A202C",
}


def inject_css():
    """CSS - Corporate Finance Design"""
    st.markdown(f"""
    <style>
    /* ── Reset & Base ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: {COLORS['grey_800']};
    }}
    
    /* ── Background ── */
    .stApp {{
        background: {COLORS['bg_light']};
    }}
    .block-container {{
        padding: 2rem 3rem;
        max-width: 100%;
    }}
    
    /* ── HEADER ── */
    .header-container {{
        background: linear-gradient(135deg, {COLORS['primary_dark']} 0%, {COLORS['primary']} 100%);
        border-radius: 0;
        padding: 1.5rem 2rem;
        margin: -1.5rem -3rem 2rem -3rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}
    .header-title {{
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
        letter-spacing: -0.02em;
    }}
    .header-subtitle {{
        font-size: 0.875rem;
        color: rgba(255,255,255,0.7);
        margin-top: 0.25rem;
    }}
    .header-meta {{
        display: flex;
        gap: 1.5rem;
        align-items: center;
    }}
    .header-badge {{
        background: rgba(255,255,255,0.15);
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-size: 0.75rem;
        color: white;
    }}
    
    /* ── TABS - Corporate Style ── */
    [data-testid="stTabs"] {{
        border-bottom: 2px solid {COLORS['grey_300']};
        margin-bottom: 2rem;
    }}
    [data-testid="stTabs"] button[role="tab"] {{
        background: transparent;
        border: none;
        padding: 1rem 1.5rem;
        font-size: 0.9rem;
        font-weight: 600;
        color: {COLORS['grey_600']};
        border-bottom: 3px solid transparent;
        margin-bottom: -2px;
        transition: all 0.2s;
    }}
    [data-testid="stTabs"] button[role="tab"]:hover {{
        color: {COLORS['primary']};
        background: {COLORS['grey_100']};
    }}
    [data-testid="stTabs"] button[aria-selected="true"] {{
        color: {COLORS['primary']};
        border-bottom-color: {COLORS['primary']};
        background: transparent;
    }}
    
    /* ── KPI CARDS - Professional Finance ── */
    .kpi-row {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin-bottom: 2rem;
    }}
    .kpi-card {{
        background: {COLORS['bg_white']};
        border-radius: 8px;
        padding: 1.5rem;
        border: 1px solid {COLORS['grey_300']};
        border-left: 4px solid {COLORS['primary']};
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .kpi-card.highlight {{
        border-left-color: {COLORS['primary_light']};
        background: linear-gradient(135deg, {COLORS['bg_white']} 0%, {COLORS['grey_100']} 100%);
    }}
    .kpi-label {{
        font-size: 0.75rem;
        font-weight: 600;
        color: {COLORS['grey_600']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }}
    .kpi-value {{
        font-size: 2rem;
        font-weight: 700;
        color: {COLORS['grey_900']};
        line-height: 1.2;
    }}
    .kpi-delta {{
        font-size: 0.875rem;
        font-weight: 600;
        margin-top: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }}
    .delta-up {{ color: {COLORS['success']}; }}
    .delta-down {{ color: {COLORS['danger']}; }}
    .delta-neutral {{ color: {COLORS['grey_600']}; }}
    
    /* ── SECTION TITLES ── */
    .section-title {{
        font-size: 1rem;
        font-weight: 700;
        color: {COLORS['grey_800']};
        margin: 2rem 0 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid {COLORS['grey_300']};
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}
    .section-title::before {{
        content: '';
        width: 4px;
        height: 1.25rem;
        background: {COLORS['primary']};
        border-radius: 2px;
    }}
    
    /* ── CHARTS CONTAINERS ── */
    .chart-container {{
        background: {COLORS['bg_white']};
        border-radius: 8px;
        padding: 1.5rem;
        border: 1px solid {COLORS['grey_300']};
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
    }}
    .chart-title {{
        font-size: 0.875rem;
        font-weight: 600;
        color: {COLORS['grey_700']};
        margin-bottom: 1rem;
    }}
    
    /* ── SIDEBAR FILTERS ── */
    [data-testid="stSidebar"] {{
        background: {COLORS['bg_white']};
        border-right: 1px solid {COLORS['grey_300']};
    }}
    [data-testid="stSidebar"] h3 {{
        font-size: 0.75rem;
        font-weight: 700;
        color: {COLORS['grey_600']};
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 1rem;
    }}
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stDateInput label {{
        font-size: 0.75rem;
        font-weight: 600;
        color: {COLORS['grey_600']};
    }}
    
    /* ── DATA TABLES ── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {COLORS['grey_300']};
        border-radius: 8px;
    }}
    
    /* ── METRICS ── */
    [data-testid="stMetric"] {{
        background: {COLORS['bg_white']};
        border: 1px solid {COLORS['grey_300']};
        border-radius: 8px;
        padding: 1rem 1.25rem;
    }}
    [data-testid="stMetric"] > div:first-child {{
        font-size: 0.7rem;
        font-weight: 600;
        color: {COLORS['grey_600']};
        text-transform: uppercase;
    }}
    [data-testid="stMetric"] > div:nth-child(2) {{
        font-size: 1.5rem;
        font-weight: 700;
    }}
    
    /* ── ALERTS ── */
    .alert-box {{
        padding: 1rem 1.25rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        font-size: 0.875rem;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
    }}
    .alert-danger {{
        background: #FFF5F5;
        border-left: 4px solid {COLORS['danger']};
        color: #C53030;
    }}
    .alert-success {{
        background: #F0FFF4;
        border-left: 4px solid {COLORS['success']};
        color: #276749;
    }}
    .alert-warning {{
        background: #FFFBF0;
        border-left: 4px solid {COLORS['warning']};
        color: #975A16;
    }}
    
    /* ── TWO COLUMN LAYOUT ── */
    .two-col {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
    }}
    
    /* ── THREE COLUMN LAYOUT ── */
    .three-col {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 1.5rem;
    }}
    
    /* ── FOOTER ── */
    .footer {{
        text-align: center;
        padding: 2rem;
        color: {COLORS['grey_500']};
        font-size: 0.75rem;
        border-top: 1px solid {COLORS['grey_300']};
        margin-top: 3rem;
    }}
    
    /* ── SPACING ── */
    .spacer {{ height: 1.5rem; }}
    </style>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# DONNÉES (MOCK - À REMPLACER PAR SSAS)
# ════════════════════════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def generate_data():
    """Génère les données de démonstration"""
    np.random.seed(42)
    
    dates = pd.date_range(start="2024-01-01", end="2026-04-27", freq="D")
    
    categories = {
        "41 - SON & IMAGE": ["TV OLED 55\"", "Barre de son", "Home cinema", "Casque audio", "Enceinte BT"],
        "42 - GROS ELECTROMENAGER": ["Frigo combine", "Lave-linge", "Lave-vaisselle", "Seche-linge", "Cuisiniere"],
        "43 - PRODUITS NOMADES": ["Smartphone", "Tablette", "Montre connectee", "Ordinateur portable", "Drone"],
        "44 - CHAUFFAGE ET CLIMATISATION": ["Climatiseur Split", "Radiateur-oil", "Chauffage soufflant", "Panneau rayonnant"],
        "45 - PETIT ELECTROMENAGER": ["Robot cuisine", "Aspirateur", "Cafetiere", "Friteuse", "Mixeur"]
    }
    
    prix_moyen = {
        "41 - SON & IMAGE": 2500, "42 - GROS ELECTROMENAGER": 3500,
        "43 - PRODUITS NOMADES": 1800, "44 - CHAUFFAGE ET CLIMATISATION": 4000,
        "45 - PETIT ELECTROMENAGER": 800
    }
    
    magasins = ["MG TUNIS", "MG ARIANA", "MG SOUSSE", "MG SFAX", "MG NABEUL", 
               "BATAM TUNIS", "BATAM ARIANA", "BATAM SOUSSE"]
    
    types_vente = ["Convention", "Credit conso", "Credit particulier", "Cash"]
    
    data = []
    for date in dates:
        saison = 1.0 + 0.25 * np.sin(2 * np.pi * date.month / 12)
        for _ in range(np.random.randint(40, 120)):
            cat = np.random.choice(list(categories.keys()))
            produit = np.random.choice(categories[cat])
            mag = np.random.choice(magasins)
            type_v = np.random.choice(types_vente, p=[0.35, 0.30, 0.25, 0.10])
            
            pu = prix_moyen[cat] * np.random.uniform(0.7, 1.4)
            qte = np.random.randint(1, 6)
            ca = qte * pu
            marge = ca * np.random.uniform(0.15, 0.32)
            
            data.append({
                "Date": date, "Annee": date.year, "Mois": date.month, "Jour": date.day,
                "JourSemaine": date.dayofweek, "Categorie": cat, "Produit": produit,
                "Magasin": mag, "TypeVente": type_v, "Quantite": qte, "PrixUnitaire": pu,
                "CA": ca, "Marge": marge, "Enseigne": "BATAM" if "BATAM" in mag else "SMG"
            })
    
    return pd.DataFrame(data)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# FONCTIONS ANALYTIQUES
# ════════════════════════════════════════════════════════════════════════════════════════════════

def get_kpis(df, filters=None):
    """Calcule les KPIs principaux"""
    dff = df.copy()
    if filters:
        for col, val in filters.items():
            if val and val not in ["Tous", "Toutes"]:
                dff = dff[dff[col] == val]
    
    if dff.empty:
        return {"CA": 0, "CA_N1": 0, "Evol": 0, "Panier": 0, "Tickets": 0, "MargePct": 0, "TopProd": "-", "Qte": 0}
    
    current_year = datetime.now().year
    prev_year = current_year - 1
    
    ca = dff[dff["Annee"] == current_year]["CA"].sum()
    ca_n1 = dff[dff["Annee"] == prev_year]["CA"].sum() if prev_year in dff["Annee"].values else 1
    evol = ((ca - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else 0
    
    tickets = len(dff[dff["Annee"] == current_year])
    panier = ca / tickets if tickets > 0 else 0
    qte = dff[dff["Annee"] == current_year]["Quantite"].sum()
    marge = dff[dff["Annee"] == current_year]["Marge"].sum()
    tx_marge = (marge / ca * 100) if ca > 0 else 0
    
    top_prod = dff[dff["Annee"] == current_year].groupby("Produit")["CA"].sum().idxmax() if not dff[dff["Annee"] == current_year].empty else "-"
    
    return {"CA": ca, "CA_N1": ca_n1, "Evol": evol, "Panier": panier, "Tickets": tickets, "MargePct": tx_marge, "TopProd": top_prod, "Qte": qte}


def get_top_products(df, n=10):
    """Top produits par CA"""
    return df.groupby("Produit")["CA"].sum().nlargest(n)


def get_magasin_perf(df):
    """Performance par magasin"""
    mag = df.groupby("Magasin").agg({"CA": "sum", "Quantite": "sum"}).reset_index()
    mag = mag.sort_values("CA", ascending=False)
    return mag


def get_business_model(df):
    """Répartition type de vente"""
    bm = df.groupby("TypeVente")["CA"].sum().reset_index()
    bm["Pct"] = bm["CA"] / bm["CA"].sum() * 100
    return bm.sort_values("CA", ascending=False)


def get_cat_evolution(df):
    """Evolution par catégorie N vs N-1"""
    current_year = datetime.now().year
    
    cat_n = df[df["Annee"] == current_year].groupby("Categorie")["CA"].sum()
    cat_n1 = df[df["Annee"] == current_year - 1].groupby("Categorie")["CA"].sum()
    
    evol = ((cat_n - cat_n1) / cat_n1.replace(0, 1) * 100).sort_values()
    return evol


# ════════════════════════════════════════════════════════════════════════════════════════════════
# COMPOSANTS VISUELS
# ════════════════════════════════════════════════════════════════════════════════════════════════

def kpi_card(label, value, delta=None, highlight=False):
    """Affiche une carte KPI corporate"""
    if delta is not None:
        if delta > 0:
            delta_html = f'<span class="delta-up">▲ {delta:+.1f}%</span>'
        elif delta < 0:
            delta_html = f'<span class="delta-down">▼ {delta:+.1f}%</span>'
        else:
            delta_html = '<span class="delta-neutral">= 0%</span>'
    else:
        delta_html = ""
    
    highlight_class = "highlight" if highlight else ""
    
    st.markdown(f"""
    <div class="kpi-card {highlight_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value:,.0f}</div>
        <div class="kpi-delta">{delta_html}</div>
    </div>
    """, unsafe_allow_html=True)


def kpi_card_simple(label, value, suffix=""):
    """Carte KPI simple sans delta"""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value:,}{suffix}</div>
    </div>
    """, unsafe_allow_html=True)


def chart_card(title, fig):
    """Container pour graphique"""
    st.markdown(f'<div class="chart-container"><div class="chart-title">{title}</div></div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)


def plot_ca_trend(df):
    """Graphique tendance CA"""
    df_grouped = df.groupby("Date")["CA"].sum().reset_index().sort_values("Date")
    
    fig = px.area(
        df_grouped, x="Date", y="CA",
        title=None,
        color_discrete_sequence=[COLORS["primary"]]
    )
    fig.update_layout(
        template="plotly_white",
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis=dict(tickformat=",.0f", gridcolor=COLORS["grey_300"]),
        xaxis=dict(gridcolor=COLORS["grey_300"])
    )
    fig.update_traces(line=dict(width=2))
    return fig


def plot_top_products_chart(top_products):
    """Graphique top produits"""
    top = top_products.reset_index().sort_values("CA")
    
    fig = px.bar(
        top, x="CA", y="Produit",
        orientation="h",
        title=None,
        color_discrete_sequence=[COLORS["primary"]]
    )
    fig.update_layout(
        template="plotly_white",
        height=max(300, len(top) * 35),
        yaxis=dict(autorange="reversed", gridcolor=COLORS["grey_300"]),
        xaxis=dict(gridcolor=COLORS["grey_300"]),
        margin=dict(l=150, r=20, t=20, b=20)
    )
    fig.update_traces(texttemplate="%{x:,.0f}", textposition="outside", textfont_size=10)
    return fig


def plot_magasin_chart(magasin_df):
    """Graphique performance magasins"""
    mag = magasin_df.head(12).sort_values("CA")
    
    fig = px.bar(
        mag, x="CA", y="Magasin",
        orientation="h",
        title=None,
        color_discrete_sequence=[COLORS["primary"]]
    )
    fig.update_layout(
        template="plotly_white",
        height=max(350, len(mag) * 35),
        yaxis=dict(autorange="reversed", gridcolor=COLORS["grey_300"]),
        xaxis=dict(gridcolor=COLORS["grey_300"]),
        margin=dict(l=150, r=20, t=20, b=20)
    )
    return fig


def plot_business_model_chart(bm):
    """Graphique type de vente"""
    colors = [COLORS["primary"], COLORS["primary_light"], COLORS["grey_600"], COLORS["grey_500"]]
    
    fig = go.Figure(data=[
        go.Pie(
            labels=bm["TypeVente"],
            values=bm["CA"],
            hole=0.5,
            marker_colors=colors,
            textinfo="percent+label",
            textposition="inside",
            textfont=dict(size=11, color="white")
        )
    ])
    fig.update_layout(
        template="plotly_white",
        height=280,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False
    )
    return fig


def plot_cat_evolution(evol):
    """Graphique évolution catégories"""
    colors = [COLORS["success"] if x >= 0 else COLORS["danger"] for x in evol]
    
    fig = px.bar(
        x=evol.index, y=evol.values,
        title=None,
        color=colors,
        color_discrete_map="identity"
    )
    fig.update_layout(
        template="plotly_white",
        height=300,
        yaxis=dict(tickformat="+.1f", gridcolor=COLORS["grey_300"], title="Evolution %"),
        xaxis=dict(gridcolor=COLORS["grey_300"]),
        margin=dict(l=40, r=20, t=20, b=40)
    )
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS["grey_600"])
    return fig


# ════════════════════════════════════════════════════════════════════════════════════════════════
# VUES PAR UNIVERS
# ════════════════════════════════════════════════════════════════════════════════════════════════

def render_univers_view(df, univers):
    """Affiche la vue détaillée d'un univers"""
    df_u = df[df["Categorie"] == univers]
    
    if df_u.empty:
        st.warning(f"Aucune donnée pour {univers}")
        return
    
    kpis = get_kpis(df_u)
    
    # KPIs univers
    st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
    kpi_card("CA", kpis["CA"], kpis["Evol"])
    kpi_card("Tickets", kpis["Tickets"])
    kpi_card("Panier Moyen", kpis["Panier"])
    kpi_card("Top Produit", kpis["TopProd"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Graphiques
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown('<div class="chart-container"><div class="chart-title">Top 10 Produits</div></div>', unsafe_allow_html=True)
        top = get_top_products(df_u, 10)
        fig = plot_top_products_chart(top)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown('<div class="chart-container"><div class="chart-title">Performance Magasins</div></div>', unsafe_allow_html=True)
        mag = get_magasin_perf(df_u)
        fig = plot_magasin_chart(mag)
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ════════════════════════════════════════════════════════════════════════════════════════════════

def main():
    inject_css()
    
    # ==================== HEADER ====================
    now = datetime.now()
    st.markdown(f"""
    <div class="header-container">
        <div>
            <div class="header-title">Pilotage Commercial SMG</div>
            <div class="header-subtitle">Tableau de bord ventes - Electromenager & Multimédia</div>
        </div>
        <div class="header-meta">
            <div class="header-badge">🟢 Données en direct</div>
            <div class="header-badge">📅 {now.strftime('%B %Y').capitalize()}</div>
            <div class="header-badge">🔄 {now.strftime('%d/%m %H:%M')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==================== SIDEBAR FILTRES ====================
    with st.sidebar:
        st.markdown("### Filtres")
        
        date_range = st.date_input(
            "Période",
            value=(datetime(2024, 1, 1), now),
            help="Sélectionnez la période"
        )
        
        categories = ["Toutes"] + sorted([
            "41 - SON & IMAGE", "42 - GROS ELECTROMENAGER",
            "43 - PRODUITS NOMADES", "44 - CHAUFFAGE ET CLIMATISATION",
            "45 - PETIT ELECTROMENAGER"
        ])
        cat_sel = st.selectbox("Catégorie", categories)
        
        all_magasins = ["Tous"] + sorted([
            "MG TUNIS", "MG ARIANA", "MG SOUSSE", "MG SFAX", "MG NABEUL",
            "BATAM TUNIS", "BATAM ARIANA", "BATAM SOUSSE"
        ])
        mag_sel = st.selectbox("Magasin", all_magasins)
        
        type_sel = st.selectbox("Type de vente", ["Tous", "Convention", "Credit conso", "Credit particulier", "Cash"])
        
        st.markdown("---")
        
        if st.button("Actualiser les données", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.caption("Source: SMGTAB/VENTES (SSAS)")
    
    # ==================== CHARGEMENT DONNÉES ====================
    with st.spinner("Chargement des données..."):
        df = generate_data()
    
    if df.empty:
        st.error("Aucune donnée disponible")
        return
    
    # ==================== FILTRAGE ====================
    filters = {}
    if cat_sel != "Toutes":
        filters["Categorie"] = cat_sel
    if mag_sel != "Tous":
        filters["Magasin"] = mag_sel
    if type_sel != "Tous":
        filters["TypeVente"] = type_sel
    
    df_filt = df.copy()
    for col, val in filters.items():
        df_filt = df_filt[df_filt[col] == val]
    
    # ==================== VUE GLOBALE - KPIs PRINCIPAUX ====================
    st.markdown('<div class="section-title">Indicateurs Clés</div>', unsafe_allow_html=True)
    
    kpis = get_kpis(df_filt, filters)
    
    # Ligne principale - CA, Evolution, Top Produit (PRIORITÉ)
    st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
    kpi_card("CHIFFRE D'AFFAIRES", kpis["CA"], kpis["Evol"], highlight=True)
    kpi_card("CA N-1", kpis["CA_N1"])
    kpi_card("TOP PRODUIT", kpis["TopProd"])
    kpi_card("ÉVOLUTION N-1", kpis["Evol"], None)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Ligne secondaire
    st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
    kpi_card_simple("Tickets", kpis["Tickets"])
    kpi_card_simple("Panier Moyen", kpis["Panier"], " TND")
    kpi_card_simple("Quantités Vendues", kpis["Qte"])
    kpi_card_simple("Taux de Marge", round(kpis["MargePct"], 1), " %")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
    
    # ==================== ANALYSES ====================
    st.markdown('<div class="section-title">Analyse Globale</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown('<div class="chart-container"><div class="chart-title">Évolution par Catégorie (N vs N-1)</div></div>', unsafe_allow_html=True)
        evol = get_cat_evolution(df_filt)
        fig = plot_cat_evolution(evol)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown('<div class="chart-container"><div class="chart-title">Répartition Type de Vente</div></div>', unsafe_allow_html=True)
        bm = get_business_model(df_filt)
        fig = plot_business_model_chart(bm)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown('<div class="chart-container"><div class="chart-title">Top 15 Produits</div></div>', unsafe_allow_html=True)
        top = get_top_products(df_filt, 15)
        fig = plot_top_products_chart(top)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown('<div class="chart-container"><div class="chart-title">Performance Magasins</div></div>', unsafe_allow_html=True)
        mag = get_magasin_perf(df_filt)
        fig = plot_magasin_chart(mag)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
    
    # ==================== ONGLETS UNIVERS ====================
    st.markdown('<div class="section-title">Analyse par Univers</div>', unsafe_allow_html=True)
    
    univers_tabs = st.tabs([
        "41 - SON & IMAGE",
        "42 - GROS ELECTROMENAGER",
        "43 - PRODUITS NOMADES",
        "44 - CHAUFFAGE & CLIM",
        "45 - PETIT ELECTRO"
    ])
    
    univers_list = [
        "41 - SON & IMAGE",
        "42 - GROS ELECTROMENAGER",
        "43 - PRODUITS NOMADES",
        "44 - CHAUFFAGE ET CLIMATISATION",
        "45 - PETIT ELECTROMENAGER"
    ]
    
    for i, tab in enumerate(univers_tabs):
        with tab:
            render_univers_view(df_filt, univers_list[i])
    
    # ==================== FOOTER ====================
    st.markdown(f"""
    <div class="footer">
        SMG - Pilotage Commercial | Connexion: SMGTAB/VENTES | Mis à jour: {now.strftime('%d/%m/%Y à %H:%M')}
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()