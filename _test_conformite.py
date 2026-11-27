# coding: utf-8
"""Test cible : tableau Conformite 40% (Niveau, Convention) + warning."""
import sys
import warnings
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=300)
at.run()

print("EXCEPTIONS:", [e.message for e in at.exception])
print("WARNINGS conf40:", [w.value[:110] for w in at.warning
                           if "40%" in w.value])
print("METRICS conf40:", [m.label for m in at.metric
                          if "Alertes (" in m.label or "risque" in m.label.lower()
                          or "Mensualité cumulée" in m.label])

dfs = at.dataframe
print("NB_DF:", len(dfs))
if len(dfs) >= 19:
    v = dfs[18].value
    print("TABLEAU cols:", list(v.columns))
    print("TABLEAU shape:", v.shape)
    print(v.to_string())

print("OK" if not at.exception else "FAIL")
