"""
detect.missing — Identifie ce que le dossier ignore.

Analyse les faits, la question, et ajoute des signaux sur les lacunes
de connaissance. Cela permet au LLM d'eviter les conclusions hatives
en connaissant ses angles morts.

Exemple :
  Question: "comment securiser login ?"
  Faits: [login, authenticate, JWT]
  Missing: [? generation token, ? configuration JWT, ? middleware]
  →
  Signal: 'Information manquante : configuration JWT non trouvee'
"""

import re
from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind

# Domaines de connaissance avec leurs mots-cles associes
_KNOWLEDGE_DOMAINS: dict[str, dict] = {
    "authentication": {
        "keywords": {"auth", "login", "authenticate", "password", "credential"},
        "expected_topics": [
            "generation token", "configuration JWT", "expiration",
            "refresh token", "middleware auth", "hash password",
        ],
    },
    "security": {
        "keywords": {"security", "xss", "csrf", "injection", "https", "cors"},
        "expected_topics": [
            "validation entree", "sanitization", "rate limiting",
            "gestion erreurs", "logging securite",
        ],
    },
    "api": {
        "keywords": {"api", "endpoint", "route", "rest", "http"},
        "expected_topics": [
            "gestion erreurs API", "versioning", "documentation",
            "pagination", "validation payload",
        ],
    },
    "database": {
        "keywords": {"sql", "db", "database", "query", "schema", "migration"},
        "expected_topics": [
            "migration schema", "index", "transaction", "backup",
            "connexion pool", "orm mapping",
        ],
    },
    "testing": {
        "keywords": {"test", "unittest", "pytest", "spec", "qa"},
        "expected_topics": [
            "tests unitaires", "tests integration", "coverage",
            "mocking", "fixtures",
        ],
    },
    "deployment": {
        "keywords": {"deploy", "docker", "ci", "cd", "pipeline", "env"},
        "expected_topics": [
            "configuration env", "variables environnement",
            "healthcheck", "monitoring", "backup strategy",
        ],
    },
}


def _detect_domains(query: str, fact_texts: list[str]) -> list[str]:
    """Detecte les domaines de connaissance pertinents."""
    q_lower = query.lower()
    all_text = q_lower + " " + " ".join(fact_texts).lower()
    domains: list[str] = []
    for domain, info in _KNOWLEDGE_DOMAINS.items():
        if any(kw in all_text for kw in info["keywords"]):
            domains.append(domain)
    return domains


def _find_gaps(domain: str, fact_texts: list[str]) -> list[str]:
    """Trouve les sujets attendus non couverts dans les faits."""
    info = _KNOWLEDGE_DOMAINS.get(domain, {})
    gaps: list[str] = []
    for topic in info.get("expected_topics", []):
        # Verifier si le sujet est deja couvert
        topic_words = set(topic.lower().split())
        found = False
        for text in fact_texts:
            text_lower = text.lower()
            if topic in text_lower:
                found = True
                break
            # Check partiel : au moins 2 mots du sujet presents
            word_hits = sum(1 for w in topic_words if w in text_lower)
            if word_hits >= 2 and word_hits >= len(topic_words) * 0.5:
                found = True
                break
        if not found:
            gaps.append(topic)

    return gaps


@register_pass("detect.missing", "Detection des lacunes de connaissance",
               requires=["classify.facts"], priority=49)
def pass_detect_missing(query: str, plan, context_pack: str,
                        intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Analyse le dossier et signale les informations manquantes.

    Ne s'active que si la question a un intent specifique (pas GENERAL).
    Ajoute des signaux "gap" pour chaque lacune identifiee.
    """
    if intent == IntentKind.GENERAL or intent == IntentKind.REPORT:
        return DossierDelta()

    if not dossier.facts:
        return DossierDelta()

    fact_texts = [f.text for f in dossier.facts]

    # 1. Detecter les domaines pertinents
    domains = _detect_domains(query, fact_texts)
    if not domains:
        return DossierDelta()

    # 2. Trouver les lacunes
    gaps: list[str] = []
    for domain in domains:
        domain_gaps = _find_gaps(domain, fact_texts)
        for gap in domain_gaps:
            gaps.append(f"[{domain}] {gap}")

    if not gaps:
        return DossierDelta()

    # 3. Ajouter les gaps comme signaux
    signals = []
    signals.append(
        f"Information manquante detectee : {len(gaps)} lacune(s) "
        f"dans {len(domains)} domaine(s)"
    )
    for gap in gaps[:5]:  # max 5 gaps pour eviter le bruit
        signals.append(f"  ? {gap}")

    if len(gaps) > 5:
        signals.append(f"  ... et {len(gaps) - 5} autre(s)")

    return DossierDelta(signals=signals)
