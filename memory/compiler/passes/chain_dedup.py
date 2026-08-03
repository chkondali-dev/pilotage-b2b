"""
chain.dedup — Fusionne les chaines d'appels en sequences logiques.

Exemple :
  login() appelle authenticate()
  authenticate() appelle jwt.decode()
  jwt.decode() leve TokenExpiredError
  →
  login() -> authenticate() -> jwt.decode() -> TokenExpiredError

Reduit le nombre de faits sans perte d'information.
"""

import re
from collections import defaultdict
from ..types import register_pass, DossierDelta, ReasoningDossier, IntentKind, Fact, FactKind
from ..detect import deduplicate


# Patterns de chaines d'appels
_CALL_PATTERNS = [
    re.compile(r"(\w+)\s+appelle\s+(\w+)", re.I),
    re.compile(r"(\w+)\s+calls?\s+(\w+)", re.I),
    re.compile(r"(\w+)\s+-\?>\s+(\w+)"),
    re.compile(r"(\w+)\s+appel\s+(?:a|de)\s+(\w+)", re.I),
    re.compile(r"(\w+)\s+invoque\s+(\w+)", re.I),
    re.compile(r"(\w+)\s+declenche\s+(\w+)", re.I),
    re.compile(r"(\w+)\s+leve\s+(\w+)", re.I),
    re.compile(r"(\w+)\s+raises?\s+(\w+)", re.I),
]


def _extract_calls(facts: list[Fact]) -> dict[str, set[str]]:
    """Extrait le graphe d'appels depuis les textes des faits."""
    graph: dict[str, set[str]] = defaultdict(set)
    for f in facts:
        text = f.text
        for pat in _CALL_PATTERNS:
            for m in pat.finditer(text):
                caller = m.group(1).strip("()")
                callee = m.group(2).strip("()")
                if caller != callee:  # pas d'auto-reference
                    graph[caller].add(callee)
                    # S'assurer que le callee est aussi dans le graphe
                    if callee not in graph:
                        graph[callee] = set()
    return dict(graph)


def _find_chains(graph: dict[str, set[str]]) -> list[list[str]]:
    """Trouve les chemins les plus longs dans le graphe (chaines)."""
    if not graph:
        return []

    # Tri topologique simple pour trouver les racines (noeuds qui ne sont
    # jamais la cible d'un appel)
    targets = {t for targets in graph.values() for t in targets}
    roots = [n for n in graph if n not in targets]

    if not roots:
        # Graphe cyclique ou tous les noeuds sont des cibles
        # Prendre les noeuds les plus connects comme "racines"
        in_degree = defaultdict(int)
        for t in targets:
            in_degree[t] += 1
        if in_degree:
            min_deg = min(in_degree.values())
            roots = [n for n in graph if in_degree.get(n, 0) == min_deg]
        else:
            roots = list(graph.keys())[:1]

    # DFS pour trouver les chemins les plus longs depuis chaque racine
    chains: list[list[str]] = []

    def _dfs(node: str, path: list[str], visited: set):
        if node in visited:
            return
        visited.add(node)
        current = path + [node]
        neighbors = graph.get(node, set()) - visited
        if not neighbors:
            # Fin de chemin
            if len(current) >= 2:
                chains.append(current)
        else:
            for nb in neighbors:
                _dfs(nb, current, visited)
        visited.discard(node)

    for r in roots:
        _dfs(r, [], set())

    # Fusionner les chaines qui se chevauchent
    # Trier par longueur (desc) pour traiter les plus longues d'abord
    chains.sort(key=len, reverse=True)

    merged: list[list[str]] = []
    seen_syms: set[str] = set()

    for chain in chains:
        unique = [s for s in chain if s not in seen_syms]
        if len(unique) >= 2:
            merged.append(unique)
            seen_syms.update(unique)

    return merged


@register_pass("chain.dedup", "Fusion des chaines d'appels en sequences logiques",
               requires=["classify.facts"], priority=46)
def pass_chain_dedup(query: str, plan, context_pack: str,
                     intent: IntentKind, dossier: ReasoningDossier) -> DossierDelta:
    """Detecte et fusionne les chaines d'appels dans les faits.

    Ne travaille pas si intent == GENERAL (pas de contexte d'appels pertinent).
    """
    if intent == IntentKind.GENERAL:
        return DossierDelta()

    # 1. Construire le graphe d'appels depuis les faits
    graph = _extract_calls(dossier.facts)
    if not graph:
        return DossierDelta()

    # 2. Trouver les chaines
    chains = _find_chains(graph)

    if not chains:
        return DossierDelta()

    # 3. Pour chaque chaine, creer un fait fusionne
    merged_facts: list[Fact] = []
    symbols_to_remove: set[str] = set()

    for chain in chains:
        chain_str = " -> ".join(chain)
        merged_facts.append(Fact(
            text=f"Chaine d'appels : {chain_str}",
            kind=FactKind.STATEMENT,
            importance=0.85,
            utility=0.7,
            category="important",
            tags=["call_chain", "merged"],
            confidence=1.0,
        ))
        symbols_to_remove.update(chain)

    # 4. Supprimer les faits individuels qui font partie des chaines
    #    (conserver les faits qui ne sont pas uniquement des references d'appel)
    before = len(dossier.facts)
    kept: list[Fact] = []
    removed_count = 0

    for f in dossier.facts:
        keep = True
        if f.kind == FactKind.STATEMENT:
            # Si ce fait ne contient QUE des appels et ses symboles sont
            # tous dans les chaines, on le supprime
            text = f.text
            mention_count = sum(1 for s in symbols_to_remove if s in text)
            total_symbols = len(re.findall(r'\b\w+\b', text))
            if mention_count >= 2 and mention_count / max(total_symbols, 1) >= 0.3:
                keep = False

        if keep:
            kept.append(f)
        else:
            removed_count += 1

    dossier.facts = kept
    dossier.facts.extend(merged_facts)

    signals = []
    if merged_facts:
        signals.append(
            f"Chaines fusionnees : {len(merged_facts)} chaines "
            f"(liberes {removed_count} faits individuels)"
        )

    return DossierDelta(signals=signals)
