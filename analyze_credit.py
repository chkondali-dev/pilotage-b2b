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

# Filter mars/avril jusqu'au 26
df_ma = df_36[(df_36['Month'].isin([3, 4])) & (df_36['Day'] <= 26)]

print('='*70)
print('COMPARAISON DATE A DATE - ECHEANCE 36 MOIS - MARS/AVRIL (jusqu au 26)')
print('='*70)

# Daily comparison
for year in [2025, 2026]:
    data = df_ma[df_ma['Year'] == year]
    print(f'\n=== {year} ===')
    print(f'Nombre de factures: {len(data)}')
    print(f'CA HT: {data["Montant_HT"].sum():,.2f}')
    print(f'CA TTC: {data["Montant_TTC"].sum():,.2f}')
    print(f'Interets HT: {data["Montant_HT_Interet"].sum():,.2f}')

# Par jour
print('\n' + '='*70)
print('COMPARAISON PAR JOUR (moyenne journaliere)')
print('='*70)

par_jour_2025 = df_ma[df_ma['Year'] == 2025].groupby('Date_compta').agg({
    'N_Facture': 'count',
    'Montant_TTC': 'sum'
}).rename(columns={'N_Facture': 'Nb_2025', 'Montant_TTC': 'CA_2025'})

par_jour_2026 = df_ma[df_ma['Year'] == 2026].groupby('Date_compta').agg({
    'N_Facture': 'count',
    'Montant_TTC': 'sum'
}).rename(columns={'N_Facture': 'Nb_2026', 'Montant_TTC': 'CA_2026'})

comp = par_jour_2025.join(par_jour_2026, how='outer').fillna(0)
comp['Evolution_CA'] = comp['CA_2026'] - comp['CA_2025']

print('\n--- MARS 2025 ---')
mars_2025 = df_ma[(df_ma['Year'] == 2025) & (df_ma['Month'] == 3)]
print(f'Nb factures: {len(mars_2025)}')
print(f'CA TTC: {mars_2025["Montant_TTC"].sum():,.2f}')

print('\n--- MARS 2026 ---')
mars_2026 = df_ma[(df_ma['Year'] == 2026) & (df_ma['Month'] == 3)]
print(f'Nb factures: {len(mars_2026)}')
print(f'CA TTC: {mars_2026["Montant_TTC"].sum():,.2f}')

print('\n--- AVRIL 2025 (jusqu au 26) ---')
avril_2025 = df_ma[(df_ma['Year'] == 2025) & (df_ma['Month'] == 4) & (df_ma['Day'] <= 26)]
print(f'Nb factures: {len(avril_2025)}')
print(f'CA TTC: {avril_2025["Montant_TTC"].sum():,.2f}')

print('\n--- AVRIL 2026 (jusqu au 26) ---')
avril_2026 = df_ma[(df_ma['Year'] == 2026) & (df_ma['Month'] == 4) & (df_ma['Day'] <= 26)]
print(f'Nb factures: {len(avril_2026)}')
print(f'CA TTC: {avril_2026["Montant_TTC"].sum():,.2f}')

# Evolution par mois
print('\n' + '='*70)
print('SYNTHESE EVOLUTION PAR MOIS')
print('='*70)

for month in [3, 4]:
    month_name = 'Mars' if month == 3 else 'Avril'
    for year in [2025, 2026]:
        data = df_ma[(df_ma['Year'] == year) & (df_ma['Month'] == month)]
        if year == 2025:
            ca_2025 = data['Montant_TTC'].sum()
            nb_2025 = len(data)
        else:
            ca_2026 = data['Montant_TTC'].sum()
            nb_2026 = len(data)
    
    evol_nb = ((nb_2026 - nb_2025) / nb_2025 * 100) if nb_2025 > 0 else 0
    evol_ca = ((ca_2026 - ca_2025) / ca_2025 * 100) if ca_2025 > 0 else 0
    
    print(f'\n{month_name}:')
    print(f'  2025: {nb_2025} factures | {ca_2025:,.2f} CA')
    print(f'  2026: {nb_2026} factures | {ca_2026:,.2f} CA')
    print(f'  Evolution: {evol_nb:+.1f}% nb | {evol_ca:+.1f}% CA')

# Top magasins 2025 vs 2026
print('\n' + '='*70)
print('TOP 10 MAGASINS 2026 (avec comparaison 2025)')
print('='*70)

mag_2026 = df_ma[df_ma['Year'] == 2026].groupby('Code_magasin').agg({
    'N_Facture': 'count',
    'Montant_TTC': 'sum'
}).rename(columns={'N_Facture': 'Nb_2026', 'Montant_TTC': 'CA_2026'})

mag_2025 = df_ma[df_ma['Year'] == 2025].groupby('Code_magasin').agg({
    'N_Facture': 'count',
    'Montant_TTC': 'sum'
}).rename(columns={'N_Facture': 'Nb_2025', 'Montant_TTC': 'CA_2025'})

comp_mag = mag_2026.join(mag_2025, how='outer').fillna(0)
comp_mag = comp_mag.sort_values('CA_2026', ascending=False).head(10)
print(comp_mag.to_string())