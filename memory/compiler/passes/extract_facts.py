"""
extract.facts — Passe 2 : parsing du Context Pack en faits.
"""

from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind
from ..detect import parse_context_pack


@register_pass("extract.facts", "Parsing du Context Pack en faits",
               requires=["extract.objective"], priority=20)
def pass_extract_facts(query: str, plan, context_pack: str,
                       intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Parse le Context Pack brut en faits types avec metadata."""
    if not context_pack:
        return DossierDelta()
    facts = parse_context_pack(context_pack)
    return DossierDelta(facts=facts)
