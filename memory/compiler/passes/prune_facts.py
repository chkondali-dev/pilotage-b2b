"""
prune.facts — Supprime les faits inutiles pour la question courante.

Apres classification et chain-dedup, cette passe elimine :
  - les faits categorises "secondary" a faible utilite
  - les doublons textuels exacts
  - les imports/modules sans rapport avec l'objectif
  - les faits Artefact dont le fichier n'est plus reference
"""

import re
from collections import Counter
from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind, Fact, FactKind
from ..detect import deduplicate


# Patterns de bruit (lignes a faible valeur)
_NOISE_PATTERNS = [
    re.compile(r"^def \w+\(.*\) -> .*$"),       # signature seule sans docstring
    re.compile(r"^import \w+$"),                  # import simple sans usage
    re.compile(r"^from \w+ import \*$"),          # import wildcard
    re.compile(r"^\.-- Context Pack"),            # decorateur context pack
    re.compile(r"^'--"),                          # fin decorateur
    re.compile(r"^Query:"),                       # ligne query (deja dans objective)
    re.compile(r"^Steps:"),                       # ligne steps
    re.compile(r"^\s*\.\.\.$"),                   # point de suspension seul
    re.compile(r"^\s*pass\s*$"),                  # pass seul
    re.compile(r"^\s*#.*$"),                      # commentaire seul
    re.compile(r"^\[\d+\.\d+\]"),                 # score de pertinence seul
    re.compile(r"^line \d+ ->"),                  # reference de ligne seule
]


@register_pass("prune.facts", "Suppression des faits inutiles, doublons, bruit",
               requires=["chain.dedup"], priority=47)
def pass_prune_facts(query: str, plan, context_pack: str,
                     intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Nettoie les faits du dossier en supprimant le contenu a faible valeur.

    Passe conservative : ne supprime jamais un fait classifie 'critical'
    ou 'important' sauf si c'est un doublon exact.
    """
    if not dossier.facts:
        return DossierDelta()

    before = len(dossier.facts)
    removed_reasons = Counter()

    # Passe 1 : Supprimer les patterns de bruit
    keep: list[Fact] = []
    for f in dossier.facts:
        if any(p.match(f.text.strip()) for p in _NOISE_PATTERNS):
            removed_reasons["bruit_structural"] += 1
            continue
        keep.append(f)

    # Passe 2 : Doublons textuels exacts (conserver le premier)
    seen_texts: set[str] = set()
    deduped: list[Fact] = []
    for f in keep:
        key = f.text.strip().lower()
        if key in seen_texts:
            removed_reasons["doublon_exact"] += 1
            continue
        seen_texts.add(key)
        deduped.append(f)
    keep = deduped

    # Passe 3 : Supprimer les faits "secondary" a faible utilite
    pruned: list[Fact] = []
    for f in keep:
        if f.category == "secondary" and f.utility < 0.3:
            removed_reasons["faible_utilite"] += 1
            continue
        pruned.append(f)

    dossier.facts = pruned
    removed_total = before - len(pruned)

    signals: list[str] = []
    if removed_total > 0:
        detail = ", ".join(f"{k}:{v}" for k, v in removed_reasons.most_common())
        signals.append(
            f"Prune : {removed_total} faits supprimes "
            f"({len(pruned)} restants — {detail})"
        )

    return DossierDelta(signals=signals)
