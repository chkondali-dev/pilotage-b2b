import os
import pandas as pd
import streamlit as st
from datetime import datetime
from openpyxl import load_workbook

st.set_page_config(page_title="CRM SMG", page_icon="👥", layout="wide")

EXCEL_FILE = 'crm_database.xlsx'
CLIENTS_SHEET = 'Clients'
INTERACTIONS_SHEET = 'Interactions'

def init_database():
    if not os.path.exists(EXCEL_FILE):
        df_clients = pd.DataFrame(columns=[
            'ID', 'Nom', 'Prenom', 'Telephone', 'Email', 'Adresse', 
            'Effectifs', 'Ranking', 'Commentaire', 'DateCreation', 'DateModification'
        ])
        df_interactions = pd.DataFrame(columns=[
            'ID', 'ClientID', 'Date', 'Type', 'Notes', 'Resultat'
        ])
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            df_clients.to_excel(writer, sheet_name=CLIENTS_SHEET, index=False)
            df_interactions.to_excel(writer, sheet_name=INTERACTIONS_SHEET, index=False)

def load_clients():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame()
    try:
        return pd.read_excel(EXCEL_FILE, sheet_name=CLIENTS_SHEET)
    except:
        return pd.DataFrame()

def load_interactions():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame()
    try:
        return pd.read_excel(EXCEL_FILE, sheet_name=INTERACTIONS_SHEET)
    except:
        return pd.DataFrame()

def save_clients(df):
    with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df.to_excel(writer, sheet_name=CLIENTS_SHEET, index=False)

def save_interactions(df):
    with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df.to_excel(writer, sheet_name=INTERACTIONS_SHEET, index=False)

def get_next_id(df):
    if df.empty:
        return 1
    return int(df['ID'].max()) + 1

st.markdown("""
<style>
    .sidebar .sidebar-content { background: linear-gradient(180deg, #1a3a5c 0%, #0d2137 100%); }
    .stButton>button { background: #1a3a5c; color: white; }
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
</style>
""", unsafe_allow_html=True)

init_database()

page = st.sidebar.selectbox("Menu", ["Dashboard", "Clients", "Recherche", "Nouveau Client"])

if page == "Dashboard":
    st.title("📊 Tableau de bord CRM")
    
    clients = load_clients()
    interactions = load_interactions()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Clients", len(clients))
    with col2:
        total_effectifs = clients['Effectifs'].sum() if not clients.empty and 'Effectifs' in clients.columns else 0
        st.metric("Effectifs Totaux", int(total_effectifs) if pd.notna(total_effectifs) else 0)
    with col3:
        st.metric("Interactions", len(interactions))
    with col4:
        st.metric("Conventions Actives", len(clients[clients['Ranking'].notna()]) if not clients.empty else 0)
    
    st.subheader("👥 Derniers Clients")
    if not clients.empty:
        st.dataframe(clients.tail(10)[['ID', 'Nom', 'Prenom', 'Telephone', 'Effectifs']], use_container_width=True)
    else:
        st.info("Aucun client")
    
    st.subheader("📞 Dernières Interactions")
    if not interactions.empty:
        st.dataframe(interactions.tail(10)[['Date', 'Type', 'Notes', 'Resultat']], use_container_width=True)
    else:
        st.info("Aucune interaction")

elif page == "Clients":
    st.title("👥 Liste des Clients")
    
    clients = load_clients()
    search = st.text_input("Rechercher", "")
    
    if search:
        clients = clients[
            clients['Nom'].str.contains(search, case=False, na=False) |
            clients['Prenom'].str.contains(search, case=False, na=False) |
            clients['Telephone'].str.contains(search, case=False, na=False)
        ]
    
    if not clients.empty:
        st.dataframe(clients[['ID', 'Nom', 'Prenom', 'Telephone', 'Email', 'Effectifs', 'Ranking']], use_container_width=True)
    else:
        st.info("Aucun client trouvé")

elif page == "Recherche":
    st.title("🔍 Recherche")
    
    query = st.text_input("Rechercher par nom, prénom, téléphone, email", "")
    
    if query:
        clients = load_clients()
        results = clients[
            clients['Nom'].str.contains(query, case=False, na=False) |
            clients['Prenom'].str.contains(query, case=False, na=False) |
            clients['Telephone'].str.contains(query, case=False, na=False) |
            clients['Email'].str.contains(query, case=False, na=False)
        ]
        
        if not results.empty:
            st.dataframe(results[['Nom', 'Prenom', 'Telephone', 'Email', 'Effectifs']], use_container_width=True)
        else:
            st.info(f"Aucun résultat pour '{query}'")

elif page == "Nouveau Client":
    st.title("➕ Nouveau Client")
    
    with st.form("client_form"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom *")
            prenom = st.text_input("Prénom")
            telephone = st.text_input("Téléphone")
            email = st.text_input("Email")
        with col2:
            adresse = st.text_area("Adresse", height=100)
            effectif = st.number_input("Effectifs", min_value=0, value=0)
            ranking = st.selectbox("Ranking", ["⭐", "⭐⭐", "⭐⭐⭐"])
            commentaire = st.text_area("Commentaire")
        
        submitted = st.form_submit_button("Enregistrer")
        
        if submitted and nom:
            clients = load_clients()
            new_client = {
                'ID': get_next_id(clients),
                'Nom': nom,
                'Prenom': prenom,
                'Telephone': telephone,
                'Email': email,
                'Adresse': adresse,
                'Effectifs': effectif,
                'Ranking': ranking,
                'Commentaire': commentaire,
                'DateCreation': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'DateModification': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            clients = pd.concat([clients, pd.DataFrame([new_client])], ignore_index=True)
            save_clients(clients)
            st.success("Client ajouté avec succès!")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("💾 Données stockées dans: crm_database.xlsx")