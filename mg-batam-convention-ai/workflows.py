"""
Workflows orchestrés — les 3 procédures du dossier en code.
Chaque étape écrit dans OUTPUTS/ et attend la précédente.
"""
import re
from datetime import datetime
from pathlib import Path
from llm import agents, config


def _slug(nom: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", nom.lower()).strip("_")


def _save(sub: str, nom: str, contenu: str) -> Path:
    date = datetime.now().strftime("%Y%m%d")
    p = config.OUTPUTS_DIR / sub / f"{_slug(nom)}_{date}.md"
    p.write_text(contenu, encoding="utf-8")
    print(f"  💾 {p}")
    return p


def revue_complete(chemin: str, renégocier: bool = False) -> None:
    """Workflow revue complète : audit → contre-audit → négociation → décision."""
    doc = Path(chemin).read_text(encoding="utf-8", errors="ignore")
    nom = Path(chemin).stem

    print(f"\n=== Revue complète — {nom} ===")

    print("\n[1/4] Audit juridique...")
    audit = agents.audit(doc, chemin)
    if not audit:
        print("  ❌ Étape interrompue — aucun LLM dispo"); return
    p_audit = _save("rapports", f"audit_{nom}", audit)

    print("\n[2/4] Contre-audit...")
    contre = agents.contre_audit(audit, doc)
    if contre:
        _save("rapports", f"contre-audit_{nom}", contre)

    if renégocier:
        print("\n[3/4] Stratégie de négociation...")
        fiche = agents.preparer_negociation(
            "Renégociation suite à revue complète. Contexte : voir audit.", audit)
        if fiche:
            _save("syntheses", f"negociation_{nom}", fiche)

    print("\n[4/4] Décision comex...")
    dossier = f"Convention : {nom}\n\n--- AUDIT ---\n{audit}\n\n--- CONTRE-AUDIT ---\n{contre or '(non généré)'}"
    if renégocier and fiche:
        dossier += f"\n\n--- NÉGOCIATION ---\n{fiche}"
    decision = agents.synthese_comex(dossier)
    if decision:
        _save("syntheses", f"decision_{nom}", decision)

    print("\n✅ Revue terminée. Résultats dans OUTPUTS/.")


def nouvelle_convention(contexte: str) -> None:
    """Workflow nouvelle convention : ébauche → conformité → stress-test → décision."""
    print("\n=== Nouvelle convention ===")

    print("\n[1/5] Ébauche...")
    brouillon = agents.rediger(f"Rédige une convention de crédit B2B. Contexte : {contexte}")
    if not brouillon:
        print("  ❌ Étape interrompue — aucun LLM dispo"); return
    _save("contrats", "convention_brouillon", brouillon)

    print("\n[2/5] Vérification conformité...")
    verif = agents.audit(brouillon, "(brouillon)")
    if verif:
        _save("rapports", "verification_brouillon", verif)

    print("\n[3/5] Stress-test...")
    stress = agents.contre_audit(verif or brouillon, brouillon)
    if stress:
        _save("rapports", "contre-audit_brouillon", stress)

    print("\n[4/5] Corrections...")
    corrige = agents.rediger(
        f"Intègre les corrections suivantes dans le brouillon de convention :\n\n{stress or verif or '(aucune)'}\n\nBrouillon :\n{brouillon}")
    if corrige:
        _save("contrats", "convention_v2", corrige)

    print("\n[5/5] Décision comex...")
    decision = agents.synthese_comex(f"Convention : nouvelle.\n\nBrouillon final :\n{corrige or brouillon}")
    if decision:
        _save("syntheses", "decision_nouvelle_convention", decision)

    print("\n✅ Terminé. Résultats dans OUTPUTS/.")


def renouvellement(chemin: str, performance: str = "") -> None:
    """Workflow renouvellement : audit → contre-audit → négociation → décision."""
    doc = Path(chemin).read_text(encoding="utf-8", errors="ignore")
    nom = Path(chemin).stem

    print(f"\n=== Renouvellement — {nom} ===")

    print("\n[1/4] Audit documentaire...")
    audit = agents.audit(doc, chemin)
    if not audit:
        print("  ❌ Étape interrompue — aucun LLM dispo"); return
    _save("rapports", f"audit_renouvellement_{nom}", audit)

    print("\n[2/4] Contre-audit...")
    contre = agents.contre_audit(audit, doc)
    if contre:
        _save("rapports", f"contre-audit_renouvellement_{nom}", contre)

    print("\n[3/4] Stratégie de renégociation...")
    fiche = agents.preparer_negociation(
        f"Renouvellement de la convention {nom}. Performance de la période : {performance or '(non fournie)'}", doc)
    if fiche:
        _save("syntheses", f"negociation_renouvellement_{nom}", fiche)

    print("\n[4/4] Décision comex...")
    decision = agents.synthese_comex(
        f"Renouvellement de : {nom}\n\nPerformance : {performance or '(non fournie)'}\n\nAudit :\n{audit}\n\nContre-audit :\n{contre or '(non généré)'}")
    if decision:
        _save("syntheses", f"decision_renouvellement_{nom}", decision)

    print("\n✅ Terminé. Résultats dans OUTPUTS/.")
