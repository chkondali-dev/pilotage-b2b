#!/usr/bin/env bash
# memory-inject.sh — Hook appelé au début d'une session OpenCode
# Injecte le contexte pertinent issu de la mémoire persistante.
#
# Installation:
#   1. Copier dans .opencode/hooks/
#   2. Référencer dans opencode.json: "hooks: { "SessionStart": ["memory-inject.sh"] }
#
# Dépendances: Python 3, memory/memory_store.py

SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHONPATH="$SCRIPT_DIR" python3 -c "
from memory.injector import inject_context
import sys

# Le contexte est injecté via stdout — OpenCode le capture
ctx = inject_context(' '.join(sys.argv[1:]) if len(sys.argv) > 1 else '')
if ctx:
    print(ctx)
" "$@"
