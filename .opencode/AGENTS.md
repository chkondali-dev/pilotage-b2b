# Session Learnings (2026-06-10)

## Convention Dashboard — Données

- **Colonne `Nom` dans les fichiers VC** : contient le nom de la convention (organisme), PAS le nom du client.
- **Colonne `Nom Client`** : contient le nom individuel du client.
- **Erreurs de saisie connues** : 4 enregistrements ont des noms individuels dans `Nom` au lieu du nom de convention :
  - AHMED ABIDI (magasin 412)
  - AMARA MISSAOUI (magasin 412)
  - BILEL BEN AMMAR (magasin 102)
  - MED KAIS SMAILI (magasin 204)
  → Ces entrées doivent être filtrées des vues "Convention".

## Seuil d'inactivité des conventions

- **Ne PAS utiliser 30 jours** comme seuil d'inactivité pour les conventions B2B → trop court, génère des faux positifs.
- **Seuil recommandé : 60 jours** (modifié dans `app.py` via un curseur sidebar : 15-180j, pas de 15, défaut 60).
- Fonction : `inactive_conventions()` ligne 493 — le paramètre `threshold_days` est passé dynamiquement depuis le slider sidebar.
- Toujours utiliser `seuil_inactif` (variable Streamlit) plutôt qu'une valeur en dur dans les labels.

## Architecture du Dashboard

- **Fichier principal** : `app.py` (2323+ lignes, Streamlit)
- **Sources de données** : fichiers Excel sur GitHub raw (voir `GITHUB_RAW` et `FILES` dans app.py)
- **Pas de base de données** : tout est chargé depuis des fichiers Excel via `load_all_data()`
- **Fichier TDC CONVENTION** : `TDC CONVENTION 1.xlsm` — colonne 0 contient les noms des conventions signées, mais les colonnes sont nommées 'Unnamed: N' (pas d'en-tête propre)

# Available Skills

## Behavioral Rules Skills

### /behavioral-rules
Create custom behavioral rules to prevent unwanted AI behaviors. Pattern-matching hooks that warn or block on dangerous commands, debug code, sensitive files, missing tests, and more.

## Plugin Development Skills

### /plugin-development
Comprehensive toolkit for creating Claude Code / OpenCode plugins. Covers plugin structure, commands, agents, skills, hooks, MCP integration, and testing.

## Git Automation Skills

### /git-automation
Automated git workflow: commit, push, and PR creation in a single flow. Smart branch management, commit messages from diff, and PR descriptions.

## Feature Development Skills

### /feature-dev-workflow
Structured 7-phase feature development: Discovery → Codebase Exploration → Clarifying Questions → Architecture Design → Implementation → Quality Review → Summary. Uses specialized agents (code-explorer, code-architect, code-reviewer) at each phase.

## Code Review Skills

### /code-review-workflow
Automated PR code review using multiple parallel agents with confidence-based scoring (0-100, threshold 80). Includes CLAUDE.md compliance checking, bug detection, finding validation, and false positive filtering.

## Security Skills

### /security-patterns
Comprehensive secure coding reference with 25+ vulnerability patterns across Python, JS/TS, and Go. Covers injection, XSS, SSRF, unsafe deserialization, crypto weaknesses, and more. Includes confidence scoring and false-positive filtering.

## Performance Skills

### /performance/optimize
Diagnose and fix code performance issues across algorithms, data structures, and computational complexity.

### /build-optimize
Optimize build times, bundle size, and asset processing.

### /optimize-db
Optimize database queries, caching strategies, and data layer performance.

### /runtime-optimize
Optimize browser rendering, animation performance, and network request efficiency.

## Context Management Skills

### /context-loader
Pre-fetches relevant context before starting work. Runs parallel searches across multiple angles, deduplicates results, and injects only the most relevant information.

### /memory-reviewer
Audits stored information quality — detects duplicates, contradictions, stale entries, and low-confidence items. Read-only analysis with actionable recommendations.

## Streamlit Skills

### /streamlit-react-component
Build custom React components (MUI, Tremor) for Streamlit apps.

## Usage

Use these skills by invoking them directly in prompts:
- "Use /security-patterns to audit this code for vulnerabilities"
- "Use /performance/optimize to improve algorithm efficiency"
- "Apply /build-optimize for faster builds"
- "Fix N+1 with /optimize-db"
- "Smooth animations with /runtime-optimize"
- "Load context with /context-loader before starting the task"
- "Audit project memories with /memory-reviewer"