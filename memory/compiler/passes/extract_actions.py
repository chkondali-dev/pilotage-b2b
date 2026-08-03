"""
extract.actions — Passe 5 : actions depuis le plan de retrieval.
"""

from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind, Action


@register_pass("extract.actions", "Actions depuis le plan de retrieval",
               requires=["extract.facts"], priority=40)
def pass_extract_actions(query: str, plan, context_pack: str,
                         intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Convertit le plan de retrieval en actions lisibles."""
    actions: list[Action] = []

    if plan and hasattr(plan, "steps") and plan.steps:
        for i, step in enumerate(plan.steps):
            label = getattr(step, "label", str(step))
            clean = label.replace("('", " : ").replace("')", "")
            actions.append(Action(text=clean, priority=i))

    if not actions:
        actions = [
            Action(text="Analyser le probleme identifie", priority=0),
            Action(text="Proposer une solution motivee", priority=1),
            Action(text="Valider avec un test reproductible", priority=2),
        ]

    if any("test" in f.text.lower() for f in dossier.facts):
        actions.append(Action(text="Ecrire un test de non-regression", priority=99))

    return DossierDelta(actions=actions)
