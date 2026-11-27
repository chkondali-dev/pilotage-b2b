# coding: utf-8
"""Test unitaire : Convention via TYPE DE VENTE (pas de mapping par nom)."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import warnings
warnings.filterwarnings("ignore")
import os
os.chdir(r"C:\Users\hachk\pilotage_b2b")

import pandas as pd
from data.config import SEUILS, TYPES_CONVENTION
from metrics.kpi import alertes_achats_repetes, convention_de_facture

print("TYPES_CONVENTION =", TYPES_CONVENTION)

dfp = pd.read_excel("CREDIT PARTICULIER.xlsx")
vc = pd.read_excel("Factures ventes enregistrées VC (4).xlsx")

# --- Test 1 : convention_de_facture sur chaque flux ---
print("\n=== convention_de_facture ===")
print("PART:", sorted(dfp.pipe(convention_de_facture).unique())[:5],
      "| attendu: que 'Hors convention'")
print("VC:", sorted(vc.pipe(convention_de_facture).unique())[:5],
      "| attendu: ~88 conventions, JAMAIS 'Hors convention'")

# --- Test 2 : alertes credit-part -> tout Hors convention ---
res = alertes_achats_repetes(dfp)
print(f"\n=== PART: {len(res)} lignes ===")
al = len(res[res["Niveau"] == "🔴 Alerte"])
rq = len(res[res["Niveau"] == "🟡 À risque"])
tout_hc = (res["Convention"] == "Hors convention").all()
print(f"Alerte={al} (att 10) | Risque={rq} (att 324) | tout Hors conv: {tout_hc}")

# --- Test 3 : alertes VC -> conventions renseignees ---
rv = alertes_achats_repetes(vc)
hors_vc = (rv["Convention"] == "Hors convention").sum()
print(f"\n=== VC: {len(rv)} lignes | Hors conv residuel: {hors_vc} (att 0) ===")
print(rv.head(5)[["Niveau", "Nom", "Convention", "Nb achats"]].to_string(index=False))

# --- Test 4 : flux mixte (part + VC EDC) ---
edc = pd.read_excel("Factures ventes enregistrées VC CONVENTION EDC.xlsx")
mix = pd.concat([dfp, edc], ignore_index=True)
rm = alertes_achats_repetes(mix)
print(f"\n=== MIXTE part+EDC: {len(rm)} | conventions != HC:",
      (rm["Convention"] != "Hors convention").sum())

# --- Test 5 : DF sans colonne type -> tout Hors convention ---
sans = dfp.drop(columns=["Type vente à crédit", "Groupe compta. client"])
print("\nSANS colonne type:", sorted(convention_de_facture(sans).unique()))

ok = (al == 10 and rq == 324 and tout_hc and hors_vc == 0)
print("\nRESULTAT:", "OK" if ok else "ECART")
print("OK" if ok else "FAIL")
