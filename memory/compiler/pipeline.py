"""
pipeline.py — Ordonnancement et execution des passes de compilation.

Point d'entree principal : compile_dossier()

Cache : les resultats sont mis en cache par hash des entrees.
    compile_dossier(query="X", context_pack="Y", ...)
    Si les memes (query + plan + context_pack + intent) sont passes,
    le cache renvoie le dossier sans re-executer.
    Activer avec cache=True (par defaut). Vider avec clear_cache().
"""

import hashlib
import json
from typing import Optional
from .types import (
    ReasoningDossier, DossierDelta, IntentKind, Constraint,
    get_all_passes, PassDef,
)
from .detect import detect_intent
from .passes import discover_passes

# ponytail: module-level dict cache, migrate to SQLite if persistence needed
_COMPILE_CACHE: dict[str, ReasoningDossier] = {}
_MAX_CACHE_SIZE = 64


def _cache_key(query: str, plan, context_pack: str, intent: IntentKind) -> str:
    """Hash stable des entrees pour le cache de compilation."""
    plan_json = json.dumps(
        {"steps": [{"tool": s.tool, "args": s.args, "label": s.label}
                    for s in (plan.steps if plan else [])]},
        sort_keys=True, default=str,
    )
    raw = f"{query}||{plan_json}||{context_pack}||{intent.value}"
    return hashlib.sha256(raw.encode()).hexdigest()


def clear_cache():
    """Vide le cache de compilation."""
    _COMPILE_CACHE.clear()


def cache_stats() -> dict:
    """Retourne les statistiques du cache."""
    return {
        "size": len(_COMPILE_CACHE),
        "max_size": _MAX_CACHE_SIZE,
    }


def resolve_pass_order() -> list[PassDef]:
    """Tri topologique des passes par dependances + priorite."""
    all_passes = get_all_passes()
    if not all_passes:
        # Si le registre est vide (tests), forcer la decouverte
        discover_passes()
        all_passes = get_all_passes()

    ordered: list[PassDef] = []
    executed: set[str] = set()
    pass_map = {p.name: p for p in all_passes}

    def _run(name: str):
        if name in executed:
            return
        p = pass_map.get(name)
        if not p:
            return
        for dep in p.requires:
            _run(dep)
        if name not in executed:
            executed.add(name)
            ordered.append(p)

    for p in sorted(all_passes, key=lambda x: x.priority):
        _run(p.name)

    return ordered


def compile_dossier(
    query: str = "",
    plan=None,
    context_pack: str = "",
    intent: Optional[IntentKind] = None,
) -> ReasoningDossier:
    """Pipeline complet : compile un dossier depuis les entrees brutes.

    Point d'entree principal du compilateur.

    Args:
        query: Question originale de l'utilisateur
        plan: RetrievalPlan de l'Intent Planner
        context_pack: Sortie brute du Context Builder
        intent: Type d'intent (detecte automatiquement si omis)

    Returns:
        ReasoningDossier rempli
    """
    if intent is None:
        intent = detect_intent(query, plan)

    # Cache check (sauf si context_pack est vide = premier appel sans contexte)
    if context_pack:
        key = _cache_key(query, plan, context_pack, intent)
        if key in _COMPILE_CACHE:
            cached = _COMPILE_CACHE[key]
            # Marquer avec un indicateur de cache hit
            cached.passes_run = [f"[CACHED] {p}" for p in cached.passes_run]
            return cached

    dossier = ReasoningDossier(intent=intent, source_context=context_pack or "")

    passes = resolve_pass_order()

    for p in passes:
        try:
            delta = p.fn(query, plan, context_pack, intent, dossier)
            if delta:
                dossier.apply(delta)
            dossier.passes_run.append(p.name)
        except ValueError:
            raise
        except Exception as e:
            dossier.apply(DossierDelta(
                constraints=[Constraint(
                    text=f"Passe '{p.name}' echouee : {e}",
                    severity="warning",
                )]
            ))

    # Cache write (eviction LRU si depasse _MAX_CACHE_SIZE)
    if context_pack:
        key = _cache_key(query, plan, context_pack, intent)
        if len(_COMPILE_CACHE) >= _MAX_CACHE_SIZE:
            # Eviction : supprimer une entree au hasard
            _COMPILE_CACHE.pop(next(iter(_COMPILE_CACHE)))
        _COMPILE_CACHE[key] = dossier

    return dossier
