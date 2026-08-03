# Memory System — SQLite + Embeddings

**Purpose:** Mémoire locale persistante pour contexte AI entre sessions.
**Stack:** Python, SQLite, sentence-transformers (all-MiniLM-L6-v2), NumPy

## Structure
```
memory/
├── memory_store.py     # SQLite store + 384d vector search (cosine)
├── injector.py         # Hook session_start : injecte le contexte au début de chaque session
├── cli.py              # CLI pour interroger/administrer la mémoire
└── session_start.py    # Point d'entrée appelé par OpenCode
```

## Conventions
- Embeddings 384d via `all-MiniLM-L6-v2` (Ollama)
- Stockage : `~/.opencode_memory/pilotage_b2b.sqlite`
- Recherche par similarité cosine + filtrage metadata
- L'injecteur est connecté aux skills `/context-loader` et `/memory-reviewer`

## Commandes
```bash
python memory/cli.py search "query"           # Chercher dans la mémoire
python memory/cli.py add --key x --value y    # Ajouter une entrée
python memory/cli.py list                     # Lister les entrées récentes
```
