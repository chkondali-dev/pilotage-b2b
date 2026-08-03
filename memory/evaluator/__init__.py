"""
evaluator — Benchmark de raisonnement pour le Project Brain.

Usage:
    python -m memory.evaluator.runner              # Run complet sur tout le corpus
    python -m memory.evaluator.runner --sample 10  # Sous-ensemble rapide
    python -m memory.evaluator.runner --category EXPLORE  # Par catégorie
    python -m memory.evaluator.report              # Afficher le dernier scoreboard
"""

from .corpus import load_corpus, list_categories
from .metrics import score_response
from .runner import run_evaluation
from .report import print_report

__all__ = ["load_corpus", "list_categories", "score_response", "run_evaluation", "print_report"]
