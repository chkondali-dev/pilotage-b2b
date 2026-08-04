"""
Contrat Lab — module de la MG Convention Suite.

Simulateur de scénario client (fiche réflexion, 5 étapes → template
recommandé + risque) puis, juste en dessous, avis AI du brain sur le
dossier sélectionné (data/dossiers/). Un seul bloc, pas d'onglets.
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mg-batam-convention-ai"))
from ui.components import inject_css

st.set_page_config(
    page_title="Contrat Lab — MG Convention Suite",
    layout="wide",
    page_icon="🧪",
)

inject_css()

st.page_link("suite.py", label="← Accueil MG Convention Suite")
st.markdown("## 🧪 Contrat Lab")
st.caption(
    "Simulez le scénario client dans la fiche réflexion, puis demandez "
    "l'avis AI du brain sur le dossier (data/dossiers/).")

# ── 1. Simulateur HTML (fiche réflexion) ─────────────────────────
sim = ROOT / "mg-batam-convention-ai" / "OUTPUTS" / "simulateur_convention_SMG.html"
if not sim.exists():
    st.error(f"Simulateur introuvable : {sim}")
else:
    st.components.v1.html(sim.read_text(encoding="utf-8"), height=1100, scrolling=True)

# ── 2. Avis AI : défense d'un dossier existant ───────────────────
DOSSIERS_DIR = ROOT / "mg-batam-convention-ai" / "data" / "dossiers"

if DOSSIERS_DIR.exists():
    st.divider()
    st.markdown("### 🤖 Avis AI — défense du dossier")
    st.caption(
        "Le brain (qwen2.5:7b via Ollama) raisonne sur le dossier choisi : "
        "couverture des garanties, niveau de sûreté, verrou framework. "
        "Analyse de 3 à 4 minutes.")

    from lab.contrat_lab import defendre

    dossiers = sorted(p.name for p in DOSSIERS_DIR.glob("*.md"))
    if not dossiers:
        st.info("Aucun dossier dans data/dossiers/ pour le moment.")
    else:
        choix = st.selectbox("Dossier à analyser", dossiers)
        mode = st.radio("Rendu", ["dg (synthèse exécutive)", "expert (détaillé)"],
                        key="lab_mode")
        if st.button("🤖 Avis AI sur le dossier", type="primary"):
            with st.spinner("Le brain analyse le dossier…"):
                try:
                    rendu = defendre(DOSSIERS_DIR / choix, mode=mode.split(" ")[0])
                except Exception as exc:
                    st.error(f"Échec de l'analyse : {exc}")
                    rendu = None
            if rendu:
                st.markdown(rendu)