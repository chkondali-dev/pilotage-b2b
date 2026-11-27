# coding: utf-8
"""Diag : colonne Convention par flux avec les VRAIES donnees (loader GitHub + prepare_data)."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import warnings
warnings.filterwarnings("ignore")
import os
os.chdir(r"C:\Users\hachk\pilotage_b2b")
import pandas as pd
from data.loader import load_all_data
from data.transforms import prepare_data
from metrics.kpi import alertes_achats_repetes, convention_de_facture

_raw = load_all_data()
print("cles _raw:", sorted(_raw.keys()))
df_vc, df_credit, df_edc, df_conv, code_df, df_part, df_cube, df_prosp, df_crm = prepare_data(_raw)
print(f"df_vc: {df_vc.shape} | df_part: {df_part.shape}")

for label, d in [("PART", df_part), ("VC", df_vc)]:
    cols = [str(c) for c in d.columns]
    has_type = "Type vente à crédit" in cols
    print(f"\n--- {label} : col 'Type vente à crédit' presente = {has_type}")
    if has_type:
        print("   valeurs:", d["Type vente à crédit"].value_counts(dropna=False).to_dict())
    print("   echantillon 'Nom':", list(d["Nom"].dropna().astype(str).unique()[:3])
          if "Nom" in cols else "PAS DE COLONNE Nom")
    r = alertes_achats_repetes(d)
    print(f"   alertes: {len(r)} | Convention uniques:",
          r["Convention"].value_counts().to_dict() if len(r) else "-")

# Tous flux
_pieces = [d for d in (df_part, df_vc) if not d.empty]
mix = pd.concat(_pieces, ignore_index=True)
rm = alertes_achats_repetes(mix)
print(f"\n--- TOUS FLUX : {len(rm)} lignes ---")
print(rm["Convention"].value_counts().head(10).to_dict())
print("\nOK")
