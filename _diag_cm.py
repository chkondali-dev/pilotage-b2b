# coding: utf-8
"""Diag : couverture conv_map (nom -> convention) sur les lignes d'alerte/risque."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import warnings
warnings.filterwarnings("ignore")
import os
os.chdir(r"C:\Users\hachk\pilotage_b2b")
import pandas as pd
from data.loader import load_all_data
from data.transforms import prepare_data
from metrics.kpi import alertes_achats_repetes, mapping_nom_convention

_raw = load_all_data()
df_vc, df_credit, df_edc, df_conv, code_df, df_part, df_cube, df_prosp, df_crm = prepare_data(_raw)

mp = mapping_nom_convention(df_vc)
print("mapping:", len(mp), "noms -> convention")

# Sans mapping (etat actuel)
res0 = alertes_achats_repetes(df_part)
# Avec mapping (etat vise)
res1 = alertes_achats_repetes(df_part, conv_map=mp)
from data.config import LIBELLE_HORS_CONVENTION
hc0 = (res0["Convention"] == LIBELLE_HORS_CONVENTION).sum()
hc1 = (res1["Convention"] == LIBELLE_HORS_CONVENTION).sum()
print(f"SANS mapping: {hc0}/{len(res0)} Hors convention")
print(f"AVEC mapping: {hc1}/{len(res1)} Hors convention "
      f"-> {len(res1)-hc1} lignes rattachees a une convention")
print(res1[res1["Convention"] != LIBELLE_HORS_CONVENTION]
      [["Niveau", "Nom", "Convention", "Année", "Nb achats"]].to_string(index=False))
print("\nOK")
