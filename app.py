import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import requests
from io import BytesIO
from urllib.parse import quote

st.set_page_config(page_title="Dashboard Pilotage B2B - SMG", layout="wide", page_icon="📊")

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"

FILES = {
    "vc": quote("Factures ventes enregistrées VC (4).xlsx"),
    "vc_credit": quote("Factures ventes enregistrées VC credit conso.xlsx"),
    "vc_edc": quote("Factures ventes enregistrées VC CONVENTION EDC.xlsx"),
    "conventions_signees": quote("TDC CONVENTION 1.xlsm"),
    "code_magasin": quote("Code MAGASIN Business Central.xlsx")
}

def load_from_url(filename):
    url = GITHUB_RAW + filename
    # FIX: ajout d'un timeout réseau pour éviter les gels indéfinis
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return pd.read_excel(BytesIO(response.content), engine='openpyxl')

def load_xlsm(filename):
    url = GITHUB_RAW + filename
    # FIX: ajout d'un timeout réseau
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
    
    try:
        df = load_from_url(FILES["vc"])
        df = clean_columns(df)
        dfs["vc"] = df
    except Exception as e:
        st.warning(f"Erreur vc: {e}")
    
    try:
        df = load_from_url(FILES["vc_credit"])
        df = clean_columns(df)
        dfs["vc_credit"] = df
    except Exception as e:
        st.warning(f"Erreur vc_credit: {e}")
    
    try:
        df = load_from_url(FILES["vc_edc"])
        df = clean_columns(df)
        dfs["vc_edc"] = df
    except Exception as e:
        st.warning(f"Erreur EDC: {e}")
    
    try:
        df = load_xlsm(FILES["conventions_signees"])
        sheet_keys = list(df.keys())
        if sheet_keys:
            dfs["conventions_signees"] = clean_columns(df[sheet_keys[0]])
    except Exception as e:
        st.warning(f"Erreur conventions: {e}")
    
    try:
        df = load_from_url(FILES["code_magasin"])
        dfs["code_magasin"] = clean_columns(df)
    except Exception as e:
        st.warning(f"Erreur code_magasin: {e}")
    
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

st.title("📊 DASHBOARD GRANDS COMPTES — SMG")
st.caption("Source: VC.CONV. Business Central")

if st.sidebar.button("🔄 Actualiser les données"):
    st.cache_data.clear()
    st.rerun()

data = load_all_data()

df_vc = data.get("vc", pd.DataFrame())
df_credit = data.get("vc_credit", pd.DataFrame())
code_magasin_df = data.get("code_magasin", pd.DataFrame())

for df in [df_vc, df_credit]:
    if 'Date comptabilisation' in df.columns:
        df['Date'] = pd.to_datetime(df['Date comptabilisation'], errors='coerce')
        df['Année'] = df['Date'].dt.year
        df['Mois'] = df['Date'].dt.month
        df['Jour'] = df['Date'].dt.day
    if 'Code magasin' in df.columns and not code_magasin_df.empty:
        df['Magasin'] = df['Code magasin'].apply(lambda x: get_magasin_name(x, code_magasin_df))

with st.sidebar:
    st.header("🔍 Filtres")
    
    annee_sel = st.selectbox("Année", [2026, 2025, 2024, 2023], index=0)
    
    mois_options = ["Tous"] + list(range(1, 13))
    mois_sel = st.selectbox("Mois", mois_options, index=4)
    
    # FIX: filtre convention restreint à l'année sélectionnée pour éviter
    # d'afficher des conventions inexistantes sur la période filtrée
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

try:
    df_filt = df_vc[df_vc['Année'] == annee_sel].copy()
    if mois_sel != "Tous":
        df_filt = df_filt[df_filt['Mois'] == mois_sel]
    if conv_sel != "Tous":
        df_filt = df_filt[df_filt['Nom'] == conv_sel]
    
    # FIX: ordre des onglets aligné avec les index utilisés dans le code
    # ACCUEIL(0), DASHBOARD(1), CA JOURNALIER(2), CONVENTIONS(3),
    # MAGASINS(4), EDC(5), ALERTES(6), PERFORMANCE(7)
    tabs = st.tabs([
        "🏠 ACCUEIL",
        "📈 DASHBOARD",
        "📅 CA JOURNALIER",
        "📋 CONVENTIONS",
        "🏪 MAGASINS",
        "🏫 EDC (Education)",
        "🔔 ALERTES",
        "📊 PERFORMANCE"
    ])
    
    # ── ONGLET 0 : ACCUEIL ──────────────────────────────────────────────────
    with tabs[0]:
        st.header("DASHBOARD GRANDS COMPTES — SMG")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # FIX: tous les KPIs sont calculés dynamiquement (plus de valeurs hardcodées)
        ca_2024 = df_vc[df_vc['Année'] == 2024]['Montant TTC'].sum() if 'Année' in df_vc.columns else 0
        ca_2025 = df_vc[df_vc['Année'] == 2025]['Montant TTC'].sum() if 'Année' in df_vc.columns else 0
        ca_2026_ytd = df_vc[df_vc['Année'] == 2026]['Montant TTC'].sum() if 'Année' in df_vc.columns else 0

        delta_2025 = f"{((ca_2025 - ca_2024) / ca_2024 * 100):+.1f}% vs 2024" if ca_2024 > 0 else "N/A"
        delta_2026 = f"{((ca_2026_ytd - ca_2025) / ca_2025 * 100):+.1f}% vs YTD 2025" if ca_2025 > 0 else "N/A"

        # FIX: nombre de conventions actives/inactives calculé depuis les données réelles
        if 'Nom' in df_vc.columns and 'Année' in df_vc.columns:
            convs_actives_2026 = df_vc[df_vc['Année'] == 2026]['Nom'].dropna().nunique()
        else:
            convs_actives_2026 = 0

        if "conventions_signees" in data:
            total_conventions = len(data["conventions_signees"])
            convs_inactives = max(0, total_conventions - convs_actives_2026)
        else:
            convs_inactives = 0

        col1.metric("CA 2025 (Full Year)", f"{ca_2025:,.0f} TND", delta=delta_2025)
        col2.metric("CA 2026 YTD", f"{ca_2026_ytd:,.0f} TND", delta=delta_2026)
        col3.metric("Conventions Actives 2026", str(convs_actives_2026))
        col4.metric("Conventions Inactives", str(convs_inactives), delta="à réactiver", delta_color="inverse")
        
        st.info(f"💡 Filtres actifs: {annee_sel} | Mois: {mois_sel if mois_sel != 'Tous' else 'Tous'} | Convention: {conv_sel}")
    
    # ── ONGLET 1 : DASHBOARD ─────────────────────────────────────────────────
    with tabs[1]:
        st.header("DASHBOARD GRANDS COMPTES — MG & BATAM")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("CA par année")
            if 'Année' in df_vc.columns:
                ca_year = df_vc.groupby('Année')['Montant TTC'].sum().reset_index()
                fig = px.bar(ca_year, x='Année', y='Montant TTC', text_auto=',.0f',
                            title="CA par année (toutes années)", color_discrete_sequence=['#00CC96'])
                # FIX: use_container_width=True remplace width='stretch' (déprécié)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Top 10 Conventions")
            if 'Nom' in df_filt.columns:
                top_conv = df_filt.groupby('Nom')['Montant TTC'].sum().nlargest(10).reset_index()
                fig2 = px.bar(top_conv, x='Montant TTC', y='Nom', orientation='h',
                             title="Top 10 Conventions", color_discrete_sequence=['#636EFA'])
                st.plotly_chart(fig2, use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("CA par mois")
            if 'Mois' in df_filt.columns:
                ca_mois = df_filt.groupby('Mois')['Montant TTC'].sum().reset_index()
                fig3 = px.bar(ca_mois, x='Mois', y='Montant TTC', text_auto=',.0f',
                             title="CA par mois", color_discrete_sequence=['#FF6692'])
                st.plotly_chart(fig3, use_container_width=True)
        
        with col4:
            st.subheader("Répartition CA Credit vs Cash")
            ca_cash = df_vc['Montant TTC'].sum() if 'Montant TTC' in df_vc.columns else 0
            ca_credit_total = df_credit['Montant TTC'].sum() if 'Montant TTC' in df_credit.columns and len(df_credit) > 0 else 0
            fig4 = px.pie(values=[ca_cash, ca_credit_total], names=['Cash', 'Crédit Conso'],
                         title="Répartition CA", hole=0.4)
            st.plotly_chart(fig4, use_container_width=True)
    
    # ── ONGLET 2 : CA JOURNALIER ──────────────────────────────────────────────
    with tabs[2]:
        st.header("CA JOURNALIER — MG & BATAM")
        st.caption("Tous les montants en TND TTC")
        
        df_jour = df_filt.copy()
        
        st.subheader("SECTION 1 — CA GLOBAL PAR JOUR")
        
        ca_jour = df_jour.groupby('Jour')['Montant TTC'].sum().reset_index()
        ca_jour.columns = ['Jour', 'CA Année N']
        
        if annee_sel > 2024:
            df_n1 = df_vc[(df_vc['Année'] == annee_sel - 1)]
            if mois_sel != "Tous":
                df_n1 = df_n1[df_n1['Mois'] == mois_sel]
            ca_jour_n1 = df_n1.groupby('Jour')['Montant TTC'].sum().reset_index()
            ca_jour_n1.columns = ['Jour', 'CA Année N-1']
            ca_jour = ca_jour.merge(ca_jour_n1, on='Jour', how='outer').fillna(0)
            ca_jour['Variation %'] = ((ca_jour['CA Année N'] - ca_jour['CA Année N-1']) / ca_jour['CA Année N-1'] * 100).round(1).replace([float('inf')], 100)
        
        st.dataframe(ca_jour, use_container_width=True)
        
        fig = px.bar(ca_jour, x='Jour', y='CA Année N', title=f"CA Journalier {annee_sel} - Mois {mois_sel}")
        st.plotly_chart(fig, use_container_width=True)
    
    # ── ONGLET 3 : CONVENTIONS ────────────────────────────────────────────────
    with tabs[3]:
        st.header("PORTEFEUILLE CONVENTIONS — MG & BATAM")
        
        if "conventions_signees" in data:
            df = data["conventions_signees"]
            
            df_conv = df.copy()
            cols_disp = ['SOCIETES', 'Code BC', 'Personne à contacter', 'N° TEL', 'EMAIL', 'Effectifs', 'CA 2025', 'POTENTIEL', 'MATURITE', 'SCORE', 'ACTION A SUIVRE']
            cols_exist = [c for c in cols_disp if c in df_conv.columns]
            
            if cols_exist:
                st.subheader("Conventions Signées")
                st.dataframe(df_conv[cols_exist], use_container_width=True)
                
                st.subheader("Statistiques")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Nb Conventions", len(df_conv))
                col2.metric("Effectif Total", f"{df_conv['Effectifs'].sum():,.0f}" if 'Effectifs' in df_conv.columns else "N/A")
                col3.metric("CA 2025", f"{df_conv['CA 2025'].sum():,.0f}" if 'CA 2025' in df_conv.columns else "N/A")
                
                if 'MATURITE' in df_conv.columns:
                    maturite_counts = df_conv['MATURITE'].value_counts()
                    fig = px.pie(values=maturite_counts.values, names=maturite_counts.index, title="Répartition Maturité")
                    st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("CA par Convention (données filtrées)")
        
        if 'Nom' in df_filt.columns and 'Montant TTC' in df_filt.columns:
            ca_conv = df_filt.groupby('Nom')['Montant TTC'].sum().nlargest(20).reset_index()
            fig = px.bar(ca_conv, x='Nom', y='Montant TTC', text_auto=',.0f', title="Top 20 Conventions par CA")
            st.plotly_chart(fig, use_container_width=True)
    
    # ── ONGLET 4 : MAGASINS ───────────────────────────────────────────────────
    # FIX: était tabs[4] avec le label "🏫 EDC" → corrigé en "🏪 MAGASINS"
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
                # FIX: log explicite si N-1 sans colonne Magasin (échec silencieux évité)
                st.warning("Colonne 'Magasin' absente pour N-1 — évolution non calculable.")
                ca_mag = ca_mag_n.copy()
                ca_mag['CA N-1'] = 0
            
            ca_mag['Évolution %'] = ((ca_mag['CA N'] - ca_mag['CA N-1']) / ca_mag['CA N-1'] * 100).round(1).replace([float('inf')], 100).replace([-float('inf')], -100)
            ca_mag['Évolution'] = ca_mag['CA N'] - ca_mag['CA N-1']
            ca_mag = ca_mag.sort_values('CA N', ascending=False)
        
        st.subheader("CA Magasin N vs N-1")
        if 'Magasin' in df_filt.columns:
            st.dataframe(ca_mag, use_container_width=True)
            
            csv_mag = ca_mag.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Télécharger CSV CA Magasin", csv_mag, "ca_magasin_n_n1.csv", "text/csv")
            
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("Top 20 Magasins par CA")
                fig = px.bar(ca_mag.head(20), x='Magasin', y='CA N', text_auto=',.0f', title="Top 20 Magasins par CA")
                st.plotly_chart(fig, use_container_width=True)
            
            with col_g2:
                st.subheader("Évolution N/N-1")
                ca_mag_top = ca_mag.head(20).copy()
                ca_mag_top['Évol_Category'] = ca_mag_top['Évolution %'].apply(
                    lambda x: 'Hausse' if x > 0 else ('Baisse' if x < 0 else 'Stable')
                )
                fig2 = px.bar(ca_mag_top, x='Magasin', y='Évolution %',
                             title="Évolution N/N-1 (%)", color='Évol_Category',
                             color_discrete_map={'Hausse': '#00CC96', 'Baisse': '#EF553B', 'Stable': '#636EFA'})
                st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("---")
        st.subheader("CA Magasin par Convention")
        
        if 'Nom' in df_filt.columns and 'Magasin' in df_filt.columns:
            ca_mag_conv = df_filt.groupby(['Magasin', 'Nom'])['Montant TTC'].sum().reset_index()
            ca_mag_conv = ca_mag_conv.pivot_table(index='Magasin', columns='Nom', values='Montant TTC', fill_value=0)
            st.dataframe(ca_mag_conv, use_container_width=True)
            
            csv = ca_mag_conv.to_csv().encode('utf-8')
            st.download_button("📥 Télécharger CSV Magasin x Convention", csv, "ca_magasin_convention.csv", "text/csv")
        
        st.markdown("---")
        
        st.subheader("Détails par magasin")
        if 'Magasin' in df_filt.columns:
            mag_summary = df_filt.groupby('Magasin').agg({
                'Montant TTC': 'sum',
                'N°': 'count'
            }).reset_index()
            mag_summary.columns = ['Magasin', 'CA Total', 'Nb Factures']
            mag_summary = mag_summary.sort_values('CA Total', ascending=False)
            st.dataframe(mag_summary, use_container_width=True)
            
            csv = mag_summary.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Télécharger CSV Magasins", csv, "ca_magasins.csv", "text/csv")
    
    # ── ONGLET 5 : EDC ───────────────────────────────────────────────────────
    # FIX: était tabs[5] avec le label "🏪 MAGASINS" → corrigé en "🏫 EDC"
    with tabs[5]:
        st.header("🏫 CONVENTION EDC - Ministère de l'Education")
        st.caption("Source: Navision VC.PARTIC.")
        
        df_edc = data.get("vc_edc", pd.DataFrame())
        
        if not df_edc.empty:
            if 'Date comptabilisation' in df_edc.columns:
                df_edc['Date'] = pd.to_datetime(df_edc['Date comptabilisation'], errors='coerce')
                df_edc['Année'] = df_edc['Date'].dt.year
                df_edc['Mois'] = df_edc['Date'].dt.month
            
            if 'Code magasin' in df_edc.columns and not code_magasin_df.empty:
                df_edc['Magasin'] = df_edc['Code magasin'].apply(lambda x: get_magasin_name(x, code_magasin_df))
            
            col_annee = st.selectbox("Année N", [2026, 2025, 2024], index=0, key="edc_annee")
            
            df_n = df_edc[df_edc['Année'] == col_annee]
            df_n1 = df_edc[df_edc['Année'] == col_annee - 1]
            
            ca_n = df_n['Montant TTC'].sum() if 'Montant TTC' in df_n.columns else 0
            ca_n1 = df_n1['Montant TTC'].sum() if 'Montant TTC' in df_n1.columns else 0
            ca_total = ca_n + ca_n1
            
            evol_annee = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else 0
            nb_factures_n = len(df_n)

            # FIX: panier moyen protégé contre division par zéro et valeur 0 trompeuse
            if nb_factures_n > 0 and ca_n > 0:
                panier_moyen = f"{ca_n / nb_factures_n:,.0f} DT"
            else:
                panier_moyen = "N/A"
            
            st.subheader("KPIS GLOBAUX")
            col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
            col_k1.metric(f"CA {col_annee}", f"{ca_n:,.0f} DT", delta=f"{evol_annee:+.1f}%")
            col_k2.metric(f"CA {col_annee-1}", f"{ca_n1:,.0f} DT")
            col_k3.metric("CA Total", f"{ca_total:,.0f} DT")
            col_k4.metric("Nb Factures", nb_factures_n)
            col_k5.metric("Panier Moyen", panier_moyen)
            
            st.subheader("ÉVOLUTION ANNUELLE")
            evol_annuelle = []
            for annee in [2024, 2025, 2026]:
                df_a = df_edc[df_edc['Année'] == annee]
                ca_a = df_a['Montant TTC'].sum() if 'Montant TTC' in df_a.columns else 0
                nb_a = len(df_a)
                panier = ca_a / nb_a if nb_a > 0 else 0
                evol = 0
                if annee > 2024:
                    df_prec = df_edc[df_edc['Année'] == annee - 1]
                    ca_prec = df_prec['Montant TTC'].sum() if 'Montant TTC' in df_prec.columns else 0
                    evol = ((ca_a - ca_prec) / ca_prec * 100) if ca_prec > 0 else 0
                evol_annuelle.append({
                    'Année': annee,
                    'CA TTC': ca_a,
                    'Nb': nb_a,
                    'Panier': panier,
                    'Évol CA': evol
                })
            
            df_evol = pd.DataFrame(evol_annuelle)
            st.dataframe(df_evol, use_container_width=True)
            
            st.subheader(f"DÉTAIL MENSUEL {col_annee} + N-1 ({col_annee - 1})")
            
            nb_mois_n = df_n.groupby('Mois').agg({
                'Montant TTC': ['sum', 'count']
            }).reset_index()
            nb_mois_n.columns = ['Mois', f'CA {col_annee}', 'Nb_N']
            nb_mois_n[f'Panier {col_annee}'] = nb_mois_n[f'CA {col_annee}'] / nb_mois_n['Nb_N']
            
            nb_mois_n1 = df_n1.groupby('Mois').agg({
                'Montant TTC': ['sum', 'count']
            }).reset_index()
            nb_mois_n1.columns = ['Mois', f'CA {col_annee-1}', 'Nb_N1']
            nb_mois_n1[f'Panier {col_annee-1}'] = nb_mois_n1[f'CA {col_annee-1}'] / nb_mois_n1['Nb_N1']
            
            ca_mois = nb_mois_n.merge(nb_mois_n1, on='Mois', how='outer').fillna(0)
            ca_mois['Δ CA'] = ca_mois[f'CA {col_annee}'] - ca_mois[f'CA {col_annee-1}']
            # FIX: remplacement de replace() chaîné par une approche numpy-safe
            ca_mois['Δ %'] = ca_mois.apply(
                lambda row: round((row['Δ CA'] / row[f'CA {col_annee-1}'] * 100), 1)
                if row[f'CA {col_annee-1}'] != 0 else (100 if row['Δ CA'] > 0 else -100),
                axis=1
            )
            
            mois_noms = {1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril', 5: 'Mai', 6: 'Juin',
                        7: 'Juillet', 8: 'Août', 9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'}
            ca_mois['Mois Nom'] = ca_mois['Mois'].map(mois_noms)
            
            # FIX: colonne dupliquée supprimée (f'CA {col_annee-1}' était listée deux fois)
            cols_aff = ['Mois', 'Mois Nom', f'CA {col_annee}', 'Nb_N', f'Panier {col_annee}',
                        f'CA {col_annee-1}', 'Nb_N1', f'Panier {col_annee-1}', 'Δ CA', 'Δ %']
            cols_aff_exist = [c for c in cols_aff if c in ca_mois.columns]
            st.dataframe(ca_mois[cols_aff_exist], use_container_width=True)
            
            st.subheader("RÉPARTITION PAR MAGASIN")
            filtre_mois = st.selectbox("Filtre mois", ["Tous"] + list(range(1, 13)), key="filtre_mois_edc")
            
            df_mag_filt = df_n if filtre_mois == "Tous" else df_n[df_n['Mois'] == filtre_mois]
            
            ca_mag = df_mag_filt.groupby('Magasin').agg({
                'Montant TTC': 'sum',
                'N°': 'count'
            }).reset_index()
            ca_mag.columns = ['Magasin', 'CA', 'Nb']
            ca_mag = ca_mag.sort_values('CA', ascending=False)
            st.dataframe(ca_mag, use_container_width=True)
            
            csv_mag = ca_mag.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Télécharger CSV Magasin", csv_mag, "ca_magasin_edc.csv", "text/csv")
            
            st.subheader("RÉPARTITION PAR DURÉE D'ÉCHÉANCE")
            if 'Nbr_Mois_Echance' in df_edc.columns:
                echeance = df_edc.groupby('Nbr_Mois_Echance').agg({
                    'Montant TTC': 'sum',
                    'N°': 'count'
                }).reset_index()
                echeance.columns = ['Nb Mois', 'CA TTC', 'Nb']
                echeance['Part %'] = (echeance['CA TTC'] / echeance['CA TTC'].sum() * 100).round(1)
                echeance['Panier'] = echeance['CA TTC'] / echeance['Nb']
                echeance = echeance.sort_values('CA TTC', ascending=False)
                st.dataframe(echeance, use_container_width=True)
            
            st.subheader("DÉTAIL DES FACTURES")
            st.dataframe(df_n, use_container_width=True)
            csv_edc = df_n.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Télécharger CSV EDC", csv_edc, "factures_edc.csv", "text/csv")
        else:
            st.warning("Aucune donnée EDC trouvée")
    
    # ── ONGLET 6 : ALERTES ───────────────────────────────────────────────────
    with tabs[6]:
        st.header("🔔 ALERTES")
        
        st.subheader("Conventions inactives à réactiver")
        
        if 'Nom' in df_vc.columns and 'Date' in df_vc.columns:
            df_2026 = df_vc[df_vc['Année'] == 2026]
            last_facture = df_2026.groupby('Nom')['Date'].max().reset_index()
            last_facture.columns = ['Convention', 'Dernière Facture']
            
            # FIX: date de référence dynamique (plus de date codée en dur)
            today = pd.Timestamp.today().normalize()
            last_facture['JoursSansFacture'] = (today - last_facture['Dernière Facture']).dt.days
            inactives = last_facture[last_facture['JoursSansFacture'] > 30].sort_values('JoursSansFacture', ascending=False)
            
            st.dataframe(inactives, use_container_width=True)
            
            if len(inactives) > 0:
                st.warning(f"⚠️ {len(inactives)} conventions sans facture depuis plus de 30 jours")
        
        st.subheader("Suivi des Actions")
        
        if "conventions_signees" in data:
            df = data["conventions_signees"]
            if 'ACTION A SUIVRE' in df.columns:
                actions = df['ACTION A SUIVRE'].value_counts()
                st.dataframe(actions, use_container_width=True)
    
    # ── ONGLET 7 : PERFORMANCE ────────────────────────────────────────────────
    with tabs[7]:
        # FIX: header manquant ajouté
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

except Exception as e:
    st.error(f"Erreur: {e}")
    import traceback
    st.code(traceback.format_exc())

st.markdown("---")
st.caption("Dashboard B2B SMG — Mis à jour automatiquement | Source: VC.CONV. Business Central")
