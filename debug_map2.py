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

df_code.columns = [c.strip() for c in df_code.columns]
code_col = "Code Navision"
name_col = next((c for c in df_code.columns if "unit" in c.lower() or "Unit" in c), None)

print("Code_col:", code_col)
print("Name_col:", name_col)

df_code[code_col] = pd.to_numeric(df_code[code_col], errors="coerce")
mapping = dict(zip(df_code[code_col], df_code[name_col]))

print("\nMapping samples:", dict(list(mapping.items())[:5]))

df_vc["Code magasin"] = pd.to_numeric(df_vc["Code magasin"], errors="coerce")
df_vc["Magasin"] = df_vc["Code magasin"].map(mapping)
df_vc["Magasin"] = df_vc["Magasin"].fillna(df_vc["Code magasin"]).astype(str)

print("\nMagasin samples:", df_vc[["Code magasin", "Magasin"]].dropna().drop_duplicates().head(10))