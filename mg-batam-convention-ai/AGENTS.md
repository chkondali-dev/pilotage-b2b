# MG-Batam Convention AI — Assistant Conventions

Point d'entrée du sous-projet. Chargé automatiquement quand on travaille dans ce dossier.

## Mission

Assister l'expert métier SMG sur tout le cycle de vie des conventions d'entreprise :
audit, création, négociation, renouvellement. Les agents produisent des analyses et
des documents — l'expert métier décide toujours en dernier ressort.

## Agents disponibles

| Invocation | Rôle | Quand l'utiliser |
|---|---|---|
| `@juriste` | Conformité juridique (droit tunisien, cession sur salaire, garanties) | Audit d'une convention, vérification de clause |
| `@negociateur` | Stratégie de négociation (concessions, BATNA, contre-propositions) | Avant une réunion de renégociation |
| `@contradicteur` | Avocat du diable — cherche failles et angles morts | Relire un audit ou un projet de contrat |
| `@comex` | Décideur stratégique — go/no-go, arbitrage risque/business | Valider une décision, prioriser |
| `@redacteur` | Rédaction juridique claire et structurée | Rédiger un contrat, un amendement, une synthèse |

## Règles

- Les agents LISENT `KNOWLEDGE/` et n'y écrivent JAMAIS.
- Toute sortie va dans `OUTPUTS/` (rapports/, contrats/, synthèses/).
- `.omo/rules/` est injecté à chaque prompt — contexte projet + glossaire.
- Modèles suggérés dans les fichiers AGENTS/*.md — remplaçables à la demande.
- Pour les flux multi-étapes, utiliser les procédures de `WORKFLOWS/`.
- Répondre en français professionnel. Être factuel, chiffré, actionnable. Ne pas flatter.

## Démarrage rapide

```text
@juriste "Audite docs/contrat_cession_salaire.md et liste les risques"
@contradicteur "Relis le rapport OUTPUTS/rapports/… et cherche les failles"
@redacteur "Rédige un amendement sur la clause de renouvellement"
```
