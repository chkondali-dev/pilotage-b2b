import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
from io import BytesIO
from urllib.parse import quote

st.set_page_config(page_title="Dashboard Pilotage B2B - SMG", layout="wide", page_icon="📊")

# ============================================================
# SECTION 1: CONFIGURATION & DATA LOADING
# ============================================================
GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"
GITHUB_RAW_IMAGES = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/"
LOGO_MG_URL = GITHUB_RAW_IMAGES + "logo-1653837429.jpg"
LOGO_BATAM_URL = GITHUB_RAW_IMAGES + "logo.svg"

FILES = {
    "vc": quote("Factures ventes enregistrées VC (4).xlsx"),
    "vc_credit": quote("Factures ventes enregistrées VC credit conso.xlsx"),
    "vc_edc": quote("Factures ventes enregistrées VC CONVENTION EDC.xlsx"),
    "conventions_signees": quote("TDC CONVENTION 1.xlsm"),
    "code_magasin": quote("Code MAGASIN Business Central.xlsx")
}

COLORS = {
    'primary': '#00CC96',
    'secondary': '#636EFA',
    'accent': '#FF6692',
    'warning': '#EF553B',
    'purple': '#AB63FA'
}

MOIS_NOMS = {1: 'Jan', 2: 'Fév', 3: 'Mar', 4: 'Avr', 5: 'Mai', 6: 'Juin',
             7: 'Juil', 8: 'Aoû', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Déc'}

def get_logo_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return url
    except:
        return None

def load_from_url(filename):
    url = GITHUB_RAW + filename
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return pd.read_excel(BytesIO(response.content), engine='openpyxl')

def load_xlsm(filename):
    url = GITHUB_RAW + filename
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return pd.read_excel(BytesIO(response.content), engine='openpyxl', sheet_name=None)

def clean_columns(df):
    if df is not None and not df.empty:
        df.columns = df.columns.str.replace('\n', ' ').str.strip()
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str)
    return df

@st.cache_data
def load_all_data():
    dfs = {}
    for key, filename in FILES.items():
        try:
            if filename == FILES["conventions_signees"]:
                df = load_xlsm(filename)
                sheet_keys = list(df.keys())
                if sheet_keys:
                    dfs[key] = clean_columns(df[sheet_keys[0]])
            else:
                df = load_from_url(filename)
                dfs[key] = clean_columns(df)
        except Exception as e:
            st.warning(f"Erreur {key}: {e}")
    return dfs

def get_magasin_name(code, code_magasin_df):
    if code_magasin_df is None or code_magasin_df.empty:
        return str(code)
    code_magasin_df = code_magasin_df.copy()
    code_magasin_df.columns = [c.strip() for c in code_magasin_df.columns]
    for col in code_magasin_df.columns:
        if 'code' in col.lower():
            code_magasin_df[col] = code_magasin_df[col].astype(str).str.strip()
    code = str(code).strip()
    for col in code_magasin_df.columns:
        if 'code' in col.lower():
            match = code_magasin_df[code_magasin_df[col] == code]
            if not match.empty:
                for name_col in match.columns:
                    if 'unit' in name_col.lower() or 'nom' in name_col.lower() or 'magasin' in name_col.lower():
                        return match[name_col].values[0]
    return str(code)

# ============================================================
# SECTION 2: DATA PROCESSING
# ============================================================
def process_data(df_vc, df_credit, code_magasin_df):
    for df in [df_vc, df_credit]:
        if 'Date comptabilisation' in df.columns:
            df['Date'] = pd.to_datetime(df['Date comptabilisation'], errors='coerce')
            df['Année'] = df['Date'].dt.year
            df['Mois'] = df['Date'].dt.month
            df['Jour'] = df['Date'].dt.day
        if 'Code magasin' in df.columns and not code_magasin_df.empty:
            df['Magasin'] = df['Code magasin'].apply(lambda x: get_magasin_name(x, code_magasin_df))
    return df_vc, df_credit

def get_ca_journalier(df, annee, mois=None):
    df_annee = df[df['Année'] == annee].copy()
    if mois and mois != "Tous":
        df_annee = df_annee[df_annee['Mois'] == mois]
    return df_annee.groupby('Jour')['Montant TTC'].sum().reset_index()

def get_ca_mensuel(df, annee, mois=None):
    df_annee = df[df['Année'] == annee].copy()
    if mois and mois != "Tous":
        df_annee = df_annee[df_annee['Mois'] == mois]
    return df_annee.groupby('Mois')['Montant TTC'].sum().reset_index()

def compare_annees(df, annee_n, annee_n1, mois=None):
    if df is None or (hasattr(df, 'empty') and df.empty) or (hasattr(df, 'shape') and df.shape[0] == 0):
        return pd.DataFrame(columns=['Mois', 'CA N', 'CA N-1', 'Variation %', 'Mois Nom'])
    ca_n = get_ca_mensuel(df, annee_n, mois)
    ca_n1 = get_ca_mensuel(df, annee_n1, mois)
    if ca_n.empty:
        return pd.DataFrame(columns=['Mois', 'CA N', 'CA N-1', 'Variation %', 'Mois Nom'])
    ca_n.columns = ['Mois', 'CA N']
    ca_n1.columns = ['Mois', 'CA N-1']
    df_comp = ca_n.merge(ca_n1, on='Mois', how='outer').fillna(0)
    df_comp['Variation %'] = ((df_comp['CA N'] - df_comp['CA N-1']) / df_comp['CA N-1'].replace(0, 1) * 100).round(1)
    df_comp['Mois Nom'] = df_comp['Mois'].map(MOIS_NOMS)
    return df_comp

# ============================================================
# SECTION 3: VISUALIZATION
# ============================================================
def plot_bar_with_labels(df, x_col, y_col, title, color=COLORS['primary'], orientation='v'):
    if df is None or (hasattr(df, 'empty') and df.empty) or (hasattr(df, 'shape') and df.shape[0] == 0):
        fig = go.Figure()
        fig.update_layout(title=title, template='plotly_white', height=400)
        return fig
    if orientation == 'h':
        fig = px.bar(df, y=y_col, x=x_col, text_auto=',.0f', title=title, 
                    color_discrete_sequence=[color], orientation='h')
    else:
        fig = px.bar(df, x=x_col, y=y_col, text_auto=',.0f', title=title, 
                    color_discrete_sequence=[color])
    fig.update_layout(template='plotly_white', height=400)
    fig.update_traces(textposition='outside')
    return fig

def plot_line_with_markers(x, y, name, color=COLORS['primary'], dash=None):
    return go.Scatter(
        x=x, y=y, mode='lines+markers', name=name,
        line=dict(color=color, width=3), marker=dict(size=8),
        line_dash=dash
    )

def plot_comparison(df, x_col, y_n, y_n1, title, xlabel, ylabel):
    if df is None or (hasattr(df, 'empty') and df.empty) or (hasattr(df, 'shape') and df.shape[0] == 0):
        fig = go.Figure()
        fig.update_layout(title=title, template='plotly_white', height=400)
        return fig
    fig = go.Figure()
    fig.add_trace(plot_line_with_markers(df[x_col].values, df[y_n].values, 'N', COLORS['primary']))
    fig.add_trace(plot_line_with_markers(df[x_col].values, df[y_n1].values, 'N-1', COLORS['warning'], 'dash'))
    fig.update_layout(
        title=title, xaxis_title=xlabel, yaxis_title=ylabel,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template='plotly_white', height=400
    )
    return fig

def plot_pie(data, names, title, colors=None):
    fig = px.pie(values=data, names=names, title=title, hole=0.4, 
                color_discrete_sequence=colors or [COLORS['primary'], COLORS['secondary'], COLORS['accent']])
    fig.update_layout(template='plotly_white', height=400)
    return fig

def plot_horizontal_bar(df, x_col, y_col, title, top_n=10, color=COLORS['secondary']):
    try:
        if df is None or len(df) == 0:
            fig = go.Figure()
            fig.update_layout(title=title, template='plotly_white', height=400)
            return fig
        df_copy = df.copy()
        n = min(top_n, len(df_copy))
        if n <= 0:
            fig = go.Figure()
            fig.update_layout(title=title, template='plotly_white', height=400)
            return fig
        df_top = df_copy.nlargest(n, x_col)
        fig = px.bar(df_top, x=x_col, y=y_col, orientation='h', title=title, 
                    color_discrete_sequence=[color])
        fig.update_layout(template='plotly_white', height=400, yaxis=dict(autorange='reversed'))
        fig.update_traces(textposition='outside')
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.update_layout(title=title, template='plotly_white', height=400)
        return fig

# ============================================================
# SECTION 4: UI LAYOUT
# ============================================================
st.title("📊 DASHBOARD PILOTAGE B2B — SMG")

col_logo1, col_logo2 = st.columns([6, 1])
with col_logo1:
    mg_url = get_logo_url(LOGO_MG_URL)
    if mg_url:
        st.image(mg_url, width=100)
with col_logo2:
    batam_url = get_logo_url(LOGO_BATAM_URL)
    if batam_url:
        st.image(batam_url, width=100)

st.caption("Source: VC.CONV. Business Central")

if st.sidebar.button("🔄 Actualiser les données"):
    st.cache_data.clear()
    st.rerun()

data = load_all_data()
df_vc = data.get("vc", pd.DataFrame())
df_credit = data.get("vc_credit", pd.DataFrame())
df_edc = data.get("vc_edc", pd.DataFrame())
df_conventions = data.get("conventions_signees", pd.DataFrame())
code_magasin_df = data.get("code_magasin", pd.DataFrame())

df_vc, df_credit = process_data(df_vc, df_credit, code_magasin_df)

if 'Date comptabilisation' in df_edc.columns:
    df_edc['Date'] = pd.to_datetime(df_edc['Date comptabilisation'], errors='coerce')
    df_edc['Année'] = df_edc['Date'].dt.year
    df_edc['Mois'] = df_edc['Date'].dt.month

with st.sidebar:
    st.header("🔍 Filtres")
    annee_sel = st.selectbox("Année", [2026, 2025, 2024, 2023], index=0)
    mois_options = ["Tous"] + list(range(1, 13))
    mois_sel = st.selectbox("Mois", mois_options, index=4)
    
    if 'Nom' in df_vc.columns and 'Année' in df_vc.columns:
        convs_for_year = df_vc[df_vc['Année'] == annee_sel]['Nom'].dropna().unique().tolist()
        conventions = ["Tous"] + sorted(convs_for_year)
    else:
        conventions = ["Tous"]
    conv_sel = st.selectbox("Convention", conventions)
    
    st.markdown("---")
    st.caption("Filtres appliqués à tout le dashboard")

if 'Année' not in df_vc.columns or df_vc.empty:
    st.error("Aucune donnée chargée. Vérifiez les fichiers sur GitHub.")
    st.stop()

df_filt = df_vc[df_vc['Année'] == annee_sel].copy()
if mois_sel != "Tous":
    df_filt = df_filt[df_filt['Mois'] == mois_sel]
if conv_sel != "Tous":
    df_filt = df_filt[df_filt['Nom'] == conv_sel]

tabs = st.tabs([
    "🏠 ACCUEIL + DASHBOARD",
    "📅 CA JOURNALIER",
    "📋 CONVENTIONS",
    "🏪 MAGASINS",
    "🏫 EDC",
    "🔔 ALERTES",
    "📊 PERFORMANCE"
])

# ============================================================
# ONGLET ACCUEIL (KPIs + Tableaux clés + Graphiques globaux)
# ============================================================
with tabs[0]:
    st.header("DASHBOARD GRANDS COMPTES — SMG")
    
    col1, col2, col3, col4 = st.columns(4)
    
    ca_2024 = df_vc[df_vc['Année'] == 2024]['Montant TTC'].sum() if 'Année' in df_vc.columns else 0
    ca_2025 = df_vc[df_vc['Année'] == 2025]['Montant TTC'].sum() if 'Année' in df_vc.columns else 0
    ca_2026_ytd = df_vc[df_vc['Année'] == 2026]['Montant TTC'].sum() if 'Année' in df_vc.columns else 0

    delta_2025 = f"{((ca_2025 - ca_2024) / ca_2024 * 100):+.1f}% vs 2024" if ca_2024 > 0 else "N/A"
    delta_2026 = f"{((ca_2026_ytd - ca_2025) / ca_2025 * 100):+.1f}% vs YTD 2025" if ca_2025 > 0 else "N/A"

    convs_actives_2026 = df_vc[df_vc['Année'] == 2026]['Nom'].dropna().nunique() if 'Nom' in df_vc.columns else 0
    total_conventions = len(df_conventions) if not df_conventions.empty else 0
    convs_inactives = max(0, total_conventions - convs_actives_2026)

    col1.metric("CA 2025", f"{ca_2025:,.0f} TND", delta=delta_2025)
    col2.metric("CA 2026 YTD", f"{ca_2026_ytd:,.0f} TND", delta=delta_2026)
    col3.metric("Conventions Actives", str(convs_actives_2026))
    col4.metric("Conventions Inactives", str(convs_inactives), delta="à réactiver", delta_color="inverse")
    
    st.markdown("---")
    st.subheader("CA par année & Top Conventions")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        if 'Année' in df_vc.columns:
            ca_year = df_vc.groupby('Année')['Montant TTC'].sum().reset_index()
            fig = plot_bar_with_labels(ca_year, 'Année', 'Montant TTC', "CA par année", COLORS['primary'])
            st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        if 'Nom' in df_filt.columns:
            top_conv = df_filt.groupby('Nom')['Montant TTC'].sum().nlargest(10).reset_index()
            fig2 = plot_horizontal_bar(top_conv, 'Montant TTC', 'Nom', "Top 10 Conventions", COLORS['secondary'])
            st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("---")
    st.subheader("CA Mensuel N vs N-1")
    
    col_g3, col_g4 = st.columns(2)
    
    with col_g3:
        df_comp = compare_annees(df_vc, annee_sel, annee_sel - 1, mois_sel if mois_sel != "Tous" else None)
        if not df_comp.empty:
            fig3 = plot_comparison(df_comp, 'Mois Nom', 'CA N', 'CA N-1', 
                               f"CA Mensuel {annee_sel} vs {annee_sel-1}", "Mois", "TND")
            st.plotly_chart(fig3, use_container_width=True)
    
    with col_g4:
        maintenant = pd.Timestamp.now()
        mois_list = []
        for i in range(2, -1, -1):
            m = maintenant - pd.DateOffset(months=i)
            mois_list.append((m.year, m.month))
        
        df_3m = df_vc[df_vc['Année'].isin([x[0] for x in mois_list])].copy()
        df_3m = df_3m[(df_3m['Année'].astype(str) + '-' + df_3m['Mois'].astype(str).str.zfill(2)).isin(
            [f"{x[0]}-{x[1]:02d}" for x in mois_list]
        )]
        
        ca_3m = df_3m.groupby(['Année', 'Mois'])['Montant TTC'].sum().reset_index()
        ca_3m['Periode'] = ca_3m['Mois'].map(MOIS_NOMS) + ' ' + ca_3m['Année'].astype(str)
        ca_3m = ca_3m.sort_values(['Année', 'Mois'])
        
        fig4 = plot_bar_with_labels(ca_3m, 'Periode', 'Montant TTC', "CA 3 derniers mois", COLORS['primary'])
        st.plotly_chart(fig4, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 👥 Top 3 / Flop 3 Clients (MOIS EN COURS)")
    
    if 'Nom' in df_filt.columns:
        ca_cli = df_filt.groupby('Nom')['Montant TTC'].sum().reset_index()
        ca_cli = ca_cli.sort_values('Montant TTC', ascending=False)
        
        top3_cli = ca_cli.head(3)
        flop3_cli = ca_cli.tail(3)
        
        col_tc, col_fc = st.columns(2)
        
        with col_tc:
            st.markdown("#### 🏆 Top 3 Clients")
            for i, (_, row) in enumerate(top3_cli.iterrows(), 1):
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #636EFA 0%, #4A52D6 100%); 
                padding: 20px; border-radius: 12px; margin-bottom: 10px; color: white;">
                    <h3 style="margin:0;">#{i} {row['Nom']}</h3>
                    <p style="font-size: 24px; margin: 10px 0 0 0; font-weight: bold;">{row['Montant TTC']:,.0f} TND</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col_fc:
            st.markdown("#### 📉 Flop 3 Clients")
            for i, (_, row) in enumerate(flop3_cli.iterrows(), 1):
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #AB63FA 0%, #8F42D6 100%); 
                padding: 20px; border-radius: 12px; margin-bottom: 10px; color: white;">
                    <h3 style="margin:0;">#{i} {row['Nom']}</h3>
                    <p style="font-size: 24px; margin: 10px 0 0 0; font-weight: bold;">{row['Montant TTC']:,.0f} TND</p>
                </div>
                """, unsafe_allow_html=True)

# ============================================================
with tabs[1]:
    st.header("DASHBOARD GLOBAL — MG & BATAM")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("CA par année")
        if 'Année' in df_vc.columns:
            ca_year = df_vc.groupby('Année')['Montant TTC'].sum().reset_index()
            fig = plot_bar_with_labels(ca_year, 'Année', 'Montant TTC', "CA par année", COLORS['primary'])
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Top 10 Conventions")
        if 'Nom' in df_filt.columns:
            top_conv = df_filt.groupby('Nom')['Montant TTC'].sum().nlargest(10).reset_index()
            fig2 = plot_horizontal_bar(top_conv, 'Montant TTC', 'Nom', "Top 10 Conventions", COLORS['secondary'])
            st.plotly_chart(fig2, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("CA Mensuel N vs N-1")
        df_comp = compare_annees(df_vc, annee_sel, annee_sel - 1, mois_sel if mois_sel != "Tous" else None)
        if not df_comp.empty:
            fig3 = plot_comparison(df_comp, 'Mois Nom', 'CA N', 'CA N-1', 
                               f"CA Mensuel {annee_sel} vs {annee_sel-1}", "Mois", "TND")
            st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        st.subheader("CA 3 derniers mois")
        maintenant = pd.Timestamp.now()
        mois_list = []
        for i in range(2, -1, -1):
            m = maintenant - pd.DateOffset(months=i)
            mois_list.append((m.year, m.month))
        
        df_3m = df_vc[df_vc['Année'].isin([x[0] for x in mois_list])].copy()
        df_3m = df_3m[(df_3m['Année'].astype(str) + '-' + df_3m['Mois'].astype(str).str.zfill(2)).isin(
            [f"{x[0]}-{x[1]:02d}" for x in mois_list]
        )]
        
        ca_3m = df_3m.groupby(['Année', 'Mois'])['Montant TTC'].sum().reset_index()
        ca_3m['Periode'] = ca_3m['Mois'].map(MOIS_NOMS) + ' ' + ca_3m['Année'].astype(str)
        ca_3m = ca_3m.sort_values(['Année', 'Mois'])
        
        fig4 = plot_bar_with_labels(ca_3m, 'Periode', 'Montant TTC', "CA 3 derniers mois", COLORS['primary'])
        st.plotly_chart(fig4, use_container_width=True)

# ============================================================
# ONGLET CA JOURNALIER (Graphique amélioré)
# ============================================================
with tabs[2]:
    st.header("CA JOURNALIER — MG & BATAM")
    st.caption("Tous les montants en TND TTC")
    
    df_jour_n = get_ca_journalier(df_vc, annee_sel, mois_sel if mois_sel != "Tous" else None)
    df_jour_n1 = get_ca_journalier(df_vc, annee_sel - 1, mois_sel if mois_sel != "Tous" else None)
    
    df_jour_n.columns = ['Jour', 'CA N']
    df_jour_n1.columns = ['Jour', 'CA N-1']
    df_jour = df_jour_n.merge(df_jour_n1, on='Jour', how='outer').fillna(0)
    df_jour['Variation %'] = ((df_jour['CA N'] - df_jour['CA N-1']) / df_jour['CA N-1'].replace(0, 1) * 100).round(1)
    
    st.dataframe(df_jour, use_container_width=True)
    
    fig_jour = plot_comparison(df_jour, 'Jour', 'CA N', 'CA N-1', 
                           f"CA Journalier {annee_sel} vs {annee_sel-1}", "Jour", "TND")
    fig_jour.update_layout(xaxis=dict(tickmode='linear', dtick=1, tickangle=45))
    st.plotly_chart(fig_jour, use_container_width=True)

# ============================================================
# ONGLET CONVENTIONS (Avec sélection interactive)
# ============================================================
with tabs[3]:
    st.header("PORTEFEUILLE CONVENTIONS — MG & BATAM")
    
    if not df_conventions.empty:
        df_conv = df_conventions.copy()
        cols_disp = ['SOCIETES', 'Code BC', 'Effectifs', 'CA 2025', 'POTENTIEL', 'MATURITE', 'SCORE']
        cols_exist = [c for c in cols_disp if c in df_conv.columns]
        
        if cols_exist:
            st.subheader("Liste des Conventions")
            st.dataframe(df_conv[cols_exist], use_container_width=True)
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Nb Conventions", len(df_conv))
            col_stat2.metric("Effectif Total", f"{df_conv['Effectifs'].sum():,.0f}" if 'Effectifs' in df_conv.columns else "N/A")
            col_stat3.metric("CA 2025", f"{df_conv['CA 2025'].sum():,.0f}" if 'CA 2025' in df_conv.columns else "N/A")
    
    st.markdown("---")
    st.subheader("📊 Analyse par Convention")
    
    all_conventions = df_vc['Nom'].dropna().unique().tolist() if 'Nom' in df_vc.columns else []
    conv_select = st.selectbox("Sélectionner une convention", sorted(all_conventions))
    
    if conv_select and conv_select != "Tous":
        df_conv_filt = df_vc[df_vc['Nom'] == conv_select].copy()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### CA Mensuel en cours vs N-1")
            df_comp_conv = compare_annees(df_conv_filt, annee_sel, annee_sel - 1)
            if not df_comp_conv.empty:
                fig = plot_comparison(df_comp_conv, 'Mois Nom', 'CA N', 'CA N-1',
                                f"CA Mensuel {conv_select}", "Mois", "TND")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### CA Cumulé Annuel N vs N-1")
            df_annee_n = df_conv_filt[df_conv_filt['Année'] == annee_sel].sort_values('Mois')
            df_annee_n1 = df_conv_filt[df_conv_filt['Année'] == annee_sel - 1].sort_values('Mois')
            
            df_annee_n['CA Cumulé N'] = df_annee_n.groupby('Mois')['Montant TTC'].sum().cumsum()
            df_annee_n1['CA Cumulé N-1'] = df_annee_n1.groupby('Mois')['Montant TTC'].sum().cumsum()
            
            df_cumul = df_annee_n[['Mois', 'CA Cumulé N']].merge(
                df_annee_n1[['Mois', 'CA Cumulé N-1']], on='Mois', how='outer'
            ).fillna(0)
            df_cumul['Mois Nom'] = df_cumul['Mois'].map(MOIS_NOMS)
            
            fig2 = plot_comparison(df_cumul, 'Mois Nom', 'CA Cumulé N', 'CA Cumulé N-1',
                                f"CA Cumulé {conv_select}", "Mois", "TND")
            st.plotly_chart(fig2, use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("#### Top Magasins")
            if 'Magasin' in df_conv_filt.columns:
                mag_ca = df_conv_filt.groupby('Magasin')['Montant TTC'].sum().nlargest(10).reset_index()
                fig3 = plot_horizontal_bar(mag_ca, 'Montant TTC', 'Magasin', "Top Magasins", COLORS['secondary'])
                st.plotly_chart(fig3, use_container_width=True)
        
        with col4:
            st.markdown("#### Répartition Credit vs Cash")
            ca_cash = df_conv_filt['Montant TTC'].sum() if 'Montant TTC' in df_conv_filt.columns else 0
            ca_credit_total = df_credit[df_credit['Nom'] == conv_select]['Montant TTC'].sum() if 'Nom' in df_credit.columns else 0
            if ca_cash > 0 or ca_credit_total > 0:
                fig4 = plot_pie([ca_cash, ca_credit_total], ['Cash', 'Crédit'], "Répartition CA")
                st.plotly_chart(fig4, use_container_width=True)

# ============================================================
# ONGLET MAGASINS
# ============================================================
with tabs[4]:
    st.header("🏪 CA PAR MAGASIN")
    
    df_n = df_filt.copy()
    df_n1 = df_vc[(df_vc['Année'] == annee_sel - 1)]
    if mois_sel != "Tous":
        df_n1 = df_n1[df_n1['Mois'] == mois_sel]
    
    if 'Magasin' in df_n.columns:
        ca_mag_n = df_n.groupby('Magasin')['Montant TTC'].sum().reset_index()
        ca_mag_n.columns = ['Magasin', 'CA N']
        
        if 'Magasin' in df_n1.columns:
            ca_mag_n1 = df_n1.groupby('Magasin')['Montant TTC'].sum().reset_index()
            ca_mag_n1.columns = ['Magasin', 'CA N-1']
            ca_mag = ca_mag_n.merge(ca_mag_n1, on='Magasin', how='outer').fillna(0)
        else:
            ca_mag = ca_mag_n.copy()
            ca_mag['CA N-1'] = 0
        
        ca_mag['Évolution %'] = ((ca_mag['CA N'] - ca_mag['CA N-1']) / ca_mag['CA N-1'].replace(0, 1) * 100).round(1)
        ca_mag = ca_mag.sort_values('CA N', ascending=False)
        
        st.subheader("CA Magasin N vs N-1")
        st.dataframe(ca_mag, use_container_width=True)
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("Top 20 Magasins")
            fig = plot_horizontal_bar(ca_mag.head(20), 'CA N', 'Magasin', "Top 20 Magasins", COLORS['primary'])
            st.plotly_chart(fig, use_container_width=True)
        
        with col_g2:
            st.subheader("Évolution N/N-1")
            ca_mag_top = ca_mag.head(20).copy()
            ca_mag_top['Évol_Category'] = ca_mag_top['Évolution %'].apply(
                lambda x: 'Hausse' if x > 0 else ('Baisse' if x < 0 else 'Stable')
            )
            fig2 = px.bar(ca_mag_top, x='Évolution %', y='Magasin', orientation='h',
                         title="Évolution N/N-1 (%)", color='Évol_Category',
                         color_discrete_map={'Hausse': COLORS['primary'], 'Baisse': COLORS['warning'], 'Stable': COLORS['secondary']})
            st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# ONGLET EDC (Simplifié)
# ============================================================
with tabs[5]:
    st.header("🏫 CONVENTION EDC - Ministère de l'Education")
    
    if not df_edc.empty:
        col_annee = st.selectbox("Année N", [2026, 2025, 2024], index=0, key="edc_annee")
        
        df_n = df_edc[df_edc['Année'] == col_annee]
        df_n1 = df_edc[df_edc['Année'] == col_annee - 1]
        
        ca_n = df_n['Montant TTC'].sum() if 'Montant TTC' in df_n.columns else 0
        ca_n1 = df_n1['Montant TTC'].sum() if 'Montant TTC' in df_n1.columns else 0
        evol = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else 0
        nb_factures = len(df_n)
        panier = ca_n / nb_factures if nb_factures > 0 else 0
        
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        col_k1.metric(f"CA {col_annee}", f"{ca_n:,.0f} DT", delta=f"{evol:+.1f}%")
        col_k2.metric(f"CA {col_annee-1}", f"{ca_n1:,.0f} DT")
        col_k3.metric("Nb Factures", nb_factures)
        col_k4.metric("Panier Moyen", f"{panier:,.0f} DT")
        
        st.markdown("---")
        st.markdown("### 📊 Répartition par Durée d'Échéance")
        
        if 'Nbr_Mois_Echance' in df_edc.columns:
            echeance = df_n.groupby('Nbr_Mois_Echance').agg({
                'Montant TTC': 'sum',
                'N°': 'count'
            }).reset_index()
            echeance.columns = ['Nb Mois', 'CA TTC', 'Nb']
            echeance['Part %'] = (echeance['CA TTC'] / echeance['CA TTC'].sum() * 100).round(1)
            echeance = echeance.sort_values('CA TTC', ascending=False)
            
            fig_echeance = px.bar(echeance, x='Nb Mois', y='CA TTC', title="Répartition par Échéance",
                             text='Part %', color_discrete_sequence=[COLORS['primary']])
            fig_echeance.update_traces(textposition='outside')
            fig_echeance.update_layout(template='plotly_white', height=400)
            st.plotly_chart(fig_echeance, use_container_width=True)
            
            st.dataframe(echeance, use_container_width=True)
    else:
        st.warning("Aucune donnée EDC trouvée")

# ============================================================
# ONGLET ALERTES
# ============================================================
with tabs[6]:
    st.header("🔔 ALERTES")
    
    if 'Nom' in df_vc.columns and 'Date' in df_vc.columns:
        df_2026 = df_vc[df_vc['Année'] == 2026]
        last_facture = df_2026.groupby('Nom')['Date'].max().reset_index()
        last_facture.columns = ['Convention', 'Dernière Facture']
        
        today = pd.Timestamp.today().normalize()
        last_facture['JoursSansFacture'] = (today - last_facture['Dernière Facture']).dt.days
        inactives = last_facture[last_facture['JoursSansFacture'] > 30].sort_values('JoursSansFacture', ascending=False)
        
        st.subheader("Conventions inactives à réactiver (>30 jours)")
        st.dataframe(inactives, use_container_width=True)
        
        if len(inactives) > 0:
            st.warning(f"⚠️ {len(inactives)} conventions sans facture depuis plus de 30 jours")

# ============================================================
# ONGLET PERFORMANCE
# ============================================================
with tabs[7]:
    st.header("📊 PERFORMANCE")
    
    col1, col2, col3, col4 = st.columns(4)
    
    if 'Année' in df_vc.columns:
        ca_2024 = df_vc[df_vc['Année'] == 2024]['Montant TTC'].sum()
        ca_2025 = df_vc[df_vc['Année'] == 2025]['Montant TTC'].sum()
        ca_2026 = df_vc[df_vc['Année'] == 2026]['Montant TTC'].sum()
        
        evol_25_24 = ((ca_2025 - ca_2024) / ca_2024 * 100) if ca_2024 > 0 else 0
        evol_26_25 = ((ca_2026 - ca_2025) / ca_2025 * 100) if ca_2025 > 0 else 0
        
        col1.metric("CA 2024", f"{ca_2024:,.0f} TND")
        col2.metric("CA 2025", f"{ca_2025:,.0f} TND", delta=f"{evol_25_24:+.1f}%")
        col3.metric("CA 2026 YTD", f"{ca_2026:,.0f} TND", delta=f"{evol_26_25:+.1f}%")
        col4.metric("Panier Moyen", f"{df_filt['Montant TTC'].mean() if len(df_filt) > 0 else 0:,.0f} TND")
    
    st.subheader("KPIs Données Filtrées")
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    col_k1.metric("CA Filtré", f"{df_filt['Montant TTC'].sum():,.0f} TND")
    col_k2.metric("Nb Factures", len(df_filt))
    col_k3.metric("Nb Conventions", df_filt['Nom'].nunique() if 'Nom' in df_filt.columns else 0)
    col_k4.metric("Nb Magasins", df_filt['Magasin'].nunique() if 'Magasin' in df_filt.columns else 0)

st.markdown("---")
st.caption("Dashboard B2B SMG — Mis à jour automatiquement | Source: VC.CONV. Business Central")