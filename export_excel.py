import pandas as pd
import warnings
warnings.filterwarnings('ignore')

file_path = r'C:\Users\hachk\OneDrive - Société Magasin Général (SMG)\Documents\hamadi\grands compte\hamadi\dashbord convention\table vente\2025\credit personnel.xlsx'

df = pd.read_excel(file_path, sheet_name='Factures ventes enregistrées VC', engine='openpyxl')

df.columns = ['N_Facture', 'N_client_facture', 'Nom', 'Unite_Code', 'N_Client', 'Nom_Client', 
              'Type_vente', 'Groupe_compta', 'Code_devise', 'Date_compta', 'Date_echeance',
              'Montant_HT', 'Montant_TTC', 'Frais_Dossier', 'Montant_HT_Interet', 'Montant_TVA_Interet',
              'RIB', 'N_compte_bancaire', 'Montant_ouvert', 'Code_magasin', 'Nbre_impressions',
              'Cloture', 'Annule', 'Nbr_Mois_Echeance', 'Facture_Importe', 'Correctif']

# Filter echance 36 mois
df_36 = df[df['Nbr_Mois_Echeance'] == 36].copy()
df_36['Year'] = df_36['Date_compta'].dt.year
df_36['Month'] = df_36['Date_compta'].dt.month
df_36['Day'] = df_36['Date_compta'].dt.day
df_36['Date_str'] = df_36['Date_compta'].dt.strftime('%Y-%m-%d')

# Filter mars/avril jusqu'au 26
df_ma = df_36[(df_36['Month'].isin([3, 4])) & (df_36['Day'] <= 26)]

# Create Excel writer
output_path = r'C:\Users\hachk\pilotage_b2b\analyse_36_mois_mars_avril_2026_vs_2025.xlsx'

with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    # Sheet 1: Resume global
    resume_data = []
    for year in [2025, 2026]:
        data = df_ma[df_ma['Year'] == year]
        
        mars = data[data['Month'] == 3]
        avril = data[(data['Month'] == 4) & (data['Day'] <= 26)]
        
        resume_data.append({
            'Année': year,
            'Mars_Nb_Factures': len(mars),
            'Mars_CA_TTC': mars['Montant_TTC'].sum(),
            'Mars_CA_HT': mars['Montant_HT'].sum(),
            'Mars_Interets': mars['Montant_HT_Interet'].sum(),
            'Avril_Nb_Factures': len(avril),
            'Avril_CA_TTC': avril['Montant_TTC'].sum(),
            'Avril_CA_HT': avril['Montant_HT'].sum(),
            'Avril_Interets': avril['Montant_HT_Interet'].sum(),
            'Total_Nb_Factures': len(data),
            'Total_CA_TTC': data['Montant_TTC'].sum(),
            'Total_CA_HT': data['Montant_HT'].sum(),
            'Total_Interets': data['Montant_HT_Interet'].sum()
        })
    
    resume_df = pd.DataFrame(resume_data)
    resume_df.to_excel(writer, sheet_name='Résumé', index=False)
    
    # Sheet 2: Comparaison par mois
    synthese = []
    for month in [3, 4]:
        month_name = 'Mars' if month == 3 else 'Avril'
        for year in [2025, 2026]:
            data = df_ma[(df_ma['Year'] == year) & (df_ma['Month'] == month)]
            synthese.append({
                'Mois': month_name,
                'Année': year,
                'Nb_Factures': len(data),
                'CA_TTC': data['Montant_TTC'].sum(),
                'CA_HT': data['Montant_HT'].sum(),
                'Interets_HT': data['Montant_HT_Interet'].sum()
            })
    
    synthese_df = pd.DataFrame(synthese)
    synthese_df.to_excel(writer, sheet_name='Par Mois', index=False)
    
    # Sheet 3: Par magasin 2026
    mag_2026 = df_ma[df_ma['Year'] == 2026].groupby('Code_magasin').agg({
        'N_Facture': 'count',
        'Montant_TTC': 'sum',
        'Montant_HT': 'sum',
        'Montant_HT_Interet': 'sum'
    }).reset_index()
    mag_2026.columns = ['Code_Magasin', 'Nb_Factures', 'CA_TTC', 'CA_HT', 'Interets_HT']
    mag_2026 = mag_2026.sort_values('CA_TTC', ascending=False)
    mag_2026.to_excel(writer, sheet_name='Par Magasin 2026', index=False)
    
    # Sheet 4: Comparaison par magasin
    mag_2025 = df_ma[df_ma['Year'] == 2025].groupby('Code_magasin').agg({
        'N_Facture': 'count',
        'Montant_TTC': 'sum'
    }).reset_index()
    mag_2025.columns = ['Code_Magasin', 'Nb_2025', 'CA_2025']
    
    mag_2026_grouped = df_ma[df_ma['Year'] == 2026].groupby('Code_magasin').agg({
        'N_Facture': 'count',
        'Montant_TTC': 'sum'
    }).reset_index()
    mag_2026_grouped.columns = ['Code_Magasin', 'Nb_2026', 'CA_2026']
    
    comp_mag = mag_2026_grouped.merge(mag_2025, on='Code_Magasin', how='outer').fillna(0)
    comp_mag['Evolution_Nb'] = comp_mag['Nb_2026'] - comp_mag['Nb_2025']
    comp_mag['Evolution_CA'] = comp_mag['CA_2026'] - comp_mag['CA_2025']
    comp_mag['Evolution_%'] = ((comp_mag['CA_2026'] - comp_mag['CA_2025']) / comp_mag['CA_2025'].replace(0, 1)) * 100
    comp_mag = comp_mag.sort_values('CA_2026', ascending=False)
    comp_mag.to_excel(writer, sheet_name='Comparaison Magasins', index=False)
    
    # Sheet 5: Détail factures 2026
    detail_2026 = df_ma[df_ma['Year'] == 2026][['Date_str', 'Code_magasin', 'Nom_Client', 'Montant_HT', 'Montant_TTC', 'Montant_HT_Interet', 'Nbr_Mois_Echeance']]
    detail_2026.columns = ['Date', 'Code_Magasin', 'Client', 'Montant_HT', 'Montant_TTC', 'Interets_HT', 'Echeance']
    detail_2026 = detail_2026.sort_values('Date', ascending=False)
    detail_2026.to_excel(writer, sheet_name='Detail 2026', index=False)

print(f'Fichier exporté: {output_path}')
print('\nFeuilles créées:')
print('1. Résumé - Synthèse globale 2025 vs 2026')
print('2. Par Mois - Comparaison mars/avril')
print('3. Par Magasin 2026 - Top magasins 2026')
print('4. Comparaison Magasins - Evolution par magasin')
print('5. Detail 2026 - Liste des factures 2026')