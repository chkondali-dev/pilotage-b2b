"""
extract.artifacts — Passe 4 : extraction des artefacts (fichiers, modules).
"""

from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind
from ..detect import extract_files


@register_pass("extract.artifacts", "Extraction des artefacts (fichiers, modules)",
               requires=["extract.facts"], priority=35)
def pass_extract_artifacts(query: str, plan, context_pack: str,
                           intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Liste les fichiers/modules references comme artefacts."""
    files = extract_files(dossier.facts)
    if not files and plan and hasattr(plan, "steps") and plan.steps:
        for step in plan.steps:
            if hasattr(step, "args") and step.args:
                files.append(step.args[0])
    return DossierDelta(artifacts=files)
