# MG-Batam Convention AI — Design Document

**Date** : 2026-06-17
**Statut** : ⚠️ **SUPERSEDED** — l'implémentation retenue est un **CLI Python autonome**
(`mg-batam-convention-ai/` : `main.py`, `llm/`, `workflows.py`), avec LLM local Ollama
+ fallback Groq, et RAG sur `KNOWLEDGE/`. Ce document reste la référence d'architecture
pour la structure AGENTS/KNOWLEDGE/PROMPTS/WORKFLOWS/OUTPUTS et les rôles des 5 agents.

## 1. Objectif

Assistant IA tout-en-un pour le cycle de vie complet des conventions d'entreprise : audit, création, négociation, renouvellement. Cinq agents spécialisés orchestrés via oh-my-openagent (Ultimate Edition), utilisés par un seul expert métier en mode brainstorming + délégation.

## 2. Architecture

```
mg-batam-convention-ai/
│
├── AGENTS.md                 ← Point d'entrée OpenCode (chargé automatiquement)
├── AGENTS/                   ← Définitions de rôle (personnalité, expertise, règles)
│   ├── juriste.md
│   ├── negociateur.md
│   ├── contradicteur.md
│   ├── comex.md
│   └── redacteur.md
│
├── .omo/
│   └── rules/                ← Règles injectées par oh-my-openagent à chaque prompt
│       ├── 01-contexte-projet.md
│       └── 02-glossaire-conventions.md
│
├── KNOWLEDGE/                ← Base documentaire (lecture seule pour les agents)
│   ├── conventions/
│   │   ├── convention_modele_rtt.docx
│   │   └── conditions_generales.md
│   ├── procedures/
│   │   ├── procedure_validation.md
│   │   └── politique_risque.md
│   ├── reference/
│   │   └── faq_conventions.md
│   └── INDEX.md              ← Table des matières générée
│
├── PROMPTS/                  ← Templates de prompts réutilisables
│   ├── audit_convention.md
│   ├── comparaison_versions.md
│   ├── analyse_risque.md
│   ├── preparation_negociation.md
│   └── synthese_comex.md
│
├── WORKFLOWS/                ← Procédures multi-étapes orchestrées
│   ├── revue_complete.md
│   ├── nouvelle_convention.md
│   └── renouvellement_convention.md
│
└── OUTPUTS/                  ← Sorties générées par les agents
    ├── rapports/
    ├── contrats/
    └── synthèses/
```

## 3. Agents

| Agent | Fichier | Rôle | Modèle recommandé |
|-------|---------|------|-------------------|
| juriste | `AGENTS/juriste.md` | Expert juridique : conformité, code du travail, clauses | Claude Opus 4.7 |
| negociateur | `AGENTS/negociateur.md` | Stratège : concessions, BATNA, contre-propositions | GPT-5.5 |
| contradicteur | `AGENTS/contradicteur.md` | Avocat du diable : vulnérabilités, angles morts | GPT-5.5 |
| comex | `AGENTS/comex.md` | Décideur stratégique : risques business, go/no-go | Claude Sonnet 4.6 |
| redacteur | `AGENTS/redacteur.md` | Rédacteur : clarté, structure, formulation juridique | Claude Sonnet 4.6 |

### Interaction entre agents
- **Audit** : Juriste + Contradicteur en parallèle, rapports fusionnés
- **Négociation** : Négociateur + Juriste — clauses acceptables vs intouchables
- **Rédaction** : Rédacteur → Comex (validation)
- **Revue complète** : Juriste → Contradicteur → Négociateur → Rédacteur → Comex

## 4. Déclaration des agents

Les agents ne sont **pas** déclarés dans `oh-my-openagent.json` (celui-ci gère les agents système : Sisyphus, Hephaestus, etc.). Les agents métier sont des **personas** définis dans des fichiers `AGENTS/*.md`, chargés via `AGENTS.md` en début de session OpenCode.

**Fonctionnement :**
- `AGENTS.md` (racine du projet) est le point d'entrée — il liste les agents disponibles et leur fichier
- Chaque `AGENTS/*.md` définit la personnalité, l'expertise, les règles de comportement
- L'utilisateur invoque un agent par son nom : `@juriste "audite cette clause"`
- Oh-my-openagent injecte `AGENTS.md` et `.omo/rules/` automatiquement dans le contexte
- Les modèles recommandés (section 3) sont des suggestions — l'utilisateur peut spécifier un modèle dans le prompt

**Emplacement du projet :** À définir — soit dans `C:\Users\hachk\pilotage_b2b\mg-batam-convention-ai\` (sous-projet lié), soit dans un dossier indépendant.

## 5. Flux de travail

### Revue complète d'une convention existante
1. `@juriste` : audit clause par clause → `OUTPUTS/rapports/`
2. `@contradicteur` : review du rapport, cherche failles → complète le rapport
3. `@negociateur` : prépare stratégie de négociation → `OUTPUTS/synthèses/`
4. `@redacteur` : rédige propositions d'amendement → `OUTPUTS/contrats/`
5. `@comex` : décision (valider/modifier/rejeter)

### Nouvelle convention
1. Brainstorming avec l'utilisateur sur les besoins
2. `@redacteur` : première ébauche → `OUTPUTS/contrats/`
3. `@juriste` : vérification conformité → `OUTPUTS/rapports/`
4. `@contradicteur` : stress-test du contrat
5. `@comex` : validation finale

## 6. Règles de fonctionnement

- Les agents **lisent** `KNOWLEDGE/` mais n'y écrivent jamais
- Toute sortie va dans `OUTPUTS/` avec sous-dossier par type
- `AGENTS.md` est le point d'entrée — chargé automatiquement par OpenCode
- `.omo/rules/` injecte le contexte projet et le glossaire à chaque prompt
- Les workflows sont exécutés séquentiellement ou en parallèle selon les dépendances

## 7. Contraintes

- Usage solo (expert métier unique)
- Conventions internes + négociations externes
- Mode brainstorming + délégation
- Intégration oh-my-openagent (Ultimate)
