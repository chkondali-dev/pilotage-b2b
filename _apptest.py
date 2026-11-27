# coding: utf-8
"""Smoke test : exécute app.py via streamlit AppTest et vérifie l'onglet Conventions encours."""
import sys
import warnings
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=300)
at.run()

print("EXCEPTIONS:", [e.message for e in at.exception])
print("ERREURS:", [e.value for e in at.error][:5])
md = [m.value for m in at.markdown]
print("MARKERS:", {k: any(k in m for m in md)
                   for k in ["Pipeline Prospection", "Relances prioritaires",
                             "Historique des statuts", "Export", "Edition",
                             "Détails prospects", "Ajouter un projet",
                             "Conformité 40", "Achats répétés",
                             "Méthodologie", "répartition par année".capitalize()]})
print("CHECKBOXES:", [c.label for c in at.checkbox])
print("METRICS:", [m.label for m in at.metric])
print("DOWNLOADS:", [d.label for d in at.get("download_button")])
print("NB_DATAFRAMES:", len(at.dataframe))
for i, d in enumerate(at.dataframe):
    try:
        v = d.value
        print(f"DF{i}:", list(v.columns)[:10], getattr(v, "shape", None))
    except Exception as exc:  # pragma: no cover
        print(f"DF{i}: <unreadable {exc}>")
print("OK" if not at.exception else "FAIL")

