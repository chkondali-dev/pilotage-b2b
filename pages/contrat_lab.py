"""
Contrat Lab — module de la MG Convention Suite.

Laboratoire de conventions : embarqué pour l'instant (simulateur HTML
fiche réflexion client, 5 étapes → template recommandé + risque).
Évoluera selon les todos : branchement sur le brain (défense de dossier),
les dossiers data/dossiers/, le framework v2.0 et le registre CSV.
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ui.components import inject_css

st.set_page_config(
    page_title="Contrat Lab — MG Convention Suite",
    layout="wide",
    page_icon="🧪",
)

inject_css()

st.page_link("suite.py", label="← Accueil MG Convention Suite")

st.markdown("## 🧪 Contrat Lab")
st.caption("Simulateur de scénario client — template recommandé, garanties et niveau de risque.")

sim = ROOT / "mg-batam-convention-ai" / "OUTPUTS" / "simulateur_convention_SMG.html"
if not sim.exists():
    st.error(f"Simulateur introuvable : {sim}")
    st.stop()

html = sim.read_text(encoding="utf-8")
st.components.v1.html(html, height=1100, scrolling=True)
