"""
injector.py — Injects relevant context at session/command start.

Usage:
    from memory.injector import inject_context
    context = inject_context("add rate limiting to API")
    # Returns formatted string of relevant past decisions
"""

from memory.memory_store import MemoryStore

MAX_CONTEXT_ITEMS = 8


def inject_context(query: str, namespace: str = "default",
                   top_k: int = MAX_CONTEXT_ITEMS) -> str:
    """
    Search memory for context relevant to the current task.
    Returns a formatted string ready for prompt injection.

    Call at the beginning of any new task or command.
    """
    store = MemoryStore(namespace)
    results = store.recall(query, top_k=top_k, min_score=0.15)

    if not results:
        return ""

    lines = ["<prior_context>"]
    for r in results:
        tags_str = ", ".join(r["tags"]) if r["tags"] else ""
        source_str = f" [{r['source']}]" if r["source"] else ""
        lines.append(f"  [{r['score']:.2f}] "
                     f"{r['content']}{source_str}"
                     f"{f' ({tags_str})' if tags_str else ''}")
    lines.append("</prior_context>")

    return "\n".join(lines)


def summarize_project_state(namespace: str = "default") -> str:
    """Generate a brief project state summary from stored memories."""
    store = MemoryStore(namespace)
    stats = store.stats()
    if stats["total"] == 0:
        return ""

    # Get high-score items
    top = store.list_all(limit=5)

    lines = ["# Project Memory State", f"- {stats['total']} items stored"]
    if stats["ollama_available"]:
        lines.append(f"- {stats['with_embeddings']} with vector embeddings")
    else:
        lines.append("- Embeddings: offline (Ollama not available)")
    lines.append("")

    if top:
        lines.append("## Key Context")
        for r in top:
            lines.append(f"- {r['content']}")

    return "\n".join(lines)


def capture_session_end(namespace: str = "default",
                        summary: str = "", tags: list = None):
    """
    Save a session summary as a memory item.
    Call at end of session to persist what was learned.
    """
    if not summary:
        return
    store = MemoryStore(namespace)
    store.remember(
        content=summary,
        tags=(tags or []) + ["session_end"],
        source="session"
    )
