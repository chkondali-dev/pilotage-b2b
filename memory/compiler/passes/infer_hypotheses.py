"""
infer.hypotheses — Passe 6 : hypotheses de debug (uniquement si DEBUG).
"""

from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind, Hypothesis


@register_pass("infer.hypotheses", "Hypotheses de debug (uniquement si DEBUG)",
               requires=["extract.facts"], priority=60)
def pass_infer_hypotheses(query: str, plan, context_pack: str,
                          intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Genere des hypotheses si l'intent est DEBUG."""
    if intent != IntentKind.DEBUG:
        return DossierDelta()

    hypotheses: list[Hypothesis] = []
    q_lower = query.lower()
    facts_text = [f.text.lower() for f in dossier.facts]

    hypotheses.append(Hypothesis(
        text="Le comportement observe differe du comportement attendu",
        confidence=0.3,
        triggered_by="default",
    ))

    if any("token" in f or "jwt" in f for f in facts_text) or "token" in q_lower:
        hypotheses.append(Hypothesis(
            text="Decalage de fuseau horaire ou expiration mal configuree",
            confidence=0.7,
            triggered_by="token_pattern",
        ))

    if any("import" in f for f in facts_text):
        hypotheses.append(Hypothesis(
            text="Import circulaire ou dependance manquante",
            confidence=0.5,
            triggered_by="import_pattern",
        ))

    if any("api" in f or "request" in f or "endpoint" in f for f in facts_text):
        hypotheses.append(Hypothesis(
            text="Contrat API modifie ou reponse inattendue du serveur",
            confidence=0.6,
            triggered_by="api_pattern",
        ))

    if any("none" in f or "null" in f for f in facts_text):
        hypotheses.append(Hypothesis(
            text="Cas None/null non gere dans le flux",
            confidence=0.6,
            triggered_by="null_pattern",
        ))

    return DossierDelta(hypotheses=hypotheses)
