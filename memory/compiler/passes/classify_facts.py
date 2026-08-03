"""
classify.facts — Passe fondatrice : classifie chaque fait selon trois dimensions.

Chaque fait reçoit :
  - importance  : valeur intrinseque du fait (0.0-1.0)
  - utility     : utilite pour la question courante (0.0-1.0)
  - category    : critical | important | context | secondary
  - tags        : mots-cles semantiques (security, auth, dataflow, ...)
"""

import re
from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind, Fact, FactKind


# Mots-cles qui augmentent l'importance intrinseque
_IMPORTANCE_BOOST = {
    "security": 0.3, "auth": 0.25, "token": 0.25, "password": 0.3,
    "encrypt": 0.3, "https": 0.2, "ssl": 0.25, "certif": 0.25,
    "sql": 0.2, "injection": 0.3, "validation": 0.2,
    "crash": 0.3, "exception": 0.2, "error": 0.15, "fail": 0.2,
    "deadlock": 0.3, "race": 0.3, "timeout": 0.2,
    "migration": 0.25, "schema": 0.2, "index": 0.15,
    "api": 0.2, "endpoint": 0.2, "route": 0.15,
    "paiement": 0.3, "payment": 0.3, "stripe": 0.3,
    "transaction": 0.25, "atomic": 0.2,
}

# Tags semantiques par mot-cle
_TAG_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(auth|login|logout|password|token|jwt|session|cookie)", re.I), "auth"),
    (re.compile(r"(security|injection|xss|csrf|cors|https|certif)", re.I), "security"),
    (re.compile(r"(call|appelle|invoke|appel|appelle|.def |.function)", re.I), "call_chain"),
    (re.compile(r"(import|module|dependency|from |require)", re.I), "dependency"),
    (re.compile(r"(class|inherits|extends|subclass|parent)", re.I), "inheritance"),
    (re.compile(r"(api|endpoint|route|http|request|response)", re.I), "api"),
    (re.compile(r"(sql|db|database|query|select|insert|update)", re.I), "database"),
    (re.compile(r"(test|unittest|pytest|assert|spec)", re.I), "testing"),
    (re.compile(r"(config|setting|env|variable d. environ)", re.I), "config"),
    (re.compile(r"(error|exception|fail|crash|bug)", re.I), "error"),
    (re.compile(r"(perf|perform|optimis|lent|slow|latenc)", re.I), "performance"),
    (re.compile(r"(ui|ux|render|affich|component|streamlit)", re.I), "ui"),
    (re.compile(r"(data|metric|kpi|score|tnd|ca |chiffre)", re.I), "data"),
    (re.compile(r"(plan|future|roadmap|todo|next|prochai)", re.I), "planning"),
]


def _classify_fact(fact: Fact, query: str) -> tuple[float, float, str, list[str]]:
    """Calcule (importance, utility, category, tags) pour un fait."""
    text_lower = fact.text.lower()
    q_lower = query.lower()

    # --- Importance (valeur intrinseque) ---
    importance = 0.5  # defaut

    # Un fait artefact (fichier) a une importance de base plus faible
    if fact.kind == FactKind.ARTIFACT:
        importance = 0.4
    # Un fait metric (KPI) est plus important
    elif fact.kind == FactKind.METRIC:
        importance = 0.6
    # Un fait signal (alerte) est important
    elif fact.kind == FactKind.SIGNAL:
        importance = 0.7

    # Boost par mots-cles semantiques
    for kw, boost in _IMPORTANCE_BOOST.items():
        if kw in text_lower:
            importance = min(1.0, importance + boost * 0.5)

    # Symbole mentionne dans la question = plus important
    if fact.symbol and fact.symbol.lower() in q_lower:
        importance = min(1.0, importance + 0.3)

    # --- Utility (utilite pour la question courante) ---
    utility = 0.3  # defaut bas

    # Chevauchement lexical entre le fait et la question
    q_words = set(re.findall(r'\w+', q_lower))
    f_words = set(re.findall(r'\w+', text_lower))
    common = q_words & f_words
    if q_words:
        overlap = len(common) / len(q_words)
        utility = min(1.0, 0.3 + overlap * 0.7)

    # Si le symbole du fait est directement mentionne
    if fact.symbol and fact.symbol.lower() in q_lower:
        utility = max(utility, 0.8)

    # Si le fait mentionne un fichier de la question
    if fact.file and fact.file.lower() in q_lower:
        utility = max(utility, 0.7)

    # --- Category ---
    combined = (importance + utility) / 2
    if combined >= 0.75:
        category = "critical"
    elif combined >= 0.55:
        category = "important"
    elif combined >= 0.35:
        category = "context"
    else:
        category = "secondary"

    # Override : signaux et erreurs toujours au moins "important"
    if fact.kind == FactKind.SIGNAL and category == "secondary":
        category = "context"
    if "error" in text_lower and category == "secondary":
        category = "context"

    # --- Tags ---
    tags: list[str] = []
    for pattern, tag in _TAG_MAP:
        if pattern.search(text_lower):
            if tag not in tags:
                tags.append(tag)

    # Toujours ajouter kind comme tag
    tags.append(fact.kind.value)

    return round(importance, 4), round(utility, 4), category, tags


@register_pass("classify.facts", "Classification des faits : importance, utility, category, tags",
               requires=["extract.facts"], priority=43)
def pass_classify_facts(query: str, plan, context_pack: str,
                        intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Classe chaque fait du dossier selon 3 dimensions.

    Cette passe est fondatrice : toutes les passes d'optimisation
    (prune, chain, prioritize) dependent de ces metadonnees.
    """
    if not dossier.facts:
        return DossierDelta()

    for fact in dossier.facts:
        imp, util, cat, tags = _classify_fact(fact, query)
        fact.importance = imp
        fact.utility = util
        fact.category = cat
        fact.tags = tags

    return DossierDelta()
