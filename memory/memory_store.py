"""
memory_store.py — Persistent memory for OpenCode sessions.

Stores decisions, conventions, patterns, and project knowledge in SQLite.
Falls back to keyword search when Ollama (embeddings) is not available.

Usage:
    from memory.memory_store import MemoryStore
    store = MemoryStore("my_project")
    store.remember("Ne pas utiliser ORM, préférer SQL brut", tags=["decision", "architecture"])
    results = store.recall("ORM")
"""

import sqlite3
import json
import hashlib
import time
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

MEMORY_DIR = Path.home() / ".opencode_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "all-minilm:latest"
EMBEDDING_DIM = 384


class MemoryStore:
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.db_path = MEMORY_DIR / f"{namespace}.sqlite"
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
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_tags
                ON memories(tags)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_score
                ON memories(score DESC)
            """)

    # ── Write ─────────────────────────────────────────────

    def remember(self, content: str, tags: Optional[list] = None,
                 source: str = "", no_embed: bool = False) -> int:
        """Store a memory. Returns memory ID.
        
        Set no_embed=True to skip embedding computation (e.g., during bulk indexing).
        """
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

    # ── Read ───────────────────────────────────────────────

    def recall(self, query: str, top_k: int = 10,
               min_score: float = 0.0) -> list[dict]:
        """
        Search memories. Uses embeddings if Ollama is available,
        falls back to keyword search.
        """
        query_vector = self._compute_embedding(query)

        if query_vector:
            return self._vector_search(query_vector, top_k, min_score)
        else:
            return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        terms = re.findall(r'\w+', query.lower())
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
                    "id": row[0],
                    "content": row[1],
                    "tags": json.loads(row[2]),
                    "source": row[3],
                    "created_at": row[4],
                    "access_count": row[5],
                    "score": row[6] + match_count * 0.1,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _vector_search(self, query_vector: bytes,
                       top_k: int, min_score: float) -> list[dict]:
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
                np.linalg.norm(query_np) * np.linalg.norm(stored_np) + 1e-10
            ))
            combined = sim * 0.8 + (row[6] / 10.0) * 0.2
            if combined >= min_score:
                scored.append({
                    "id": row[0],
                    "content": row[1],
                    "tags": json.loads(row[2]),
                    "source": row[3],
                    "created_at": row[4],
                    "access_count": row[5],
                    "score": round(combined, 4),
                    "similarity": round(sim, 4),
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def list_all(self, tag_filter: Optional[str] = None,
                 limit: int = 50) -> list[dict]:
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
            {
                "id": r[0], "content": r[1], "tags": json.loads(r[2]),
                "source": r[3], "created_at": r[4],
                "access_count": r[5], "score": r[6],
            }
            for r in rows
        ]

    # ── Utility ────────────────────────────────────────────

    _ollama_checked = False
    _ollama_ok = False

    def _compute_embedding(self, text: str) -> Optional[bytes]:
        """Try Ollama embedding. Returns packed bytes or None if unavailable.
        
        Checks connectivity once, then caches the result for subsequent calls.
        """
        if not text:
            return None
        if MemoryStore._ollama_checked and not MemoryStore._ollama_ok:
            return None
        if not MemoryStore._ollama_checked:
            MemoryStore._ollama_checked = True
            try:
                req = urllib.request.Request(
                    OLLAMA_URL,
                    data=json.dumps({
                        "model": EMBEDDING_MODEL,
                        "prompt": "ping"
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=2) as resp:
                    result = json.loads(resp.read())
                    MemoryStore._ollama_ok = bool(result.get("embedding"))
            except Exception:
                MemoryStore._ollama_ok = False
            return None  # Don't embed the ping

        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=json.dumps({
                    "model": EMBEDDING_MODEL,
                    "prompt": text
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
                vec = result.get("embedding")
                if vec:
                    import struct
                    return struct.pack(f"{len(vec)}f", *vec)
                return None
        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError,
                json.JSONDecodeError, OSError):
            return None

    def stats(self) -> dict:
        with sqlite3.connect(str(self.db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            with_vector = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE vector IS NOT NULL"
            ).fetchone()[0]
            return {
                "total": total,
                "with_embeddings": with_vector,
                "namespace": self.namespace,
                "db_path": str(self.db_path),
                "ollama_available": self._compute_embedding("test") is not None,
            }

    def close(self):
        pass  # SQLite context manager handles this
