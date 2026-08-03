"""
impact_analyzer.py — BFS impact analysis over code relations.

Given a symbol, traces:
  forward  : everything that depends on it (callers, inheritors, importers)
  backward : everything it depends on   (callees, imports, types used)

Usage:
    analyzer = ImpactAnalyzer(relations_store)
    report = analyzer.forward_impact("compute_kpi", depth=3)
    report = analyzer.full_impact("metrics/kpi.py:compute_kpi")
"""

from memory.relations import RelationsStore


class ImpactAnalyzer:
    """BFS traversal over RelationsStore to measure change impact."""

    def __init__(self, relations: RelationsStore):
        self.relations = relations

    # ── Public API ──────────────────────────────────────────

    def forward_impact(self, symbol: str, *,
                       file_path: str = "",
                       depth: int = 3,
                       relation_types: list[str] | None = None,
                       top_k: int = 200) -> dict:
        """Everything that depends on *symbol* (callers, inheritors, …).

        BFS forward: start at symbol → find relations targeting it →
        the sources are "affected" → expand from those sources.

        Returns dict with:
          levels: list of {depth, symbol, file, kind, …} per level
          stats: {total_nodes, max_depth}
          nodes: flat deduplicated set of all affected symbols
        """
        start = {"symbol": symbol, "file": file_path}
        tree, stats = self._bfs(
            seeds=[start],
            direction="forward",
            max_depth=depth,
            relation_types=relation_types,
            top_k=top_k,
        )
        return self._build_report(tree, stats, "forward")

    def backward_impact(self, symbol: str, *,
                        file_path: str = "",
                        depth: int = 3,
                        relation_types: list[str] | None = None,
                        top_k: int = 200) -> dict:
        """Everything *symbol* depends on (callees, imports, …).

        BFS backward: start at symbol → find relations from it →
        the targets are "dependencies" → expand from those targets.
        """
        start = {"symbol": symbol, "file": file_path}
        tree, stats = self._bfs(
            seeds=[start],
            direction="backward",
            max_depth=depth,
            relation_types=relation_types,
            top_k=top_k,
        )
        return self._build_report(tree, stats, "backward")

    def full_impact(self, symbol: str, *,
                    file_path: str = "",
                    depth: int = 2,
                    top_k: int = 200) -> dict:
        """Combined forward + backward impact report."""
        fwd = self.forward_impact(
            symbol, file_path=file_path, depth=depth, top_k=top_k,
        )
        bwd = self.backward_impact(
            symbol, file_path=file_path, depth=depth, top_k=top_k,
        )
        return {
            "symbol": symbol,
            "file": file_path,
            "forward": fwd,
            "backward": bwd,
            "forward_count": fwd["stats"]["total_nodes"],
            "backward_count": bwd["stats"]["total_nodes"],
            "total_impact": fwd["stats"]["total_nodes"] + bwd["stats"]["total_nodes"],
        }

    def summarize(self, symbol: str, *,
                  file_path: str = "",
                  top_k: int = 50) -> dict:
        """Single-page description of a symbol's role."""
        callers = self.relations.find_callers(symbol, top_k=top_k)
        callees = self.relations.find_callees(symbol, top_k=top_k)
        inheritors = self.relations.find_inheritors(symbol)[:top_k]

        # All relation types this symbol participates in
        as_source = self.relations.find_relations(
            source_symbol=symbol, limit=top_k,
        )
        as_target = self.relations.find_relations(
            target_symbol=symbol, limit=top_k,
        )

        # Dependencies (things this symbol uses)
        deps = {}
        for r in as_source:
            k = r["relation_type"]
            deps.setdefault(k, []).append(r["target_symbol"])

        # Dependents (things that use this symbol)
        used_by = {}
        for r in as_target:
            k = r["relation_type"]
            used_by.setdefault(k, []).append(r["source_symbol"])

        return {
            "symbol": symbol,
            "file": file_path or (as_source[0]["source_file"] if as_source else ""),
            "callers": [c["function"] for c in callers],
            "callees": [c["symbol"] for c in callees],
            "inheritors": [c["class"] for c in inheritors],
            "dependencies": deps,
            "dependents": used_by,
            "caller_count": len(callers),
            "callee_count": len(callees),
            "inheritor_count": len(inheritors),
        }

    # ── Internal BFS ────────────────────────────────────────

    def _bfs(self, seeds: list[dict], direction: str, *,
             max_depth: int, relation_types: list[str] | None,
             top_k: int) -> tuple[list, dict]:
        """Generic BFS over the relation graph.

        Args:
            seeds: [{"symbol": str, "file": str}, …]
            direction: "forward" (target→source) or "backward" (source→target)
            max_depth: how many BFS levels
            relation_types: optional filter on relation_type

        Returns:
            (tree: list of {depth, level list}, stats: dict)
        """
        tree = []          # list of levels, each level is a list of results
        discovered = set() # nodes already queued (prevents double-queue)
        current = seeds

        for d in range(max_depth + 1):
            if not current:
                break

            level: list[dict] = []
            # Collect unique neighbors across all seeds at this level
            pending: dict[str, dict] = {}  # nk → node (dedup neighbors)

            for node in current:
                sym = node["symbol"]
                fpath = node.get("file", "")
                key = f"{fpath}:{sym}" if fpath else sym
                # This node was already queued and processed → skip
                if d > 0:
                    level.append(node)

                # Find connected nodes
                neighbors = self._neighbors(
                    symbol=sym, file_path=fpath,
                    direction=direction, relation_types=relation_types,
                    top_k=top_k,
                )
                for nb in neighbors:
                    nk = f"{nb.get('file', '')}:{nb['symbol']}"
                    if nk not in discovered:
                        discovered.add(nk)
                        nb["_via"] = node.get("_via", []) + [{
                            "relation_type": nb.get("_rel_type", "?"),
                            "line": nb.get("line", 0),
                        }]
                        nb.pop("_rel_type", None)
                        # Dedup neighbors: same symbol found from >1 seed
                        if nk not in pending:
                            pending[nk] = nb

            if level or d == 0:
                tree.append({"depth": d, "nodes": level})

            current = list(pending.values())

        # Stats
        all_nodes = set()
        for lvl in tree:
            for n in lvl["nodes"]:
                all_nodes.add(n["symbol"])
        return tree, {"total_nodes": len(all_nodes), "max_depth": len(tree) - 1}

    def _neighbors(self, symbol: str, file_path: str, *,
                   direction: str,
                   relation_types: list[str] | None,
                   top_k: int) -> list[dict]:
        """Get immediate neighbors of symbol in the relation graph."""
        results: list[dict] = []

        if direction == "forward":
            # Find relations where symbol is the target
            # → sources are "affected" (they depend on symbol)
            rows = self.relations.find_relations(
                target_symbol=symbol, target_file=file_path
                if file_path else "",
                limit=top_k,
            )
        else:
            # Find relations where symbol is the source
            # → targets are "dependencies" (symbol depends on them)
            rows = self.relations.find_relations(
                source_symbol=symbol, source_file=file_path
                if file_path else "",
                limit=top_k,
            )

        for r in rows:
            if relation_types and r["relation_type"] not in relation_types:
                continue
            if direction == "forward":
                # The source depends on our symbol
                results.append({
                    "symbol": r["source_symbol"],
                    "file": r["source_file"],
                    "_rel_type": r["relation_type"],
                    "line": r["line_number"],
                    "condition": r["condition"],
                })
            else:
                # Our symbol depends on the target
                results.append({
                    "symbol": r["target_symbol"],
                    "file": r["target_file"],
                    "_rel_type": r["relation_type"],
                    "line": r["line_number"],
                    "condition": r["condition"],
                })

        return results

    # ── Report builder ──────────────────────────────────────

    def _build_report(self, tree: list, stats: dict,
                      direction: str) -> dict:
        """Build final report dict from BFS tree."""
        # Level layout
        levels = []
        for lvl in tree:
            levels.append({
                "depth": lvl["depth"],
                "count": len(lvl["nodes"]),
                "nodes": [
                    {
                        "symbol": n["symbol"],
                        "file": n.get("file", ""),
                        "via": n.get("_via", []),
                    }
                    for n in lvl["nodes"]
                ],
            })

        # All unique symbols
        flat = set()
        for lvl in tree:
            for n in lvl["nodes"]:
                flat.add(n["symbol"])

        return {
            "direction": direction,
            "levels": levels,
            "stats": {
                "total_nodes": stats["total_nodes"],
                "max_depth": stats["max_depth"],
                "unique_symbols": sorted(flat),
            },
        }


# ── Quick demo ──────────────────────────────────────────────

if __name__ == "__main__":
    from memory.relations import RelationsStore

    relations = RelationsStore("pilotage_b2b")
    analyzer = ImpactAnalyzer(relations)

    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "compute_kpi"
    report = analyzer.summarize(symbol)
    print(f"=== Impact summary: {symbol} ===")
    print(f"  File:          {report['file']}")
    print(f"  Callers:       {report['caller_count']}")
    print(f"  Callees:       {report['callee_count']}")
    print(f"  Inheritors:    {report['inheritor_count']}")
    print(f"  Dependencies:  {list(report['dependencies'].keys())}")
    print(f"  Dependents:    {list(report['dependents'].keys())}")

    if len(sys.argv) > 2:
        depth = int(sys.argv[2])
        print(f"\n=== Forward impact (depth={depth}) ===")
        fwd = analyzer.forward_impact(symbol, depth=depth)
        print(f"  Nodes: {fwd['stats']['total_nodes']}, Depth: {fwd['stats']['max_depth']}")
        for lvl in fwd["levels"]:
            if lvl["nodes"]:
                print(f"  Level {lvl['depth']}: {lvl['count']} nodes")
                for n in lvl["nodes"][:10]:
                    via = n["via"][-1]["relation_type"] if n["via"] else ""
                    print(f"    {n['symbol']:40s} ({via})")
