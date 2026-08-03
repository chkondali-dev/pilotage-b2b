"""
session_start.py — Appelé au début de chaque session OpenCode.

Injecte le contexte pertinent du projet dans le prompt.
Usage: python memory/session_start.py [query]
"""

import sys
from memory.injector import inject_context, summarize_project_state

# Récupère la query depuis les args ou utilise le dernier message
query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""

# Charge le résumé du projet
state = summarize_project_state("pilotage_b2b")
if state:
    print(state)
    print()

# Si une query est fournie, injecte le contexte pertinent
if query:
    ctx = inject_context(query, "pilotage_b2b")
    if ctx:
        print(ctx)

if not state and not query:
    print("Aucun contexte mémoire disponible. Commencez par stocker des décisions :")
    print("  python -m memory.cli remember \"<decision>\" --tags tag1,tag2")
