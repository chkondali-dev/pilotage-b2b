"""
prioritize — Allocateur de budget tokens par categorie.

Decoupe le budget disponible par priorite :
  Architecture : 1000 tokens
  Faits critiques : 3500 tokens
  Chaines causales : 2000 tokens
  Contraintes : 800 tokens
  Contexte : 700 tokens

Les faits sont tries par (importance + utility) au sein de chaque
categorie, puis tronques si le budget est depasse.
"""

from collections import OrderedDict
from typing import Optional
from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind

# Budget par categorie (modele par defaut)
_BUDGET: dict[str, int] = {
    "critical":  3500,
    "important": 2000,
    "context":   800,
    "secondary": 200,   # quasi-jamais utilise apres prune
}

_BUDGET_ARCH: int = 1000
_BUDGET_ACTIONS: int = 500
_BUDGET_CONSTRAINTS: int = 800


def _estimate_tokens(fact_text: str) -> int:
    """Estimation grossiere : ~1 token = 4 caracteres en Python."""
    return max(1, len(fact_text) // 4)


@register_pass("prioritize", "Allocation du budget tokens par priorite et tri",
               requires=["prune.facts"], priority=48)
def pass_prioritize(query: str, plan, context_pack: str,
                    intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Trie et tronque les faits selon leur priorite et le budget disponible.

    Ordre de tri final : importance(desc) -> utility(desc) -> category
    Les faits 'critical' et 'important' sont preserves en priorite.
    """
    if not dossier.facts:
        return DossierDelta()

    before = len(dossier.facts)

    # 1. Trier les faits par (category priority, importance+utility)
    cat_order = {"critical": 0, "important": 1, "context": 2, "secondary": 3}

    dossier.facts.sort(key=lambda f: (
        cat_order.get(f.category, 99),
        -(f.importance + f.utility),
    ))

    # 2. Appliquer le budget par categorie
    budget_used: dict[str, int] = {}
    kept: list = []
    truncated_by_cat: dict[str, int] = {}

    for f in dossier.facts:
        cat = f.category if f.category in _BUDGET else "context"
        tokens = _estimate_tokens(f.text)
        used = budget_used.get(cat, 0)

        if used + tokens <= _BUDGET[cat]:
            budget_used[cat] = used + tokens
            kept.append(f)
        else:
            truncated_by_cat[cat] = truncated_by_cat.get(cat, 0) + 1

    dossier.facts = kept

    # 3. Tronquer les contraintes aussi
    const_before = len(dossier.constraints)
    const_budget = _BUDGET_CONSTRAINTS
    const_used = 0
    keep_const: list = []
    for c in dossier.constraints:
        t = _estimate_tokens(c.text)
        if const_used + t <= const_budget:
            const_used += t
            keep_const.append(c)
    dossier.constraints = keep_const
    const_removed = const_before - len(dossier.constraints)

    # 4. Tronquer les actions
    act_before = len(dossier.actions)
    act_budget = _BUDGET_ACTIONS
    act_used = 0
    keep_act: list = []
    for a in dossier.actions:
        t = _estimate_tokens(a.text)
        if act_used + t <= act_budget:
            act_used += t
            keep_act.append(a)
    dossier.actions = keep_act
    act_removed = act_before - len(dossier.actions)

    signals: list[str] = []
    pruned = before - len(kept)
    if pruned > 0:
        detail = ", ".join(
            f"{k}:{v}" for k, v in sorted(truncated_by_cat.items())
        )
        signals.append(f"Prioritize : {pruned} faits tronques (budget — {detail})")
    if const_removed > 0:
        signals.append(f"Prioritize : {const_removed} contraintes tronquees")
    if act_removed > 0:
        signals.append(f"Prioritize : {act_removed} actions tronquees")

    return DossierDelta(signals=signals)
