"""
dossier_builder.py — Compilateur de Dossier de Reflexion.

AVERTISSEMENT : Ce fichier est un wrapper retrocompatible.
L'implementation se trouve dans memory/compiler/.

Architecture (inspiree LLVM) :

    Query ---> Retrieval Planner ---> Brain Query ---> Context Pack
                                                            |
                                                    +-------v--------+
                                                    |  Pass 1        |
                                                    |  Extraction    | ---> facts, constraints, artifacts
                                                    +-------+--------+
                                                            |
                                                    +-------v--------+
                                                    |  Pass 2        |
                                                    |  Inference     | ---> hypotheses, signals, actions
                                                    +-------+--------+
                                                            |
                                                    +-------v--------+
                                                    |  Pass 3        |
                                                    |  Validation    | ---> raise/warn si invalide
                                                    +-------+--------+
                                                            |
                                                    +-------v--------+
                                                    |  Renderer      |
                                                    |  (Prompt/JSON) | ---> str -> LLM
                                                    +-------+--------+
                                                            |
                                                    ReasoningDossier
                                                    (IR pure, pas de render)
"""

# Re-exporter tout depuis le nouveau module modulaire
# pylint: disable=unused-import, wrong-import-position, wildcard-import

import warnings
from memory.compiler.types import (
    IntentKind, FactKind, Fact, Constraint, Action, Hypothesis,
    DossierDelta, ReasoningDossier, PassFn, PassDef,
    register_pass, get_all_passes, clear_passes,
)
from memory.compiler.detect import (
    detect_intent, is_debug_query, extract_symbol,
    deduplicate, parse_context_pack, extract_files,
)
from memory.compiler.pipeline import compile_dossier, resolve_pass_order
from memory.compiler.renderers import RendererPrompt, RendererJSON, render_to_prompt, render_to_dict

from memory.compiler import *  # noqa: F401, F403


# Retrocompatibilite : DossierBuilder
class DossierBuilder:
    """Interface retrocompatible avec l'ancienne API.

    Delegue a compile_dossier() et compile_report() du compilateur modulaire.
    """

    def build(self, query: str, plan=None, context_pack: str = "") -> ReasoningDossier:
        from memory.compiler.pipeline import compile_dossier as _compile
        return _compile(query=query, plan=plan, context_pack=context_pack)

    def build_report(
        self,
        objective: str = "",
        facts: list | None = None,
        constraints: list | None = None,
        actions: list | None = None,
    ) -> ReasoningDossier:
        """Report path : construit un dossier depuis des donnees metier."""
        dossier = ReasoningDossier(
            intent=IntentKind.REPORT,
            objective=objective,
        )

        parsed_facts = []
        if facts:
            for f in facts:
                if isinstance(f, Fact):
                    parsed_facts.append(f)
                else:
                    text = str(f)
                    kind = FactKind.METRIC if any(
                        kw in text.lower() for kw in ("tnd", "dt", "%", "evolution")
                    ) else FactKind.STATEMENT
                    parsed_facts.append(Fact(text=text, kind=kind))

        dossier.facts = parsed_facts

        if constraints:
            for c in constraints:
                dossier.constraints.append(
                    c if isinstance(c, Constraint) else Constraint(text=str(c))
                )

        if actions:
            for a in actions:
                dossier.actions.append(
                    a if isinstance(a, Action) else Action(text=str(a))
                )

        return dossier


# Retrocompatibilite : le decorateur register_pass (important pour les tests)
# Deja re-exporte ci-dessus


# CLI (identique a l'original)
if __name__ == "__main__":
    import sys
    from memory.intent_planner import IntentPlanner
    from memory.context_builder import ContextBuilder

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "comment fonctionne index_file ?"

    planner = IntentPlanner()
    plan = planner.plan(query)
    builder = ContextBuilder("pilotage_b2b")
    context = builder.build(plan)

    dossier = compile_dossier(query=query, plan=plan, context_pack=context)
    print(RendererPrompt().render(dossier))
    print(f"\n[PASSES] {', '.join(dossier.passes_run)}")
    print(f"[INTENT] {dossier.intent.value}")
