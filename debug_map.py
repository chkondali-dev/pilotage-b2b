import pandas as pd
import requests
from io import BytesIO
from urllib.parse import quote

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"

files = {
    "vc": quote("Factures ventes enregistrées VC (4).xlsx"),
    "code_mag": quote("Code MAGASIN Business Central.xlsx"),
}

raw_vc = requests.get(GITHUB_RAW + files["vc"], timeout=30).content
df_vc = pd.read_excel(BytesIO(raw_vc))

raw_code = requests.get(GITHUB_RAW + files["code_mag"], timeout=30).content
df_code = pd.read_excel(BytesIO(raw_code))

print("VC Code Magasin sample:", df_vc["Code magasin"].dropna().unique()[:5])
print("Code Navision sample:", df_code["Code Navision"].unique()[:5])

code_col = "Code Navision"
name_col = "Unite "
mapping = df_code.set_index(code_col)[name_col].to_dict()

df_vc["Magasin"] = df_vc["Code magasin"].astype(str).str.strip().map(mapping)
print("\nAfter mapping:")
print(df_vc[["Code magasin", "Magasin"]].dropna().drop_duplicates().head(10))