"""
==================================================================================================
DASHBOARD RETAIL SMG - PILOTAGE COMMERCIAL VENTES ÉLECTROMÉNAGER
==================================================================================================
Version: 2.0 - Optimise pour connexion Excel + Pret pour SSAS
==================================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
import os

warnings.filterwarnings('ignore')

# ════════════════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION & STYLE
# ════════════════════════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Dashboard Retail SMG - Pilotage Commercial",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Palette de couleurs
COLORS = {
    "primary": "#1e3a8a",
    "secondary": "#0d9488",
    "success": "#059669",
    "danger": "#dc2626",
    "warning": "#d97706",
    "info": "#0284c7",
    "dark": "#0f172a",
    "muted": "#64748b",
    "batam": "#f97316",
    "smg": "#1d4ed8",
}


def inject_css():
    """CSS personnalise"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background: linear-gradient(180deg, #f0f4ff 0%, #f7fafc 50%, #f0fdf4 100%); }
    .block-container { padding: 1rem 2rem; max-width: 1600px; }
    
    /* KPI Cards */
    .kpi-card {
        background: white;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.12); }
    .kpi-label { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-value { font-size: 1.75rem; font-weight: 800; color: #0f172a; margin: 0.25rem 0; }
    .kpi-delta { font-size: 0.85rem; font-weight: 600; }
    .delta-pos { color: #059669; }
    .delta-neg { color: #dc2626; }
    .delta-neu { color: #64748b; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0a0f1e 0%, #1a3060 100%); }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: white !important; }
    
    /* Metrics */
    [data-testid="stMetric"] { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; }
    
    /* Tabs */
    [data-testid="stTabs"] button[role="tab"] { border-radius: 10px 10px 0 0; padding: 0.75rem 1.5rem; font-weight: 600; }
    [data-testid="stTabs"] button[aria-selected="true"] { background: linear-gradient(135deg, #1e3a8a, #0d9488); color: white !important; }
    
    /* Charts */
    div[data-testid="stPlotlyChart"] { background: white; border-radius: 16px; padding: 1rem; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
    
    /* Section */
    .section-header { font-size: 1.1rem; font-weight: 700; color: #0f172a; margin: 1.5rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid #1e3a8a; }
    
    /* Alerts */
    .alert-card { border-radius: 12px; padding: 1rem; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.75rem; }
    .alert-danger { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; }
    .alert-warning { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }
    .alert-success { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }
    </style>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES - VERSION HYBRIDE (Excel + Mock + SSAS)
# ════════════════════════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800)
def load_data():
    """
    Charge les données depuis Excel (source principale)
    + Mode backup: données mockées
    """
    
    excel_path = r"C:\Users\hachk\OneDrive - Société Magasin Général (SMG)\Documents\hamadi\DASH GEM.xlsx"
    
    # Essaie d'abord le fichier Excel
    if os.path.exists(excel_path):
        try:
            st.info(f"Chargement des donnees depuis: {excel_path}")
            df = load_from_excel(excel_path)
            if not df.empty:
                st.success(f"Donnees chargees: {len(df)} lignes")
                return df, "excel"
        except Exception as e:
            st.warning(f"Erreur chargement Excel: {e}")
    
    # Fallback: génération données mock
    st.info("Utilisation des donnees de demonstration")
    df = generate_mock_data()
    return df, "mock"


def load_from_excel(file_path):
    """Charge et parse le fichier Excel DASH GEM"""
    
    # Feuilles à tester
    sheets_to_try = ["vente par jours", "vente par article", "CA PAR MAGASIN", "CA TOTAL CHAINE EM N N-1"]
    
    dfs = []
    
    for sheet in sheets_to_try:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, nrows=1000)
            if not df.empty:
                df["Source_Sheet"] = sheet
                dfs.append(df)
        except:
            pass
    
    if dfs:
        # Combine all sheets
        combined = pd.concat(dfs, ignore_index=True)
        return clean_excel_data(combined)
    
    return pd.DataFrame()


def clean_excel_data(df):
    """Nettoie les données Excel"""
    # Supprime les lignes vide
    df = df.dropna(how='all')
    
    # Renomme les colonnes
    df.columns = df.columns.str.strip()
    
    return df


@st.cache_data(ttl=3600)
def generate_mock_data():
    """Génère des données mock réalistes pour demonstration"""
    np.random.seed(42)
    
    dates = pd.date_range(start="2024-01-01", end="2026-04-27", freq="D")
    
    categories = {
        "41 - SON & IMAGE": ["TV OLED 55\"", "Barre de son", "Home cinema", "Casque audio", "Enceinte BT", "Soundbar", "Projecteur"],
        "42 - GROS ELECTROMENAGER": ["Frigo combine", "Lave-linge", "Lave-vaisselle", "Seche-linge", "Cuisiniere", "Four encastrable", "Plaque cuisson"],
        "43 - PRODUITS NOMADES": ["Smartphone", "Tablette", "Montre connectee", "Ordinateur portable", "Drone", "Appareil photo", "GPS"],
        "44 - CHAUFFAGE ET CLIMATISATION": ["Climatiseur Split", "Radiateur-oil", "Chauffage soufflant", "Panneau rayonnant", "Pompe a chaleur", "Chauffe-eau"],
        "45 - PETIT ELECTROMENAGER": ["Robot cuisine", "Aspirateur", "Cafetiere", "Friteuse", "Grille-pain", "Mixeur", "Fer a repasser"]
    }
    
    produits_par_cat = {cat: produits for cat, produits in categories.items()}
    all_produits = [(p, c) for c, produits in categories.items() for p in produits]
    
    magasins = [
        "MG TUNIS", "MG ARIANA", "MG BORJ LOUZIR", "MG SOUSSE", "MG SFAX",
        "MG NABEUL", "MG KAIROUAN", "MG BEJA", "MG BIZERTE",
        "BATAM TUNIS", "BATAM ARIANA", "BATAM SOUSSE", "BATAM SFAX", "BATAM NABEUL"
    ]
    
    types_vente = ["Convention", "Credit conso", "Credit particulier", "Cash"]
    
    # Prix moyens par catégorie
    prix_moyen = {
        "41 - SON & IMAGE": 2500,
        "42 - GROS ELECTROMENAGER": 3500,
        "43 - PRODUITS NOMADES": 1800,
        "44 - CHAUFFAGE ET CLIMATISATION": 4000,
        "45 - PETIT ELECTROMENAGER": 800
    }
    
    data = []
    
    for date in dates:
        # Jour de la semaine (0=lundi)
        jour_sem = date.dayofweek
        
        # Facteur saisonnier
        saison = 1.0 + 0.3 * np.sin(2 * np.pi * date.month / 12)
        
        # Week-end boost
        weekend_factor = 1.3 if jour_sem >= 5 else 1.0
        
        for _ in range(np.random.randint(50, 150)):
            cat = np.random.choice(list(categories.keys()))
            produit = np.random.choice(categories[cat])
            mag = np.random.choice(magasins)
            type_v = np.random.choice(types_vente, p=[0.35, 0.30, 0.25, 0.10])
            
            # Prix avec variation
            base_prix = prix_moyen[cat]
            variation_prix = np.random.uniform(0.7, 1.5)
            pu = base_prix * variation_prix
            
            # Quantité
            qte = np.random.randint(1, 8)
            
            # CA
            ca = qte * pu
            
            # Marge (15-35%)
            marge = ca * np.random.uniform(0.15, 0.35)
            
            data.append({
                "Date": date,
                "Annee": date.year,
                "Mois": date.month,
                "Jour": date.day,
                "JourSemaine": jour_sem,
                "Semestre": 1 if date.month <= 6 else 2,
                "Categorie": cat,
                "Produit": produit,
                "Magasin": mag,
                "TypeVente": type_v,
                "Quantite": qte,
                "PrixUnitaire": pu,
                "CA": ca,
                "Marge": marge,
                "MargePct": marge / ca * 100,
                "Enseigne": "BATAM" if "BATAM" in mag else "SMG"
            })
    
    return pd.DataFrame(data)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# FONCTIONS ANALYTIQUES
# ════════════════════════════════════════════════════════════════════════════════════════════════

def calculate_kpis(df, filters=None):
    """Calcule les KPIs executifs"""
    
    dff = df.copy()
    if filters:
        for col, val in filters.items():
            if val and val != "Tous" and val != "Toutes":
                dff = dff[dff[col] == val]
    
    if dff.empty:
        return {k: 0 for k in ["CA", "Evol_N1", "Evol_Obj", "PanierMoyen", "Tickets", 
                               "Quantite", "Marge", "TxMarge", "Contribution", "RunRate"]}
    
    current_year = datetime.now().year
    prev_year = current_year - 1
    
    df_n = dff[dff["Annee"] == current_year]
    df_n1 = dff[dff["Annee"] == prev_year]
    
    ca_n = df_n["CA"].sum()
    ca_n1 = df_n1["CA"].sum() if not df_n1.empty else 1
    
    evol = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else 0
    ca_obj = ca_n1 * 1.10
    evol_obj = ((ca_n - ca_obj) / ca_obj * 100) if ca_obj > 0 else 0
    
    qte_n = df_n["Quantite"].sum()
    marge_n = df_n["Marge"].sum()
    tx_marge = (marge_n / ca_n * 100) if ca_n > 0 else 0
    
    tickets_n = len(df_n)
    panier = ca_n / tickets_n if tickets_n > 0 else 0
    
    jours_passes = max((datetime.now() - datetime(current_year, 1, 1)).days, 1)
    run_rate = ca_n / jours_passes
    
    return {
        "CA": ca_n,
        "CA_N1": ca_n1,
        "Evol_N1": evol,
        "Evol_Obj": evol_obj,
        "PanierMoyen": panier,
        "Tickets": tickets_n,
        "Quantite": qte_n,
        "Marge": marge_n,
        "TxMarge": tx_marge,
        "RunRate": run_rate
    }


def generate_alerts(df):
    """Genere les alertes automatiques"""
    alerts = []
    
    current_year = datetime.now().year
    df_n = df[df["Annee"] == current_year]
    df_n1 = df[df["Annee"] == current_year - 1]
    
    if df_n.empty:
        return alerts
    
    # Produits en forte baisse
    ca_n = df_n.groupby("Produit")["CA"].sum()
    ca_n1 = df_n1.groupby("Produit")["CA"].sum()
    evol = ((ca_n - ca_n1) / ca_n1.replace(0, 1) * 100)
    
    for prod in evol[evol < -30].sort_values().index[:5]:
        alerts.append({"type": "danger", "category": "Produit", "message": f"{prod}: {evol[prod]:.1f}% vs N-1"})
    
    # Magasins sous-performants
    mag_n = df_n.groupby("Magasin")["CA"].sum()
    mag_n1 = df_n1.groupby("Magasin")["CA"].sum()
    evol_mag = ((mag_n - mag_n1) / mag_n1.replace(0, 1) * 100)
    
    for mag in evol_mag[evol_mag < -20].sort_values().index[:3]:
        alerts.append({"type": "warning", "category": "Magasin", "message": f"{mag}: {evol_mag[mag]:.1f}% vs N-1"})
    
    # Categories en croissance
    cat_n = df_n.groupby("Categorie")["CA"].sum()
    cat_n1 = df_n1.groupby("Categorie")["CA"].sum()
    evol_cat = ((cat_n - cat_n1) / cat_n1.replace(0, 1) * 100)
    
    for cat in evol_cat[evol_cat > 20].sort_values(ascending=False).index[:2]:
        alerts.append({"type": "success", "category": "Categorie", "message": f"{cat}: +{evol_cat[cat]:.1f}% vs N-1"})
    
    return alerts


# ════════════════════════════════════════════════════════════════════════════════════════════════
# FONCTIONS DE VISUALISATION
# ════════════════════════════════════════════════════════════════════════════════════════════════

def plot_ca_temporal(df, title="CA"):
    df_grouped = df.groupby("Date")["CA"].sum().reset_index().sort_values("Date")
    fig = px.line(df_grouped, x="Date", y="CA", title=title, color_discrete_sequence=[COLORS["primary"]])
    fig.update_layout(template="plotly_white", height=350, yaxis=dict(tickformat=",.0f"), xaxis=dict(rangeslider=dict(visible=True)))
    fig.update_traces(mode="lines+markers", line=dict(width=2))
    return fig


def plot_top_products(df, n=10):
    top = df.groupby("Produit")["CA"].sum().nlargest(n).reset_index().sort_values("CA")
    fig = px.bar(top, x="CA", y="Produit", orientation="h", title=f"Top {n} Produits", color_discrete_sequence=[COLORS["primary"]])
    fig.update_layout(template="plotly_white", height=max(300, n*30), yaxis=dict(autorange="reversed"))
    return fig


def plot_magasin_performance(df, n=15):
    mag = df.groupby("Magasin").agg({"CA": "sum", "Marge": "sum"}).reset_index()
    mag["Tx_Marge"] = mag["Marge"] / mag["CA"] * 100
    mag = mag.sort_values("CA", ascending=False).head(n)
    
    fig = px.bar(mag, x="CA", y="Magasin", orientation="h", title=f"Top {n} Magasins", 
                 color="Tx_Marge", color_continuous_scale=["#dc2626", "#fcd34d", "#059669"])
    fig.update_layout(template="plotly_white", height=max(400, n*30), yaxis=dict(autorange="reversed"))
    return fig


def plot_business_model(df):
    bm = df.groupby("TypeVente").agg({"CA": "sum", "Quantite": "sum"}).reset_index()
    colors = [COLORS["primary"], COLORS["secondary"], COLORS["warning"], COLORS["info"]]
    
    fig = go.Figure(data=[go.Pie(labels=bm["TypeVente"], values=bm["CA"], hole=0.5, 
                                  marker_colors=colors, textinfo="percent+label")])
    fig.update_layout(title="Repartition Type Vente", template="plotly_white", height=350)
    return fig


def plot_category_comparison(df):
    current_year = datetime.now().year
    
    cat_n = df[df["Annee"] == current_year].groupby("Categorie")["CA"].sum().reset_index()
    cat_n1 = df[df["Annee"] == current_year - 1].groupby("Categorie")["CA"].sum().reset_index()
    
    cat = cat_n.merge(cat_n1, on="Categorie", how="outer", suffixes=("_N", "_N1")).fillna(0)
    cat["Evolution"] = (cat["CA_N"] - cat["CA_N1"]) / cat["CA_N1"].replace(0, 1) * 100
    cat = cat.sort_values("Evolution")
    
    colors = [COLORS["success"] if x >= 0 else COLORS["danger"] for x in cat["Evolution"]]
    
    fig = px.bar(cat, x="Categorie", y="Evolution", title="Evolution N vs N-1 (%)", color=colors, color_discrete_map="identity")
    fig.update_layout(template="plotly_white", height=400, yaxis=dict(tickformat="+.1f"))
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS["muted"])
    return fig


def plot_heatmap(df):
    df_f = df[df["Annee"] == datetime.now().year]
    heatmap = df_f.pivot_table(values="CA", index="JourSemaine", columns="Mois", aggfunc="sum").fillna(0)
    jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    heatmap.index = jours
    
    fig = px.imshow(heatmap, labels=dict(x="Mois", y="Jour", color="CA"), color_continuous_scale="Blues", title="Heatmap CA: Jour x Mois")
    fig.update_layout(height=300)
    return fig


# ════════════════════════════════════════════════════════════════════════════════════════════════
# COMPOSANTS UI
# ════════════════════════════════════════════════════════════════════════════════════════════════

def display_kpi_card(label, value, delta=None, format="number", suffix=""):
    if format == "currency":
        formatted = f"{value:,.0f} TND"
    elif format == "percent":
        formatted = f"{value:.1f}%"
    else:
        formatted = f"{value:,.0f}"
    
    if delta is not None:
        if delta > 0:
            delta_str = f"+{delta:.1f}%"
            cls = "delta-pos"
        elif delta < 0:
            delta_str = f"{delta:.1f}%"
            cls = "delta-neg"
        else:
            delta_str = "= 0%"
            cls = "delta-neu"
    else:
        delta_str = ""
        cls = "delta-neu"
    
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{formatted}{suffix}</div>
        <div class="kpi-delta {cls}">{delta_str}</div>
    </div>
    """, unsafe_allow_html=True)


def display_alerts(alerts):
    for alert in alerts:
        icon = "!" if alert["type"] == "danger" else ("i" if alert["type"] == "warning" else "+")
        st.markdown(f"""
        <div class="alert-card alert-{alert['type']}">
            <span style="font-size:1.25rem;">{icon}</span>
            <div><strong>{alert['category']}</strong>: {alert['message']}</div>
        </div>
        """, unsafe_allow_html=True)


def render_univers_tab(df, univers):
    """Affiche les donnees pour un univers produit"""
    df_u = df[df["Categorie"] == univers]
    
    if df_u.empty:
        st.warning(f"Aucune donnee pour {univers}")
        return
    
    kpis = calculate_kpis(df_u)
    
    # KPIs ligne
    cols = st.columns(6)
    with cols[0]: st.metric("CA", f"{kpis['CA']:,.0f}", f"{kpis['Evol_N1']:+.1f}%")
    with cols[1]: st.metric("vs Obj", f"{kpis['Evol_Obj']:+.1f}%")
    with cols[2]: st.metric("Panier", f"{kpis['PanierMoyen']:,.0f}")
    with cols[3]: st.metric("Qte", f"{kpis['Quantite']:,}")
    with cols[4]: st.metric("Marge", f"{kpis['TxMarge']:.1f}%")
    with cols[5]: st.metric("Tickets", f"{kpis['Tickets']:,}")
    
    st.markdown("")
    
    # Analyses
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(plot_top_products(df_u, 10), use_container_width=True)
    with c2:
        st.plotly_chart(plot_magasin_performance(df_u, 8), use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ════════════════════════════════════════════════════════════════════════════════════════════════

def main():
    inject_css()
    
    # ==================== HEADER ====================
    col_h1, col_h2 = st.columns([6, 1])
    with col_h1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0a0f1e, #1a3060, #0d3d34); 
                    border-radius: 16px; padding: 1.5rem; margin-bottom: 1rem; color: white;">
            <h1 style="margin:0; font-size:1.75rem; font-weight:800;">Dashboard Retail SMG</h1>
            <p style="margin:0.5rem 0 0; color:rgba(255,255,255,0.7);">Pilotage Commercial - Electromenager & Multim</p>
            <div style="margin-top:0.75rem; display:flex; gap:0.5rem;">
                <span style="background:rgba(255,255,255,0.1); padding:0.25rem 0.75rem; border-radius:20px; font-size:0.75rem;">
                    Source: DASH GEM.xlsx / Donnees Demo
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_h2:
        if st.button("Actualiser", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # ==================== SIDEBAR ====================
    with st.sidebar:
        st.markdown("### Filtres")
        
        date_range = st.date_input("Periode", value=(datetime(2024, 1, 1), datetime.now()))
        
        st.markdown("---")
        
        categories = ["Toutes"] + sorted(["41 - SON & IMAGE", "42 - GROS ELECTROMENAGER", 
                                         "43 - PRODUITS NOMADES", "44 - CHAUFFAGE ET CLIMATISATION", 
                                         "45 - PETIT ELECTROMENAGER"])
        cat_sel = st.selectbox("Categorie", categories)
        
        all_magasins = ["Tous"] + sorted(["MG TUNIS", "MG ARIANA", "MG BORJ LOUZIR", "MG SOUSSE", "MG SFAX",
                                          "MG NABEUL", "MG KAIROUAN", "MG BEJA", "MG BIZERTE",
                                          "BATAM TUNIS", "BATAM ARIANA", "BATAM SOUSSE", "BATAM SFAX", "BATAM NABEUL"])
        mag_sel = st.selectbox("Magasin", all_magasins)
        
        type_sel = st.selectbox("Type de vente", ["Tous", "Convention", "Credit conso", "Credit particulier", "Cash"])
        
        st.markdown("---")
        st.markdown("### Exporter")
        st.download_button("Exporter CSV", data="", file_name="export.csv", disabled=True)
    
    # ==================== CHARGEMENT ====================
    with st.spinner("Chargement..."):
        df, source = load_data()
    
    if df.empty:
        st.error("Aucune donnee disponible")
        return
    
    # Filtres
    filters = {}
    if cat_sel != "Toutes":
        filters["Categorie"] = cat_sel
    if mag_sel != "Tous":
        filters["Magasin"] = mag_sel
    if type_sel != "Tous":
        filters["TypeVente"] = type_sel
    
    if filters:
        df = df.copy()
        for col, val in filters.items():
            df = df[df[col] == val]
    
    # ==================== VUE GLOBALE ====================
    st.markdown("## Vue Globale - KPIs")
    
    kpis = calculate_kpis(df)
    
    kcols = st.columns(6)
    with kcols[0]: display_kpi_card("CA Total", kpis["CA"], kpis["Evol_N1"], "currency")
    with kcols[1]: display_kpi_card("vs Objectif", kpis["Evol_Obj"], None, "percent")
    with kcols[2]: display_kpi_card("Panier", kpis["PanierMoyen"], None, "currency")
    with kcols[3]: display_kpi_card("Tickets", kpis["Tickets"], None, "number")
    with kcols[4]: display_kpi_card("Tx Marge", kpis["TxMarge"], None, "percent")
    with kcols[5]: display_kpi_card("Run Rate", kpis["RunRate"], None, "currency")
    
    st.markdown("---")
    
    # ==================== ALERTES ====================
    st.markdown("### Alertes & Insights")
    alerts = generate_alerts(df)
    
    if alerts:
        acols = st.columns(3)
        dangers = [a for a in alerts if a["type"] == "danger"]
        warnings = [a for a in alerts if a["type"] == "warning"]
        successes = [a for a in alerts if a["type"] == "success"]
        
        with acols[0]:
            if dangers: st.markdown("**! Alertes**"); display_alerts(dangers)
        with acols[1]:
            if warnings: st.markdown("**i A surveiller**"); display_alerts(warnings)
        with acols[2]:
            if successes: st.markdown("**+ Opportunites**"); display_alerts(successes)
    else:
        st.success("Aucune alerte majeure")
    
    st.markdown("---")
    
    # ==================== GRAPHIQUES ====================
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(plot_category_comparison(df), use_container_width=True)
    with c2: st.plotly_chart(plot_business_model(df), use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(plot_top_products(df, 15), use_container_width=True)
    with c2: st.plotly_chart(plot_magasin_performance(df, 15), use_container_width=True)
    
    # ==================== ONGLETS UNIVERS ====================
    st.markdown("---")
    st.markdown("## Univers Produits")
    
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
            render_univers_tab(df, univers_list[i])
    
    # ==================== FOOTER ====================
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center; color:#64748b; font-size:0.8rem; padding:1rem;">
        Dashboard Retail SMG | Source: {source} | MAJ: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()