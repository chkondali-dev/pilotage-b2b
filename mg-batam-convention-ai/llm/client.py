"""
Client LLM unifié — auto-détection Ollama > Groq, cache par prompt.
Équivalent de data/loader.py dans le dashboard.
"""
import functools
import re
import requests
from llm import config


@functools.lru_cache(maxsize=64)
def _ollama_available() -> bool:
    """Vérifie si Ollama tourne sur localhost (caché)."""
    try:
        r = requests.get(f"{config.OLLAMA_ENDPOINT}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def provider() -> str:
    """'ollama' si dispo, 'groq' si clé API, sinon ''."""
    if _ollama_available():
        return "ollama"
    if config.GROQ_API_KEY:
        return "groq"
    return ""


def chat(prompt: str, role: str = "analyse", system: str | None = None) -> str | None:
    """Appelle le LLM. role ∈ MODELS (analyse, negociation, redaction, comex).

    Retourne le texte de la réponse, ou None si aucun LLM dispo.
    """
    prov = provider()
    if not prov:
        print("  ⚠️  Aucun LLM disponible (Ollama offline, pas de clé API)")
        return None

    model = config.MODELS.get(role, config.MODELS["analyse"])
    headers = {"Content-Type": "application/json"}
    endpoint = f"{config.OLLAMA_ENDPOINT}/v1/chat/completions"

    if prov == "groq":
        endpoint = config.GROQ_ENDPOINT
        headers["Authorization"] = f"Bearer {config.GROQ_API_KEY}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system or "Tu es un expert juridique et commercial senior chez SMG. Réponds en français."},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
    }

    try:
        print(f"  [LLM] {model} via {prov}...")
        r = requests.post(endpoint, headers=headers, json=payload, timeout=900)  # ponytail: 7B sur CPU = lent
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        # Nettoyer le markdown parasite autour du JSON
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content)
        return content
    except Exception as e:
        print(f"  ⚠️  Erreur LLM: {e}")
        return None
