"""
infer.signals — Passe 7 : signaux faibles et patterns suspects.
"""

from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind
from ..detect import deduplicate


@register_pass("infer.signals", "Signaux faibles et patterns suspects",
               requires=["extract.facts"], priority=65)
def pass_infer_signals(query: str, plan, context_pack: str,
                       intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Detecte des signaux faibles dans les faits."""
    signals: list[str] = []
    facts_text = [f.text.lower() for f in dossier.facts]

    if any("timeout" in f for f in facts_text):
        signals.append("Delai d'attente (timeout) detecte dans les appels")
    if any("try" in f or "except" in f for f in facts_text):
        signals.append("Gestion d'exceptions presente — verifier les cas non couverts")
    if any("deprecated" in f or "obsolete" in f for f in facts_text):
        signals.append("API ou fonction marquee comme deprecated")
    if any(("..." in f or "pass" in f) for f in facts_text):
        signals.append("Implementation incomplete detectee (pass, ...)")

    signals = deduplicate(signals)
    return DossierDelta(signals=signals)
