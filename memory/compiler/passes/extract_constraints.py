"""
extract.constraints — Passe 3 : contraintes generiques (stack, fichiers, tests).
"""

from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind, Constraint
from ..detect import extract_files


@register_pass("extract.constraints", "Contraintes generiques (stack, fichiers, tests)",
               requires=["extract.facts"], priority=30)
def pass_extract_constraints(query: str, plan, context_pack: str,
                             intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Inferre les contraintes depuis le contexte et la requete."""
    constraints: list[Constraint] = []
    facts = dossier.facts
    q = query.lower()

    constraints.append(Constraint(text="Stack Python 3.14", severity="info"))

    if any("test" in f.text.lower() for f in facts) or "test" in q:
        constraints.append(Constraint(
            text="Ne pas casser les tests existants",
            severity="warning",
        ))

    files = extract_files(facts)
    if files:
        file_list = ", ".join(files[:5])
        if len(files) > 5:
            file_list += f" (+{len(files)-5} autres)"
        constraints.append(Constraint(
            text=f"Fichiers concernes : {file_list}",
            severity="info",
        ))

    if any(kw in q for kw in ("sqlite", "schema", "db", "base", "donnee", "data")):
        constraints.append(Constraint(
            text="Ne pas modifier le schema de base de donnees",
            severity="error",
        ))

    if any(kw in q for kw in ("perf", "lent", "slow", "optimise")):
        constraints.append(Constraint(
            text="Maintenir ou ameliorer les performances actuelles",
            severity="warning",
        ))

    return DossierDelta(constraints=constraints)
