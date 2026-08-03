"""
intent_planner.py — Intent Planner pour Project Brain.

Traduit une question vague en un plan de retrieval structuré.
Chaque étape du plan est exécutable par le Context Builder.

Usage:
    planner = IntentPlanner()
    plan = planner.plan("comment fonctionne authentification ?")
    # → [{"tool": "find", "args": ["authentification"]},
    #     {"tool": "calls", "args": ["authentification"]}]
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RetrievalStep:
    """Une étape atomique du plan de retrieval."""
    tool: str          # find | calls | deps | module | query | symbol
    args: list[str]    # arguments de l'outil
    label: str = ""    # description lisible (optionnelle)


@dataclass
class RetrievalPlan:
    """Plan complet généré par l'Intent Planner."""
    query: str
    steps: list[RetrievalStep] = field(default_factory=list)
    confidence: float = 1.0  # 0.0 → 1.0

    def __bool__(self):
        return len(self.steps) > 0


# ── Stop words à ignorer dans le symbole ───────────────
_STOP = frozenset({
    "de", "du", "des", "le", "la", "les", "un", "une",
    "the", "a", "an", "of", "in", "to", "for", "with",
    "est", "et", "que", "qui", "quoi", "dans", "sur",
    "ce", "cette", "ces", "mon", "ma", "mes", "ton", "ta",
})


def _extract_symbol(text: str) -> Optional[str]:
    """Extrait le symbole probable d'une question.

    Stratégie, par priorité :
    1. Un token contenant '/' (chemin fichier)
    2. Un token contenant '.' (module.symbole)
    3. Un token CamelCase (ClassName)
    4. Le dernier token non-stop-word
    """
    # Nettoyer la ponctuation de fin
    text = text.strip().rstrip("?.!")

    tokens = text.split()

    # 1. Chemin fichier
    for t in reversed(tokens):
        if "/" in t:
            return t

    # 2. Module.symbole
    for t in reversed(tokens):
        if "." in t:
            return t

    # 3. CamelCase
    for t in reversed(tokens):
        if t[0].isupper() if t else False:
            return t

    # 4. Contient underscore (snake_case probable)
    for t in reversed(tokens):
        if "_" in t:
            return t

    # 5. Dernier token non-stop-word
    for t in reversed(tokens):
        clean = t.strip(",;:()'\"")
        if clean and clean.lower() not in _STOP and len(clean) > 1:
            return clean

    # 6. Dernier token
    return tokens[-1] if tokens else None


# ── Règles : (pattern_regex, [outils], description) ─────
# Le symbole est extrait via _extract_symbol à la fin,
# pas depuis un groupe de capture dans la regex.

_RULES = [
    # ── "how does X work?" / "comment fonctionne X ?" ───
    (r"(?:how\s+does|comment\s+fonctionne|comment\s+marche)",
     ["symbol", "calls"],
     "Symbole + graphe d'appels"),

    (r"(\w[\w.]*)\s+(?:fonctionne|marche|work)",
     ["symbol", "calls"],
     "Symbole + graphe d'appels"),

    # ── "what calls / uses X ?" ──────────────────────────
    (r"(?:what|qui)\s+(?:calls|appelle|utilise|invoke|uses)",
     ["calls"],
     "Callers d'un symbole"),

    # ── "what does X depend on?" ─────────────────────────
    (r"(?:what|de\s+quoi)\s+(?:does|est-ce)\s+[\w./]+\s+(?:depend|dépend|import|utilise)",
     ["deps"],
     "Dépendances d'un module"),

    # ── "where is X?" ────────────────────────────────────
    (r"(?:where|où)\s+(?:is|se\s+trouve|est)\s+(?:\w+\s+)*(?:\w+\s+)?([\w./]+)",
     ["find"],
     "Localiser un symbole"),

    # ── "find / cherche X" ───────────────────────────────
    (r"(?:find|trouve|cherche|recherche)\s+(\w[\w/.]*)",
     ["find"],
     "Rechercher un symbole"),

    # ── "explain / explain architecture" ─────────────────
    (r"(?:explain|explique|décris|describe)\s+(?:the\s+|l['a'])?(?:architecture\s+)?",
     ["module", "deps", "calls"],
     "Vue complète d'un module"),

    (r"(?:architecture|structure)\s+(?:de|l['a']|du|d['u'])",
     ["module", "deps"],
     "Architecture d'un module"),

    # ── "what is X?" ─────────────────────────────────────
    (r"(?:what|qu'est-ce)\s+(?:is|c'est)\s+(\w[\w.]*)",
     ["symbol", "module"],
     "Définition + module"),

    # ── "show me X" ──────────────────────────────────────
    (r"(?:show|montre|affiche)\s+(?:me|moi)?\s*(\w[\w./]*)",
     ["symbol", "module"],
     "Afficher un symbole et son module"),

    # ── "de quoi dépend X ?" / "quelles sont les dépendances de X ?" ──
    (r"(?:de\s+quoi|quels?|quelles?)\s+(?:dépend|depend|sont\s+les\s+dépendances?|sont\s+les\s+dependances?)\s+(?:\w+\s+)*(?:\w+\s+)?(\w[\w./]*)",
     ["deps"],
     "Dépendances"),

    # ── "qu'est-ce que X importe ?" ──────────────────────
    (r"(?:qu'est-ce\s+que|what\s+does)\s+(\w[\w.]*)\s+(?:import|importe|utilise)",
     ["deps"],
     "Dépendances"),

    # ── Fallback ─────────────────────────────────────────
    (r".+", ["query"],
     "Recherche sémantique (fallback)"),
]


class IntentPlanner:
    """Analyse une question et produit un plan de retrieval."""

    def __init__(self, rules: Optional[list] = None):
        self.rules = rules or _RULES

    def plan(self, query: str) -> RetrievalPlan:
        q = query.strip()
        if not q:
            return RetrievalPlan(query=q, confidence=0.0)

        q_lower = q.lower()

        for pattern, tools, label in self.rules:
            m = re.search(pattern, q_lower)
            if m:
                # Extraire le symbole : groupe capture > _extract_symbol > None
                symbol = m.group(1) if m.lastgroup and len(m.groups()) >= 1 else _extract_symbol(q)

                if symbol is None:
                    return RetrievalPlan(query=q, confidence=0.0)

                steps = [RetrievalStep(tool=t, args=[symbol], label=f"{t}('{symbol}')")
                         for t in tools]
                return RetrievalPlan(query=q, steps=steps, confidence=0.9)

        return RetrievalPlan(query=q, confidence=0.0)

    def plan_debug(self, query: str) -> str:
        """Version lisible du plan pour debug."""
        plan = self.plan(query)
        if not plan:
            return f"[INTENT] Aucun plan trouvé pour : {query}"
        lines = [f"[INTENT] Query: {plan.query}  (confidence={plan.confidence})"]
        for i, step in enumerate(plan.steps, 1):
            lines.append(f"  {i}. {step.tool}({', '.join(step.args)})  # {step.label}")
        return "\n".join(lines)


import re  # noqa: E402 (import après définition des dataclasses)


if __name__ == "__main__":
    planner = IntentPlanner()
    tests = [
        "comment fonctionne index_file ?",
        "what calls authenticate ?",
        "où est définie la classe MemoryStore ?",
        "explique l'architecture de data/loader.py",
        "de quoi dépend le module auth ?",
        "what is RelationsStore ?",
        "comment marche le système d'import ?",
        "explique architecture memory_store.py",
        "trouve index_project",
        "show me RelationsStore",
        "what are the dependencies of code_indexer ?",
    ]
    for t in tests:
        print(planner.plan_debug(t))
        print()
