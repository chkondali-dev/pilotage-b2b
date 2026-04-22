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
print("VC COLUMNS:", df_vc.columns.tolist())
print("VC SHAPE:", df_vc.shape)
print(df_vc.head(2))

print("\n--- Code Magasin mapping ---")
raw_code = requests.get(GITHUB_RAW + files["code_mag"], timeout=30).content
df_code = pd.read_excel(BytesIO(raw_code))
print("Code columns:", df_code.columns.tolist())
print(df_code.head(3))