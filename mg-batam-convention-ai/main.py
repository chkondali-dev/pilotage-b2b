"""
Convention AI — CLI. Point d'entrée de l'assistant.

Usage :
    python main.py audit <fichier>
    python main.py risque <fichier>
    python main.py comparer <version_a> <version_b>
    python main.py negocier <contexte>
    python main.py comex <dossier_ou_texte>
    python main.py workflow revue_complete <fichier> [--negocier]
    python main.py workflow nouvelle <contexte>
    python main.py workflow renouvellement <fichier> [--performance "texte"]
    python main.py indexer            # indexe KNOWLEDGE/ dans la mémoire
    python main.py question "texte"   # question avec contexte KNOWLEDGE (RAG)
"""
import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ponytail: console Windows + emojis
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour memory/

from llm import agents, client, rag
import workflows


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def main() -> None:
    p = argparse.ArgumentParser(prog="convention-ai")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("audit", help="Audit clause par clause")
    sp.add_argument("fichier")
    sp.add_argument("--rag", action="store_true", help="Enrichir avec KNOWLEDGE/")

    sp = sub.add_parser("risque", help="Analyse de risque grille SMG")
    sp.add_argument("fichier")

    sp = sub.add_parser("comparer", help="Comparer deux versions")
    sp.add_argument("version_a")
    sp.add_argument("version_b")

    sp = sub.add_parser("negocier", help="Fiche de négociation")
    sp.add_argument("contexte")

    sp = sub.add_parser("comex", help="Décision comex")
    sp.add_argument("dossier")

    sp = sub.add_parser("workflow")
    sp.add_argument("type", choices=["revue_complete", "nouvelle", "renouvellement"])
    sp.add_argument("fichier", nargs="?")
    sp.add_argument("--negocier", action="store_true")
    sp.add_argument("--performance", default="")

    sub.add_parser("indexer", help="Indexer KNOWLEDGE/ (RAG)")

    sp = sub.add_parser("question", help="Question avec RAG sur KNOWLEDGE/")
    sp.add_argument("texte")

    args = p.parse_args()

    if args.cmd == "audit":
        doc = _read(args.fichier)
        prompt = doc
        if args.rag:
            prompt = rag.enrichir_prompt(f"audit convention {Path(args.fichier).stem}", doc)
        print(agents.audit(prompt, args.fichier) or "❌ Échec LLM")
    elif args.cmd == "risque":
        print(agents.analyse_risque(_read(args.fichier), args.fichier) or "❌ Échec LLM")
    elif args.cmd == "comparer":
        print(agents.comparer(_read(args.version_a), _read(args.version_b)) or "❌ Échec LLM")
    elif args.cmd == "negocier":
        print(agents.preparer_negociation(args.contexte) or "❌ Échec LLM")
    elif args.cmd == "comex":
        print(agents.synthese_comex(args.dossier) or "❌ Échec LLM")
    elif args.cmd == "workflow":
        if args.type == "revue_complete":
            if not args.fichier:
                p.error("workflow revue_complete requiert <fichier>")
            workflows.revue_complete(args.fichier, renégocier=args.negocier)
        elif args.type == "nouvelle":
            if not args.fichier:
                p.error("workflow nouvelle requiert <contexte>")
            workflows.nouvelle_convention(args.fichier)
        elif args.type == "renouvellement":
            if not args.fichier:
                p.error("workflow renouvellement requiert <fichier>")
            workflows.renouvellement(args.fichier, args.performance)
    elif args.cmd == "indexer":
        n = rag.indexer()
        print(f"✅ {n} chunks indexés depuis KNOWLEDGE/")
    elif args.cmd == "question":
        prompt = rag.enrichir_prompt(args.texte, args.texte)
        system = "Tu es un expert des conventions B2B SMG (MG, BATAM, cession sur salaire). Réponds en français, factuel, cité si possible."
        print(client.chat(prompt, role="analyse", system=system) or "❌ Échec LLM")


if __name__ == "__main__":
    main()
