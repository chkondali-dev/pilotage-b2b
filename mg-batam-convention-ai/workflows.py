"""
Workflows orchestrés — les 3 procédures du dossier en code.
Chaque étape écrit dans OUTPUTS/ et attend la précédente.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from llm import agents, brain, config
from llm.reasoning import compile_dossier, render_json

# Business Core partagé (racine du workspace) — registre unique de suivi
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import business.conventions as _conventions

# Registre unique (Business Core) — remplace l'ancienne copie locale du projet
CSV_SIGNEES = _conventions.REGISTRY_PATH  # compat main.py (affichage du chemin)


def _slug(nom: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", nom.lower()).strip("_")


def _save(sub: str, nom: str, contenu: str) -> Path:
    date = datetime.now().strftime("%Y%m%d")
    p = config.OUTPUTS_DIR / sub / f"{_slug(nom)}_{date}.md"
    p.write_text(contenu, encoding="utf-8")
    print(f"  💾 {p}")
    return p


def _dossier_audit(audit: str, nom: str):
    """Compile un audit en ReasoningDossier + archive JSON. Retourne le dossier (None si vide).

    Les informations manquantes détectées sont ensuite injectées dans le prompt comex
    (anti-hallucination : le comex sait ce qui n'est pas confirmé).
    """
    if not audit:
        return None
    dossier = compile_dossier(audit)
    p = (config.OUTPUTS_DIR / "rapports"
         / f"{_slug(nom)}_dossier_{datetime.now().strftime('%Y%m%d')}.json")
    p.write_text(json.dumps(render_json(dossier), ensure_ascii=False, indent=2),
                 encoding="utf-8")
    print(f"  💾 {p}  ({len(dossier.facts)} faits · {len(dossier.missing)} info. manquantes)")
    return dossier


def register_convention(code: str, client: str, scenario: str = "", garantie: str = "",
                        statut: str = "Prospection", date_signature: str = "", notes: str = "") -> str:
    """Ajoute ou met à jour une ligne du registre unique (Business Core).

    Retourne "created" ou "updated".
    """
    return _conventions.register_convention(code, client, scenario=scenario, garantie=garantie,
                                            statut=statut, date_signature=date_signature, notes=notes)


def _bilan_csv(chemin: str) -> dict | None:
    """Retrouve la ligne du registre (Business Core) correspondant au fichier (bilan auto).

    Matching par tokens (≥3 lettres) entre nom du fichier et client/code,
    bonus si le code exact figure dans le nom. Ponytail: heuristique simple —
    un match sur 2+ tokens ou le code; en dessous, pas de bilan (aucun faux positif).
    """
    rows = _conventions.load_all()
    if not rows:
        return None
    stem = re.sub(r"[^a-z0-9]+", " ", Path(chemin).stem.lower())
    stem_tokens = {t for t in stem.split() if len(t) >= 3}
    if not stem_tokens:
        return None
    best, best_score, best_code = None, 0, False
    for r in rows:
        code = r.get("code", "").strip().lower()
        hay_tokens = {t for t in re.split(r"[^a-z0-9]+", f"{r.get('client', '')} {code}".lower())
                      if len(t) >= 3}
        overlap = len(stem_tokens & hay_tokens)
        has_code = code in stem.split()
        score = overlap * 10 + (10 if has_code else 0)
        if score > best_score:
            best, best_score, best_code = r, score, has_code
    if best is None or (best_score < 20 and not best_code):
        return None
    return {k: v for k, v in best.items() if str(v or "").strip()}


def _kpis_vente(client: str) -> str:
    """CA N / N-1 par convention via le loader autonome smg_data (dégradation silencieuse).

    Matching par tokens (≥3 lettres, ≥2 tokens communs) — même heuristique que _bilan_csv.
    """
    try:
        import pandas as pd
        from smg_data import load_vc
        df_vc = load_vc()
        if df_vc.empty or "Nom" not in df_vc.columns or "Montant TTC" not in df_vc.columns:
            return ""
        client_tokens = {t for t in re.split(r"[^a-z0-9]+", client.lower()) if len(t) >= 3}
        if not client_tokens:
            return ""
        noms = df_vc["Nom"].fillna("")
        noms_tokens = noms.map(
            lambda n: {t for t in re.split(r"[^a-z0-9]+", n.lower()) if len(t) >= 3})
        scores = noms_tokens.map(lambda s: len(client_tokens & s))
        match = df_vc[scores >= 2]
        if match.empty or "Année" not in match.columns:
            return ""
        annee_n = int(match["Année"].max())
        ca_n = match[match["Année"] == annee_n]["Montant TTC"].sum()
        ca_n1 = match[match["Année"] == annee_n - 1]["Montant TTC"].sum()
        evo = f"{(ca_n / ca_n1 - 1) * 100:+.1f}%" if ca_n1 else "N/A (N-1 nul)"
        return (f"CA facturé {annee_n}: {ca_n:,.0f} TND | CA {annee_n - 1}: {ca_n1:,.0f} TND"
                f" | Évolution: {evo}")
    except Exception:
        return ""


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
    dossier_audit = _dossier_audit(audit, f"audit_{nom}")

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
    if dossier_audit and dossier_audit.missing:
        dossier += ("\n\n--- POINTS À CONFIRMER (détection automatique) ---\n"
                    + "\n".join(f"- {m}" for m in dossier_audit.missing))
    decision = agents.synthese_comex(dossier)
    if decision:
        _save("syntheses", f"decision_{nom}", decision)

    print("\n✅ Revue terminée. Résultats dans OUTPUTS/.")


def _demande_oui_non(question: str) -> bool:
    """Gate humain (verrou 🔒, signatures) — non interactif : retourne True."""
    try:
        rep = input(f"  {question} [o/N] ").strip().lower()
        return rep in ("o", "oui", "y", "yes")
    except EOFError:
        return True  # mode non interactif (tests / pipeline) : poursuit


def _avec_framework(texte: str) -> str:
    """Appose le référentiel (extrait) au document audité — l'audit compare à la norme."""
    p = config.KNOWLEDGE_DIR / "reference" / "framework_conventions_smg.md"
    if not p.exists():
        return texte
    extrait = p.read_text(encoding="utf-8", errors="ignore")[:8000]
    return f"{texte}\n\n--- RÉFÉRENTIEL (extrait framework v2.0) ---\n{extrait}"


def _consigne_redaction(contexte: str, num: str, params: dict) -> str:
    """Consigne de rédaction pilotée par les paramètres métier du scénario (C2)."""
    return (
        f"Rédige une convention de crédit B2B SMG — scénario {num} ({params['titre']}), "
        f"régime {params['regime']}, conformément au framework v2.0.\n"
        f"Contexte : {contexte}\n\n"
        f"Paramètres contractuels (Business Core — ne pas dévier) :\n"
        f"- Garantie : {params['garantie']}\n"
        f"- Plafond : {params['plafond'][0]} à {params['plafond'][1]} TND\n"
        f"- Durée : {params['duree_mois']} mois\n"
        f"- Taux : {params['taux']}%/mois\n"
        f"- Circuit : {params['circuit']}\n"
        f"- RFA : {params['rfa']}\n"
        f"- Seuil 40% : {"taux d'endettement à mentionner" if params['seuil_40'] else 'non applicable'}\n"
        f"- Condition suspensive (PLUS) : "
        f"{'traite + reconnaissance de dette' if params['condition_suspensive'] else 'aucune'}\n"
        f"- Recouvrement : {params['recouvrement']}\n"
        + (f"- Règle absolue : {params['regle_absolue']}\n" if params.get("regle_absolue") else "")
        + "\nRègles impératives :\n"
        "- Terminologie : 'cession sur salaire' — JAMAIS 'cession de créance' ni "
        "'Réserve de Fonds d'Avances'.\n"
        "- Qualités des parties, ne pas remplacer : " + params["qualites"] + ".\n"
        "- Structure : 17 articles (parties, objet, garanties, plafond, durée, modalités de "
        "paiement, qualités/conditions, traitement des données, confidentialité, obligations "
        "SMG, suspension/défaut, recouvrement, résiliation, litiges/juridiction, élection de "
        "domicile, preuve électronique, force majeure/décès) + 3 annexes (spécimen de "
        "signature, reconnaissance de dette légalisée, spécimen lettre de change le cas échéant).\n"
        "- AUCUN chiffre inventé : les champs non fournis (client, montants nominatifs, "
        "échéancier) restent '________' à compléter par l'expert."
    )


def _extraire_verdict(rendu: str) -> str:
    """Verdict 🟢/🟠/🔴 du rendu brain (défaut 🟠)."""
    m = re.search(r"[🟢🟠🔴]", rendu or "")
    return m.group(0) if m else "🟠"


def nouvelle_convention(contexte: str) -> None:
    """Workflow création de convention — FRAMEWORK_CONVENTIONS_SMG.md v2.0 (9 étapes / 4 phases).

    Phase 1 Rédaction : 1 Prospection → 2 Choix scénario → 3 Rédaction
    Phase 2 Verrouillage : 4 DÉFENSE DU DOSSIER → 5 Décision finale 🔒
    Phase 3 Validation : 6 Juridique → 7 Corrections → 8 Signatures (gate D1)
    Phase 4 Suivi : 9 Recouvrement / registre

    Règle impérative du framework : le verrou risque (4-5) PRÉCÈDE le juridique (6).
    """
    from business import scenarios  # brique métier : matrice 7 scénarios (framework v2.0)

    print("\n=== Nouvelle convention — framework v2.0 (9 étapes / 4 phases) ===")

    # ── PHASE 1 · RÉDACTION ──
    print("\n[1/9] Prospection / qualification du client...")
    profil = scenarios.extraire_profil(contexte)
    if profil["type"] == "physique" and profil["amicale"] and profil["employeur_garant"] is None:
        profil["employeur_garant"] = _demande_oui_non(
            "L'employeur garantit-il le prélèvement (caution employeur) ?")
    print(f"  Profil : {profil['type']} | amicale={profil['amicale']} "
          f"| administration={profil['administration']} | groupe={profil['groupe']}")

    print("\n[2/9] Choix du scénario (matrice 7 — arbre B2)...")
    num = scenarios.choisir_scenario(profil)
    if num is None:
        print("  ❌ Profil hors matrice des 7 scénarios — compléter le contexte "
              "(type de client, amicale, garantie employeur).")
        return
    params = scenarios.parametres_scenario(num)
    print(f"  Scénario {num} · {params['titre']} ({params['regime']})")
    print(f"  Garantie : {params['garantie']} | Plafond : {params['plafond'][0]}–"
          f"{params['plafond'][1]} TND | {params['duree_mois']} mois | {params['taux']}%/mois")

    print("\n[3/9] Rédaction paramétrée...")
    brouillon = agents.rediger(_consigne_redaction(contexte, num, params))
    if not brouillon:
        print("  ❌ Étape interrompue — aucun LLM dispo"); return
    _save("contrats", f"convention_scenario_{num}_v1", brouillon)

    # ── PHASE 2 · VERROUILLAGE RISQUE (avant le juridique) ──
    print("\n[4/9] Défense du dossier (brain, pipeline A→D)...")
    defense = brain.raisonner(
        f"Défends le dossier de convention scénario {num} ({params['titre']}). "
        f"Garantie : {params['garantie']}. Circuit : {params['circuit']}. "
        f"Contexte : {contexte}. Argumente les risques traités (garanties, seuil 40%, RFA, "
        "recouvrement) et ce qui reste à sécuriser avant verrouillage.",
        mode="dg")
    verdict = "🟠"
    if defense:
        _save("rapports", f"defense_dossier_scenario_{num}", defense)
        verdict = _extraire_verdict(defense)
    print(f"  Verdict du dossier : {verdict}")

    print("\n[5/9] Décision finale (verrou 🔒)...")
    if not _demande_oui_non(f"Verrouiller le dossier scénario {num} (verdict {verdict}) "
                            "et passer en validation juridique ?"):
        print("  ❌ Dossier non verrouillé — convention non produite. "
              "Ajuster la défense (étape 4/9).")
        return
    _save("syntheses", f"decision_verrou_scenario_{num}",
          f"# Verrou du dossier — scénario {num}\n\n"
          f"Verdict : {verdict}\n"
          "Défense : voir rapports/defense_dossier_scenario_{num}")

    # ── PHASE 3 · VALIDATION ──
    print("\n[6/9] Juridique (conformité au framework)...")
    verif = agents.audit(_avec_framework(brouillon), "(brouillon)")
    if verif:
        _save("rapports", f"verification_scenario_{num}", verif)
    dossier_verif = _dossier_audit(verif, f"verification_scenario_{num}")

    print("\n[7/9] Corrections...")
    corrige = agents.rediger(
        f"Intègre les corrections suivantes dans le brouillon de convention scénario {num} :\n\n"
        f"{verif or '(aucune)'}\n\nBrouillon :\n{brouillon}")
    if corrige:
        _save("contrats", f"convention_scenario_{num}_v2", corrige)
    texte_final = corrige or brouillon

    print("\n[8/9] Gate final D1 + signatures (DG → client)...")
    checks = scenarios.verifier_production(texte_final, num)
    ok_all = True
    for c in checks:
        statut = "✅" if c["ok"] else ("⚠️" if c["severity"] == "warning" else "❌")
        if not c["ok"] and c["severity"] == "erreur":
            ok_all = False
        print(f"  {statut} {c['check']} — {c['detail']}")
    if not ok_all:
        print("  ⚠️ Gate non vert : corriger avant signature (erreurs ❌ ci-dessus).")
    print("  Requis : " + " · ".join(params["signataires"]))
    _demande_oui_non("Convention signée par toutes les parties ?")

    # ── PHASE 4 · SUIVI ──
    print("\n[9/9] Recouvrement / inscription au registre...")
    m_client = re.search(r"[Cc]lient\s*[:：]\s*([^\n,]+)", contexte)
    client = m_client.group(1).strip() if m_client else "client à préciser"
    code = f"CONV-{num}-{datetime.now().strftime('%Y%m%d')}"
    etat = register_convention(code, client, scenario=f"{num} - {params['titre']}",
                               garantie=params["garantie"], statut="Prospection",
                               notes=f"Framework v2.0 | verrou {verdict} | "
                                     f"recouvrement : {params['recouvrement']}")
    print(f"  Registre : {etat} → {code} ({client})")

    if ok_all:
        print("\n✅ Terminé. Résultats dans OUTPUTS/.")
    else:
        print("\n⚠️ Terminé avec réserves — gate D1 non vert : corriger les erreurs ❌ "
              "du brouillon final avant signature (étape 8/9).")


def renouvellement(chemin: str, performance: str = "") -> None:
    """Workflow renouvellement : audit → contre-audit → négociation → décision.

    Le bilan est alimenté automatiquement : ligne conventions_signees.csv + KPIs vente
    (CA N / N-1) via le pipeline du dashboard, si disponibles.
    """
    doc = Path(chemin).read_text(encoding="utf-8", errors="ignore")
    nom = Path(chemin).stem

    ligne = _bilan_csv(chemin)
    bilan_csv = " | ".join(f"{k}={v}" for k, v in ligne.items()) if ligne else ""
    kpis = _kpis_vente(ligne["client"] if ligne else nom)
    bilan = " | ".join(x for x in (bilan_csv, kpis) if x) or performance or "(non fournie)"

    print(f"\n=== Renouvellement — {nom} ===")
    print(f"  Bilan auto : {bilan}")

    print("\n[1/4] Audit documentaire...")
    audit = agents.audit(doc, chemin)
    if not audit:
        print("  ❌ Étape interrompue — aucun LLM dispo"); return
    _save("rapports", f"audit_renouvellement_{nom}", audit)
    dossier_audit = _dossier_audit(audit, f"audit_renouvellement_{nom}")

    print("\n[2/4] Contre-audit...")
    contre = agents.contre_audit(audit, doc)
    if contre:
        _save("rapports", f"contre-audit_renouvellement_{nom}", contre)

    print("\n[3/4] Stratégie de renégociation...")
    fiche = agents.preparer_negociation(
        f"Renouvellement de la convention {nom}. Bilan de la période : {bilan}", doc)
    if fiche:
        _save("syntheses", f"negociation_renouvellement_{nom}", fiche)

    print("\n[4/4] Décision comex...")
    dossier = f"Renouvellement de : {nom}\n\nBilan : {bilan}\n\nAudit :\n{audit}\n\nContre-audit :\n{contre or '(non généré)'}"
    if dossier_audit and dossier_audit.missing:
        dossier += ("\n\n--- POINTS À CONFIRMER (détection automatique) ---\n"
                    + "\n".join(f"- {m}" for m in dossier_audit.missing))
    decision = agents.synthese_comex(dossier)
    if decision:
        _save("syntheses", f"decision_renouvellement_{nom}", decision)

    print("\n✅ Terminé. Résultats dans OUTPUTS/.")
