"""Benchmark rerun « changement de filtre Annee » (Phase 2, mesure AVANT/APRES).

Execute le script app.py en mode bare (sans serveur Streamlit), hors-ligne
(snapshot tests/fixtures/, horloge figee), en simulant le selecteur « Annee ».
Le scan de tendances IA est neutralise (mock) : on mesure le code du
dashboard, pas les timeouts reseau/LLM.

Le cache st.cache_data persiste entre les runs du meme process : le 2e run
avec une annee differente reproduit un vrai rerun Streamlit (pre-calcs
invalides, chargement conserve).

Usage :  python -X utf8 tests/bench_rerun.py [2026,2025,2026] [ONGLET]
ONGLET (apres refonte) : valeur simulee du selecteur, ex "Vue Executive".
Sortie : une ligne RUN par annee + resume.
"""
import os
import runpy
import sys
import time

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TESTS_DIR)
for p in (ROOT_DIR, TESTS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from baseline_lib import offline_env  # noqa: E402

import streamlit as st  # noqa: E402

_ANNEES = [int(a) for a in (sys.argv[1] if len(sys.argv) > 1 else "2026,2025,2026").split(",")]
_ONGLET = sys.argv[2] if len(sys.argv) > 2 else None

_AN_COURANTE = [_ANNEES[0]]
_orig_selectbox = st.selectbox


def _selectbox(label, options, **kw):
    if label == "Année":
        return _AN_COURANTE[0]
    return _orig_selectbox(label, options, **kw)


st.selectbox = _selectbox

if _ONGLET is not None:
    # Apres refonte 2.1 : seul l'onglet actif est simule.
    st.segmented_control = lambda label, options, **kw: _ONGLET  # noqa: E731
    st.radio = lambda label, options, **kw: _ONGLET  # noqa: E731

# Scan tendances : mock (on mesure le dashboard, pas les timeouts LLM).
import trend_analyzer as _ta  # noqa: E402
import trend_alert_panel as _tap  # noqa: E402

_ta.TrendAnalyzer.scan_all = lambda self: {"convention_alerts": []}
_tap.render_alert_panel = lambda *a, **k: None

temps = []
with offline_env():
    for an in _ANNEES:
        _AN_COURANTE[0] = an
        t0 = time.perf_counter()
        runpy.run_path(os.path.join(ROOT_DIR, "app.py"), run_name="__main__")
        dt = time.perf_counter() - t0
        temps.append((an, dt))
        print(f"RUN annee={an}: {dt:.2f}s", flush=True)

print("RESUME " + " | ".join(f"{an}: {dt:.2f}s" for an, dt in temps))
