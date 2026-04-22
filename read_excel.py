import pandas as pd
import sys

xl = pd.ExcelFile(r'C:\Users\hachk\OneDrive - Société Magasin Général (SMG)\Documents\hamadi\grands compte\hamadi\dashbord convention\table vente\2025\TDC CONVENTION 1.xlsm')
df = pd.read_excel(xl, sheet_name='convention en cours')
print("COLUMNS:", df.columns.tolist()[:20])
print("SHAPE:", df.shape)

non_empty = df.dropna(how='all')
print("NON_EMPTY_ROWS:", len(non_empty))

with open('output.txt', 'w', encoding='utf-8') as f:
    f.write("COLUMNS:\n")
    for col in df.columns.tolist():
        f.write(f"  {col}\n")
    f.write("\nNON_EMPTY_ROWS:\n")
    for i in range(min(10, len(non_empty))):
        row = non_empty.iloc[i]
        vals = [str(v) for v in row.dropna().tolist()[:15]]
        f.write(f"ROW_{i}: {', '.join(vals)}\n")