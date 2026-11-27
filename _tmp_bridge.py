"""Démo : pont de variation volume x panier sur les données réelles."""
import sys

sys.path.insert(0, r"C:\Users\hachk\pilotage_b2b")

import pandas as pd

from data.loader import load_all_data
from data.transforms import prepare_data
from metrics.kpi import bridge_volume_panier

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 50)

raw = load_all_data()
df_vc = prepare_data(raw)[0]
annee = int(df_vc["Année"].dropna().max())
print(f"=== Année analysée : {annee} (base {annee-1}) ===\n")

for label, mois in [("ANNÉE ENTIÈRE", None), ("SEPTEMBRE SEUL", [9])]:
    b = bridge_volume_panier(df_vc, annee, mois)
    print(f"--- {label} ---")
    print(b.to_string(index=False))
    eff = b.set_index("Étape")["Effet (TND)"]
    v, p, m = eff.get("+ Volume"), eff.get("+ Panier"), eff.get("+ Mix")
    if pd.notna(v):
        print(f"  volume ({v:+,.0f}) + panier ({p:+,.0f}) + interaction ({m:+,.0f})"
              f" = {v+p+m:+,.0f}")
        print(f"  ΔCA réel (CA N − CA N-1)  = {eff.get('= CA N'):+,.0f}")
        print(f"  -> additivité exacte : {abs((v+p+m) - eff.get('= CA N')) < 1}")
        print(f"  CA N-1 = {b.loc[0, 'Valeur']:,.0f} | CA N = {b.loc[len(b)-1, 'Valeur']:,.0f}")
    print()
