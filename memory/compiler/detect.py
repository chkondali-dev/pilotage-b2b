"""
detect.py — Detection d'intention a partir de la requete utilisateur.

Regles par priorite :
  1. DEBUG : mots-cles de bug/erreur
  2. REFACTOR : refactor/amelioration/simplification
  3. ARCH : architecture/design/structure
  4. EXPLORE : questions commencant par comment/how/what/where...
  5. Fallback : GENERAL
"""

from typing import Optional
from .types import IntentKind, Fact


_DEBUG_KEYWORDS = frozenset({
    "bug", "bugue", "error", "erreur", "fail", "failed",
    "broken", "casse", "marche pas", "ne marche",
    "echoue", "echoue", "plante", "crash", "plante",
    "exception", "regress", "regress", "fix", "corrig",
    "problem", "probleme", "issue", "incident", "dysfonction",
    "expire", "expire", "expiration", "invalide", "invalid",
})


def is_debug_query(query: str) -> bool:
    q = query.lower()
    if "ne marche" in q or "marche pas" in q:
        return True
    return any(kw in q for kw in _DEBUG_KEYWORDS)


def extract_symbol(query: str) -> Optional[str]:
    """Extraction simple du symbole depuis une requete."""
    q = query.strip().rstrip("?!.")
    for token in reversed(q.split()):
        clean = token.strip(",;:()'\"")
        if clean and clean[0].isupper():
            return clean
        if "_" in clean:
            return clean
        if "." in clean and not clean.startswith("http"):
            return clean
    return None


def deduplicate(items: list, key_fn=lambda x: x) -> list:
    """Deduplique une liste en conservant l'ordre."""
    seen = set()
    result = []
    for item in items:
        k = key_fn(item)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def parse_context_pack(context_pack: str) -> list:
    """Parse un Context Pack en liste de Facts."""
    from .types import Fact, FactKind
    facts: list[Fact] = []
    current_section = ""

    for line in context_pack.split("\n"):
        raw = line.rstrip("\n")
        m = __import__("re").match(r"\s*==\s*(.+?)\s*==", raw)
        if m:
            current_section = m.group(1).strip()
            facts.append(Fact(
                text=f"[Section] {current_section}",
                kind=FactKind.ARTIFACT,
                source=current_section,
            ))
            continue

        stripped = raw.strip()
        if not stripped:
            continue

        if (stripped.startswith(".--") or stripped.startswith("'--")
            or stripped.startswith("Query:") or stripped.startswith("Steps:")
            or stripped == "."):
            continue

        cleaned = __import__("re").sub(r"\s+", " ", stripped)
        if len(cleaned) <= 3:
            continue

        import re
        file_match = re.search(r"[\w./\\-]+\.py", cleaned)
        filepath = file_match.group(0) if file_match else None

        symbol = None
        sym_match = re.match(r"^\s*\[?(\w+)\]?\s", cleaned)
        if sym_match:
            sym = sym_match.group(1)
            if sym not in ("function", "class", "constant", "import", "Section",
                          "Called", "Calls", "line", "File"):
                symbol = sym

        kind = FactKind.STATEMENT
        if filepath and ("/" in filepath or "\\" in filepath):
            kind = FactKind.ARTIFACT
        if any(kw in cleaned.lower() for kw in ("score", "tnd", "%", "ca ", "kpi")):
            kind = FactKind.METRIC
        if any(kw in cleaned.lower() for kw in ("warning", "suspect", "anomal", "alert")):
            kind = FactKind.SIGNAL

        facts.append(Fact(
            text=cleaned,
            kind=kind,
            confidence=1.0,
            source=f"Context Pack :: {current_section}" if current_section else "Context Pack",
            symbol=symbol,
            file=filepath,
        ))

    return facts


def extract_files(facts: list) -> list[str]:
    """Liste les fichiers uniques references dans les faits."""
    import re
    files = set()
    for f in facts:
        if f.file:
            files.add(f.file)
        for m in re.findall(r"[\w./\\-]+\.py", f.text):
            if "/" in m or "\\" in m:
                files.add(m)
    return sorted(files)


def detect_intent(query: str, plan=None,
                  facts: Optional[list] = None) -> IntentKind:
    """Detecte le type d'intent depuis la requete et le contexte."""
    if not query:
        return IntentKind.GENERAL

    q = query.lower()

    if is_debug_query(q):
        return IntentKind.DEBUG

    if any(kw in q for kw in ("refactor", "amelior", "restructur", "simplif",
                               "reorganis", "clean", "nettoy", "modernise")):
        return IntentKind.REFACTOR

    if any(kw in q for kw in ("architecture", "design pattern", "structure",
                               "comment organiser", "quel choix", "trade-off",
                               "compar", "vs ", "versus")):
        return IntentKind.ARCH

    starter = q.split()[0] if q.split() else ""
    if starter in ("comment", "how", "what", "where", "que", "qui", "ou",
                   "qu'est", "c'est", "explique", "explain", "montre", "show",
                   "trouve", "find", "cherche", "affiche"):
        return IntentKind.EXPLORE

    return IntentKind.GENERAL
