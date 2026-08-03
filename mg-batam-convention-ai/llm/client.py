"""
Client LLM unifié — auto-détection Ollama > Groq, cache par prompt.
Équivalent de data/loader.py dans le dashboard.
"""
import functools
import re
import requests
from llm import config


@functools.lru_cache(maxsize=64)
def _ollama_has_model(model: str) -> bool:
    """Vrai si Ollama tourne ET a le modèle demandé installé (caché)."""
    try:
        r = requests.get(f"{config.OLLAMA_ENDPOINT}/api/tags", timeout=2)
        if r.status_code != 200:
            return False
        tags = [t.get("name", "") for t in r.json().get("models", [])]
        return any(t == model or t.startswith(model + ":") for t in tags)
    except Exception:
        return False


def provider(model: str) -> str:
    """'ollama' si le modèle y est installé, 'groq' si clé API, sinon ''."""
    if _ollama_has_model(model):
        return "ollama"
    if config.GROQ_API_KEY:
        return "groq"
    return ""


def chat(prompt: str, role: str = "analyse", system: str | None = None,
         meta: bool = False) -> str | None | tuple:
    """Appelle le LLM. role ∈ MODELS (analyse, negociation, redaction, comex, brain).

    Retourne le texte de la réponse, ou None si aucun LLM dispo.
    meta=True → retourne (texte, meta) avec meta = {modele, provider, duree_s, usage}.
    """
    model = config.MODELS.get(role, config.MODELS["analyse"])
    prov = provider(model)
    if not prov:
        print("  ⚠️  Aucun LLM disponible (modèle absent d'Ollama, pas de clé API)")
        return (None, {}) if meta else None
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

    import time
    t_debut = time.perf_counter()
    try:
        print(f"  [LLM] {model} via {prov}...")
        r = requests.post(endpoint, headers=headers, json=payload, timeout=900)  # ponytail: 7B sur CPU = lent
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        # Nettoyer le markdown parasite autour du JSON
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content)
        duree = time.perf_counter() - t_debut
        print(f"  [LLM] {model} via {prov} — {duree:.1f}s")
        if meta:
            return content, {"modele": model, "provider": prov,
                             "duree_s": round(duree, 1), "usage": data.get("usage")}
        return content
    except Exception as e:
        print(f"  ⚠️  Erreur LLM: {e}")
        return (None, {}) if meta else None
