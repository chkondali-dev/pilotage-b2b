import pandas as pd
from data.loader import load_all_data
from data.transforms import prepare_data

raw = load_all_data()
code_df = raw.get('code_magasin', pd.DataFrame())
df_vc, df_credit, df_edc, df_conv, code_df_out, df_credit_part, df_cube_mag, df_prospection, df_crm = prepare_data(raw)

print('Transformed df_cube_mag columns exactly:')
for i, c in enumerate(df_cube_mag.columns):
    print(f'  {i}: "{c}"')

print()
annee_col = [c for c in df_cube_mag.columns if 'Annee' in c or 'Année' in c]
print(f'Annee matching cols: {annee_col}')
if annee_col:
    print(f'  Values: {df_cube_mag[annee_col[0]].unique()[:10]}')

print()
ca_col = [c for c in df_cube_mag.columns if 'CA' in c.upper() or 'Montant' in c.upper() or 'TTC' in c.upper()]
print(f'CA/Montant/TTC matching cols: {ca_col}')
if ca_col:
    print(f'  Values sample: {df_cube_mag[ca_col[0]].unique()[:5]}')
    print(f'  Sum: {df_cube_mag[ca_col[0]].sum()}')

print()
from metrics.kpi import ca_sum
for annee in [2024, 2025, 2026]:
    s = ca_sum(df_cube_mag, annee)
    print(f'  ca_sum(df, {annee}) = {s}')