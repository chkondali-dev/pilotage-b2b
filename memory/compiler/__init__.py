"""
memory.compiler — Compilateur de Dossier de Reflexion.

Remplace `dossier_builder.py` par une architecture modulaire.

Principes :
  - Chaque passe est un fichier independant dans `passes/`.
  - Le pipeline decouvre les passes via `register_pass` + autodiscover.
  - Les types sont centralises dans `types.py`.
  - Rendu separe dans `renderers.py`.
  - Retrocompatibilite via `dossier_builder.py` qui re-exporte tout.

Usage :
    from memory.compiler.pipeline import compile_dossier
    from memory.compiler.types import ReasoningDossier, IntentKind
"""

from .types import (
    IntentKind, FactKind, Fact, Constraint, Action, Hypothesis,
    DossierDelta, ReasoningDossier, PassFn, PassDef,
)
from .detect import detect_intent
from .pipeline import compile_dossier, resolve_pass_order, clear_cache, cache_stats
from .renderers import RendererPrompt, RendererJSON, render_to_prompt, render_to_dict

__all__ = [
    "IntentKind", "FactKind", "Fact", "Constraint", "Action", "Hypothesis",
    "DossierDelta", "ReasoningDossier", "PassFn", "PassDef",
    "detect_intent",
    "compile_dossier", "resolve_pass_order", "clear_cache", "cache_stats",
    "RendererPrompt", "RendererJSON", "render_to_prompt", "render_to_dict",
]
