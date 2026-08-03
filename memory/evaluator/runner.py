"""
runner.py — Exécute le pipeline de raisonnement sur un corpus de test.

Usage :
    python -m memory.evaluator.runner
    python -m memory.evaluator.runner --sample 10
    python -m memory.evaluator.runner --category EXPLORE
    python -m memory.evaluator.runner --output results.json
    python -m memory.evaluator.runner --dry-run
"""

import argparse
import json
import time
import sys
from pathlib import Path
from typing import Optional

from .corpus import load_corpus
from .metrics import score_response, EvalMetrics


def _run_single_question(
    question_id: str,
    category: str,
    query: str,
    expected_keywords: list[str],
    expected_files: list[str],
    dry_run: bool = False,
) -> EvalMetrics:
    """Exécute le pipeline sur une question et mesure les résultats.

    En dry_run, on simule pour tester la structure sans vrai pipeline.
    """
    if dry_run:
        # Simuler une réponse
        time.sleep(0.05)
        fake_response = (
            f"Analyse de {question_id} : {query[:60]}... "
            f"Les modules concernés sont dans memory/. "
            f"Utilisation de SQLite pour la persistance. "
        )
        elapsed = 1.2  # simulé
        char_count = len(fake_response)
        return score_response(
            question_id=question_id,
            category=category,
            response_text=fake_response,
            expected_keywords=expected_keywords,
            expected_files=expected_files,
            elapsed=elapsed,
            char_count=char_count,
        )

    # ── Pipeline réel ─────────────────────────────────
    try:
        from memory.intent_planner import IntentPlanner
        from memory.context_builder import ContextBuilder
        from memory.dossier_builder import compile_dossier, RendererPrompt

        start = time.time()

        # 1. Planner
        planner = IntentPlanner()
        plan = planner.plan(query)

        # 2. Context Builder
        builder = ContextBuilder("pilotage_b2b")
        context_pack = builder.build(plan)

        # 3. Compilation
        dossier = compile_dossier(
            query=query,
            plan=plan,
            context_pack=context_pack,
        )

        # 4. Renderer
        response = RendererPrompt().render(dossier)

        elapsed = time.time() - start
        char_count = len(response)

        return score_response(
            question_id=question_id,
            category=category,
            response_text=response,
            expected_keywords=expected_keywords,
            expected_files=expected_files,
            elapsed=elapsed,
            char_count=char_count,
        )

    except Exception as e:
        elapsed = time.time() - start if 'start' in dir() else 0.0
        return EvalMetrics(
            question_id=question_id,
            category=category,
            erreur=str(e),
            temps_reponse=round(elapsed, 3),
        )


def run_evaluation(
    category: str = "",
    sample: int = 0,
    dry_run: bool = False,
    output: Optional[str] = None,
) -> list[EvalMetrics]:
    """Exécute l'évaluation sur tout le corpus.

    Args:
        category: Filtrer par catégorie (vide = toutes).
        sample: Nombre d'échantillons (0 = toutes).
        dry_run: Simuler sans vrai pipeline.
        output: Chemin fichier JSON pour sauvegarder.

    Returns:
        Liste des métriques par question.
    """
    questions = load_corpus(category=category, sample=sample)
    total = len(questions)

    print(f"\n{'='*55}")
    print(f"REASONING EVALUATOR - v{getattr(__import__('memory.evaluator.corpus', fromlist=['CORPUS_VERSION']), 'CORPUS_VERSION', '?')}")
    print(f"Questions: {total}  |  Mode: {'dry-run' if dry_run else 'pipeline'}")
    if category:
        print(f"Filtre: {category}")
    print(f"{'='*55}\n")

    results: list[EvalMetrics] = []

    for i, q in enumerate(questions, 1):
        label = f"[{i}/{total}] {q.id} ({q.category})"
        print(f"  {label}... ", end="", flush=True)

        metrics = _run_single_question(
            question_id=q.id,
            category=q.category,
            query=q.question,
            expected_keywords=q.expected_keywords,
            expected_files=q.expected_files,
            dry_run=dry_run,
        )

        results.append(metrics)

        status = f"[OK] {metrics.score_global:.2f}" if not metrics.erreur else f"[ERR] {metrics.erreur[:60]}"
        print(status)

    # Stats globales
    scored = [r for r in results if not r.erreur]
    if scored:
        avg_score = sum(r.score_global for r in scored) / len(scored)
        avg_time = sum(r.temps_reponse for r in scored) / len(scored)
        avg_exact = sum(r.exactitude for r in scored) / len(scored)
        avg_pert = sum(r.pertinence for r in scored) / len(scored)

    print(f"\n{'-'*55}")
    print(f"  Score global moyen : {avg_score:.3f}")
    print(f"  Exactitude moyenne : {avg_exact:.3f}")
    print(f"  Pertinence moyenne : {avg_pert:.3f}")
    print(f"  Temps moyen/reponse : {avg_time:.2f}s")
    print(f"  Questions reussies   : {len(scored)}/{total}")
    print(f"{'-'*55}\n")

    # Sauvegarder si demandé
    if output:
        _save_results(results, output)

    return results


def _save_results(results: list[EvalMetrics], path: str):
    """Sauvegarde les résultats en JSON."""
    data = []
    for r in results:
        data.append({
            "question_id": r.question_id,
            "category": r.category,
            "exactitude": r.exactitude,
            "pertinence": r.pertinence,
            "couverture_fichiers": r.couverture_fichiers,
            "tokens_consommes": r.tokens_consommes,
            "temps_reponse": r.temps_reponse,
            "fichiers_references": r.fichiers_references,
            "score_global": r.score_global,
            "erreur": r.erreur,
        })

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        "version": "1.0.0",
        "total": len(data),
        "results": data,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Resultats sauvegardes : {output_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReasoningEvaluator - benchmark du Project Brain")
    parser.add_argument("--category", "-c", default="", help="Catégorie (EXPLORE|DEBUG|REFACTOR|ARCH|REPORT|GENERAL)")
    parser.add_argument("--sample", "-s", type=int, default=0, help="Nombre d'échantillons")
    parser.add_argument("--output", "-o", default="", help="Fichier JSON de sortie")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Simulation sans vrai pipeline")
    args = parser.parse_args()

    run_evaluation(
        category=args.category,
        sample=args.sample,
        dry_run=args.dry_run,
        output=args.output or None,
    )
