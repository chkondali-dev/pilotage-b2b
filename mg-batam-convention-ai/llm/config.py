"""
Configuration centralisée — modèles LLM, endpoints, dossier du projet.
Équivalent de data/config.py dans le dashboard.
"""
import os
from pathlib import Path

# ── Dossiers ─────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent          # mg-batam-convention-ai/
KNOWLEDGE_DIR = ROOT / "KNOWLEDGE"
OUTPUTS_DIR = ROOT / "OUTPUTS"
AGENTS_DIR = ROOT / "AGENTS"
DATA_DIR = ROOT / "data"                               # registre CSV + base SQLite locale

for _d in (OUTPUTS_DIR / "rapports", OUTPUTS_DIR / "contrats", OUTPUTS_DIR / "syntheses", DATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Endpoints ────────────────────────────────────────────────
OLLAMA_ENDPOINT = "http://localhost:11434"

# ── Modèles par rôle ─────────────────────────────────────────
# Rôles "analyse" tournent en local (8B, confortable sur CPU 16GB).
# Rôle "redaction" passe par Groq/API (qualité française) — fallback local si pas de clé.
# Le modèle d'embeddings (RAG) est défini dans llm/store.py — store local autonome.
# brain : qwen2.5:7b par défaut (≈3× plus rapide que deepseek-r1:7b, qui raisonne ~9 min).
#        Revenir au raisonneur : CAI_BRAIN_MODEL=deepseek-r1:7b.
MODELS = {
    "analyse":  os.getenv("CAI_ANALYSE_MODEL",  "qwen2.5:7b"),        # audit, risque, comparaison
    "negociation": os.getenv("CAI_NEGO_MODEL",  "qwen2.5:7b"),        # stratégie
    "redaction": os.getenv("CAI_REDACTION_MODEL", "llama-3.3-70b-versatile"),  # Groq
    "comex":    os.getenv("CAI_COMEX_MODEL",    "qwen2.5:7b"),        # décision
    "brain":    os.getenv("CAI_BRAIN_MODEL",    "qwen2.5:7b"),    # raisonnement final (Ollama)
}

# ── Fallback API (Groq, OpenAI-compatible) ───────────────────
GROQ_ENDPOINT = os.getenv("LLM_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")
GROQ_API_KEY = os.getenv("LLM_API_KEY", "")

# Température basse : on veut du factuel, pas de la créativité
TEMPERATURE = 0.3
MAX_TOKENS = 4096  # ponytail: 8000 trop lent sur CPU — 4096 suffit pour un rapport structuré
