"""
Dashboard Pilotage B2B - SMG
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import requests
from io import BytesIO
from datetime import datetime, timedelta

st.set_page_config(page_title="Pilotage B2B - SMG", layout="wide", page_icon="📊")

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/"
LOCAL_DATA = r"C:\Users\hachk\pilotage_b2b\2025"

FILES = {
    "vc": os.path.join(LOCAL_DATA, [f for f in os.listdir(LOCAL_DATA) if 'VC (4)' in f][0]),
    "vc_credit": os.path.join(LOCAL_DATA, [f for f in os.listdir(LOCAL_DATA) if 'VC credit' in f][0]),
    "vc_edc": os.path.join(LOCAL_DATA, [f for f in os.listdir(LOCAL_DATA) if 'VC CONVENTION EDC' in f][0]),
    "conventions": os.path.join(LOCAL_DATA, [f for f in os.listdir(LOCAL_DATA) if 'TDC CONVENTION' in f][0]),
    "code_magasin": os.path.join(LOCAL_DATA, [f for f in os.listdir(LOCAL_DATA) if 'Code MAGASIN' in f][0]),
}

COLORS = {
    "green": "#059669", "red": "#DC2626", "blue": "#1E40AF",
    "slate": "#64748B", "amber": "#F59E0B", "purple": "#7C3AED",
}

@st.cache_data(ttl=3600)
def load_excel(filepath):
    try:
        if not os.path.exists(filepath):
            st.error(f"Fichier non trouve: {filepath}")
            return None
        df = pd.read_excel(filepath, engine='openpyxl')
        for col in df.columns:
            if str(col).startswith('Unnamed'):
                df = df.drop(columns=[col])
        return df
    except Exception as e:
        st.error(f"Erreur chargement {filepath}: {e}")
        return None

def load_all_data():
    with st.spinner("Chargement des donnees..."):
        dfs = {}
        for name, filepath in FILES.items():
            df = load_excel(filepath)
            if df is not None:
                dfs[name] = df
        return dfs

def main():
    st.title("📊 Pilotage B2B - SMG")
    st.markdown(f"**Mis a jour:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    dfs = load_all_data()
    
    if not dfs:
        st.error("Impossible de charger les donnees. Verifiez la connexion internet.")
        return
    
    tabs = st.tabs(["Accueil", "CA Journalier", "Conventions", "Magasins", "Alertes"])
    
    with tabs[0]:
        st.header("Vue d'ensemble")
        
        col1, col2, col3, col4 = st.columns(4)
        
        if "vc" in dfs:
            df = dfs["vc"]
            date_col = None
            amount_col = None
            
            for col in df.columns:
                col_lower = col.lower() if isinstance(col, str) else ""
                if date_col is None and ("date" in col_lower or "jour" in col_lower):
                    date_col = col
                if amount_col is None and ("montant" in col_lower or "ca" in col_lower or "vend" in col_lower):
                    amount_col = col
            
            if date_col and amount_col:
                try:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                    df["Jour"] = df[date_col].dt.date
                    today = datetime.now().date()
                    yesterday = (datetime.now() - timedelta(days=1)).date()
                    
                    ca_today = df[df["Jour"] == today][amount_col].sum()
                    ca_yesterday = df[df["Jour"] == yesterday][amount_col].sum()
                    ca_month = df[df[date_col].dt.month == datetime.now().month][amount_col].sum()
                    
                    col1.metric("CA Aujourd'hui", f"{ca_today:,.0f} TND" if pd.notna(ca_today) else "N/A")
                    col2.metric("CA Hier", f"{ca_yesterday:,.0f} TND" if pd.notna(ca_yesterday) else "N/A")
                    col3.metric("CA Mois", f"{ca_month:,.0f} TND" if pd.notna(ca_month) else "N/A")
                    col4.metric("Nb Factures", len(df))
                except Exception as e:
                    st.warning(f"Erreur calcul KPIs: {e}")
    
    with tabs[1]:
        st.header("CA Journalier")
        if "vc" in dfs:
            try:
                st.dataframe(dfs["vc"].head(50), width='stretch')
            except:
                st.write("Donnees non disponibles")
    
    with tabs[2]:
        st.header("Conventions")
        if "conventions" in dfs:
            try:
                st.dataframe(dfs["conventions"].head(50), width='stretch')
            except:
                st.write("Donnees non disponibles")
    
    with tabs[3]:
        st.header("Magasins")
        if "code_magasin" in dfs:
            try:
                st.dataframe(dfs["code_magasin"].head(50), width='stretch')
            except:
                st.write("Donnees non disponibles")
    
    with tabs[4]:
        st.header("Alertes")
        st.info("Aucune alerte pour le moment")

if __name__ == "__main__":
    main()