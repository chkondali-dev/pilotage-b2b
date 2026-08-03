"""
brain.py — Pipeline de raisonnement en couches (roadmap A → D).

    Utilisateur → Intent Planner → Context Builder → Brain Query (+ Ollama optionnel)
               → ReasoningDossier (structurer_pack, déterministe)     [Phase A]
               → ContextCoverage (coverage, calculé par le système)   [Phase B]
               → DeepSeek (raisonnement + ModelAssessment JSON)       [Phase C]
               → Decision Renderer (--mode) + journal de raisonnement [Phase C/D]

Deux contrats DISTINCTS, jamais fusionnés (principe : le système ne mesure pas la
vérité, il mesure ce qu'il possède / manque / exploite) :
  - ContextCoverage : état du contexte — objectif, mesurable, calculé par le système.
  - ModelAssessment : appréciation du modèle — subjective, déclarée par DeepSeek.

Usage :
    python main.py brain "demande" [--mode expert|dg|technique|commercial|audit]
"""

import json
import re
import time
from datetime import datetime

from llm import client, config
from llm.reasoning import (Constraint, Fact, ReasoningDossier,
                           _PATTERNS_TROUS, _sans_accents)
from llm.store import MemoryStore

# ── Intent Planner (déterministe, sans LLM) ───────────────────────

_INTENTIONS = [
    # (nom, pattern regex, poids) — les questions factuelles (poids 2, premières)
    # l'emportent sur un mot du domaine isolé ; « que » seul n'est pas interrogatif.
    ("question",       r"\bquel\w*\b|\bquoi\b|\bcomment\b|\bpourquoi\b|\bcombien\b|est-?ce\b|\bquand\b|\bqui\b", 2),
    ("renouvellement", r"renouvel|recondu|échéance|echeance|arrivée? (à|a) terme|prolong", 1),
    ("negociation",    r"négoci|negoci|batna|contre-?offre|stratégie|strategie|marge", 1),
    ("defense",        r"\bdéfend\w*\b|\bdefend\w*\b|soutenance|plaide|verrouillage", 1),
    ("audit",          r"audit|clause|conformité|conformit|juridique|examine? la", 1),
    ("risque",         r"risque|grille|exposition|probabilité|probabilit", 1),
    ("comex",          r"comex|décision|decision|valide|rejette|approuve|tranche", 1),
    ("redaction",      r"rédige|redige|rédaction|redaction|écris|ecris|ébauche|ebauche|contrat type", 1),
    ("revue",          r"revue|contre-?audit|vérif|verif|compar", 1),
]

_FICHIER_RE = re.compile(r"([\w\-]+\.(?:md|docx|txt))", re.I)


def intent_planner(demande: str) -> tuple[str, str]:
    """Détecte l'intention dominante et la cible (fichier nommé, sinon '')."""
    low = demande.lower()
    scores = [(nom, poids * len(re.findall(pat, low))) for nom, pat, poids in _INTENTIONS]
    nom, score = max(scores, key=lambda x: x[1])
    intention = nom if score > 0 else "question"
    m = _FICHIER_RE.search(demande)
    return intention, (m.group(1) if m else "")


# ── Contrat métier : sources requises par intention ───────────────
# Principe d'architecture : aucun composant avant son contrat métier défini.
# Ce mapping est le contrat : chaque intention déclare ce qu'elle exige.
# docs = sources documentaires ; kpis = registre + indicateurs vente.

REQUIS_PAR_INTENTION: dict[str, dict] = {
    "renouvellement": {"docs": ("document", "politique_risque", "memoire", "framework"),
                       "kpis": ("registre", "kpis")},
    "audit":          {"docs": ("document", "faq", "conditions_generales", "memoire", "framework"),
                       "kpis": ()},
    "risque":         {"docs": ("document", "politique_risque", "faq", "memoire"),
                       "kpis": ()},
    "negociation":    {"docs": ("document", "memoire"),
                       "kpis": ("registre", "kpis")},
    "defense":        {"docs": ("politique_risque", "framework", "memoire"),
                       "kpis": ()},
    "comex":          {"docs": ("document", "politique_risque", "memoire"),
                       "kpis": ("registre", "kpis")},
    "redaction":      {"docs": ("document", "memoire", "framework"),
                       "kpis": ()},
    "revue":          {"docs": ("document", "politique_risque", "memoire"),
                       "kpis": ("registre", "kpis")},
    "question":       {"docs": ("memoire", "faq"),
                       "kpis": ()},
}

# Sources statiques KNOWLEDGE — état vérifié par le système
_FICHIERS_STATIQUES = {
    "faq": config.KNOWLEDGE_DIR / "reference" / "faq_conventions.md",
    "politique_risque": config.KNOWLEDGE_DIR / "procedures" / "politique_risque.md",
    "conditions_generales": config.KNOWLEDGE_DIR / "conventions" / "conditions_generales.md",
    "framework": config.KNOWLEDGE_DIR / "reference" / "framework_conventions_smg.md",
}


# ── Context Builder ───────────────────────────────────────────────

def _trouver_document(cible: str) -> str:
    """Cherche la cible (nom de fichier) sous ROOT (data, OUTPUTS, KNOWLEDGE…)."""
    if not cible:
        return ""
    for base in (config.ROOT / "data", config.OUTPUTS_DIR, config.KNOWLEDGE_DIR, config.ROOT):
        for f in base.rglob(cible):
            try:
                return f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
    return ""


def _etat_source(nom: str) -> str:
    """'ok' | 'coquille' | 'absent' pour une source statique KNOWLEDGE."""
    p = _FICHIERS_STATIQUES.get(nom)
    if p is None:
        return "ok"
    if not p.exists():
        return "absent"
    debut = p.read_text(encoding="utf-8", errors="ignore")[:200]
    if re.search(r"à rédiger|à déposer|à compléter|coquille|placeholder", debut, re.I):
        return "coquille"
    return "ok"


def context_builder(demande: str, intention: str, cible: str) -> dict:
    """Rassemble le contexte : document, registre, KPIs, mémoire, état des sources."""
    from workflows import _bilan_csv, _kpis_vente  # import local : éviter cycle

    ctx: dict = {"intention": intention, "demande": demande}

    doc = _trouver_document(cible)
    if doc:
        ctx["document"] = doc[:6000]

    if intention in ("renouvellement", "revue", "audit", "comex", "negociation"):
        ligne = _bilan_csv(cible) if cible else None
        if ligne:
            ctx["registre"] = " | ".join(f"{k}={v}" for k, v in ligne.items())
            kpis = _kpis_vente(ligne.get("client", ""))
            if kpis:
                ctx["kpis"] = kpis

    ctx["memoire"] = brain_query(demande)

    # État des sources requises (ok / coquille / absent) — pour ContextCoverage
    requis = REQUIS_PAR_INTENTION.get(intention, REQUIS_PAR_INTENTION["question"])
    ctx["etat_sources"] = {}
    for nom in requis["docs"]:
        if nom in ("document", "memoire"):
            ctx["etat_sources"][nom] = "ok" if ctx.get(nom) else "absent"
        else:
            ctx["etat_sources"][nom] = _etat_source(nom)
    for nom in requis["kpis"]:
        ctx["etat_sources"][nom] = "ok" if ctx.get(nom) else "absent"
    return ctx


# ── Brain Query (mémoire + Ollama optionnel) ─────────────────────

def brain_query(demande: str, top_k: int = 8) -> list[dict]:
    """Interroge la mémoire (store SQLite convention_ai).

    Ollama est optionnel ici : embeddings all-minilm s'il tourne,
    sinon repli mots-clés (déjà géré par MemoryStore.recall).

    Diversification : au plus 2 chunks par source documentaire — sinon un
    seul fichier (ex. politique_risque) accapare le contexte et les chunks
    du framework / dossier client n'arrivent jamais dans le top_k.
    """
    hits = MemoryStore("convention_ai").recall(demande, top_k=top_k * 3)
    par_source: dict[str, list[dict]] = {}
    for h in hits:
        par_source.setdefault(h.get("source", "?"), []).append(h)
    diversifies: list[dict] = []
    for hs in par_source.values():
        diversifies.extend(hs[:2])
    diversifies.sort(key=lambda h: h.get("score", 0), reverse=True)
    return diversifies[:top_k]


# ── Phase B : ContextCoverage (calculé par le système, objectif) ──

def coverage(ctx: dict) -> dict:
    """Mesure l'état du contexte : sources possédées / manquantes, KPIs, mémoire."""
    requis = REQUIS_PAR_INTENTION.get(ctx["intention"], REQUIS_PAR_INTENTION["question"])
    etats = ctx.get("etat_sources", {})

    manquants = [f"{nom} ({raison})" for nom, raison in sorted(etats.items())
                 if raison != "ok"]
    scores = [float(m.get("score", 0)) for m in ctx.get("memoire", [])]
    return {
        "intention": ctx["intention"],
        "required_sources": len(etats),
        "available_sources": sum(1 for r in etats.values() if r == "ok"),
        "required_kpis": len(requis["kpis"]),
        "available_kpis": sum(1 for k in requis["kpis"] if etats.get(k) == "ok"),
        "memory_chunks": len(ctx.get("memoire", [])),
        "average_relevance": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "missing": manquants,
    }


# ── Phase A : ReasoningDossier (structurer_pack, déterministe) ────

def structurer_pack(ctx: dict) -> ReasoningDossier:
    """Fabrique un dossier de faits sourcés depuis le contexte.

    Déterministe (aucun appel LLM) : les faits sont les chunks/registre/KPIs
    déjà sourcés ; les manques viennent des patterns de trous + sources requises
    indisponibles. Réutilise les types de llm/reasoning.py.
    """
    dossier = ReasoningDossier(objective=ctx["demande"])
    for m in ctx.get("memoire", []):
        dossier.facts.append(Fact(text=m.get("content", "")[:500], kind="contexte",
                                  confidence=float(m.get("score", 0.5)),
                                  source=m.get("source", "?")))
    if ctx.get("document"):
        dossier.facts.append(Fact(text=ctx["document"][:2000], kind="document",
                                  confidence=0.8, source="document concerné"))
        # Fait pivot : niveau de sûreté DÉCLARÉ par le dossier → risque
        # (politique de risque §2/§3). Déterministe — le modèle ne déduit plus
        # lui-même (deepseek-r1:7b a tendance à classer la cession en niveau 2
        # alors que le dossier dit niveau 1).
        m = re.search(r"niveau\s+(\d)", _sans_accents(ctx["document"]))
        if m:
            niveau = int(m.group(1))
            risque = {1: "faible", 2: "moyen", 3: "modéré", 4: "élevé"}.get(niveau)
            if risque:
                dossier.facts.append(Fact(
                    text=f"Niveau de sûreté déclaré par le dossier : {niveau} "
                         f"(politique de risque §2/§3) → risque {risque}.",
                    kind="regle", confidence=0.9,
                    source="document concerné (section garanties)"))
    if ctx.get("registre"):
        dossier.facts.append(Fact(text=ctx["registre"], kind="registre",
                                  confidence=0.9, source="registre CSV"))
    if ctx.get("kpis"):
        dossier.facts.append(Fact(text=ctx["kpis"], kind="kpi",
                                  confidence=0.9, source="KPIs vente"))

    vus: set[str] = set()
    for f in dossier.facts:
        if any(re.search(p, _sans_accents(f.text)) for p in _PATTERNS_TROUS):
            tronc = f.text[:200]
            if tronc not in vus:
                vus.add(tronc)
                dossier.missing.append(tronc)

    for src in coverage(ctx).get("missing", []):
        dossier.constraints.append(
            Constraint(text=f"Source requise indisponible : {src}", severity="warning"))
    return dossier


# ── Prompt de raisonnement (Phase C) ──────────────────────────────

_SYSTEM = (
    "Tu es le cerveau de raisonnement de convention-ai (SMG — conventions B2B "
    "MG/BATAM, cession sur salaire). On te fournit un dossier structuré : faits "
    "sourcés numérotés [F#], informations manquantes, contraintes, couverture. "
    "Raisonne EXCLUSIVEMENT sur ce dossier. Réponds en français, factuel. "
    "N'invente JAMAIS un chiffre, une clause ou une règle absente du dossier : "
    "toute information indisponible va dans assessment.unanswered."
)


def _prompt_raisonnement(ctx: dict, dossier: ReasoningDossier, cov: dict) -> str:
    """Assemble le paquet : dossier sourcé + coverage + consigne JSON stricte."""
    faits = "\n".join(f"[F{i}] ({f.source}) {f.text[:300]}"
                      for i, f in enumerate(dossier.facts, 1)) or "(aucun fait)"
    manques = "\n".join(f"- {m}" for m in dossier.missing) or "- aucun détecté"
    contraintes = "\n".join(f"- {c.text}" for c in dossier.constraints) or "- aucune"

    template_json = (
        '{"analyse": "… (cite les faits par [F#])", "verdict": "…", '
        '"recommandation": "…", "questions_ouvertes": ["…"], '
        '"assessment": {"confidence": 0-100, "rationale": ["…"], "unanswered": ["…"]}}'
    )
    return (
        f"INTENTION : {ctx['intention']}\n"
        f"DEMANDE : {ctx['demande']}\n\n"
        f"--- DOSSIER STRUCTURÉ ---\n{faits}\n\n"
        f"--- INFORMATIONS MANQUANTES ---\n{manques}\n\n"
        f"--- CONTRAINTES ---\n{contraintes}\n\n"
        f"--- COUVERTURE DU CONTEXTE (mesurée par le système) ---\n"
        f"{json.dumps(cov, ensure_ascii=False)}\n\n"
        "--- CONSIGNE ---\n"
        "Réponds UNIQUEMENT par un objet JSON valide, sans texte autour, au format :\n"
        f"{template_json}\n"
        "L'analyse cite les faits par leur numéro [F#]. Le verdict est une décision "
        "claire (🟢/🟠/🔴 + phrase). assessment.confidence = ton niveau de confiance "
        "déclaré (auto-évaluation, pas une mesure). assessment.unanswered = ce qui "
        "manque pour être certain (y compris les sources du coverage manquantes)."
    )


def _reparer_analyse(texte: str) -> str:
    """deepseek-r1:7b sort parfois « analyse » comme un tableau de lignes NON
    quotées (JSON invalide : `"analyse": [ [F1] texte ... ]`). On quote chaque
    ligne pour rendre l'objet parsable. Ne touche à rien si rien à réparer."""
    m = re.search(r'"analyse"\s*:\s*\[', texte)
    if not m:
        return texte
    start = m.end()
    fin_m = re.search(r'\]\s*,\s*"', texte[start:])
    if not fin_m:
        return texte
    corps = texte[start:start + fin_m.start()]
    lignes = [l.strip().rstrip(",") for l in corps.split("\n") if l.strip()]
    if not lignes or all(l.startswith('"') for l in lignes):
        return texte
    quotees = []
    for l in lignes:
        if l.startswith('"') and l.endswith('"'):
            quotees.append(l)
        else:
            quotees.append('"' + l.replace("\\", "\\\\").replace('"', '\\"') + '"')
    return texte[:start] + ", ".join(quotees) + texte[start + fin_m.start():]


def _parse_json(texte: str | None) -> dict | None:
    """Extrait le premier objet JSON de la réponse du modèle (tolérant)."""
    if not texte:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texte, re.S)
    cible = m.group(1) if m else texte
    m = re.search(r"\{.*\}", cible, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        # deepseek-r1:7b : analyse sort parfois en tableau non quoté → réparer
        repare = _reparer_analyse(m.group(0))
        try:
            return json.loads(repare)
        except Exception:
            return None


# ── Phase C/D : Decision Renderer (même raisonnement, rendus variés) ─

def render(data: dict | None, dossier: ReasoningDossier, cov: dict,
           mode: str = "expert") -> str:
    """Formate la réponse du modèle selon le mode — sans second appel LLM.

    Le raisonnement (data) est identique ; seul le rendu change.
    """
    if not data:
        return "⚠️ Le modèle n'a pas produit de JSON structuré. Voir le journal."

    analyse = data.get("analyse") or ""
    verdict = data.get("verdict") or ""
    reco = data.get("recommandation") or ""
    questions = data.get("questions_ouvertes") or []
    ass = data.get("assessment") or {}
    conf = ass.get("confidence")
    unanswered = ass.get("unanswered") or []

    # Résolution des preuves : [F#] → source → document (Evidence renderer)
    def sources_de(texte: str) -> str:
        cites = sorted({int(n) for n in re.findall(r"\[F(\d+)\]", texte)})
        lignes = []
        for n in cites:
            if 1 <= n <= len(dossier.facts):
                f = dossier.facts[n - 1]
                lignes.append(f"- [F{n}] **{f.source or '?'}** — {f.text[:120]}")
        return "\n".join(lignes) if lignes else "- aucune citation"

    def sec(titre: str, corps: str) -> str:
        return f"## {titre}\n\n{corps}" if corps.strip() else ""

    cov_txt = (f"Sources **{cov['available_sources']}/{cov['required_sources']}**"
               f" · KPIs **{cov['available_kpis']}/{cov['required_kpis']}**"
               f" · mémoire {cov['memory_chunks']} chunks"
               f" (pertinence moy. {cov['average_relevance']})"
               + (f" · manque : {', '.join(cov['missing'])}" if cov["missing"] else ""))
    ass_txt = (f"Confiance déclarée : **{conf}%**"
               + (f"\nJustification : {', '.join(ass.get('rationale') or [])}")
               + (f"\nNon répondu : {', '.join(unanswered)}" if unanswered else ""))

    if mode == "dg":
        return "\n\n".join(filter(None, [
            "# Synthèse exécutive",
            f"**Situation :** {analyse[:400]}",
            f"**Décision :** {verdict}",
            f"**Recommandation :** {reco}",
            f"**Couverture :** {cov_txt}",
            sec("Confiance du modèle", ass_txt),
        ]))
    if mode == "technique":
        return "\n\n".join(filter(None, [
            "# Dossier technique",
            sec("Analyse", analyse),
            sec("Preuves résolues ([F#] → source)", sources_de(analyse)),
            sec("Recommandation", reco),
            sec("Couverture du contexte", cov_txt),
        ]))
    if mode == "commercial":
        return "\n\n".join(filter(None, [
            "# Argumentaire commercial",
            sec("Position", analyse),
            sec("À mettre en avant", reco),
            f"**Verdict interne :** {verdict}",
            sec("Points de vigilance", "\n".join(f"- {u}" for u in unanswered)),
        ]))
    if mode == "audit":
        return "\n\n".join(filter(None, [
            "# Rapport d'audit",
            sec("Verdict", verdict),
            sec("Analyse", analyse),
            sec("Manques documentaires", "\n".join(f"- {m}" for m in cov["missing"])),
            sec("Questions ouvertes", "\n".join(f"- {q}" for q in questions)),
            sec("Couverture", cov_txt),
            sec("Évaluation du modèle", ass_txt),
        ]))
    # expert (défaut)
    return "\n\n".join(filter(None, [
        "# Raisonnement",
        f"**Intention :** {cov['intention']}",
        sec("Analyse", analyse),
        sec("Preuves ([F#] → source → document)", sources_de(analyse)),
        sec("Verdict", verdict),
        sec("Recommandation", reco),
        sec("Questions ouvertes", "\n".join(f"- {q}" for q in questions)),
        sec("Couverture du contexte (mesurée par le système)", cov_txt),
        sec("Évaluation du modèle (déclarée par DeepSeek)", ass_txt),
    ]))


# ── Phase D : journal de raisonnement ─────────────────────────────

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def journaliser(rec: dict) -> str:
    """Archive le journal de raisonnement (JSON) dans OUTPUTS/rapports/."""
    p = (config.OUTPUTS_DIR / "rapports"
         / f"raisonnement_{_slug(rec.get('intention', 'brain'))}_"
           f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


# ── Pipeline complet ──────────────────────────────────────────────

def raisonner(demande: str, mode: str = "expert") -> str | None:
    """Intent → contexte → dossier → coverage → DeepSeek → rendu → journal."""
    t0 = time.perf_counter()
    intention, cible = intent_planner(demande)
    ctx = context_builder(demande, intention, cible)
    dossier = structurer_pack(ctx)
    cov = coverage(ctx)

    print(f"[brain] intention={intention} cible={cible or '-'} "
          f"couverture={cov['available_sources']}/{cov['required_sources']} "
          f"({len(dossier.facts)} faits, {len(dossier.missing)} manques)")

    texte, meta = client.chat(_prompt_raisonnement(ctx, dossier, cov),
                              role="brain", system=_SYSTEM, meta=True) or (None, {})
    data = _parse_json(texte)
    if data is None and texte:
        # retry : deepseek-r1 sort parfois de la structure JSON demandée
        texte2, meta2 = client.chat(
            _prompt_raisonnement(ctx, dossier, cov) + "\nTa réponse précédente n'était pas "
            "un JSON valide. Réponds UNIQUEMENT par l'objet JSON au format demandé, sans "
            "aucun texte autour.", role="brain", system=_SYSTEM, meta=True) or (None, {})
        if texte2:
            texte, meta = texte2, meta2 or meta
        data = _parse_json(texte)
    rendu = render(data, dossier, cov, mode)

    journaliser({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "demande": demande,
        "intention": intention,
        "cible": cible,
        "mode": mode,
        "duree_s": round(time.perf_counter() - t0, 1),
        "modele": (meta or {}).get("modele"),
        "provider": (meta or {}).get("provider"),
        "tokens": (meta or {}).get("usage"),
        "sources_utilisees": [f.source for f in dossier.facts if f.source],
        "sources_ignorees": cov["missing"],
        "contraintes": [c.text for c in dossier.constraints],
        "inconnues": dossier.missing,
        "coverage": cov,
        "assessment": (data or {}).get("assessment"),
        "reponse": (data or {}).get("analyse") or (texte or ""),
    })
    return rendu


if __name__ == "__main__":
    # Self-check : l'intention est détectée sans appel LLM (rapide, déterministe).
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for ex, attendu in [
        ("Renouvellement de la convention Amicale Personnel CNAM — que décider ?",
         "renouvellement"),
        ("Audite la convention_mutuelle_2025.md clause par clause", "audit"),
        ("Quel est le plafond d'exposition BATAM ?", "question"),
        ("Rédige une ébauche de convention de crédit pour MJ", "redaction"),
        ("Défends le dossier de convention scénario 06 (Groupe multi-sociétés) avant verrouillage",
         "defense"),
    ]:
        it, cb = intent_planner(ex)
        print(f"  {it:<15} (cible={cb or '-'})  ← {ex[:60]}")
        assert it == attendu, f"{ex} → {it} (attendu {attendu})"
    # fait pivot : niveau de sûreté déclaré injecté (déterministe, sans LLM)
    d = structurer_pack({
        "demande": "Défends le dossier meditech.md",
        "intention": "defense",
        "document": "Garanties : cession sur salaire + caution solidaire — niveau 1 de sûretés (sécurité maximale).",
        "memoire": [], "etat_sources": {},
    })
    pivots = [f.text for f in d.facts if f.kind == "regle" and "Niveau de sûreté" in f.text]
    assert pivots and "risque faible" in pivots[0], pivots
    print("  structurer_pack → fait pivot « niveau 1 → risque faible » : OK")
    print("Self-check OK")
