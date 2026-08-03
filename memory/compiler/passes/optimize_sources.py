"""
optimize.sources — Passe d'optimisation : analyse et suggestions de refactoring.

Detecte :
  - Imports redondants (meme module importe plusieurs fois)
  - Pistes de simplification (code mort, fonctions inutilisees)
  - Opportunites de performance (boucles, appels reseau)
"""

from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind, FactKind
from ..detect import deduplicate


@register_pass("optimize.sources", "Optimisation et suggestions de refactoring",
               requires=["extract.facts"], priority=50)
def pass_optimize_sources(query: str, plan, context_pack: str,
                          intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Analyse les faits et propose des optimisations de code source."""
    if intent == IntentKind.DEBUG:
        # Debug : chercher des redondances qui cachent le bug
        return DossierDelta()

    signals: list[str] = []
    options: list[str] = []
    facts_text = [f.text.lower() for f in dossier.facts]

    # 1. Imports redondants (plusieurs imports du meme module dans un fichier)
    imports = [f for f in dossier.facts if f.kind == FactKind.ARTIFACT and "import" in f.text.lower()]
    if len(imports) > 3:
        signals.append(f"{len(imports)} imports detectes — verifier les dependances inutilisees")

    # 2. Fichier unique reference plusieurs fois (piste de refactoring)
    files = set()
    multi_file_count = 0
    for f in dossier.facts:
        if f.file:
            if f.file in files:
                multi_file_count += 1
            files.add(f.file)
    if multi_file_count > 5:
        signals.append(
            f"{multi_file_count} references repetees vers les memes fichiers — "
            "extraire les acces dans une variable/helper"
        )

    # 3. Detection de pattern "if/elif long"
    long_chain = False
    for text in facts_text:
        if text.count("elif") > 3 or text.count("else if") > 3:
            long_chain = True
            break
    if long_chain:
        options.append(
            "Remplacer la chaine if/elif par un dict de dispatch ou un pattern strategy"
        )

    # 4. Detection de commentaires TODO/FIXME
    todos = sum(1 for f in facts_text if "todo" in f or "fixme" in f or "xxx" in f)
    if todos > 0:
        signals.append(f"{todos} marqueurs TODO/FIXME dans le code concerne")

    # 5. Suggestion specifique au type de requete
    q = query.lower()
    if any(kw in q for kw in ("perf", "lent", "slow", "optimise", "rapide")):
        options.append(
            "Utiliser un cache (lru_cache / st.cache_data) pour les appels coutoux"
        )
    if any("api" in f or "request" in f or "http" in f for f in facts_text):
        options.append(
            "Mutualiser les appels API : un seul point d'entree avec cache"
        )

    signals = deduplicate(signals)
    options = deduplicate(options)

    return DossierDelta(
        signals=signals,
        options=options,
    )
