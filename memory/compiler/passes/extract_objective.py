"""
extract.objective — Passe 1 : extraction et nettoyage de l'objectif.
"""

import re
from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind


@register_pass("extract.objective", "Extraction et nettoyage de l'objectif", priority=10)
def pass_extract_objective(query: str, plan, context_pack: str,
                           intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Extrait l'objectif depuis la requete utilisateur."""
    if not query:
        return DossierDelta()

    obj = query.strip().rstrip("?!.")

    patterns = [
        (r"^comment\s+fonctionne\s+(.+)", 1),
        (r"^comment\s+marche\s+(.+)", 1),
        (r"^how\s+does\s+(.+?)\s+work\s*$", 1),
        (r"^(?:comment\s+|how\s+does\s+|how\s+to\s+)(.+)", 1),
        (r"^(?:what\s+is\s+|qu'est-ce\s+que\s+|c'est\s+quoi\s+)(.+)", 1),
        (r"^(?:explique\s+(?:moi\s+)?|explain\s+)(.+)", 1),
        (r"^(?:trouve\s+|cherche\s+|find\s+)(.+)", 1),
        (r"^(?:montre\s+(?:moi\s+)?|show\s+(?:me\s+)?)(.+)", 1),
        (r"^(?:ou\s+(?:est|se\s+trouve)\s+)(.+)", 1),
        (r"^(?:pourquoi\s+|why\s+does\s+)(.+)", 1),
        (r"^(?:de\s+quoi\s+depend\s+)(.+)", 1),
    ]

    for pat, g in patterns:
        m = re.search(pat, obj, re.IGNORECASE)
        if m:
            core = m.group(g).strip().rstrip("?!")
            if core:
                return DossierDelta(objective=f"Comprendre {core}")

    if obj and not obj[0].isupper():
        obj = obj[0].upper() + obj[1:]
    return DossierDelta(objective=obj)
