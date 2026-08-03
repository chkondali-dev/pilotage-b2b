"""
RAG léger — retrieval sur KNOWLEDGE/ via embeddings all-minilm (Ollama).
Store SQLite local autonome : llm/store.py (base data/convention_ai.sqlite).
"""
import hashlib
import re
from pathlib import Path
from llm import config
from llm.store import MemoryStore


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
    """Indexe les .md/.txt de KNOWLEDGE/ (et data/dossiers/) dans la mémoire
    (idempotent par hash).

    Les dossiers client (data/dossiers/) sont indexés avec le tag
    « dossier » : le brain les retrouve par requête sémantique, pas
    seulement par nom de fichier cible.

    Les documents marqués SUPERSEDED (bandeau « ⚠️ **SUPERSEDED** » en tête) ne
    sont PAS indexés : ils sont obsolètes et pollueraient la pertinence.
    """
    store = MemoryStore("convention_ai")
    n = 0
    purges = 0

    # dossiers client en premier : requis par les intentions defense/comex
    dossiers_dir = config.DATA_DIR / "dossiers"
    bases = []
    if dossiers_dir.is_dir():
        bases.append(dossiers_dir)
    bases.append(knowledge_dir or config.KNOWLEDGE_DIR)

    # hash des chunks actuels par source → purge des chunks périmés ensuite
    actuels: dict[str, set] = {}
    hasher = hashlib.sha256

    for base in bases:
        for f in base.rglob("*"):
            if f.suffix.lower() not in (".md", ".txt"):
                continue
            texte = f.read_text(encoding="utf-8", errors="ignore")
            tete = texte[:200]
            if "superseded" in tete.lower():
                continue
            source = str(f.relative_to(config.ROOT))
            tags = ["dossier", f.stem] if base == dossiers_dir \
                else ["convention_ai", f.stem]
            chunks = _chunks(texte)
            for chunk in chunks:
                mid = store.remember(chunk, tags=tags, source=source)
                if mid != -1:
                    n += 1
            hashes = {hasher(chunk.strip().encode()).hexdigest() for chunk in chunks}
            actuels[source] = hashes

    # purge : chunks dont la source a changé de contenu (ex. placeholder → modèle)
    for source, keeps in actuels.items():
        purges += store.purge_source(source, keeps)
    if purges:
        print(f"  ↳ {purges} chunk(s) périmé(s) purgé(s) de la mémoire")
    return n


def chercher(question: str, top_k: int = 4) -> list[dict]:
    """Retourne les chunks KNOWLEDGE les plus pertinents pour une question."""
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
