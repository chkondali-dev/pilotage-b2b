"""
report.py — Génération du scoreboard d'évaluation.

Usage :
    python -m memory.evaluator.report              # Afficher le dernier résultats
    python -m memory.evaluator.report results.json  # Afficher un fichier spécifique
"""

import json
import sys
from pathlib import Path
from typing import Optional

from .metrics import EvalMetrics


def _load_results(path: Optional[str] = None) -> list[EvalMetrics]:
    """Charge les résultats depuis un fichier JSON.

    Cherche par défaut dans results/evaluator-latest.json.
    """
    if path is None:
        candidates = [
            Path("results/evaluator-latest.json"),
            Path("memory/evaluator/results.json"),
        ]
        for c in candidates:
            if c.exists():
                path = str(c)
                break
        if path is None:
            print("  Aucun fichier de résultats trouvé.")
            print("  Lancer d'abord : python -m memory.evaluator.runner --output results.json")
            sys.exit(1)

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    results = []
    for r in data.get("results", []):
        results.append(EvalMetrics(
            question_id=r.get("question_id", ""),
            category=r.get("category", ""),
            exactitude=r.get("exactitude", 0.0),
            pertinence=r.get("pertinence", 0.0),
            couverture_fichiers=r.get("couverture_fichiers", 0.0),
            tokens_consommes=r.get("tokens_consommes", 0),
            temps_reponse=r.get("temps_reponse", 0.0),
            fichiers_references=r.get("fichiers_references", []),
            score_global=r.get("score_global", 0.0),
            erreur=r.get("erreur", ""),
        ))
    return results


def _by_category(results: list[EvalMetrics]) -> dict[str, list[EvalMetrics]]:
    """Groupe les résultats par catégorie."""
    cats: dict[str, list[EvalMetrics]] = {}
    for r in results:
        cats.setdefault(r.category, []).append(r)
    return cats


def print_report(path: Optional[str] = None) -> dict:
    """Affiche le scoreboard complet et retourne les statistiques.

    Args:
        path: Chemin vers le fichier JSON de résultats.

    Returns:
        Dict avec les stats globales et par catégorie.
    """
    results = _load_results(path)

    if not results:
        print("\n  Aucun résultat à afficher.\n")
        return {}

    sep = "=" * 55
    dash = "-" * 55

    # -- Header --
    print(f"\n{sep}")
    print("REASONING EVALUATOR - SCOREBOARD")
    print(f"{sep}")
    print(f"Questions : {len(results)}")
    reussies = sum(1 for r in results if not r.erreur)
    echouees = len(results) - reussies
    print(f"Reussies  : {reussies}")
    print(f"Echouees  : {echouees}")
    print(f"{dash}\n")

    # -- Par categorie --
    by_cat = _by_category(results)
    cat_data: dict[str, dict] = {}

    print(f"{'Categorie':<15} {'N':>4} {'Score':>7} {'Exact.':>7} {'Pert.':>7} {'Tps/s':>7}")
    print(f"{dash}")

    for cat in sorted(by_cat.keys()):
        items = by_cat[cat]
        scored = [r for r in items if not r.erreur]
        n = len(items)
        if scored:
            avg_score = sum(r.score_global for r in scored) / len(scored)
            avg_exact = sum(r.exactitude for r in scored) / len(scored)
            avg_pert = sum(r.pertinence for r in scored) / len(scored)
            avg_time = sum(r.temps_reponse for r in scored) / len(scored)
        else:
            avg_score = avg_exact = avg_pert = 0.0
            avg_time = 0.0

        cat_data[cat] = {
            "count": n,
            "score_moyen": round(avg_score, 4),
            "exactitude_moyenne": round(avg_exact, 4),
            "pertinence_moyenne": round(avg_pert, 4),
            "temps_moyen": round(avg_time, 3),
        }

        print(f"{cat:<15} {n:>4} {avg_score:>7.3f} {avg_exact:>7.3f} {avg_pert:>7.3f} {avg_time:>7.2f}")

    # -- Global --
    print(f"{dash}")
    scored = [r for r in results if not r.erreur]
    if scored:
        g_score = sum(r.score_global for r in scored) / len(scored)
        g_exact = sum(r.exactitude for r in scored) / len(scored)
        g_pert = sum(r.pertinence for r in scored) / len(scored)
        g_time = sum(r.temps_reponse for r in scored) / len(scored)
    else:
        g_score = g_exact = g_pert = g_time = 0.0

    print(f"{'GLOBAL':<15} {len(results):>4} {g_score:>7.3f} {g_exact:>7.3f} {g_pert:>7.3f} {g_time:>7.2f}")
    print(f"{sep}\n")

    # -- Details erreurs --
    failed = [r for r in results if r.erreur]
    if failed:
        print("ERREURS :")
        for r in failed:
            print(f"  {r.question_id:<10} {r.erreur[:80]}")
        print()

    # -- Top / Flop --
    scored_sorted = sorted(
        [r for r in results if not r.erreur],
        key=lambda x: x.score_global, reverse=True
    )
    if scored_sorted:
        print("TOP 3 :")
        for r in scored_sorted[:3]:
            print(f"  {r.question_id:<10} {r.score_global:.3f}")
        print()

        print("FLOP 3 :")
        for r in scored_sorted[-3:]:
            print(f"  {r.question_id:<10} {r.score_global:.3f}")
        print()

    # -- Stats consolidees --
    stats = {
        "total": len(results),
        "reussies": reussies,
        "echouees": echouees,
        "score_global_moyen": round(g_score, 4) if scored else 0,
        "exactitude_moyenne": round(g_exact, 4) if scored else 0,
        "pertinence_moyenne": round(g_pert, 4) if scored else 0,
        "temps_moyen": round(g_time, 3) if scored else 0,
        "par_categorie": cat_data,
    }

    return stats


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    print_report(path)
