"""
metrics.py — Fonctions de scoring pour le ReasoningEvaluator.

Mesure :
  - exactitude : proportion de mots-clés attendus présents dans la réponse
  - pertinence : rapport signal/bruit de la réponse
  - tokens_consommes : taille de la réponse en caractères (proxy)
  - temps_reponse : temps d'exécution en secondes
  - fichiers_references : fichiers listés dans les artefacts
  - score_global : moyenne pondérée des sous-scores
"""

import time
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvalMetrics:
    """Métriques brutes pour une question."""
    question_id: str
    category: str

    # Scoring
    exactitude: float = 0.0       # 0.0 → 1.0
    pertinence: float = 0.0       # 0.0 → 1.0
    couverture_fichiers: float = 0.0  # 0.0 → 1.0

    # Consommation
    tokens_consommes: int = 0     # proxy: nombre de caractères
    temps_reponse: float = 0.0    # secondes
    fichiers_references: list[str] = field(default_factory=list)

    # Résultat
    score_global: float = 0.0     # moyenne pondérée
    erreur: str = ""


def _keyword_match_score(text: str, keywords: list[str]) -> float:
    """Proportion de mots-clés attendus présents dans le texte (insensible à la casse)."""
    if not keywords:
        return 1.0  # pas de mots-clés = pas de pénalité
    text_lower = text.lower()
    found = 0
    for kw in keywords:
        if kw.lower() in text_lower:
            found += 1
    return found / len(keywords)


def _file_match_score(files_referenced: list[str], expected_files: list[str]) -> float:
    """Proportion de fichiers attendus référencés."""
    if not expected_files:
        return 1.0
    ref_lower = [f.lower().replace("\\", "/") for f in files_referenced]
    found = 0
    for ef in expected_files:
        ef_norm = ef.lower().replace("\\", "/")
        if any(ef_norm in r for r in ref_lower):
            found += 1
    return found / len(expected_files)


def _noise_ratio(text: str, keywords: list[str]) -> float:
    """Rapport signal/bruit : proportion du texte qui est du bruit (ponctuation, mots vides).
    
    Un score proche de 1.0 = peu de bruit, texte dense en information.
    """
    if not text.strip():
        return 0.3  # texte vide = bruit maximal

    words = text.split()
    if not words:
        return 0.3

    # Mots vides français + anglais
    stop_words = {
        "le", "la", "les", "un", "une", "des", "du", "de", "ce", "cet", "cette",
        "ces", "mon", "ton", "son", "notre", "votre", "leur", "mes", "tes", "ses",
        "nos", "vos", "leurs", "et", "ou", "mais", "donc", "car", "ni", "que",
        "qui", "quoi", "dont", "où", "sur", "sous", "dans", "avec", "sans",
        "pour", "par", "à", "au", "aux", "en", "vers", "chez", "entre", "depuis",
        "pendant", "avant", "après", "the", "a", "an", "of", "in", "to", "for",
        "with", "on", "at", "from", "by", "is", "it", "as", "be", "this", "that",
        "was", "are", "were", "been", "being", "have", "has", "had", "do", "does",
        "did", "will", "would", "can", "could", "should", "may", "might", "shall",
        "not", "no", "nor", "so", "if", "then", "than", "too", "very", "just",
        "about", "also", "how", "what", "when", "where", "which", "who", "why",
        "fichier", "fonction", "classe", "module", "code", "projet",
    }

    meaningful = sum(1 for w in words if w.lower() not in stop_words and len(w) > 2)
    ratio = meaningful / len(words) if words else 0.0

    # Remapper [0.0, 1.0] → score de pertinence (un texte 100% mots vides = 0.3)
    return 0.3 + ratio * 0.7


def _extract_files_from_text(text: str, base_paths: Optional[list[str]] = None) -> list[str]:
    """Extrait les chemins de fichiers d'un texte."""
    files = set()
    # Chemins .py, .xlsx, .json, .md, .yaml, .toml, .sh
    for m in re.finditer(r'[\w./\\\-]+\.(?:py|xlsx?|json|md|yaml|toml|sh|csv)', text):
        path = m.group(0)
        # Filtrer les chemins trop courts ou génériques
        if len(path) > 5 and path not in ("fichier.py", "module.py", "app.py"):
            files.add(path)
    return sorted(files)


def score_response(
    question_id: str,
    category: str,
    response_text: str,
    expected_keywords: list[str],
    expected_files: list[str],
    elapsed: float = 0.0,
    char_count: int = 0,
) -> EvalMetrics:
    """Calcule l'ensemble des métriques pour une réponse.

    Args:
        question_id: Identifiant de la question.
        category: Catégorie de la question.
        response_text: Texte complet de la réponse à évaluer.
        expected_keywords: Mots-clés attendus dans une bonne réponse.
        expected_files: Fichiers qui devraient être référencés.
        elapsed: Temps d'exécution en secondes.
        char_count: Nombre de caractères de la réponse (proxy tokens).

    Returns:
        EvalMetrics avec tous les scores calculés.
    """
    text = response_text.strip()
    
    # 1. Exactitude : présence des mots-clés
    exact = _keyword_match_score(text, expected_keywords)

    # 2. Pertinence : rapport signal/bruit
    pert = _noise_ratio(text, expected_keywords)

    # 3. Couverture fichiers
    files_found = _extract_files_from_text(text)
    file_score = _file_match_score(files_found, expected_files)

    # 4. Score global : pondéré
    #    exactitude 40%, pertinence 25%, fichiers 20%, temps 15%
    #    (le temps est normé : < 2s = 1.0, > 30s = 0.0)
    time_score = max(0.0, min(1.0, 1.0 - (elapsed - 2.0) / 28.0)) if elapsed > 0 else 0.5
    global_score = (
        exact * 0.40 +
        pert * 0.25 +
        file_score * 0.20 +
        time_score * 0.15
    )

    return EvalMetrics(
        question_id=question_id,
        category=category,
        exactitude=round(exact, 4),
        pertinence=round(pert, 4),
        couverture_fichiers=round(file_score, 4),
        tokens_consommes=char_count,
        temps_reponse=round(elapsed, 3),
        fichiers_references=files_found,
        score_global=round(global_score, 4),
    )
