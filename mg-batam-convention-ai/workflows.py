"""
Workflows orchestrés — les 3 procédures du dossier en code.
Chaque étape écrit dans OUTPUTS/ et attend la précédente.
"""
import csv as _csv
import re
import sys
from datetime import date, datetime
from pathlib import Path
from llm import agents, config

# Pont vers le repo racine : CSV de suivi des conventions signées (dashboard tabs[6])
ROOT_REPO = Path(__file__).resolve().parent.parent
CSV_SIGNEES = ROOT_REPO / "data" / "conventions_signees.csv"
CSV_FIELDS = ["code", "client", "scenario", "garantie", "statut",
              "date_debut_prospection", "date_signature", "nb_modifications", "notes"]


def _slug(nom: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", nom.lower()).strip("_")


def _save(sub: str, nom: str, contenu: str) -> Path:
    date = datetime.now().strftime("%Y%m%d")
    p = config.OUTPUTS_DIR / sub / f"{_slug(nom)}_{date}.md"
    p.write_text(contenu, encoding="utf-8")
    print(f"  💾 {p}")
    return p


def register_convention(code: str, client: str, scenario: str = "", garantie: str = "",
                        statut: str = "Prospection", date_signature: str = "", notes: str = "") -> str:
    """Ajoute ou met à jour une ligne de data/conventions_signees.csv (suivi dashboard).

    Retourne "created" ou "updated". Ponytail: lecture+écriture complète du CSV, sans verrou —
    à passer en SQLite si des écritures concurrentes apparaissent.
    """
    CSV_SIGNEES.parent.mkdir(exist_ok=True)
    rows: list[dict] = []
    if CSV_SIGNEES.exists():
        with open(CSV_SIGNEES, encoding="utf-8") as f:
            rows = list(_csv.DictReader(f, delimiter=";"))
    for r in rows:
        if str(r.get("code", "")).strip().lower() == code.strip().lower():
            for k, v in (("client", client), ("scenario", scenario), ("garantie", garantie),
                         ("statut", statut), ("date_signature", date_signature), ("notes", notes)):
                if v:
                    r[k] = v
            r["nb_modifications"] = str(int(r.get("nb_modifications") or 0) + 1)
            break
    else:
        rows.append({"code": re.sub(r"[^A-Z0-9_]", "_", code.strip().upper())[:20],
                     "client": client, "scenario": scenario, "garantie": garantie,
                     "statut": statut, "date_debut_prospection": date.today().isoformat(),
                     "date_signature": date_signature, "nb_modifications": "0", "notes": notes})
        with open(CSV_SIGNEES, "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=CSV_FIELDS, delimiter=";")
            w.writeheader()
            w.writerows(rows)
        return "created"
    with open(CSV_SIGNEES, "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=CSV_FIELDS, delimiter=";")
        w.writeheader()
        w.writerows(rows)
    return "updated"


def _bilan_csv(chemin: str) -> dict | None:
    """Retrouve la ligne conventions_signees.csv correspondant au fichier (bilan auto).

    Matching par tokens (≥3 lettres) entre nom du fichier et client/code,
    bonus si le code exact figure dans le nom. Ponytail: heuristique simple —
    un match sur 2+ tokens ou le code; en dessous, pas de bilan (aucun faux positif).
    """
    if not CSV_SIGNEES.exists():
        return None
    stem = re.sub(r"[^a-z0-9]+", " ", Path(chemin).stem.lower())
    stem_tokens = {t for t in stem.split() if len(t) >= 3}
    if not stem_tokens:
        return None
    with open(CSV_SIGNEES, encoding="utf-8") as f:
        rows = list(_csv.DictReader(f, delimiter=";"))
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
    """CA N / N-1 par convention via le pipeline du dashboard (dégradation silencieuse).

    Matching par tokens (≥3 lettres, ≥2 tokens communs) — même heuristique que _bilan_csv.
    """
    try:
        sys.path.insert(0, str(ROOT_REPO))
        import pandas as pd
        from data.loader import _filter_conventions, load_all_data
        from data.transforms import _add_date_cols, _map_magasins
        raw = load_all_data()
        df_vc = _filter_conventions(
            _map_magasins(_add_date_cols(raw.get("vc", pd.DataFrame())),
                          raw.get("code_magasin", pd.DataFrame())))
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
    decision = agents.synthese_comex(
        f"Renouvellement de : {nom}\n\nBilan : {bilan}\n\nAudit :\n{audit}\n\nContre-audit :\n{contre or '(non généré)'}")
    if decision:
        _save("syntheses", f"decision_renouvellement_{nom}", decision)

    print("\n✅ Terminé. Résultats dans OUTPUTS/.")
