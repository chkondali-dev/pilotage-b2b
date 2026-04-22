import pandas as pd
import os
from datetime import datetime

CRM_FILE = 'crm_database.xlsx'
EXCEL_SOURCE = r'C:\Users\hachk\OneDrive - Société Magasin Général (SMG)\Documents\hamadi\grands compte\hamadi\dashbord convention\table vente\2025\TDC CONVENTION 1.xlsm'

def get_clients_from_excel():
    xl = pd.ExcelFile(EXCEL_SOURCE)
    df = pd.read_excel(xl, sheet_name='convention en cours')
    
    non_empty = df.dropna(how='all')
    if non_empty.empty:
        print("Aucune donnée trouvee")
        return
    
    rows = []
    for i, row in non_empty.iterrows():
        row_data = row.dropna().tolist()
        if len(row_data) < 2:
            continue
        
        nom = str(row_data[1]) if len(row_data) > 1 else ""
        if not nom or nom == "conventions en cours":
            continue
        
        contact = str(row_data[3]) if len(row_data) > 3 else ""
        telephone = str(row_data[4]) if len(row_data) > 4 else ""
        email = str(row_data[6]) if len(row_data) > 6 else ""
        ranking = str(row_data[7]) if len(row_data) > 7 else "⭐"
        commentaire = str(row_data[5]) if len(row_data) > 5 else ""
        
        rows.append({
            'Nom': nom,
            'Prenom': contact,
            'Telephone': telephone,
            'Email': email,
            'Adresse': '',
            'Effectifs': 0,
            'Ranking': ranking,
            'Commentaire': commentaire,
            'DateCreation': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'DateModification': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    if rows:
        df_clients = pd.DataFrame(rows)
        df_clients['ID'] = range(1, len(df_clients) + 1)
        
        df_interactions = pd.DataFrame(columns=[
            'ID', 'ClientID', 'Date', 'Type', 'Notes', 'Resultat'
        ])
        
        with pd.ExcelWriter(CRM_FILE, engine='openpyxl') as writer:
            df_clients.to_excel(writer, sheet_name='Clients', index=False)
            df_interactions.to_excel(writer, sheet_name='Interactions', index=False)
        
        print(f"Importe {len(df_clients)} clients!")
        for i, r in df_clients.head(5).iterrows():
            print(f"  {r['ID']}: {r['Nom']} - {r['Telephone']}")
    else:
        print("Aucun client trouve")

get_clients_from_excel()