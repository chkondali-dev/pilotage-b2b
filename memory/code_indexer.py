"""
code_indexer.py — Tree-sitter based code indexer for Project Brain.

Scans .py files using Tree-sitter AST, extracting symbols (classes, functions,
constants, imports) and relationships (calls, inherits, imports, raises,
decorators, routes, types, overrides, implements).

v3 — 8 new relation types:
  overrides : method in subclass shadows parent method
  raises      : function raises an exception
  catches     : except clause catches an exception type
  decorator   : function/class decorated with @symbol
  route       : @app.get("/path") style route decorator
  test        : test_X function tests symbol X
  uses_type   : type annotation in parameter/return
  implements  : class implements Protocol/ABC

Usage:
    from memory.code_indexer import index_project
    stats = index_project("/path/to/project")
"""

import re
import os
from pathlib import Path
from tree_sitter import Parser, Language
import tree_sitter_python

from memory.memory_store import MemoryStore
from memory.relations import RelationsStore

# ── Tree-sitter initialisation (once) ──────────────────────

_PY_LANG = Language(tree_sitter_python.language())
_PARSER = Parser(_PY_LANG)

# Regex for route decorators: @<prefix>.<method>("<path>")
_ROUTE_RE = re.compile(
    r'(?:app|router|api|blueprint|bp)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
)

# Known Protocol/ABC base names
_PROTOCOL_BASES = frozenset({
    "Protocol", "ABC", "ABCMeta",
    "typing.Protocol", "abc.ABC", "abc.ABCMeta",
    "collections.abc.*",
})


# ── Helpers ─────────────────────────────────────────────────


def _text(source: bytes, node) -> str:
    """Get source text for a Tree-sitter node."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _get_docstring(source: bytes, block_node) -> str:
    """Extract docstring from a module/class/function block node."""
    if block_node is None or block_node.type != "block" or not block_node.children:
        return ""
    first = block_node.children[0]
    if first.type == "expression_statement" and first.children:
        child = first.children[0]
        if child.type == "string":
            raw = _text(source, child)
            for q in ('"""', "'''", '"', "'"):
                if raw.startswith(q) and raw.endswith(q):
                    return raw[len(q):-len(q)].strip()
    return ""


def _params(source: bytes, params_node) -> str:
    """Extract parameter names from a Tree-sitter parameters node."""
    if params_node is None:
        return ""
    parts = []
    for child in params_node.children:
        if child.type == "identifier":
            parts.append(_text(source, child))
        elif child.type in ("typed_parameter", "default_parameter"):
            for sub in child.children:
                if sub.type == "identifier":
                    parts.append(_text(source, sub))
                    break
        elif child.type == "list_splat_pattern":
            for sub in child.children:
                if sub.type == "identifier":
                    parts.append(f"*{_text(source, sub)}")
    return ", ".join(parts)


def _param_types(source: bytes, params_node) -> list[tuple[str, str]]:
    """Extract (param_name, type_name) from typed parameters."""
    types: list[tuple[str, str]] = []
    if params_node is None:
        return types
    for child in params_node.children:
        if child.type == "typed_parameter":
            name = ""
            type_name = ""
            for sub in child.children:
                if sub.type == "identifier" and not name:
                    name = _text(source, sub)
                elif sub.type in ("identifier", "attribute"):
                    type_name = _text(source, sub)
            if name and type_name:
                types.append((name, type_name))
    return types


def _return_type(source: bytes, func_node) -> str:
    """Extract return type annotation if present."""
    for child in func_node.children:
        if child.type == "type" and child.children:
            return _text(source, child.children[0])
    return ""


def _is_constant(name: str) -> bool:
    return len(name) > 1 and name.isupper() and ("_" in name or name.isupper())


def _find_calls(source: bytes, node, depth: int = 0) -> list[tuple[str, int]]:
    """Recursively find all call nodes: returns [(callee_name, line), ...]."""
    calls = []
    if depth > 50:
        return calls
    for child in node.children:
        if child.type == "call":
            fn_node = child.children[0] if child.children else None
            if fn_node:
                name = _text(source, fn_node)
                calls.append((name, fn_node.start_point[0] + 1))
        calls.extend(_find_calls(source, child, depth + 1))
    return calls


def _find_raises(source: bytes, node, depth: int = 0) -> list[str]:
    """Find all raise_statement nodes, return exception names."""
    raises: list[str] = []
    if depth > 50:
        return raises
    for child in node.children:
        if child.type == "raise_statement":
            if child.children and len(child.children) >= 2:
                exc_node = child.children[1]
                if exc_node.type == "call":
                    fn = exc_node.children[0] if exc_node.children else None
                    if fn:
                        raises.append(_text(source, fn))
                elif exc_node.type in ("identifier", "attribute"):
                    raises.append(_text(source, exc_node))
        raises.extend(_find_raises(source, child, depth + 1))
    return raises


def _find_catches(source: bytes, node, depth: int = 0) -> list[str]:
    """Find all except_clause nodes, return caught exception names."""
    catches: list[str] = []
    if depth > 50:
        return catches
    for child in node.children:
        if child.type == "except_clause":
            # except [ExceptionType] as e:
            for sub in child.children:
                if sub.type in ("identifier", "attribute"):
                    name = _text(source, sub)
                    if name.lower() not in ("as",):
                        catches.append(name)
        catches.extend(_find_catches(source, child, depth + 1))
    return catches


def _module_name(filepath: Path, project_root: Path) -> str:
    """Convert file path to dotted module name."""
    rel = filepath.relative_to(project_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].replace(".py", "")
    return ".".join(parts)


# ── Main indexing ───────────────────────────────────────────


def index_file(filepath: Path, store: MemoryStore, relations: RelationsStore,
               project_root: Path) -> dict:
    """Parse a single .py file with Tree-sitter. Store symbols + relations."""
    stats = {"classes": 0, "functions": 0, "constants": 0, "imports": 0}
    rel_path = str(filepath.relative_to(project_root)).replace("\\", "/")
    mod_name = _module_name(filepath, project_root)

    try:
        source = filepath.read_bytes()
    except Exception:
        return stats

    tree = _PARSER.parse(source)
    root = tree.root_node
    if root.type != "module":
        return stats

    # ── Module docstring ──
    if root.children and root.children[0].type == "expression_statement":
        doc = _get_docstring(source, root)
        if doc:
            store.remember(
                content=f"[{rel_path}] Module: {doc[:200]}",
                tags=["code:module", "docstring"],
                source=rel_path, no_embed=True,
            )

    # ── Top-level walk ──
    for child in root.children:
        t = child.type

        # ── Import ──
        if t == "import_statement":
            for sub in child.children:
                if sub.type in ("dotted_name", "aliased_import"):
                    name = _text(source, sub)
                    store.remember(
                        content=f"[{rel_path}] import {name}",
                        tags=["code:import"], source=rel_path, no_embed=True,
                    )
                    relations.add_import(rel_path, "", name, "")
                    stats["imports"] += 1

        elif t == "import_from_statement":
            module_name = ""
            names = []
            for sub in child.children:
                if sub.type == "dotted_name":
                    if not module_name:
                        module_name = _text(source, sub)
                    else:
                        names.append(_text(source, sub))
                elif sub.type == "aliased_import":
                    names.append(_text(source, sub))
                elif sub.type == "wildcard_import":
                    names.append("*")
            for name in names:
                store.remember(
                    content=f"[{rel_path}] from {module_name} import {name}",
                    tags=["code:import"], source=rel_path, no_embed=True,
                )
                relations.add_import(rel_path, module_name, name, "")
                stats["imports"] += 1

        # ── Class ──
        elif t == "class_definition":
            _process_class(source, child, store, relations, rel_path, stats)

        # ── Top-level function ──
        elif t == "function_definition":
            _process_function(source, child, store, relations, rel_path, "", stats)

        # ── Decorated function/class ──
        elif t == "decorated_definition":
            _process_decorated_definition(source, child, store, relations,
                                          rel_path, "", stats)

        # ── Constants ──
        elif t == "expression_statement":
            for expr in child.children:
                if expr.type == "assignment":
                    left = expr.children[0] if expr.children else None
                    if left and left.type == "identifier":
                        name = _text(source, left)
                        if _is_constant(name):
                            right = _text(source, expr.children[-1]) if len(expr.children) > 1 else ""
                            if len(right) > 120:
                                right = right[:117] + "..."
                            store.remember(
                                content=f"[{rel_path}] {name} = {right}",
                                tags=["code:constant"], source=rel_path, no_embed=True,
                            )
                            stats["constants"] += 1

        # ── Recurse into containers (if/with/try/for) for nested defs ──
        else:
            _find_nested_defs(source, child, store, relations, rel_path, stats)

    return stats


def _find_nested_defs(source: bytes, node, store: MemoryStore,
                      relations: RelationsStore, rel_path: str,
                      stats: dict, depth: int = 0):
    """Recursively find function/class definitions inside control flow blocks."""
    if depth > 20:
        return
    depth += 1
    for child in node.children:
        t = child.type
        if t == "function_definition":
            _process_function(source, child, store, relations,
                              rel_path, "", stats)
        elif t == "class_definition":
            _process_class(source, child, store, relations, rel_path, stats)
        elif t == "decorated_definition":
            _process_decorated_definition(source, child, store, relations,
                                          rel_path, "", stats)
        else:
            _find_nested_defs(source, child, store, relations,
                              rel_path, stats, depth)


def _process_class(source: bytes, node, store: MemoryStore,
                   relations: RelationsStore, rel_path: str, stats: dict,
                   extra_decorators: list[str] | None = None):
    """Index a class definition: store class + methods + inheritance + decorators."""
    stats["classes"] += 1
    class_name = ""
    bases = []
    block_node = None
    decorators: list[str] = list(extra_decorators or [])

    for child in node.children:
        if child.type == "identifier":
            class_name = _text(source, child)
        elif child.type == "argument_list":
            for arg in child.children:
                if arg.type in ("identifier", "attribute"):
                    bases.append(_text(source, arg))
        elif child.type == "block":
            block_node = child
        elif child.type == "decorator":
            dec = _extract_decorator(source, child)
            if dec:
                decorators.append(dec)

    class_doc = _get_docstring(source, block_node)

    # Store class
    content = f"[{rel_path}] class {class_name}"
    if bases:
        content += f"({', '.join(bases)})"
    if class_doc:
        content += f" — {class_doc[:150]}"
    store.remember(
        content=content, tags=["code:class"], source=rel_path, no_embed=True,
    )

    # Inheritance relations
    for base in bases:
        relations.add_inherit(rel_path, class_name, base)
        # Implements: Protocol / ABC bases
        if any(pb in base for pb in _PROTOCOL_BASES):
            relations.add_relation(
                source_file=rel_path, source_symbol=class_name,
                target_symbol=base, kind="implements",
            )

    # Decorators on class
    for dec in decorators:
        if _ROUTE_RE.match(dec):
            m = _ROUTE_RE.match(dec)
            if m:
                relations.add_relation(
                    source_file=rel_path, source_symbol=class_name,
                    target_symbol=f"{m.group(1).upper()} {m.group(2)}",
                    kind="route", metadata={"method": m.group(1), "path": m.group(2)},
                )
        else:
            relations.add_relation(
                source_file=rel_path, source_symbol=class_name,
                target_symbol=dec, kind="decorator",
            )

    # Methods
    if block_node:
        for item in block_node.children:
            if item.type == "function_definition":
                _process_function(source, item, store, relations,
                                  rel_path, f"{class_name}.", stats,
                                  class_bases=bases, class_name=class_name)
            elif item.type == "decorated_definition":
                _process_decorated_definition(source, item, store, relations,
                                              rel_path, f"{class_name}.", stats,
                                              class_bases=bases, class_name=class_name)


def _process_decorated_definition(source: bytes, node, store: MemoryStore,
                                  relations: RelationsStore, rel_path: str,
                                  prefix: str, stats: dict,
                                  class_bases: list[str] | None = None,
                                  class_name: str = ""):
    """Unpack a decorated_definition: extract decorators, process inner def."""
    decorators: list[str] = []
    inner = None
    for child in node.children:
        if child.type == "decorator":
            dec = _extract_decorator(source, child)
            if dec:
                decorators.append(dec)
        elif child.type == "function_definition":
            inner = child
        elif child.type == "class_definition":
            inner = child

    if inner is None:
        return

    if inner.type == "function_definition":
        _process_function(source, inner, store, relations,
                          rel_path, prefix, stats,
                          class_bases=class_bases, class_name=class_name,
                          extra_decorators=decorators)
    elif inner.type == "class_definition":
        _process_class(source, inner, store, relations, rel_path, stats,
                       extra_decorators=decorators)


def _extract_decorator(source: bytes, decorator_node) -> str:
    """Extract decorator text from @decorator node."""
    for child in decorator_node.children:
        if child.type in ("identifier", "attribute", "call"):
            if child.type == "call":
                fn = child.children[0] if child.children else None
                if fn:
                    return _text(source, fn)
            return _text(source, child)
    return ""


def _process_function(source: bytes, node, store: MemoryStore,
                      relations: RelationsStore, rel_path: str,
                      prefix: str, stats: dict,
                      class_bases: list[str] | None = None,
                      class_name: str = "",
                      extra_decorators: list[str] | None = None):
    """Index a function/method: extract symbol, calls, raises, decorators, types."""
    stats["functions"] += 1
    func_name = ""
    params_node = None
    block_node = None
    decorators: list[str] = list(extra_decorators or [])

    for child in node.children:
        if child.type == "identifier":
            func_name = _text(source, child)
        elif child.type == "parameters":
            params_node = child
        elif child.type == "block":
            block_node = child
        elif child.type == "decorator":
            dec = _extract_decorator(source, child)
            if dec:
                decorators.append(dec)

    qualified = prefix + func_name
    func_doc = _get_docstring(source, block_node)

    # ── Store symbol ──
    param_text = _params(source, params_node)
    content = f"[{rel_path}] def {qualified}({param_text})"
    ret_type = _return_type(source, node)
    if ret_type:
        content += f" -> {ret_type}"
    if func_doc:
        content += f"\n    {func_doc[:200]}"
    store.remember(
        content=content, tags=["code:function"], source=rel_path, no_embed=True,
    )

    # ── Calls ──
    if block_node:
        for callee, line in _find_calls(source, block_node):
            relations.add_call(rel_path, qualified, callee, line)

    # ── Raises ──
    if block_node:
        for exc_name in _find_raises(source, block_node):
            relations.add_relation(
                source_file=rel_path, source_symbol=qualified,
                target_symbol=exc_name, kind="raises",
            )

    # ── Catches ──
    if block_node:
        for exc_name in _find_catches(source, block_node):
            relations.add_relation(
                source_file=rel_path, source_symbol=qualified,
                target_symbol=exc_name, kind="catches",
            )

    # ── Decorators ──
    for dec in decorators:
        # Route decorator?
        m = _ROUTE_RE.match(dec)
        if m:
            route_sym = f"{m.group(1).upper()} {m.group(2)}"
            relations.add_relation(
                source_file=rel_path, source_symbol=qualified,
                target_symbol=route_sym, kind="route",
                metadata={"method": m.group(1), "path": m.group(2)},
            )
        else:
            relations.add_relation(
                source_file=rel_path, source_symbol=qualified,
                target_symbol=dec, kind="decorator",
            )

    # ── Uses_type (param type annotations) ──
    for param_name, type_name in _param_types(source, params_node):
        relations.add_relation(
            source_file=rel_path, source_symbol=qualified,
            target_symbol=f"{type_name}",
            kind="uses_type",
            metadata={"param": param_name, "type": type_name},
        )

    # ── Return type as uses_type ──
    if ret_type:
        relations.add_relation(
            source_file=rel_path, source_symbol=qualified,
            target_symbol=ret_type, kind="uses_type",
            metadata={"return_type": ret_type},
        )

    # ── Overrides (method in subclass shadows parent) ──
    if class_bases and class_name:
        # Method in a class with inheritance → potential override
        if func_name != "__init__":
            for base in class_bases:
                relations.add_relation(
                    source_file=rel_path, source_symbol=qualified,
                    target_symbol=f"{base}.{func_name}",
                    kind="overrides",
                    metadata={"potential": True, "base_class": base},
                )

    # ── Test (convention: test_X → tests X) ──
    if func_name.startswith("test_") or func_name.startswith("test"):
        tested_sym = func_name.replace("test_", "", 1).replace("test", "", 1)
        if tested_sym and tested_sym[0].isupper():
            relations.add_relation(
                source_file=rel_path, source_symbol=qualified,
                target_symbol=tested_sym, kind="test",
                metadata={"convention": "test_X"},
            )


# ── Project-level orchestration ─────────────────────────────


def index_project(project_root: str, namespace: str = "default",
                  include_dirs: tuple | None = None,
                  exclude_dirs: tuple | None = None) -> dict:
    """Walk project directory and index all .py files with Tree-sitter."""
    if include_dirs is None:
        include_dirs = ()
    if exclude_dirs is None:
        exclude_dirs = (".git", "__pycache__", "node_modules", ".venv",
                        ".opencode", "mempalace", ".omo")

    store = MemoryStore(namespace)
    relations = RelationsStore(namespace)
    root = Path(project_root).resolve()
    total = {"files": 0, "classes": 0, "functions": 0,
             "constants": 0, "imports": 0}

    print(f"[BRAIN] Indexing project: {root.name}")
    print(f"   Namespace: {namespace}, DB: {store.db_path}\n")

    for pyfile in sorted(root.rglob("*.py")):
        rel = pyfile.relative_to(root)
        parts = rel.parts
        if any(p in parts for p in exclude_dirs):
            continue
        if include_dirs and not any(p in parts for p in include_dirs):
            continue

        rel_str = str(rel).replace("\\", "/")
        relations.clear_file(rel_str)

        stats = index_file(pyfile, store, relations, root)
        if any(v > 0 for v in stats.values()):
            print(f"  {rel} — {stats}")
            total["files"] += 1
            for k in stats:
                total[k] += stats[k]

    # Store project metadata
    store.remember(
        content=(
            f"Project {root.name} indexed with Tree-sitter: "
            f"{total['files']} files, {total['classes']} classes, "
            f"{total['functions']} functions, {total['constants']} constants, "
            f"{total['imports']} imports"
        ),
        tags=["code:index", "project_meta"],
        source="brain", no_embed=True,
    )

    rel_stats = relations.stats()
    print(f"\n-> Indexed {total['files']} files: "
          f"{total['classes']} classes, {total['functions']} functions, "
          f"{total['constants']} constants, {total['imports']} imports")
    if rel_stats:
        print(f"   Relations: {rel_stats}")

    return total


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    index_project(root, namespace="pilotage_b2b")
