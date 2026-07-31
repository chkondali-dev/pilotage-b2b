# Prompt — Analyse de risque

Utilisateur : `@juriste "Analyse le risque de la convention X"` ou `@contradicteur` en contre-audit

## Consigne

Évalue le risque global de la convention (ou du portefeuille de conventions) selon la grille SMG.

## Grille de risque SMG

| Profil | Risque |
|---|---|
| Cession sur salaire + bonne tendance | `faible` |
| Garantie solidaire seule ou tendance irrégulière | `moyen` |
| Baisse continue 2+ mois OU lettre de change seule | `élevé` |

## Format de sortie

```markdown
# Analyse de risque — <Convention ou Portefeuille>
**Date :** <date>

## Profil de garantie
- Cession confirmée Tribunal Cantonal : ✅ / ❌ / ⚠️ <détail>
- Notification Paierie Générale : ✅ / ❌ / ⚠️ <détail>
- Garanties additionnelles : <liste>
- Respect du tiers saisissable : ✅ / ❌ / ⚠️

## Exposition
- Encours : <montant TND>
- CA tendance : <évolution N/N-1>
- Concentration : <part du CA total si applicable>

## Risque global : 🟢 faible / 🟠 moyen / 🔴 élevé
- <justification 2-3 lignes>

## Recommandation
- reconduire / renégocier / surveiller / relancer urgent / suspendre
- <action concrète, 1 phrase>
```

## Règles

- Un seul critère `🔴` tire le risque global vers le haut.
- Toujours vérifier la confirmation Tribunal Cantonal — c'est le point le plus critique.
- Si données de tendance disponibles (dashboard), les intégrer ; sinon le dire explicitement.
- Chaque faille suit la **grille de risque unifiée** (AGENTS/contradicteur.md) : gravité, probabilité, impact financier estimé.
- Ne cite que les textes présents dans KNOWLEDGE/ ou le document — sinon « à confirmer par un juriste ».
