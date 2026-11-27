"""Vérifications assert-based du poids conventionnel / CA global.

Usage : python tests/test_poids_convention_cube.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.transforms import load_cube_magasin
from metrics.kpi import poids_convention_cube

# Cube brut : lignes de total annuel + 2 magasins, dont un jour N-1 au-delà
# du dernier jour N (doit être tronqué).
raw = pd.DataFrame([
    ["TEMPS ATMD", None, None],
    ["CA TTC ART", "Étiquettes de colonnes", None],
    ["Étiquettes de lignes", "16 - MG CITY NABEUL", "61 - BATAM JEAN JAURES"],
    ["2025", None, None],
    ["2025-01-01", 100, 200],
    ["2025-01-02", 100, 200],
    ["2025-01-03", 500, 500],   # jour sans équivalent en N → exclu
    ["2026", None, None],
    ["2026-01-01", 200, 300],
    ["2026-01-02", 200, None],  # case vide → ignorée
], columns=["col0", "col1", "col2"])
code = pd.DataFrame([
    [103, 16, "MG CITY NABEUL", "MG"],
    [105, 61, "BATAM JEAN JAURES", "BATAM"],
], columns=["Code Navision", "Code Business Central", "Unité", "enseigne"])

cube = load_cube_magasin(raw, code)
assert len(cube) == 9, cube
assert set(cube["Jour"]) == {1, 2, 3}
assert set(cube["Enseigne"]) == {"MG", "BATAM"}
assert cube[cube["Année"] == 2026]["CA Magasin"].sum() == 700


def _vc(annee, jour, magasin, enseigne, montant, type_vente="VC.CONV."):
    return {
        "Année": annee, "Mois": 1, "Jour": jour,
        "Date": pd.Timestamp(annee, 1, jour),
        "Magasin": magasin, "Enseigne": enseigne,
        "Montant TTC": montant, "Type vente à crédit": type_vente,
    }


vc = pd.DataFrame([
    _vc(2025, 1, "MG CITY NABEUL", "MG", 20),
    _vc(2025, 1, "BATAM JEAN JAURES", "BATAM", 60),
    _vc(2025, 2, "MG CITY NABEUL", "MG", 20),
    _vc(2025, 2, "BATAM JEAN JAURES", "BATAM", 60),
    _vc(2025, 3, "MG CITY NABEUL", "MG", 250),   # jour exclu de N-1
    _vc(2025, 3, "BATAM JEAN JAURES", "BATAM", 250),
    _vc(2026, 1, "MG CITY NABEUL", "MG", 40),
    _vc(2026, 1, "BATAM JEAN JAURES", "BATAM", 90),
    _vc(2026, 2, "MG CITY NABEUL", "MG", 40),
    _vc(2026, 2, "BATAM JEAN JAURES", "BATAM", 90),
    _vc(2026, 2, "MG CITY NABEUL", "MG", 999, "VC.PARTIC."),  # hors convention
])

r = poids_convention_cube(cube, vc, 2026)
# N : cube 700, VC.CONV. 260 (la ligne VC.PARTIC. est exclue)
assert r["ca_global"] == 700, r["ca_global"]
assert r["ca_conv"] == 260, r["ca_conv"]
assert r["ca_reste"] == 440
assert r["poids_pct"] == 37.1, r["poids_pct"]
# N-1 tronquée au jour 2 : cube 600, convention 160 (pas 1600 / 660)
assert r["ca_global_n1"] == 600, r["ca_global_n1"]
assert r["ca_conv_n1"] == 160, r["ca_conv_n1"]
assert r["poids_n1_pct"] == 26.7, r["poids_n1_pct"]
assert r["ecart_pt"] == 10.4, r["ecart_pt"]
assert r["nb_sans_correspondance"] == 0

_bat = r["par_enseigne"].set_index("Enseigne").loc["BATAM"]
assert _bat["CA global"] == 300 and _bat["CA conv"] == 180
assert r["par_magasin"].set_index("Magasin").loc["MG CITY NABEUL"]["Poids %"] == 20.0

# Sans donnée N : pas de base → NaN, jamais 0 % ou +100 % fictif.
r0 = poids_convention_cube(cube, vc, 2027)
assert pd.isna(r0["poids_pct"]) and pd.isna(r0["ecart_pt"])
assert r0["par_magasin"].empty

print("OK — parseur cube, troncature N-1, filtre VC.CONV. et poids magasin/enseigne")
