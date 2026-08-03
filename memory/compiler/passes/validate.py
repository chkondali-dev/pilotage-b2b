"""
validate.dossier — Passe 8 : validation globale du dossier.
"""

from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind, Constraint


@register_pass("validate.dossier", "Validation globale du dossier",
               requires=["extract.objective", "extract.facts"], priority=80)
def pass_validate(query: str, plan, context_pack: str,
                  intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Valide l'integrite du dossier. Peut lever des erreurs."""
    errors: list[str] = []
    warnings: list[str] = []

    if not dossier.objective:
        errors.append("OBJECTIF vide — impossible de raisonner sans objectif")

    if not dossier.facts:
        warnings.append("Aucun fait extrait — le LLM n'aura pas de contexte")

    if intent == IntentKind.DEBUG and not dossier.hypotheses:
        warnings.append("Intent DEBUG mais aucune hypothese generee")

    if dossier.signals and not any("test" in a.text.lower() for a in dossier.actions):
        warnings.append("Des signaux ont ete detectes mais aucune action corrective")

    if errors:
        raise ValueError(
            f"Validation du dossier echouee ({len(errors)} erreur(s)):\n"
            + "\n".join(f"  ! {e}" for e in errors)
        )

    delta = DossierDelta()
    for w in warnings:
        delta.constraints.append(Constraint(text=f"[VALIDATION] {w}", severity="warning"))
    return delta
