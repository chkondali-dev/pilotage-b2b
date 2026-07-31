# Prompt — Comparaison de versions

Utilisateur : `@redacteur "Compare <version A> et <version B> de la convention X"`

## Consigne

Compare deux versions d'un même document et produis une table de différences actionnable.

## Format de sortie

```markdown
# Comparaison — <Convention> (<version A> vs <version B>)
**Date :** <date>

## Différences

| Clause | Version A | Version B | Impact | Recommandation |
|---|---|---|---|---|
| <n° + intitulé> | <extrait A> | <extrait B> | 🔴/🟠/🟡 + effet | <accepter / refuser / renégocier> |

## Résumé
- <nb> clauses modifiées : <nb> à l'avantage de SMG, <nb> au désavantage
- Évolution globale de l'exposition : <phrase chiffrée>

## Points d'attention
- <clauses nouvelles ou supprimées>
- <changements de montants/taux/durée>
```

## Règles

- Chaque différence : extraits exacts des deux versions.
- Impact : chiffré quand possible (ex: +2% de taux = +X TND/an).
- Indique clairement quelle version est la plus favorable à SMG.
