"""
store.py — Mémoire locale autonome de convention-ai (SQLite + embeddings).

Stocke les chunks KNOWLEDGE/ et le registre de décisions dans une base SQLite
propre au projet (data/convention_ai.sqlite) — aucune dépendance au repo racine.
Embeddings all-minilm via Ollama ; dégradation silencieuse vers recherche
par mots-clés si Ollama est indisponible.

Interface (identique à l'usage RAG) :
    store = MemoryStore("convention_ai")
    store.remember(chunk, tags=[...], source=...)   # idempotent par hash
    results = store.recall(query, top_k=4)          # dicts {content, source, score, ...}
"""

import hashlib
import json
import re
import sqlite3
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path

from llm import config

OLLAMA_URL = config.OLLAMA_ENDPOINT + "/api/embeddings"
EMBEDDING_MODEL = "all-minilm:latest"
EMBEDDING_DIM = 384


class MemoryStore:
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.db_path = config.DATA_DIR / f"{namespace}.sqlite"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    tags TEXT DEFAULT '[]',
                    source TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    score REAL DEFAULT 0.0,
                    vector BLOB
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(tags)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_score ON memories(score DESC)")

    # ── Write ─────────────────────────────────────────────

    def remember(self, content: str, tags: list | None = None,
                 source: str = "", no_embed: bool = False) -> int:
        """Stocke une entrée. Retourne son id (idempotent : doublon → update)."""
        content = content.strip()
        if not content:
            return -1
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        now = time.time()
        tags_json = json.dumps(tags or [])
        vector = None if no_embed else self._compute_embedding(content)
        with sqlite3.connect(str(self.db_path)) as conn:
            try:
                cur = conn.execute("""
                    INSERT INTO memories (content, content_hash, tags, source,
                                          created_at, updated_at, vector)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (content, content_hash, tags_json, source, now, now, vector))
                return cur.lastrowid or -1
            except sqlite3.IntegrityError:
                conn.execute("""
                    UPDATE memories SET updated_at = ?, access_count = access_count + 1,
                                        vector = COALESCE(?, vector)
                    WHERE content_hash = ?
                """, (now, vector, content_hash))
                row = conn.execute("SELECT id FROM memories WHERE content_hash = ?",
                                   (content_hash,)).fetchone()
                return row[0] if row else -1

    def forget(self, memory_id: int) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            c = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return c.rowcount > 0

    def purge_source(self, source: str, keep_hashes: set) -> int:
        """Supprime les chunks d'une source dont le hash n'est plus dans
        keep_hashes — garde la mémoire synchronisée avec les fichiers."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT id, content_hash FROM memories WHERE source = ?",
                (source,)).fetchall()
            ids = [r[0] for r in rows if r[1] not in keep_hashes]
            if ids:
                conn.executemany("DELETE FROM memories WHERE id = ?",
                                 [(i,) for i in ids])
            return len(ids)

    # ── Read ───────────────────────────────────────────────

    def recall(self, query: str, top_k: int = 10, min_score: float = 0.0) -> list[dict]:
        """Recherche sémantique (embeddings) avec repli mots-clés."""
        query_vector = self._compute_embedding(query)
        if query_vector:
            return self._vector_search(query_vector, top_k, min_score)
        return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        terms = re.findall(r"\w+", query.lower())
        if not terms:
            return []
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute("""
                SELECT id, content, tags, source, created_at, access_count, score
                FROM memories ORDER BY score DESC, created_at DESC
            """).fetchall()
        results = []
        for row in rows:
            content_lower = row[1].lower()
            match_count = sum(1 for t in terms if t in content_lower)
            if match_count > 0:
                results.append({
                    "id": row[0], "content": row[1], "tags": json.loads(row[2]),
                    "source": row[3], "created_at": row[4], "access_count": row[5],
                    "score": row[6] + match_count * 0.1,
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _vector_search(self, query_vector: bytes, top_k: int, min_score: float) -> list[dict]:
        import numpy as np
        query_np = np.frombuffer(query_vector, dtype=np.float32)
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute("""
                SELECT id, content, tags, source, created_at, access_count, score, vector
                FROM memories WHERE vector IS NOT NULL
                ORDER BY score DESC LIMIT ?
            """, (top_k * 5,)).fetchall()
        scored = []
        for row in rows:
            vec = row[7]
            if not vec:
                continue
            stored_np = np.frombuffer(vec, dtype=np.float32)
            sim = float(np.dot(query_np, stored_np) / (
                np.linalg.norm(query_np) * np.linalg.norm(stored_np) + 1e-10))
            combined = sim * 0.8 + (row[6] / 10.0) * 0.2
            if combined >= min_score:
                scored.append({
                    "id": row[0], "content": row[1], "tags": json.loads(row[2]),
                    "source": row[3], "created_at": row[4], "access_count": row[5],
                    "score": round(combined, 4), "similarity": round(sim, 4),
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def list_all(self, tag_filter: str | None = None, limit: int = 50) -> list[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            if tag_filter:
                rows = conn.execute("""
                    SELECT id, content, tags, source, created_at, access_count, score
                    FROM memories WHERE tags LIKE ? ORDER BY score DESC, created_at DESC LIMIT ?
                """, (f"%{tag_filter}%", limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT id, content, tags, source, created_at, access_count, score
                    FROM memories ORDER BY score DESC, created_at DESC LIMIT ?
                """, (limit,)).fetchall()
        return [
            {"id": r[0], "content": r[1], "tags": json.loads(r[2]), "source": r[3],
             "created_at": r[4], "access_count": r[5], "score": r[6]}
            for r in rows
        ]

    # ── Embeddings ─────────────────────────────────────────

    def _compute_embedding(self, text: str) -> bytes | None:
        """Embedding all-minilm via Ollama. None si Ollama indisponible.

        Pas de flag KO définitif : un échec est soit instantané (Ollama down,
        repli mots-clés sans pénalité), soit transitoire (modèle en cours de
        chargement) — dans ce cas l'appel suivant retente et réussit.
        """
        if not text:
            return None
        try:
            # ponytail: all-minilm a 256 tokens de contexte. Mesuré sur les vrais
            # chunks : 800 chars → HTTP 500 (schémas ASCII tokenisent dense),
            # 500 chars → toujours OK. On tronque avant d'envoyer ; le contenu
            # complet reste en base pour le recall mots-clés. Fenêtrage +
            # agrégation si la qualité sémantique venait à manquer.
            prompt = text[:500]
            req = urllib.request.Request(
                OLLAMA_URL,
                data=json.dumps({"model": EMBEDDING_MODEL, "prompt": prompt}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            # timeout large : le 1er appel charge le modèle en RAM
            with urllib.request.urlopen(req, timeout=30) as resp:
                vec = json.loads(resp.read()).get("embedding")
                if vec:
                    return struct.pack(f"{len(vec)}f", *vec)
                return None
        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError,
                json.JSONDecodeError, OSError):
            return None

    def stats(self) -> dict:
        with sqlite3.connect(str(self.db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            with_vector = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE vector IS NOT NULL").fetchone()[0]
            return {"total": total, "with_embeddings": with_vector,
                    "namespace": self.namespace, "db_path": str(self.db_path)}
