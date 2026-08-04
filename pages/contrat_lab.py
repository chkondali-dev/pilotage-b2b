"""
Contrat Lab intelligent — module de la MG Convention Suite.

Wizard natif Streamlit alimenté par le framework SMG v2.0 :
    questions prospect → scénario (lab/contrat_lab.py, source de vérité
    KNOWLEDGE/reference/framework_conventions_smg.md)
    → génération du dossier data/dossiers/<slug>.md
    → défense par le brain (llm/brain.py, deepseek-r1:7b via Ollama).

Le simulateur HTML historique reste disponible en onglet (legacy).
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
st.markdown("## 🧪 Contrat Lab intelligent")
st.caption(
    "Assistant de scénario alimenté par le framework v2.0 — profilez le prospect, "
    "générez son dossier, puis soumettez-le au brain pour défense avant verrouillage."
)

onglet_lab, onglet_legacy = st.tabs(["🧠 Assistant intelligent", "📄 Simulateur HTML (legacy)"])

with onglet_lab:
    from lab.contrat_lab import (DOSSIERS_DIR, _qualifier, defendre,
                                 generer_dossier)

    TYPE_LABEL = {
        "Société privée (SA/SARL)": "prive",
        "Administration publique": "admin",
        "Ordre professionnel": "ordre",
        "Association / ONG / Syndicat": "asso",
        "Groupe multi-sociétés": "groupe",
        "Coopérative / Mutuelle": "mutuelle",
    }
    AMICALE_LABEL = {
        "Oui — avec caution de l'employeur": "oui-avec",
        "Oui — employeur refuse la caution": "oui-sans",
        "Amicale seule (sans employeur structuré)": "seule",
        "Non": "non",
    }

    st.markdown("### Profil du prospect")
    choix_type = st.radio("Nature de l'entité", list(TYPE_LABEL), key="lab_type")
    reponses: dict = {"type": TYPE_LABEL[choix_type]}

    if reponses["type"] == "prive":
        choix_ami = st.radio(
            "L'entité dispose-t-elle d'une amicale ?", list(AMICALE_LABEL),
            key="lab_amicale")
        reponses["amicale"] = AMICALE_LABEL[choix_ami]
        if reponses["amicale"] == "non":
            reponses["international"] = (
                "oui" if st.radio("Activité internationale ?", ["Non", "Oui"],
                                  key="lab_inter") == "Oui" else "non")
            if reponses["international"] == "non":
                reponses["taille"] = (
                    "pme" if st.radio("Effectif ?", ["Standard", "PME (< 20 employés)"],
                                      key="lab_taille") == "PME (< 20 employés)"
                    else "standard")

    st.markdown("### Client")
    client = st.text_input(
        "Nom du client (le dossier sera créé dans data/dossiers/)",
        key="lab_client", placeholder="ex : SARL Batam Services")

    sc = _qualifier(reponses)
    if sc:
        st.markdown(
            f"**Scénario détecté : {sc['name']}** — risque **{sc['risque']}** "
            f"(niveau {sc['niveau']}) · plafond {sc['plafond']} · {sc['duree']}")

    if st.button("📝 Générer le dossier", type="primary"):
        if not client.strip():
            st.warning("Saisissez le nom du client.")
        else:
            path, sc = generer_dossier(reponses, client)
            st.session_state["lab_dossier"] = str(path)
            st.success(
                f"Dossier généré → `{path.relative_to(DOSSIERS_DIR.parent)}` "
                f"({sc['name']}, risque {sc['risque']}).")
            with st.expander("Aperçu du dossier", expanded=True):
                st.markdown(path.read_text(encoding="utf-8"))

    dossier_p = st.session_state.get("lab_dossier")
    if dossier_p and Path(dossier_p).exists():
        st.divider()
        st.markdown("### 🔬 Défense du dossier (brain)")
        st.caption(
            "Le brain (deepseek-r1:7b via Ollama) raisonne sur le dossier : "
            "couverture des garanties, niveau de sûreté, verrou framework. "
            "Analyse de 6 à 10 minutes.")
        mode = st.radio("Rendu", ["dg (synthèse exécutive)", "expert (détaillé)"],
                        key="lab_mode")
        if st.button("Défendre le dossier avant verrouillage", type="primary"):
            with st.spinner("Le brain analyse le dossier…"):
                try:
                    rendu = defendre(Path(dossier_p), mode=mode.split(" ")[0])
                except Exception as exc:
                    st.error(f"Échec de la défense : {exc}")
                    rendu = None
            if rendu:
                st.markdown(rendu)

with onglet_legacy:
    sim = ROOT / "mg-batam-convention-ai" / "OUTPUTS" / "simulateur_convention_SMG.html"
    if not sim.exists():
        st.error(f"Simulateur introuvable : {sim}")
    else:
        st.components.v1.html(sim.read_text(encoding="utf-8"), height=1100,
                              scrolling=True)