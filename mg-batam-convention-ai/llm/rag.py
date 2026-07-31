"""
RAG léger — retrieval sur KNOWLEDGE/ via embeddings all-minilm (Ollama).
Réutilise le moteur memory/memory_store.py du repo (déjà en production).
"""
import re
from pathlib import Path
from llm import config

try:
    from memory.memory_store import MemoryStore  # repo racine
except ImportError:
    MemoryStore = None


def _chunks(text: str, size: int = 1500) -> list[str]:
    """Découpe un texte en chunks à chevauchement léger (ponytail: split naïf par paragraphes)."""
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) > size and buf:
            chunks.append(buf)
            buf = p
        else:
            buf += "\n\n" + p
    if buf:
        chunks.append(buf)
    return chunks


def indexer(knowledge_dir: Path | None = None) -> int:
    """Indexe les .md/.txt de KNOWLEDGE/ dans la mémoire (idempotent par hash)."""
    if MemoryStore is None:
        print("  ⚠️  memory.memory_store indisponible — RAG désactivé")
        return 0
    store = MemoryStore("convention_ai")
    n = 0
    for f in (knowledge_dir or config.KNOWLEDGE_DIR).rglob("*"):
        if f.suffix.lower() not in (".md", ".txt"):
            continue
        for chunk in _chunks(f.read_text(encoding="utf-8", errors="ignore")):
            mid = store.remember(chunk, tags=["convention_ai", f.stem],
                                 source=str(f.relative_to(config.ROOT)))
            if mid != -1:
                n += 1
    return n


def chercher(question: str, top_k: int = 4) -> list[dict]:
    """Retourne les chunks KNOWLEDGE les plus pertinents pour une question."""
    if MemoryStore is None:
        return []
    store = MemoryStore("convention_ai")
    results = store.recall(question, top_k=top_k)
    out = []
    for r in results:
        content = r.get("content", r) if isinstance(r, dict) else str(r)
        source = r.get("source", "") if isinstance(r, dict) else ""
        out.append({"content": content, "source": source})
    return out


def enrichir_prompt(question: str, prompt: str) -> str:
    """Ajoute le contexte KNOWLEDGE au prompt, s'il y a des résultats."""
    hits = chercher(question)
    if not hits:
        return prompt
    extra = "\n\n---\nContexte KNOWLEDGE (références SMG) :\n"
    for h in hits:
        extra += f"\n[{h['source']}] {h['content'][:800]}\n"
    return prompt + extra
