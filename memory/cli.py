"""
CLI to interact with the memory system and Project Brain.

Usage:
    python -m memory.cli remember "content" --tags decision,architecture
    python -m memory.cli recall "search query"
    python -m memory.cli list --tag decision
    python -m memory.cli forget <id>
    python -m memory.cli stats
    python -m memory.cli inject "task description"
    python -m memory.cli brain index [--include-dir src,data]
    python -m memory.cli brain query "search terms"
    python -m memory.cli brain find <symbol_name>
    python -m memory.cli brain module <module_path>
    python -m memory.cli brain calls <symbol_name>
    python -m memory.cli brain deps <module_name>
    python -m memory.cli brain context "question vague"
    python -m memory.cli brain status
"""

import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from memory.memory_store import MemoryStore
from memory.injector import inject_context, summarize_project_state
from memory.code_indexer import index_project
from memory.relations import RelationsStore

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
NAMESPACE = "pilotage_b2b"


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m memory.cli <command> [args]")
        print("Commands: remember, recall, list, forget, stats, state, inject, brain")
        return

    cmd = args[0]
    store = MemoryStore(NAMESPACE)

    if cmd == "remember":
        _cmd_remember(store, args[1:])
    elif cmd == "recall":
        _cmd_recall(store, args[1:])
    elif cmd == "list":
        _cmd_list(store, args[1:])
    elif cmd == "forget":
        _cmd_forget(store, args[1:])
    elif cmd == "stats":
        st = store.stats()
        print(json.dumps(st, indent=2))
    elif cmd == "inject":
        query = " ".join(args[1:])
        ctx = inject_context(query, NAMESPACE)
        if ctx:
            print(ctx)
        else:
            print("No relevant context found.")
    elif cmd == "state":
        print(summarize_project_state(NAMESPACE) or "No state yet.")
    elif cmd == "brain":
        _cmd_brain(store, args[1:])
    else:
        print(f"Unknown command: {cmd}")


# ── Sub-command implementations ─────────────────────────────


def _cmd_remember(store, args):
    tags = []
    source = "manual"
    content_parts = []
    skip_next = False
    for i, a in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if a == "--tags" and i + 1 < len(args):
            tags = [t.strip() for t in args[i + 1].split(",")]
            skip_next = True
        elif a == "--source" and i + 1 < len(args):
            source = args[i + 1]
            skip_next = True
        elif a.startswith("--"):
            continue
        else:
            content_parts.append(a)
    content = " ".join(content_parts)
    if not content:
        print("Error: no content provided")
        return
    mid = store.remember(content, tags=tags, source=source)
    print(f"Stored as id={mid}")


def _cmd_recall(store, args):
    query = " ".join(args)
    results = store.recall(query, top_k=10)
    if not results:
        print("No results.")
        return
    for r in results:
        tags = ", ".join(r["tags"]) if r["tags"] else ""
        print(f"  [{r['score']:.2f}] {r['content']} ({tags})")


def _cmd_list(store, args):
    tag = None
    for i, a in enumerate(args):
        if a == "--tag" and i + 1 < len(args):
            tag = args[i + 1]
    items = store.list_all(tag_filter=tag)
    if not items:
        print("Nothing stored yet.")
        return
    for r in items:
        tags = ", ".join(r["tags"])
        print(f"  #{r['id']} [{r['score']:.1f}] {r['content'][:100]} ({tags})")


def _cmd_forget(store, args):
    if not args:
        print("Usage: forget <id>")
        return
    ok = store.forget(int(args[0]))
    print("Deleted." if ok else "Not found.")


# ── Brain commands ──────────────────────────────────────────


def _cmd_brain(store, args):
    if not args:
        _print_brain_help()
        return

    sub = args[0]
    sub_args = args[1:]

    if sub == "index":
        _brain_index(store, sub_args)
    elif sub == "query":
        _brain_query(store, sub_args)
    elif sub == "find":
        _brain_find(store, sub_args)
    elif sub == "module":
        _brain_module(store, sub_args)
    elif sub == "calls":
        _brain_calls(store, sub_args)
    elif sub == "deps":
        _brain_deps(store, sub_args)
    elif sub == "context":
        _brain_context(store, sub_args)
    elif sub == "status":
        _brain_status(store)
    else:
        _print_brain_help()


def _print_brain_help():
    print("Project Brain commands:")
    print("  brain index [--include-dir dir1,dir2]  Index project code")
    print("  brain query <query>                     Search indexed code")
    print("  brain find <name>                       Find a symbol by name")
    print("  brain module <path>                     Show module structure")
    print("  brain calls <name>                      Show callers/callees for a symbol")
    print("  brain deps <module>                     Show module dependencies")
    print("  brain context <question>                Ask a question in natural language")
    print("  brain status                            Show index statistics")


def _brain_index(store, args):
    """Index all project .py files + scan git history."""
    include_dirs = None
    for i, a in enumerate(args):
        if a == "--include-dir" and i + 1 < len(args):
            include_dirs = tuple(d.strip() for d in args[i + 1].split(","))

    # 1. Code index
    stats = index_project(
        str(PROJECT_ROOT),
        namespace=NAMESPACE,
        include_dirs=include_dirs,
    )

    # 2. Git history
    print("\n[GIT] Scanning git history...")
    _index_git(store)
    print()

    # 3. Store project-level summary
    store.remember(
        content=(
            f"Project Brain indexed {stats['files']} files, "
            f"{stats['functions']} functions, {stats['classes']} classes. "
            f"Root: {PROJECT_ROOT.name}"
        ),
        tags=["brain:index", "project_meta"],
        source="brain", no_embed=True,
    )


def _index_git(store):
    """Read recent git log and store commit summaries."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--stat", "--max-count=30"],
            capture_output=True, text=True, check=True,
            cwd=str(PROJECT_ROOT),
        )
        output = result.stdout.strip()
        if not output:
            print("   No git history found.")
            return

        # Parse commits
        commits = []
        current = []
        for line in output.split("\n"):
            if line.startswith(" ") and current:
                current.append(line.strip())
            elif line.strip():
                if current:
                    commits.append("\n".join(current))
                current = [line.strip()]
        if current:
            commits.append("\n".join(current))

        for i, commit_text in enumerate(commits):
            lines = commit_text.split("\n")
            header = lines[0]
            files = [l for l in lines[1:] if l and not l.startswith(" ")]
            # Store every 3rd commit to avoid overload
            if i % 3 == 0:
                store.remember(
                    content=f"[git] {header}\n    Files: {'; '.join(files[:5])}",
                    tags=["brain:git", "project_meta"],
                    source="brain", no_embed=True,
                )

        print(f"   {len(commits)} commits scanned, {len(commits) // 3 + 1} stored")

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   Git not available or not a git repository.")


def _brain_query(store, args):
    """Search indexed code using semantic recall."""
    query = " ".join(args)
    if not query:
        print("Usage: brain query <search terms>")
        return

    # Search all code-related tags
    results = store.recall(query, top_k=15, min_score=0.0)

    if not results:
        print("No results found in Project Brain.")
        return

    # Group by tag for display
    categories = {"code:function": [], "code:class": [], "code:constant": [],
                  "code:import": [], "code:module": [], "brain:git": [],
                  "other": []}

    for r in results:
        tags = r["tags"]
        placed = False
        for cat in categories:
            if cat in tags:
                categories[cat].append(r)
                placed = True
                break
        if not placed:
            categories["other"].append(r)

    # Display
    for cat_name, cat_label in [
        ("code:function", "Functions"),
        ("code:class", "Classes"),
        ("code:constant", "Constants"),
        ("code:import", "Imports"),
        ("code:module", "Modules"),
        ("brain:git", "Git History"),
        ("other", "Other"),
    ]:
        items = categories[cat_name]
        if not items:
            continue
        print(f"\n-- {cat_label} --")
        for r in items[:5]:
            tags = ", ".join(r["tags"])
            print(f"  [{r['score']:.2f}] {r['content'][:200]}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")


def _brain_find(store, args):
    """Find a symbol by exact name match (searches content field via SQL)."""
    name = " ".join(args).strip()
    if not name:
        print("Usage: brain find <symbol_name>")
        return

    with sqlite3.connect(str(store.db_path)) as conn:
        rows = conn.execute(
            "SELECT id, content, tags, source, score FROM memories "
            "WHERE content LIKE ? ORDER BY score DESC LIMIT 50",
            (f"%{name}%",),
        ).fetchall()

    if not rows:
        print(f"No symbol found matching '{name}'.")
        return

    print(f"\n[FIND] {len(rows)} results for '{name}':\n")
    for r in rows:
        tags = ", ".join(json.loads(r[2]))
        print(f"  [{r[4]:.2f}] {r[1][:250]}")
        print(f"       tags: {tags[:150]}\n")


def _brain_module(store, args):
    """Show everything indexed for a specific module/file."""
    path = " ".join(args).strip()
    if not path:
        print("Usage: brain module <file_path_or_name>")
        return

    with sqlite3.connect(str(store.db_path)) as conn:
        rows = conn.execute(
            "SELECT id, content, tags, source, score FROM memories "
            "WHERE source LIKE ? ORDER BY score DESC, id",
            (f"%{path}%",),
        ).fetchall()

    if not rows:
        print(f"No module found matching '{path}'.")
        return

    source = rows[0][3]
    print(f"\n[MODULE] {source}\n")

    for r in rows:
        tags = ", ".join(json.loads(r[2]))
        print(f"  {r[1][:200]}")
    print(f"\n  ({len(rows)} items total)")


def _brain_status(store):
    """Show index statistics."""
    stats = store.stats()
    all_items = store.list_all(limit=1000)

    # Count by tag
    tag_counts = {}
    for r in all_items:
        for t in r["tags"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    print("\n[BRAIN] Project Brain Status")
    print(f"   Namespace: {stats['namespace']}")
    print(f"   DB: {stats['db_path']}")
    print(f"   Total items: {stats['total']}")
    print(f"   With embeddings: {stats['with_embeddings']}")
    print(f"   Ollama: {'available' if stats['ollama_available'] else 'offline'}")
    print()
    if tag_counts:
        print("   By category:")
        for tag, count in sorted(tag_counts.items()):
            print(f"     {tag}: {count}")


def _brain_calls(store, args):
    """Show callers/callees for a symbol using RelationsStore."""
    name = " ".join(args).strip()
    if not name:
        print("Usage: brain calls <symbol_name>")
        return

    relations = RelationsStore(NAMESPACE)
    called_by = relations.get_called_by(name)
    calls_to = relations.get_calls(name)

    print(f"\n[BRAIN CALLS] {name}\n")

    if not called_by and not calls_to:
        print("  No call relationships found.")
        print("  Tip: run `brain index` first to build the call graph.")
        return

    if called_by:
        print(f"  Called by ({len(called_by)}):")
        for file_path, caller, _ in sorted(set(called_by)):
            print(f"    {file_path} :: {caller}")
        print()

    if calls_to:
        print(f"  Calls ({len(calls_to)}):")
        for callee, line, _ in sorted(set(calls_to)):
            print(f"    line {line} -> {callee}")


def _brain_deps(store, args):
    """Show dependencies for a module using RelationsStore."""
    module = " ".join(args).strip()
    if not module:
        print("Usage: brain deps <module_name>")
        return

    # Convert dotted module name to relative file path(s)
    file_candidates = [
        module.replace(".", "/") + ".py",
        module.replace(".", "/") + "/__init__.py",
    ]

    relations = RelationsStore(NAMESPACE)

    # Gather: what does this module import?
    imports: list[dict] = []
    for fc in file_candidates:
        imports.extend(relations.find_imports(fc))

    # Also find importers (who imports this module)
    importers = relations.find_importers(module)

    print(f"\n[BRAIN DEPS] {module}\n")

    if not imports and not importers:
        print("  No dependency data found.")
        print("  Tip: run `brain index` first.")
        return

    if imports:
        print(f"  Imports ({len(imports)}):")
        for imp in sorted(set(i["import"] for i in imports)):
            print(f"    {imp}")
        print()

    if importers:
        print(f"  Imported by ({len(importers)}):")
        for importer in sorted(importers):
            print(f"    {importer}")


def _brain_context(store, args):
    """Intent Planner + Context Builder + Dossier Compiler : interroge le cerveau en langage naturel."""
    query = " ".join(args).strip()
    if not query:
        print("Usage: brain context <question>")
        print("Ex: brain context comment fonctionne index_file ?")
        return

    from memory.intent_planner import IntentPlanner
    from memory.context_builder import ContextBuilder
    from memory.dossier_builder import compile_dossier, RendererPrompt

    planner = IntentPlanner()
    plan = planner.plan(query)

    builder = ContextBuilder(NAMESPACE)
    pack = builder.build(plan)

    dossier = compile_dossier(query=query, plan=plan, context_pack=pack)

    print(RendererPrompt().render(dossier))
    print(f"  [PASSES] {', '.join(dossier.passes_run)}")
    print(f"  [INTENT] {dossier.intent.value}")
    print(f"  [FAITS] {len(dossier.facts)} | [CONTRAINTES] {len(dossier.constraints)} | [ACTIONS] {len(dossier.actions)}")

    if dossier.hypotheses:
        print(f"  [HYPOTHESES] {len(dossier.hypotheses)}")
    if dossier.signals:
        print(f"  [SIGNAUX] {len(dossier.signals)}")
    if dossier.artifacts:
        print(f"  [ARTEFACTS] {', '.join(dossier.artifacts[:5])}")
    print()

    # Afficher le contexte brut en dessous (optionnel)
    print("--- CONTEXT PACK BRUT ---")
    print(pack)


if __name__ == "__main__":
    main()
