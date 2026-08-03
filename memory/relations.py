"""
relations.py — Dependency graph store for Project Brain.

Tracks calls, imports, inheritance, and generic relations between symbols.
Stored in the same SQLite database as MemoryStore.

Usage:
    from memory.relations import RelationsStore
    relations = RelationsStore("pilotage_b2b")
    relations.add_call("auth.py", "login", "authenticate", 42)
    callers = relations.find_callers("authenticate")

v2 additions:
    relations.add_relation("config.py", "TIMEOUT", "utils.py", "wait",
                           kind="references", metadata={"value": 30})
    results = relations.find_relations(source="config.py", kind="references")
    conditional = relations.find_relations(condition="feature_x")
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

MEMORY_DIR = Path.home() / ".opencode_memory"


class RelationsStore:
    """Stores symbol relationships extracted from code analysis."""

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.db_path = MEMORY_DIR / f"{namespace}.sqlite"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            # CREATE TABLE IF NOT EXISTS (schema v2 avec condition + metadata)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file TEXT NOT NULL,
                    source_symbol TEXT NOT NULL,
                    source_type TEXT DEFAULT '',
                    target_file TEXT DEFAULT '',
                    target_symbol TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    line_number INTEGER DEFAULT 0,
                    condition TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}'
                )
            """)
            # Migration v1→v2 : ajouter les colonnes manquantes pour les vieilles DB
            cols = {r[1] for r in conn.execute("PRAGMA table_info(relations)").fetchall()}
            if "condition" not in cols:
                conn.execute("ALTER TABLE relations ADD COLUMN condition TEXT DEFAULT ''")
            if "metadata" not in cols:
                conn.execute("ALTER TABLE relations ADD COLUMN metadata TEXT DEFAULT '{}'")
            # Index (apres les ALTER TABLE pour les vieilles DB)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_source
                ON relations(source_file, source_symbol)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_target
                ON relations(target_symbol)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_type
                ON relations(relation_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_condition
                ON relations(condition)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_source_type
                ON relations(source_file, relation_type)
            """)

    # ── Write ─────────────────────────────────────────────

    def add_relation(self, source_file: str, source_symbol: str = "",
                     target_file: str = "", target_symbol: str = "",
                     kind: str = "references", *,
                     line_number: int = 0,
                     condition: str = "",
                     metadata: Optional[dict] = None) -> int:
        """Record a generic relation between two symbols.

        Args:
            source_file: Source file path
            source_symbol: Symbol name in source
            target_file: Target file path (can be empty)
            target_symbol: Symbol name in target
            kind: Relation type label (e.g. 'references', 'configures', 'triggers')
            line_number: Source line number
            condition: Condition under which this relation holds (feature flag, env, ...)
            metadata: Arbitrary key-value metadata dict

        Returns:
            Row ID of the inserted relation
        """
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                """INSERT INTO relations
                   (source_file, source_symbol, target_file, target_symbol,
                    relation_type, line_number, condition, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (source_file, source_symbol, target_file, target_symbol,
                 kind, line_number, condition, meta_json),
            )
            return cur.lastrowid or -1

    def add_call(self, source_file: str, source_function: str,
                 callee: str, line_number: int = 0,
                 condition: str = "", metadata: Optional[dict] = None):
        """Record that source_function calls callee."""
        return self.add_relation(
            source_file=source_file, source_symbol=source_function,
            target_symbol=callee, kind="calls",
            line_number=line_number, condition=condition, metadata=metadata,
        )

    def add_import(self, source_file: str, module: str, name: str,
                   alias: str = "", condition: str = "",
                   metadata: Optional[dict] = None):
        """Record that source_file imports name from module."""
        target = f"{module}.{name}" if module and name else (module or name)
        if alias:
            target += f" as {alias}"
        return self.add_relation(
            source_file=source_file, source_symbol="",
            target_symbol=target, kind="imports",
            condition=condition, metadata=metadata,
        )

    def add_inherit(self, source_file: str, class_name: str, base_class: str,
                    condition: str = "", metadata: Optional[dict] = None):
        """Record that class_name inherits from base_class."""
        return self.add_relation(
            source_file=source_file, source_symbol=class_name,
            target_symbol=base_class, kind="inherits",
            condition=condition, metadata=metadata,
        )

    # ── Read ──────────────────────────────────────────────

    def find_relations(self, *, source_file: str = "",
                       source_symbol: str = "",
                       target_file: str = "",
                       target_symbol: str = "",
                       kind: str = "",
                       condition: str = "",
                       limit: int = 50) -> list[dict]:
        """Generic relation query with filters. All filters are optional.

        Only returns relations matching ALL non-empty filters.
        """
        clauses: list[str] = []
        params: list = []

        if source_file:
            clauses.append("source_file = ?")
            params.append(source_file)
        if source_symbol:
            clauses.append("source_symbol = ?")
            params.append(source_symbol)
        if target_file:
            clauses.append("target_file = ?")
            params.append(target_file)
        if target_symbol:
            clauses.append("target_symbol = ?")
            params.append(target_symbol)
        if kind:
            clauses.append("relation_type = ?")
            params.append(kind)
        if condition:
            clauses.append("condition = ?")
            params.append(condition)

        where = " AND ".join(clauses) if clauses else "1=1"

        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                f"""SELECT id, source_file, source_symbol, target_file,
                           target_symbol, relation_type, line_number,
                           condition, metadata
                    FROM relations WHERE {where}
                    ORDER BY id DESC LIMIT ?""",
                (*params, limit),
            ).fetchall()

        return [
            {
                "id": r[0], "source_file": r[1], "source_symbol": r[2],
                "target_file": r[3], "target_symbol": r[4],
                "relation_type": r[5], "line_number": r[6],
                "condition": r[7],
                "metadata": json.loads(r[8]) if r[8] else {},
            }
            for r in rows
        ]

    def find_callers(self, symbol: str, top_k: int = 20) -> list[dict]:
        """Find all functions that call the given symbol."""
        rows = self.find_relations(target_symbol=symbol, kind="calls", limit=top_k)
        return [
            {"file": r["source_file"], "function": r["source_symbol"],
             "line": r["line_number"], "condition": r["condition"],
             "metadata": r["metadata"]}
            for r in rows
        ]

    def find_callees(self, symbol: str, top_k: int = 20) -> list[dict]:
        """Find all symbols called by the given function."""
        rows = self.find_relations(source_symbol=symbol, kind="calls", limit=top_k)
        return [
            {"symbol": r["target_symbol"], "line": r["line_number"],
             "condition": r["condition"], "metadata": r["metadata"]}
            for r in rows
        ]

    def find_imports(self, file_path: str) -> list[dict]:
        """Find all imports in a given file."""
        rows = self.find_relations(source_file=file_path, kind="imports", limit=200)
        return [{"import": r["target_symbol"], "condition": r["condition"]} for r in rows]

    def find_importers(self, module: str) -> list[str]:
        """Find all files that import the given module."""
        keyword = f"{module}."
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """SELECT DISTINCT source_file FROM relations
                   WHERE target_symbol LIKE ? AND relation_type = 'imports'
                   ORDER BY source_file""",
                (f"{keyword}%",),
            ).fetchall()
        return [r[0] for r in rows]

    def find_inheritors(self, class_name: str) -> list[dict]:
        """Find all classes that inherit from the given class."""
        rows = self.find_relations(target_symbol=class_name, kind="inherits")
        return [{"file": r["source_file"], "class": r["source_symbol"],
                 "condition": r["condition"]} for r in rows]

    def symbol_deps(self, symbol: str) -> dict:
        """Get full dependency picture for a symbol."""
        return {
            "callers": self.find_callers(symbol),
            "callees": self.find_callees(symbol),
        }

    def module_deps(self, file_path: str) -> dict:
        """Get dependency picture for a module/file."""
        imports = self.find_imports(file_path)
        imported_by = self.find_importers(file_path)
        return {
            "imports": imports,
            "imported_by": imported_by,
        }

    def stats(self) -> dict:
        """Return relation count by type."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """SELECT relation_type, COUNT(*) as cnt
                   FROM relations GROUP BY relation_type ORDER BY cnt DESC"""
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def clear_file(self, file_path: str):
        """Remove all relations for a given file (before re-indexing)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM relations WHERE source_file = ?", (file_path,))

    # ── Old-style helpers (backward compat) ───────────────

    def get_called_by(self, symbol: str) -> list[tuple[str, str, int]]:
        """Get list of (file, function, line) that call the given symbol."""
        return [
            (r["file"], r["function"], r["line"])
            for r in self.find_callers(symbol)
        ]

    def get_calls(self, symbol: str) -> list[tuple[str, int, str]]:
        """Get list of (callee, line, file) that the given symbol calls."""
        rows = self.find_callees(symbol)
        return [(r["symbol"], r["line"], "") for r in rows]

    def get_imports(self, module_name: str) -> list[tuple[str, str, str]]:
        """Get list of (module, symbol, file) matching a module name."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """SELECT source_file, target_symbol, relation_type
                   FROM relations
                   WHERE target_symbol LIKE ? AND relation_type = 'imports'
                   ORDER BY source_file""",
                (f"{module_name}%",),
            ).fetchall()
        results = []
        for file_path, target, _ in rows:
            if "." in target:
                mod, sym = target.split(".", 1)
            else:
                mod, sym = target, ""
            results.append((mod, sym, file_path))
        return results
