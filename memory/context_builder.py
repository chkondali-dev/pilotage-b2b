"""
context_builder.py — Context Builder pour Project Brain.

Exécute un RetrievalPlan (produit par l'Intent Planner) et assemble
un Context Pack structuré, prêt à être passé à un LLM pour raisonnement.

Usage:
    builder = ContextBuilder("pilotage_b2b")
    pack = builder.build(plan)
    print(pack)
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional

from memory.memory_store import MemoryStore
from memory.relations import RelationsStore
from memory.intent_planner import RetrievalPlan, RetrievalStep


# ── Helpers d'affichage ──────────────────────────────

def _section(title: str, body: str, indent: str = "  ") -> str:
    """Encadre une section dans le Context Pack."""
    if not body.strip():
        return ""
    lines = body.strip().split("\n")
    out = [f"  == {title} =="]
    for line in lines:
        out.append(f"{indent}{line}")
    out.append("")
    return "\n".join(out)


def _kv(key: str, value: str, width: int = 16) -> str:
    """Clé/valeur alignée."""
    return f"{key:<{width}}{value}"


def _limit(text: str, n: int = 300) -> str:
    """Tronque proprement."""
    if len(text) <= n:
        return text
    return text[:n-3] + "..."


# ── Context Builder ─────────────────────────────────


class ContextBuilder:
    """Exécute un plan de retrieval et produit un Context Pack structuré."""

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.store = MemoryStore(namespace)
        self.relations = RelationsStore(namespace)

    # ── Outils ────────────────────────────────────────

    def _tool_symbol(self, symbol: str) -> str:
        """Cherche la définition d'un symbole (classe ou fonction)."""
        parts = []
        with sqlite3.connect(str(self.store.db_path)) as conn:
            # Recherche dans le contenu : "class Symbol" ou "def Symbol"
            rows = conn.execute(
                """SELECT content, source, tags
                   FROM memories
                   WHERE (content LIKE ? OR content LIKE ?)
                     AND (tags LIKE '%code:class%' OR tags LIKE '%code:function%')
                   ORDER BY score DESC LIMIT 5""",
                (f"%class {symbol}%", f"%def {symbol}%"),
            ).fetchall()

        for content, source, tags_json in rows:
            tags = json.loads(tags_json)
            kind = "class" if "code:class" in tags else "function"
            parts.append(f"  [{kind}] {_limit(content, 250)}")
            parts.append(f"  {_kv('File', source)}")

        if not parts:
            return f"  Symbole '{symbol}' non trouvé.\n"

        return "\n".join(parts) + "\n"

    def _tool_find(self, query: str) -> str:
        """Recherche un symbole par nom."""
        with sqlite3.connect(str(self.store.db_path)) as conn:
            rows = conn.execute(
                """SELECT content, source, score
                   FROM memories
                   WHERE content LIKE ?
                   ORDER BY score DESC LIMIT 10""",
                (f"%{query}%",),
            ).fetchall()

        if not rows:
            return f"  Aucun résultat pour '{query}'.\n"

        parts = []
        for content, source, score in rows:
            parts.append(f"  [{score:.2f}] {_limit(content, 200)}")
            parts.append(f"  {_kv('File', source)}")
        return "\n".join(parts) + "\n"

    def _tool_calls(self, symbol: str) -> str:
        """Graphe d'appels d'un symbole."""
        called_by = self.relations.get_called_by(symbol)
        calls_to = self.relations.get_calls(symbol)

        if not called_by and not calls_to:
            return f"  Aucune relation d'appel pour '{symbol}'.\n"

        parts = []
        if called_by:
            parts.append(f"  Called by ({len(called_by)}) :")
            for fp, caller, _ in sorted(set(called_by))[:10]:
                clean = Path(fp).stem if "/" in fp or "\\" in fp else fp
                parts.append(f"    {clean} :: {caller}")
            if len(called_by) > 10:
                parts.append(f"    ... et {len(called_by) - 10} autres")

        if parts:
            parts.append("")

        if calls_to:
            parts.append(f"  Calls ({len(calls_to)}) :")
            for callee, line, _ in sorted(set(calls_to))[:20]:
                parts.append(f"    line {line} -> {callee}")
            if len(calls_to) > 20:
                parts.append(f"    ... et {len(calls_to) - 20} autres")

        return "\n".join(parts) + "\n"

    def _tool_deps(self, module: str) -> str:
        """Dépendances d'un module."""
        # Imports du module
        file_candidates = [
            module.replace(".", "/") + ".py",
            module.replace(".", "/") + "/__init__.py",
        ]
        imports = []
        for fc in file_candidates:
            imports.extend(self.relations.find_imports(fc))

        # Importers (qui importe ce module)
        importers = self.relations.find_importers(module)

        if not imports and not importers:
            return f"  Aucune dépendance pour '{module}'.\n"

        parts = []
        if imports:
            parts.append(f"  Imports ({len(imports)}) :")
            for imp in sorted(set(i["import"] for i in imports))[:15]:
                parts.append(f"    {imp}")
            if len(imports) > 15:
                parts.append(f"    ... et {len(imports) - 15} autres")

        if parts and importers:
            parts.append("")

        if importers:
            parts.append(f"  Imported by ({len(importers)}) :")
            for importer in sorted(importers)[:10]:
                parts.append(f"    {importer}")
            if len(importers) > 10:
                parts.append(f"    ... et {len(importers) - 10} autres")

        return "\n".join(parts) + "\n"

    def _tool_module(self, symbol: str) -> str:
        """Tout le contenu indexé d'un module/fichier."""
        with sqlite3.connect(str(self.store.db_path)) as conn:
            # Chercher par source contenant le symbole
            rows = conn.execute(
                """SELECT content, tags FROM memories
                   WHERE source LIKE ? ORDER BY id""",
                (f"%{symbol}%",),
            ).fetchall()

        if not rows:
            return f"  Aucun module trouvé pour '{symbol}'.\n"

        parts = []
        counts = {"class": 0, "function": 0, "constant": 0, "import": 0}
        for content, tags_json in rows:
            tags = json.loads(tags_json)
            # Compter
            for t in tags:
                if t.startswith("code:"):
                    k = t.replace("code:", "")
                    if k in counts:
                        counts[k] += 1
            # Afficher les 30 premiers symboles
            if len(parts) < 30:
                content_short = _limit(content, 180)
                parts.append(f"    {content_short}")

        # Résumé
        summary = (f"  [{symbol}] {counts['class']} classes, "
                   f"{counts['function']} fonctions, "
                   f"{counts['constant']} constantes, "
                   f"{counts['import']} imports")
        header = f"{summary}\n"
        if len(rows) > 30:
            header += f"  ({len(rows)} items, affichage des 30 premiers)\n"

        return header + "\n".join(parts) + "\n"

    def _tool_query(self, text: str) -> str:
        """Recherche sémantique dans les souvenirs."""
        results = self.store.recall(text, top_k=10, min_score=0.0)
        if not results:
            return f"  Aucun résultat pour '{text}'.\n"

        parts = []
        for r in results[:10]:
            score = r.get("score", 0)
            source = r.get("source", "")
            parts.append(f"  [{score:.2f}] [{source}] {_limit(r['content'], 200)}")
        return "\n".join(parts) + "\n"

    # ── Dispatch ──────────────────────────────────────

    _TOOLS = {
        "symbol": _tool_symbol,
        "find":   _tool_find,
        "calls":  _tool_calls,
        "deps":   _tool_deps,
        "module": _tool_module,
        "query":  _tool_query,
    }

    def build(self, plan: RetrievalPlan) -> str:
        """Exécute le plan et retourne un Context Pack formaté."""
        sections = []
        sections.append(f"Query: {plan.query}")
        steps_desc = ", ".join(s.label for s in plan.steps)
        sections.append(f"Steps: {steps_desc}\n")

        for step in plan.steps:
            tool_fn = self._TOOLS.get(step.tool)
            if tool_fn is None:
                continue
            body = tool_fn(self, step.args[0] if step.args else "")
            section = _section(step.label, body)
            if section:
                sections.append(section)

        # Assembler
        header = ".-- Context Pack --------------------------------------------------"
        footer = "'-----------------------------------------------------------------"
        body = "\n".join(sections)
        return f"{header}\n{body}\n{footer}\n"

    def build_from_query(self, query: str) -> str:
        """Raccourci : Intent Planner + Context Builder en un appel."""
        from memory.intent_planner import IntentPlanner
        planner = IntentPlanner()
        plan = planner.plan(query)
        return self.build(plan)


# ── CLI direct ───────────────────────────────────────


if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "comment fonctionne index_file ?"
    builder = ContextBuilder("pilotage_b2b")
    print(builder.build_from_query(query))
